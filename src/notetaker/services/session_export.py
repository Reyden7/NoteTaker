import os
import shutil
import tempfile
import uuid
from pathlib import Path
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import session_directory
from .export import export_draft

def export_session(store, sid, destination: Path):
    state, review = store.reviewed_content(sid)
    directory = session_directory(store.root, sid) / "exports"
    directory.mkdir(exist_ok=True)
    internal = directory / (str(uuid.uuid4()) + destination.suffix.lower())
    export_draft(state["draft"]["content"], review, internal, session_id=sid, municipality=state["metadata"].get("municipality", ""),
                 session_date=state["metadata"].get("date", ""), votes=state["votes"], decisions=state["decisions"])
    atomic_json(internal.with_suffix(".snapshot.json"), {k: state[k] for k in ("title", "metadata", "speakers", "utterances", "votes", "decisions", "draft")})
    digest = sha256_file(internal)
    store.record_export(sid, state["draft"]["id"], internal, digest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=destination.parent, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as target, internal.open("rb") as source:
            shutil.copyfileobj(source, target)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination
