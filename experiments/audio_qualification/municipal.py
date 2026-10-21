"""Independent municipal datasets, existing local models, immutable run outputs."""
import copy
import json
import os
import shutil
import wave
import uuid
from pathlib import Path
from .core import ROOT,BENCH,WORK,read,sha,utc,digest,blank_zone,validate_project,QualificationError

MUNICIPAL_ROOT=ROOT/'output/audio-qualification/municipal'


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)


def register_source(source,folder,kind='real',label='Conseil municipal'):
    source=Path(source).resolve(strict=True);folder=Path(folder).resolve()
    if kind not in ('real','human_simulation','technical_test'):raise QualificationError('Indiquer réel, simulation jouée ou test technique.')
    if source.suffix.lower() not in ('.wav','.mp3','.m4a'):raise QualificationError('Choisir un WAV, MP3 ou M4A local.')
    if folder.exists():raise QualificationError('Ce projet existe déjà. Ouvrez-le ou choisissez un nouveau dossier ; aucun résultat ne sera remplacé.')
    folder.mkdir(parents=True);original=folder/'input'/('original'+source.suffix.lower());original.parent.mkdir()
    before=sha(source);shutil.copyfile(source,original)
    if sha(source)!=before or sha(original)!=before:raise QualificationError('Le fichier source a changé pendant la copie. Copie conservée pour diagnostic.')
    value={'schema':1,'id':uuid.uuid4().hex,'label':label,'kind':kind,'created_utc':utc(),
        'source':{'path':str(original),'sha256':before,'original_path':str(source)},
        'protected':{str(p):sha(p) for p in (ROOT/'src').rglob('*.py')},
        'quality_status':'Not annotated or qualified. A human simulation is not natural meeting evidence.'}
    write_new(folder/'source.json',value);return value


def normalize_audio(folder):
    import av
    folder=Path(folder);source=read(folder/'source.json')['source'];target=folder/'normalized.wav'
    if target.exists():raise QualificationError('Le WAV de ce projet existe déjà ; il est conservé.')
    if sha(source['path'])!=source['sha256']:raise QualificationError('Copie source altérée.')
    frames=0
    with av.open(source['path']) as container,wave.open(str(target),'wb') as out:
        if not container.streams.audio:raise QualificationError('Aucune piste audio.')
        out.setparams((1,2,16000,0,'NONE','not compressed'))
        resampler=av.AudioResampler(format='s16',layout='mono',rate=16000)
        for frame in container.decode(audio=0):
            for normalized in resampler.resample(frame):
                out.writeframesraw(normalized.to_ndarray().tobytes());frames+=normalized.samples
            if frames>3600*16000:raise QualificationError('Fichier supérieur à une heure : choisir explicitement un extrait pour cette qualification.')
        for normalized in resampler.resample(None):
            out.writeframesraw(normalized.to_ndarray().tobytes());frames+=normalized.samples
    if frames==0:raise QualificationError('Audio vide ; aucune chaîne ne sera lancée.')
    value={'path':str(target.resolve()),'sha256':sha(target),'duration':frames/16000,'format':'PCM16 mono 16000 Hz',
        'recommended_10_to_15_minutes':600<=frames/16000<=900,
        'time_origin':'0 in normalized recording; original file preserved; no source trimming'}
    write_new(folder/'audio.json',value);return value


def offline_env():
    env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8',
        'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1',
        'PYANNOTE_METRICS_ENABLED':'0','OTEL_SDK_DISABLED':'true','DO_NOT_TRACK':'1',
        'NLTK_DATA':str(ROOT/'models/audio-lab/nltk'),'TORCH_HOME':str(BENCH/'torch-cache')}
    for key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN','HUGGINGFACE_TOKEN'):env.pop(key,None)
    return env


def engine_requests(audio,run,device):
    if device not in ('cpu','cuda'):raise QualificationError('Choisir CPU ou CUDA explicitement.')
    source=read(BENCH/'runs/A-cpu-v2/full/asr-request.json');result=[]
    for name,task in (('small','asr'),('sherpa','sherpa')):
        request={**source,'task':task,'device':'cpu','audio':str(audio),'output':str(run/name/'result.json')}
        result.append((name,ROOT/'.venv-lab-a/Scripts/python.exe',request))
    for name,task,asset in (('large','asr','large'),('community','community','community'),('alignment','alignment','alignment')):
        meta=read(BENCH/'assets'/f'{asset}.json');model=Path(meta['path'])
        if not model.is_absolute() or not model.exists():raise QualificationError('Modèle local manquant : '+str(model)+'. Aucun téléchargement automatique.')
        request={'task':task,'device':device,'audio':str(audio),'model':str(model),'output':str(run/name/'result.json')}
        if name=='alignment':request['transcription']=str(run/'large/result.json')
        result.append((name,ROOT/'.venv-lab-b/Scripts/python.exe',request))
    for name,interpreter,request in result:
        if not interpreter.is_file():raise QualificationError('Environnement isolé absent : '+str(interpreter))
        for key in ('model','segmentation','embedding','refinement_embedding'):
            if key in request and not Path(request[key]).exists():raise QualificationError('Dépendance locale absente : '+request[key])
    return result


