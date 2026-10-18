import json
import sqlite3
from pathlib import Path
import pytest
from notetaker.infrastructure.database import MIGRATIONS, migrate, open_database
from notetaker.services.storage import SessionStore
from notetaker.services.directory import DirectoryService, person_name
from notetaker.services.pipeline import integral_transcript
from notetaker.services.session_export import export_session


@pytest.fixture
def directory(tmp_path):
    store = SessionStore(tmp_path/'data')
    yield store, DirectoryService(store)
    store.close()


def person(service, first='Élodie', last='Martin', position='Conseillère', city='Saint-Étienne'):
    return service.save_person(dict(first_name=first, last_name=last, position=position, municipality=city))


def rows(*people):
    return [{'person_id': pid, 'attendance': 'present'} for pid in people]


def analysis(store, sid):
    store.save_analysis(sid, [dict(id=f's{i}', start_ms=i*1000, end_ms=(i+1)*1000,
        speaker_id='a', text=f'Texte corrigé {i}.', uncertain=True) for i in range(2)],
        {'a': 'Nom manuel historique'}, store.get(sid)['revision'])


def test_directory_accent_search_filters_homonyms_and_archive_persistence(directory):
    store, service = directory
    a = person(service)
    b = person(service, city='Lyon')
    assert a != b
    assert len(service.list_people('elodie etienne conseillere')) == 1
    assert [p['id'] for p in service.list_people(municipality='lyon')] == [b]
    service.archive_person(a, True)
    assert [p['id'] for p in service.list_people()] == [b]
    assert service.list_people(status='archived')[0]['id'] == a
    service.archive_person(a, False)
    reopened = SessionStore(store.root)
    try:
        assert len(DirectoryService(reopened).list_people()) == 2
    finally:
        reopened.close()
    assert [h['action'] for h in service.history(a)] == ['reactivate', 'archive', 'create']


def test_directory_edit_detects_stale_writes_and_keeps_before_image(directory):
    _, service = directory
    pid = person(service)
    old = service.get_person(pid)
    service.save_person({**old, 'position': 'Adjointe'}, pid, old['revision'])
    with pytest.raises(ValueError, match='modifiée'):
        service.save_person({**old, 'first_name': 'Autre'}, pid, old['revision'])
    assert json.loads(service.history(pid)[0]['content_json'])['position'] == 'Conseillère'
    assert service.get_person(pid)['first_name'] == 'Élodie'


@pytest.mark.parametrize('values', [dict(first_name='', last_name='Martin'),
    dict(first_name='A', last_name='B\nC'), dict(first_name='A'*201, last_name='B')])
def test_invalid_civil_fields_are_rejected_without_partial_insert(directory, values):
    _, service = directory
    with pytest.raises(ValueError):
        service.save_person(values)
    assert service.list_people(status='all') == []


def test_session_snapshot_roles_and_presence_are_independent_across_sessions(directory):
    store, service = directory
    pid = person(service)
    one, two = store.create('Premier conseil'), store.create('Second conseil')
    service.save_participants(one, [{'person_id': pid, 'attendance': 'excused', 'session_role': 'Secrétaire désigné'}])
    original = service.get_person(pid)
    service.save_person({**original, 'last_name': 'Durand', 'position': 'Adjointe'}, pid, original['revision'])
    service.save_participants(two, rows(pid))
    first, second = service.participants(one)[0], service.participants(two)[0]
    assert first['snapshot']['last_name'] == 'Martin' and second['snapshot']['last_name'] == 'Durand'
    assert first['session_role'] == 'Secrétaire désigné' and second['session_role'] == ''
    assert first['snapshot']['position'] == 'Conseillère' and service.get_person(pid)['position'] == 'Adjointe'
    updated = service.participants(one)
    updated[0]['attendance'] = 'absent'
    service.save_participants(one, updated)
    assert service.participants(one)[0]['snapshot']['last_name'] == 'Martin'


