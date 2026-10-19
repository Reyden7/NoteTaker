"""Match both executables/resources to tested sources; no quality claim."""
import argparse
import json
import sys
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths
from notetaker import __version__

p = argparse.ArgumentParser()
p.add_argument('--bundle', type=Path, default=ROOT/'dist/direct-summary-final/NoteTaker')
bundle = p.parse_args().bundle.resolve(strict=True)
modules = ['notetaker', 'notetaker.main', 'notetaker.engines.direct_summary',
    'notetaker.engines.direct_runtime', 'notetaker.domain.direct_summary',
    'notetaker.services.direct_summary', 'notetaker.services.storage', 'notetaker.services.evidence',
    'notetaker.ui.direct_summary', 'notetaker.ui.window', 'notetaker.infrastructure.atomic',
    'notetaker.infrastructure.cpu_profile', 'notetaker.infrastructure.windows_job',
    'notetaker.infrastructure.process', 'notetaker.workers.probe',
    'notetaker.engines.registry_summary', 'notetaker.engines.topic_summary']
for name in ('NoteTaker.exe', 'NoteTaker-worker.exe'):
    archive = CArchiveReader(str(bundle/name)).open_embedded_archive('PYZ.pyz')
    for module in modules:
        compiled = archive.extract(module)
        source = ROOT/'src'/Path(module.replace('.', '/')).with_suffix('.py')
        if module == 'notetaker':
            source = ROOT/'src/notetaker/__init__.py'
        assert compiled == compile(source.read_text(encoding='utf-8'), compiled.co_filename,
                                   'exec', dont_inherit=True, optimize=0), (name, module)
assert sha256_file(ROOT/'src/notetaker/schemas/minutes.json') == sha256_file(
    bundle/'_internal/notetaker/schemas/minutes.json')
ModelPaths(bundle).verify()
status = json.loads((bundle/'BUILD-STATUS.json').read_text(encoding='utf-8-sig'))
assert status['version'] == __version__ and status['models_included'] and status['development_only']
report = {'version': __version__, 'bundle': str(bundle), 'both_executables_match_tested_sources': modules,
    'executables_sha256': {name: sha256_file(bundle/name) for name in ('NoteTaker.exe', 'NoteTaker-worker.exe')},
    'new_schema_matches': True, 'all_manifest_model_hashes_checked': True,
    'payload_shared_only_after_exact_hash_match': True, 'clean_offline_windows_validation': False,
    'quality_validated': False, 'commercial_validation': False}
atomic_json(ROOT/'docs/evidence/direct-summary-bundle-sources.json', report)
print(json.dumps(report, ensure_ascii=True, indent=2))
