"""Run the packaged workers with a sanitized environment on this developer PC.

This is deliberately NOT the clean offline Windows acceptance test.
"""
import json
import os
import subprocess
import sys
import time
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths
parser = argparse.ArgumentParser()
parser.add_argument('--bundle', type=Path, default=ROOT / "dist/NoteTaker")
parser.add_argument('--report', type=Path, default=ROOT / "docs/evidence/bundle-validation.json")
args = parser.parse_args()
bundle = args.bundle.resolve()
models = ModelPaths(bundle)
models.verify()
forbidden = [str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_file() and any(token in p.name.casefold() for token in ('virtualkeyboard', 'asio'))]
if forbidden:
    raise AssertionError('Unapproved optional binary in payload: ' + ', '.join(forbidden))
workspace = ROOT / "output/bundle-validation" / str(uuid.uuid4())
workspace.mkdir(parents=True)
audio = ROOT / "output/phase0/fr-synthetic.wav"
requests = [
    {"engine": "asr", "device": "cpu", "audio": str(audio), "model": str(models.asr)},
    {"engine": "diarization-sherpa", "device": "cpu", "audio": str(audio), "segmentation": str(models.segmentation), "embedding": str(models.embedding), "refinement_embedding": str(models.refinement_embedding), "overlap": True},
    {"engine": "llm", "device": "cpu", "binary": str(models.llama), "model": str(models.llm), "workspace": str(workspace),
     "task": "summary", "utterances": [
         {"id": "s0", "speaker_id": "a", "start_ms": 0, "end_ms": 10000, "text": "Les travaux de la bibliothèque sont estimés à vingt mille euros. Je propose de commencer par réparer la toiture."},
         {"id": "s1", "speaker_id": "b", "start_ms": 10000, "end_ms": 20000, "text": "Je suis opposé à ce calendrier car la bibliothèque doit rester ouverte. Je propose de reporter les travaux aux vacances."}]},
]
env = dict(os.environ)
env.pop("PYTHONPATH", None)
env.pop("PYTHONHOME", None)
env["PYTHONIOENCODING"] = "utf-8"
env["PATH"] = os.environ.get("SystemRoot", "C:\\Windows") + "\\System32"
results = {
    "excluded_optional_binaries_absent": True,
    "environment": "developer PC; system Python paths removed; not clean Windows; host not disconnected",
    "tested_at_utc": datetime.now(timezone.utc).isoformat(),
    "executables_sha256": {name: sha256_file(bundle / name) for name in ("NoteTaker.exe", "NoteTaker-worker.exe")},
    "workers": {},
}
for request in requests:
    name = request["engine"]
    path = workspace / (name + ".json")
    atomic_json(path, request)
    started = time.perf_counter()
    process = subprocess.run([str(bundle / "NoteTaker-worker.exe"), str(path)], cwd=workspace, env=env,
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    (workspace / (name + ".stderr.txt")).write_text(process.stderr, encoding="utf-8")
    (workspace / (name + ".stdout.txt")).write_text(process.stdout, encoding="utf-8")
    try:
        response = json.loads(process.stdout)
    except ValueError:
        response = {"status": "invalid-response"}
    results["workers"][name] = {"exit_code": process.returncode, "seconds": round(time.perf_counter() - started, 3), "response": response}
    if process.returncode == 0 and not process.stdout.isascii():
        raise AssertionError('Worker JSON protocol must remain ASCII across Windows locales')
    if name == 'asr' and response.get('status') == 'completed':
        texts = ''.join(s['text'] for s in response['result']['segments'])
        if '\ufffd' in texts or not any(ord(c) > 127 for c in texts):
            raise AssertionError('French ASR text lost Unicode characters in the compiled worker')
        results['french_unicode_preserved'] = True
    atomic_json(args.report, results)
    print(name, process.returncode, response.get("status"), flush=True)
    if process.returncode or response.get("status") != "completed":
        raise SystemExit(f"Packaged {name} failed; inspect {workspace}")
results["bundle_size_bytes"] = sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file())
atomic_json(args.report, results)
