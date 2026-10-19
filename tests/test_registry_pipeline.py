"""Contract/failure tests use authored model replies; native replay is separate."""
import copy
import json
import pytest
from pathlib import Path
from notetaker.domain.information_registry import seed_registry,validate_registry
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService
from notetaker.services.pipeline import Pipeline
from notetaker.engines import registry_summary as engine


def rows(count=8):
    return [{'id':f's{i}','speaker_id':f'v{i%2}','start_ms':i*4000,'end_ms':i*4000+3000,
        'text':f'Je demande une consultation des habitants du quartier numéro {i}.','uncertain':False} for i in range(count)]


def test_every_source_unit_is_examined_and_more_than_six_notes_survive(tmp_path,monkeypatch):
    utterances=rows(8);state={'utterances':utterances,'speakers':{'v0':'Voix 1','v1':'Voix 2'}}
    document=seed_registry('fixture',state);requests=[]
    def call(request,label,instruction,payload,schema,tokens):
        requests.extend(u['id'] for u in payload['units'])
        return {'units':{u['id']:{'notes':[{'subject':'Consultation','type':'proposal','discourse':'own',
            'content':'La personne demande une consultation du quartier '+str(u['id'])+'.','quote':u['text']}],
            'remainder_reason':'Tous les mots restent dans l’inventaire'} for u in payload['units']}}
    monkeypatch.setattr(engine,'call_json',call)
    monkeypatch.setattr(engine.prose,'classify_notes',lambda request,claims,*a:{c['id']:{'kind':'proposal','discourse':'own'} for c in claims})
    monkeypatch.setattr(engine.prose,'verify',lambda request,label,items,**k:{i['id']:dict.fromkeys(['meaning','modality','attribution','relation'],'supported') for i in items})
    result=engine.extract_registry({'registry':document,'utterances':utterances,'workspace':str(tmp_path)})
    assert len(requests)==8 and len(set(requests))==8
    assert len([e for e in result['entries'] if e['category']=='information'])==8
    assert all(e['verification']=='pending' for e in result['entries'] if e['category']=='information')
    assert len(result['processing']['inspected_units'])==8
    assert result['sources']==utterances;validate_registry(result)


def test_failed_model_check_leaves_candidates_and_full_inventory_in_checkpoint(tmp_path,monkeypatch):
    utterances=rows(2);state={'utterances':utterances,'speakers':{'v0':'Voix 1','v1':'Voix 2'}}
    document=seed_registry('fixture',state)
    def call(request,label,instruction,payload,schema,tokens):
        return {'units':{u['id']:{'notes':[{'subject':'Consultation','type':'proposal','discourse':'own',
            'content':'La personne demande une consultation des habitants.','quote':u['text']}],
            'remainder_reason':'À vérifier'} for u in payload['units']}}
    monkeypatch.setattr(engine,'call_json',call)
    monkeypatch.setattr(engine.prose,'classify_notes',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('MODEL_FAILED')))
    with pytest.raises(RuntimeError,match='MODEL_FAILED'):
        engine.extract_registry({'registry':document,'utterances':utterances,'workspace':str(tmp_path),'verification_policy':'eager'})
    saved=json.loads((tmp_path/'registry-checkpoint.json').read_text(encoding='utf-8'))
    assert len(saved['sources'])==2 and len(saved['entries'])==4
    assert all(e['verification']=='pending' for e in saved['entries'])
    assert saved['processing']['status']=='partial';validate_registry(saved)


def test_pipeline_recovers_real_partial_checkpoint_without_approving_or_overwriting_draft(tmp_path,monkeypatch):
    from notetaker.infrastructure.atomic import atomic_json
    from notetaker.services.pipeline import integral_transcript
    store=SessionStore(tmp_path/'data');sid=store.create('Fixture de récupération')
    store.save_analysis(sid,rows(2),{'v0':'Voix 1','v1':'Voix 2'},0)
    store.save_draft(sid,integral_transcript(store.get(sid)));before=store.get(sid)['draft']
    class Models:
        llama=Path('fake-not-executed');llm=Path('fake-not-executed')
        def verify(self):pass
    pipeline=Pipeline(store.root,models=Models())
    def fail(workspace,request,**kwargs):
        doc=copy.deepcopy(request['registry']);doc['processing']['status']='partial'
        atomic_json(workspace/'registry-checkpoint.json',doc);raise RuntimeError('FIXTURE_FAILURE')
    monkeypatch.setattr(pipeline,'_run',fail)
    with pytest.raises(RuntimeError,match='FIXTURE_FAILURE'):pipeline.prepare_registry(sid)
    assert store.get(sid)['draft']==before
    assert RegistryService(store).latest(sid)['content']['processing']['status']=='interrupted'
    store.close()


