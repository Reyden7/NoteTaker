"""Space-saving development bundle, verified against current PyInstaller analysis.

Only identical immutable payload bytes are shared. Existing bundles are never
edited. New code/resources are copied from this build's analysis, not guessed
from the previous executable. This does not qualify a commercial installer.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker import __version__

p = argparse.ArgumentParser()
p.add_argument('--source-bundle', type=Path, required=True)
p.add_argument('--target', type=Path, required=True)
p.add_argument('--benchmark-note', default='development PC; consult native benchmark intervals separately')
args = p.parse_args()
started_at = datetime.now(timezone.utc).isoformat()
source, target = args.source_bundle.resolve(), args.target.resolve()
if not source.is_relative_to(ROOT/'dist') or not target.is_relative_to(ROOT/'dist') or source == target:
    raise ValueError('Development bundles must be distinct directories inside dist')
if target.exists() or not (source/'NoteTaker.exe').is_file():
    raise ValueError('Target must be new; source must be an existing development bundle')
if shutil.disk_usage(ROOT).free < 160*1024**2:
    raise OSError('At least 160 MiB are needed for development executables and temporary files')
before = {name: sha256_file(source/name) for name in ('NoteTaker.exe', 'NoteTaker-worker.exe')}
env = dict(os.environ)
env['PYTHONPATH'] = str(ROOT/'src')
env['NOTETAKER_DEV_EXECUTABLES_ONLY'] = '1'
base = ROOT/'.cache'/('shared-dev-tests-'+uuid.uuid4().hex)
subprocess.run([sys.executable, '-m', 'pytest', '-q', '--basetemp', str(base),
    '--junitxml', str(ROOT/'docs/evidence/pytest-direct-summary.xml')], cwd=ROOT, env=env, check=True)
with (ROOT/'build-pyinstaller.log').open('w', encoding='utf-8') as out, (ROOT/'build-pyinstaller-stderr.log').open('w', encoding='utf-8') as err:
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', 'packaging/notetaker.spec'],
        cwd=ROOT, env=env, stdout=out, stderr=err, check=True,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
payload = json.loads((ROOT/'build/notetaker/development-payload.json').read_text(encoding='utf-8'))
target.mkdir(parents=True, exist_ok=False)
counts = {'linked_files': 0, 'linked_bytes': 0, 'copied_files': 0, 'copied_bytes': 0}
for relative, original, kind in payload:
    if kind not in ('DATA', 'BINARY', 'EXTENSION'):
        raise ValueError('Unsupported payload type: '+kind)
    path = (target/'_internal'/relative).resolve()
    if not path.is_relative_to(target):
        raise ValueError('Payload path escapes the new bundle')
    current = Path(original).resolve(strict=True)
    old = source/'_internal'/relative
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(current)
    if old.is_file() and old.stat().st_size == current.stat().st_size and sha256_file(old) == digest:
        os.link(old, path)
        counts['linked_files'] += 1
        counts['linked_bytes'] += current.stat().st_size
    else:
        shutil.copy2(current, path)
        counts['copied_files'] += 1
        counts['copied_bytes'] += current.stat().st_size
    if sha256_file(path) != digest:
        raise ValueError('Payload hash mismatch: '+relative)
for name in ('NoteTaker.exe', 'NoteTaker-worker.exe'):
    shutil.copy2(ROOT/'build/notetaker'/name, target/name)
shutil.copytree(ROOT/'third_party', target/'third_party')
for original, name in [('LICENSES-THIRD-PARTY.md', 'LICENSES-THIRD-PARTY.md'),
    ('docs/operator-guide.md', 'GUIDE-UTILISATEUR.md'), ('docs/field-test.md', 'RECETTE-TERRAIN.md'),
    ('docs/registry-workflow-fix.md', 'registry-workflow-fix.md'),
    ('docs/information-registry-0.2.4.md', 'REGISTRE-INFORMATIONS.md'),
    ('docs/direct-summary-0.2.5.md', 'LABORATOIRE-SYNTHESE.md'),
    ('docs/direct-summary-human-evaluation.md', 'direct-summary-human-evaluation.md')]:
    shutil.copy2(ROOT/original, target/name)
assert before == {name: sha256_file(source/name) for name in before}
status = {'development_only': True, 'models_included': False, 'version': __version__,
    'qualification': 'QUALITY UNDER EVALUATION; NOT VALIDATED ON CLEAN OFFLINE WINDOWS',
    'asset_storage': 'verified immutable payload NTFS hardlinks; development only',
    'source_bundle_preserved': True, **counts}
status.update(started_at=started_at, finished_at=datetime.now(timezone.utc).isoformat(),
              benchmark_host_activity=args.benchmark_note)
atomic_json(target/'BUILD-STATUS.json', status)
atomic_json(ROOT/'docs/evidence/direct-summary-shared-build.json', status)
print(json.dumps(status, ensure_ascii=True), flush=True)
