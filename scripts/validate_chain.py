"""Real CPU chain on an explicitly supplied fixture; no quality certification.

All output stays in an isolated validation directory. The review test is marked
AUTOMATED TEST and does not represent a human review of a real meeting.
"""
import argparse
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import session_directory
from notetaker.services.storage import SessionStore
from notetaker.services.audio import import_audio
from notetaker.services.pipeline import Pipeline
from notetaker.services.session_export import export_session

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--fixture", action="store_true", help="Permit export-gate fault test on a known non-meeting fixture")
    args = parser.parse_args()
    if (args.data_dir / "notetaker.sqlite3").exists():
        raise SystemExit("Use a fresh isolated data directory for validation")
    store = SessionStore(args.data_dir)
    sid = store.create("Validation technique — données d’essai", {"municipality": "Commune fictive", "date": "2026-10-16", "agenda": ["Travaux de la bibliothèque"]})
    directory = session_directory(store.root, sid)
    path, digest = import_audio(args.audio, directory)
    store.add_take(sid, "import", path, sha256=digest)
    report = {"fixture": args.fixture, "session_id": sid, "input_sha256": digest, "data_directory": str(store.root), "natural_french_three_speakers": "not-validated"}
    pipeline = Pipeline(store.root, progress=lambda message: print(message, flush=True))
    started = time.perf_counter()
    report["analysis"] = pipeline.analyse(sid)
    report["analysis_seconds"] = round(time.perf_counter() - started, 3)
    started = time.perf_counter()
    report["minutes"] = pipeline.generate(sid)
    report["generation_seconds"] = round(time.perf_counter() - started, 3)
    try:
        export_session(store, sid, store.root / "unreviewed.pdf")
    except ValueError:
        report["unreviewed_export_blocked"] = True
    else:
        raise AssertionError("Unreviewed export was not blocked")
    if args.fixture:
        # Test-only explicit gate invocation in isolated non-meeting data, never auto-approved in the app.
        vote = {"id": "test-vote", "title": "Vote fictif saisi par le test", "status": "entered", "for_count": 3,
                "against_count": 1, "abstain_count": 0, "nonparticipating_count": 0, "source": "AUTOMATED TEST FIXTURE"}
        store.save_manual(sid, [vote], ["Décision fictive saisie uniquement pour vérifier l’export"])
        store.save_draft(sid, store.get(sid)["draft"]["content"])
        store.approve(sid, "AUTOMATED TEST FIXTURE — NOT A HUMAN REVIEW")
        for suffix in ["pdf", "docx"]:
            export_session(store, sid, store.root / ("chain-fixture." + suffix))
        report["export_gate_test"] = "automated-fixture-only"
    report["original_intact"] = sha256_file(path) == digest == sha256_file(args.audio)
    reopened = SessionStore(store.root)
    report["reopened"] = bool(reopened.get(sid)["draft"])
    reopened.close()
    atomic_json(ROOT / "docs/evidence/application-chain.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    store.close()

if __name__ == "__main__":
    main()
