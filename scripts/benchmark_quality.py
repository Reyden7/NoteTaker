"""Replay actual field workers in an isolated directory; never approves a meeting."""
import argparse
import re
import json
import shutil
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.process import run_worker

parser = argparse.ArgumentParser()
parser.add_argument('--stage', choices=['asr', 'diarization', 'summary'], required=True)
parser.add_argument('--diarization', type=Path)
parser.add_argument('--model', type=Path)
parser.add_argument('--run-label')
args = parser.parse_args()
work = ROOT / 'output/quality-02'
if args.run_label and (args.stage != 'summary' or not re.fullmatch(r'[a-z0-9-]+', args.run_label)):
    raise ValueError('INVALID_SUMMARY_RUN_LABEL')
stage_work = work / args.run_label if args.run_label else work
stage_work.mkdir(parents=True, exist_ok=True)
records = json.loads((work / 'baseline/records.json').read_text(encoding='utf-8'))
jobs = Path(records['audio_take'][0]['path']).parent.parent / 'jobs'
source = next(jobs.glob('*/normalized.wav'))
audio = work / 'input-normalized.wav'
if not audio.exists():
    shutil.copyfile(source, audio)
if sha256_file(audio) != sha256_file(source):
    raise ValueError('BENCHMARK_AUDIO_CHANGED')
models = ModelPaths()
if args.stage == 'asr':
    request = {'engine': 'asr', 'device': 'cpu', 'model': str(models.asr), 'audio': str(audio)}
elif args.stage == 'diarization':
    request = {'engine': 'diarization-sherpa', 'device': 'cpu', 'audio': str(audio), 'segmentation': str(models.segmentation),
               'embedding': str(models.embedding), 'refinement_embedding': str(models.refinement_embedding), 'overlap': True}
else:
    from notetaker.services.pipeline import align_transcript
    asr = json.loads((work / 'asr-result.json').read_text(encoding='utf-8'))['result']
    diarization = json.loads(args.diarization.read_text(encoding='utf-8'))
    diarization = diarization.get('result', diarization)
    rows, speakers = align_transcript(asr['segments'], diarization)
    atomic_json(work / 'aligned-transcript.json', {'utterances': rows, 'speakers': speakers})
    summary_workspace = stage_work / 'summary'
    summary_workspace.mkdir(exist_ok=True)
    request = {'engine': 'llm', 'task': 'summary', 'device': 'cpu', 'binary': str(models.llama), 'model': str(args.model.resolve() if args.model else models.llm),
               'workspace': str(summary_workspace), 'utterances': rows}
path = stage_work / (args.stage + '-request.json')
cached_calls_before = len(list((stage_work / 'summary').glob('*.identity.json'))) if args.stage == 'summary' else 0
if args.stage == 'summary':
    from datetime import datetime, timezone
    atomic_json(stage_work / 'summary-execution.json', {'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in [
            ROOT / 'src/notetaker/engines/hierarchical_summary.py', ROOT / 'src/notetaker/workers/probe.py',
            ROOT / 'src/notetaker/services/pipeline.py']},
        'model_sha256': sha256_file(Path(request['model'])), 'binary_sha256': sha256_file(models.llama),
        'audio_sha256': sha256_file(audio), 'aligned_transcript_sha256': sha256_file(work / 'aligned-transcript.json'), 'run_label': args.run_label})
atomic_json(path, request)
print('Starting field benchmark stage', args.stage, flush=True)
started = time.perf_counter()
result = run_worker(path, timeout=7200)
atomic_json(stage_work / (args.stage + '-result.json'), result)
timing = {'cpu_seconds_wall': round(time.perf_counter() - started, 3), 'audio_sha256': sha256_file(audio),
          'human_reference_accuracy': 'not-measured', 'human_review': 'not-performed'}
if args.stage == 'summary':
    calls = {p.stem.removesuffix('.timing'): json.loads(p.read_text(encoding='utf-8'))['wall_seconds']
             for p in (stage_work / 'summary').glob('*.timing.json') if p.with_name(p.name.replace('.timing.json', '.identity.json')).exists()}
    timing.update({'cached_result_candidates_before_resume': cached_calls_before,
                   'cumulative_native_call_wall_seconds': round(sum(calls.values()), 3), 'native_call_wall_seconds': calls,
                   'wall_time_note': 'resumed worker duration excludes earlier cached inference; cumulative calls include their original measured times; not isolated CPU performance'})
atomic_json(stage_work / (args.stage + '-timing.json'), timing)
print(args.stage, result.get('status'), 'seconds', round(time.perf_counter() - started, 3), flush=True)
