import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def atomic_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows readers may briefly omit FILE_SHARE_DELETE. Keep the old
        # complete file until a bounded atomic replacement succeeds; never
        # fall back to truncating it in place.
        for attempt in range(21):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if os.name != 'nt' or attempt == 20:
                    raise
                time.sleep(min(0.01 * (attempt + 1), 0.1))
    finally:
        Path(temp).unlink(missing_ok=True)
