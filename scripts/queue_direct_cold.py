"""Sequence two already-authorized local benchmarks, never parallel Qwen runs."""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json

p = argparse.ArgumentParser()
p.add_argument('--after-legacy', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
args = p.parse_args()
legacy, work = args.after_legacy.resolve(), args.work.resolve()
assert (legacy/'report.json').is_file() and not work.exists()
assert legacy.is_relative_to(ROOT/'output') and work.is_relative_to(ROOT/'output')
queue_path = work.with_name(work.name+'-queue.json')
record = {'status':'waiting_for_legacy', 'legacy':str(legacy), 'next_work':str(work),
          'started_at_utc':datetime.now(timezone.utc).isoformat(),
          'scope':'sequencing only; wait time is not inference time', 'fresh_qwen_runs_sequential':True}
started = time.monotonic()
print('Waiting for preserved legacy worker before starting a new empty-cache direct run.', flush=True)
while True:
    # A replacing writer/antivirus can temporarily deny even a read on Windows.
    # Retry only that transient error; malformed reports must still fail visibly.
    for attempt in range(21):
        try:
            state = json.loads((legacy/'report.json').read_text(encoding='utf-8'))
            break
        except PermissionError:
            if attempt == 20:
                raise
            time.sleep(min(0.01 * (attempt + 1), 0.1))
    record.update(legacy_status=state['status'], legacy_calls_completed=state.get('qwen_calls_completed'),
                  wait_seconds=time.monotonic()-started)
    atomic_json(queue_path,record)
    if state['status'] != 'running':
        break
    if time.monotonic()-started > 14400:
        raise TimeoutError('Legacy benchmark still running; new inference was not started')
    time.sleep(2)
# The legacy script closes its Job immediately after persisting final status.
time.sleep(2)
record.update(status='running_direct', direct_started_at_utc=datetime.now(timezone.utc).isoformat())
atomic_json(queue_path,record)
print('Legacy finished; starting the full corrected direct pipeline with no response cache.', flush=True)
result = subprocess.run([sys.executable,str(ROOT/'scripts/run_direct_field.py'),'--work',str(work)],
    cwd=ROOT, timeout=14400, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
record.update(status='completed' if result.returncode==0 else 'direct_failed',
              direct_exit_code=result.returncode, finished_at_utc=datetime.now(timezone.utc).isoformat())
atomic_json(queue_path,record)
sys.exit(result.returncode)
