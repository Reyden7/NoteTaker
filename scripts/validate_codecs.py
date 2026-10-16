"""Encode existing synthetic fixture, then exercise actual import/decode paths."""
import json
import sys
import wave
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import av
from notetaker.services.audio import import_audio, prepare_audio
from notetaker.infrastructure.atomic import atomic_json, sha256_file
source = ROOT / "output/phase0/fr-synthetic.wav"
directory = ROOT / "output/codec-validation"
directory.mkdir(exist_ok=True)
results = {}
for suffix, codec in [("wav", None), ("mp3", "libmp3lame"), ("m4a", "aac")]:
    path = source if codec is None else directory / ("fixture." + suffix)
    if codec:
        with av.open(str(source)) as original, av.open(str(path), "w") as target:
            stream = target.add_stream(codec, rate=16000)
            stream.layout = "mono"
            resampler = av.AudioResampler(format=stream.codec_context.format.name, layout="mono", rate=16000)
            for frame in original.decode(audio=0):
                for converted in resampler.resample(frame):
                    for packet in stream.encode(converted):
                        target.mux(packet)
            for converted in resampler.resample(None):
                for packet in stream.encode(converted):
                    target.mux(packet)
            for packet in stream.encode(None):
                target.mux(packet)
    copied, digest = import_audio(path, directory)
    normalized = prepare_audio([{"kind": "import", "path": str(copied), "sha256": digest}], directory / ("decoded-" + suffix + ".wav"))
    with wave.open(str(normalized)) as audio:
        results[suffix] = {"original_preserved": sha256_file(path) == digest, "sample_rate": audio.getframerate(),
                           "channels": audio.getnchannels(), "frames": audio.getnframes(), "duration_seconds": audio.getnframes() / audio.getframerate()}
    assert results[suffix]["original_preserved"] and results[suffix]["duration_seconds"] > 10
atomic_json(ROOT / "docs/evidence/codec-validation.json", results)
print(json.dumps(results, indent=2))
