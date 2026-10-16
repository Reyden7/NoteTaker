"""Local metadata and packaged-license inventory, not a complete binary SBOM."""
import hashlib
import importlib.metadata as metadata
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
profile = sys.argv[1] if len(sys.argv) > 1 else "asr"
if profile not in {"asr", "diarization"}:
    raise SystemExit("Unknown evidence profile")
out = ROOT / "docs/evidence"
notices = ROOT / "third_party" / profile
components = []
for dist in metadata.distributions():
    name = dist.metadata["Name"]
    copied = []
    for file in dist.files or []:
        if not any(part.endswith(".dist-info") for part in file.parts):
            continue
        if not any(token in file.as_posix().lower() for token in ["license", "copying", "notice"]):
            continue
        source = Path(dist.locate_file(file))
        if not source.is_file():
            continue
        destination = notices / name / Path(*file.parts[1:])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        copied.append(destination.relative_to(ROOT).as_posix())
    components.append({"name": name, "version": dist.version,
                       "license": dist.metadata.get("License-Expression") or dist.metadata.get("License"),
                       "packaged_notices": copied})
(out / f"dependencies-{profile}.json").write_text(json.dumps({"python": platform.python_version(),
    "platform": platform.platform(), "components": sorted(components, key=lambda c: c["name"].lower())}, ensure_ascii=False, indent=2), encoding="utf-8")
if profile == "asr":
    import psutil
    import av
    (out / "pyav-library-meta.json").write_text(json.dumps(av._core.library_meta, indent=2), encoding="utf-8")
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=10)
    hardware = {"platform": platform.platform(), "processor": platform.processor(), "ram_bytes": psutil.virtual_memory().total,
                "logical_cpus": psutil.cpu_count(), "gpu_inventory_only": gpu.stdout.strip(),
                "gpu_command_exit": gpu.returncode, "free_disk_bytes": psutil.disk_usage(str(ROOT)).free}
    (out / "hardware.json").write_text(json.dumps(hardware, indent=2), encoding="utf-8")
print(f"Recorded {len(components)} distributions for {profile}; packaged notices copied, audit still incomplete.")
