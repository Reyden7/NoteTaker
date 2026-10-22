"""Policy and fault injection, distinct from the opt-in real hardware recipe."""
import json
import threading
import wave
from pathlib import Path
from types import SimpleNamespace
import pytest
from notetaker.services.audio_engine import (GPUAudio, GPUUnavailable, select_engine,
    read_mode, save_mode, community_data, preserve_simultaneous)
from notetaker.infrastructure.process import JobCancelled
from notetaker.services.pipeline import Pipeline, align_transcript
from notetaker.services.storage import SessionStore
from notetaker.services.transcript import preserve_corrections


class FakeGPU:
    failure = None
    calls = []
    def verify(self):
        self.calls.append('verify')
        if self.failure:
            raise self.failure
    def run(self, workspace, task, cancel):
        self.calls.append(task)
        return {'kernel_test': True}


@pytest.mark.parametrize('mode,device,calls', [('cpu','cpu',[]),('auto','cuda',['verify','preflight']),('gpu','cuda',['verify','preflight'])])
def test_selection(mode, device, calls, tmp_path):
    gpu = FakeGPU(); gpu.calls = []
    assert select_engine(mode, gpu, tmp_path, threading.Event(), lambda m: None)['device'] == device
    assert gpu.calls == calls


@pytest.mark.parametrize('code', ['GPU_RUNTIME_MISSING','GPU_MODEL_INTEGRITY_FAILED',
    'GPU_CUDA_UNAVAILABLE','GPU_FLOAT16_UNAVAILABLE','GPU_MEMORY_INSUFFICIENT','GPU_RUNTIME_VERSION_MISMATCH'])
def test_auto_admission_failure_and_explicit_gpu_error(code, tmp_path):
    gpu = FakeGPU(); gpu.calls = []; gpu.failure = GPUUnavailable(code)
    route = select_engine('auto',gpu,tmp_path,threading.Event(),lambda m: None)
    assert route['device'] == 'cpu' and route['reason'] == code
    with pytest.raises(GPUUnavailable, match=code):
        select_engine('gpu',gpu,tmp_path,threading.Event(),lambda m: None)


def test_cancellation_is_not_cpu_fallback(tmp_path):
    gpu = FakeGPU(); gpu.failure = JobCancelled('JOB_CANCELLED')
    with pytest.raises(JobCancelled):
        select_engine('auto',gpu,tmp_path,threading.Event(),lambda m: None)


def test_mode_persistence_no_sqlite_migration(tmp_path):
    assert read_mode(tmp_path) == 'auto'
    save_mode(tmp_path,'gpu'); assert read_mode(tmp_path)=='gpu'
    with pytest.raises(ValueError):save_mode(tmp_path,'whisperx')
    (tmp_path/'audio-settings.json').write_text('{broken')
    assert read_mode(tmp_path)=='cpu'


def test_missing_runtime_never_downloads(tmp_path):
    with pytest.raises(GPUUnavailable, match='RUNTIME_MISSING'):GPUAudio(tmp_path).verify()


@pytest.mark.parametrize('failure', ['none','cuda','memory','float16','version'])
def test_real_preflight_policy_exercises_kernel_and_library_support(tmp_path,monkeypatch,failure):
    import sys
    import importlib.metadata
    from notetaker.workers.gpu_audio import preflight
    calls=[]
    class Tensor:
        def __matmul__(self,other):calls.append('kernel');return self
        def sum(self):return self
        def item(self):return 65536
    versions={'torch':'2.8.0+cu128','pyannote.audio':'4.0.7','ctranslate2':'4.8.3','faster-whisper':'1.2.1','av':'18.1.0'}
    cuda=SimpleNamespace(is_available=lambda:failure!='cuda',synchronize=lambda:None,empty_cache=lambda:None,
        mem_get_info=lambda:(0 if failure=='memory' else 10*1024**3,12*1024**3),get_device_name=lambda i:'Mock device — not hardware evidence')
    monkeypatch.setitem(sys.modules,'torch',SimpleNamespace(cuda=cuda,ones=lambda *a,**k:Tensor()))
    monkeypatch.setitem(sys.modules,'ctranslate2',SimpleNamespace(get_cuda_device_count=lambda:1,
        get_supported_compute_types=lambda *a: {'int8'} if failure=='float16' else {'float16'}))
    monkeypatch.setattr(importlib.metadata,'version',lambda name:'bad' if failure=='version' else versions[name])
    request={'large':str(tmp_path),'community':str(tmp_path),'min_free_vram':8*1024**3}
    if failure=='none':
        assert preflight(request)['kernel_test'] and calls==['kernel']
    else:
        with pytest.raises(RuntimeError,match='GPU_'):preflight(request)
        assert ('kernel' in calls)==(failure=='memory')


