import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import copy
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QInputDialog,QMessageBox
from PySide6.QtTest import QTest
from notetaker.ui.window import MainWindow
from notetaker.ui.evidence import ClaimEditor
from notetaker.services.evidence import draft_issues


@pytest.fixture
def window(tmp_path):
    app=QApplication.instance() or QApplication([])
    win=MainWindow(tmp_path/'data')
    sid=win.store.create('Conseil de test')
    text='Je propose une rénovation de la bibliothèque pour maintenir le service public.'
    win.store.save_analysis(sid,[{'id':'s0','start_ms':0,'end_ms':8000,'text':text,'speaker_id':'a','uncertain':False}],{'a':'Intervenant 1'},0)
    claim={'id':'c0','speaker':'a','kind':'proposal','text':'Une rénovation est proposée afin de préserver le service public.','evidence':[{'id':'s0','quote':text}]}
    win.store.save_draft(sid,{'points':[{'title':'Bibliothèque','summary':'Proposition — Intervenant 1 : '+claim['text'],'sources':['s0'],'vote_id':None,'claims':[claim]}],'to_verify':[]})
    win.sid=sid;win.load_session();win.show();app.processEvents()
    yield win
    win.close();app.processEvents()


def test_prose_edit_never_removes_claim_checks(window):
    window.points.setCurrentRow(0)
    window.point_text.setPlainText('Texte corrigé manuellement, sources conservées.')
    window.save_draft()
    assert window.store.get(window.sid)['draft']['content']['points'][0]['claims'][0]['id']=='c0'


def test_validation_failure_opens_precise_diagnostic_before_review_name(window,monkeypatch):
    state=window.store.get(window.sid)
    window.store.edit_utterance(window.sid,'s0',state['utterances'][0]['text'],None,confirm=True)
    window.load_session()
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**k:pytest.fail('Do not request reviewer name before evidence is fixed'))
    window.approve()
    assert window.evidence_dialog.isVisible()
    assert window.evidence_dialog.issues[0]['claim_id']=='c0'
    assert window.evidence_dialog.issues[0]['reason']=='mixed_or_wrong_speaker'
    assert window.store.get(window.sid)['draft']['review'] is None
    window.evidence_dialog.close()


def test_claim_editor_can_rebind_voice_without_dropping_evidence(window):
    state=window.store.get(window.sid)
    window.store.rename_speaker(window.sid,'a','Mme Exemple')
    window.store.db.execute("INSERT INTO speaker VALUES('b',?,'M. Autre')",(window.sid,));window.store.db.commit()
    window.store.edit_utterance(window.sid,'s0',state['utterances'][0]['text'],'b',confirm=True)
    state=window.store.get(window.sid)
    editor=ClaimEditor(state['draft']['content']['points'][0],0,state,window)
    editor.use_source_voice();editor.check()
    assert editor.apply.isEnabled()
    editor.commit()
    assert editor.result_point['claims'][0]['speaker']=='b'
    assert editor.result_point['claims'][0]['evidence']==state['draft']['content']['points'][0]['claims'][0]['evidence']
    assert 'M. Autre' in editor.result_point['summary']


def test_human_review_succeeds_after_explicit_reference_refresh(window,monkeypatch):
    window.store.rename_speaker(window.sid,'a','Mme Exemple')
    window.load_session()
    monkeypatch.setattr(window,'show_private_text',lambda *a:None)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.Yes)
    window.refresh_claim_attributions()
    assert not draft_issues(window.store.get(window.sid)['draft']['content'],window.store.get(window.sid))
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**k:('Relecteur fictif',True))
    window.approve()
    assert window.store.get(window.sid)['draft']['review']['reviewer']=='Relecteur fictif'
