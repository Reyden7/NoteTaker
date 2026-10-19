"""Test harness: disjoint real CPU extraction, then one complete global plan.

This is process parallelism, not an alternate model or simulated result.
Every worker request carries the full source snapshot for validation/merging.
Native extraction prompts receive six bounded turns; production remains serial.
"""
import copy
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker.infrastructure.process import run_worker
from notetaker.infrastructure.paths import ModelPaths
from notetaker.domain.information_registry import stable_id,validate_registry,coverage
from notetaker.engines.hierarchical_summary import source_units
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService

work=ROOT/'output/information-registry/field-670';store=SessionStore(work/'data')
sid='0ce77b44-c8a0-482f-be0d-ef5a68b80aa2';service=RegistryService(store)
active=service.latest(sid);state=store.get(sid);models=ModelPaths();models.verify()
units=source_units(state['utterances']);count=(len(units)+5)//6
partitions=[list(range(0,10)),list(range(10,20)),list(range(20,count))]
assert sorted(i for part in partitions for i in part)==list(range(count))
base=copy.deepcopy(active['content']);source_owner={s['id']:i//6 for i,u in enumerate(units) for s in u['source_spans']}
unit_owner={stable_id(sid,'unit',[s['id'] for s in u['source_spans']]):i//6 for i,u in enumerate(units)}
started=time.perf_counter();initial_hash=sha256_file(ROOT/'src/notetaker/engines/registry_summary.py')
report={'scope':'test-only parallel real CPU extraction; full source context in each job',
    'status':'running','source_rows':len(state['utterances']),'units':len(units),'batches':count,
    'partitions':partitions,'source_code_sha256_at_start':initial_hash,'production_parallelism_enabled':False,
    'verification_policy':'on_request; provisional candidates never become eligible without verification or explicit information approval'}
atomic_json(work/'parallel-report.json',report)

def run_part(index,indices):
    folder=work/f'part-{index}';folder.mkdir(exist_ok=True);inference=folder/'inference';inference.mkdir(exist_ok=True)
    if index==0:
        for path in (work/'inference').glob('registry-extract-*'):
            if path.is_file() and not (inference/path.name).exists():shutil.copy2(path,inference/path.name)
    document=base
    checkpoint=inference/'registry-checkpoint.json'
    if checkpoint.exists():
        resumed=json.loads(checkpoint.read_text(encoding='utf-8'))
        if resumed['source_sha256']!=base['source_sha256']:raise ValueError('REGISTRY_STALE')
        document=resumed
    request={'engine':'llm','task':'registry_extract','device':'cpu','binary':str(models.llama),'model':str(models.llm),
        'workspace':str(inference),'registry':document,'utterances':state['utterances'],
        'lexicon':state['metadata'].get('lexicon',[]),'registry_batch_indices':indices,'verification_policy':'on_request'}
    timings={p.name:p.stat().st_mtime_ns for p in inference.glob('*.timing.json')}
    atomic_json(folder/'request.json',request);start=time.perf_counter()
    result=run_worker(folder/'request.json',timeout=14400)
    atomic_json(folder/'response.json',result)
    doc=result['result']['registry'];validate_registry(doc)
    expected={uid for uid,batch in unit_owner.items() if batch in indices}
    if not expected<=set(doc['processing'].get('inspected_units',[])):raise ValueError('REGISTRY_EXTRACTION_INCOMPLETE')
    part_report={'part':index,'seconds':round(time.perf_counter()-start,3),'completed_units':len(expected),
        'new_native_calls':sum(timings.get(p.name)!=p.stat().st_mtime_ns for p in inference.glob('*.timing.json'))}
    atomic_json(folder/'part-report.json',part_report);print(json.dumps(part_report),flush=True)
    return index,doc,part_report

try:
    docs={};stats=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run_part,i,part) for i,part in enumerate(partitions)]
        for future in as_completed(futures):
            index,doc,part_report=future.result();docs[index]=doc;stats.append(part_report)
    merged=copy.deepcopy(base);chosen={}
    for part,doc in docs.items():
        assert doc['sources']==base['sources'] and doc['speakers']==base['speakers']
        for e in doc['entries']:
            if e['category']=='source':owner=source_owner.get(e['evidence'][0]['id'])
            else:
                label=e.get('origin',{}).get('batch','')
                owner=int(label.split('-')[2]) if label.startswith('registry-extract-') else None
            if e['id'] not in chosen or owner in partitions[part]:chosen[e['id']]=e
    merged['entries']=list(chosen.values());merged['processing']['inspected_units']=sorted({u for d in docs.values() for u in d['processing']['inspected_units']})
    assert set(merged['processing']['inspected_units'])==set(unit_owner)
    assert {e['id'] for d in docs.values() for e in d['entries']}==set(chosen)
    merged['processing'].update(status='extracted',parallel_test_parts=stats,total_units=len(units))
    validate_registry(merged);atomic_json(work/'merged-extraction.json',merged)
    service.save(sid,merged,expected_id=active['id'],actor='Qwen CPU — lots de test réunis',reason='Tous les lots extraits ; aucune information perdue à la réunion')
    active=service.latest(sid);report.update(status='extracted',parts=stats,coverage=coverage(merged))
    atomic_json(work/'parallel-report.json',report)
    folder=work/'finalize';folder.mkdir(exist_ok=True)
    request={'engine':'llm','task':'registry_finalize','device':'cpu','binary':str(models.llama),'model':str(models.llm),
        'workspace':str(folder),'registry':merged,'utterances':state['utterances'],'lexicon':state['metadata'].get('lexicon',[])}
    atomic_json(folder/'request.json',request);print('All extraction units merged; starting one global topic/relation plan.',flush=True)
    result=run_worker(folder/'request.json',timeout=14400);atomic_json(folder/'response.json',result)
    service.save(sid,result['result']['registry'],expected_id=active['id'],actor='Qwen CPU — plan global de test',reason='Plan global terminé ; vérification humaine requise')
    atomic_json(work/'registry.json',result['result']['registry']);report.update(status='prepared',coverage=coverage(result['result']['registry']))
except BaseException as error:
    report.update(status='failed',error=str(error));raise
finally:
    report['wall_seconds']=round(time.perf_counter()-started,3)
    report['source_code_unchanged_during_run']=sha256_file(ROOT/'src/notetaker/engines/registry_summary.py')==initial_hash
    atomic_json(work/'parallel-report.json',report);atomic_json(ROOT/'docs/evidence/information-registry-parallel.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2),flush=True);store.close()
