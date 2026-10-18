import os
import sys
from pathlib import Path

def resource_root() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[3]

def default_data_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "NoteTaker"

def session_directory(root: Path, session_id: str) -> Path:
    import uuid
    if str(uuid.UUID(session_id)) != session_id:
        raise ValueError("INVALID_SESSION_ID")
    directory = root / "sessions" / session_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory

class ModelPaths:
    def __init__(self, root: Path | None = None):
        self.root = root or resource_root()
        self.asr = self.root / "models/asr/small"
        self.segmentation = self.root / "models/diarization/sherpa/sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
        self.embedding = self.root / "models/diarization/sherpa/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
        self.refinement_embedding = self.root / "models/diarization/wespeaker/voxceleb_resnet34-sherpa.onnx"
        self.llm = self.root / "models/llm/qwen3-4b-instruct-2507/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
        self.llama = self.root / "runtimes/llama-cpu-b11681/llama-completion.exe"

    def verify(self):
        import json
        from .models import verify_assets
        for name in ("models_manifest.json", "diarization_models_manifest.json"):
            manifest = json.loads((self.root / name).read_text(encoding="utf-8"))
            verify_assets(self.root, manifest["assets"])
        if not self.llama.is_file():
            raise FileNotFoundError("LLAMA_CPU_MISSING")
