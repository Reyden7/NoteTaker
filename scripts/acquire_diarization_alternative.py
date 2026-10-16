"""Explicit build acquisition of publicly redistributed MIT/Apache ONNX models."""
import hashlib
import json
import tarfile
from pathlib import Path
from acquire_phase0 import ROOT, download

meta = json.loads((ROOT / "docs/evidence/diarization-alternative-upstream.json").read_text())
dest = ROOT / "models/diarization/sherpa"
dest.mkdir(parents=True, exist_ok=True)
records = []
PINNED = {
    "sherpa-onnx-pyannote-segmentation-3-0.tar.bz2": "24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488",
    "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx": "1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b",
}
for group, filename in [
    ("sherpa-segmentation", "sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"),
    ("sherpa-embedding", "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"),
]:
    asset = next(a for a in meta[group]["assets"] if a["name"] == filename)
    path = dest / filename
    expected = (asset.get("digest") or "").removeprefix("sha256:") or None
    download(asset["browser_download_url"], path, expected or PINNED[filename])
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    records.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest,
                    "upstream_sha256": expected, "asset_id": asset["id"], "size_bytes": path.stat().st_size,
                    "url": asset["browser_download_url"], "updated_at": asset["updated_at"]})
    if filename.endswith(".bz2"):
        with tarfile.open(path) as archive:
            archive.extractall(dest, filter="data")
all_files = []
for path in sorted(dest.rglob("*")):
    if path.is_file():
        with path.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        all_files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest,
                          "size_bytes": path.stat().st_size, "redistribution": "pending-notices"})
manifest = {"status": "development-only", "archives": records, "assets": all_files,
            "embedding_license_source": "https://modelscope.cn/models/iic/speech_eres2net_base_sv_zh-cn_3dspeaker_16k/resolve/master/README.md"}
(ROOT / "diarization_models_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(records, indent=2))
