"""Authored invariants, not human annotations of the French debate."""
import copy
import json
import sqlite3
import pytest
from notetaker.domain.information_registry import seed_registry,validate_registry,admissible,coverage,to_claim
from notetaker.services.information_registry import RegistryService
from notetaker.services.storage import SessionStore
from notetaker.engines import registry_summary as engine


@pytest.fixture
def sample(tmp_path):
    store=SessionStore(tmp_path/'data');sid=store.create('Conseil de test')
    rows=[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':3000,'text':'Faut-il ouvrir une bibliothèque le dimanche ?','uncertain':False,
           'source':{'automatic_attribution':False}},
          {'id':'s1','speaker_id':'b','start_ms':3000,'end_ms':7000,'text':'Je propose une consultation des habitants avant cette ouverture.','uncertain':False},
          {'id':'s2','speaker_id':None,'start_ms':7100,'end_ms':7500,'text':'','uncertain':True}]
    store.save_analysis(sid,rows,{'a':'Élodie Martin','b':'Voix 2'},0)
    yield store,sid,RegistryService(store)
    store.close()


def add_information(sample):
    store,sid,service=sample;record=service.initialize(sid);doc=record['content']
    entry=copy.deepcopy(doc['entries'][0]);entry.update(id='info-stable',category='information',subject='Bibliothèque',type='question',
        discourse='question',content='La personne demande si la bibliothèque doit ouvrir le dimanche.',verification='supported',reasons=[])
    doc['entries'].append(entry)
    service.save(sid,doc,expected_id=record['id'],actor='Fixture',reason='Donnée construite')
    return service.latest(sid)


def test_inventory_includes_empty_and_uncertain_sources_and_ids_are_repeatable(sample):
    store,sid,service=sample;state=store.get(sid)
    a=seed_registry(sid,state);b=seed_registry(sid,state)
    assert a==b and len(a['entries'])==3 and a['entries'][2]['content']==''
    assert a['entries'][0]['author_status']=='confirmed'
    assert a['entries'][1]['author_status']=='automatic'
    assert a['entries'][2]['author_status']=='unknown'
    validate_registry(a)


def test_invalid_source_may_remain_visible_but_never_be_approved(sample):
    _,sid,service=sample;record=add_information(sample)
    service.change(sid,record['id'],'info-stable','edit',actor='Alice',reason='Citation à corriger',updates={'evidence':[{'id':'s0','quote':'phrase inventée'}]})
    record=service.latest(sid);entry=record['content']['entries'][-1]
    assert entry['id']=='info-stable' and entry['verification']=='pending'
    assert not admissible(entry,{'utterances':record['content']['sources']})
    with pytest.raises(ValueError,match='REGISTRY_INVALID_SOURCE'):
        service.change(sid,record['id'],entry['id'],'approve',actor='Alice',reason='Erreur')


def test_human_correction_move_exclusion_reopen_and_reopen_database_keep_history(sample):
    store,sid,service=sample;record=add_information(sample)
    service.change(sid,record['id'],'info-stable','edit',actor='Alice',reason='Sujet plus précis',updates={'subject':'Horaires de la bibliothèque'})
    record=service.latest(sid);assert record['content']['entries'][-1]['human_status']=='pending'
    service.change(sid,record['id'],'info-stable','approve',actor='Alice',reason='Écoute et sens vérifiés')
    record=service.latest(sid);assert record['content']['entries'][-1]['human_status']=='approved'
    service.change(sid,record['id'],'info-stable','exclude',actor='Alice',reason='Hors périmètre')
    record=service.latest(sid);assert not admissible(record['content']['entries'][-1],store.get(sid))
    service.change(sid,record['id'],'info-stable','reopen',actor='Alice',reason='À reprendre')
    other=SessionStore(store.root)
    try:
        latest=RegistryService(other).latest(sid)
        assert latest['content']['entries'][-1]['subject']=='Horaires de la bibliothèque'
        assert len(latest['content']['entries'][-1]['history'])==4
        assert len(RegistryService(other).history(sid))==6
        assert not other.get(sid)['draft']
    finally:other.close()


def test_concurrent_change_refuses_stale_writer(sample):
    _,sid,service=sample;record=add_information(sample)
    service.change(sid,record['id'],'info-stable','approve',actor='Alice',reason='Contrôlé')
    with pytest.raises(ValueError,match='REGISTRY_CONCURRENT_CHANGE'):
        service.save(sid,record['content'],expected_id=record['id'],actor='Worker',reason='Ancien résultat')


