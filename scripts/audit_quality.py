"""Read-only audit of a field session; detailed session data stays in output/."""
import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.infrastructure.atomic import atomic_json, sha256_file


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--audio", type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "output/quality-02/baseline")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect((args.data_dir / "notetaker.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    sessions = db.execute("SELECT * FROM session WHERE title=?", (args.title,)).fetchall()
    if len(sessions) != 1:
        raise SystemExit(f"Expected one session, found {len(sessions)}")
    sid = sessions[0]["id"]
    # A consistent backup includes committed WAL, without changing the source DB.
    target = args.output / "baseline.sqlite3"
    if target.exists():
        raise SystemExit("Baseline already exists; use another output directory")
    with sqlite3.connect(target) as backup:
        db.backup(backup)
    records = {name: [dict(row) for row in db.execute(f"SELECT * FROM {name} WHERE session_id=?", (sid,))]
               for name in ("audio_take", "speaker", "utterance", "draft_minutes", "job", "export", "edit_history")}
    db.close()
    atomic_json(args.output / "records.json", {"session": dict(sessions[0]), **records})
    duration = collections.Counter()
    short = collections.Counter()
    for u in records["utterance"]:
        duration[u["speaker_id"]] += (u["end_ms"] - u["start_ms"]) / 1000
        short[u["speaker_id"]] += (u["end_ms"] - u["start_ms"]) < 1000
    drafts = sorted(records["draft_minutes"], key=lambda d: d["revision"])
    content = json.loads(drafts[-1]["content_json"]) if drafts else {"points": [], "to_verify": []}
    import av
    with av.open(str(args.audio)) as audio:
        stream = audio.streams.audio[0]
        original = {"sha256": sha256_file(args.audio), "bytes": args.audio.stat().st_size,
                    "seconds": float(stream.duration * stream.time_base) if stream.duration else None,
                    "channels": stream.codec_context.channels, "rate": stream.codec_context.sample_rate,
                    "codec": stream.codec_context.name}
    pdfs = []
    from pypdf import PdfReader
    for item in records["export"]:
        path = Path(item["path"])
        if path.suffix.lower() == ".pdf" and path.exists():
            pdfs.append({"sha256": sha256_file(path), "pages": len(PdfReader(path).pages), "bytes": path.stat().st_size})
    report = {"session_id": sid, "original": original, "speakers": len(records["speaker"]),
              "utterances": len(records["utterance"]), "uncertain_utterances": sum(u["uncertain"] for u in records["utterance"]),
              "short_utterances_below_1s": sum(short.values()), "speaker_seconds": dict(duration),
              "speakers_below_5s": sum(t < 5 for t in duration.values()),
              "draft_points": len(content["points"]), "draft_characters": sum(len(p["summary"]) for p in content["points"]),
              "verification_alerts": len(content["to_verify"]), "pdfs": pdfs,
              "jobs": [{k: j[k] for k in ("kind", "status", "error_code")} for j in records["job"]]}
    atomic_json(args.output / "statistics.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "speaker_seconds"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
