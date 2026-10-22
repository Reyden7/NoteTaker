"""Offline inventory/staging of the tested GPU runtime. DEVELOPMENT ONLY.

Run with .venv-lab-b/Scripts/python.exe. Uses installed distribution RECORDs,
never a package index or the HF account cache. This is not legal clearance.
"""
import argparse
import hashlib
import json
import shutil
import sys
from importlib.metadata import distribution
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ['torch==2.8.0+cu128', 'pyannote.audio==4.0.7', 'faster-whisper==1.2.1',
         'ctranslate2==4.8.3', 'av==18.1.0', 'psutil']


def closure(seeds):
    selected, requested, queue = {}, {}, list(seeds)
    while queue:
        req = Requirement(queue.pop())
        key = canonicalize_name(req.name)
        dist = distribution(req.name)
        if req.specifier and not req.specifier.contains(dist.version, prereleases=True):
            raise ValueError('INSTALLED_REQUIREMENT_MISMATCH:' + str(req))
        extras = {''} | req.extras
        if key in selected and extras <= requested[key]:
            continue
        requested.setdefault(key, set()).update(extras)
        selected[key] = dist
        for value in dist.requires or []:
            child = Requirement(value)
            if child.marker is None or any(child.marker.evaluate({'extra': extra}) for extra in requested[key]):
                queue.append(value)
    if 'whisperx' in selected:
        raise ValueError('UNEXPECTED_WHISPERX_DEPENDENCY')
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path, help='New directory for inventory and optional runtime')
    parser.add_argument('--stage-development', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('STAGING_MUST_STAY_IN_WORKSPACE')
    output.mkdir(parents=True, exist_ok=False)
    selected = closure(SEEDS)
    site = Path(distribution('torch').locate_file('')).resolve()
    sources = {}
    for dist in selected.values():
        for file in dist.files or []:
            if '__pycache__' in file.parts or file.suffix == '.pyc':
                continue
            source = Path(dist.locate_file(file)).resolve()
            if source.is_relative_to(site) and source.is_file():
                sources['Lib/site-packages/' + source.relative_to(site).as_posix()] = source
    base = Path(sys.base_prefix)
    for name in ['python.exe', 'python3.dll', 'python311.dll', 'vcruntime140.dll', 'vcruntime140_1.dll', 'LICENSE.txt']:
        sources[name] = base / name
    for directory in ['Lib', 'DLLs']:
        for source in (base / directory).rglob('*'):
            if source.is_file() and '__pycache__' not in source.parts and 'site-packages' not in source.parts:
                sources[source.relative_to(base).as_posix()] = source
    # Only the GPU worker and its small infrastructure, never the lab package,
    # summary engines, HF login files, test recordings, or annotation database.
    for name in ['__init__.py', 'workers/__init__.py', 'workers/gpu_audio.py',
                 'infrastructure/__init__.py', 'infrastructure/atomic.py', 'infrastructure/offline.py']:
        sources['app/notetaker/' + name] = ROOT / 'src/notetaker' / name
    runtime = output / 'audio-gpu'
    records = []
    for name, source in sorted(sources.items()):
        with source.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        records.append({'path': name, 'size_bytes': source.stat().st_size, 'sha256': digest})
        if args.stage_development:
            target = runtime / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    inventory = {'development_only': True, 'commercial_redistribution_approved': False,
        'source_python': sys.version, 'python_base': str(base), 'whisperx_included': False,
        'model_payload': 'gpu_audio_manifest.json, copied separately by the installer builder',
        'distributions': [{'name': key, 'version': dist.version,
            'license_metadata': dist.metadata.get('License-Expression') or dist.metadata.get('License'),
            'license_files': dist.metadata.get_all('License-File') or []} for key, dist in sorted(selected.items())],
        'files': records, 'payload_bytes': sum(r['size_bytes'] for r in records)}
    (output/'inventory.json').write_text(json.dumps(inventory, ensure_ascii=True, indent=2), encoding='utf-8')
    (output/'requirements-installed.txt').write_text('\n'.join(key+'=='+dist.version for key,dist in sorted(selected.items()))+'\n',encoding='utf-8')
    print(json.dumps({'distributions':len(selected),'files':len(records),
                      'bytes':inventory['payload_bytes'],'staged':args.stage_development}))


if __name__ == '__main__':
    main()
