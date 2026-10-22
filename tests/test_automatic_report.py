import copy
import json
import threading
import uuid
import wave
from datetime import date,timedelta
from pathlib import Path
import pytest
from notetaker.services.storage import SessionStore
from notetaker.services.pipeline import Pipeline
from notetaker.services.voice_profiles import VoiceProfiles,rank_voice
from notetaker.services.working_export import export_working_copy
from notetaker.services.session_export import export_session


def fixture_state(tmp_path):
    store=SessionStore(tmp_path/'data');sid=store.create('Réunion fictive')
    audio=tmp_path/'normalized.wav'
    with wave.open(str(audio),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\0'*32000*3)
    store.save_analysis(sid,[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':3000,'text':'Je propose une consultation des habitants.',
        'uncertain':False,'source':{'normalized_audio':str(audio)}}],{'a':'Intervenant 1'},0)
    return store,sid,audio


def test_direct_draft_without_registry_reuses_transcript_and_keeps_official_gate(tmp_path,monkeypatch):
    store,sid,audio=fixture_state(tmp_path);before=copy.deepcopy(store.get(sid)['utterances'])
    pipeline=Pipeline(store.root)
    monkeypatch.setattr(pipeline.models,'verify',lambda:None)
    monkeypatch.setattr(pipeline,'analyse',lambda *a:pytest.fail('ASR must be reused'))
    def run(workspace,request,**kwargs):
        assert request['task']=='automatic_report' and 'registry' not in request
        assert request['editorial_v4'] and request['discourse_anchors']
        return {'document_mode':'summary','points':[{'title':'Consultation','summary':'Une consultation est proposée.','sources':['s0'],'vote_id':None}],
            'to_verify':['Brouillon non relu.']}
    monkeypatch.setattr(pipeline,'_run',run)
    result=pipeline.automatic_report(sid)
    assert result['transcription_reused'] and store.get(sid)['draft']['review'] is None
    assert store.get(sid)['utterances']==before
    assert store.db.execute('select count(*) from information_registry').fetchone()[0]==0
    for suffix in ('pdf','docx'):
        target=tmp_path/('BROUILLON.'+suffix);export_working_copy(store,sid,target);assert target.exists()
    from pypdf import PdfReader
    reader=PdfReader(tmp_path/'BROUILLON.pdf')
    assert all('NON VALIDÉ' in p.extract_text() or 'NON RELU' in p.extract_text() for p in reader.pages)
    from docx import Document
    doc=Document(tmp_path/'BROUILLON.docx')
    assert 'BROUILLON NON RELU' in doc.sections[0].footer.paragraphs[0].text
    with pytest.raises(ValueError,match='HUMAN_REVIEW'):export_session(store,sid,tmp_path/'official.pdf')
    assert store.get(sid)['draft']['review'] is None
    store.approve(sid,'Relecteur fictif — action explicite du test')
    export_session(store,sid,tmp_path/'reviewed.pdf')
    assert (tmp_path/'reviewed.pdf').exists()
    store.close()


def test_working_export_still_refuses_invalid_source(tmp_path):
    store,sid,audio=fixture_state(tmp_path)
    store.save_draft(sid,{'points':[{'title':'Test','summary':'Test','sources':['missing'],'vote_id':None}],'to_verify':[]},allow_invalid=True)
    with pytest.raises(ValueError):export_working_copy(store,sid,tmp_path/'bad.pdf')
    store.close()


@pytest.mark.parametrize('vectors,refs,status',[
    ([[1,0],[1,0]],{'a':[[1,0]],'b':[[0,1]]},'suggested'),
    ([[0,0,1],[0,0,1]],{'a':[[1,0,0]],'b':[[0,1,0]]},'not_identified'),
    ([[1,0],[1,0]],{'a':[[1,0]],'b':[[1,.01]]},'uncertain'),
    ([[1,0]],{'a':[[1,0]]},'uncertain'),
    ([[1,0],[0,1]],{'a':[[1,0]],'b':[[0,1]]},'uncertain')])
def test_synthetic_match_unknown_nearby_short_and_switch(vectors,refs,status):
    result=rank_voice(vectors,refs,.8,.1)
    assert result['status']==status
    if status!='suggested':assert 'person_id' not in result


