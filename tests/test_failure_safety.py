import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from notetaker.services import audio_segments
from notetaker.domain.minutes import record_human_review

def test_failure_between_wav_commit_and_manifest_preserves_orphan(tmp_path, monkeypatch):
    def disk_full(*args):
        raise OSError("injected disk-full during manifest commit")
    monkeypatch.setattr(audio_segments, "atomic_json", disk_full)
    with pytest.raises(OSError):
        audio_segments.commit_pcm_segment(tmp_path, b"\0\0" * 16000)
    report = audio_segments.inspect_recovery(tmp_path)
    assert len(report["orphans"]) == 1
    assert (tmp_path / report["orphans"][0]).stat().st_size > 32000

def test_network_guard_blocks_before_dns_or_connection():
    code = """
import socket
from notetaker.infrastructure.offline import deny_python_network
attempts=deny_python_network()
try:
    socket.create_connection(('example.com', 443), timeout=1)
except PermissionError:
    print(len(attempts))
else:
    raise SystemExit('guard failed')
"""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0 and result.stdout.strip() == "1"

def test_empty_review_cannot_authorize_export():
    with pytest.raises(ValueError, match="REVIEWER_REQUIRED"):
        record_human_review({"points": [], "to_verify": []}, " ")

def test_worker_launcher_forces_utf8_for_french_text(tmp_path, monkeypatch):
    from notetaker.infrastructure import process
    from notetaker.infrastructure.atomic import atomic_json
    request = tmp_path / "request.json"
    atomic_json(request, {})
    def completed(*args, **kwargs):
        assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
        return subprocess.CompletedProcess(args, 0, '{"status":"completed","text":"Séance à vérifier"}', "")
    monkeypatch.setattr(process.subprocess, "run", completed)
    from notetaker.infrastructure import windows_job
    class FixtureChild:
        returncode = 0
        def communicate(self, timeout):
            return '{"status":"completed","text":"Séance à vérifier"}', ''
    class FixtureJob:
        def close(self):pass
    def launched(*args, **kwargs):
        assert kwargs['env']['PYTHONIOENCODING'] == 'utf-8'
        assert kwargs['encoding'] == 'utf-8' and kwargs['errors'] == 'strict'
        return FixtureChild(), FixtureJob()
    monkeypatch.setattr(windows_job, 'start_process', launched)
    assert process.run_worker(request)["text"] == "Séance à vérifier"
