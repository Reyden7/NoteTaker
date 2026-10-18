"""Explicit build-only acquisition for a comparative CPU study, not app startup."""
import json
import urllib.request
from pathlib import Path
from acquire_phase0 import download, ROOT

REPO = 'unsloth/Qwen3-4B-Instruct-2507-GGUF'
REVISION = 'a06e946bb6b655725eafa393f4a9745d460374c9'
NAME = 'Qwen3-4B-Instruct-2507-Q4_K_M.gguf'
EXPECTED = '3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597'
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'NoteTaker-build-quality-study'}), timeout=60) as r:
        return r.read()
meta = json.loads(get(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true'))
asset = next(a for a in meta['siblings'] if a['rfilename'] == NAME)
if meta['sha'] != REVISION or meta.get('cardData', {}).get('license') != 'apache-2.0' or asset['lfs']['sha256'] != EXPECTED:
    raise ValueError('UNEXPECTED_CANDIDATE_PROVENANCE')
evidence = ROOT / 'docs/evidence'
(evidence / 'qwen-instruct-upstream.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
(evidence / 'qwen-instruct-quantization-card.md').write_bytes(get(f'https://huggingface.co/{REPO}/raw/{REVISION}/README.md'))
folder = ROOT / 'models/llm/qwen3-4b-instruct-2507'
folder.mkdir(parents=True, exist_ok=True)
download(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{NAME}', folder / NAME, EXPECTED)
base = json.loads(get('https://huggingface.co/api/models/Qwen/Qwen3-4B-Instruct-2507'))
base_rev = base['sha']
if base.get('cardData', {}).get('license') != 'apache-2.0':
    raise ValueError('UNEXPECTED_BASE_LICENSE')
for name in ['LICENSE', 'README.md']:
    (folder / name).write_bytes(get(f'https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/{base_rev}/{name}'))
proof = {'candidate_only': True, 'model': (folder / NAME).relative_to(ROOT).as_posix(), 'sha256': EXPECTED,
         'size_bytes': (folder / NAME).stat().st_size, 'revision': REVISION, 'quantization_by': 'Unsloth',
         'base_model': 'Qwen/Qwen3-4B-Instruct-2507', 'base_revision': base_rev, 'license': 'Apache-2.0',
         'redistribution': 'pending-notices', 'not_used_by_application_yet': True}
(evidence / 'qwen-instruct-candidate.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
print(json.dumps(proof, ensure_ascii=True))
