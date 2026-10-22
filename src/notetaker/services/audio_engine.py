"""Audio engine policy. No model download, hidden fallback, or person identification."""
import json
import math
from pathlib import Path
from notetaker.infrastructure.atomic import atomic_json
from notetaker.infrastructure.models import verify_assets
from notetaker.infrastructure.paths import resource_root
from notetaker.infrastructure.process import run_worker, JobCancelled

MODES = {"auto", "cpu", "gpu"}
# Conservative admission threshold, not a promise that any workload will fit.
MIN_FREE_VRAM = 8 * 1024**3
GPU_DIAGNOSTICS = {
    'GPU_RUNTIME_MISSING': 'L’environnement GPU local est absent.',
    'GPU_MODEL_INTEGRITY_FAILED': 'Un modèle GPU est absent ou son intégrité ne correspond plus au manifeste.',
    'GPU_RUNTIME_VERSION_MISMATCH': 'Les versions des bibliothèques GPU ne correspondent pas à celles qualifiées.',
    'GPU_CUDA_UNAVAILABLE': 'CUDA ne peut pas être initialisé par les bibliothèques de traitement.',
    'GPU_FLOAT16_UNAVAILABLE': 'Le calcul CUDA float16 requis est indisponible.',
    'GPU_MEMORY_INSUFFICIENT': 'La mémoire GPU libre est inférieure au seuil prudent de 8 Gio.',
    'GPU_OUT_OF_MEMORY': 'La mémoire GPU a été épuisée pendant le traitement.',
    'GPU_INVALID_DIARIZATION_OUTPUT': 'La sortie de diarisation GPU est incohérente.',
    'GPU_INVALID_WORKER_RESPONSE': 'La réponse du processus GPU est inexploitable.',
}


class GPUUnavailable(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__("GPU_AUDIO_UNAVAILABLE:" + code)


def read_mode(data_root):
    path = Path(data_root) / "audio-settings.json"
    if not path.exists():
        return "auto"
    try:
        mode = json.loads(path.read_text(encoding="utf-8"))["mode"]
        return mode if mode in MODES else "cpu"
    except (ValueError, KeyError, TypeError):
        return "cpu"


def save_mode(data_root, mode):
    if mode not in MODES:
        raise ValueError("INVALID_ENGINE_MODE")
    atomic_json(Path(data_root) / "audio-settings.json", {"version": 1, "mode": mode})


class GPUAudio:
    def __init__(self, root=None):
        self.root = Path(root or resource_root()).resolve()
        packaged = self.root / "runtimes/audio-gpu/python.exe"
        self.python = packaged if packaged.is_file() else self.root / ".venv-lab-b/Scripts/python.exe"
        self.large = self.root / "models/audio-lab/large"
        self.community = self.root / "models/audio-lab/community"

    def verify(self):
        if not self.python.is_file():
            raise GPUUnavailable("GPU_RUNTIME_MISSING")
        try:
            manifest = json.loads((self.root / "gpu_audio_manifest.json").read_text(encoding="utf-8"))
            verify_assets(self.root, manifest["assets"])
        except (OSError, ValueError, KeyError) as error:
            raise GPUUnavailable("GPU_MODEL_INTEGRITY_FAILED") from error

    def run(self, workspace, task, cancel):
        request = {"task": task, "large": str(self.large), "community": str(self.community),
                   "min_free_vram": MIN_FREE_VRAM}
        if task != "preflight":
            request["audio"] = str(workspace / "normalized.wav")
        path = workspace / ("gpu-" + task + ".request.json")
        atomic_json(path, request)
        try:
            response = run_worker(path, python=self.python, module="notetaker.workers.gpu_audio",
                                  cancel=cancel, timeout=180 if task == "preflight" else 7200)
        except JobCancelled:
            raise
        except (RuntimeError, OSError, TimeoutError) as error:
            code = str(error)
            # Only machine codes cross into the UI, never native exception text.
            raise GPUUnavailable(code if code.startswith("GPU_") else type(error).__name__) from error
        if not isinstance(response.get('result'), dict):
            raise GPUUnavailable('GPU_INVALID_WORKER_RESPONSE')
        atomic_json(path.with_suffix(".result.json"), response)
        return response["result"]


def select_engine(mode, gpu, workspace, cancel, progress):
    if mode not in MODES:
        raise ValueError("INVALID_ENGINE_MODE")
    if mode == "cpu":
        return {"device": "cpu", "selected": mode, "reason": "CPU_REQUESTED"}
    progress("Vérification réelle CUDA, mémoire libre et intégrité des modèles GPU")
    try:
        gpu.verify()
        probe = gpu.run(workspace, "preflight", cancel)
        return {"device": "cuda", "selected": mode, "probe": probe}
    except GPUUnavailable as error:
        if mode == "gpu":
            raise
        progress('Mode automatique : ' + GPU_DIAGNOSTICS.get(error.code, 'GPU indisponible (' + error.code + ').') + ' Small + sherpa sur CPU.')
        return {"device": "cpu", "selected": mode, "reason": error.code}


def community_data(turns):
    """Validate standard (overlapping) turns and derive exact concurrent spans."""
    clean = []
    for t in turns:
        a, b = float(t["start"]), float(t["end"])
        if not math.isfinite(a) or not math.isfinite(b) or a < 0 or b <= a or not isinstance(t["speaker"], str) or not t["speaker"]:
            raise ValueError("GPU_INVALID_TURNS")
        clean.append({"start": a, "end": b, "speaker": t["speaker"]})
    clean.sort(key=lambda t: (t["start"], t["end"], t["speaker"]))
    events = {}
    for t in clean:
        events.setdefault(t["start"], []).append((t["speaker"], 1))
        events.setdefault(t["end"], []).append((t["speaker"], -1))
    active, previous, overlaps = {}, None, []
    for stamp, changes in sorted(events.items()):
        voices = sorted(k for k, v in active.items() if v > 0)
        if previous is not None and stamp > previous and len(voices) > 1:
            overlaps.append({"start": previous, "end": stamp, "speakers": voices})
        for voice, delta in changes:
            active[voice] = active.get(voice, 0) + delta
        previous = stamp
    return {"turns": clean, "possible_overlaps": overlaps,
            "diagnostics": {"engine": "community-1", "speaker_count_forced": False,
                            "overlap_preserved": True, "confidence_available": False}}


def preserve_simultaneous(rows, diar):
    for row in rows:
        source = row["source"]
        source["diarization_engine"] = "community-1"
        source["diarization_turns"] = [t for t in diar["turns"]
            if t["start"] * 1000 < row["end_ms"] and t["end"] * 1000 > row["start_ms"]]
        simultaneous = [o for o in diar["possible_overlaps"]
            if o["start"] * 1000 < row["end_ms"] and o["end"] * 1000 > row["start_ms"]]
        source["simultaneous_turns"] = simultaneous
        if simultaneous:
            # Single-stream ASR cannot decide who said a word in an overlap.
            # Do not duplicate text or force one of the concurrent voices.
            row["speaker_id"] = None
            row["uncertain"] = True
            source["possible_overlap"] = True
    return rows
