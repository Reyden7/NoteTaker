"""Preserve imports and derive mono PCM16 without changing any original take."""
import os
import shutil
import uuid
import wave
from pathlib import Path
from notetaker.infrastructure.atomic import sha256_file
from .recording import inspect_capture

def import_audio(source: Path, session_dir: Path):
    source = source.resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in {".wav", ".mp3", ".m4a"}:
        raise ValueError("WAV_MP3_M4A_REQUIRED")
    directory = session_dir / "originals"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (str(uuid.uuid4()) + source.suffix.lower())
    partial = target.with_suffix(target.suffix + ".part")
    before = sha256_file(source)
    with source.open("rb") as src, partial.open("xb") as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
        dst.flush()
        os.fsync(dst.fileno())
    if sha256_file(partial) != before or sha256_file(source) != before:
        raise ValueError("SOURCE_CHANGED_DURING_IMPORT")
    os.replace(partial, target)
    return target, before

def prepare_audio(takes: list[dict], target: Path, progress=lambda stage: None):
    import av
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".wav.part")
    frames_written = 0
    def resample_input(rate, layout):
        return av.AudioResampler(format="s16", layout="mono", rate=16000)
    with partial.open("wb") as disk:
        with wave.open(disk, "wb") as out:
            out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            def emit(frames):
                nonlocal frames_written
                for frame in frames:
                    out.writeframesraw(bytes(frame.planes[0])[:frame.samples * 2])
                    frames_written += frame.samples
            for index, take in enumerate(takes):
                progress(f"Préparation audio {index + 1}/{len(takes)}")
                path = Path(take["path"]).resolve(strict=True)
                if take["kind"] == "import":
                    if sha256_file(path) != take["sha256"]:
                        raise ValueError("ORIGINAL_AUDIO_INTEGRITY_FAILED")
                    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
                    with av.open(str(path)) as container:
                        for decoded in container.decode(audio=0):
                            emit(resampler.resample(decoded))
                    emit(resampler.resample(None))
                else:
                    capture = inspect_capture(path)
                    if capture["integrity_errors"]:
                        raise ValueError("CAPTURE_AUDIO_INTEGRITY_FAILED")
                    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
                    size = capture["channels"] * 2
                    layout = "mono" if capture["channels"] == 1 else "stereo"
                    pts = 0
                    for chunk in capture["chunks"]:
                        with chunk.open("rb") as stream:
                            while data := stream.read(size * 8192):
                                data = data[:len(data) // size * size]
                                if not data:
                                    continue
                                frame = av.AudioFrame(format="s16", layout=layout, samples=len(data) // size)
                                frame.sample_rate = capture["rate"]
                                frame.pts = pts
                                pts += frame.samples
                                frame.planes[0].update(data)
                                emit(resampler.resample(frame))
                    emit(resampler.resample(None))
            if not frames_written:
                raise ValueError("NO_RECOVERABLE_AUDIO")
        disk.flush()
        os.fsync(disk.fileno())
    os.replace(partial, target)
    return target
