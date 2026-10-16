"""Durability experiment for completed PCM segments, NOT a microphone recorder.

One writer per directory. No silent recovery/deletion of incomplete recordings.
"""
import json
import os
import uuid
import wave
from pathlib import Path
from notetaker.infrastructure.atomic import atomic_json, sha256_file

def commit_pcm_segment(directory: Path, pcm: bytes, *, sample_rate=16000, channels=1) -> Path:
    if sample_rate < 8000 or channels < 1 or not pcm or len(pcm) % (2 * channels):
        raise ValueError("INVALID_PCM16_FRAMES")
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "segments.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"version": 1, "segments": []}
    final = directory / (uuid.uuid4().hex + ".wav")
    partial = final.with_suffix(".partial")
    with partial.open("xb") as stream:
        with wave.open(stream, "wb") as output:
            output.setnchannels(channels)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(pcm)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(partial, final)
    manifest["segments"].append({"path": final.name, "sha256": sha256_file(final), "frames": len(pcm) // (2 * channels)})
    atomic_json(manifest_path, manifest)
    return final

def inspect_recovery(directory: Path) -> dict:
    manifest_path = directory / "segments.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"segments": []}
    valid, damaged, known = [], [], set()
    for item in manifest["segments"]:
        path = (directory / item["path"]).resolve()
        if not path.is_relative_to(directory.resolve()) or path.parent != directory.resolve():
            raise ValueError("UNSAFE_SEGMENT_PATH")
        known.add(path.name)
        (valid if path.is_file() and sha256_file(path) == item["sha256"] else damaged).append(path.name)
    return {"valid": valid, "damaged": damaged,
            "orphans": sorted(p.name for p in directory.glob("*.wav") if p.name not in known),
            "partial": sorted(p.name for p in directory.glob("*.partial"))}
