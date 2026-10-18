"""Explicit build acquisition: official model card/weights and OFL font files."""
import hashlib
import json
import urllib.request
from pathlib import Path
from acquire_phase0 import download, ROOT


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "NoteTaker-quality-audit"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


evidence = ROOT / "docs/evidence"
PINNED_REVISION = "ff1ac5bca8ef11e90662b879aa923979e0bd277b"
meta = json.loads(get(f"https://huggingface.co/api/models/Wespeaker/wespeaker-voxceleb-resnet34/revision/{PINNED_REVISION}?blobs=true"))
if meta.get("cardData", {}).get("license") != "apache-2.0":
    raise ValueError("MODEL_LICENSE_NOT_EXPECTED")
revision = meta["sha"]
if revision != PINNED_REVISION:
    raise ValueError("UNEXPECTED_MODEL_REVISION")
asset = next(a for a in meta["siblings"] if a["rfilename"] == "voxceleb_resnet34.onnx")
expected = asset["lfs"]["sha256"]
model_url = f"https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34/resolve/{revision}/voxceleb_resnet34.onnx"
model_path = ROOT / "models/diarization/wespeaker/voxceleb_resnet34.onnx"
download(model_url, model_path, expected)
(evidence / "wespeaker-upstream.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
card_url = f"https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34/raw/{revision}/README.md"
(evidence / "wespeaker-model-card.md").write_bytes(get(card_url))
records = [{"path": model_path.relative_to(ROOT).as_posix(), "sha256": expected,
            "revision": revision, "url": model_url, "license": "Apache-2.0", "redistribution": "pending-notices"}]
# Metadata adapter described by sherpa 1.13.8. Original weights remain intact.
import onnx
adapted = model_path.with_name("voxceleb_resnet34-sherpa.onnx")
graph = onnx.load(str(model_path))
properties = {"framework": "wespeaker", "language": "English", "sample_rate": "16000", "output_dim": "256",
              "normalize_samples": "0", "url": model_url, "comment": "NoteTaker: metadata only, network weights unchanged"}
for key, value in properties.items():
    prop = graph.metadata_props.add()
    prop.key, prop.value = key, value
onnx.save(graph, str(adapted))
records.append({"path": adapted.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(adapted.read_bytes()).hexdigest(),
                "derived_from_sha256": expected, "modification": "sherpa-compatible metadata only; weights unchanged",
                "license": "Apache-2.0", "redistribution": "pending-notices"})
font_revision = "ffebf8c1ee449e544955a7e813c54f9b73848eac"
folder = ROOT / "src/notetaker/assets/fonts"
folder.mkdir(parents=True, exist_ok=True)
for name in ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf", "LICENSE"):
    relative = "LICENSE" if name == "LICENSE" else "hinted/ttf/NotoSans/" + name
    url = f"https://raw.githubusercontent.com/notofonts/noto-fonts/{font_revision}/{relative}"
    content = get(url)
    (folder / name).write_bytes(content)
    records.append({"path": (folder / name).relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(content).hexdigest(),
                    "revision": font_revision, "url": url, "license": "OFL-1.1"})
(evidence / "quality-assets.json").write_text(json.dumps({"assets": records}, indent=2), encoding="utf-8")
manifest_path = ROOT / "diarization_models_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["assets"] = [a for a in manifest["assets"] if "/wespeaker/" not in a["path"]]
adapted_record = next(r for r in records if r["path"].endswith("-sherpa.onnx"))
manifest["assets"].append({**adapted_record, "size_bytes": adapted.stat().st_size})
manifest["refinement_embedding_license_source"] = card_url
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("Downloaded official WeSpeaker weights with upstream hash and Noto Sans OFL font files; see quality-assets.json")
