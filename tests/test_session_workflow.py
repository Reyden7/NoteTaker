import json
import os
import subprocess
import sys
import wave
from pathlib import Path
import pytest
from notetaker.infrastructure.atomic import sha256_file
from notetaker.infrastructure.paths import session_directory
from notetaker.services.storage import SessionStore
from notetaker.services.audio import import_audio, prepare_audio
from notetaker.services.recording import CaptureJournal, inspect_capture, recover_capture
from notetaker.services.pipeline import align_transcript, assemble_draft
from notetaker.services.session_export import export_session

@pytest.fixture
def store(tmp_path):
    value = SessionStore(tmp_path / "data")
    yield value
    value.close()

def analysed_session(store):
    sid = store.create("Séance du conseil", {"municipality": "Commune test", "date": "2026-10-16", "agenda": ["Bibliothèque"]})
    rows = [{"id": "s0", "start_ms": 0, "end_ms": 1000, "text": "La bibliothèque sera rénovée.", "speaker_id": "speaker_0", "uncertain": True}]
    store.save_analysis(sid, rows, {"speaker_0": "Intervenant 1"}, 0)
    return sid

def draft_for(store, sid):
    state = store.get(sid)
    return assemble_draft(state, {"selections": {"0": ["s0"]}})

def test_session_persists_metadata_history_and_archive(store):
    sid = analysed_session(store)
    store.archive(sid)
    reopened = SessionStore(store.root)
    try:
        state = reopened.get(sid)
        assert state["archived"] == 1 and state["metadata"]["agenda"] == ["Bibliothèque"]
        assert state["utterances"][0]["text"] == "La bibliothèque sera rénovée."
        assert reopened.list_sessions("conseil")[0]["id"] == sid
    finally:
        reopened.close()

def test_analysis_cannot_replace_concurrent_edits(store):
    sid = analysed_session(store)
    revision = store.get(sid)["revision"]
    store.rename_speaker(sid, "speaker_0", "Mme Dupont")
    with pytest.raises(ValueError, match="CHANGED_DURING_ANALYSIS"):
        store.save_analysis(sid, [], {}, revision)
    assert store.get(sid)["utterances"]

def test_overlapping_and_uncovered_speech_stays_uncertain():
    rows, speakers = align_transcript([{"id": "s0", "start": 0, "end": 2, "text": "Bonjour"}, {"id": "s1", "start": 3, "end": 4, "text": "Suite"}],
        {"turns": [{"start": 0, "end": 2, "speaker": "a"}], "possible_overlaps": [{"start": 1, "end": 1.5}]})
    assert rows[0]["uncertain"] and rows[0]["source"]["possible_overlap"]
    assert rows[1]["uncertain"] and rows[1]["speaker_id"] is None
    assert speakers == {"a": "Intervenant 1"}

def test_generated_draft_cannot_create_vote_or_narrative_fact(store):
    sid = analysed_session(store)
    store.edit_utterance(sid, "s0", "Le vote donne douze voix pour.", "speaker_0")
    draft = draft_for(store, sid)
    assert all(p["vote_id"] is None and "douze voix" not in p["summary"] for p in draft["points"])
    assert any("Saisir le résultat" in v for v in draft["to_verify"])
    assert store.get(sid)["votes"] == []

@pytest.mark.parametrize("change", ["transcript", "speaker", "votes", "metadata", "draft"])
def test_every_relevant_edit_invalidates_export_review(store, tmp_path, change):
    sid = analysed_session(store)
    store.save_draft(sid, draft_for(store, sid))
    with pytest.raises(ValueError, match="HUMAN_REVIEW"):
        export_session(store, sid, tmp_path / "no-review.pdf")
    store.approve(sid, "Test reviewer fixture")
    if change == "transcript":
        store.edit_utterance(sid, "s0", "Texte corrigé.", "speaker_0")
    elif change == "speaker":
        store.rename_speaker(sid, "speaker_0", "Mme Exemple")
    elif change == "votes":
        store.save_manual(sid, [], ["Décision saisie"])
    elif change == "metadata":
        store.save_details(sid, "Nouveau titre", store.get(sid)["metadata"])
    else:
        draft = draft_for(store, sid)
        draft["points"][0]["summary"] = "Modification humaine"
        store.save_draft(sid, draft)
    with pytest.raises(ValueError, match="HUMAN_REVIEW"):
        export_session(store, sid, tmp_path / "stale.pdf")
    assert not (tmp_path / "stale.pdf").exists()

