"""Build/development only: record public upstream metadata; never used by the app."""
import concurrent.futures
import hashlib
import json
import urllib.request
from pathlib import Path

TARGETS = {
    "pyannote-4.0.2": "https://pypi.org/pypi/pyannote.audio/4.0.2/json",
    "pyannote-current": "https://pypi.org/pypi/pyannote.audio/json",
    "torchcodec-0.7.0": "https://pypi.org/pypi/torchcodec/0.7.0/json",
    "torchcodec-current": "https://pypi.org/pypi/torchcodec/json",
    "pyside-6.8.3": "https://pypi.org/pypi/PySide6/6.8.3/json",
    "whisper-small": "https://huggingface.co/api/models/Systran/faster-whisper-small?blobs=true",
    "qwen-4b": "https://huggingface.co/api/models/Qwen/Qwen3-4B-GGUF?blobs=true",
    "community-1": "https://huggingface.co/api/models/pyannote/speaker-diarization-community-1?blobs=true",
    "llama-releases": "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest",
}

def fetch(item):
    name, url = item
    req = urllib.request.Request(url, headers={"User-Agent": "NoteTaker-phase0-audit"})
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            raw = response.read()
        data = json.loads(raw)
        return name, {"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "data": data}
    except Exception as exc:
        return name, {"url": url, "error": str(exc)}

if __name__ == "__main__":
    out = Path("docs/evidence/upstream-metadata.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        result = dict(pool.map(fetch, TARGETS.items()))
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, entry in result.items():
        d = entry.get("data", {})
        info = d.get("info", {})
        print(name, entry.get("error") or info.get("version") or d.get("sha") or d.get("tag_name"))
        if info:
            print("Python:", info.get("requires_python"), "Windows wheels:", [x["filename"] for x in d.get("urls", []) if "win_amd64" in x["filename"]][:3])
            if "pyannote" in name:
                print(info.get("requires_dist"))
        elif "siblings" in d:
            print([(x["rfilename"], x.get("size")) for x in d["siblings"]])
        elif "assets" in d:
            print([(a["name"], a["size"]) for a in d["assets"] if "win-cpu-x64" in a["name"]])