def test_windows_dpapi_and_vault_retention_deletion_and_model_binding(tmp_path):
    from notetaker.infrastructure.voice_vault import protect,unprotect
    import sys
    if sys.platform!='win32':pytest.skip('Windows DPAPI required')
    raw=b'fictional pcm marker - NOT A REAL VOICE'
    encrypted=protect(raw);assert encrypted!=raw and unprotect(encrypted)==raw
    vault=VoiceProfiles(tmp_path)
    with pytest.raises(ValueError,match='désactivée'):vault.begin(str(uuid.uuid4()))
    vault.configure({'enabled':True,'legal_reference':'TEST TECHNIQUE FICTIF','authorized_by':'fixture',
        'expires':(date.today()+timedelta(days=1)).isoformat(),'retention_days':1,'threshold':.8,'margin':.1})
    pid=str(uuid.uuid4());sid=vault.begin(pid);vault.append(sid,raw)
    reference={'model_hash':'h1','preprocessing':'pcm16-mono-16000-v1','vectors':[[1,0],[1,0]]}
    vault.finish(sid,reference)
    assert raw not in vault.path.read_bytes()
    assert vault.pcm(sid)==raw and len(vault.references('h1')[pid])==2 and vault.references('h2')=={}
    vault.configure({'enabled':False})
    with pytest.raises(ValueError):vault.pcm(sid)
    vault.delete(pid);assert vault.samples(pid)==[]


def test_engine_keeps_rejected_paraphrase_inventory_and_no_invented_vote(tmp_path,monkeypatch):
    from notetaker.engines import automatic_report as engine
    store,sid,audio=fixture_state(tmp_path);state=store.get(sid)
    calls=[]
    def call(request,label,instruction,inputs,schema,**kwargs):
        calls.append(label)
        if 'check' in label:return {'c0':{'supported':False,'reason':'Proposition devenue décision'}}
        return {'subjects':[{'title':'Décision adoptée','interventions':[{'speaker':'a','kind':'reported_decision',
            'text':'La consultation est adoptée à l’unanimité.','evidence':[{'id':'s0','quote':'Je propose une consultation des habitants.'}],
            'uncertainty':''}]}]}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':state['utterances'],'speaker_labels':{'a':'Voix 1'}})
    assert 'unanimité' not in result['points'][0]['summary']
    assert 'Je propose' in result['points'][0]['summary'] and result['points'][0]['vote_id'] is None
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert 'unanimité' in inventory['items'][0]['text'] and not inventory['items'][0]['checks_passed']
    assert calls==['automatic-0000','automatic-check-0000']
    store.close()


def test_simple_ui_saves_reopens_and_keeps_advanced_tools(tmp_path):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication
    from notetaker.ui.window import MainWindow
    app=QApplication.instance() or QApplication([])
    window=MainWindow(tmp_path/'ui');window.show();app.processEvents()
    assert not window.advanced_mode.isChecked() and window.simple_page.isVisible() and not window.tabs.isVisible()
    sid=window.store.create('Réunion fictive')
    window.store.save_analysis(sid,[{'id':'s0','start_ms':0,'end_ms':1000,'speaker_id':'a','text':'Texte fictif','uncertain':False}],{'a':'Intervenant 1'},0)
    window.store.save_draft(sid,{'points':[{'title':'Sujet','summary':'Texte fictif','sources':['s0'],'vote_id':None}],'to_verify':['À vérifier']})
    window.sid=sid;window.load_session()
    window.simple_page.text.setPlainText('Correction humaine conservée.');window.simple_page.save()
    assert window.store.get(sid)['draft']['content']['points'][0]['summary']=='Correction humaine conservée.'
    window.open_review();assert window.tabs.isVisible() and window.tabs.currentIndex()==3
    window.close();app.processEvents()
    store=SessionStore(tmp_path/'ui')
    assert store.get(sid)['draft']['content']['points'][0]['summary']=='Correction humaine conservée.'
    assert store.get(sid)['draft']['review'] is None;store.close()