def test_registry_document_roundtrip_requires_final_human_review_and_valid_provenance(tmp_path,monkeypatch):
    from notetaker.services.session_export import export_session
    from notetaker.domain.minutes import content_digest
    store=SessionStore(tmp_path/'data');sid=store.create('Export de fixture')
    store.save_analysis(sid,rows(1),{'v0':'Personne test'},0)
    service=RegistryService(store);record=service.initialize(sid);doc=copy.deepcopy(record['content'])
    info=copy.deepcopy(doc['entries'][0]);info.update(id='info',category='information',type='proposal',subject='Consultation',discourse='own',
        content='Une consultation des habitants est demandée.',verification='supported')
    doc['entries'].append(info)
    service.save(sid,doc,expected_id=record['id'],actor='Fixture',reason='Information construite')
    point={'title':'Consultation','summary':'La personne demande une consultation des habitants.','sources':['s0'],'vote_id':None,
        'claims':[engine.to_claim(info)]}
    draft={'points':[point],'to_verify':[],'information_registry':{'revision_id':service.latest(sid)['id'],
        'content_sha256':content_digest(doc),'information_ids':['info']}}
    store.save_draft(sid,draft)
    with pytest.raises(ValueError,match='HUMAN_REVIEW'):export_session(store,sid,tmp_path/'fixture.pdf')
    invalid=copy.deepcopy(draft);invalid['information_registry']['content_sha256']='0'*64
    with pytest.raises(ValueError,match='REGISTRY_DOCUMENT_REFERENCE_INVALID'):store.save_draft(sid,invalid)
    store.approve(sid,'Relecture automatisée de fixture uniquement')
    assert Path(export_session(store,sid,tmp_path/'fixture.pdf')).is_file()
    assert Path(export_session(store,sid,tmp_path/'fixture.docx')).is_file()
    did=store.get(sid)['draft']['id'];store.close()
    reopened=SessionStore(tmp_path/'data')
    try:
        assert reopened.get(sid)['draft']['id']==did
        reopened.reviewed_content(sid)
        current=RegistryService(reopened).latest(sid)
        RegistryService(reopened).change(sid,current['id'],'info','exclude',actor='Alice',reason='Information exclue après contrôle')
        with pytest.raises(ValueError,match='REGISTRY_DOCUMENT_REFERENCE_INVALID'):
            reopened.save_draft(sid,draft)
    finally:reopened.close()


