"""Inventory actual PE files/imports; this is not a redistribution clearance."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import pefile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
p = argparse.ArgumentParser()
p.add_argument('--bundle', type=Path, default=ROOT / 'dist/quality-02/NoteTaker')
p.add_argument('--report', type=Path, default=ROOT / 'docs/evidence/native-payload-quality02.json')
args = p.parse_args()
bundle = args.bundle.resolve(strict=True)
records = []
for path in sorted(bundle.rglob('*')):
    if not path.is_file() or path.suffix.casefold() not in {'.exe', '.dll', '.pyd'}:
        continue
    binary = pefile.PE(str(path), fast_load=True)
    binary.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    imports = sorted({entry.dll.decode('ascii', errors='strict') for entry in getattr(binary, 'DIRECTORY_ENTRY_IMPORT', [])})
    binary.close()
    records.append({'path': path.relative_to(bundle).as_posix(), 'size_bytes': path.stat().st_size,
                    'sha256': sha256_file(path), 'imports': imports})
report = {'scope': 'PE binary/import inventory only; not complete third-party SBOM or license clearance',
    'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'native_files': len(records),
    'forbidden_optional_files': [r['path'] for r in records if any(t in Path(r['path']).name.casefold() for t in ['virtualkeyboard', 'asio'])],
    'nvidia_runtime_files': [r['path'] for r in records if any(t in Path(r['path']).name.casefold() for t in ['cudnn', 'cublas', 'cudart', 'nvcuda'])],
    'qt_libraries': [Path(r['path']).name for r in records if Path(r['path']).name.startswith('Qt6')],
    'clean_windows_validation': False, 'commercial_clearance': False, 'files': records}
atomic_json(args.report, report)
print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=True,indent=2))
