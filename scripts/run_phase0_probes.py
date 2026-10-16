"""Real, repeatable CPU and GPU-attempt probes with saved measurements.

Only the synthetic fixture is used. No microphone recording or field evaluation.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.infrastructure.atomic import atomic_json
from notetaker.infrastructure.offline import OFFLINE_ENV
from notetaker.domain.minutes import validate_minutes
from notetaker.engines.router import run_with_fallback

OUT = ROOT / "output/phase0"
EVIDENCE = ROOT / "docs/evidence"
OUT.mkdir(parents=True, exist_ok=True)

def measured(command, name, timeout=180):
    env = dict(os.environ, **OFFLINE_ENV)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    stdout, stderr = OUT / (name + ".stdout.txt"), OUT / (name + ".stderr.txt")
    start = time.perf_counter()
    peak = 0
    with stdout.open("wb") as out, stderr.open("wb") as err:
        process = subprocess.Popen([str(x) for x in command], env=env, stdout=out, stderr=err)
        monitored = psutil.Process(process.pid)
        timed_out = False
        while process.poll() is None:
            try:
                processes = [monitored, *monitored.children(recursive=True)]
                peak = max(peak, sum(p.memory_info().rss for p in processes if p.is_running()))
            except psutil.NoSuchProcess:
                pass
            if time.perf_counter() - start > timeout:
                process.kill()
                timed_out = True
                break
            time.sleep(0.05)
        process.wait()
    return {"returncode": process.returncode, "timeout": timed_out,
            "wall_seconds": round(time.perf_counter() - start, 3),
            "peak_aggregate_rss_bytes": peak, "stdout": stdout.relative_to(ROOT).as_posix(),
            "stderr": stderr.relative_to(ROOT).as_posix()}

def main():
    results = {"fixture_kind": "synthetic-french-speech", "cpu_threads": 4,
               "network_validation": "Python audit hook for ASR only; native traffic not audited; host not disconnected",
               "hardware": {"ram_bytes": psutil.virtual_memory().total, "logical_cpus": psutil.cpu_count(), "free_disk_bytes": psutil.disk_usage(str(ROOT)).free}}
    audio = OUT / "fr-synthetic.wav"
    if not audio.exists():
        raise SystemExit("Create synthetic fixture explicitly first")
    results["asr"] = {}
    def asr_attempt(device):
        request = OUT / ("asr-" + device + ".request.json")
        atomic_json(request, {"engine": "asr", "device": device, "audio": str(audio), "model": str(ROOT / "models/asr/small")})
        data = measured([sys.executable, "-m", "notetaker.workers.probe", request], "asr-" + device)
        try:
            data["response"] = json.loads((ROOT / data["stdout"]).read_text(encoding="utf-8"))
        except ValueError:
            data["response"] = {"status": "native-crash-or-invalid-output"}
        results["asr"][device] = data
        atomic_json(EVIDENCE / "phase0-probes.json", results)
        if data["returncode"] != 0 or data["response"].get("status") != "completed":
            raise RuntimeError("REPRESENTATIVE_ASR_TASK_FAILED")
        return data
    routed = run_with_fallback(asr_attempt)
    results["asr_selected_device"] = routed.device
    results["asr_routing_attempts"] = [a.__dict__ for a in routed.attempts]
    if "cpu" not in results["asr"]:
        asr_attempt("cpu")
    schema = ROOT / "src/notetaker/schemas/minutes.json"
    prompt = OUT / "llm-prompt.txt"
    prompt.write_text(
        '<|im_start|>system\nTu rédiges un brouillon de procès-verbal en français. '
        'Réponds uniquement en JSON conforme au schéma. Cite les sources s0. '
        'Ne crée aucun nom, montant, date ou résultat de vote absent. '
        'vote_id doit être null car aucun vote structuré n\'est fourni. '
        'Signale le résultat du vote comme à compléter dans to_verify.\n<|im_end|>\n'
        '<|im_start|>user\nOrdre du jour : travaux de la bibliothèque. '
        'Segment s0 : Nous examinons les travaux de la bibliothèque. '
        'Le montant annoncé est de douze mille euros. Le résultat du vote reste à compléter. '
        '/no_think\n<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n', encoding="utf-8")
    binary = ROOT / "runtimes/llama-cpu-b11681/llama-completion.exe"
    model = ROOT / "models/llm/qwen3-4b/Qwen3-4B-Q4_K_M.gguf"
    command = [binary, "-m", model, "-f", prompt, "-jf", schema, "-ngl", "0", "-t", "4", "-c", "4096", "-n", "512",
               "--temp", "0", "--seed", "42", "--offline", "--no-display-prompt", "--simple-io", "-no-cnv"]
    data = measured(command, "llm-cpu", timeout=240)
    raw = (ROOT / data["stdout"]).read_text(encoding="utf-8").strip()
    # completion may append an end-of-text display marker after the JSON value.
    try:
        content, end = json.JSONDecoder().raw_decode(raw)
        validate_minutes(content, {"s0"}, {})
        data["schema_valid"] = True
        data["result"] = content
        data["trailing_output"] = raw[end:].strip()
        atomic_json(OUT / "llm-draft.json", content)
    except Exception as error:
        data["schema_valid"] = False
        data["validation_error"] = type(error).__name__
    results["llm_cpu"] = data
    results["diarization"] = {"status": "community-1-not-acquired", "reason": "HTTP 401; alternative requested by user",
                              "alternative_report": "docs/evidence/diarization-alternative-probe.json"}
    atomic_json(EVIDENCE / "phase0-probes.json", results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["asr"]["cpu"]["returncode"] == 0 and data.get("schema_valid") else 1

if __name__ == "__main__":
    raise SystemExit(main())
