"""Real two-voice synthetic diarization probe, automatic clustering, no identities."""
import json
import sys
import wave
from pathlib import Path
from run_phase0_probes import ROOT, OUT, EVIDENCE, measured
from notetaker.engines.router import run_with_fallback
from notetaker.infrastructure.atomic import atomic_json
from notetaker.infrastructure.models import verify_assets

def main():
    manifest = json.loads((ROOT / "diarization_models_manifest.json").read_text())
    verify_assets(ROOT, manifest["assets"])
    audio = OUT / "two-synthetic-voices.wav"
    truth = []
    position = 0
    with wave.open(str(audio), "wb") as target:
        target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        for index in [0, 1, 0, 1]:
            with wave.open(str(OUT / f"voice-{index}.wav"), "rb") as source:
                assert (source.getnchannels(), source.getsampwidth(), source.getframerate()) == (1, 2, 16000)
                data = source.readframes(source.getnframes())
            duration = len(data) / 32000
            truth.append({"start": position, "end": position + duration, "synthetic_voice": index})
            target.writeframes(data)
            target.writeframes(b"\0\0" * 16000)
            position += duration + 1
    results = {"fixture": "four alternating turns, two installed synthetic voices, no overlap", "duration_seconds": position,
               "truth": truth, "attempts": {}, "quality_scope": "Smoke test only; not French field DER; embeddings trained on Chinese speech",
               "network_validation": "Python socket audit guard only; native network not captured"}
    def attempt(device):
        request = OUT / f"sherpa-{device}.request.json"
        atomic_json(request, {"engine": "diarization-sherpa", "device": device, "audio": str(audio),
                     "segmentation": str(ROOT / "models/diarization/sherpa/sherpa-onnx-pyannote-segmentation-3-0/model.onnx"),
                     "embedding": str(ROOT / "models/diarization/sherpa/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx")})
        data = measured([sys.executable, "-m", "notetaker.workers.probe", request], f"sherpa-{device}")
        data["response"] = json.loads((ROOT / data["stdout"]).read_text(encoding="utf-8"))
        results["attempts"][device] = data
        if data["returncode"] != 0:
            raise RuntimeError("DIARIZATION_PROBE_FAILED")
        return data
    routed = run_with_fallback(attempt)
    turns = routed.value["response"]["result"]["turns"]
    results["selected_device"] = routed.device
    results["detected_speakers"] = len({t["speaker"] for t in turns})
    majorities = []
    for expected in truth:
        overlap = {}
        for turn in turns:
            common = max(0, min(turn["end"], expected["end"]) - max(turn["start"], expected["start"]))
            overlap[turn["speaker"]] = overlap.get(turn["speaker"], 0) + common
        majorities.append(max(overlap, key=overlap.get) if overlap else None)
    results["majority_speaker_per_turn"] = majorities
    results["two_voice_smoke_passed"] = bool(len(majorities) == 4 and None not in majorities and majorities[0] == majorities[2] and majorities[1] == majorities[3] and majorities[0] != majorities[1])
    atomic_json(EVIDENCE / "diarization-alternative-probe.json", results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["two_voice_smoke_passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
