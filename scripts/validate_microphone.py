"""Short real microphone I/O check; records locally, never transcribes the content."""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.services.recording import input_devices, MicrophoneRecorder, inspect_capture
from notetaker.services.audio import prepare_audio
from notetaker.infrastructure.atomic import atomic_json

parser = argparse.ArgumentParser()
parser.add_argument("--device", type=int, required=True)
parser.add_argument("--seconds", type=int, default=3)
args = parser.parse_args()
if not 1 <= args.seconds <= 1200:
    raise SystemExit("Choose a duration between 1 and 1200 seconds")
device = next(d for d in input_devices() if d["id"] == args.device)
directory = ROOT / "output/microphone-validation" / str(uuid.uuid4())
directory.parent.mkdir(parents=True, exist_ok=True)
recorder = MicrophoneRecorder()
recorder.start(directory, device)
try:
    time.sleep(args.seconds)
finally:
    recorder.stop()
capture = inspect_capture(directory)
normalized = prepare_audio([{"kind": "capture", "path": str(directory)}], directory.parent / (directory.name + ".wav"))
report = {"device": device, "requested_seconds": args.seconds, "captured_frames": capture["recoverable_frames"],
          "sample_rate": capture["rate"], "seconds": capture["recoverable_frames"] / capture["rate"],
          "error_code": recorder.error, "raw_directory": str(directory), "normalized": str(normalized),
          "scope": "real microphone I/O only; not a natural French meeting or speech-quality evaluation"}
atomic_json(ROOT / "docs/evidence/microphone-validation.json", report)
print(json.dumps(report, indent=2))
raise SystemExit(1 if recorder.error or not capture["recoverable_frames"] else 0)
