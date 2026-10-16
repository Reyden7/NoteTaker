import argparse
import json
from pathlib import Path
from .infrastructure.offline import enforce_offline

def main():
    enforce_offline()
    parser = argparse.ArgumentParser(description="NoteTaker — outils techniques de phase 0")
    parser.add_argument("command", choices=["gui", "verify-models"], nargs="?", default="gui")
    parser.add_argument("--manifest", type=Path, default=Path("models_manifest.json"))
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        import sys
        from .workers.probe import main as worker_main
        sys.argv = [sys.argv[0], str(args.worker)]
        return worker_main()
    if args.command == "gui":
        import sys
        from PySide6.QtWidgets import QApplication, QMessageBox
        from PySide6.QtCore import QLockFile
        from .infrastructure.paths import default_data_root
        from .ui.window import MainWindow
        root = (args.data_dir or default_data_root()).resolve()
        root.mkdir(parents=True, exist_ok=True)
        app = QApplication(sys.argv[:1])
        app.setApplicationName("NoteTaker")
        app.setOrganizationName("NoteTaker")
        app.setStyle("Fusion")
        lock = QLockFile(str(root / "application.lock"))
        if not lock.tryLock(0):
            QMessageBox.warning(None, "NoteTaker déjà ouvert", "Une autre instance utilise déjà ce dossier de séances.")
            return 1
        def report(exc_type, value, tb):
            from .ui.window import explain_error
            QMessageBox.warning(app.activeWindow(), "Action non effectuée", explain_error(value))
        sys.excepthook = report
        window = MainWindow(root)
        window.show()
        result = app.exec()
        lock.unlock()
        return result
    from .infrastructure.models import verify_assets
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    verify_assets(args.manifest.resolve().parent, manifest["assets"])
    print("Intégrité des fichiers de développement vérifiée. Distribution non approuvée.")

if __name__ == "__main__":
    raise SystemExit(main())
