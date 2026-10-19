"""Compare preserved 0.2.4 bytecode with sources for engines outside this task."""
import json
import sys
import types
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file

baseline = ROOT/'dist/information-registry/NoteTaker/NoteTaker-worker.exe'
archive = CArchiveReader(str(baseline)).open_embedded_archive('PYZ.pyz')

def source_code(name, old):
    path = ROOT/'src'/Path(name.replace('.', '/')).with_suffix('.py')
    return compile(path.read_text(encoding='utf-8'), old.co_filename, 'exec', dont_inherit=True, optimize=0)

unchanged = {}
for name in ('notetaker.engines.registry_summary', 'notetaker.engines.topic_summary',
             'notetaker.engines.hierarchical_summary', 'notetaker.domain.information_registry',
             'notetaker.services.information_registry', 'notetaker.engines.speaker_refinement',
             'notetaker.engines.overlap', 'notetaker.engines.router'):
    old = archive.extract(name)
    unchanged[name] = source_code(name, old) == old
old = archive.extract('notetaker.workers.probe')
new = source_code('notetaker.workers.probe', old)
definitions = lambda code: {c.co_name: c for c in code.co_consts if isinstance(c, types.CodeType)}
functions = {name: definitions(old)[name] == definitions(new)[name]
             for name in ('transcribe', 'diarize', 'diarize_sherpa')}
assert all(unchanged.values()) and all(functions.values())
report = {'scope': 'bytecode identity against preserved 0.2.4; no new ASR/diarization inference',
          'baseline_worker_sha256': sha256_file(baseline), 'unchanged_modules': unchanged,
          'unchanged_audio_functions': functions, 'clean_offline_windows_validation': False}
atomic_json(ROOT/'docs/evidence/direct-summary-preserved-engines.json', report)
print(json.dumps(report, ensure_ascii=True, indent=2))
