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
                                       vad_filter=True, word_timestamps=True)
    return {"language": info.language, "duration_seconds": info.duration,
            "segments": [{"id": f"s{i}", "start": s.start, "end": s.end, "text": s.text,
                           "words": [{"start": w.start, "end": w.end, "word": w.word, "probability": w.probability} for w in (s.words or [])],
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
    from notetaker.engines.overlap import possible_overlaps
    result = {"turns": [{"start": t.start, "end": t.end, "speaker": f"speaker_{t.speaker}"} for t in output],
            "clustering": "automatic-threshold-0.5", "device": "cpu",
            "possible_overlaps": possible_overlaps(samples, segmentation) if request.get("overlap", False) else []}
    if request.get("speaker_strategy", "clean-anchors") == "clean-anchors":
        from notetaker.engines.speaker_refinement import extract_observations, assign_observations
        refinement_model = local_path(request.get("refinement_embedding", str(embedding)))
        observations, vectors = extract_observations(samples, result["turns"], refinement_model, result["possible_overlaps"])
        is_wespeaker = "wespeaker" in str(refinement_model).lower()
        refined = assign_observations(observations, vectors, threshold=0.4 if is_wespeaker else 0.5, linkage="complete" if is_wespeaker else "average")
        refined["diagnostics"]["embedding_model"] = refinement_model.name
        refined["possible_overlaps"] = result["possible_overlaps"]
        refined["diagnostics"]["initial_sherpa_speakers"] = len({t["speaker"] for t in result["turns"]})
        return refined
    return result

def main():
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    start = time.perf_counter()
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        kind = request["engine"]
        from notetaker.engines.llama_adapter import select_sources
        from notetaker.engines.hierarchical_summary import summarize
        result = {"asr": transcribe, "diarization": diarize, "diarization-sherpa": diarize_sherpa,
                  "llm": summarize if request.get("task") == "summary" else select_sources}[kind](request)
        response = {"status": "completed", "engine": kind, "result": result}
    except Exception as exc:
        import re
        code = str(exc)
        response = {"status": "failed", "error_code": code if re.fullmatch(r"[A-Z][A-Z0-9_]*(?: U\+[0-9A-F,+ U]+)?", code) else type(exc).__name__}
    response["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    response["python_network_attempts"] = len(NETWORK_ATTEMPTS)
    # ASCII JSON remains lossless even when a frozen Windows interpreter ignores
    # PYTHONIOENCODING. Never send locale-encoded French through a UTF-8 pipe.
    print(json.dumps(response, ensure_ascii=True))
    return 0 if response["status"] == "completed" else 2

if __name__ == "__main__":
    raise SystemExit(main())
