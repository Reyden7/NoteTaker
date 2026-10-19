# Python/Qt/native library bundle. Models are copied separately by build.ps1.
from pathlib import Path
import json
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, copy_metadata

root = Path(SPECPATH).parent
datas = [(str(root / "src/notetaker/schemas"), "notetaker/schemas"), (str(root / "src/notetaker/assets"), "notetaker/assets")]
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
    hiddenimports=hidden, excludes=["torch", "torchaudio", "pyannote", "pytest", "tkinter", "onnx",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick"])
# Desktop Widgets needs neither PortAudio ASIO nor the GPL/commercial-only
# optional Virtual Keyboard plugin accidentally collected through Qt hooks.
a.binaries = [entry for entry in a.binaries if not any(token in entry[0].lower() for token in ("asio", "virtualkeyboard"))]
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="NoteTaker", console=False, upx=False)
worker = EXE(pyz, a.scripts, [], exclude_binaries=True, name="NoteTaker-worker", console=True, upx=False)
if os.environ.get('NOTETAKER_DEV_EXECUTABLES_ONLY') == '1':
    # The development assembler verifies and hardlinks identical payload files.
    # Default builds retain ordinary COLLECT behavior.
    (Path(workpath) / 'development-payload.json').write_text(
        json.dumps(list(a.binaries) + list(a.datas), ensure_ascii=False), encoding='utf-8')
else:
    coll = COLLECT(gui, worker, a.binaries, a.datas, strip=False, upx=False, name="NoteTaker")