def test_simultaneous_voices_kept_without_duplicating_words():
    diar = community_data([{'start':0,'end':2,'speaker':'voice_a'}, {'start':1,'end':3,'speaker':'voice_b'}])
    rows, names = align_transcript([{'id':'s0','start':0,'end':3,'text':'Quel projet ? Oui.',
        'words':[{'start':0,'end':.8,'word':'Quel '},{'start':1.1,'end':1.5,'word':'projet ? '},
                 {'start':2.1,'end':2.8,'word':'Oui.'}]}],diar)
    preserve_simultaneous(rows,diar)
    assert names == {'voice_a':'Intervenant 1','voice_b':'Intervenant 2'}
    assert diar['possible_overlaps'] == [{'start':1.0,'end':2.0,'speakers':['voice_a','voice_b']}]
    simultaneous = [u for u in rows if u['source']['simultaneous_turns']]
    assert simultaneous and all(u['speaker_id'] is None and u['uncertain'] for u in simultaneous)
    assert sum(u['text'].count('projet') for u in rows)==1
    assert rows[-1]['speaker_id']=='voice_b'


def test_adjacent_turns_are_not_overlap_and_no_speaker_limit():
    diar=community_data([{'start':i,'end':i+1,'speaker':f's{i}'} for i in range(25)])
    assert not diar['possible_overlaps'] and len({t['speaker'] for t in diar['turns']})==25


@pytest.mark.parametrize('start,end', [(-1,1),(1,1),(2,1),(0,float('nan')),(0,float('inf'))])
def test_invalid_turn_rejected(start,end):
    with pytest.raises(ValueError):community_data([{'start':start,'end':end,'speaker':'s'}])


def test_simultaneous_metadata_uses_stable_internal_ids():
    old={'speakers':{'old':'Intervenant 1'},'utterances':[{'id':'oldrow','start_ms':0,'end_ms':1000,
        'text':'bonjour','speaker_id':'old','uncertain':False,'source':{}}]}
    incoming=[{'id':'s0','start_ms':0,'end_ms':1000,'text':'bonjour','speaker_id':'new','uncertain':False,
        'source':{'diarization_engine':'community-1','candidates':['new'],
        'diarization_turns':[{'start':0,'end':1,'speaker':'new'}],
        'simultaneous_turns':[{'start':0,'end':1,'speakers':['new','unknown']}]}}]
    rows,names=preserve_corrections(old,incoming,{'new':'Intervenant 1'})
    assert rows[0]['speaker_id']=='old'
    assert rows[0]['source']['diarization_turns'][0]['speaker']=='old'
    assert rows[0]['source']['simultaneous_turns'][0]['speakers']==['old','unknown']


def test_compaction_preserves_all_gpu_turns_after_short_pause():
    from notetaker.services.transcript import compact_rows
    rows=[{'id':f's{i}','start_ms':i*1200,'end_ms':i*1200+1000,'text':'Bonjour',
        'speaker_id':'v','uncertain':False,'source':{'diarization_engine':'community-1',
        'diarization_turns':[{'start':i*1.2,'end':i*1.2+1,'speaker':'v'}]}} for i in range(2)]
    merged=compact_rows(rows)
    assert len(merged)==1 and len(merged[0]['source']['diarization_turns'])==2
    assert merged[0]['end_ms']==2200


