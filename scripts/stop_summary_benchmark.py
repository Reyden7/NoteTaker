"""Stop only this repository's explicitly identified summary benchmark tree."""
import sys
from pathlib import Path
import psutil
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.process import stop_tree

matches = []
for process in psutil.process_iter(['cmdline']):
    try:
        command = process.info['cmdline'] or []
        if any(Path(a).name == 'benchmark_quality.py' for a in command) and '--stage' in command:
            if command[command.index('--stage') + 1] == 'summary' and Path(process.cwd()).resolve() == ROOT:
                matches.append(process)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue
roots = [p for p in matches if p.ppid() not in {other.pid for other in matches}]
if len(roots) != 1:
    raise SystemExit(f'Expected exactly one benchmark root, found {len(roots)}; no processes stopped')
process = roots[0]
children = process.children(recursive=True)
for child in reversed(children):
    try:
        child.kill()
    except psutil.NoSuchProcess:
        pass
process.kill()
psutil.wait_procs([process, *children], timeout=5)
print('Stopped only the identified summary benchmark; preserved all intermediate files')
