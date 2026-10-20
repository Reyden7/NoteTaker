"""Real catalogue/assignment inferences, never a full pipeline or quality score."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.engines.direct_summary import group_candidates, GROUPING_CONTRACT
from notetaker.engines.direct_runtime import DirectRuntime
from notetaker.domain.direct_summary import plan_from_catalogue
from notetaker.infrastructure.atomic import atomic_json, sha256_file

p = argparse.ArgumentParser()
p.add_argument('--source-work', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
args = p.parse_args()
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
source, work = args.source_work.resolve(), args.work.resolve()
assert source.is_relative_to(ROOT/'output') and work.is_relative_to(ROOT/'output')
cold = read(source/'cold-report.json')
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
directory = source/'data/sessions'/sid/'direct-experiments'/cold['service_result']['run_id']
artifact_sha = sha256_file(directory/'result.json')
prompt = (directory/'inference/group-000.prompt.txt').read_text(encoding='utf-8')
payload = json.loads(prompt.split('<|im_start|>user\n', 1)[1].rsplit('\n<|im_end|>\n<|im_start|>assistant\n', 1)[0])
request = read(directory/'request.json')
work.mkdir(parents=True, exist_ok=False)
request.update(workspace=str(work), cache_mode='cold')
runtime = DirectRuntime(request)
raw = group_candidates(runtime, payload['agenda'], payload['phrases'])
try:
    plan = plan_from_catalogue(raw, [row['id'] for row in payload['phrases']])
except ValueError as error:
    atomic_json(work/'probe.json', {'status': 'refused', 'error': str(error),
        'raw_plan': raw, 'grouping_contract': GROUPING_CONTRACT, 'quality_validated': False})
    raise
assert sha256_file(directory/'result.json') == artifact_sha
report = {'scope': 'native catalogue and assignment on all previously admitted candidates; not full pipeline or cold end-to-end performance',
    'grouping_contract': GROUPING_CONTRACT, 'input_candidates': len(payload['phrases']),
    'plan': plan, 'subjects': len(plan['topics']),
    'single_candidate_subjects': sum(len(t['sentences']) == 1 for t in plan['topics']),
    'fresh_calls': sum(not call['cache_hit'] for call in runtime.profile),
    'native_wall_seconds': sum(call['wall_seconds'] for call in runtime.profile),
    'source_artifact_unchanged': True, 'human_review_created': False, 'quality_validated': False}
atomic_json(work/'probe.json', report)
print(json.dumps(report, ensure_ascii=True, indent=2))