@pytest.fixture
def session(tmp_path):
    store=SessionStore(tmp_path/'data');sid=store.create('Test interruption')
    path=tmp_path/'audio.wav'
    with wave.open(str(path),'wb') as stream:
        stream.setparams((1,2,16000,0,'NONE',''));stream.writeframes(b'\0\0'*16000)
    from notetaker.infrastructure.atomic import sha256_file
    store.add_take(sid,'import',path,sha256=sha256_file(path))
    store.save_analysis(sid,[{'id':'human','start_ms':0,'end_ms':1000,'text':'Correction humaine',
        'speaker_id':'v','uncertain':False,'source':{'automatic_attribution':False}}],{'v':'Mme Test'},1)
    yield store,sid,path
    store.close()


@pytest.mark.parametrize('failure_stage', ['asr','diarization','cancel'])
def test_gpu_failures_do_not_replace_analysis_or_run_cpu(session,monkeypatch,failure_stage):
    store,sid,path=session
    before=store.get(sid)
    calls=[]
    def run(self,workspace,task,cancel):
        calls.append(task)
        if task=='preflight':return {'kernel_test':True}
        if failure_stage=='cancel':raise JobCancelled('JOB_CANCELLED')
        if task==failure_stage:raise GPUUnavailable('GPU_OUT_OF_MEMORY')
        return {'segments':[{'id':'s0','start':0,'end':1,'text':'automatique'}]}
    monkeypatch.setattr(GPUAudio,'verify',lambda self:None)
    monkeypatch.setattr(GPUAudio,'run',run)
    pipe=Pipeline(store.root)
    monkeypatch.setattr(pipe,'_run',lambda *a,**k:pytest.fail('No implicit CPU retry'))
    with pytest.raises((GPUUnavailable,JobCancelled)):pipe.analyse(sid,'auto')
    after=store.get(sid)
    assert before['utterances']==after['utterances'] and before['revision']==after['revision']
    assert path.is_file() and store.jobs(sid)[0]['status']==('cancelled' if failure_stage=='cancel' else 'failed')


def test_gpu_reanalysis_preserves_confirmed_human_row(session,monkeypatch):
    store,sid,path=session
    monkeypatch.setattr(GPUAudio,'verify',lambda self:None)
    def run(self,workspace,task,cancel):
        if task=='preflight':return {'kernel_test':True}
        if task=='asr':return {'segments':[{'id':'s0','start':0,'end':1,'text':'texte machine'}]}
        return {'turns':[{'start':0,'end':1,'speaker':'SPEAKER_00'}]}
    monkeypatch.setattr(GPUAudio,'run',run)
    result=Pipeline(store.root).analyse(sid,'gpu')
    state=store.get(sid)
    assert result['device']=='cuda' and state['utterances'][0]['text']=='Correction humaine'
    assert state['speakers']['v']=='Mme Test'
    assert not state['votes'] and state['draft'] is None


def test_gpu_worker_environment_excludes_credentials_even_when_frozen(tmp_path,monkeypatch):
    from notetaker.infrastructure import process,windows_job
    import sys
    request=tmp_path/'req.json';request.write_text('{}')
    monkeypatch.setenv('HF_TOKEN','secret-fixture-not-real')
    monkeypatch.setenv('HUGGING_FACE_HUB_TOKEN','secret-fixture-not-real')
    monkeypatch.setenv('HF_TOKEN_PATH','global-fixture-path-never-used')
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    def launch(command,**kw):
        assert command[:3]==['gpu-python.exe','-m','notetaker.workers.gpu_audio']
        assert 'HF_TOKEN' not in kw['env'] and 'HUGGING_FACE_HUB_TOKEN' not in kw['env']
        assert kw['env']['HF_HOME']==str(tmp_path/'offline-cache')
        assert kw['env']['HF_TOKEN_PATH']==str(tmp_path/'offline-cache'/'token')
        assert kw['env']['HF_HUB_DISABLE_IMPLICIT_TOKEN']=='1'
        assert kw['env']['HF_HUB_OFFLINE']=='1'
        return SimpleNamespace(returncode=0,communicate=lambda **kw: ('{"status":"completed"}','')),SimpleNamespace(close=lambda:None)
    monkeypatch.setattr(windows_job,'start_process',launch)
    assert process.run_worker(request,python=Path('gpu-python.exe'),module='notetaker.workers.gpu_audio')['status']=='completed'
