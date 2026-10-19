"""Run local inference against a frozen field snapshot. Never writes a review."""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.process import run_worker
from notetaker.services.pipeline import assemble_summary
from notetaker.services.evidence import require_valid_evidence

p=argparse.ArgumentParser()
p.add_argument('--snapshot',type=Path,required=True)
p.add_argument('--session',required=True)
p.add_argument('--work',type=Path,required=True)
p.add_argument('--length',choices=['short','standard','detailed'],default='standard')
args=p.parse_args()
work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
snapshot=args.snapshot.resolve(strict=True);before=sha256_file(snapshot)
with sqlite3.connect(snapshot.as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    state=dict(db.execute('SELECT * FROM session WHERE id=?',(args.session,)).fetchone())
    state['metadata']=json.loads(state.pop('metadata_json'))
    state['utterances']=[dict(r) for r in db.execute('SELECT * FROM utterance WHERE session_id=? ORDER BY start_ms,id',(args.session,))]
    state['speakers']={r['id']:r['label'] for r in db.execute('SELECT * FROM speaker WHERE session_id=?',(args.session,))}
    baseline=json.loads(db.execute('SELECT content_json FROM draft_minutes WHERE session_id=? ORDER BY revision DESC LIMIT 1',(args.session,)).fetchone()[0])
atomic_json(work/'state.json',state);atomic_json(work/'baseline.json',baseline)
models=ModelPaths();models.verify()
inference=work/'inference';inference.mkdir(exist_ok=True)
request={'engine':'llm','task':'summary','device':'cpu','binary':str(models.llama),'model':str(models.llm),
    'workspace':str(inference),'summary_length':args.length,'lexicon':state['metadata'].get('lexicon',[]),
    'utterances':[{k:u[k] for k in ['id','text','speaker_id','start_ms','end_ms','uncertain']} for u in state['utterances']]}
atomic_json(work/'request.json',request)
report={'scope':'same frozen field transcription; summary only; no ASR/diarization rerun; no live data edits',
    'snapshot_sha256':before,'transcription_rows':len(state['utterances']),
    'last_transcription_ms':max(u['end_ms'] for u in state['utterances']),
    'length':args.length,'human_reference_available':False,'human_fidelity_improvement_measured':None,
    'human_review_created':False,'production_export_performed':False,
    'model_sha256':sha256_file(models.llm),'binary_sha256':sha256_file(models.llama),
    'source_sha256':{name:sha256_file(ROOT/name) for name in ['src/notetaker/engines/topic_summary.py','src/notetaker/engines/hierarchical_summary.py','src/notetaker/services/pipeline.py','src/notetaker/domain/summary.py','src/notetaker/services/evidence.py','src/notetaker/schemas/minutes.json']},
    'cached_calls_at_start':len(list(inference.glob('*.identity.json')))}
timings_before={p.name:p.stat().st_mtime_ns for p in inference.glob('*.timing.json')}
started=time.perf_counter()
try:
    print('Starting real CPU topic-summary inference; private source data stays in the isolated workspace.',flush=True)
    response=run_worker(work/'request.json',timeout=10800)
    atomic_json(work/'response.json',response)
    result=response['result'];draft=assemble_summary(state,result)
    require_valid_evidence(draft,state)
    atomic_json(work/'draft.json',draft)
    report.update(status='passed',old_topics=len(baseline['points']),new_topics=len(draft['points']),
        old_characters=sum(len(p['summary']) for p in baseline['points']),new_characters=sum(len(p['summary']) for p in draft['points']),
        new_sourced_sentences=sum(len(p['narrative']) for p in draft['points']),diagnostics=result['diagnostics'])
except BaseException as error:
    report.update(status='failed',error_type=type(error).__name__,error=str(error));raise
finally:
    report['wall_seconds']=round(time.perf_counter()-started,3)
    report['native_calls_executed_this_run']=sum(timings_before.get(p.name)!=p.stat().st_mtime_ns for p in inference.glob('*.timing.json'))
    report['snapshot_unchanged']=sha256_file(snapshot)==before
    atomic_json(work/'comparison.json',report)
    atomic_json(ROOT/f'docs/evidence/topic-summary-{args.length}.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2),flush=True)
