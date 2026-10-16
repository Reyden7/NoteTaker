"""Explicit BUILD-ONLY acquisition of audited public artifacts, never app startup.

No credentials, no gating bypass, no implicit model downloads.
"""
import concurrent.futures
import hashlib
import json
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = json.loads((ROOT / "docs/evidence/upstream-metadata.json").read_text(encoding="utf-8"))

def download(url, dest, expected=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and expected:
        with dest.open("rb") as existing:
            if hashlib.file_digest(existing, "sha256").hexdigest() == expected:
                return
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "NoteTaker-build-phase0"})
    with urllib.request.urlopen(req, timeout=60) as response, part.open("wb") as out:
        shutil.copyfileobj(response, out, 1024 * 1024)
    with part.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if expected and digest != expected:
        raise ValueError("Downloaded file does not match upstream SHA256")
    part.replace(dest)

def model(key, repo, folder, filenames):
    data = META[key]["data"]
    rev = data["sha"]
    assets = []
    for name in filenames:
        entry = next(x for x in data["siblings"] if x["rfilename"] == name)
        expected = entry.get("lfs", {}).get("sha256")
        path = ROOT / folder / name
        url = f"https://huggingface.co/{repo}/resolve/{rev}/{name}"
        download(url, path, expected)
        with path.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        assets.append({"path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size,
                       "sha256": digest, "upstream_sha256": expected, "provenance": url,
                       "revision": rev, "redistribution": "pending-notices",
                       "license": "MIT" if key == "whisper-small" else "Apache-2.0"})
    return assets

def llama():
    releases = json.loads((ROOT / "docs/evidence/llama-releases.json").read_text())
    release = next(r for r in releases if r["tag_name"] == "b11681")
    asset = next(a for a in release["assets"] if a["name"] == "llama-b11681-bin-win-cpu-x64.zip")
    archive = ROOT / ".cache" / asset["name"]
    digest = asset.get("digest", "").removeprefix("sha256:") or None
    download(asset["browser_download_url"], archive, digest)
    dest = ROOT / "runtimes/llama-cpu-b11681"
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = (dest / member.filename).resolve()
            if not target.is_relative_to(dest.resolve()):
                raise ValueError("Unsafe archive")
        zipped.extractall(dest)
    with archive.open("rb") as f:
        checksum = hashlib.file_digest(f, "sha256").hexdigest()
    return {"tag": release["tag_name"], "url": asset["browser_download_url"],
            "archive_sha256": checksum, "upstream_digest": digest,
            "size_bytes": archive.stat().st_size, "redistribution": "pending-notices"}

def gate_probe():
    rev = META["community-1"]["data"]["sha"]
    url = f"https://huggingface.co/pyannote/speaker-diarization-community-1/resolve/{rev}/config.yaml"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return {"http_status": response.status, "acquired": False, "url": url}
    except urllib.error.HTTPError as error:
        return {"http_status": error.code, "acquired": False, "url": url,
                "reason": "Build account must accept upstream conditions; no credentials used."}

if __name__ == "__main__":
    if shutil.disk_usage(ROOT).free < 8 * 1024**3:
        raise SystemExit("At least 8 GiB free required for these development probes")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(model, "whisper-small", "Systran/faster-whisper-small", "models/asr/small", ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "README.md"]),
                pool.submit(model, "qwen-4b", "Qwen/Qwen3-4B-GGUF", "models/llm/qwen3-4b", ["Qwen3-4B-Q4_K_M.gguf", "LICENSE", "README.md"]),
                pool.submit(llama)]
        results = [j.result() for j in jobs]
    manifest = {"schema_version": 1, "status": "development-only", "assets": results[0] + results[1],
                "llama": results[2], "diarization": gate_probe()}
    (ROOT / "models_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(manifest["assets"]), "llama": manifest["llama"], "diarization": manifest["diarization"]}, indent=2))
