"""Municipal review roles must also apply to the experimental orchestrator."""
import pytest
from test_direct_summary import make_service_fixture


def select_mode(store, sid, mode):
    state = store.get(sid)
    store.save_details(sid, state['title'], {**state['metadata'], 'document_mode': mode})


def require_secretary(store, sid):
    assert store.get(sid)['draft']['content']['document_mode'] == 'municipal'
    with pytest.raises(ValueError, match='MUNICIPAL_SECRETARY_REVIEW_REQUIRED'):
        store.approve(sid, 'Fixture automatisée sans rôle')
    store.approve(sid, 'Secrétaire de fixture automatisée', role='secretary')


def test_direct_municipal_draft_keeps_the_existing_secretary_review_gate(tmp_path, monkeypatch):
    store, sid, service = make_service_fixture(tmp_path, monkeypatch)
    select_mode(store, sid, 'municipal')
    service.generate(sid)
    require_secretary(store, sid)
    store.close()


def test_reuse_respects_current_municipal_mode_and_clears_review(tmp_path, monkeypatch):
    store, sid, service = make_service_fixture(tmp_path, monkeypatch)
    generated = service.generate(sid)
    select_mode(store, sid, 'municipal')
    service.reuse(sid, generated['run_id'])
    assert store.get(sid)['draft']['review'] is None
    require_secretary(store, sid)
    store.close()


def test_direct_synthesis_is_never_labelled_integral_transcript(tmp_path, monkeypatch):
    store, sid, service = make_service_fixture(tmp_path, monkeypatch)
    select_mode(store, sid, 'transcript')
    service.generate(sid)
    assert store.get(sid)['draft']['content']['document_mode'] == 'summary'
    store.close()
