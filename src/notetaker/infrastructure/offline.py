"""Apply policy BEFORE importing any inference library."""
import os
import sys
from pathlib import Path

OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "PYANNOTE_METRICS_ENABLED": "0",
    "DO_NOT_TRACK": "1",
    "OTEL_SDK_DISABLED": "true",
    "LLAMA_ARG_OFFLINE": "1",
}

def enforce_offline() -> None:
    # Deliberately override user values, rather than setdefault.
    os.environ.update(OFFLINE_ENV)

def deny_python_network() -> list[str]:
    """Probe guard, not a native-code firewall. Records event names, never addresses."""
    attempts = []
    def audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            attempts.append(event)
            raise PermissionError("NETWORK_FORBIDDEN")
    sys.addaudithook(audit)
    return attempts

def local_path(value: str | Path, *, directory: bool = False) -> Path:
    path = Path(value).resolve(strict=True)
    if directory and not path.is_dir():
        raise ValueError("LOCAL_MODEL_DIRECTORY_REQUIRED")
    if not directory and not path.is_file():
        raise ValueError("LOCAL_FILE_REQUIRED")
    return path
