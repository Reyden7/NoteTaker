"""Real PortAudio capture with durable PCM journal independent of AI processes."""
import json
import hashlib
import os
import queue
import threading
import time
from pathlib import Path
from notetaker.infrastructure.atomic import atomic_json, sha256_file

class CaptureJournal:
    def __init__(self, directory: Path, rate: int, channels: int, segment_seconds=60):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=False)
        self.rate, self.channels = rate, channels
        self.frame_bytes = channels * 2
        self.limit = rate * segment_seconds * self.frame_bytes
        self.state = {"version": 1, "rate": rate, "channels": channels, "sample_width": 2,
                      "status": "recording", "frames": 0, "segments": [], "hashes": {}, "active": None, "committed_bytes": 0}
        self.stream = None
        self.active_bytes = 0
        self.digest = hashlib.sha256()
        self.last_flush = time.monotonic()
        self._checkpoint()

    def _checkpoint(self):
        if self.stream:
            self.stream.flush()
            os.fsync(self.stream.fileno())
        self.state["committed_bytes"] = self.active_bytes
        self.state["active_sha256"] = self.digest.hexdigest() if self.stream else None
        atomic_json(self.directory / "capture.json", self.state)
        self.last_flush = time.monotonic()

    def write(self, data):
        if len(data) % self.frame_bytes:
            raise ValueError("INCOMPLETE_PCM_FRAME")
        while data:
            if self.stream is None:
                self.state["active"] = f"{len(self.state['segments']):06d}.pcm.part"
                self.stream = (self.directory / self.state["active"]).open("xb")
                self.active_bytes = 0
                self.digest = hashlib.sha256()
                self._checkpoint()
            block, data = data[:self.limit - self.active_bytes], data[self.limit - self.active_bytes:]
            self.stream.write(block)
            self.digest.update(block)
            self.active_bytes += len(block)
            self.state["frames"] += len(block) // self.frame_bytes
            if self.active_bytes == self.limit:
                self._finish_segment()
        if time.monotonic() - self.last_flush >= 1:
            self._checkpoint()

    def _finish_segment(self):
        if self.stream is None:
            return
        self._checkpoint()
        self.stream.close()
        self.stream = None
        partial = self.directory / self.state["active"]
        final = partial.with_suffix("")
        os.replace(partial, final)
        self.state["hashes"][final.name] = self.digest.hexdigest()
        self.state["segments"].append(final.name)
        self.state["active"] = None
        self.active_bytes = 0
        self._checkpoint()

    def close(self, status="completed"):
        self._finish_segment()
        self.state["status"] = status
        self._checkpoint()

def inspect_capture(directory: Path):
    state = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
    if state.get("version") != 1 or state.get("sample_width") != 2 or state["channels"] not in (1, 2) or not 8000 <= state["rate"] <= 192000:
        raise ValueError("UNSUPPORTED_CAPTURE_FORMAT")
    # Discover the rename-before-manifest gap as well as interrupted active files.
    chunks = sorted([*directory.glob("*.pcm"), *directory.glob("*.pcm.part")], key=lambda p: p.name)
    frame_bytes = state["channels"] * 2
    errors = []
    for name, digest in state.get("hashes", {}).items():
        path = directory / name
        if Path(name).name != name or not path.is_file() or sha256_file(path) != digest:
            errors.append(name)
    active = state.get("active")
    if active and Path(active).name != active:
        raise ValueError("UNSAFE_CAPTURE_PATH")
    if active and (directory / active).is_file() and state.get("active_sha256"):
        digest = hashlib.sha256()
        remaining = state["committed_bytes"]
        with (directory / active).open("rb") as stream:
            while remaining:
                block = stream.read(min(1024 * 1024, remaining))
                if not block:
                    break
                digest.update(block)
                remaining -= len(block)
        if remaining or digest.hexdigest() != state["active_sha256"]:
            errors.append(active)
    return {**state, "chunks": chunks, "recoverable_frames": sum(p.stat().st_size // frame_bytes for p in chunks),
            "requires_recovery": state["status"] == "recording", "integrity_errors": errors}

def recover_capture(directory: Path):
    report = inspect_capture(directory)
    if report["requires_recovery"]:
        original = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
        original["status"] = "interrupted"
        atomic_json(directory / "capture.json", original)
    return inspect_capture(directory)

def input_devices():
    import sounddevice as sd
    apis = sd.query_hostapis()
    return [{"id": i, "name": d["name"], "api": apis[d["hostapi"]]["name"],
             "channels": min(2, int(d["max_input_channels"])), "rate": int(d["default_samplerate"])}
            for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]

class MicrophoneRecorder:
    def __init__(self):
        self.stream = None
        self.thread = None
        self.paused = False
        self.level = 0.0
        self.error = None
        self.frames = 0
        self.rate = 0
        self.queue = queue.Queue(maxsize=256)
        self.finished = threading.Event()

    def start(self, directory: Path, device: dict):
        import sounddevice as sd
        import numpy as np
        self.rate = device["rate"]
        self.journal = CaptureJournal(directory, self.rate, device["channels"])
        def callback(data, frames, timestamp, status):
            if status:
                self.error = "AUDIO_INPUT_OVERFLOW_OR_DEVICE_ERROR"
            samples = np.frombuffer(data, dtype="<i2").astype(np.int32)
            self.level = float(np.max(np.abs(samples))) / 32768 if samples.size else 0
            if not self.paused:
                try:
                    self.queue.put_nowait(bytes(data))
                    self.frames += frames
                except queue.Full:
                    self.error = "AUDIO_DISK_QUEUE_FULL"
                    raise sd.CallbackStop()
        def writer():
            try:
                while not self.finished.is_set() or not self.queue.empty():
                    try:
                        data = self.queue.get(timeout=0.1)
                    except queue.Empty:
                        if time.monotonic() - self.journal.last_flush >= 1:
                            self.journal._checkpoint()
                        continue
                    self.journal.write(data)
                self.journal.close("interrupted" if self.error else "completed")
            except Exception:
                self.error = "AUDIO_WRITE_FAILED_RAW_FILES_PRESERVED"
                if self.journal.stream:
                    self.journal.stream.close()
        self.thread = threading.Thread(target=writer, name="notetaker-audio-writer", daemon=False)
        self.thread.start()
        try:
            self.stream = sd.RawInputStream(device=device["id"], channels=device["channels"], samplerate=self.rate,
                                            dtype="int16", blocksize=2048, callback=callback)
            self.stream.start()
        except BaseException:
            self.error = "MICROPHONE_START_FAILED"
            self.stop()
            raise

    def stop(self):
        try:
            if self.stream:
                try:
                    self.stream.stop()
                finally:
                    self.stream.close()
                    self.stream = None
        finally:
            self.finished.set()
            if self.thread:
                self.thread.join(timeout=10)
                if self.thread.is_alive():
                    self.error = "AUDIO_WRITER_STILL_FLUSHING"

    @property
    def seconds(self):
        return self.frames / self.rate if self.rate else 0