def test_new_audio_triggers_existing_analysis_and_failure_preserves_old_draft(tmp_path,monkeypatch):
    from notetaker.infrastructure.process import JobCancelled
    store,sid,audio=fixture_state(tmp_path)
    original={'points':[{'title':'Ancien','summary':'Ancien brouillon conservé','sources':['s0'],'vote_id':None}],'to_verify':[]}
    store.save_draft(sid,original)
    pipeline=Pipeline(store.root)
    monkeypatch.setattr(pipeline.models,'verify',lambda:None)
    monkeypatch.setattr(pipeline,'_run',lambda *a,**k:(_ for _ in ()).throw(JobCancelled('JOB_CANCELLED')))
    with pytest.raises(JobCancelled):pipeline.automatic_report(sid)
    assert store.get(sid)['draft']['content']==original
    assert store.jobs(sid)[-1]['status']=='cancelled'
    # No transcript: orchestrator invokes the unchanged existing analysis service.
    fresh=store.create('Nouvel audio');called=[]
    def analyse(new_sid):
        called.append(new_sid)
        current=store.get(new_sid)
        store.save_analysis(new_sid,[{'id':'s1','speaker_id':'a','text':'Propos fictifs','start_ms':0,'end_ms':2000,
            'uncertain':False,'source':{'normalized_audio':str(audio)}}],{'a':'Intervenant 1'},current['revision'])
    monkeypatch.setattr(pipeline,'analyse',analyse)
    monkeypatch.setattr(pipeline,'_run',lambda *a,**k:{'points':[{'title':'Sujet','summary':'Propos fictifs','sources':['s1'],'vote_id':None}],'to_verify':[]})
    result=pipeline.automatic_report(fresh)
    assert called==[fresh] and not result['transcription_reused'] and store.get(fresh)['draft']['review'] is None
    store.close()


@pytest.mark.parametrize('quote,kind,prose',[
    ('Pourquoi augmenter ce budget ?','argument','Le budget doit augmenter.'),
    ('Je propose une consultation des habitants.','proposal','Une consultation de 5000 euros est proposée.'),
    ('Je raconte mon expérience personnelle.','proposal','Une réforme est proposée.'),
    ('Je ne suis pas contre cette proposition.','position','La personne soutient cette proposition.')])
def test_deterministic_checks_do_not_promote_known_distortions(tmp_path,monkeypatch,quote,kind,prose):
    from notetaker.engines import automatic_report as engine
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'check' in label:return {'c0':{'supported':True,'reason':'Faux avis machine de fixture'}}
        return {'subjects':[{'title':'Sujet','interventions':[{'speaker':'a','kind':kind,'text':prose,
            'evidence':[{'id':'s0','quote':quote}],'uncertainty':''}]}]}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':[{'id':'s0','speaker_id':'a','text':quote,
        'start_ms':0,'end_ms':4000}],'speaker_labels':{'a':'Voix 1'}})
    assert result['generation_diagnostics']['paraphrase_claims']==0
    assert prose not in result['points'][0]['summary'] and quote in result['points'][0]['summary']


def test_long_meeting_all_segments_reach_bounded_blocks():
    from notetaker.engines.hierarchical_summary import coherent_blocks
    rows=[{'id':str(i),'speaker_id':str(i%4),'text':'Une intervention de réunion. '*8,
        'start_ms':i*10000,'end_ms':(i+1)*10000} for i in range(1080)]
    blocks=list(coherent_blocks(rows,max_characters=6000,max_seconds=180,overlap=1))
    assert {r['id'] for b in blocks for r in b}=={r['id'] for r in rows}
    assert all(sum(len(r['text']) for r in b)<=6000 for b in blocks)


def test_encrypted_microphone_writer_uses_no_plaintext_journal(tmp_path,monkeypatch):
    from notetaker.services.voice_capture import EncryptedVoiceCapture
    import sys,types
    vault=VoiceProfiles(tmp_path)
    vault.configure({'enabled':True,'legal_reference':'Fixture technique fictive','authorized_by':'test',
        'expires':(date.today()+timedelta(days=1)).isoformat(),'retention_days':1})
    data=b'\x01\x02'*2048
    class Stream:
        def __init__(self,**kwargs):self.callback=kwargs['callback']
        def start(self):self.callback(data,2048,None,None);self.callback(data,2048,None,None)
        def stop(self):pass
        def close(self):pass
    monkeypatch.setitem(sys.modules,'sounddevice',types.SimpleNamespace(RawInputStream=Stream))
    capture=EncryptedVoiceCapture(vault,str(uuid.uuid4()));capture.start(0);capture.stop()
    assert not capture.error and capture.frames==4096
    assert vault.pcm(capture.sample_id)==data*2
    assert data not in vault.path.read_bytes()
    assert not list(tmp_path.rglob('*.pcm')) and not list(tmp_path.rglob('*.wav'))
    assert vault.samples()[0]['state']=='pending'
    with vault.connection() as db:db.execute("UPDATE sample SET expires='2000-01-01'")
    assert vault.purge_expired()==1 and vault.samples()==[]


