"""Compare global speaker clustering using identical cached field observations."""
import json
import argparse
import sys
import time
import wave
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.engines.speaker_refinement import extract_observations, assign_observations
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.atomic import atomic_json, sha256_file

parser = argparse.ArgumentParser()
parser.add_argument('--model', type=Path)
parser.add_argument('--variant', default='eres2net')
args = parser.parse_args()
base_work = ROOT / "output/quality-02"
work = base_work / args.variant
work.mkdir(parents=True, exist_ok=True)
records = json.loads((base_work / "baseline/records.json").read_text(encoding="utf-8"))
jobs = Path(records["audio_take"][0]["path"]).parent.parent / "jobs"
audio = next(jobs.glob("*/normalized.wav"))
baseline = json.loads(next(jobs.glob("*/diarization-sherpa-cpu.request.result.json")).read_text(encoding="utf-8"))["result"]
cache = work / "observations.npz"
if cache.exists():
    vectors = np.load(cache)["vectors"]
    observations = json.loads((work / "observations.json").read_text(encoding="utf-8"))
    extraction = json.loads((work / "extraction.json").read_text(encoding="utf-8"))
else:
    with wave.open(str(audio)) as stream:
        samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32) / 32768
    started = time.perf_counter()
    observations, vectors = extract_observations(samples, baseline["turns"], args.model or ModelPaths().embedding, baseline["possible_overlaps"], print)
    extraction = {"seconds": round(time.perf_counter() - started, 3), "normalized_audio_sha256": sha256_file(audio), "samples": len(samples)}
    np.savez(cache, vectors=vectors)
    atomic_json(work / "observations.json", observations)
    atomic_json(work / "extraction.json", extraction)
results = {"baseline_speakers": 195, "human_reference": "not-available", "extraction": extraction, "variants": {}}
for linkage in ("complete", "average"):
    for threshold in (0.4, 0.5, 0.6, 0.7):
        result = assign_observations(observations, vectors, threshold, linkage)
        key = f"{linkage}-{threshold}"
        results["variants"][key] = result["diagnostics"]
        atomic_json(work / (key + ".json"), result)
        print(key, result["diagnostics"]["speakers"], "uncertain", result["diagnostics"]["uncertain_observations"], flush=True)
atomic_json(ROOT / f"docs/evidence/quality-02-speakers-{args.variant}.json", results)