def test_explicit_doubt_removes_machine_supported_information_from_writing(sample):
    store,sid,service=sample;record=add_information(sample)
    assert admissible(record['content']['entries'][-1],store.get(sid))
    service.change(sid,record['id'],'info-stable','reopen',actor='Alice',reason='Le sens me paraît déformé')
    entry=service.latest(sid)['content']['entries'][-1]
    assert entry['human_lock'] and entry['verification']=='pending'
    assert not admissible(entry,store.get(sid))
    record=service.latest(sid);incoming=copy.deepcopy(record['content'])
    incoming['entries'][-1]['verification']='supported'
    with pytest.raises(ValueError,match='HUMAN_CHANGE_PROTECTED'):
        service.save(sid,incoming,expected_id=record['id'],actor='Worker',reason='Recalcul')
    service.change(sid,record['id'],'info-stable','approve',actor='Alice',reason='Nouveau contrôle réel')
    assert service.latest(sid)['content']['entries'][-1]['human_status']=='approved'


@pytest.mark.parametrize('action',['edit','split','merge','rename'])
def test_source_changes_mark_registry_stale_and_preserve_old_information(sample,action):
    store,sid,service=sample;record=add_information(sample)
    if action=='edit':store.edit_utterance(sid,'s0','Texte modifié','a')
    elif action=='split':store.split_utterance(sid,'s0',1500,8)
    elif action=='rename':
        with store.db:store.db.execute("UPDATE speaker SET label='Autre nom' WHERE session_id=? AND id='a'",(sid,))
    else:
        store.edit_utterance(sid,'s1',store.get(sid)['utterances'][1]['text'],'a')
        store.merge_utterances(sid,['s0','s1'])
    assert service.latest(sid)['stale']
    new=service.initialize(sid)
    old_info=next(e for e in new['content']['entries'] if e['id']=='info-stable')
    assert old_info['verification']=='insufficient' and old_info['content']==record['content']['entries'][-1]['content']
    assert not new['stale'] and len(service.history(sid))==3


def test_source_inventory_cannot_disappear_or_be_changed(sample):
    _,_,service=sample;doc=service.initialize(sample[1])['content']
    invalid=copy.deepcopy(doc);invalid['entries'].pop()
    with pytest.raises(ValueError,match='INVENTORY_INCOMPLETE'):validate_registry(invalid)
    invalid=copy.deepcopy(doc);invalid['sources'][0]['text']='Modifié'
    with pytest.raises(ValueError,match='SNAPSHOT_CHANGED'):validate_registry(invalid)


def test_potential_decision_is_never_an_automatic_municipal_decision(sample):
    store,sid,service=sample;record=add_information(sample);entry=record['content']['entries'][-1]
    entry.update(type='potential_decision',human_status='approved')
    assert not admissible(entry,store.get(sid))
    assert store.get(sid)['decisions']==[] and store.get(sid)['votes']==[]


def test_uncertain_attribution_does_not_become_writable_from_machine_semantic_support(sample):
    store,sid,service=sample;state=copy.deepcopy(store.get(sid));state['utterances'][0]['uncertain']=True
    doc=seed_registry(sid,state);info=copy.deepcopy(doc['entries'][0])
    info.update(id='uncertain',category='information',verification='supported')
    assert info['author_status']=='uncertain' and not admissible(info,state)
    info['human_status']='approved';assert admissible(info,state)


def test_raw_source_correction_creates_information_without_mutating_inventory(sample):
    _,sid,service=sample;record=service.initialize(sid);source=copy.deepcopy(record['content']['entries'][0])
    new_id=service.change(sid,record['id'],source['id'],'edit',actor='Alice',reason='Question du débat',updates={
        'content':'La personne interroge une ouverture le dimanche.','type':'question','discourse':'question'})
    latest=service.latest(sid)['content']
    assert latest['entries'][0]==source and new_id!=source['id'] and latest['entries'][-1]['category']=='information'


