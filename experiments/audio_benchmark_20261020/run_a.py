"""Stage-gated reference chain, reusing readonly production engine functions."""
import argparse
import os
import sys
from .common import ROOT,OUT,read,sha,write
from .measured import run


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['60s','180s','full']);p.add_argument('--device',default='cpu',choices=['cpu','cuda']);a=p.parse_args()
    stage_order=['60s','180s','full'];index=stage_order.index(a.stage)
    base=OUT/'runs'/('A-'+a.device+'-v2')/a.stage
    if index and read(base.parent/stage_order[index-1]/'gate.json')['passed'] is not True: raise ValueError('PREVIOUS_STAGE_REQUIRED')
    manifest=read(OUT/'manifest.json');case=manifest['cases'][a.stage]
    if sha(case['audio'])!=case['sha256']:raise ValueError('BENCHMARK_AUDIO_CHANGED')
    if not all(sha(path)==digest for path,digest in manifest['protected'].items()):raise ValueError('PRODUCTION_OR_REFERENCE_CHANGED')
    if base.exists():raise FileExistsError(base)
    base.mkdir(parents=True)
    env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'}
    env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',LLAMA_ARG_OFFLINE='1')
    attempts=[]
    for task in ['asr','sherpa']:
        request={'task':task,'audio':case['audio'],'device':a.device if task=='asr' else 'cpu',
            'model':str(ROOT/'models/asr/small'),
            'segmentation':str(ROOT/'models/diarization/sherpa/sherpa-onnx-pyannote-segmentation-3-0/model.onnx'),
            'embedding':str(ROOT/'models/diarization/sherpa/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx'),
            'refinement_embedding':str(ROOT/'models/diarization/wespeaker/voxceleb_resnet34-sherpa.onnx'),
            'speaker_strategy':'clean-anchors','overlap':True,'output':str(base/(task+'-result.json'))}
        path=base/(task+'-request.json');write(path,request)
        measure=run([ROOT/'.venv-lab-a/Scripts/python.exe','-m','experiments.audio_benchmark_20261020.worker',path],
                    base/task,timeout=1800 if a.stage=='full' else 600,cancel=OUT/'CANCEL',env=env)
        attempts.append(measure)
        if measure['status']!='completed':break
    passed=len(attempts)==2 and all(r['status']=='completed' for r in attempts)
    write(base/'gate.json',{'passed':passed,'stage':a.stage,'chain':'A','quality_validated':False,
        'protected_unchanged':all(sha(path)==digest for path,digest in manifest['protected'].items())})
    print('A '+a.stage+' gate='+str(passed),flush=True)


if __name__=='__main__':main()
