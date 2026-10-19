"""Cold replay of the preserved 0.2.4 executable; private copies only."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.windows_job import start_process
from notetaker.infrastructure.cpu_profile import job_cpu
from notetaker.domain.minutes import content_digest

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
p.add_argument('--prepare', action='store_true')
args = p.parse_args()
work = args.work.resolve()
work.mkdir(parents=True, exist_ok=False)
request = json.loads((ROOT/'output/information-registry/field-670/write.request.json').read_text(encoding='utf-8'))
inference = work/'inference'
inference.mkdir()
request['workspace'] = str(inference)
if args.prepare:
    from notetaker.domain.information_registry import seed_registry
    request['task'] = 'registry_prepare'
    request['registry'] = seed_registry(request['registry']['session_id'],
        {'utterances': request['utterances'], 'speakers': request['registry']['speakers']})
    request['verification_policy'] = 'on_request'
atomic_json(work/'request.json', request)
worker = ROOT/'dist/information-registry/NoteTaker/NoteTaker-worker.exe'
report = {'status': 'running', 'pipeline': '0.2.4 preserved frozen worker',
          'worker_sha256': sha256_file(worker), 'input_rows': len(request['utterances']),
          'preparation_included': args.prepare, 'prior_registry_verification_included': False,
          'input_rows_sha256': content_digest(request['utterances']),
          'cold_scope': 'empty response cache; new processes; OS disk cache not flushed',
          'human_reference': False, 'quality_scores': None}
atomic_json(work/'report.json', report)
started = time.perf_counter()
with (work/'stdout.json').open('wb') as out, (work/'stderr.txt').open('wb') as err:
    process, job = start_process([str(worker), str(work/'request.json')], stdout=out, stderr=err,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        while process.poll() is None:
            report['wall_seconds'] = round(time.perf_counter()-started, 3)
            report['cpu'] = job_cpu(job)
            report['qwen_calls_completed'] = len(list(inference.glob('*.timing.json')))
            atomic_json(work/'report.json', report)
            time.sleep(2)
        report.update(status='completed' if process.returncode == 0 else 'failed', exit_code=process.returncode,
                      wall_seconds=round(time.perf_counter()-started, 3), cpu=job_cpu(job),
                      qwen_calls_completed=len(list(inference.glob('*.timing.json'))))
        atomic_json(work/'report.json', report)
    finally:
        job.close()
print(json.dumps(report), flush=True)
