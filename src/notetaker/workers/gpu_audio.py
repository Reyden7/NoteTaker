"""Isolated CUDA worker, imported only by the GPU Python runtime."""
import json
import sys
import time
from pathlib import Path
from notetaker.infrastructure.offline import enforce_offline, deny_python_network, local_path


def preflight(request):
    import torch
    import ctranslate2
    from importlib.metadata import version
    expected = {"torch": "2.8.0+cu128", "pyannote.audio": "4.0.7", "ctranslate2": "4.8.3",
                "faster-whisper": "1.2.1", "av": "18.1.0"}
    versions = {name: version(name) for name in expected}
    if versions != expected:
        raise RuntimeError("GPU_RUNTIME_VERSION_MISMATCH")
    if not torch.cuda.is_available() or ctranslate2.get_cuda_device_count() < 1:
        raise RuntimeError("GPU_CUDA_UNAVAILABLE")
    if "float16" not in ctranslate2.get_supported_compute_types("cuda", 0):
        raise RuntimeError("GPU_FLOAT16_UNAVAILABLE")
    # Execute actual CUDA kernels, not a PCI device inventory.
    value = torch.ones((256, 256), device="cuda")
    if (value @ value).sum().item() <= 0:
        raise RuntimeError('GPU_KERNEL_TEST_FAILED')
    del value
    torch.cuda.synchronize()
    torch.cuda.empty_cache()
    free, total = torch.cuda.mem_get_info()
    if free < request["min_free_vram"]:
        raise RuntimeError("GPU_MEMORY_INSUFFICIENT")
    local_path(request["large"], directory=True)
    local_path(request["community"], directory=True)
    return {"device": "cuda", "name": torch.cuda.get_device_name(0), "free_vram_bytes": free,
            "total_vram_bytes": total, "versions": versions, "kernel_test": True}


def transcribe(request):
    import torch  # loads the tested CUDA/cuDNN DLLs before CT2
    from faster_whisper import WhisperModel
    engine = WhisperModel(str(local_path(request["large"], directory=True)), device="cuda",
                          compute_type="float16", cpu_threads=4, num_workers=1, local_files_only=True)
    segments, info = engine.transcribe(str(local_path(request["audio"])), language="fr", beam_size=5,
                                       vad_filter=True, word_timestamps=True)
    rows = [{"id": f"s{i}", "start": s.start, "end": s.end, "text": s.text,
             "words": [{"start": w.start, "end": w.end, "word": w.word, "probability": w.probability}
                       for w in (s.words or [])], "avg_logprob": s.avg_logprob,
             "no_speech_prob": s.no_speech_prob} for i, s in enumerate(segments)]
    del engine
    torch.cuda.synchronize()
    return {"segments": rows, "language": info.language, "duration_seconds": info.duration, "device": "cuda"}


def diarize(request):
    import torch
    import numpy as np
    import wave
    from pyannote.audio import Pipeline
    torch.set_num_threads(4)
    with wave.open(str(local_path(request["audio"])), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 16000):
            raise ValueError("GPU_PCM16_MONO_16000_REQUIRED")
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").astype(np.float32) / 32768
    engine = Pipeline.from_pretrained(str(local_path(request["community"], directory=True)))
    engine.to(torch.device("cuda"))
    output = engine({"waveform": torch.from_numpy(samples[None, :]), "sample_rate": 16000})
    turns = [{"start": float(t.start), "end": float(t.end), "speaker": str(s)}
             for t, s in output.speaker_diarization]
    del engine
    torch.cuda.synchronize()
    return {"turns": turns, "device": "cuda", "exclusive_output_used": False}


def main():
    enforce_offline()
    attempts = deny_python_network()
    import psutil
    import threading
    start, cpu0 = time.perf_counter(), time.process_time()
    peak = [0]
    done = threading.Event()
    def sample():
        while not done.is_set():
            info = psutil.Process().memory_info()
            peak[0] = max(peak[0], getattr(info, "private", info.rss))
            done.wait(.1)
    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        result = {"preflight": preflight, "asr": transcribe, "diarization": diarize}[request["task"]](request)
        response = {"status": "completed", "result": result}
    except Exception as error:
        # No transcript, credential, or exception detail on the pipe.
        code = str(error)
        if "out of memory" in code.lower():
            code = "GPU_OUT_OF_MEMORY"
        elif not code.startswith("GPU_") or not all(c.isupper() or c == "_" or c.isdigit() for c in code):
            code = "GPU_" + type(error).__name__.upper()
        response = {"status": "failed", "error_code": code}
    finally:
        done.set()
        thread.join()
    response["measurement"] = {"elapsed_seconds": time.perf_counter() - start,
        "cpu_seconds": time.process_time() - cpu0, "peak_host_private_bytes_sampled": peak[0],
        "python_network_attempts": len(attempts), "vram_peak_measured": False}
    # Preserve diagnostics even when the parent receives a failure/cancellation.
    from notetaker.infrastructure.atomic import atomic_json
    atomic_json(Path(sys.argv[1]).with_suffix(".worker-result.json"), response)
    print(json.dumps(response, ensure_ascii=True))
    return 0 if response["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
