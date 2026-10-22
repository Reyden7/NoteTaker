import copy
import json
import os
import wave
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer
from notetaker.services.playback_audio import write_playback_excerpt
from notetaker.infrastructure.media import configure_media_backend
from notetaker.ui.playback import LocalPlayback


def wav(path, channels=1, rate=16000):
    samples = bytes(range(256)) * (rate * channels * 2 // 256 + 1)
    samples = samples[:rate * channels * 2]
    with wave.open(str(path), 'wb') as out:
        out.setparams((channels, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(samples)
    return samples


@pytest.mark.parametrize('channels,rate', [(1,16000), (2,48000), (1,44100)])
def test_exact_pcm_frames_and_header_without_source_change(tmp_path, channels, rate):
    source, target = tmp_path/'source.wav', tmp_path/'passage.wav'
    samples = wav(source, channels, rate)
    before = source.read_bytes()
    report = write_playback_excerpt(source, target, 123, 567)
    with wave.open(str(target), 'rb') as audio:
        assert audio.getnchannels() == channels
        assert audio.getsampwidth() == 2 and audio.getframerate() == rate
        assert audio.getnframes() == report['last_frame'] - report['first_frame']
        assert audio.readframes(audio.getnframes()) == samples[report['first_frame']*channels*2:report['last_frame']*channels*2]
    assert source.read_bytes() == before
    assert report['start_ms'] == 123 and report['end_ms'] == 567


@pytest.mark.parametrize('start,end', [(0,0), (300,200), (-1,100), (0,1001), (None,100)])
def test_bad_boundaries_fail_without_clamping_or_original_changes(tmp_path, start, end):
    source = tmp_path/'source.wav'; wav(source)
    before = source.read_bytes()
    with pytest.raises(ValueError):
        write_playback_excerpt(source, tmp_path/'clip.wav', start, end)
    assert source.read_bytes() == before and not (tmp_path/'clip.wav').exists()


def test_source_cannot_be_overwritten_and_corruption_is_explicit(tmp_path):
    source = tmp_path/'source.wav'; wav(source)
    with pytest.raises(ValueError, match='distincte'):
        write_playback_excerpt(source, source, 0, 100)
    damaged = tmp_path/'damaged.wav'; damaged.write_bytes(source.read_bytes()[:-100])
    with pytest.raises(ValueError, match='tronqué'):
        write_playback_excerpt(damaged, tmp_path/'clip.wav', 0, 1000)
    assert not (tmp_path/'clip.wav').exists()


@pytest.mark.parametrize('channels,width', [(3,2), (1,1)])
def test_unsupported_wav_is_rejected_explicitly(tmp_path, channels, width):
    source = tmp_path/'source.wav'
    with wave.open(str(source), 'wb') as out:
        out.setparams((channels,width,16000,0,'NONE','not compressed'))
        out.writeframes(b'\0'*(16000*channels*width))
    with pytest.raises(ValueError, match='PCM 16 bits mono ou stéréo'):
        write_playback_excerpt(source,tmp_path/'clip.wav',0,200)


def test_backend_is_windows_only_and_process_local(monkeypatch):
    import notetaker.infrastructure.media as module
    monkeypatch.setenv('QT_MEDIA_BACKEND', 'ffmpeg')
    monkeypatch.setattr(module.sys, 'platform', 'win32')
    configure_media_backend()
    assert os.environ['QT_MEDIA_BACKEND'] == 'windows'
    monkeypatch.setattr(module.sys, 'platform', 'linux')
    monkeypatch.setenv('QT_MEDIA_BACKEND', 'custom')
    configure_media_backend()
    assert os.environ['QT_MEDIA_BACKEND'] == 'custom'


class Player(QObject):
    errorOccurred = Signal(object, str)
    mediaStatusChanged = Signal(object)
    positionChanged = Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.url = QUrl(); self.plays = 0; self.stops = 0
        self.state = QMediaPlayer.StoppedState
    def setAudioOutput(self, output): pass
    def source(self): return self.url
    def setSource(self, url): self.url = url
    def play(self): self.plays += 1; self.state = QMediaPlayer.PlayingState
    def pause(self): self.state = QMediaPlayer.PausedState
    def playbackState(self): return self.state
    def stop(self): self.stops += 1; self.state = QMediaPlayer.StoppedState
    def errorString(self): return 'échec technique de test'


@pytest.fixture
def playback(monkeypatch):
    from notetaker.ui import playback as module
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(module, 'QMediaPlayer', Player)
    # Fake only the transport: no sound/hardware requirement for unit tests.
    for name in ('PlayingState','StoppedState','PausedState','InvalidMedia','EndOfMedia'):
        setattr(Player, name, getattr(QMediaPlayer, name))
    class Device:
        def isNull(self): return False
    class Devices:
        @staticmethod
        def defaultAudioOutput(): return Device()
    class Output:
        def __init__(self, parent=None): pass
        def setDevice(self, device): pass
    monkeypatch.setattr(module, 'QMediaDevices', Devices)
    monkeypatch.setattr(module, 'QAudioOutput', Output)
    controller = LocalPlayback()
    messages = []; controller.message.connect(messages.append)
    yield controller, messages, app
    controller.close()


def test_one_clip_no_pending_seek_end_and_no_repeated_error(playback, tmp_path):
    controller, messages, app = playback
    source = tmp_path/'source.wav'; wav(source)
    positions = []; controller.positionChanged.connect(positions.append)
    controller.play(source, 123, 567)
    clip = Path(controller.player.source().toLocalFile())
    assert clip != source and clip.exists()
    controller.player.positionChanged.emit(200)
    assert positions[-1] == 323
    controller.toggle(); assert not controller.watchdog.isActive()
    controller.toggle(); assert controller.watchdog.isActive()
    controller.player.mediaStatusChanged.emit(QMediaPlayer.EndOfMedia)
    assert not controller._active and not controller.watchdog.isActive()
    assert positions[-1] == 567 and not clip.exists()
    controller.play(source, 100, 300)
    assert Path(controller.player.source().toLocalFile()) == clip
    controller.player.errorOccurred.emit(None, 'sortie indisponible')
    count = len(messages)
    controller.player.errorOccurred.emit(None, 'sortie indisponible')
    controller.player.mediaStatusChanged.emit(QMediaPlayer.LoadedMedia)
    assert len(messages) == count and 'Lecture impossible' in messages[-1]
    assert not clip.exists() and not controller.watchdog.isActive()
    assert controller.player.plays == 3  # first, resume, second clip; no retry
    controller.play(source)  # full preview must reset the excerpt interval
    assert controller._offset == 0 and controller._end is None
    assert controller.player.source() == QUrl.fromLocalFile(str(source))


def test_watchdog_and_missing_file_report_once(playback, tmp_path):
    controller, messages, app = playback
    source = tmp_path/'source.wav'; wav(source)
    controller.play(source, 0, 200)
    controller.watchdog.timeout.emit()
    assert 'ne progresse plus' in messages[-1] and not controller._active
    assert controller.player.source().isEmpty()
    controller.play(tmp_path/'absent.wav', 0, 200)
    assert 'Lecture impossible' in messages[-1] and not controller._active


def test_missing_output_device_has_actionable_error_without_loading(playback, tmp_path, monkeypatch):
    from notetaker.ui import playback as module
    controller, messages, app = playback
    class Missing:
        def isNull(self): return True
    monkeypatch.setattr(module.QMediaDevices, 'defaultAudioOutput', lambda: Missing())
    source = tmp_path/'source.wav'; wav(source)
    controller.play(source, 0, 200)
    assert 'Aucune sortie audio Windows' in messages[-1]
    assert controller.player.plays == 0 and controller.player.source().isEmpty()
    assert not controller.watchdog.isActive() and not controller._active


def test_error_during_setsource_never_autoplays(playback, tmp_path, monkeypatch):
    controller, messages, app = playback
    source = tmp_path/'source.wav'; wav(source)
    set_source = controller.player.setSource
    def fail(url):
        set_source(url)
        if not url.isEmpty():
            controller.player.errorOccurred.emit(None, 'Initialisation impossible')
    monkeypatch.setattr(controller.player, 'setSource', fail)
    controller.play(source,0,200)
    assert not controller._active and controller.player.plays == 0
    assert controller.player.source().isEmpty() and not controller.watchdog.isActive()
    assert len([m for m in messages if 'Lecture impossible' in m]) == 1


def test_both_ui_routes_preserve_the_snapshot_and_pass_exact_bounds(tmp_path, monkeypatch):
    from notetaker.ui.window import MainWindow
    from notetaker.services.information_registry import RegistryService
    from PySide6.QtWidgets import QPushButton
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path/'data')
    audio = tmp_path/'normalized.wav'; wav(audio)
    sid = window.store.create('Test écoute')
    window.store.save_analysis(sid, [{'id':'s0','speaker_id':'a','start_ms':123,'end_ms':567,
        'text':'Je propose une consultation.','uncertain':False,
        'source':{'normalized_audio':str(audio)}}], {'a':'Intervenant'}, 0)
    # Store's input source contract is an explicit nested dict.
    window.sid = sid; window.load_session()
    record = RegistryService(window.store).initialize(sid)
    window.registry_page.load(sid)
    window.registry_page.filter.setCurrentIndex(window.registry_page.filter.findData('sources'))
    captured = []
    monkeypatch.setattr(window.playback, 'play', lambda *args: captured.append(args))
    before = copy.deepcopy(window.store.get(sid)['utterances'])
    window.transcript_table.selectRow(0); window.play_selected()
    next(b for b in window.registry_page.findChildren(QPushButton) if b.text()=='Écouter la citation sélectionnée').click()
    assert captured == [(audio,123,567), (audio,123,567)]
    assert window.store.get(sid)['utterances'] == before
    assert RegistryService(window.store).latest(sid)['content']['sources'] == record['content']['sources']
    window.close(); app.processEvents()
