"""Exercise one actual on-request CPU check, with no human approval created."""
import json
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService
from notetaker.services.pipeline import Pipeline
from notetaker.domain.information_registry import evidence_issues,source_fingerprint
from notetaker.infrastructure.paths import ModelPaths

parser=argparse.ArgumentParser();parser.add_argument('--bundle',type=Path);args=parser.parse_args()
bundle=args.bundle.resolve(strict=True) if args.bundle else None

work=ROOT/'output/information-registry/field-670';store=SessionStore(work/'data')
sid='0ce77b44-c8a0-482f-be0d-ef5a68b80aa2';service=RegistryService(store)
record=service.latest(sid)
if not record or record['stale'] or record['content']['processing']['status']!='ready_for_review':raise ValueError('REGISTRY_EXTRACTION_INCOMPLETE')
state=store.get(sid);before=source_fingerprint(state)
reviews=[tuple(r) for r in store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision',(sid,))]
observations=json.loads((ROOT/'docs/evidence/information-registry-agent-observations.json').read_text(encoding='utf-8'))
flagged=[]
for observation in observations['observations']:
    active=service.latest(sid);entry=next((e for e in active['content']['entries'] if e['id']==observation['entry_id']),None)
    if not entry or entry.get('human_lock') or entry['content']!=observation['content']:continue
    reason=('Généralisation d’un récit personnel vers des observateurs non cités.' if 'Generalisation' in observation['reason'] else
        'Métatexte sur un fragment incomplet ; aucune information substantielle établie.')
    service.change(sid,active['id'],entry['id'],'reopen',actor='Audit de développement automatisé — non humain',
        reason=reason+' Doute signalé ; aucune validation humaine créée.')
    flagged.append(entry['id'])
active=service.latest(sid)
candidates=[e for e in active['content']['entries'] if e['category']=='information' and not e.get('human_lock')
    and e['human_status']=='pending' and e['verification']!='supported' and not e.get('normalized_variant_id')
    and e['speaker'] in state['speakers'] and not evidence_issues(e,state)
    and 30<=len(' '.join(r['quote'] for r in e['evidence']))<=500]
if not candidates:raise ValueError('NO_PENDING_REGISTRY_INFORMATION')
candidates.sort(key=lambda e:(e['author_status']!='confirmed',e['type']!='question',-min(r['start_ms'] for r in e['evidence'])))
chosen=candidates[0];old_jobs={r['id'] for r in store.jobs(sid)};started=time.perf_counter()
report={'scope':'actual new Pipeline.verify_information CPU worker; same source rows; no human approval',
    'information_id':chosen['id'],'before_verification':chosen['verification'],'flagged_development_observations':flagged,
    'human_reference_available':False,'human_review_created':False,'status':'running'}
if bundle:
    report.update(worker_execution='actual frozen worker; source service matched separately to frozen code',
        frozen_worker_sha256=sha256_file(bundle/'NoteTaker-worker.exe'),
        environment='developer PC; Python paths removed, PATH=System32; host not disconnected, not clean Windows')
try:
    print('Starting one real local CPU information check; original source and human choices remain protected.',flush=True)
    pipeline=Pipeline(store.root,models=ModelPaths(bundle) if bundle else None,progress=lambda message:print(message,flush=True))
    if bundle:
        def frozen_worker(workspace,request,timeout=1800):
            path=workspace/'llm-cpu.request.json';atomic_json(path,request)
            env=dict(os.environ);env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
            env['PATH']=os.environ.get('SystemRoot','C:\\Windows')+'\\System32';env['PYTHONIOENCODING']='utf-8'
            result=subprocess.run([str(bundle/'NoteTaker-worker.exe'),str(path)],cwd=workspace,env=env,
                capture_output=True,text=True,encoding='utf-8',errors='strict',timeout=timeout,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (workspace/'frozen-worker.stderr.txt').write_text(result.stderr,encoding='utf-8')
            response=json.loads(result.stdout);atomic_json(path.with_suffix('.result.json'),response)
            if result.returncode or response.get('status')!='completed':raise RuntimeError(response.get('error_code','FROZEN_WORKER_FAILED'))
            return response['result']
        pipeline._run=frozen_worker
    result=pipeline.verify_information(sid,chosen['id'])
    latest=service.latest(sid);focus=next(e for e in latest['content']['entries'] if e['id']==result['focus_id'])
    report.update(status='passed',focus_id=focus['id'],after_verification=focus['verification'],checks=focus['checks'],
        original_information_retained=any(e['id']==chosen['id'] for e in latest['content']['entries']))
    jobs=[j for j in store.jobs(sid) if j['id'] not in old_jobs];assert len(jobs)==1
    folder=store.root/'sessions'/sid/'jobs'/jobs[0]['id']
    response=json.loads((folder/'llm-cpu.request.result.json').read_text(encoding='utf-8'))
    assert response['python_network_attempts']==0
    report.update(native_calls=len(list(folder.glob('*.timing.json'))),python_network_attempts=0,job_status=jobs[0]['status'])
except BaseException as error:
    report.update(status='failed',error=str(error));raise
finally:
    report['seconds']=round(time.perf_counter()-started,3)
    report['source_rows_unchanged']=source_fingerprint(store.get(sid))==before
    report['historical_reviews_unchanged']=reviews==[tuple(r) for r in store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision',(sid,))]
    report['source_rows']=len(store.get(sid)['utterances'])
    atomic_json(work/'on-request-report.json',report);atomic_json(ROOT/'docs/evidence/information-registry-native-request.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2),flush=True);store.close()
