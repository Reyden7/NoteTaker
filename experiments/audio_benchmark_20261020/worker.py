"""Single real engine invocation, local files only; output is never a meeting."""
import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from notetaker.infrastructure.offline import enforce_offline,deny_python_network
enforce_offline()
os.environ.update(OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',PYANNOTE_METRICS_ENABLED='0')
NETWORK=deny_python_network()


def moss(request):
    import torch
    from transformers import AutoModelForCausalLM,AutoProcessor
    from moss_transcribe_diarize import parse_transcript
    from moss_transcribe_diarize.inference_utils import build_transcription_messages,generate_transcription
    torch.set_num_threads(4)
    device=torch.device(request.get('device','cpu'))
    if device.type=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA_UNAVAILABLE')
    dtype=torch.bfloat16 if device.type=='cuda' else torch.float32
    path=Path(request['model']).resolve(strict=True)
    model=AutoModelForCausalLM.from_pretrained(str(path),trust_remote_code=True,local_files_only=True,
        dtype='auto',attn_implementation='sdpa').to(dtype=dtype).to(device).eval()
    processor=AutoProcessor.from_pretrained(str(path),trust_remote_code=True,local_files_only=True)
    messages=build_transcription_messages(request['audio'])
    progress_path=Path(request['output']).with_name('generation-progress.json')
    def token_progress(count):
        if count%50==0:progress_path.write_text(json.dumps({'generated_tokens':count}),encoding='utf-8')
    gpu={}
    if device.type=='cuda':
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
        begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True);begin.record()
    result=generate_transcription(model,processor,messages,device=device,dtype=dtype,
        max_new_tokens=request['max_new_tokens'],do_sample=False,token_callback=token_progress)
    if device.type=='cuda':
        end.record();torch.cuda.synchronize()
        gpu={'cuda_event_interval_seconds':begin.elapsed_time(end)/1000,
             'cuda_interval_scope':'Generation stream interval including idle/host gaps; NOT sum of active kernel times.',
             'torch_peak_allocated_bytes':torch.cuda.max_memory_allocated(),
             'torch_peak_reserved_bytes':torch.cuda.max_memory_reserved()}
    # Save the raw stream before parsing. A parser failure must not erase it.
    Path(request['output']).with_name('moss-raw.txt').write_text(result['text'],encoding='utf-8')
    segments=[{'start':float(s.start),'end':float(s.end),'speaker':s.speaker,'text':s.text,
               'uncertainty_status':'No calibrated confidence exposed by this model'} for s in parse_transcript(result['text'])]
    return {**result,'segments':segments,'gpu_metrics':gpu,
        'token_budget_reached':result['generated_tokens']>=request['max_new_tokens'],
        'attention_implementation':'sdpa','default_official_prompt_used':True,'dtype':str(dtype)}


def alignment(request):
    import torch
    import numpy as np
    import wave
    from whisperx.alignment import load_align_model,align
    torch.set_num_threads(4)
    source=json.loads(Path(request['transcription']).read_text(encoding='utf-8'))['result']
    with wave.open(request['audio'],'rb') as stream:
        samples=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').astype(np.float32)/32768
    model,metadata=load_align_model('fr',request['device'],model_name=request['model'],model_cache_only=True)
    result=align(source['segments'],model,metadata,samples,request['device'],return_char_alignments=False)
    result['same_recognized_text_input']=True
    result['source_transcription']=request['transcription']
    return result


def community(request):
    import torch
    import numpy as np
    import wave
    from pyannote.audio import Pipeline
    torch.set_num_threads(4)
    path=Path(request['model']).resolve(strict=True)
    with wave.open(request['audio'],'rb') as stream:
        samples=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').astype(np.float32)/32768
    pipeline=Pipeline.from_pretrained(str(path))
    pipeline.to(torch.device(request['device']))
    result=pipeline({'waveform':torch.from_numpy(samples[None,:]),'sample_rate':16000})
    def rows(annotation):
        return [{'start':float(t.start),'end':float(t.end),'speaker':str(s)} for t,s in annotation]
    return {'turns':rows(result.speaker_diarization),'exclusive_turns':rows(result.exclusive_speaker_diarization),
            'speaker_count_forced':False,'overlap_preserved_in_standard_output':True}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('request',type=Path);args=parser.parse_args()
    request=json.loads(args.request.read_text(encoding='utf-8'))
    target=Path(request['output']);target.parent.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();result={}
    try:
        from notetaker.workers.probe import transcribe,diarize_sherpa
        if request['task']=='asr':
            if request.get('device')=='cuda':
                # Load this isolated environment's CUDA/cuDNN DLLs before CTranslate2.
                import torch
                if not torch.cuda.is_available():raise RuntimeError('CUDA_UNAVAILABLE')
                torch.cuda.synchronize()
            result=transcribe(request)
        elif request['task']=='sherpa': result=diarize_sherpa(request)
        elif request['task']=='moss':result=moss(request)
        elif request['task']=='alignment':result=alignment(request)
        elif request['task']=='community':result=community(request)
        else: raise ValueError('UNIMPLEMENTED_ENGINE_TASK')
        record={'status':'completed','task':request['task'],'device':request.get('device','cpu'),'result':result}
    except BaseException as error:
        traceback.print_exc()
        record={'status':'failed','task':request['task'],'error_type':type(error).__name__,'error':str(error)}
    record.update(elapsed_seconds=time.perf_counter()-started,python_network_attempts=len(NETWORK))
    target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='result'},ensure_ascii=True),flush=True)
    return 0 if record['status']=='completed' else 2


if __name__=='__main__':raise SystemExit(main())