def test_structured_manual_vote_and_decision_exported_without_inference(store, tmp_path):
    sid = analysed_session(store)
    vote = {"id": "v0", "title": "Travaux", "status": "entered", "for_count": 12, "against_count": 2, "abstain_count": 1, "nonparticipating_count": 0, "source": "Saisie opérateur test"}
    store.save_manual(sid, [vote], ["Demander un devis complémentaire"])
    store.save_draft(sid, draft_for(store, sid))
    store.approve(sid, "Test review only")
    path = export_session(store, sid, tmp_path / "reviewed.pdf")
    from pypdf import PdfReader
    text = "\n".join(p.extract_text() for p in PdfReader(path).pages)
    assert "pour 12, contre 2" in text and "devis complémentaire" in text
    assert "BROUILLON NON OFFICIEL" in text
    assert list(session_directory(store.root, sid).glob("exports/*.snapshot.json"))

def test_incomplete_vote_cannot_be_saved(store):
    sid = analysed_session(store)
    with pytest.raises(ValueError, match="COUNTS_AND_SOURCE"):
        store.save_manual(sid, [{"id": "v", "title": "Vote", "status": "entered", "for_count": 0}], [])
    with pytest.raises(ValueError, match="UNKNOWN_VOTE"):
        store.save_manual(sid, [{"id": "v", "title": "Vote", "status": "unknown", "for_count": 2}], [])

def test_pcm_capture_rolls_segments_and_is_recoverable(tmp_path):
    directory = tmp_path / "capture"
    journal = CaptureJournal(directory, 16000, 1, segment_seconds=1)
    journal.write(b"\0\0" * 40000)
    journal.close()
    report = inspect_capture(directory)
    assert report["recoverable_frames"] == 40000 and len(report["chunks"]) == 3
    target = prepare_audio([{"kind": "capture", "path": str(directory)}], tmp_path / "result.wav")
    with wave.open(str(target)) as audio:
        assert audio.getnframes() == 40000

def test_real_crash_keeps_checkpoint_and_active_pcm(tmp_path):
    directory = tmp_path / "crashed"
    code = """
import os,sys
from pathlib import Path
from notetaker.services.recording import CaptureJournal
j=CaptureJournal(Path(sys.argv[1]),16000,1)
j.write(b'\\0\\0'*20000); j._checkpoint(); os._exit(29)
"""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    child = subprocess.run([sys.executable, "-c", code, str(directory)], env=env)
    assert child.returncode == 29
    report = recover_capture(directory)
    assert report["status"] == "interrupted" and report["recoverable_frames"] == 20000
    assert report["chunks"][0].suffix == ".part"
    target = prepare_audio([{"kind": "capture", "path": str(directory)}], tmp_path / "recovered.wav")
    with wave.open(str(target)) as audio:
        assert audio.getnframes() == 20000

def test_import_preserves_original_and_rejects_tampering(tmp_path, store):
    sid = store.create("Import")
    source = tmp_path / "source.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0\0\0" * 48000)
    digest = sha256_file(source)
    copied, original_digest = import_audio(source, session_directory(store.root, sid))
    assert copied != source and digest == original_digest == sha256_file(copied)
    take = {"kind": "import", "path": str(copied), "sha256": digest}
    normalized = prepare_audio([take], tmp_path / "normalized.wav")
    with wave.open(str(normalized)) as audio:
        assert audio.getframerate() == 16000 and audio.getnchannels() == 1 and audio.getnframes() == 16000
    copied.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="INTEGRITY"):
        prepare_audio([take], tmp_path / "tampered.wav")
    assert sha256_file(source) == digest

def test_long_context_is_split_and_every_character_kept():
    from notetaker.engines.llama_adapter import source_chunks
    original = "Échange municipal été " * 1000
    chunks = list(source_chunks([{"id": "s0", "text": original}]))
    assert len(chunks) > 5
    assert "".join(record["text"] for chunk in chunks for record in chunk) == original
    assert {record["id"] for chunk in chunks for record in chunk} == {"s0"}

def test_split_and_merge_preserve_times_and_require_review(store):
    sid = analysed_session(store)
    store.edit_utterance(sid, "s0", "Première phrase. Deuxième phrase.", "speaker_0", confirm=True)
    second = store.split_utterance(sid, "s0", 500, 17)
    rows = store.get(sid)["utterances"]
    assert rows[0]["end_ms"] == rows[1]["start_ms"] == 500 and rows[1]["id"] == second
    assert all(u["uncertain"] for u in rows)
    with store.db:
        store.db.execute("INSERT INTO speaker VALUES('speaker_1',?,'Intervenant 2')", (sid,))
    store.edit_utterance(sid, second, rows[1]["text"], "speaker_1", confirm=True)
    store.merge_speakers(sid, "speaker_1", "speaker_0")
    state = store.get(sid)
    assert len(state["speakers"]) == 1
    assert all(u["speaker_id"] == "speaker_0" for u in state["utterances"])

