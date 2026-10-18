import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from notetaker.ui.window import MainWindow
from notetaker.ui.directory import DirectoryDialog, PersonPicker
from notetaker.services.directory import DirectoryService


@pytest.fixture
def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path/'ui')
    window.show()
    app.processEvents()
    yield window
    window.close()
    app.processEvents()


def make_person(service, first='Élodie', last='Martin', city='Commune test'):
    return service.save_person({'first_name':first,'last_name':last,'position':'Conseillère','municipality':city})


def test_directory_can_be_used_without_session_and_never_enrolls(window):
    assert window.sid is None and window.directory_button.isEnabled()
    dialog = DirectoryDialog(window.store, window)
    dialog.show()
    dialog.fields['first_name'].setText('Élodie')
    dialog.fields['last_name'].setText('Martin')
    dialog.fields['position'].setText('Conseillère')
    dialog.fields['municipality'].setText('Commune test')
    QTest.mouseClick(dialog.save_button, Qt.LeftButton)
    pid = dialog.pid
    assert pid and dialog.table.rowCount() == 1
    assert not dialog.voice_button.isEnabled()
    QTest.mouseClick(dialog.voice_button, Qt.LeftButton)
    assert len(dialog.service.history(pid)) == 1
    dialog.fields['position'].setText('Adjointe')
    QTest.mouseClick(dialog.save_button, Qt.LeftButton)
    assert dialog.service.get_person(pid)['position'] == 'Adjointe'
    QTest.mouseClick(dialog.archive_button, Qt.LeftButton)
    assert dialog.table.rowCount() == 0
    dialog.status_filter.setCurrentIndex(1)
    assert dialog.table.rowCount() == 1
    QTest.mouseClick(dialog.archive_button, Qt.LeftButton)
    dialog.status_filter.setCurrentIndex(0)
    dialog.search.setText('elodie commune')
    assert dialog.table.rowCount() == 1
    dialog.search.setText('absent du répertoire')
    assert dialog.table.rowCount() == 0
    dialog.close()


def test_directory_unsaved_form_cancel_keeps_edits(window, monkeypatch):
    dialog = DirectoryDialog(window.store, window)
    dialog.fields['first_name'].setText('À conserver')
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.Cancel)
    dialog.new_person()
    assert dialog.fields['first_name'].text() == 'À conserver' and dialog.dirty
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.Discard)
    dialog.new_person()
    assert dialog.fields['first_name'].text() == '' and not dialog.dirty
    dialog.close()


def test_participant_widgets_save_proxy_roles_and_reopen(window, monkeypatch):
    service = DirectoryService(window.store)
    a, b = make_person(service), make_person(service, 'Paul', 'Bernard')
    sid = window.store.create('Conseil de test')
    window.sid = sid
    window.load_session()
    page = window.participants_page
    def choose(picker):
        picker.selected = {a,b}
        return QDialog.Accepted
    monkeypatch.setattr(PersonPicker, 'exec', choose)
    page.add_people()
    indices = {p['person_id']:i for i,p in enumerate(page.records)}
    ia, ib = indices[a], indices[b]
    page.table.cellWidget(ia,2).setCurrentIndex(page.table.cellWidget(ia,2).findData('represented'))
    page.table.cellWidget(ib,2).setCurrentIndex(page.table.cellWidget(ib,2).findData('present'))
    page.table.cellWidget(ia,4).setCurrentIndex(page.table.cellWidget(ia,4).findData(b))
    page.table.item(ib,3).setText('Présidence de séance')
    page.table.item(ia,5).setText('Pouvoir remis avant ouverture')
    QTest.mouseClick(page.save_button, Qt.LeftButton)
    assert not page.dirty
    window.load_session()
    stored = service.participants(sid)
    assert next(p for p in stored if p['person_id']==a)['proxy_to_person_id'] == b
    assert service.get_person(b)['position'] == 'Conseillère'
    assert next(p for p in stored if p['person_id']==b)['session_role'] == 'Présidence de séance'
    assert window.person_combo.count() == 3


def test_manual_directory_assignment_through_transcription_widgets(window):
    service = DirectoryService(window.store)
    pid = make_person(service)
    sid = window.store.create('Conseil')
    window.store.save_analysis(sid,[{'id':'s0','start_ms':0,'end_ms':1000,'text':'Correction conservée.','speaker_id':'a','uncertain':True}], {'a':'Voix 1'},0)
    service.save_participants(sid,[{'person_id':pid,'attendance':'present'}])
    window.sid = sid
    window.load_session()
    window.tabs.setCurrentIndex(2)
    window.transcript_table.selectRow(0)
    window.person_combo.setCurrentIndex(window.person_combo.findData(pid))
    QTest.mouseClick(window.assign_person_button, Qt.LeftButton)
    state = window.store.get(sid)
    assert state['speakers']['directory-'+pid] == 'Élodie Martin'
    assert state['utterances'][0]['text'] == 'Correction conservée.'
    assert window.transcript_table.item(0,1).text() == 'Élodie Martin'
    assert window.speaker_combo.currentData() == 'directory-'+pid
    assert window.utterance_edit.toPlainText() == 'Correction conservée.'
    assert 'manuellement' in window.uncertainty.text()
    assert len(service.history(pid)) == 1