def test_routing_conserves_ambiguous_information_and_human_topic_edits(tmp_path,monkeypatch):
    utterances=rows(2);state={'utterances':utterances,'speakers':{'v0':'Voix 1','v1':'Voix 2'}}
    doc=seed_registry('fixture',state)
    for i in range(2):
        info=copy.deepcopy(doc['entries'][i]);info.update(id=f'i{i}',category='information',subject='Sujet manuel' if i==0 else 'Provisoire',
            verification='ambiguous',history=[{'action':'edit'}] if i==0 else [])
        doc['entries'].append(info)
    def call(request,label,instruction,payload,schema,tokens):
        if 'route' in label:return {'assignments':{key:'T0' for key in payload['provisional_groups']}}
        return {'subjects':['Consultation des habitants']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.group_registry({'workspace':str(tmp_path),'utterances':utterances},doc)
    assert [e['subject'] for e in result['entries'] if e['category']=='information']==['Sujet manuel','Consultation des habitants']
    assert len(result['entries'])==4


def test_failed_v4_to_v5_migration_rolls_back_new_table_and_version(tmp_path):
    import sqlite3
    from notetaker.infrastructure.database import migrate,MIGRATIONS
    db=sqlite3.connect(tmp_path/'v4.sqlite3');migrate(db,{k:v for k,v in MIGRATIONS.items() if k<=4})
    with pytest.raises(sqlite3.OperationalError):
        migrate(db,{**{k:v for k,v in MIGRATIONS.items() if k<=4},5:[MIGRATIONS[5][0],'INVALID SQL']})
    assert db.execute('PRAGMA user_version').fetchone()[0]==4
    assert db.execute("SELECT name FROM sqlite_master WHERE name='information_registry'").fetchall()==[]
    db.close()


def test_unknown_voice_is_rejected_for_writing_even_after_information_approval(tmp_path):
    from notetaker.domain.information_registry import admissible
    utterances=[{**rows(1)[0],'speaker_id':None}];doc=seed_registry('fixture',{'utterances':utterances,'speakers':{}})
    info=copy.deepcopy(doc['entries'][0]);info.update(category='information',human_status='approved',verification='supported',type='proposal')
    assert not admissible(info,{'utterances':utterances})


@pytest.mark.parametrize('scenario',['success','concurrent_edit','native_failure'])
def test_generate_service_commits_current_registry_and_draft_or_preserves_existing_data(tmp_path,monkeypatch,scenario):
    from notetaker.domain.information_registry import coverage
    from notetaker.infrastructure.atomic import atomic_json
    store=SessionStore(tmp_path/'data');sid=store.create('Parcours du service')
    store.save_analysis(sid,rows(1),{'v0':'Personne test'},0)
    service=RegistryService(store);record=service.initialize(sid);doc=record['content']
    info=copy.deepcopy(doc['entries'][0]);info.update(id='information',category='information',type='proposal',subject='Consultation',discourse='own',
        content='Une consultation des habitants est demandée.',verification='supported')
    doc['entries'].append(info);service.save(sid,doc,expected_id=record['id'],actor='Fixture',reason='Contrat de worker')
    class Models:
        llama=Path('not-run');llm=Path('not-run')
        def verify(self):pass
    pipeline=Pipeline(store.root,models=Models())
    def fake_worker(workspace,request,**kwargs):
        assert request['task']=='registry_write' and len(request['registry']['sources'])==1
        if scenario=='native_failure':
            ledger=copy.deepcopy(request['registry']);ledger['writing']={'rejected':[{'id':'information','reason':'fixture_rejection'}]}
            atomic_json(workspace/'registry-checkpoint.json',ledger);raise RuntimeError('FIXTURE_NATIVE_FAILURE')
        if scenario=='concurrent_edit':
            active=service.latest(sid)
            service.change(sid,active['id'],'information','exclude',actor='Opératrice test',reason='Modification pendant calcul')
        return {'strategy':'contextual-topic-paragraphs-v1','registry':request['registry'],'claims':[engine.to_claim(info)],
            'topics':[{'title':'Consultation','claims':['information'],'sentences':[{'text':'{{V1}} demande une consultation des habitants.',
                'voice_bindings':{'V1':'v0'},'claim_ids':['information'],'relation':'proposal','machine_verdict':'fixture_only'}]}],
            'diagnostics':{'summary_length':'standard','registry_strategy':'information-registry-v1','registry_coverage':coverage(request['registry'])}}
    monkeypatch.setattr(pipeline,'_run',fake_worker)
    try:
        if scenario=='success':
            assert pipeline.generate(sid)=={'points':1}
            result=store.get(sid)['draft'];assert result['review'] is None
            assert result['content']['information_registry']['revision_id']==service.latest(sid)['id']
            store.approve(sid,'Relecture de fixture uniquement');store.reviewed_content(sid)
        elif scenario=='concurrent_edit':
            with pytest.raises(ValueError,match='SESSION_CHANGED'):pipeline.generate(sid)
            assert store.get(sid)['draft'] is None
            assert service.latest(sid)['content']['entries'][-1]['human_status']=='excluded'
        else:
            with pytest.raises(RuntimeError,match='FIXTURE_NATIVE_FAILURE'):pipeline.generate(sid)
            assert store.get(sid)['draft'] is None
            assert service.latest(sid)['content']['writing']['rejected'][0]['id']=='information'
    finally:store.close()


def test_reclassified_variant_preserves_original_rejection_and_has_independent_verdict(tmp_path,monkeypatch):
    utterances=[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':5000,'text':'Les habitants refusent-ils cette ouverture ?','uncertain':False}]
    doc=seed_registry('fixture',{'utterances':utterances,'speakers':{'a':'Voix 1'}})
    monkeypatch.setattr(engine,'call_json',lambda *a,**k:{'units':{'u0':{'notes':[{'subject':'Ouverture','type':'proposal','discourse':'own',
        'content':'Les habitants refusent cette ouverture.','quote':utterances[0]['text']}],'remainder_reason':'Cas construit'}}})
    monkeypatch.setattr(engine.prose,'classify_notes',lambda request,claims,*a:{c['id']:{'kind':'question','discourse':'question'} for c in claims})
    monkeypatch.setattr(engine.prose,'rephrase_notes',lambda request,claims,*a:{c['id']:'La personne demande si les habitants refusent cette ouverture.' for c in claims})
    monkeypatch.setattr(engine.prose,'verify',lambda request,label,items,**k:{i['id']:dict.fromkeys(['meaning','modality','attribution','relation'],'supported') for i in items})
    result=engine.extract_registry({'registry':doc,'utterances':utterances,'workspace':str(tmp_path),'verification_policy':'eager'})
    information=[e for e in result['entries'] if e['category']=='information']
    assert len(information)==2
    original,variant=information
    assert original['verification']=='rejected' and original['type']=='proposal'
    assert variant['id']!=original['id'] and variant['origin']['alternative_of']==original['id']
    assert variant['type']=='question' and variant['verification']=='supported'
    assert variant['evidence']==original['evidence'] and len(variant['checks'])==4


def test_partial_batch_keeps_full_source_context_and_cannot_be_marked_ready(tmp_path,monkeypatch):
    utterances=rows(8);doc=seed_registry('fixture',{'utterances':utterances,'speakers':{'v0':'Voix 1','v1':'Voix 2'}})
    seen=[]
    def call(request,label,instruction,payload,schema,tokens):
        assert len(request['utterances'])==8
        seen.extend(u['id'] for u in payload['units'])
        return {'units':{u['id']:{'notes':[],'remainder_reason':'Aucune note dans la fixture'} for u in payload['units']}}
    monkeypatch.setattr(engine,'call_json',call)
    request={'registry':doc,'utterances':utterances,'workspace':str(tmp_path),'registry_batch_indices':[1]}
    result=engine.extract_registry(request)
    assert seen==['u6','u7'] and len(result['sources'])==8
    assert result['processing']['status']=='partial_extraction'
    with pytest.raises(ValueError,match='REGISTRY_EXTRACTION_INCOMPLETE'):engine.finalize({**request,'registry':result})


def test_repeated_quote_does_not_guess_the_first_audio_occurrence(tmp_path):
    utterances=[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':2000,'text':'Je propose une consultation.','uncertain':False},
        {'id':'s1','speaker_id':'a','start_ms':2100,'end_ms':4000,'text':'Je propose une consultation.','uncertain':False}]
    doc=seed_registry('fixture',{'utterances':utterances,'speakers':{'a':'Voix 1'}})
    entry=engine.add_candidate(doc,{'utterances':utterances},
        {'subject':'Consultation','type':'proposal','discourse':'own','content':'Une consultation est proposée.','quote':'Je propose une consultation.'},
        engine.source_units(utterances)[0],'fixture')
    assert entry['verification']=='rejected' and entry['evidence']==[]
    assert len(doc['sources'])==2 and entry['origin']['unit_source_ids']==['s0','s1']


def test_on_request_check_of_human_locked_information_is_advisory_only(tmp_path,monkeypatch):
    utterances=rows(1);doc=seed_registry('fixture',{'utterances':utterances,'speakers':{'v0':'Voix 1'}})
    info=copy.deepcopy(doc['entries'][0]);info.update(id='locked',category='information',human_lock=True,verification='pending',
        content='Une consultation des habitants est demandée.',type='proposal',discourse='own')
    doc['entries'].append(info);before=copy.deepcopy(info)
    monkeypatch.setattr(engine.prose,'verify',lambda request,label,items,**k:{i['id']:dict.fromkeys(['meaning','modality','attribution','relation'],'supported') for i in items})
    result=engine.verify_information({'registry':doc,'utterances':utterances,'workspace':str(tmp_path),'information_id':'locked'})
    checked=result['registry']['entries'][-1]
    assert {k:v for k,v in checked.items() if k!='advisory'}==before
    assert checked['advisory']['checks']['meaning']=='supported' and result['focus_id']=='locked'


def test_relation_search_reunites_a_topic_after_intervening_unrelated_subjects(tmp_path,monkeypatch):
    utterances=rows(11)
    utterances[0]['text']='Combien coûtera l’ouverture de la bibliothèque ?'
    utterances[10].update(text='Pour répondre à votre question sur la bibliothèque, le coût reste à établir.',speaker_id='v1',start_ms=600000,end_ms=603000)
    doc=seed_registry('fixture',{'utterances':utterances,'speakers':{'v0':'Voix 1','v1':'Voix 2'}})
    for i in range(11):
        info=copy.deepcopy(doc['entries'][i]);info.update(id=f'i{i}',category='information',subject='Bibliothèque' if i in [0,10] else 'Voirie',
            verification='supported',type='question' if i==0 else 'answer' if i==10 else 'argument')
        doc['entries'].append(info)
    def call(request,label,instruction,payload,schema,tokens):
        items=payload['information']
        if {v['type'] for v in items.values()}=={'question','answer'}:
            return {'relations':[{'from':'I1','to':'I0','kind':'answers','reason':'Relation explicite construite pour le test'}]}
        return {'relations':[]}
    monkeypatch.setattr(engine,'call_json',call)
    monkeypatch.setattr(engine.prose,'verify',lambda request,label,items,**k:{i['id']:dict.fromkeys(['meaning','modality','attribution','relation'],'supported') for i in items})
    result=engine.link_registry({'utterances':utterances,'workspace':str(tmp_path)},doc)
    assert len(result['relations'])==1
    assert result['relations'][0]['from']=='i10' and result['relations'][0]['to']=='i0'
    assert {e['id'] for e in result['relations'][0]['evidence']}=={'s0','s10'}


def test_requested_semantic_failure_keeps_new_variant_in_recoverable_checkpoint(tmp_path,monkeypatch):
    utterances=[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':4000,'text':'Les habitants refusent-ils cette ouverture ?','uncertain':False}]
    doc=seed_registry('fixture',{'utterances':utterances,'speakers':{'a':'Voix 1'}})
    entry=engine.add_candidate(doc,{'utterances':utterances},{'subject':'Ouverture','type':'proposal','discourse':'own',
        'content':'Les habitants refusent cette ouverture.','quote':utterances[0]['text']},engine.source_units(utterances)[0],'fixture')
    monkeypatch.setattr(engine.prose,'classify_notes',lambda request,claims,*a:{c['id']:{'kind':'question','discourse':'question'} for c in claims})
    monkeypatch.setattr(engine.prose,'rephrase_notes',lambda request,claims,*a:{c['id']:'La personne demande si les habitants refusent cette ouverture.' for c in claims})
    monkeypatch.setattr(engine.prose,'verify',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('FIXTURE_MODEL_FAILURE')))
    with pytest.raises(RuntimeError,match='FIXTURE_MODEL_FAILURE'):
        engine.verify_information({'registry':doc,'utterances':utterances,'workspace':str(tmp_path),'information_id':entry['id']})
    recovered=json.loads((tmp_path/'registry-checkpoint.json').read_text(encoding='utf-8'))
    information=[e for e in recovered['entries'] if e['category']=='information']
    assert len(information)==2 and information[-1]['verification']=='pending'
    assert information[-1]['origin']['alternative_of']==entry['id'];validate_registry(recovered)
