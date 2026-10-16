# Python/Qt/native library bundle. Models are copied separately by build.ps1.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root / "src/notetaker/schemas"), "notetaker/schemas")]
binaries = []
hidden = ["notetaker.workers.probe", "notetaker.engines.llama_adapter", "notetaker.engines.overlap", "backports.tarfile"]
for package in ("faster_whisper", "sherpa_onnx"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hidden += h
binaries += collect_dynamic_libs("onnxruntime")
for package in ("ctranslate2", "faster-whisper", "sherpa-onnx", "sherpa-onnx-core"):
    datas += copy_metadata(package)
a = Analysis([str(root / "packaging/entry.py")], pathex=[str(root / "src")], binaries=binaries, datas=datas,
    hiddenimports=hidden, excludes=["torch", "torchaudio", "pyannote", "pytest", "tkinter",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick"])
# PortAudio's ASIO variant is not part of the audited WASAPI product path.
a.binaries = [entry for entry in a.binaries if "asio" not in entry[0].lower()]
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="NoteTaker", console=False, upx=False)
worker = EXE(pyz, a.scripts, [], exclude_binaries=True, name="NoteTaker-worker", console=True, upx=False)
coll = COLLECT(gui, worker, a.binaries, a.datas, strip=False, upx=False, name="NoteTaker")