def combine(asr,diar,whisperx=False,exclusive=False):
    from experiments.audio_benchmark_20261020.analyze import align_reference
    from experiments.audio_benchmark_20261020.combine_b import standard_overlap
    segments=[]
    for i,s in enumerate(asr['segments']):
        words=copy.deepcopy(s.get('words') or [])
        incomplete=not words or any(w.get('start') is None or w.get('end') is None for w in words)
        if whisperx:words=[{**w,'word':' '+w['word'].lstrip()} for w in words]
        segments.append({**s,'id':f's{i}','words':[] if incomplete else words})
    rows,aliases=align_reference(segments,{'turns':diar.get('exclusive_turns',diar['turns']) if exclusive else diar['turns'],
        'possible_overlaps':diar.get('possible_overlaps',standard_overlap(diar['turns']))})
    return {'segments':[{'id':r['id'],'start':r['start_ms']/1000,'end':r['end_ms']/1000,
        'text':r['text'],'speaker':r['speaker_id'],'uncertain':r['uncertain'],'source':r['source']} for r in rows],
        'speaker_aliases':aliases,'names_assigned':False}


def select_excerpts(duration,diar=None,hints=()):
    """Small deterministic spread, independent of WER and model ranking. No truth."""
    if duration<=0:raise QualificationError('Durée invalide.')
    # At most six 25-second nonoverlapping regions, about 2.5 minutes to annotate.
    selections=[];width=min(25,duration)
    for i,fraction in enumerate((.05,.23,.41,.59,.77,.94)):
        start=max(0,min(duration-width,duration*fraction-width/2));end=start+width
        if any(start<b and end>a for a,b in selections):continue
        selections.append((start,end))
    result=[blank_zone(f'M{i+1:02d}',a,b,f'M{i+1:02d} · échantillon temporel non validé') for i,(a,b) in enumerate(selections)]
    # Hints supplied by the operator are candidate events, not inferred decisions/votes.
    for h in hints:
        if h['kind'] not in ('simple','speaker_change','proposal','deliberation','vote','overlap'):raise QualificationError('Type d’événement inconnu.')
        if not 0<=h['start']<h['end']<=duration:raise QualificationError('Repère hors audio.')
    return result


def finalize_run(folder,run,device):
    folder,run=Path(folder),Path(run);audio=read(folder/'audio.json');meta=read(folder/'source.json')
    source_map={key:run/name/'result.json' for key,name in (('small_asr','small'),('small_diar','sherpa'),('large_asr','large'),('community','community'),('whisperx','alignment'))}
    raw={k:read(path)['result'] for k,path in source_map.items()}
    small=combine(raw['small_asr'],raw['small_diar']);write_new(run/'small-display.json',small);source_map['small_display']=run/'small-display.json'
    import re
    before=re.sub(r'\s+','',''.join(s['text'] for s in raw['large_asr']['segments']))
    after=re.sub(r'\s+','',''.join(s['text'] for s in raw['whisperx']['segments']))
    if before!=after:raise QualificationError('WhisperX a modifié le texte reconnu : sorties conservées, comparaison bloquée.')
    for prefix,source in (('without-whisperx',raw['large_asr']),('with-whisperx',raw['whisperx'])):
        for mode in ('standard','exclusive'):
            name=prefix+'-'+mode;path=run/(name+'.json')
            write_new(path,combine(source,raw['community'],prefix=='with-whisperx',mode=='exclusive'));source_map[name]=path
    measurements={name:read(run/name/'process/measurement.json') for name in ('small','sherpa','large','community','alignment')}
    def stats(names):
        m=[measurements[n] for n in names]
        return {'wall_seconds':sum(x['wall_seconds'] for x in m),'cpu_total_seconds':sum(x['cpu']['user_seconds']+x['cpu']['kernel_seconds'] for x in m),
            'peak_committed_bytes':max(x['peak_job_committed_bytes'] for x in m),'components':names,
            'interpretation':'Sum of separate component processes; peak is max because they run sequentially. OS file caches not purged; not a cold-cache measurement.'}
    perf={'A complet CPU':stats(['small','sherpa']),f'B complet {device.upper()}, sans WhisperX':stats(['large','community']),
          f'B complet {device.upper()}, avec WhisperX':stats(['large','community','alignment'])}
    write_new(run/'performance.json',perf);source_map['performance']=run/'performance.json'
    project={'schema':1,'id':uuid.uuid4().hex,'created_utc':utc(),'audio':{k:audio[k] for k in ('path','sha256','duration')},
        'sources':{k:{'path':str(path.resolve()),'sha256':sha(path)} for k,path in source_map.items()},'voices':[],
        'zones':select_excerpts(audio['duration'],raw['community']['turns']),
        'human_reference_origin':'Blank municipal annotation; never copied from ASR. Events, proposals and votes remain unverified.',
        'lab_workspace':str(run.resolve()),'municipal_source':meta,'selection_protocol':'six deterministic temporal samples, up to 25s each; editable before annotation; no engine accuracy selection'}
    validate_project(project);write_new(run/'project.json',project);return project


