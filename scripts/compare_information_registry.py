"""Real local CPU replay on the frozen 670 rows, never a human approval."""
import argparse
import copy
import json
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.process import run_worker
from notetaker.domain.minutes import content_digest
from notetaker.domain.information_registry import coverage
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService
from notetaker.services.pipeline import assemble_summary
from notetaker.services.evidence import require_valid_evidence

p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True)
p.add_argument('--prepare-only',action='store_true');p.add_argument('--resume',action='store_true')
args=p.parse_args();work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
snapshot=ROOT/'output/summary-paragraphs/38a6b4c9d8704b669d4acd8a49c2ff8e/snapshot.sqlite3'
sid='0ce77b44-c8a0-482f-be0d-ef5a68b80aa2';before=sha256_file(snapshot)
data=work/'data';data.mkdir(exist_ok=True);dbpath=data/'notetaker.sqlite3'
if not dbpath.exists():
    with sqlite3.connect(snapshot.as_uri()+'?mode=ro',uri=True) as source,sqlite3.connect(dbpath) as target:source.backup(target)
store=SessionStore(data);service=RegistryService(store);state=store.get(sid)
original_rows=copy.deepcopy(state['utterances']);old_draft=copy.deepcopy(state['draft'])
baseline=json.loads((snapshot.parent/'standard-4min/draft.json').read_text(encoding='utf-8'))
models=ModelPaths();models.verify();inference=work/'inference';inference.mkdir(exist_ok=True)
report={'scope':'same 670 frozen utterances; actual Qwen CPU; no ASR/diarization change; no human approval',
    'status':'running','source_snapshot_sha256':before,'transcription_rows':len(original_rows),
    'model_sha256':sha256_file(models.llm),'binary_sha256':sha256_file(models.llama),
    'human_reference_available':False,'human_review_created':False,
    'dimensions':{key:{'status':'not_measured_without_human_annotation'} for key in
        ['semantic_theme_coverage','semantic_information_loss','attribution_errors','meaning_inversions','grouping_relevance','writing_quality']}}
if args.resume and (work/'comparison.json').exists():
    previous=json.loads((work/'comparison.json').read_text(encoding='utf-8'))
    if previous.get('source_snapshot_sha256')!=before:raise ValueError('SOURCE_SNAPSHOT_CHANGED')
timings={x.name:x.stat().st_mtime_ns for x in inference.glob('*.timing.json')};started=time.perf_counter()
active=None
try:
    active=service.initialize(sid)
    request={'engine':'llm','device':'cpu','binary':str(models.llama),'model':str(models.llm),
        'workspace':str(inference),'registry':active['content'],'utterances':state['utterances'],
        'lexicon':state['metadata'].get('lexicon',[]),'summary_length':'standard','task':'registry_prepare'}
    if active['content']['processing']['status']!='ready_for_review':
        atomic_json(work/'prepare.request.json',request)
        print('Real CPU preparation started; all source inventory is already persisted.',flush=True)
        response=run_worker(work/'prepare.request.json',timeout=14400)
        atomic_json(work/'prepare.response.json',response)
        service.save(sid,response['result']['registry'],expected_id=active['id'],actor='Qwen CPU — essai réel',reason='Préparation sur copie isolée, à relire')
        active=service.latest(sid)
    report.update(status='prepared',coverage=coverage(active['content']),registry_revision=active['revision'],
        subjects=dict(Counter(e['subject'] for e in active['content']['entries'] if e['category']=='information')),
        verification=dict(Counter(e['verification'] for e in active['content']['entries'] if e['category']=='information')),
        rejection_reasons=dict(Counter(r for e in active['content']['entries'] if e['category']=='information' for r in e['reasons'])),
        relations=len(active['content']['relations']))
    atomic_json(work/'registry.json',active['content']);atomic_json(work/'comparison.json',report)
    if not args.prepare_only:
        request.update(task='registry_write',registry=active['content'])
        atomic_json(work/'write.request.json',request)
        print('Real CPU prose generation started from the persisted registry; no review fabricated.',flush=True)
        response=run_worker(work/'write.request.json',timeout=14400);atomic_json(work/'write.response.json',response)
        result=response['result'];draft=assemble_summary(state,result);require_valid_evidence(draft,state)
        rid=service.save(sid,result['registry'],expected_id=active['id'],actor='Qwen CPU — essai réel',reason='Rédaction et omissions, sans approbation')
        draft['information_registry']={'revision_id':rid,'content_sha256':content_digest(result['registry']),
            'information_ids':list(dict.fromkeys(c['id'] for point in draft['points'] for c in point['claims']))}
        store.save_draft(sid,draft,expected_context=store.context_hash(sid));atomic_json(work/'draft.json',draft)
        report.update(status='passed',old_topics=len(baseline['points']),new_paragraphs=len(draft['points']),
            new_subjects=len(set(p['title'] for p in draft['points'])),old_source_segments=len({s for p in baseline['points'] for s in p['sources']}),
            new_source_segments=len({s for p in draft['points'] for s in p['sources']}),
            written_information=len(draft['information_registry']['information_ids']),
            new_characters=sum(len(p['summary']) for p in draft['points']),diagnostics=result['diagnostics'])
        try:store.reviewed_content(sid)
        except ValueError as error:report['production_export_without_review_blocked']='HUMAN_REVIEW' in str(error)
        else:raise AssertionError('Unexpected review on real data')
        active=service.latest(sid);atomic_json(work/'registry.json',active['content'])
except BaseException as error:
    report.update(status='failed',error=str(error),error_type=type(error).__name__)
    checkpoint=inference/'registry-checkpoint.json'
    if active and checkpoint.exists():
        try:
            partial=json.loads(checkpoint.read_text(encoding='utf-8'))
            service.save(sid,partial,expected_id=active['id'],actor='NoteTaker — essai interrompu',reason='Conservation des résultats partiels et refus')
            atomic_json(work/'registry.json',partial)
        except Exception as recovery:report['recovery_error']=str(recovery)
    raise
finally:
    report['wall_seconds']=round(time.perf_counter()-started,3)
    report['native_calls_executed_this_run']=sum(timings.get(x.name)!=x.stat().st_mtime_ns for x in inference.glob('*.timing.json'))
    report['original_snapshot_unchanged']=sha256_file(snapshot)==before
    report['copied_transcription_unchanged']=store.get(sid)['utterances']==original_rows
    report['historical_draft_preserved']=any(r['id']==old_draft['id'] for r in store.draft_history(sid))
    report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):sha256_file(p) for p in
        [ROOT/'src/notetaker/engines/registry_summary.py',ROOT/'src/notetaker/domain/information_registry.py',ROOT/'src/notetaker/services/information_registry.py']}
    atomic_json(work/'comparison.json',report);atomic_json(ROOT/'docs/evidence/information-registry-real-comparison.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'diagnostics'}},ensure_ascii=True,indent=2),flush=True)
    store.close()
