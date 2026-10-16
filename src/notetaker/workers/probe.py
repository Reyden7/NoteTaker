"""Real phase 0 probes. Artifacts are local; missing dependencies fail explicitly."""
import json
import sys
import time
from pathlib import Path
from notetaker.infrastructure.offline import enforce_offline, local_path, deny_python_network

enforce_offline()
NETWORK_ATTEMPTS = deny_python_network()

def transcribe(request):
    from faster_whisper import WhisperModel
    audio = local_path(request["audio"])
    model = local_path(request["model"], directory=True)
    device = request.get("device", "cpu")
    engine = WhisperModel(str(model), device=device,
                          compute_type="int8" if device == "cpu" else "float16",
                          cpu_threads=4, num_workers=1, local_files_only=True)
    segments, info = engine.transcribe(str(audio), language="fr", beam_size=5,
                                       vad_filter=False, word_timestamps=True)
    return {"language": info.language, "duration_seconds": info.duration,
            "segments": [{"id": f"s{i}", "start": s.start, "end": s.end, "text": s.text,
                           "avg_logprob": s.avg_logprob, "no_speech_prob": s.no_speech_prob}
                          for i, s in enumerate(segments)]}

def diarize(request):
    # Check model BEFORE importing Torch, and never accept a hub ID.
    model = local_path(request["model"], directory=True)
    audio = local_path(request["audio"])
    import torch
    import wave
    import numpy as np
    from pyannote.audio import Pipeline
    with wave.open(str(audio), "rb") as source:
        if (source.getsampwidth(), source.getnchannels(), source.getframerate()) != (2, 1, 16000):
            raise ValueError("PCM16_MONO_16000_REQUIRED")
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").astype(np.float32) / 32768
    pipeline = Pipeline.from_pretrained(str(model))
    pipeline.to(torch.device(request.get("device", "cpu")))
    output = pipeline({"waveform": torch.from_numpy(samples[None, :]), "sample_rate": 16000})
    return {"turns": [{"start": t.start, "end": t.end, "speaker": s}
                       for t, s in output.speaker_diarization]}

def diarize_sherpa(request):
    segmentation = local_path(request["segmentation"])
    embedding = local_path(request["embedding"])
    audio = local_path(request["audio"])
    # The audited Windows wheel is CPU only. Never silently claim CUDA use.
    if request.get("device", "cpu") != "cpu":
        raise RuntimeError("SHERPA_GPU_NOT_QUALIFIED")
    import numpy as np
    import wave
    import sherpa_onnx as s
    config = s.OfflineSpeakerDiarizationConfig(
        segmentation=s.OfflineSpeakerSegmentationModelConfig(
            pyannote=s.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(segmentation)),
            num_threads=4, provider="cpu"),
        embedding=s.SpeakerEmbeddingExtractorConfig(model=str(embedding), num_threads=4, provider="cpu"),
        clustering=s.FastClusteringConfig(num_clusters=-1, threshold=0.5))
    if not config.validate():
        raise RuntimeError("INVALID_SHERPA_CONFIG")
    engine = s.OfflineSpeakerDiarization(config)
    with wave.open(str(audio), "rb") as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, engine.sample_rate):
            raise ValueError("PCM16_MONO_16000_REQUIRED")
        samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32) / 32768
    output = engine.process(samples).sort_by_start_time()
    return {"turns": [{"start": t.start, "end": t.end, "speaker": f"speaker_{t.speaker}"} for t in output],
            "clustering": "automatic-threshold-0.5", "device": "cpu"}

def main():
    start = time.perf_counter()
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        kind = request["engine"]
        result = {"asr": transcribe, "diarization": diarize, "diarization-sherpa": diarize_sherpa}[kind](request)
        response = {"status": "completed", "engine": kind, "result": result}
    except Exception as exc:
        response = {"status": "failed", "error_code": type(exc).__name__}
    response["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    response["python_network_attempts"] = len(NETWORK_ATTEMPTS)
    print(json.dumps(response, ensure_ascii=False))
    return 0 if response["status"] == "completed" else 2

if __name__ == "__main__":
    raise SystemExit(main())
