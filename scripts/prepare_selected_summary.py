"""Lock a tested candidate for DEVELOPMENT; does not assert human acceptance."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths
from notetaker.engines.hierarchical_summary import validate_grouping

p = argparse.ArgumentParser()
p.add_argument('--result', type=Path, required=True)
args = p.parse_args()
result = json.loads(args.result.read_text(encoding='utf-8'))['result']
validate_grouping({'topics': result['topics']}, [c['id'] for c in result['claims']])
if not result['claims'] or result.get('device') != 'cpu':
    raise ValueError('COMPLETE_CPU_COMPARISON_REQUIRED')
proof_file = ROOT / 'docs/evidence/qwen-instruct-candidate.json'
proof = json.loads(proof_file.read_text(encoding='utf-8'))
model = ROOT / proof['model']
if sha256_file(model) != proof['sha256'] or ModelPaths().llm != model:
    raise ValueError('MODEL_PATH_OR_HASH_NOT_SELECTED')
request = json.loads(args.result.with_name('summary-request.json').read_text(encoding='utf-8'))
if Path(request['model']).resolve() != model.resolve():
    raise ValueError('COMPARISON_USED_ANOTHER_MODEL')
aligned = json.loads((ROOT / 'output/quality-02/aligned-transcript.json').read_text(encoding='utf-8'))
execution = json.loads(args.result.with_name('summary-execution.json').read_text(encoding='utf-8'))
if request['utterances'] != aligned['utterances'] or execution['model_sha256'] != proof['sha256']:
    raise ValueError('COMPLETE_CURRENT_TRANSCRIPT_COMPARISON_REQUIRED')
folder = model.parent
(folder / 'README-quantization.md').write_bytes((ROOT / 'docs/evidence/qwen-instruct-quantization-card.md').read_bytes())
proof['not_used_by_application_yet'] = False
proof['candidate_only'] = False
proof['development_selected_after_comparative_cpu_run'] = True
proof['human_quality_acceptance'] = False
proof['comparison_result_sha256'] = sha256_file(args.result)
atomic_json(folder / 'PROVENANCE.json', proof)
manifest_path = ROOT / 'models_manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['assets'] = [a for a in manifest['assets'] if not a['path'].startswith('models/llm/')]
for asset in [model, folder / 'LICENSE', folder / 'README.md', folder / 'README-quantization.md', folder / 'PROVENANCE.json']:
    record = {'path': asset.relative_to(ROOT).as_posix(), 'size_bytes': asset.stat().st_size,
        'sha256': sha256_file(asset), 'upstream_sha256': proof['sha256'] if asset == model else None,
        'revision': proof['revision'] if asset in [model, folder / 'README-quantization.md'] else proof['base_revision'],
        'provenance': 'https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF' if asset in [model, folder / 'README-quantization.md'] else 'https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507',
        'redistribution': 'pending-notices', 'license': 'Apache-2.0'}
    if asset.name == 'PROVENANCE.json':
        record.update({'provenance': 'generated locally from pinned upstream metadata and comparative CPU result', 'revision': None})
    manifest['assets'].append(record)
manifest['summary_model'] = {'path': proof['model'], 'template': 'qwen3-instruct-2507',
                             'development_only': True, 'human_quality_acceptance': False}
atomic_json(manifest_path, manifest)
atomic_json(proof_file, proof)
print('Development manifest prepared; no commercial or human acceptance asserted.')
