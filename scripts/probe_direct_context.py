"""One REAL context contract probe. Not a whole-meeting performance comparison."""
import argparse
import json
import sys
import uuid
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json
from notetaker.infrastructure.offline import enforce_offline, deny_python_network
from notetaker.domain.direct_summary import VERSION, MARKER
from notetaker.engines.direct_summary import summarize
from notetaker.engines.direct_runtime import DirectRuntime
from notetaker.infrastructure.paths import ModelPaths

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
args = p.parse_args()
work = args.work.resolve()
work.mkdir(parents=True, exist_ok=False)
test_root = work/'test-root'
atomic_json(test_root/MARKER, {'id': str(uuid.uuid4()), 'purpose': 'direct-summary-test'})
original = next((ROOT/'output/direct-summary/direct-cold-02/data/sessions').glob('*/direct-experiments/*/request.json'))
request = json.loads(original.read_text(encoding='utf-8'))
request.update(pipeline_version=VERSION, workspace=str(work), test_root=str(test_root), cache_mode='cold')
atomic_json(work/'request.json', request)
enforce_offline()
attempts = deny_python_network()
ModelPaths().verify()
runtime = DirectRuntime(request)

class ProbeComplete(Exception):
    pass

class OneContext:
    def call(self, label, *args, **kwargs):
        if label != 'context-000':
            raise ProbeComplete()
        return runtime.call(label, *args, **kwargs)

try:
    summarize(request, OneContext())
except ProbeComplete:
    checkpoint = json.loads((work/'direct-checkpoint.json').read_text(encoding='utf-8'))
    report = {'scope': 'one real CPU context; contract probe only, NOT complete 670-row comparison',
        'version': VERSION, 'total_source_rows_preserved': len(checkpoint['all_sources']),
        'contexts_completed': len(checkpoint['parts']), 'whole_meeting_processed': False,
        'candidates': len(checkpoint['candidates']),
        'static_states': dict(Counter(c['status'] for c in checkpoint['candidates'])),
        'rejection_reasons': dict(Counter(r['reason'] for r in checkpoint['rejected'])),
        'fresh_native_calls': 1, 'cached_calls': 0, 'profile': runtime.profile,
        'human_review_created': False, 'quality_validated': False, 'python_network_attempts': len(attempts)}
    atomic_json(work/'probe.json', report)
    print(json.dumps(report, ensure_ascii=True), flush=True)
else:
    raise AssertionError('Expected an explicitly partial context probe')