def write_launcher(project_path):
    """Fixed command, no user labels or imported text embedded in shell code."""
    project_path=Path(project_path);target=project_path.parent/'Ouvrir-ce-test.cmd'
    with target.open('x',encoding='utf-8',newline='') as f:
        f.write('@echo off\r\ncd /d "'+str(ROOT)+'"\r\n"'+str(ROOT/'.venv/Scripts/python.exe')+'" -m experiments.audio_qualification.app --project "%~dp0project.json"\r\npause\r\n')
    return target


def run_benchmark(folder,device='cuda',run_function=None):
    from experiments.audio_benchmark_20261020.measured import run as real_run
    run_function=run_function or real_run;folder=Path(folder);audio=read(folder/'audio.json');source=read(folder/'source.json')
    if sha(audio['path'])!=audio['sha256']:raise QualificationError('WAV altéré ; aucun calcul lancé.')
    if not all(sha(p)==h for p,h in source['protected'].items()):raise QualificationError('Le code protégé a changé depuis l’import. Préparer un nouveau projet pour conserver la provenance.')
    attempt=folder/'runs'/uuid.uuid4().hex;attempt.mkdir(parents=True)
    import psutil,platform
    write_new(attempt/'hardware.json',{'platform':platform.platform(),'logical_cpus':psutil.cpu_count(),'physical_cpus':psutil.cpu_count(logical=False),
        'memory_bytes':psutil.virtual_memory().total,'candidate_device_requested':device,'CPU_baseline_always':True})
    for stage,seconds in (('60s',min(60,audio['duration'])),('180s',min(180,audio['duration'])),('full',audio['duration'])):
        if (folder/'CANCEL').exists():raise QualificationError('Calcul annulé avant le palier suivant ; sorties conservées.')
        stage_path=attempt/stage;stage_path.mkdir()
        if stage=='full':clip=Path(audio['path'])
        else:
            clip=stage_path/'audio.wav'
            with wave.open(audio['path'],'rb') as inp,wave.open(str(clip),'wb') as out:
                out.setparams(inp.getparams());out.writeframes(inp.readframes(round(seconds*inp.getframerate())))
        for name,interpreter,request in engine_requests(clip,stage_path,device):
            path=stage_path/name;path.mkdir();write_new(path/'request.json',request)
            print(f'{stage} · {name} · {request["device"]}',flush=True)
            measured=run_function([interpreter,'-m','experiments.audio_benchmark_20261020.worker',path/'request.json'],path/'process',
                timeout=3600 if stage=='full' else 900,memory_limit=(4 if name in ('small','sherpa') else 12)*1024**3,
                cancel=folder/'CANCEL',env=offline_env())
            result=read(path/'result.json') if (path/'result.json').is_file() else {}
            if measured['status']!='completed' or result.get('status')!='completed':
                raise QualificationError(f'{name} : échec/annulation au palier {stage}. Diagnostic conservé dans {path}. Aucun résultat manquant n’est simulé.')
            values=result['result'].get('segments',result['result'].get('turns',[]))
            if not values or any(not 0<=s['start']<=s['end']<=seconds+.1 for s in values):raise QualificationError(f'{name} : sortie vide ou horaires invalides. Palier suivant bloqué.')
        write_new(stage_path/'gate.json',{'technical_passed':True,'quality_validated':False,'audio_sha256':sha(clip)})
    project=finalize_run(folder,attempt/'full',device)
    if not all(sha(p)==h for p,h in source['protected'].items()):raise QualificationError('Code protégé modifié pendant le benchmark ; résultats à auditer.')
    write_launcher(attempt/'full/project.json')
    write_new(attempt/'ready.json',{'project':str(attempt/'full/project.json'),'quality_validated':False,'BFMTV_unchanged_by_design':True})
    return attempt/'full/project.json'
