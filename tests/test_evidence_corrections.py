"""Reproductions on fictional data; model outputs below are explicit fixtures."""
import copy
import json
from pathlib import Path
import pytest
from notetaker.services.storage import SessionStore
from notetaker.services.directory import DirectoryService
from notetaker.services.evidence import DraftEvidenceError,draft_issues,propose_attribution_refresh
from notetaker.services.transcript import compact_rows,preserve_corrections
from notetaker.services.session_export import export_session
from notetaker.engines.hierarchical_summary import grounded_claim


@pytest.fixture
def session(tmp_path):
    store=SessionStore(tmp_path/'data');sid=store.create('Conseil fictif',{'municipality':'Commune test'})
    text='Je propose une rénovation de la bibliothèque pour maintenir le service public dans de bonnes conditions.'
    store.save_analysis(sid,[{'id':'s0','start_ms':0,'end_ms':10000,'text':text,'speaker_id':'a','uncertain':True},
        {'id':'s1','start_ms':11000,'end_ms':16000,'text':'Je demande également un devis détaillé avant les travaux.','speaker_id':'a','uncertain':True}],{'a':'Intervenant 1'},0)
    claim={'id':'c0','kind':'proposal','speaker':'a','text':'Une rénovation est proposée pour préserver le service de la bibliothèque.',
        'evidence':[{'id':'s0','quote':text}]}
    draft={'document_mode':'summary','points':[{'title':'Bibliothèque','summary':'Proposition — Intervenant 1 (attribution à vérifier) : '+claim['text'],
        'sources':['s0'],'vote_id':None,'claims':[claim]}],'to_verify':[]}
    store.save_draft(sid,draft)
    yield store,sid,draft
    store.close()


def assign(store,sid,first='Alice'):
    directory=DirectoryService(store)
    pid=directory.save_person({'first_name':first,'last_name':'Exemple','position':'Conseillère','municipality':'Commune test'})
    current=directory.participants(sid)
    directory.save_participants(sid,[*current,{'person_id':pid,'attendance':'present'}])
    directory.assign_person(sid,['s0'],pid)
    return pid


def test_reproduce_changed_directory_identity_reports_exact_claim_source_and_reason(session,tmp_path):
    store,sid,draft=session
    assign(store,sid)
    with pytest.raises(DraftEvidenceError) as caught:store.save_draft(sid,draft)
    issue=caught.value.issues[0]
    assert issue['claim_id']=='c0' and issue['source_id']=='s0' and issue['point_index']==0
    assert issue['reason']=='mixed_or_wrong_speaker'
    assert issue['actual_speaker'].startswith('directory-') and issue['expected_speaker']=='a'
    assert 'intervenant' in issue['message'].lower()


def test_explicit_refresh_keeps_claims_quotes_sources_and_requires_fresh_review(session,tmp_path):
    store,sid,draft=session
    assign(store,sid)
    proposal,changed=propose_attribution_refresh(draft,store.get(sid))
    assert changed==[0] and not draft_issues(proposal,store.get(sid))
    before=draft['points'][0]['claims'][0];after=proposal['points'][0]['claims'][0]
    assert before['text']==after['text'] and before['evidence']==after['evidence']
    assert 'Alice Exemple' in proposal['points'][0]['summary'] and 'Intervenant 1' not in proposal['points'][0]['summary']
    store.save_draft(sid,proposal)
    with pytest.raises(ValueError,match='HUMAN_REVIEW'):export_session(store,sid,tmp_path/'blocked.pdf')
    store.approve(sid,'Test de relecture fictif')
    assert export_session(store,sid,tmp_path/'allowed.pdf').is_file()
    assert export_session(store,sid,tmp_path/'allowed.docx').is_file()
    assert len(store.draft_history(sid))==2


def test_inconsistent_working_revision_survives_reopen_but_never_exports(session,tmp_path):
    store,sid,draft=session
    assign(store,sid)
    store.save_draft(sid,draft,allow_invalid=True)
    reopened=SessionStore(store.root)
    try:
        assert reopened.get(sid)['draft']['content']['points'][0]['claims']==draft['points'][0]['claims']
        with pytest.raises(DraftEvidenceError):reopened.approve(sid,'Test')
        with pytest.raises(ValueError,match='HUMAN_REVIEW'):export_session(reopened,sid,tmp_path/'no.docx')
    finally:reopened.close()


