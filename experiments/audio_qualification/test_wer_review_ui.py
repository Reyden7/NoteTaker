import copy
import os
import pytest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextCursor
from .core import digest
from .wer_plan import PlanStore,approved,token_view
from .wer_review import WERReviewDialog
from .test_wer_plan import overlapped


@pytest.fixture(scope='session')
def app():return QApplication.instance() or QApplication([])


@pytest.fixture
def dialog(app,tmp_path):
    project,data=overlapped();d=WERReviewDialog(project,data,store=PlanStore(tmp_path/'plan.sqlite'),media=False)
    d.show();app.processEvents();yield d;d.dirty=False;d.reject();app.processEvents()


def choose_sequential(d):
    index=next(i for i,b in enumerate(d.plan['blocks']) if b['start']==.1)
    d.table.setCurrentCell(index,0)


def test_proposals_are_not_automatically_validated_and_reference_unchanged(dialog):
    before=digest(dialog.project);assert not any(approved(b) for b in dialog.plan['blocks'])
    assert not dialog.calculate.isEnabled()
    assert dialog.project['zones'][0]['reviews']['text'] and dialog.project['zones'][0]['reviews']['diarization']
    assert dialog.project['zones'][0]['words']==[] and digest(dialog.project)==before


def test_explicit_validation_enables_partial_wer_without_human_word_times(dialog):
    before=digest(dialog.project);choose_sequential(dialog)
    dialog.first,dialog.last=0,1;dialog.dirty=True;dialog.update_selection()
    dialog.reviewer.setText('Annotatrice test');dialog.heard.setChecked(True);dialog.validate_current()
    assert sum(approved(b) for b in dialog.plan['blocks'])==1 and dialog.calculate.isEnabled()
    assert digest(dialog.project)==before and dialog.project['zones'][0]['words']==[]
    dialog.end.setValue(.95);dialog.save_pending()
    assert not approved(dialog.block()) and not dialog.heard.isChecked()


def test_text_selection_copies_only_original_human_words(dialog):
    choose_sequential(dialog);cursor=dialog.full_text.textCursor()
    cursor.setPosition(0);cursor.setPosition(7,QTextCursor.KeepAnchor);dialog.full_text.setTextCursor(cursor)
    dialog.select_text();assert dialog.first==0 and dialog.last==1
    assert dialog.snippet.toPlainText()=='Bonjour'
    assert dialog.block()['approval'] is None


def test_additional_split_is_pending_and_old_plan_history_retained(dialog,monkeypatch):
    choose_sequential(dialog);before=digest(dialog.project);old_revision=dialog.revision;old_count=len(dialog.plan['blocks'])
    monkeypatch.setattr(dialog.player,'position',lambda:600)
    dialog.split_current()
    assert len(dialog.plan['blocks'])==old_count+1 and dialog.revision!=old_revision
    assert not any(approved(b) for b in dialog.plan['blocks']) and digest(dialog.project)==before


def test_cannot_calculate_unapproved_proposals(dialog):
    from .core import QualificationError
    with pytest.raises(QualificationError):dialog.accept()
