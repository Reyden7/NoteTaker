"""Validate the revised synthesis on the first actual block, without approval."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.engines.hierarchical_summary import coherent_blocks
from notetaker.infrastructure.atomic import atomic_json
from notetaker.infrastructure.process import run_worker

work = ROOT / 'output/quality-02'
request = json.loads((work / 'summary-request.json').read_text(encoding='utf-8'))
first = next(coherent_blocks(request['utterances']))
ids = {u['id'] for u in first}
request['utterances'] = [u for u in request['utterances'] if u['id'] in ids]
workspace = work / 'paraphrase-probe'
workspace.mkdir(exist_ok=True)
request['workspace'] = str(workspace)
path = workspace / 'request.json'
atomic_json(path, request)
response = run_worker(path, timeout=1200)
atomic_json(workspace / 'response.json', response)
print(json.dumps(response['result']['diagnostics']))
