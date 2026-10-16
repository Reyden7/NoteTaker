"""Run the packaged workers with a sanitized environment on this developer PC.

This is deliberately NOT the clean offline Windows acceptance test.
"""
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths
bundle = ROOT / "dist/NoteTaker"
models = ModelPaths(bundle)
models.verify()
workspace = ROOT / "output/bundle-validation" / str(uuid.uuid4())
workspace.mkdir(parents=True)
audio = ROOT / "output/phase0/fr-synthetic.wav"
requests = [
    {"engine": "asr", "device": "cpu", "audio": str(audio), "model": str(models.asr)},
    {"engine": "diarization-sherpa", "device": "cpu", "audio": str(audio), "segmentation": str(models.segmentation), "embedding": str(models.embedding), "overlap": True},
    {"engine": "llm", "device": "cpu", "binary": str(models.llama), "model": str(models.llm), "workspace": str(workspace),
     "agenda": ["Bibliothèque"], "utterances": [{"id": "s0", "text": "Nous examinons les travaux de la bibliothèque. Aucun résultat de vote n’est fourni."}]},
]
env = dict(os.environ)
env.pop("PYTHONPATH", None)
env.pop("PYTHONHOME", None)
env["PYTHONIOENCODING"] = "utf-8"
env["PATH"] = os.environ.get("SystemRoot", "C:\\Windows") + "\\System32"
results = {
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
    atomic_json(ROOT / "docs/evidence/bundle-validation.json", results)
    print(name, process.returncode, response.get("status"), flush=True)
    if process.returncode or response.get("status") != "completed":
        raise SystemExit(f"Packaged {name} failed; inspect {workspace}")
results["bundle_size_bytes"] = sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file())
atomic_json(ROOT / "docs/evidence/bundle-validation.json", results)
