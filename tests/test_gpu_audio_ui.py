import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtWidgets import QApplication, QDialog, QComboBox
from PySide6.QtCore import QTimer
from notetaker.ui.window import MainWindow, explain_error
from notetaker.services.audio_engine import read_mode, save_mode


@pytest.fixture
def window(tmp_path):
    app=QApplication.instance() or QApplication([])
    win=MainWindow(tmp_path/'data');win.show();app.processEvents()
    yield win
    win.close();app.processEvents()


@pytest.mark.parametrize('mode',['cpu','gpu','auto'])
def test_audio_settings_save_and_reopen(window,mode):
    def select():
        dialog=window.findChild(QDialog)
        choice=dialog.findChild(QComboBox,'audio_engine_choice')
        assert choice.count()==3
        choice.setCurrentIndex(choice.findData(mode));dialog.accept()
    QTimer.singleShot(0,select)
    window.audio_settings()
    assert read_mode(window.store.root)==mode
    assert 'Moteur audio' in window.engine_status.text()


def test_settings_cancel_retains_previous_mode(window):
    save_mode(window.store.root,'cpu')
    QTimer.singleShot(0,lambda:window.findChild(QDialog).reject())
    window.audio_settings();assert read_mode(window.store.root)=='cpu'


def test_gpu_error_offers_explicit_cpu_retry_without_starting_it(window,monkeypatch):
    sid=window.store.create('Test');window.sid=sid;window.load_session()
    calls=[]
    monkeypatch.setattr(window,'analyse',lambda mode=None:calls.append(mode))
    window.task_failure('analysis','GPUUnavailable : GPU_AUDIO_UNAVAILABLE:GPU_OUT_OF_MEMORY')
    assert window.cpu_retry.isVisible() and calls==[]
    assert 'mémoire GPU' in window.status.text()
    window.cpu_retry.click();assert calls==['cpu']


def test_cancellation_is_not_a_gpu_failure(window):
    window.task_failure('analysis','JobCancelled : JOB_CANCELLED')
    assert not window.cpu_retry.isVisible()
    assert 'conserv' in window.status.text()


def test_gpu_diagnostics_in_french():
    assert '8 Gio' in explain_error('GPU_AUDIO_UNAVAILABLE:GPU_MEMORY_INSUFFICIENT')
    assert 'CUDA' in explain_error('GPU_AUDIO_UNAVAILABLE:GPU_CUDA_UNAVAILABLE')
