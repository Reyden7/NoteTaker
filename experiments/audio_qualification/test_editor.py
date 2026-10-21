import copy
import os
import sqlite3
import wave
import pytest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QTableWidgetItem
from .core import (ReferenceStore,QualificationError,approve,update_zone,review_valid,sha,
                   initial_project,verify_inputs,load_dataset,WORK)
from .app import QualificationWindow
from .test_scoring import project,dataset,reference


@pytest.fixture(scope='session')
def app():return QApplication.instance() or QApplication([])


@pytest.fixture
def window(tmp_path,app):
    w=QualificationWindow(tmp_path/'human.sqlite',project=project(),dataset=dataset(),media=False)
    w.show();app.processEvents();yield w;w.close();app.processEvents()


def test_transactional_history_reopen_conflict_and_foreign_database_refusal(tmp_path):
    path=tmp_path/'human.sqlite';s=ReferenceStore(path);p=reference();rid=s.save(p,None,'Alice','initial')
    p['zones'][0]=update_zone(p['zones'][0],verbatim='Correction humaine')
    rid2=s.save(p,rid,'Alice','correction');assert ReferenceStore(path).load()==(rid2,p)
    assert s.snapshot(rid)['zones'][0]['verbatim']=='Bonjour mairie'
    with pytest.raises(QualificationError):s.save(p,rid,'autre fenêtre','conflit')
    foreign=tmp_path/'existing.sqlite'
    with sqlite3.connect(foreign) as c:c.execute('CREATE TABLE sessions(id TEXT)')
    before=sha(foreign)
    with pytest.raises(QualificationError):ReferenceStore(foreign)
    assert sha(foreign)==before


def test_domain_reviews_invalidate_on_actual_changes_only():
    p=reference();z=p['zones'][0];h=p['audio']['sha256']
    corrected=update_zone(z,verbatim='Bonjour madame')
    assert not review_valid(corrected,'text',h) and review_valid(corrected,'diarization',h)
    moved=update_zone(z,turns=[{'start':.1,'end':.8,'speaker':'vB'}])
    assert review_valid(moved,'text',h) and not review_valid(moved,'diarization',h)
    changed=update_zone(z,start=.01)
    assert not any(review_valid(changed,d,h) for d in ('text','diarization','word_times'))


def test_cannot_approve_blank_or_unheard_or_guessed_words():
    p=project()
    with pytest.raises(QualificationError):approve(p,'z1','text','Test',True)
    p['zones'][0]['verbatim']='Bonjour'
    with pytest.raises(QualificationError):approve(p,'z1','text','',True)
    with pytest.raises(QualificationError):approve(p,'z1','text','Test',False)
    p['zones'][0]['unintelligible']=True
    with pytest.raises(QualificationError):approve(p,'z1','text','Test',True)


def test_editor_starts_blind_and_never_imports_hypothesis_as_truth(window,app):
    assert not window.show_hypotheses.isChecked() and window.verbatim.toPlainText()==''
    assert all(view.table.rowCount()==0 for view in window.views.values())
    QTest.mouseClick(window.show_hypotheses,Qt.LeftButton);app.processEvents()
    assert window.zone()['hypotheses_seen'] is True
    assert window.verbatim.toPlainText()=='' and all(view.table.rowCount()>0 for view in window.views.values())


def test_word_correction_review_invalidation_and_switching_zone_keeps_selection(window,app):
    window.reviewer.setText('Relectrice test');window.verbatim.setPlainText('Bonjour mairie')
    window.text_heard.setChecked(True);window.review('text')
    assert review_valid(window.zone(),'text',window.project['audio']['sha256'])
    previous=window.revision;window.verbatim.setPlainText('Bonjour conseil')
    window.zone_list.setCurrentRow(1);app.processEvents()
    assert window.zone_id=='z2' and window.zone_list.currentItem().data(Qt.UserRole)=='z2'
    assert window.store.snapshot(previous)['zones'][0]['verbatim']=='Bonjour mairie'
    first=window.project['zones'][0];assert first['verbatim']=='Bonjour conseil' and first['reviews']['text'] is None


