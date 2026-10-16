"""Render the actual PySide6 widgets using the real isolated validation database."""
import json
import os
import sys
from pathlib import Path
os.environ["QT_QPA_PLATFORM"] = "windows" if os.name == "nt" else "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from PySide6.QtWidgets import QApplication
from notetaker.ui.window import MainWindow
report = json.loads((ROOT / "docs/evidence/application-chain.json").read_text(encoding="utf-8"))
app = QApplication([])
window = MainWindow(report["data_directory"])
window.sid = report["session_id"]
window.reload_history()
window.load_session()
window.ensurePolished()
destination = ROOT / "output/ui-validation"
destination.mkdir(exist_ok=True)
for index, name in [(0, "session"), (1, "audio"), (2, "transcript"), (3, "minutes"), (4, "votes")]:
    window.tabs.setCurrentIndex(index)
    if index == 2 and window.transcript_table.rowCount():
        window.transcript_table.selectRow(0)
    app.processEvents()
    if not window.grab().save(str(destination / (name + ".png"))):
        raise RuntimeError("SCREENSHOT_WRITE_FAILED")
window.close()
print(destination)
