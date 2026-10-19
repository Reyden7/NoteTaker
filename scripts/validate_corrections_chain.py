"""Real CPU workers and exports on the known synthetic fixture only, never a meeting."""
import copy
import json
import sys
import time
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from notetaker.services.storage import SessionStore
from notetaker.services.directory import DirectoryService
from notetaker.services.audio import import_audio
from notetaker.services.pipeline import Pipeline
from notetaker.services.session_export import export_session
from notetaker.services.evidence import draft_issues,propose_attribution_refresh,DraftEvidenceError
from notetaker.infrastructure.paths import session_directory
from notetaker.infrastructure.atomic import sha256_file,atomic_json

data=ROOT/'output/corrections-chain'/uuid.uuid4().hex
fixture=ROOT/'output/corrections-fixture/substantive-synthetic.wav'
assert fixture.is_file()
store=SessionStore(data);sid=store.create('Recette automatisée — voix synthétiques, aucune séance réelle',{'municipality':'Commune fictive'})
report={'scope':'known synthetic audio fixture only; actual CPU engines; simulated human actions for export gate testing',
        'data_directory':str(data),'session_id':sid,'human_review_of_real_meeting':False,'real_french_accuracy_measured':False}
started=time.perf_counter()
try:
    path,digest=import_audio(fixture,session_directory(data,sid));store.add_take(sid,'import',path,sha256=digest)
    pipeline=Pipeline(data,progress=lambda s:print(s,flush=True))
    report['analysis']=pipeline.analyse(sid,mode='cpu')
    report['generation']=pipeline.generate(sid,mode='summary')
    state=store.get(sid);draft=copy.deepcopy(state['draft']['content'])
    assert any(p.get('claims') for p in draft['points'])
    claim=next(c for p in draft['points'] for c in p.get('claims',[]))
    ids=list(dict.fromkeys(e['id'] for e in claim['evidence']))
    directory=DirectoryService(store)
    people=[directory.save_person({'first_name':name,'last_name':'TEST FICTIF','position':'Fixture','municipality':'Commune fictive'}) for name in ['Personne A','Personne B']]
    directory.save_participants(sid,[{'person_id':p,'attendance':'present'} for p in people])
    directory.assign_person(sid,ids,people[0]);directory.assign_person(sid,ids,people[1])
    assert draft_issues(draft,store.get(sid))
    proposal,_=propose_attribution_refresh(draft,store.get(sid));assert not draft_issues(proposal,store.get(sid))
    store.save_draft(sid,proposal)
    u=next(u for u in store.get(sid)['utterances'] if u['id']==ids[0])
    cut=u['text'].find(' ',max(1,len(u['text'])//2))
    if cut<0:cut=len(u['text'])//2
    child=store.split_utterance(sid,u['id'],(u['start_ms']+u['end_ms'])//2,cut)
    assert not draft_issues(store.get(sid)['draft']['content'],store.get(sid))
    store.merge_utterances(sid,[u['id'],child])
    assert not draft_issues(store.get(sid)['draft']['content'],store.get(sid))
    protected=copy.deepcopy(next(u for u in store.get(sid)['utterances'] if u['id']==ids[0]))
    report['repeat_analysis']=pipeline.analyse(sid,mode='cpu')
    same=next(u for u in store.get(sid)['utterances'] if u['id']==protected['id'])
    assert all(same[k]==protected[k] for k in ['id','text','speaker_id','start_ms','end_ms','source_json'])
    report['manual_correction_preserved']=True
    report['regeneration']=pipeline.generate(sid,mode='summary')
    state=store.get(sid)
    assert not draft_issues(state['draft']['content'],state)
    try:export_session(store,sid,data/'forbidden.pdf')
    except ValueError:report['unreviewed_export_blocked']=True
    else:raise AssertionError('Export before review')
    store.approve(sid,'AUTOMATED FIXTURE ONLY — NOT A HUMAN REVIEW')
    for ext in ['pdf','docx']:
        export_session(store,sid,data/f'fixture-reviewed.{ext}')
    reopened=SessionStore(data)
    try:assert reopened.reviewed_content(sid)[0]['draft']['content']==state['draft']['content']
    finally:reopened.close()
    report.update({'status':'passed','exports':['pdf','docx'],'reopened_with_review_and_sources':True,
                   'original_audio_unchanged':sha256_file(path)==digest==sha256_file(fixture)})
except BaseException as error:
    report.update({'status':'failed','error_type':type(error).__name__,'error':str(error)})
    raise
finally:
    store.close();report['wall_seconds']=round(time.perf_counter()-started,3)
    atomic_json(ROOT/'docs/evidence/corrections-real-workers-chain.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2),flush=True)
