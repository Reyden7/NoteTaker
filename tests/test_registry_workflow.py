"""Regression fixtures, never human annotations of the municipal recording."""
import copy
import json
import threading
import time
from pathlib import Path
import pytest
from notetaker.engines import registry_summary as engine
from notetaker.domain.information_registry import seed_registry,stable_id,admissible
from notetaker.services.registry_workflow import approval_blockers,preparation_report
from notetaker.services.information_registry import RegistryService
from notetaker.services.storage import SessionStore
from notetaker.services.pipeline import Pipeline


def state():
    return {'utterances':[{'id':'s0','speaker_id':'a','start_ms':1000,'end_ms':5000,
        'text':'Je conteste cette procédure, car le conseil doit en débattre avant toute communication.',
        'uncertain':False}], 'speakers':{'a':'Intervenant 1'}}


def candidate():
    return {'subject':'Débat avant communication','type':'objection','discourse':'own',
        'content':'La personne conteste la procédure et demande un débat du conseil avant la communication.',
        'quote':state()['utterances'][0]['text']}


def test_extraction_keeps_criticism_quote_first_and_does_not_supply_voice_alias(tmp_path,monkeypatch):
    original=state();document=seed_registry('fixture',original)
    def call(request,label,instruction,payload,schema,tokens):
        assert list(schema['properties']['units']['properties']['u0']['properties']['notes']['items']['properties'])[0]=='quote'
        assert all('speaker' not in u for u in payload['units'])
        assert 'même sans action future' in instruction
        return {'units':{'u0':{'notes':[candidate()],'remainder_reason':'Critique conservée ; aucune décision établie.'}}}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.extract_registry({'registry':document,'utterances':original['utterances'],'workspace':str(tmp_path)})
    infos=[e for e in result['entries'] if e['category']=='information']
    assert len(infos)==1 and infos[0]['evidence'][0]['id']=='s0'
    assert infos[0]['verification']=='pending' and infos[0]['human_status']=='pending'
    assert not approval_blockers(infos[0],original)
    assert result['sources']==original['utterances'] and not admissible(infos[0],original)


def test_contract_upgrade_reextracts_and_failure_cannot_mark_old_units_done(tmp_path,monkeypatch):
    original=state();document=seed_registry('fixture',original)
    document['processing']={'extraction_contract':'typed-variants-v2',
        'inspected_units':[stable_id('fixture','unit',['s0'])],'status':'ready_for_review'}
    def fail(*args,**kw):raise RuntimeError('fixture_native_failure')
    monkeypatch.setattr(engine,'call_json',fail)
    with pytest.raises(RuntimeError):engine.extract_registry({'registry':document,'utterances':original['utterances'],'workspace':str(tmp_path)})
    saved=json.loads((tmp_path/'registry-checkpoint.json').read_text(encoding='utf-8'))
    assert saved['processing']['inspected_units']==[]
    assert saved['processing']['extraction_contract']==engine.EXTRACTION_CONTRACT
    assert saved['sources']==original['utterances']


def test_resume_does_not_reextract_current_units_and_preserves_human_entries(tmp_path,monkeypatch):
    original=state();document=seed_registry('fixture',original)
    info=engine.add_candidate(document,{'utterances':original['utterances']},candidate(),engine.source_units(original['utterances'])[0],'fixture')
    info.update(human_lock=True,human_status='approved')
    before=copy.deepcopy(info)
    document['processing']={'extraction_contract':engine.EXTRACTION_CONTRACT,'inspected_units':[stable_id('fixture','unit',['s0'])]}
    monkeypatch.setattr(engine,'call_json',lambda *a,**k:pytest.fail('No repeated extraction'))
    result=engine.extract_registry({'registry':document,'utterances':original['utterances'],'workspace':str(tmp_path)})
    assert result['entries'][-1]==before


def test_preparing_completed_current_contract_reuses_without_llm_or_human_change(tmp_path,monkeypatch):
    original=state();document=seed_registry('fixture',original)
    document['processing']={'extraction_contract':engine.EXTRACTION_CONTRACT,'status':'ready_for_review',
        'inspected_units':[stable_id('fixture','unit',['s0'])]}
    monkeypatch.setattr(engine,'call_json',lambda *a,**k:pytest.fail('No redundant inference'))
    result=engine.prepare({'registry':document,'utterances':original['utterances'],'workspace':str(tmp_path)})
    assert result['reused'] and result['registry']==document


def test_previous_machine_proposals_stay_consultable_but_human_work_is_protected():
    original=state();document=seed_registry('fixture',original)
    info=engine.add_candidate(document,{'utterances':original['utterances']},candidate(),engine.source_units(original['utterances'])[0],'fixture')
    info['origin']['extraction_contract']='typed-variants-v2';info['verification']='supported'
    human=copy.deepcopy(info);human.update(id='human-kept',human_lock=True,human_status='approved');document['entries'].append(human)
    before=copy.deepcopy(human)
    engine.separate_previous_proposals(document)
    assert info['previous_extraction'] and not admissible(info,original)
    assert document['entries'][-1]==before and admissible(human,original)
    assert info['content']==candidate()['content'] and info['evidence']