def test_proxies_require_distinct_selected_present_holder_and_are_transactional(directory):
    store, service = directory
    a, b = person(service), person(service, first='Paul')
    sid = store.create('Conseil')
    valid = [{'person_id': a, 'attendance': 'represented', 'proxy_to_person_id': b, 'proxy_note': 'Pouvoir reçu, séance entière'},
             {'person_id': b, 'attendance': 'present', 'session_role': 'Présidence'}]
    service.save_participants(sid, valid)
    baseline = service.participants(sid)
    revision = store.get(sid)['revision']
    for bad in [
        [{**valid[0], 'proxy_to_person_id': a}, valid[1]],
        [valid[0], {**valid[1], 'attendance': 'absent'}],
        [valid[0]],
        [{**valid[0], 'attendance': 'excused'}, valid[1]],
        [valid[1], valid[1]],
    ]:
        with pytest.raises(ValueError):
            service.save_participants(sid, bad)
        assert service.participants(sid) == baseline
        assert store.get(sid)['revision'] == revision
    # Unknown attendance stays unknown; no automatic present/quorum/vote calculation.
    service.save_participants(sid, [{'person_id': a, 'attendance': 'unconfirmed'}])
    assert service.participants(sid)[0]['attendance'] == 'unconfirmed'
    assert store.get(sid)['votes'] == []


def test_archived_people_remain_in_existing_sessions_but_cannot_be_newly_selected(directory):
    store, service = directory
    pid = person(service)
    one, two = store.create('Ancienne'), store.create('Nouvelle')
    service.save_participants(one, rows(pid))
    service.archive_person(pid, True)
    service.save_participants(one, [{'person_id': pid, 'attendance': 'absent'}])
    with pytest.raises(ValueError, match='Réactivez'):
        service.save_participants(two, rows(pid))
    assert service.participants(one)[0]['snapshot']['last_name'] == 'Martin'


def test_concurrent_participant_changes_are_not_silently_overwritten(directory):
    store, service = directory
    pid = person(service)
    sid = store.create('Conseil')
    service.save_participants(sid, rows(pid), expected=[])
    with pytest.raises(ValueError, match='présences ont changé'):
        service.save_participants(sid, [], expected=[])
    assert len(service.participants(sid)) == 1


def test_manual_assignment_changes_only_selected_text_voice_and_is_restorable(directory):
    store, service = directory
    pid = person(service)
    sid = store.create('Conseil')
    analysis(store, sid)
    service.save_participants(sid, rows(pid))
    profile = service.get_person(pid)
    service.assign_person(sid, ['s0'], pid)
    state = store.get(sid)
    assert state['utterances'][0]['speaker_id'] == 'directory-'+pid
    assert state['utterances'][1]['speaker_id'] == 'a'
    assert state['utterances'][0]['text'] == 'Texte corrigé 0.'
    source = json.loads(state['utterances'][0]['source_json'])
    assert source['directory_person_id'] == pid and not source['automatic_attribution']
    assert service.get_person(pid) == profile
    before = store.analysis_history(sid)[0]
    store.restore_analysis(sid, before['id'])
    restored = store.get(sid)
    assert restored['utterances'][0]['speaker_id'] == 'a'
    assert restored['speakers']['a'] == 'Nom manuel historique'
    assert len(service.participants(sid)) == 1


def test_reanalysis_preserves_named_manual_corrections_in_history(directory):
    store, service = directory
    pid = person(service)
    sid = store.create('Conseil')
    analysis(store, sid)
    service.save_participants(sid, rows(pid))
    service.assign_person(sid, ['s0'], pid)
    analysis(store, sid)
    historic = store.analysis_history(sid)[0]
    store.restore_analysis(sid, historic['id'])
    state = store.get(sid)
    assert json.loads(state['utterances'][0]['source_json'])['directory_person_id'] == pid
    assert state['speakers']['directory-'+pid] == 'Élodie Martin'