def test_audio_selection_never_deletes_a_take(store, tmp_path):
    sid = store.create("Prises")
    path = tmp_path / "original.wav"
    path.write_bytes(b"kept original")
    tid = store.add_take(sid, "import", path, sha256=sha256_file(path))
    store.set_take_enabled(tid, False)
    assert path.exists() and store.get(sid)["takes"][0]["enabled"] == 0

def test_diarization_failure_keeps_transcript_and_original(store, tmp_path, monkeypatch):
    from notetaker.services.pipeline import Pipeline
    sid = store.create("Panne moteur")
    source = tmp_path / "speech.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * 16000)
    path, digest = import_audio(source, session_directory(store.root, sid))
    store.add_take(sid, "import", path, sha256=digest)
    pipeline = Pipeline(store.root)
    monkeypatch.setattr(pipeline.models, "verify", lambda: None)
    def injected_stage(workspace, request, **kwargs):
        if request["engine"] == "asr":
            return {"segments": [{"id": "s0", "start": 0, "end": 1, "text": "Fault injection fixture"}]}
        raise RuntimeError("Injected diarization failure; not an inference test")
    monkeypatch.setattr(pipeline, "_run", injected_stage)
    with pytest.raises(RuntimeError, match="TRANSCRIPT_PRESERVED"):
        pipeline.analyse(sid)
    assert store.get(sid)["utterances"][0]["uncertain"] == 1
    assert sha256_file(path) == digest
    assert store.jobs(sid)[0]["status"] == "failed"

def test_worker_cancel_stops_without_starting_fallback(tmp_path):
    import threading
    from notetaker.infrastructure.process import run_worker, JobCancelled
    from notetaker.infrastructure.atomic import atomic_json
    request = tmp_path / "request.json"
    atomic_json(request, {"engine": "diarization", "model": str(tmp_path / "absent")})
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(JobCancelled):
        run_worker(request, cancel=cancel, timeout=10)

def test_capture_tampering_is_reported_and_original_retained(tmp_path):
    directory = tmp_path / "capture"
    journal = CaptureJournal(directory, 16000, 1)
    journal.write(b"\0\0" * 16000)
    journal.close()
    chunk = inspect_capture(directory)["chunks"][0]
    chunk.write_bytes(b"\1\0" * 16000)
    assert inspect_capture(directory)["integrity_errors"] == [chunk.name]
    with pytest.raises(ValueError, match="INTEGRITY"):
        prepare_audio([{"kind": "capture", "path": str(directory)}], tmp_path / "derived.wav")
    assert chunk.exists()

def test_migration_from_phase0_keeps_sessions_and_jobs(tmp_path):
    import sqlite3
    from notetaker.infrastructure.database import migrate, MIGRATIONS, open_database
    path = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(path)
    migrate(connection, {1: MIGRATIONS[1]})
    with connection:
        connection.execute("INSERT INTO session(id,title) VALUES('legacy','Ancienne séance')")
        connection.execute("INSERT INTO job VALUES('j','legacy','asr','completed',NULL)")
    connection.close()
    migrated = open_database(path)
    assert migrated.execute("PRAGMA user_version").fetchone()[0] == 5
    assert migrated.execute("SELECT title FROM session").fetchone()[0] == "Ancienne séance"
    assert migrated.execute("SELECT status FROM job").fetchone()[0] == "completed"
    migrated.close()

@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object qualification")
def test_windows_job_terminates_child_tree(tmp_path):
    import time
    import psutil
    from notetaker.infrastructure.windows_job import WindowsJob
    pidfile = tmp_path / "child.pid"
    code = """
import subprocess,sys,time
from pathlib import Path
time.sleep(0.3)
child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
Path(sys.argv[1]).write_text(str(child.pid))
time.sleep(60)
"""
    process = subprocess.Popen([sys.executable, "-c", code, str(pidfile)])
    job = WindowsJob(process)
    try:
        deadline = time.monotonic() + 5
        while not pidfile.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pidfile.exists()
        child = psutil.Process(int(pidfile.read_text()))
        job.close()
        process.wait(timeout=5)
        gone, alive = psutil.wait_procs([child], timeout=3)
        assert not alive
    finally:
        job.close()
        if process.poll() is None:
            process.kill()
