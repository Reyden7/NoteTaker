"""Full 670-row frozen-worker replay using explicit, checked response caches.

This verifies packaging/protocol with zero fresh inference. The independent
cold source run supplies native performance; never label this replay cold.
"""
import argparse
import copy
import json
import os
import subprocess
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService
from notetaker.services.direct_summary import artifact_path

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
p.add_argument('--bundle', type=Path, required=True)
args = p.parse_args()
work, bundle = args.work.resolve(), args.bundle.resolve()
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
benchmark = read(work/'cold-report.json')
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
root = work/'data'
artifact = artifact_path(root, sid, benchmark['service_result']['run_id'])
original = read(artifact)
request = read(artifact.parent/'request.json')
models = ModelPaths(bundle)
models.verify()
request.update(cache_mode='resume', binary=str(models.llama), model=str(models.llm))
request_path = work/'frozen-replay.request.json'
atomic_json(request_path, request)
store = SessionStore(root)
before = store.get(sid)
registry_before = RegistryService(store).latest(sid)
reviews_before = [tuple(row) for row in store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision', (sid,))]
workspace = Path(request['workspace'])
cache_before = {str(path): sha256_file(path) for path in workspace.glob('*.result.json')}
env = dict(os.environ)
env.pop('PYTHONPATH', None)
env.pop('PYTHONHOME', None)
env['PATH'] = os.environ.get('SystemRoot', 'C:\\Windows')+'\\System32'
started = time.perf_counter()
process = subprocess.run([str(bundle/'NoteTaker-worker.exe'), str(request_path)], cwd=work,
    env=env, capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=1800,
    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
(work/'frozen-replay.stderr.txt').write_text(process.stderr, encoding='utf-8')
(work/'frozen-replay.stdout.json').write_text(process.stdout, encoding='utf-8')
response = json.loads(process.stdout)
assert process.returncode == 0 and response['status'] == 'completed', response
assert process.stdout.isascii() and response['python_network_attempts'] == 0
after_replay, expected = copy.deepcopy(response['result']), copy.deepcopy(original['result'])
after_replay['ledger'].pop('wall_seconds', None)
expected['ledger'].pop('wall_seconds', None)
assert after_replay == expected
profile = read(workspace/'direct-profile.json')
assert profile['fresh_calls'] == 0
assert profile['cached_calls'] == benchmark['profile']['fresh_calls']
assert cache_before == {str(path): sha256_file(path) for path in workspace.glob('*.result.json')}
assert store.get(sid) == before
assert RegistryService(store).latest(sid) == registry_before
assert reviews_before == [tuple(row) for row in store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision', (sid,))]
report = {'scope': 'actual frozen worker on all 670 rows, explicit strict response cache; not a cold performance run',
    'rows': len(before['utterances']), 'fresh_native_calls': 0, 'cached_calls': profile['cached_calls'],
    'cold_source_run_fresh_calls': benchmark['profile']['fresh_calls'],
    'seconds': time.perf_counter()-started, 'result_equal_except_measured_duration': True,
    'cache_results_unchanged': True, 'source_draft_registry_reviews_unchanged': True,
    'python_network_attempts': response['python_network_attempts'], 'ascii_protocol': True,
    'worker_sha256': sha256_file(bundle/'NoteTaker-worker.exe'), 'bundle': str(bundle),
    'human_review_created': False, 'quality_validated': False, 'clean_offline_windows_validation': False}
atomic_json(ROOT/'docs/evidence/direct-summary-frozen-replay.json', report)
store.close()
print(json.dumps(report, ensure_ascii=True, indent=2))