def test_requested_control_uses_short_native_labels_without_changing_information_ids(tmp_path,monkeypatch):
    original=state();document=seed_registry('fixture',original);labels=[]
    info=engine.add_candidate(document,{'utterances':original['utterances']},candidate(),engine.source_units(original['utterances'])[0],'fixture')
    def classify(request,claims,by_id,label):
        labels.append(label)
        return {c['id']:{'kind':'argument','discourse':'own'} for c in claims}
    monkeypatch.setattr(engine.prose,'classify_notes',classify)
    monkeypatch.setattr(engine.prose,'verify',lambda request,label,items,**kw:{i['id']:dict.fromkeys(['meaning','modality','attribution','relation'],'supported') for i in items})
    result=engine.verify_information({'registry':document,'utterances':original['utterances'],
        'workspace':str(tmp_path),'information_id':info['id']})
    assert all(len(label)<40 for label in labels)
    assert result['registry']['entries'][-1]['id']==info['id'] and len(info['id'])==36


@pytest.mark.parametrize('problem,expected',[
    ('alias','internal_voice_alias_in_content'),('literal','verbatim_transcription_not_a_summary'),
    ('question','question_changed_to_assertion'),('missing','missing_evidence'),
    ('invented_quote','quote_not_in_source'),('empty_interval','source_interval_empty'),
    ('unknown','unknown_source_voice'),('greeting','greeting_not_substantive')])
def test_approval_guard_reuses_safety_rules(problem,expected):
    original=state();document=seed_registry('fixture',original)
    info=engine.add_candidate(document,{'utterances':original['utterances']},candidate(),engine.source_units(original['utterances'])[0],'fixture')
    if problem=='alias':info['content']='V1 critique la procédure.'
    if problem=='literal':info['content']=original['utterances'][0]['text']
    if problem=='question':info.update(type='question',discourse='question',content='Le conseil confirme la procédure.')
    if problem=='missing':info['evidence']=[]
    if problem=='invented_quote':info['evidence'][0]['quote']='Le conseil a voté douze voix pour.'
    if problem=='empty_interval':original['utterances'][0]['end_ms']=1000;info['evidence'][0]['end_ms']=1000
    if problem=='unknown':original['utterances'][0]['speaker_id']=None;info['speaker']='unattributed'
    if problem=='greeting':original['utterances'][0]['text']='Merci.';info['evidence'][0]['quote']='Merci.'
    assert expected in approval_blockers(info,original)


def test_partial_extraction_does_not_claim_unexamined_sources_have_no_information(tmp_path):
    original=state();document=seed_registry('fixture',original)
    engine.refresh_source_rows(document)
    assert 'not_analyzed' in document['entries'][0]['reasons']
    assert 'no_candidate_citation' not in document['entries'][0]['reasons']


def test_unresolved_quote_reports_proposed_information_instead_of_disappearing(tmp_path):
    original=state();document=seed_registry('fixture',original);c=candidate();c['quote']='citation absente'
    entry=engine.add_candidate(document,{'utterances':original['utterances']},c,engine.source_units(original['utterances'])[0],'fixture')
    engine.refresh_source_rows(document)
    assert document['entries'][0]['unlinked_candidate_ids']==[entry['id']]
    report=preparation_report(document,original)
    assert report['created_information_entries']==1 and report['blocked_information_entries']==1


def test_human_approval_does_not_bypass_question_safety_and_is_persistent(tmp_path):
    store=SessionStore(tmp_path/'data');sid=store.create('Fixture')
    try:
        original=state();store.save_analysis(sid,original['utterances'],original['speakers'],0)
        service=RegistryService(store);record=service.initialize(sid);d=record['content']
        info=engine.add_candidate(d,{'utterances':original['utterances']},candidate(),engine.source_units(original['utterances'])[0],'fixture')
        info.update(type='question',discourse='question',content='Le conseil a confirmé la procédure.')
        service.save(sid,d,expected_id=record['id'],actor='Fixture',reason='Donnée de test')
        record=service.latest(sid)
        with pytest.raises(ValueError,match='APPROVAL_BLOCKED'):
            service.change(sid,record['id'],info['id'],'approve',actor='Fixture',reason='Doit être refusé')
        assert service.latest(sid)['id']==record['id']
        service.change(sid,record['id'],info['id'],'edit',actor='Fixture',reason='Correction explicite',updates={
            'type':'objection','discourse':'own','content':candidate()['content']})
        record=service.latest(sid)
        service.change(sid,record['id'],info['id'],'approve',actor='TEST AUTOMATISÉ',reason='Fixture uniquement')
        assert store.get(sid)['draft'] is None
    finally:store.close()
    other=SessionStore(tmp_path/'data')
    try:assert RegistryService(other).latest(sid)['content']['entries'][-1]['human_status']=='approved'
    finally:other.close()


def test_registry_progress_is_read_from_worker_without_changes_to_sources(tmp_path,monkeypatch):
    import notetaker.services.pipeline as pipeline
    from notetaker.infrastructure.atomic import atomic_json
    def worker(path,**kw):
        atomic_json(path.parent/'summary-progress.json',{'phase':'registry','completed':6,'total':14})
        time.sleep(.5)
        return {'status':'completed','result':{'ok':True}}
    monkeypatch.setattr(pipeline,'run_worker',worker)
    events=[];p=Pipeline(tmp_path,progress=events.append)
    result=p._run(tmp_path,{'engine':'llm','task':'registry_prepare'})
    assert result['ok'] and any(e.startswith('REGISTRY_PROGRESS:') and '14' in e for e in events)