def test_cache_is_short_context_bound_and_explicitly_reported(tmp_path,monkeypatch):
    store,sid,audio=fixture_state(tmp_path);pipeline=Pipeline(store.root)
    monkeypatch.setattr(pipeline.models,'verify',lambda:None)
    seen=[]
    def run(workspace,request,**kwargs):
        cache=Path(request['cache_workspace']);seen.append(cache)
        assert len(cache.name)==24
        assert len(json.loads((cache/'cache-key.json').read_text())['sha256'])==64
        (cache/'fixture.result.json').write_text('{}')
        return {'points':[{'title':'Sujet','summary':'Une consultation est proposée.','sources':['s0'],'vote_id':None}],'to_verify':[]}
    monkeypatch.setattr(pipeline,'_run',run)
    first=pipeline.automatic_report(sid);second=pipeline.automatic_report(sid)
    assert first['cache_results_available_before_run']==[]
    assert second['cache_results_available_before_run']==['fixture.result.json']
    assert seen[0]==seen[1]
    store.close()


def test_cache_resume_prefers_newer_results_to_obsolete_seed_files(tmp_path,monkeypatch):
    import os
    from notetaker.infrastructure.paths import session_directory
    store,sid,audio=fixture_state(tmp_path);state=store.get(sid);pipeline=Pipeline(store.root)
    monkeypatch.setattr(pipeline.models,'verify',lambda:None)
    for index,label in enumerate(('obsolete','newer'),1):
        jid=store.start_job(sid,'automatic-report')
        folder=session_directory(store.root,sid)/'jobs'/jid;folder.mkdir(parents=True)
        (folder/'editorial-fixture.result.json').write_text(json.dumps({'from':label}))
        request=folder/'llm-cpu.request.json'
        request.write_text(json.dumps({'task':'automatic_report','utterances':state['utterances'],'agenda':[],'lexicon':[]}))
        os.utime(request,ns=(index*1_000_000_000,index*1_000_000_000))
        store.finish_job(jid,True)
    def run(workspace,request,**kwargs):
        # The inference helper still checks the full identity. This service test
        # catches the earlier first-file-wins loss before that helper is called.
        assert json.loads((Path(request['cache_workspace'])/'editorial-fixture.result.json').read_text())=={'from':'newer'}
        return {'points':[{'title':'Consultation','summary':'Une consultation est proposée.','sources':['s0'],'vote_id':None}],'to_verify':[]}
    monkeypatch.setattr(pipeline,'_run',run)
    pipeline.automatic_report(sid)
    store.close()


@pytest.mark.parametrize('source,text,reason',[
    ("Nous n'avons pas fait une délibération avec débat à chaque fois.",
     'Des ventes ont été réalisées sans délibération.','absence_of_debate_changed_to_absence_of_deliberation'),
    ('Le tractopelle date de 1997, je pense que ça ne coûtait pas énormément.',
     'La personne insiste sur la nécessité de transparence.','transparency_requirement_not_in_cited_source'),
    ('Nous voyons apparaître ces petits panneaux.',
     'La personne critique les panneaux publicitaires.','advertising_qualification_not_in_source'),
    ("Nous aimerions des réponses quand on pose des questions sur RESS.",
     'La personne dénonce une absence de projet politique clair.','political_project_requires_its_own_source'),
    ("Nous avons géré l'argent public avec honneur et probité.",
     'Les messages ne reflètent pas une gestion responsable.','defence_of_management_changed_to_accusation'),
    ('Nous avons une vague idée, mais nous voulons des réponses quand nous posons des questions sur RESS.',
     'La personne reconnaît une vague idée sur RESS.','unspecified_idea_assigned_to_a_specific_topic'),
    ("Nous n'avons pas fait de conférence de presse à chaque fois.",
     "La personne critique l'absence de conférence de presse.",'historical_practice_changed_to_objection'),
    ('Soit vous nous accusez réellement, soit cette petite musique que vous laissez entendre est déplacée.',
     'La personne rejette une accusation.','insinuation_changed_to_formal_accusation')])
def test_observed_municipal_context_errors_are_not_promoted(source,text,reason):
    from notetaker.engines.automatic_report import contextual_risk
    assert contextual_risk(text,[source])==reason


