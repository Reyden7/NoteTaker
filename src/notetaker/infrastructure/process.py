"""Bounded subprocess communication. No network server or shell interpretation."""
import json
import os
import subprocess
import sys
from pathlib import Path
from .offline import OFFLINE_ENV

def run_worker(request: Path, *, python: Path | None = None, timeout: float = 120) -> dict:
    env = dict(os.environ)
    env.update(OFFLINE_ENV)
    env["PYTHONIOENCODING"] = "utf-8"
    # Development path; frozen worker entry points will be built during phase 6.
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    try:
        completed = subprocess.run(
            [str(python or sys.executable), "-m", "notetaker.workers.probe", str(request.resolve(strict=True))],
            env=env, capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("WORKER_TIMEOUT") from exc
    if completed.returncode:
        raise RuntimeError(f"WORKER_EXIT_{completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("INVALID_WORKER_RESPONSE") from exc
    if result.get("status") != "completed":
        raise RuntimeError(result.get("error_code", "WORKER_FAILED"))
    return result
