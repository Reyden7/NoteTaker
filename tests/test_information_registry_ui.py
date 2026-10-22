import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import copy
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QPushButton,QDialog
from notetaker.ui.information_registry import RegistryPage
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService


@pytest.fixture
def page(tmp_path):
    app=QApplication.instance() or QApplication([])
    store=SessionStore(tmp_path/'data');sid=store.create('Séance de test interface')
    store.save_analysis(sid,[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':4000,'text':'Je propose une consultation des habitants.','uncertain':False}],{'a':'Élodie Martin'},0)
    service=RegistryService(store);record=service.initialize(sid)
    info=copy.deepcopy(record['content']['entries'][0]);info.update(id='info',category='information',subject='Consultation',type='proposal',discourse='own',
        content='La personne propose de consulter les habitants.',verification='ambiguous',reasons=['contextual_entailment_rejected'])
    record['content']['entries'].append(info);service.save(sid,record['content'],expected_id=record['id'],actor='Fixture',reason='Cas fictif')
    played=[];errors=[];prepared=[];written=[]
    page=RegistryPage(store,lambda:prepared.append(True),lambda:written.append(True),played.append,errors.append)
    page.load(sid);page.show();app.processEvents()
    yield page,store,sid,played,errors,prepared,written,app
    page.close();store.close();app.processEvents()


def click(page,text):next(b for b in page.findChildren(QPushButton) if b.text()==text).click()


def test_prepare_and_write_are_separate_actions_and_ambiguous_information_is_visible(page):
    p,store,sid,played,errors,prepared,written,app=page
    assert p.rows.rowCount()==1 and p.entry['id']=='info'
    p.filter.setCurrentIndex(p.filter.findData('review'));app.processEvents()
    assert 'info' in [e['id'] for e in p.visible]
    click(p,'Préparer / reprendre le registre');assert prepared==[True] and written==[]
    click(p,'Rédiger depuis ce registre');assert written==[]
    assert not p.write_button.isEnabled() and 'Écouter et vérifier' in p.guide.text()
    assert store.get(sid)['draft'] is None


def test_correction_approval_and_exclusion_use_real_widgets_and_keep_information_id(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.actor.setText('Opératrice test');p.justification.setText('Audio vérifié')
    p.subject.setText('Consultation des habitants');p.content.setPlainText('Une consultation des habitants est proposée par la personne.')
    click(p,'Enregistrer la correction');app.processEvents()
    assert not errors and p.service.latest(sid)['content']['entries'][-1]['id']=='info'
    click(p,'Approuver cette information');app.processEvents()
    assert p.service.latest(sid)['content']['entries'][-1]['human_status']=='approved'
    click(p,'Exclure avec motif');app.processEvents()
    p.filter.setCurrentIndex(p.filter.findData('excluded'));app.processEvents()
    assert p.rows.rowCount()==1 and p.entry['id']=='info'
    assert store.get(sid)['draft'] is None


def test_listen_uses_source_id_and_context_and_search_are_not_generated_text(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.listen();assert played==['s0'] and 'Je propose une consultation' in p.context.toPlainText()
    p.search.setText('Élodie');assert p.rows.rowCount()==1
    p.search.setText('introuvable');assert p.rows.rowCount()==0
    p.search.clear();p.filter.setCurrentIndex(p.filter.findData('sources'));app.processEvents()
    assert p.entry['category']=='source' and p.content.toPlainText()==store.get(sid)['utterances'][0]['text']


def test_missing_exact_evidence_never_displays_an_invented_zero_timestamp(page):
    p,store,sid,played,errors,prepared,written,app=page
    record=p.service.latest(sid)
    info=next(e for e in record['content']['entries'] if e['id']=='info')
    info.update(evidence=[],verification='rejected',reasons=['no_unique_exact_quote_for_speaker'])
    p.service.save(sid,record['content'],expected_id=record['id'],actor='Fixture',reason='Citation absente')
    p.load(sid);app.processEvents()
    assert p.rows.item(0,0).text()=='À rattacher'
    assert p.sources.rowCount()==0


def test_unsaved_text_cannot_be_silently_approved_and_missing_actor_is_actionable(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.content.setPlainText('Correction non enregistrée');click(p,'Approuver cette information')
    assert not p.approve_button.isEnabled() and 'Enregistrez' in p.action_hint.text()
    p.discard_changes();click(p,'Approuver cette information');assert 'ACTOR_REASON' in str(errors[-1])
    assert p.service.latest(sid)['content']['entries'][-1]['human_status']=='pending'


def test_source_picker_result_is_attached_with_exact_quote_and_real_time(page,monkeypatch):
    import notetaker.ui.information_registry as ui
    p,store,sid,played,errors,prepared,written,app=page
    class Picker:
        chosen={'id':'s0','quote':'une consultation des habitants'}
        def __init__(self,*args):pass
        def exec(self):return QDialog.Accepted
    monkeypatch.setattr(ui,'SourcePicker',Picker)
    p.add_source()
    assert p.sources.rowCount()==2
    assert p.sources.item(1,1).text()=='une consultation des habitants'
    assert p.sources.item(1,0).data(Qt.UserRole)=='s0'


def test_new_registry_does_not_display_historical_document_review_as_current(tmp_path):
    from notetaker.ui.window import MainWindow
    from notetaker.services.pipeline import integral_transcript
    app=QApplication.instance() or QApplication([]);window=MainWindow(tmp_path/'ui-stale')
    sid=window.store.create('Fixture de relecture')
    window.store.save_analysis(sid,[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':3000,'text':'Une intervention fictive.','uncertain':False}],{'a':'Personne test'},0)
    window.store.save_draft(sid,integral_transcript(window.store.get(sid)));window.store.approve(sid,'Fixture uniquement')
    RegistryService(window.store).initialize(sid);window.sid=sid;window.load_session()
    try:
        assert 'ancienne relecture conservée' in window.review_status.text()
        assert window.store.get(sid)['draft']['review']['reviewer']=='Fixture uniquement'
    finally:window.close();app.processEvents()


def test_stale_registry_audio_and_context_use_original_snapshot_not_edited_transcription(page):
    p,store,sid,played,errors,prepared,written,app=page
    captured=[];p.play_snapshot=captured.append
    old_text=store.get(sid)['utterances'][0]['text']
    store.edit_utterance(sid,'s0','Nouvelle version différente','a')
    p.load(sid);p.listen()
    assert captured[0]['text']==old_text
    assert old_text in p.context.toPlainText() and 'Nouvelle version différente' not in p.context.toPlainText()
    assert p.current['stale'] and played==[]


def test_rejected_unmatched_quote_context_also_uses_original_snapshot_when_stale(page):
    p,store,sid,played,errors,prepared,written,app=page
    record=p.service.latest(sid)
    info=next(e for e in record['content']['entries'] if e['id']=='info')
    info.update(evidence=[],verification='rejected',origin={'unit_source_ids':['s0'],
        'raw_candidate':{'quote':'Une citation introuvable'}})
    p.service.save(sid,record['content'],expected_id=record['id'],actor='Fixture',reason='Origine sans citation exacte')
    old_text=store.get(sid)['utterances'][0]['text']
    store.edit_utterance(sid,'s0','Une transcription corrigée différente','a')
    captured=[];p.play_snapshot=captured.append
    p.load(sid);app.processEvents();p.listen()
    assert p.current['stale'] and old_text in p.context.toPlainText()
    assert 'Une transcription corrigée différente' not in p.context.toPlainText()
    assert captured[0]['text']==old_text and not errors


def test_initialize_without_ai_immediately_opens_full_sources_and_calls_no_model(page):
    p,store,sid,played,errors,prepared,written,app=page
    other=store.create('Initialisation sans moteur')
    store.save_analysis(other,[{'id':'s9','speaker_id':'a','start_ms':0,'end_ms':2000,'text':'Une intervention source.','uncertain':False}],{'a':'Personne test'},0)
    p.load(other);click(p,'Initialiser sans IA');app.processEvents()
    assert p.current and p.filter.currentData()=='sources' and p.rows.rowCount()==1
    assert prepared==written==[] and p.entry['content']=='Une intervention source.'
    assert store.get(other)['draft'] is None


def test_requested_qwen_check_uses_saved_information_and_does_not_drop_pending_edit(page):
    p,store,sid,played,errors,prepared,written,app=page;requested=[];p.verify_callback=requested.append
    click(p,'Demander un contrôle Qwen de cette fiche');assert requested==['info']
    p.content.setPlainText('Correction non enregistrée')
    click(p,'Demander un contrôle Qwen de cette fiche')
    assert requested==['info'] and not p.verify_button.isEnabled() and 'Enregistrez' in p.action_hint.text()


def test_filter_reload_and_selection_do_not_silently_drop_unsaved_correction(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.filter.setCurrentIndex(p.filter.findData('review'));p.focus_entry('info')
    p.content.setPlainText('Correction en cours à conserver')
    p.rows.selectRow(0);p.search.setText('Autre filtre');p.load(sid);app.processEvents()
    assert p.content.toPlainText()=='Correction en cours à conserver' and p.entry['id']=='info'
    p.discard_changes()
    assert p.content.toPlainText()=='La personne propose de consulter les habitants.'


def test_saving_from_source_focuses_new_information_instead_of_an_unrelated_row(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.filter.setCurrentIndex(p.filter.findData('sources'));p.content.setPlainText('Une consultation préalable est proposée.')
    p.actor.setText('Opératrice test');p.justification.setText('Nouvelle fiche issue de la source')
    click(p,'Enregistrer la correction');app.processEvents()
    assert not errors and p.entry['category']=='information' and p.entry['id']!='info'
    assert p.content.toPlainText()=='Une consultation préalable est proposée.'


def test_qt_plain_text_whitespace_normalization_is_not_a_false_unsaved_change(page):
    p,store,sid,played,errors,prepared,written,app=page
    record=p.service.latest(sid);text='Consultation\u00a0des habitants.\r\nTexte de suite.'
    p.service.change(sid,record['id'],'info','edit',actor='Fixture',reason='Espaces et retours Windows',updates={'content':text})
    p.load(sid);app.processEvents()
    assert not p.editor_changed()
    assert p.service.latest(sid)['content']['entries'][-1]['content']==text


def test_prepare_returns_from_sources_to_actionable_information(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.filter.setCurrentIndex(p.filter.findData('sources'))
    p.preparation_complete({'created_information_entries':1,'proposed_information_entries':1})
    assert p.filter.currentData()=='proposed' and p.entry['id']=='info'
    assert 'créé 1' in p.banner.text() and p.approve_button.isEnabled()


def test_source_cannot_be_approved_or_checked_as_information_and_links_are_accessible(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.filter.setCurrentIndex(p.filter.findData('sources'))
    assert not p.approve_button.isEnabled() and not p.verify_button.isEnabled()
    assert 'source conservée' in p.action_hint.text()
    assert p.linked_button.isVisible() and p.create_button.isVisible()
    p.show_linked();assert p.entry['id']=='info' and p.filter.currentData()=='all'


def test_review_view_keeps_raw_passages_separate(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.filter.setCurrentIndex(p.filter.findData('review'))
    assert all(e['category']=='information' for e in p.visible)
    p.filter.setCurrentIndex(p.filter.findData('sources'))
    assert all(e['category']=='source' for e in p.visible)


def test_source_creation_is_explicit_and_keeps_the_original_verbatim(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.filter.setCurrentIndex(p.filter.findData('sources'));source=copy.deepcopy(p.entry)
    p.start_information()
    assert not p.content.toPlainText() and p.sources.item(0,1).text()==source['content']
    p.subject.setText('Consultation');p.content.setPlainText('Une consultation des habitants est demandée.')
    p.kind.setCurrentIndex(p.kind.findData('proposal'));p.actor.setText('Fixture');p.justification.setText('Cas construit')
    p.save_button.click();assert not errors and p.entry['category']=='information'
    doc=p.service.latest(sid)['content']
    assert next(e for e in doc['entries'] if e['id']==source['id'])==source


def test_invalid_citation_displays_specific_reason_and_disables_approval(page):
    p,store,sid,played,errors,prepared,written,app=page
    record=p.service.latest(sid)
    p.service.change(sid,record['id'],'info','edit',actor='Fixture',reason='Source insuffisante',
        updates={'evidence':[{'id':'s0','quote':'Une citation inventée'}]})
    p.load(sid);p.focus_entry('info')
    assert not p.approve_button.isEnabled() and 'mot pour mot' in p.action_hint.text()
    p.filter.setCurrentIndex(p.filter.findData('corrections'));assert p.entry['id']=='info'


def test_human_approval_moves_guide_to_writing_without_validating_document(page):
    p,store,sid,played,errors,prepared,written,app=page
    p.actor.setText('Fixture');p.justification.setText('Contrôle de test, pas une réunion réelle')
    p.approve_button.click()
    assert not errors and p.write_button.isEnabled() and '5/6' in p.guide.text()
    assert store.get(sid)['draft'] is None
    p.write_button.click();assert written==[True]
