"""Real first field block through the candidate chain; reuses identical extraction."""
import json
import argparse
import shutil
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.engines.hierarchical_summary import source_units, coherent_blocks
from notetaker.infrastructure.atomic import atomic_json
from notetaker.infrastructure.process import run_worker
from notetaker.infrastructure.paths import ModelPaths
parser = argparse.ArgumentParser()
parser.add_argument('--label', choices=['instruct-first-block', 'instruct-first-block-word-fix'], default='instruct-first-block')
args = parser.parse_args()
work = ROOT / 'output/quality-02'
rows = json.loads((work / 'aligned-transcript.json').read_text(encoding='utf-8'))['utterances']
units = source_units(rows)
first = next(coherent_blocks(units))
unit_ids = {u['id'] for u in first}
ids = {span['id'] for u in units if u['id'] in unit_ids for span in u['source_spans']}
directory = work / args.label
directory.mkdir(exist_ok=True)
for p in (work / 'instruct-2507/summary').glob('block-000.*'):
    if not (directory / p.name).exists():
        shutil.copy2(p, directory / p.name)
models = ModelPaths()
request = {'engine': 'llm', 'task': 'summary', 'device': 'cpu', 'binary': str(models.llama),
    'model': str(ROOT / 'models/llm/qwen3-4b-instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf'),
    'workspace': str(directory), 'utterances': [u for u in rows if u['id'] in ids]}
atomic_json(directory / 'request.json', request)
started = time.perf_counter()
result = run_worker(directory / 'request.json', timeout=900)
atomic_json(directory / 'result.json', result)
print(json.dumps({'wall_seconds':round(time.perf_counter()-started,3),'result':result['result']},ensure_ascii=True,indent=2))
