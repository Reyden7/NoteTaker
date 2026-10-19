"""Real CPU experiment on an isolated backup of the existing 0.2.4 field data."""
import argparse
import copy
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.offline import OFFLINE_ENV
from notetaker.infrastructure.windows_job import start_process
from notetaker.infrastructure.cpu_profile import job_cpu
from notetaker.domain.direct_summary import MARKER, fingerprint
from notetaker.services.storage import SessionStore
from notetaker.services.direct_summary import DirectSummaryService, artifact_path
from notetaker.services.information_registry import RegistryService
from notetaker.domain.minutes import content_digest

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
args = p.parse_args()
work = args.work.resolve()
work.mkdir(parents=True, exist_ok=False)
source = ROOT/'output/direct-summary/input-024.sqlite3'
snapshot = ROOT/'output/summary-paragraphs/38a6b4c9d8704b669d4acd8a49c2ff8e/snapshot.sqlite3'
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
before = sha256_file(source)
data = work/'data'
data.mkdir()
with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True) as src, sqlite3.connect(data/'notetaker.sqlite3') as dest:
    src.backup(dest)
atomic_json(data/MARKER, {'id': str(uuid.uuid4()), 'purpose': 'direct-summary-test'})
store = SessionStore(data)
state = store.get(sid)
original_rows = copy.deepcopy(state['utterances'])
original_registry = copy.deepcopy(RegistryService(store).latest(sid))
original_history = store.draft_history(sid)
legacy_request = json.loads((ROOT/'output/information-registry/field-670/write.request.json').read_text(encoding='utf-8'))
assert original_rows == legacy_request['utterances'], 'The comparison must use exactly the same 670 rows'
assert state['speakers'] == legacy_request['registry']['speakers'], 'Speaker labels must also be identical'
assert state['metadata'].get('lexicon', []) == legacy_request.get('lexicon', []), 'Lexicons must match'
report = {'status': 'running', 'input_rows': len(original_rows), 'input_sha256': fingerprint(state),
          'source_db_sha256': before, 'snapshot_sha256': sha256_file(snapshot),
          'scope': 'complete direct pipeline, fresh responses; native CPU; same 670 rows; no approval',
          'human_reference_available': False, 'human_reference_preparation': '12 excerpts ready for user annotation',
          'quality_scores': None, 'cold_scope': 'empty application response cache; OS file cache not flushed'}
implementation = [ROOT/'src/notetaker'/relative for relative in (
    'engines/direct_summary.py', 'engines/direct_runtime.py', 'domain/direct_summary.py',
    'services/direct_summary.py', 'services/evidence.py', 'infrastructure/atomic.py', 'schemas/minutes.json')]
report['implementation_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in implementation}
atomic_json(work/'report.json', report)


class ProfiledService(DirectSummaryService):
    profile_prefix = ''
    def run(self, path):
        env = dict(os.environ)
        env.update(OFFLINE_ENV)
        env['PYTHONPATH'] = str(ROOT/'src')
        env['PYTHONIOENCODING'] = 'utf-8'
        started = time.perf_counter()
        with (path.parent/'worker.stdout.json').open('wb') as out, (path.parent/'worker.stderr.txt').open('wb') as err:
            process, job = start_process([sys.executable, '-m', 'notetaker.workers.probe', str(path)],
                stdout=out, stderr=err, env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                while process.poll() is None:
                    report[self.profile_prefix+'worker_wall_seconds'] = time.perf_counter()-started
                    report[self.profile_prefix+'worker_cpu'] = job_cpu(job)
                    atomic_json(work/'report.json', report)
                    time.sleep(2)
                report[self.profile_prefix+'worker_wall_seconds'] = time.perf_counter()-started
                report[self.profile_prefix+'worker_cpu'] = job_cpu(job)
                response = json.loads((path.parent/'worker.stdout.json').read_text(encoding='utf-8'))
                if process.returncode:
                    raise RuntimeError(response.get('error_code', 'NATIVE_WORKER_FAILED'))
                report[self.profile_prefix+'python_network_attempts'] = response['python_network_attempts']
                assert response['python_network_attempts'] == 0
                return response
            finally:
                job.close()


started = time.perf_counter()
try:
    service = ProfiledService(data, enabled=True, progress=lambda s: print(s, flush=True))
    result = service.generate(sid)
    artifact = artifact_path(data, sid, result['run_id'])
    record = json.loads(artifact.read_text(encoding='utf-8'))
    profile = record['profile']
    ledger = record['result']['ledger']
    report.update(status='completed', service_result=result, wall_seconds=time.perf_counter()-started,
        profile=profile, paragraphs=len(record['result']['topics']), operator_alerts=len(ledger['alerts']),
        candidates=len(ledger['candidates']), rejected=sum(c['status'] == 'rejected' for c in ledger['candidates']),
        rejection_events=len(ledger['rejected']),
        sources_not_cited=sum(not r['written_ids'] for r in ledger['inventory']),
        inventory_rows=len(ledger['inventory']))
    try:
        store.reviewed_content(sid)
    except ValueError as error:
        report['export_without_new_human_review_blocked'] = 'HUMAN_REVIEW' in str(error)
    else:
        raise AssertionError('Unexpected human review')
    atomic_json(work/'cold-report.json', report)
    # Distinct replay: caches reuse exact intermediate prose, never counted as fresh inference.
    request_path = artifact.parent/'request.json'
    request = json.loads(request_path.read_text(encoding='utf-8'))
    request['cache_mode'] = 'resume'
    warm = artifact.parent/'resume.request.json'
    atomic_json(warm, request)
    service.profile_prefix = 'resume_'
    resumed = service.run(warm)
    atomic_json(work/'resume-response.json', resumed)
    warm_profile = json.loads((Path(request['workspace'])/'direct-profile.json').read_text(encoding='utf-8'))
    atomic_json(work/'resume-profile.json', warm_profile)
    before_replay, after_replay = copy.deepcopy(record['result']), copy.deepcopy(resumed['result'])
    before_replay['ledger'].pop('wall_seconds', None)
    after_replay['ledger'].pop('wall_seconds', None)
    report['resume'] = {'fresh_calls': warm_profile['fresh_calls'], 'cached_calls': warm_profile['cached_calls'],
                        'elapsed_seconds': resumed['elapsed_seconds'],
                        'result_equal_except_measured_duration': after_replay == before_replay}
except BaseException as error:
    report.update(status='failed', error=str(error), error_type=type(error).__name__)
    raise
finally:
    report['source_db_unchanged'] = sha256_file(source) == before
    report['copied_rows_unchanged'] = store.get(sid)['utterances'] == original_rows
    report['registry_unchanged'] = RegistryService(store).latest(sid) == original_registry
    report['draft_history_preserved'] = {r['id'] for r in original_history} <= {r['id'] for r in store.draft_history(sid)}
    report['implementation_unchanged_during_run'] = report['implementation_sha256'] == {
        str(path.relative_to(ROOT)): sha256_file(path) for path in implementation}
    atomic_json(work/'report.json', report)
    store.close()
    print(json.dumps({k:v for k,v in report.items() if k not in ('profile',)}, ensure_ascii=True), flush=True)
