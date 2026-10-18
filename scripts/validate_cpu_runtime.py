"""Real natural-audio smoke of an isolated CPU DLL, not full field acceptance."""
import importlib.metadata
import json
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json,sha256_file
work=ROOT/'output/quality-02/cpu-runtime-probe';work.mkdir(exist_ok=True)
original=Path(importlib.metadata.distribution('ctranslate2').locate_file('ctranslate2'))
original_hash=sha256_file(original/'ctranslate2.dll')
overlay=ROOT/'.cache/ctranslate2-cpu-package'
candidate=ROOT/'.cache/ctranslate2-cpu-build/Release/ctranslate2.dll'
if not overlay.exists():
    shutil.copytree(original,overlay/'ctranslate2',ignore=shutil.ignore_patterns('*.dll','__pycache__'))
    shutil.copyfile(candidate,overlay/'ctranslate2/ctranslate2.dll')
else:
    assert sha256_file(overlay/'ctranslate2/ctranslate2.dll') == sha256_file(candidate), 'Different existing runtime; preserve it'
    for extension in original.glob('*.pyd'):
        assert sha256_file(overlay/'ctranslate2'/extension.name) == sha256_file(extension), 'Different Python ABI extension'
if '--probe' not in sys.argv:
    started=time.perf_counter()
    evidence=ROOT/'docs/evidence/ctranslate2-cpu-smoke.json'
    if evidence.exists():
        shutil.copyfile(evidence,work/f'previous-smoke-{time.time_ns()}.json')
        evidence.unlink()
    process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--probe'],stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,encoding='utf-8',errors='replace')
    timed_out=False
    try:
        stdout,stderr=process.communicate(timeout=600)
    except subprocess.TimeoutExpired:
        # Windows venv launchers may have a real Python child. Stop only this
        # known probe tree; do not leave native inference orphaned after a timeout.
        import psutil
        root=psutil.Process(process.pid)
        for child in reversed(root.children(recursive=True)):
            try: child.kill()
            except psutil.NoSuchProcess: pass
        process.kill()
        stdout,stderr=process.communicate()
        timed_out=True
    (work/'stdout.txt').write_text(stdout,encoding='utf-8')
    (work/'stderr.txt').write_text(stderr,encoding='utf-8')
    if (process.returncode or timed_out) and not evidence.exists():
        atomic_json(evidence,{'status':'native_process_timed_out' if timed_out else 'native_process_failed','exit_code':process.returncode,
            'candidate_dll_sha256':sha256_file(candidate),'inference_tested':False,
            'active_environment_replaced':False,'commercial_clearance':False,
            'scope':'30s natural excerpt; native failure is not a successful inference',
            'wall_seconds':round(time.perf_counter()-started,3),
            'original_wheel_dll_unchanged':sha256_file(original/'ctranslate2.dll')==original_hash})
    print(evidence.read_text(encoding='utf-8') if evidence.exists() else stderr)
    raise SystemExit(process.returncode)
with wave.open(str(ROOT/'output/quality-02/input-normalized.wav'),'rb') as source:
    assert (source.getnchannels(),source.getsampwidth(),source.getframerate())==(1,2,16000)
    source.setpos(600*16000);frames=source.readframes(30*16000)
with wave.open(str(work/'natural-excerpt.wav'),'wb') as out:
    out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(frames)
sys.path.insert(0,str(overlay))
report={'scope':'30s natural excerpt only; not complete meeting or clean Windows qualification',
        'candidate_dll_sha256':sha256_file(candidate),'inference_tested':False,'active_environment_replaced':False,
        'commercial_clearance':False,'source_offset_seconds':600,'duration_seconds':30}
started=time.perf_counter()
try:
    import ctranslate2
    report['loaded_module']=str(ctranslate2.__file__)
    report['cuda_device_count']=ctranslate2.get_cuda_device_count()
    report['cpu_compute_types']=sorted(ctranslate2.get_supported_compute_types('cpu'))
    if not Path(ctranslate2.__file__).resolve().is_relative_to(overlay): raise ValueError('WRONG_NATIVE_PACKAGE')
    from notetaker.workers.probe import transcribe
    from notetaker.infrastructure.paths import ModelPaths
    result=transcribe({'device':'cpu','audio':str(work/'natural-excerpt.wav'),'model':str(ModelPaths().asr)})
    atomic_json(work/'asr-result.json',result)
    text=''.join(s['text'] for s in result['segments'])
    report.update({'status':'cpu_import_and_natural_asr_smoke_passed','inference_tested':True,
        'segments':len(result['segments']),'words':sum(len(s.get('words',[])) for s in result['segments']),
        'replacement_characters':text.count('\ufffd')})
    assert result['segments'] and '\ufffd' not in text and report['cuda_device_count']==0
except Exception as error:
    report.update({'status':'failed','error':str(error),'error_type':type(error).__name__})
finally:
    report['wall_seconds']=round(time.perf_counter()-started,3)
    report['original_wheel_dll_unchanged']=sha256_file(original/'ctranslate2.dll')==original_hash
    atomic_json(ROOT/'docs/evidence/ctranslate2-cpu-smoke.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
if report['status']=='failed': raise SystemExit(1)
