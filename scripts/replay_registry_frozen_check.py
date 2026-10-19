"""Recheck frozen worker after UI-only fix, using strict native cache; do not save old state."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService

evidence = ROOT / 'docs/evidence'
previous = json.loads((evidence / 'information-registry-native-request-before-time-label.json').read_text(encoding='utf-8'))
bundle = ROOT / 'dist/information-registry/NoteTaker'
archives = sorted((ROOT / 'dist').glob('dev-previous-*/NoteTaker-worker.exe'), key=lambda p: p.stat().st_mtime, reverse=True)
old = next(p for p in archives if sha256_file(p) == previous['frozen_worker_sha256'])
old_modules = CArchiveReader(str(old)).open_embedded_archive('PYZ.pyz')
new_modules = CArchiveReader(str(bundle / 'NoteTaker-worker.exe')).open_embedded_archive('PYZ.pyz')
unchanged = ['notetaker.engines.registry_summary', 'notetaker.engines.topic_summary',
    'notetaker.domain.information_registry', 'notetaker.workers.probe',
    'notetaker.services.pipeline', 'notetaker.services.information_registry']
for name in unchanged:
    assert old_modules.extract(name) == new_modules.extract(name), name
work = ROOT / 'output/information-registry/field-670'
request_path = next(p for p in (work / 'data/sessions').rglob('llm-cpu.request.json')
    if json.loads(p.read_text(encoding='utf-8')).get('information_id') == previous['information_id'])
expected = json.loads(request_path.with_suffix('.result.json').read_text(encoding='utf-8'))
workspace = request_path.parent
timings = {p.name: p.stat().st_mtime_ns for p in workspace.glob('*.timing.json')}
store = SessionStore(work / 'data')
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
state_before = store.get(sid)
registry_before = RegistryService(store).latest(sid)['id']
env = dict(os.environ)
env.pop('PYTHONPATH', None)
env.pop('PYTHONHOME', None)
env['PATH'] = os.environ.get('SystemRoot', 'C:\\Windows') + '\\System32'
started = time.perf_counter()
process = subprocess.run([str(bundle / 'NoteTaker-worker.exe'), str(request_path)], cwd=workspace,
    env=env, capture_output=True, text=True, encoding='utf-8', timeout=1800,
    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
response = json.loads(process.stdout)
assert process.returncode == 0 and response['status'] == 'completed'
assert response['result'] == expected['result'] and response['python_network_attempts'] == 0
assert timings == {p.name: p.stat().st_mtime_ns for p in workspace.glob('*.timing.json')}
assert store.get(sid) == state_before and RegistryService(store).latest(sid)['id'] == registry_before
report = {**previous, 'scope': 'actual final frozen worker replay on earlier request; strict native cache; response never saved to current registry',
    'worker_execution': 'actual final frozen worker; native algorithms bytecode identical to earlier fresh check',
    'frozen_worker_sha256': sha256_file(bundle / 'NoteTaker-worker.exe'),
    'native_calls': 0, 'native_cache_hits': len(timings), 'seconds': round(time.perf_counter() - started, 3),
    'previous_fresh_native_calls': previous['native_calls'], 'previous_fresh_seconds': previous['seconds'],
    'previous_fresh_evidence': 'information-registry-native-request-before-time-label.json',
    'unchanged_frozen_algorithms': unchanged, 'current_registry_not_replaced_by_old_response': True}
atomic_json(work / 'final-frozen-replay.response.json', response)
atomic_json(evidence / 'information-registry-native-request.json', report)
store.close()
print(json.dumps(report, ensure_ascii=True, indent=2))
