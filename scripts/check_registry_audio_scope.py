"""Compare audio engine code with the preserved 0.2.3 frozen worker.

This checks code identity, not new runtime accuracy or clean-PC compatibility.
"""
import json
import sys
import types
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
baseline=ROOT/'dist/topic-summary/NoteTaker/NoteTaker-worker.exe'
archive=CArchiveReader(str(baseline)).open_embedded_archive('PYZ.pyz')

def current(name,old):
    path=ROOT/'src'/Path(name.replace('.','/')).with_suffix('.py')
    return compile(path.read_text(encoding='utf-8'),old.co_filename,'exec',dont_inherit=True,optimize=0)

name='notetaker.workers.probe';old=archive.extract(name);new=current(name,old)
definitions=lambda code:{c.co_name:c for c in code.co_consts if isinstance(c,types.CodeType)}
old_defs,new_defs=definitions(old),definitions(new)
functions={name:old_defs[name]==new_defs[name] for name in ['transcribe','diarize','diarize_sherpa']}
modules={}
for name in ['notetaker.engines.speaker_refinement','notetaker.engines.overlap','notetaker.engines.router']:
    old=archive.extract(name);modules[name]=old==current(name,old)
assert all(functions.values()) and all(modules.values())
report={'scope':'code identity versus preserved 0.2.3 worker; not a new ASR/voice quality or runtime test',
    'baseline_worker_sha256':sha256_file(baseline),'audio_functions_unchanged':functions,'audio_modules_unchanged':modules,
    'new_audio_inference_performed':False,'clean_offline_windows_validation':False}
atomic_json(ROOT/'docs/evidence/information-registry-audio-engines-unchanged.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