def test_rejected_candidate_and_source_remainder_never_disappear(sample,tmp_path):
    store,sid,_=sample;state=store.get(sid);doc=seed_registry(sid,state)
    units=engine.source_units(state['utterances']);request={'utterances':state['utterances'],'workspace':str(tmp_path)}
    candidate={'subject':'Bibliothèque','type':'question','discourse':'question','content':'La personne demande une ouverture.','quote':'citation absente'}
    entry=engine.add_candidate(doc,request,candidate,units[0],'fixture')
    assert entry['verification']=='rejected' and entry['origin']['raw_candidate']==candidate
    assert engine.add_candidate(doc,request,candidate,units[0],'fixture') is entry
    engine.refresh_source_rows(doc);validate_registry(doc)
    assert doc['entries'][0]['unrepresented_text']==state['utterances'][0]['text']
    assert coverage(doc)['source_segments_without_candidate_citation']==3


def test_relation_requires_both_endpoints_and_explicit_human_confirmation(sample):
    _,sid,service=sample;record=add_information(sample)
    doc=copy.deepcopy(record['content']);other=copy.deepcopy(doc['entries'][-1]);other.update(id='other',type='answer')
    doc['entries'].append(other);service.save(sid,doc,expected_id=record['id'],actor='Fixture',reason='Deuxième information')
    record=service.latest(sid)
    service.relation(sid,record['id'],actor='Alice',reason='Réponse explicitement vérifiée',source_id='other',target_id='info-stable',kind='answers')
    doc=service.latest(sid)['content'];assert doc['relations'][0]['human_status']=='approved'
    invalid=copy.deepcopy(doc);invalid['relations'][0]['evidence']=[]
    with pytest.raises(ValueError,match='RELATION_SOURCES_REQUIRED'):validate_registry(invalid)


def test_migration_v4_preserves_existing_draft_reviews_and_creates_consistent_backup(tmp_path):
    from notetaker.infrastructure.database import migrate,MIGRATIONS,open_database
    path=tmp_path/'legacy.sqlite3';db=sqlite3.connect(path)
    migrate(db,{k:v for k,v in MIGRATIONS.items() if k<=4})
    with db:
        db.execute("INSERT INTO session(id,title) VALUES('s','Conseil')")
        db.execute("INSERT INTO draft_minutes(id,session_id,revision,content_json,review_json,context_sha256) VALUES('d','s',1,'{}','{\"reviewer\":\"Alice\"}','hash')")
    before=db.execute('SELECT * FROM draft_minutes').fetchall();db.close()
    db=open_database(path)
    assert db.execute('PRAGMA user_version').fetchone()[0]==5
    assert db.execute('SELECT * FROM draft_minutes').fetchall()==before
    assert db.execute('SELECT COUNT(*) FROM information_registry').fetchone()[0]==0
    backups=list((tmp_path/'migration-backups').glob('*.sqlite3'));assert len(backups)==1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute('PRAGMA user_version').fetchone()[0]==4
        assert backup.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    db.close()


def test_approved_information_does_not_approve_document_and_registry_change_invalidates_context(sample):
    from notetaker.services.pipeline import integral_transcript
    store,sid,service=sample;record=add_information(sample)
    store.save_draft(sid,integral_transcript(store.get(sid)));store.approve(sid,'Fixture seulement')
    previous=store.context_hash(sid)
    service.change(sid,record['id'],'info-stable','approve',actor='Alice',reason='Vérifié')
    assert store.context_hash(sid)!=previous
    assert store.get(sid)['draft']['review']  # Historic record preserved, but context is stale.
    with pytest.raises(ValueError,match='HUMAN_REVIEW'):store.reviewed_content(sid)


@pytest.mark.parametrize('problem',['damaged','empty','different_source','length'])
def test_worker_boundary_keeps_legacy_transcription_and_length_gates(sample,problem):
    from notetaker.domain.information_registry import validate_generation_input
    store,sid,service=sample;document=service.initialize(sid)['content']
    request={'task':'registry_write','registry':document,'utterances':copy.deepcopy(document['sources'])}
    validate_generation_input(request)
    if problem=='damaged':request['utterances'][0]['text']='Texte endommagé \ufffd';expected='DAMAGED_TRANSCRIPT'
    elif problem=='empty':request['utterances']=[];expected='TRANSCRIPT_REQUIRED'
    elif problem=='different_source':request['utterances'][0]['end_ms']+=1;expected='REGISTRY_SNAPSHOT_CHANGED'
    else:request['summary_length']='unbounded';expected='INVALID_SUMMARY_LENGTH'
    with pytest.raises(ValueError,match=expected):validate_generation_input(request)