def test_correct_voice_boundaries_overlap_and_make_words_without_invented_times(window,app):
    window.verbatim.setPlainText('Bonjour mairie');window.save()
    window.add_timed_row(False);window.turn_table.setItem(0,0,QTableWidgetItem('.1'));window.turn_table.setItem(0,1,QTableWidgetItem('.9'))
    window.turn_table.cellWidget(0,2).setCurrentIndex(1);window.save()
    window.reviewer.setText('Test');window.text_heard.setChecked(True);window.review('text')
    window.turn_heard.setChecked(True);window.review('diarization')
    window.make_words();assert [w['text'] for w in window.zone()['words']]==['bonjour','mairie']
    assert all(w['start'] is None and w['end'] is None for w in window.zone()['words'])
    assert window.zone()['reviews']['word_times'] is None
    window.turn_table.setItem(0,1,QTableWidgetItem('1.2'));window.save()
    assert window.zone()['reviews']['diarization'] is None


def test_invalid_numeric_draft_survives_close_and_reopen(window,app):
    path=window.store.path;window.add_timed_row(False)
    window.turn_table.setItem(0,0,QTableWidgetItem('saisie incomplète'))
    window.close();app.processEvents()
    other=QualificationWindow(path,dataset=dataset(),media=False)
    try:
        assert other.turn_table.item(0,0).text()=='saisie incomplète'
        assert 'récupérée' in other.status.text()
        other.turn_table.setItem(0,0,QTableWidgetItem('0.1'));other.turn_table.setItem(0,1,QTableWidgetItem('0.9'));other.save()
    finally:other.close()


def test_synchronized_highlights_and_seek_keep_one_absolute_clock(window,app):
    window.show_hypotheses.setChecked(True);window.seek(.3);window.on_position(300)
    assert window.clock.text()=='00:00.300'
    assert all(view.active=={0} for view in window.views.values())
    assert window.slider.minimum()==0 and window.slider.maximum()==2000


def test_real_benchmark_sources_load_readonly_and_reference_is_empty():
    p=initial_project();verify_inputs(p);d=load_dataset(p)
    assert len(p['zones'])==12 and all(not z['verbatim'] and not z['turns'] for z in p['zones'])
    assert p['audio']['sha256']=='95da1f0787fd22ad313acfd367fda3012b47587660cb9b1a2d6e6001bf0e708a'
    assert d['chains']['large']['asr']==d['chains']['whisperx']['asr']
    assert d['chains']['large']['diarization']==d['chains']['whisperx']['diarization']
    assert all(z['reviews']['text'] is None for z in p['zones'])


def test_changed_source_blocks_scoring_and_keeps_human_reference(tmp_path):
    p=reference();audio=tmp_path/'audio.wav';audio.write_bytes(b'test fixture only')
    source=tmp_path/'hypothesis.json';source.write_text('{}')
    p['audio']['path']=str(audio);p['audio']['sha256']=sha(audio)
    # Reviews belong to the earlier fixture hash: update through actual approval.
    for z in p['zones']:
        for domain in z['reviews']:z['reviews'][domain]=None
    p=approve(p,'z1','text','Test',True)
    p['sources']={'test':{'path':str(source),'sha256':sha(source)}}
    store=ReferenceStore(tmp_path/'human.sqlite');rid=store.save(p,None,'Test','annotation')
    verify_inputs(p);source.write_text('{"modified":true}')
    with pytest.raises(QualificationError):verify_inputs(p)
    assert store.load()==(rid,p) and p['zones'][0]['verbatim']=='Bonjour mairie'


def test_edit_after_comparison_labels_report_as_old_reference(window):
    from .core import digest
    window.report_markdown='# Mesures de la référence figée'
    window.report_reference_hash=digest(window.project);window.update_report_view()
    assert 'ancienne révision' not in window.results.toPlainText()
    window.verbatim.setPlainText('Correction après comparaison')
    assert 'ancienne révision' in window.results.toPlainText()
    window.save();assert 'ancienne révision' in window.results.toPlainText()


def test_restore_cannot_erase_exposure_to_hypotheses(window):
    before=copy.deepcopy(window.project)
    window.show_hypotheses.setChecked(True);assert window.zone()['hypotheses_seen']
    window.commit(before,'Restauration avant comparaison')
    assert window.zone()['hypotheses_seen']
    window.verbatim.setPlainText('Bonjour mairie');window.reviewer.setText('Test');window.text_heard.setChecked(True);window.review('text')
    assert window.zone()['reviews']['text']['hypotheses_seen_before_review'] is True


def test_restore_that_removes_current_new_zone_returns_to_existing_zone(window):
    from .core import blank_zone
    previous=copy.deepcopy(window.project);added=copy.deepcopy(previous)
    added['zones'].append(blank_zone('new',7,8));window.commit(added,'Nouvelle zone');window.select_zone_id('new')
    assert window.zone_id=='new'
    window.commit(previous,'Restauration');assert window.zone_id=='z1' and window.zone()['id']=='z1'
