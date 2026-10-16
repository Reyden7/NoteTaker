import argparse
import json
from pathlib import Path
from .infrastructure.offline import enforce_offline

def main():
    enforce_offline()
    parser = argparse.ArgumentParser(description="NoteTaker — outils techniques de phase 0")
    parser.add_argument("command", choices=["verify-models"])
    parser.add_argument("--manifest", type=Path, default=Path("models_manifest.json"))
    args = parser.parse_args()
    from .infrastructure.models import verify_assets
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    verify_assets(args.manifest.resolve().parent, manifest["assets"])
    print("Intégrité des fichiers de développement vérifiée. Distribution non approuvée.")

if __name__ == "__main__":
    main()
