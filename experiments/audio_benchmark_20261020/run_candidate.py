"""Independent engine paliers; no silent success on incomplete generation."""
import argparse
import os
from .common import ROOT,OUT,read,sha,write
from .measured import run


def main():
    p=argparse.ArgumentParser();p.add_argument('engine',choices=['moss','large','alignment','community'])
    p.add_argument('stage',choices=['60s','180s','full']);p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    p.add_argument('--series',default='main');a=p.parse_args()
    if not a.series.replace('-','').isalnum():raise ValueError('INVALID_SERIES')
    order=['60s','180s','full'];idx=order.index(a.stage)
    base=OUT/'runs'/(a.engine+'-'+a.device+'-'+a.series)/a.stage
    if idx and not read(base.parent/order[idx-1]/'gate.json')['passed']:raise ValueError('PREVIOUS_STAGE_REQUIRED')
    if base.exists():raise FileExistsError(base)
    manifest=read(OUT/'manifest.json');case=manifest['cases'][a.stage]
    if not all(sha(path)==h for path,h in manifest['protected'].items()):raise ValueError('PROTECTED_CHANGED')
    if sha(case['audio'])!=case['sha256']:raise ValueError('AUDIO_CHANGED')
    asset=read(OUT/'assets'/(a.engine+'.json')) if a.engine!='community' or (OUT/'assets/community.json').is_file() else None
    if asset is None:raise FileNotFoundError('COMMUNITY_OFFICIAL_ACCESS_REQUIRED')
    base.mkdir(parents=True)
    request={'task':{'large':'asr'}.get(a.engine,a.engine),'audio':case['audio'],'device':a.device,
        'model':asset['path'],'output':str(base/'result.json')}
    if a.engine=='moss':request['max_new_tokens']={'60s':4096,'180s':8192,'full':32768}[a.stage]
    if a.engine=='alignment':request['transcription']=str(OUT/'runs'/('large-'+a.device+'-main')/a.stage/'result.json')
    write(base/'request.json',request)
    env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8',
         'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1',
         'HF_MODULES_CACHE':str(OUT/'dynamic-modules'/a.engine),'TORCH_HOME':str(OUT/'torch-cache'),
         'NLTK_DATA':str(ROOT/'models/audio-lab/nltk'),'PYANNOTE_METRICS_ENABLED':'0',
         'OTEL_SDK_DISABLED':'true','DO_NOT_TRACK':'1'}
    env.pop('HF_TOKEN',None);env.pop('HUGGING_FACE_HUB_TOKEN',None)
    interpreter=ROOT/('.venv-lab-c' if a.engine=='moss' else '.venv-lab-b')/'Scripts/python.exe'
    measure=run([interpreter,'-m','experiments.audio_benchmark_20261020.worker',base/'request.json'],base/'process',
        timeout=3600 if a.stage=='full' else 900,cancel=OUT/'CANCEL',env=env)
    result=read(base/'result.json') if (base/'result.json').is_file() else {}
    passed=measure['status']=='completed' and result.get('status')=='completed'
    errors=[]
    if passed:
        output=result['result'];segments=output.get('segments',output.get('turns',[]))
        if not segments:errors.append('NO_SEGMENTS')
        if output.get('token_budget_reached'):errors.append('GENERATION_POSSIBLY_TRUNCATED')
        if any(s['start']<0 or s['end']<s['start'] or s['end']>case['duration_seconds']+0.1 for s in segments):errors.append('INVALID_SEGMENT_TIMES')
    passed=passed and not errors
    write(base/'gate.json',{'passed':passed,'errors':errors,'engine':a.engine,'device':a.device,
        'stage':a.stage,'complete_chain_B':False,'quality_validated':False,
        'protected_unchanged':all(sha(path)==h for path,h in manifest['protected'].items())})
    print(a.engine+' '+a.stage+' '+a.device+' gate='+str(passed),flush=True)


if __name__=='__main__':main()