def test_single_targeted_repair_keeps_original_and_rechecks_sources(tmp_path,monkeypatch):
    from notetaker.engines import automatic_report as engine
    quote="Nous n'avons pas fait une délibération avec débat à chaque fois."
    original='Les ventes ont été faites sans délibération.'
    corrected='La personne indique que les délibérations ne donnaient pas systématiquement lieu à un débat.'
    labels=[]
    def call(request,label,instruction,inputs,schema,**kwargs):
        labels.append(label)
        if 'repair-check' in label or ('check' in label and 'repair' not in label):
            return {'c0':{'supported':True,'reason':'Avis machine de test'}}
        if 'repair' in label:
            assert inputs['items'][0]['reason']=='absence_of_debate_changed_to_absence_of_deliberation'
            return {'revisions':{'c0':{'topic':'Débat','text':corrected,'kind':'reported_action','uncertainty':''}}}
        return {'paragraphs':[{'topic':'Débat','speaker':'V1','nature':'argument','text':original,'sources':['s0'],'uncertainty':''}]}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'repair_rejected':True,'utterances':[{'id':'s0','speaker_id':'a',
        'text':quote,'start_ms':0,'end_ms':4000}],'speaker_labels':{'a':'Voix 1'}})
    assert result['generation_diagnostics']['paraphrase_claims']==1 and corrected in result['points'][0]['summary']
    assert result['points'][0]['claims'][0]['kind']=='argument'
    record=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))['items'][0]
    assert record['original_text']==original and record['repair_attempted'] and record['evidence'][0]['quote']==quote
    assert labels==['automatic-0000','automatic-check-0000','automatic-repair-0000','automatic-repair-check-0000']


def test_failed_repair_still_returns_safe_draft_and_keeps_error(tmp_path,monkeypatch):
    from notetaker.engines import automatic_report as engine
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'repair' in label:raise RuntimeError('Échec natif fictif')
        if 'check' in label:return {'c0':{'supported':True,'reason':'Avis de fixture'}}
        return {'paragraphs':[{'topic':'Consultation','speaker':'V1','nature':'proposition','text':'Une consultation de 5000 euros est proposée.',
            'sources':['s0'],'uncertainty':''}]}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'repair_rejected':True,'utterances':[{'id':'s0','speaker_id':'a',
        'text':'Je propose une consultation.','start_ms':0,'end_ms':3000}],'speaker_labels':{'a':'Voix 1'}})
    assert '5000' not in result['points'][0]['summary'] and 'Je propose' in result['points'][0]['summary']
    assert any('réécriture ciblée' in w for w in result['to_verify'])
    assert (tmp_path/'automatic-repair-error-0000.json').exists()


def test_exact_known_compound_names_are_kept_but_new_names_still_rejected():
    from notetaker.engines.topic_summary import identity_problem
    claims=[{'evidence':[{'quote':'Nous parlons de Clermont-Ferrand et de ChatGPT.'}]}]
    assert identity_problem('La personne cite Clermont-Ferrand et ChatGPT.',claims) is None
    assert identity_problem('La personne cite Clermont-Autre.',claims)=='unsupported_proper_name'


def test_compact_model_format_uses_aliases_and_exact_server_sources(tmp_path,monkeypatch):
    from notetaker.engines import automatic_report as engine
    from notetaker.services.evidence import draft_issues
    store,sid,audio=fixture_state(tmp_path);state=store.get(sid)
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'check' in label:return {'c0':{'supported':True,'reason':'Avis machine de fixture'}}
        assert inputs['turns'][0]['speaker']=='V1' and 'paragraphs' in schema['properties']
        return {'paragraphs':[{'topic':'Consultation','speaker':'V1','nature':'proposition',
            'text':'Une consultation des habitants est proposée.','sources':['s0'],'uncertainty':'Les modalités restent à préciser.'}]}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':state['utterances'],'speaker_labels':{'a':'Voix 1'}})
    assert result['generation_diagnostics']['paraphrase_claims']==1
    assert 'Intervenant non identifié' in result['points'][0]['summary']
    assert result['points'][0]['claims'][0]['evidence']==[{'id':'s0','quote':state['utterances'][0]['text']}]
    assert not draft_issues(result,state)
    store.save_draft(sid,result)
    changed=copy.deepcopy(state);changed['speakers']['a']='Nouveau nom manuel'
    assert any(i['reason']=='narrative_voice_changed' for i in draft_issues(result,changed))
    store.close()