def test_quote_change_and_missing_source_cannot_be_fixed_by_voice_refresh(session):
    store,sid,draft=session
    store.edit_utterance(sid,'s0','Un autre texte corrigé.','a',confirm=True)
    proposal,_=propose_attribution_refresh(draft,store.get(sid))
    assert any(i['reason']=='quote_not_in_source' for i in draft_issues(proposal,store.get(sid)))
    damaged=copy.deepcopy(draft);damaged['points'][0]['claims'][0]['evidence'][0]['id']='deleted'
    reasons={i['reason'] for i in draft_issues(damaged,store.get(sid))}
    assert 'missing_source' in reasons


def test_mixed_voices_are_not_silently_unified(session):
    store,sid,draft=session
    modified=copy.deepcopy(draft)
    modified['points'][0]['sources'].append('s1')
    modified['points'][0]['claims'][0]['evidence'].append({'id':'s1','quote':store.get(sid)['utterances'][1]['text']})
    assign(store,sid)
    proposal,_=propose_attribution_refresh(modified,store.get(sid))
    assert proposal['points'][0]['claims'][0]['speaker']=='a'
    assert any(i['reason']=='mixed_or_wrong_speaker' for i in draft_issues(proposal,store.get(sid)))


def test_split_maps_exact_quote_to_both_children_and_keeps_old_revision(session,tmp_path):
    store,sid,draft=session
    text=store.get(sid)['utterances'][0]['text'];cut=text.index('pour')
    child=store.split_utterance(sid,'s0',5000,cut)
    state=store.get(sid);updated=state['draft']['content']
    assert {e['id'] for e in updated['points'][0]['claims'][0]['evidence']}=={'s0',child}
    assert not draft_issues(updated,state)
    assert json.loads(store.draft_history(sid)[1]['content_json'])==draft
    store.approve(sid,'Test fictif après scission')
    assert export_session(store,sid,tmp_path/'split.pdf').is_file()
    store.edit_utterance(sid,child,state['utterances'][1]['text'],None,confirm=True)
    assert draft_issues(store.get(sid)['draft']['content'],store.get(sid))


def test_merge_remaps_citations_and_restores_full_snapshot(session,tmp_path):
    store,sid,draft=session
    updated=copy.deepcopy(draft);updated['points'][0]['sources'].append('s1')
    updated['points'][0]['claims'][0]['evidence'].append({'id':'s1','quote':store.get(sid)['utterances'][1]['text']})
    store.save_draft(sid,updated)
    store.merge_utterances(sid,['s0','s1'])
    state=store.get(sid)
    assert len(state['utterances'])==1 and state['utterances'][0]['end_ms']==16000
    assert not draft_issues(state['draft']['content'],state)
    assert state['draft']['content']['points'][0]['sources']==['s0']
    store.approve(sid,'Test fictif après regroupement')
    assert export_session(store,sid,tmp_path/'merged.docx').is_file()
    history=next(h for h in store.analysis_history(sid) if h['kind']=='merge_segments')
    store.restore_analysis(sid,history['id'])
    assert len(store.get(sid)['utterances'])==2


def test_reanalysis_never_replaces_confirmed_text_identity_ids_and_audio_times(session):
    store,sid,draft=session
    pid=assign(store,sid)
    store.edit_utterance(sid,'s0','Texte relu par l’agent.','directory-'+pid,confirm=True)
    before=store.get(sid)['utterances'][0]
    incoming=[{'id':'s0','start_ms':0,'end_ms':10000,'text':'Nouvelle transcription incorrecte.','speaker_id':'a','uncertain':False}]
    store.save_analysis(sid,incoming,{'a':'Intervenant 1'},store.get(sid)['revision'])
    after=store.get(sid)['utterances'][0]
    assert {k:after[k] for k in ('id','text','speaker_id','start_ms','end_ms','source_json')}=={k:before[k] for k in ('id','text','speaker_id','start_ms','end_ms','source_json')}


def test_ambiguous_partial_time_alignment_preserves_active_data_on_failure(session):
    store,sid,_=session
    assign(store,sid)
    before=store.get(sid)
    with pytest.raises(ValueError,match='MANUAL_ALIGNMENT'):
        store.save_analysis(sid,[{'id':'new','start_ms':0,'end_ms':15000,'text':'Un segment qui traverse la correction.','speaker_id':'x','uncertain':False}],{'x':'Intervenant 1'},before['revision'])
    assert store.get(sid)['utterances']==before['utterances']