def test_changed_presence_invalidates_review_and_export_includes_snapshots(directory, tmp_path):
    from pypdf import PdfReader
    from docx import Document
    store, service = directory
    a, b = person(service), person(service, first='Paul', last='Bernard')
    sid = store.create('Conseil', {'participants': 'Mention historique conservée'})
    analysis(store, sid)
    draft = integral_transcript(store.get(sid))
    draft['document_mode'] = 'municipal'
    store.save_draft(sid, draft)
    store.approve(sid, 'Test secrétaire', role='secretary')
    service.save_participants(sid, [{'person_id': a, 'attendance': 'represented', 'proxy_to_person_id': b},
                                   {'person_id': b, 'attendance': 'present', 'session_role': 'Présidence'}])
    with pytest.raises(ValueError, match='HUMAN_REVIEW'):
        export_session(store, sid, tmp_path/'not-approved.pdf')
    store.save_draft(sid, draft)
    store.approve(sid, 'Test secrétaire', role='secretary')
    pdf = export_session(store, sid, tmp_path/'presence.pdf')
    docx = export_session(store, sid, tmp_path/'presence.docx')
    text = '\n'.join(p.extract_text() for p in PdfReader(pdf).pages)
    word = '\n'.join(p.text for p in Document(docx).paragraphs)
    for content in [text, word]:
        assert 'Élodie Martin' in content and 'Paul Bernard' in content
        assert 'Mention historique conservée' in content and 'Présidence' in content
        assert 'procuration à Paul Bernard' in ' '.join(content.split())


def test_v3_migration_preserves_reviews_corrections_and_creates_consistent_backup(tmp_path):
    from notetaker.domain.minutes import content_digest
    path = tmp_path/'notetaker.sqlite3'
    db = sqlite3.connect(path)
    migrate(db, {k:v for k,v in MIGRATIONS.items() if k <= 3})
    with db:
        db.execute("INSERT INTO session(id,title,metadata_json) VALUES('s','Conseil historique','{}')")
        db.execute("INSERT INTO manual_record(session_id) VALUES('s')")
        db.execute("INSERT INTO speaker VALUES('a','s','Nom corrigé')")
        db.execute("INSERT INTO utterance VALUES('u','s','a',0,1000,'Paroles corrigées',0,'{}')")
        context = content_digest({'title':'Conseil historique','metadata':{},'takes':[],
            'speakers':{'a':'Nom corrigé'},'utterances':[{'id':'u','session_id':'s','speaker_id':'a','start_ms':0,'end_ms':1000,'text':'Paroles corrigées','uncertain':0,'source_json':'{}'}], 'votes':[], 'decisions':[]})
        content={'points':[{'title':'Discussion','summary':'Texte relu','sources':['u'],'vote_id':None}],'to_verify':[]}
        review={'reviewer':'Secrétaire historique','content_sha256':content_digest(content),'reviewed_at':'2026-10-01','context_sha256':context}
        db.execute('INSERT INTO draft_minutes(id,session_id,revision,content_json,review_json,context_sha256) VALUES(?,?,?,?,?,?)',
                   ('d','s',1,json.dumps(content),json.dumps(review),context))
    db.close()
    store = SessionStore(tmp_path)
    try:
        state, _ = store.reviewed_content('s')
        assert state['participants'] == [] and store.context_hash('s') == context
        assert state['utterances'][0]['text'] == 'Paroles corrigées'
        backups = list((tmp_path/'migration-backups').glob('*.sqlite3'))
        assert len(backups) == 1
        with sqlite3.connect(backups[0]) as saved:
            assert saved.execute('PRAGMA user_version').fetchone()[0] == 3
            assert saved.execute('SELECT label FROM speaker').fetchone()[0] == 'Nom corrigé'
    finally:
        store.close()
    again = open_database(path)
    again.close()
    assert len(list((tmp_path/'migration-backups').glob('*.sqlite3'))) == 1


def test_no_biometric_storage_or_model_calls_in_directory(directory, monkeypatch):
    store, service = directory
    def forbidden(*a, **kw):
        pytest.fail('Directory operations must not invoke any AI worker')
    monkeypatch.setattr('notetaker.services.pipeline.run_worker', forbidden)
    pid = person(service)
    sid = store.create('Conseil')
    service.save_participants(sid, rows(pid))
    analysis(store, sid)
    service.assign_person(sid, ['s0'], pid)
    tables = {r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not any('embedding' in t or 'voice_profile' in t for t in tables)
    assert not list(store.root.rglob('*.onnx')) and not list(store.root.rglob('*.wav'))
