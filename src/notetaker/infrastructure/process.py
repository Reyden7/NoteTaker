"""Bounded subprocess communication. No network server or shell interpretation."""
import json
import os
import subprocess
import sys
from pathlib import Path
from .offline import OFFLINE_ENV

class JobCancelled(Exception):
    pass

def stop_tree(process):
    import psutil
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
        psutil.wait_procs(children, timeout=3)
    except psutil.NoSuchProcess:
        pass
    process.wait(timeout=5)

def run_worker(request: Path, *, python: Path | None = None, timeout: float = 120, cancel=None,
               module="notetaker.workers.probe") -> dict:
    env = dict(os.environ)
    env.update(OFFLINE_ENV)
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        env.pop(key, None)
    if module == "notetaker.workers.gpu_audio":
        # A new empty cache per analysis job proves that client credentials/cache
        # are unnecessary. Never inherit the build account's HF authentication.
        env["HF_HOME"] = str(request.parent / "offline-cache")
        env['HF_TOKEN_PATH'] = str(request.parent / 'offline-cache' / 'token')
        env['HF_STORED_TOKENS_PATH'] = str(request.parent / 'offline-cache' / 'stored_tokens')
        env['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
        for key in ('HF_HUB_CACHE', 'HUGGINGFACE_HUB_CACHE', 'TRANSFORMERS_CACHE'):
            env[key] = str(request.parent / "offline-cache" / "hub")
        env["TORCH_HOME"] = str(request.parent / "offline-cache" / "torch")
        env["OMP_NUM_THREADS"] = env["MKL_NUM_THREADS"] = "4"
    env["PYTHONIOENCODING"] = "utf-8"
    if python:
        env.pop('PYTHONHOME', None)
        env.pop('VIRTUAL_ENV', None)
        env['PYTHONNOUSERSITE'] = '1'
    # Development path; frozen worker entry points will be built during phase 6.
    env["PYTHONPATH"] = (str(python.parent / "app") if python and ((python.parent / 'app').is_dir() or getattr(sys, "frozen", False))
                         else str(Path(__file__).resolve().parents[2]))
    command = ([str(python or sys.executable), "-m", module, str(request.resolve(strict=True))]
               if python or not getattr(sys, "frozen", False) else [str(Path(sys.executable).with_name("NoteTaker-worker.exe")), str(request.resolve(strict=True))])
    try:
        if cancel is not None or os.name == 'nt':
            import time
            started = time.monotonic()
            from .windows_job import start_process
            child, job = start_process(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, encoding="utf-8", errors="strict", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                while True:
                    if (cancel is not None and cancel.is_set()) or time.monotonic() - started > timeout:
                        job.close()
                        stop_tree(child)
                        if cancel is not None and cancel.is_set():
                            raise JobCancelled("JOB_CANCELLED")
                        raise TimeoutError("WORKER_TIMEOUT")
                    try:
                        stdout, stderr = child.communicate(timeout=0.2)
                        completed = subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
                        break
                    except subprocess.TimeoutExpired:
                        continue
            finally:
                job.close()
        else:
            completed = subprocess.run(
                command,
                env=env, capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="strict",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("WORKER_TIMEOUT") from exc
    if completed.returncode:
        try:
            failed = json.loads(completed.stdout)
        except (ValueError, TypeError):
            failed = {}
        if isinstance(failed, dict) and failed.get("status") == "failed" and isinstance(failed.get("error_code"), str):
            raise RuntimeError(failed["error_code"])
        raise RuntimeError(f"WORKER_EXIT_{completed.returncode}")
    try:
        result = json.loads(completed.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("INVALID_WORKER_RESPONSE") from exc
    if result.get("status") != "completed":
        raise RuntimeError(result.get("error_code", "WORKER_FAILED"))
    return result