def test_compaction_keeps_lexical_content_timing_and_unknown_overlap_boundaries():
    rows=[{'id':str(i),'start_ms':i*1100,'end_ms':i*1100+1000,'text':t,'speaker_id':speaker,
           'uncertain':False,'source':{'automatic_attribution':True}} for i,(t,speaker) in enumerate([('Bonjour','a'),('à tous.','a'),('—',None),('Qui parle ?',None)])]
    compact=compact_rows(rows)
    assert len(compact)==2 and compact[0]['text']=='Bonjour à tous.'
    assert compact[0]['start_ms']==0 and compact[0]['end_ms']==2100
    assert compact[1]['speaker_id'] is None
    rows[1]['source']['possible_overlap']=True
    assert len(compact_rows(rows))==3


def test_anonymous_voice_id_is_stable_by_mutual_time_overlap():
    old={'utterances':[{'id':'old','start_ms':0,'end_ms':10000,'text':'Paroles','speaker_id':'stable','source_json':'{}'}], 'speakers':{'stable':'Intervenant 7'}}
    incoming=[{'id':'new','start_ms':0,'end_ms':10000,'text':'Paroles','speaker_id':'fresh','source':{}}]
    rows,names=preserve_corrections(old,incoming,{'fresh':'Intervenant 1'})
    assert rows[0]['speaker_id']=='stable' and names['stable']=='Intervenant 7'


def test_reference_validation_does_not_mutate_claim_or_hash(session):
    store,sid,draft=session
    claim=copy.deepcopy(draft['points'][0]['claims'][0]);claim['evidence'][0]['quote']='«'+claim['evidence'][0]['quote']+'»'
    before=copy.deepcopy(claim)
    assert grounded_claim(claim,store.get(sid)['utterances'])[0]
    assert claim==before


def test_renamed_voice_keeps_uuid_but_requires_printed_name_refresh(session):
    store,sid,draft=session
    store.rename_speaker(sid,'a','Mme Exemple')
    assert any(i['reason']=='stale_attribution_text' for i in draft_issues(draft,store.get(sid)))
    proposal,_=propose_attribution_refresh(draft,store.get(sid))
    assert not draft_issues(proposal,store.get(sid))
    assert proposal['points'][0]['claims'][0]['speaker']=='a'
    assert 'Mme Exemple' in proposal['points'][0]['summary']


def test_split_and_draft_source_remap_rollback_together(session):
    import sqlite3
    store,sid,_=session
    before=store.get(sid);history=store.draft_history(sid)
    store.db.execute("CREATE TRIGGER reject_revision BEFORE UPDATE OF revision ON session BEGIN SELECT RAISE(ABORT,'forced storage failure'); END")
    store.db.commit()
    with pytest.raises(sqlite3.IntegrityError,match='forced storage failure'):
        store.split_utterance(sid,'s0',5000,before['utterances'][0]['text'].index('pour'))
    assert store.get(sid)['utterances']==before['utterances']
    assert store.draft_history(sid)==history


def test_legacy_migration_keeps_claim_sources_snapshot_and_review(session,tmp_path):
    store,sid,draft=session
    store.approve(sid,'Relecteur fictif avant migration')
    before=store.get(sid)
    with store.db:
        for table in ('information_registry','session_participant','directory_history','directory_person'):
            store.db.execute('DROP TABLE '+table)
        store.db.execute('PRAGMA user_version=3')
    store.close()
    reopened=SessionStore(store.root)
    try:
        state,review=reopened.reviewed_content(sid)
        assert state['draft']==before['draft'] and state['utterances']==before['utterances']
        assert not draft_issues(state['draft']['content'],state)
        assert export_session(reopened,sid,tmp_path/'migrated.pdf').is_file()
        assert list((store.root/'migration-backups').glob('*.sqlite3'))
    finally:reopened.close()


def test_split_anonymous_voice_does_not_force_old_id_on_ambiguous_groups():
    old={'utterances':[{'id':'old','start_ms':0,'end_ms':10000,'text':'Paroles','speaker_id':'stable','source_json':'{}'}], 'speakers':{'stable':'Intervenant 7'}}
    incoming=[{'id':'n1','start_ms':0,'end_ms':6000,'text':'Paroles','speaker_id':'x','source':{}},
              {'id':'n2','start_ms':6000,'end_ms':10000,'text':'Suite','speaker_id':'y','source':{}}]
    rows,_=preserve_corrections(old,incoming,{'x':'Intervenant 1','y':'Intervenant 2'})
    assert all(r['speaker_id']!='stable' for r in rows)


def test_mid_word_split_merge_keeps_original_text_and_citations(session):
    store,sid,_=session
    original=store.get(sid)['utterances'][0]['text']
    child=store.split_utterance(sid,'s0',5000,5)
    store.merge_utterances(sid,['s0',child])
    state=store.get(sid)
    assert state['utterances'][0]['text']==original
    assert not draft_issues(state['draft']['content'],state)
