"""One local player, bounded PCM excerpts, explicit failure and resource cleanup."""
from pathlib import Path
from tempfile import TemporaryDirectory
from notetaker.infrastructure.media import configure_media_backend

configure_media_backend()
from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from notetaker.services.playback_audio import write_playback_excerpt


class LocalPlayback(QObject):
    positionChanged = Signal(int)
    message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.output)
        self.player.errorOccurred.connect(self._error)
        self.player.mediaStatusChanged.connect(self._status)
        self.player.positionChanged.connect(self._position)
        self.watchdog = QTimer(self)
        self.watchdog.setSingleShot(True)
        self.watchdog.setInterval(5000)
        self.watchdog.timeout.connect(lambda: self._error(None, 'Le lecteur ne démarre plus ou ne progresse plus.'))
        self._temp = None
        self._active = False
        self._offset = 0
        self._end = None
        self._last_position = -1
        self.last_excerpt = None

    def stop(self):
        self._active = False
        self.watchdog.stop()
        self.player.stop()
        # Release native file handles before removing/reusing the single clip.
        self.player.setSource(QUrl())
        if self._temp:
            try:
                (Path(self._temp.name) / 'passage.wav').unlink(missing_ok=True)
            except OSError:
                # No new filename is allocated on another click: bounded disk use.
                pass

    def close(self):
        self.stop()
        if self._temp:
            self._temp.cleanup()
            self._temp = None

    def play(self, path, start_ms=None, end_ms=None):
        self.stop()
        self.last_excerpt = None
        try:
            device = QMediaDevices.defaultAudioOutput()
            if device.isNull():
                raise ValueError('Aucune sortie audio Windows n’est disponible. Branchez ou activez un casque ou des haut-parleurs.')
            self.output.setDevice(device)
            path = Path(path).resolve(strict=True)
            if not path.is_file():
                raise ValueError('Le fichier audio associé est absent.')
            self._offset = 0 if start_ms is None else start_ms
            self._end = end_ms
            if start_ms is not None or end_ms is not None:
                if not self._temp:
                    self._temp = TemporaryDirectory(prefix='notetaker-playback-')
                clip = Path(self._temp.name) / 'passage.wav'
                self.last_excerpt = write_playback_excerpt(path, clip, start_ms, end_ms)
                path = clip
            self._active = True
            self._last_position = -1
            self.watchdog.start()
            self.message.emit('Lecture locale du passage sélectionné.' if end_ms is not None else 'Lecture locale de l’audio préparé.')
            self.player.setSource(QUrl.fromLocalFile(str(path)))
            if self._active:  # setSource can emit a synchronous error
                self.player.play()
        except Exception as error:
            self._active = True
            if isinstance(error, FileNotFoundError):
                detail = 'Le fichier audio associé est absent. Vérifiez son emplacement ou restaurez sa copie conservée.'
            elif isinstance(error, PermissionError):
                detail = 'Le fichier audio ou la copie temporaire est inaccessible. Vérifiez les droits d’accès et fermez les lecteurs qui utilisent ce fichier.'
            else:
                detail = str(error)
            self._error(None, detail)

    def toggle(self):
        if not self._active:
            self.message.emit('Sélectionnez un passage à écouter ou préparez l’écoute des prises.')
        elif self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.watchdog.stop()
        else:
            self.watchdog.start()
            self.player.play()

    def _position(self, position):
        if not self._active:
            return
        if position > self._last_position:
            self._last_position = position
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.watchdog.start()
        absolute = self._offset + position
        self.positionChanged.emit(min(absolute, self._end) if self._end is not None else absolute)

    def _status(self, status):
        if not self._active:
            return
        if status == QMediaPlayer.InvalidMedia:
            self._error(None, self.player.errorString() or 'Le fichier audio ne peut pas être ouvert.')
        elif status == QMediaPlayer.EndOfMedia:
            end = self._end
            self.stop()
            if end is not None:
                self.positionChanged.emit(end)
            self.message.emit('Fin du passage sélectionné.' if end is not None else 'Fin de l’enregistrement.')

    def _error(self, error=None, detail=''):
        if not self._active:
            return
        self.stop()  # latch before stop/source signals; no retry or autoplay loop
        self.message.emit('Lecture impossible : ' + (detail or self.player.errorString()) +
            ' Vérifiez la sortie son Windows, puis sélectionnez à nouveau le passage. Les données de séance sont conservées.')
