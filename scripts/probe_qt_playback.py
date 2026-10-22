"""Bounded real Windows media probe; no annotations or audio are written."""
import argparse
import json
import os
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('audio', type=Path)
parser.add_argument('--backend', choices=['ffmpeg', 'windows'], required=True)
parser.add_argument('--report', type=Path, required=True)
args = parser.parse_args()
os.environ['QT_MEDIA_BACKEND'] = args.backend
from PySide6.QtCore import QCoreApplication, QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

app = QCoreApplication([])
output = QAudioOutput()
player = QMediaPlayer()
player.setAudioOutput(output)
report = {'backend': args.backend, 'audio': str(args.audio.resolve()), 'events': [], 'devices': []}
started = time.monotonic()
for device in QMediaDevices.audioOutputs():
    fmt = device.preferredFormat()
    report['devices'].append({'name': device.description(), 'default': device.isDefault(),
        'rate': fmt.sampleRate(), 'channels': fmt.channelCount(), 'layout': str(fmt.channelConfig()),
        'sample_format': str(fmt.sampleFormat())})
def event(kind, value):
    report['events'].append({'elapsed_s': round(time.monotonic()-started, 3), 'kind': kind, 'value': value})
player.positionChanged.connect(lambda p: event('position', p))
player.mediaStatusChanged.connect(lambda s: event('status', str(s)))
player.errorOccurred.connect(lambda e, text: event('error', text))
player.setSource(QUrl.fromLocalFile(str(args.audio.resolve())))
player.play()
QTimer.singleShot(3000, app.quit)
app.exec()
player.stop()
player.setSource(QUrl())
args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
