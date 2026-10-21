"""UI fixtures use test stores, no real annotation approval or model launch."""
import copy
import pytest
from .test_editor import app,window
from .core import digest,QualificationError
from .test_scoring import reference,dataset
from .wer_plan import prepare,PlanStore,approved
from .test_wer_plan import overlapped
from .wer_review import WERReviewDialog
from .correction_ui import GapDialog,CorrectionDialog
from .municipal_ui import MunicipalDialog
from .app import QualificationWindow


def test_targeted_suggestion_is_not_applied_or_approved_on_open(app,tmp_path):
    p,data=overlapped();store=PlanStore(tmp_path/'plan.sqlite');plan=prepare(p,data);store.save(p,plan,None)
    focus=next(b['id'] for b in plan['blocks'] if b['start']==.1)
    d=WERReviewDialog(p,data,store=store,media=False,focus=focus,suggested_range=[0,2])
    before=digest(p);assert d.current==focus and not any(approved(b) for b in d.plan['blocks'])
    d.use_suggestion();assert d.dirty and not d.heard.isChecked()
    assert digest(p)==before;d.reject()


def test_gap_dialog_requires_name_voice_and_explicit_hearing_and_keeps_text(app,tmp_path):
    p=reference();w=QualificationWindow(tmp_path/'human.sqlite',project=p,dataset=dataset(),media=False)
    old=digest(w.project);task={'id':'gap','zone':'z1','start':.9,'end':2,'detail':'test'}
    d=GapDialog(w,task,'Test');d.table.cellWidget(0,2).setCurrentIndex(2)
    assert not d.heard.isChecked() and not d.carry.isChecked()
    with pytest.raises(QualificationError):d.apply()
    assert digest(w.project)==old
    d.heard.setChecked(True);d.apply()
    assert w.project['zones'][0]['verbatim']==p['zones'][0]['verbatim']
    assert w.project['zones'][0]['reviews']['text']==p['zones'][0]['reviews']['text']
    assert len(w.project['zones'][0]['turns'])==2
    assert (tmp_path/'corrections.sqlite').exists();w.close()


def test_correction_queue_and_municipal_dialog_never_start_models_on_open(window):
    p=digest(window.project)
    d=CorrectionDialog(window);assert digest(window.project)==p;d.accept()
    m=MunicipalDialog(window);assert m.process is None and m.folder is None
    assert not m.run_button.isEnabled() and not m.open_button.isEnabled();m.reject()


def test_sample_choice_is_explicit_and_does_not_create_a_validation(window):
    from .municipal_ui import SamplingDialog
    before=digest(window.project);d=SamplingDialog(window)
    assert digest(window.project)==before
    d.apply()
    assert all(not any(z['reviews'].values()) and not z['verbatim'] and not z['turns'] for z in window.project['zones'])
    assert window.project['zones'][0]['id']=='M01'


def test_operator_log_change_marks_report_stale(window):
    from .corrections import TaskLog
    window.report_markdown='# Rapport';window.report_reference_hash=digest(window.project);window.report_operator_hash=digest([])
    window.update_report_view();assert 'ancienne révision' not in window.results.toPlainText()
    TaskLog(window.workspace/'corrections.sqlite').append(window.project,{'id':'test','zone':'z1'},'Test','verified_unchanged',1)
    window.update_report_view();assert 'ancienne révision' in window.results.toPlainText()


def test_play_starts_in_selected_zone_if_decoder_reset_position(window,monkeypatch):
    window.select_zone_id('z2');monkeypatch.setattr(window.player,'position',lambda:0)
    calls=[];monkeypatch.setattr(window,'seek',lambda value,*args:calls.append(value))
    window.toggle_play();assert calls==[4]


def test_qprocess_import_decodes_real_wav_without_starting_models(window,tmp_path,monkeypatch):
    import wave,time
    from PySide6.QtTest import QTest
    from .municipal_ui import QMessageBox
    from .core import read,sha
    source=tmp_path/'technical-fixture.wav'
    with wave.open(str(source),'wb') as w:w.setparams((2,2,48000,0,'NONE','not compressed'));w.writeframes(bytes(48000*4))
    before=sha(source);d=MunicipalDialog(window);d.folder=tmp_path/'imported-fixture';errors=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:errors.append(str(args[-1])))
    d.start(['import',str(d.folder),'--source',str(source),'--kind','technical_test'])
    deadline=time.monotonic()+20
    while d.process is not None and time.monotonic()<deadline:QTest.qWait(50)
    if d.process is not None:
        d.cancel();d.process.kill();QTest.qWait(100)
    assert not errors and d.process is None
    assert read(d.folder/'audio.json')['duration']==1
    assert d.run_button.isEnabled() and not d.open_button.isEnabled()
    assert sha(source)==before and not (d.folder/'runs').exists()
    d.reject()
