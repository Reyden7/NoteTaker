"""Real Windows application playback on a SQLite backup, without editing sources.

Run with --recipe <data directory> --output <new directory>. Uses the installed
Windows output, at the application's normal volume. No models or network.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import wave

parser = argparse.ArgumentParser()
parser.add_argument('--recipe', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
from notetaker.infrastructure.offline import enforce_offline, deny_python_network
enforce_offline()
attempts = deny_python_network()
from notetaker.ui.window import MainWindow
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from windows_audio_meter import ProcessAudioMeter

original = args.recipe/'notetaker.sqlite3'
before = hashlib.sha256(original.read_bytes()).hexdigest()
copied = args.output/'recipe-copy'; copied.mkdir()
with sqlite3.connect(original.resolve().as_uri()+'?mode=ro', uri=True) as src:
    with sqlite3.connect(copied/'notetaker.sqlite3') as dst:
        src.backup(dst)
app = QApplication([])
window = MainWindow(copied)
window.show(); app.processEvents()
meter = ProcessAudioMeter()
sid = window.store.list_sessions()[0]['id']
window.sid = sid; window.load_session()
registry = window.registry_page
candidate = next(e for e in registry.visible if e['category']=='information' and e['evidence'] and
    any(s['start_ms'] > 0 and 1000 <= s['end_ms']-s['start_ms'] <= 10000 for s in registry.current['content']['sources']
        if s['id']==e['evidence'][0]['id']))
registry.focus_entry(candidate['id'])
uid = registry.sources.item(0,0).data(256)
source = next(s for s in registry.current['content']['sources'] if s['id']==uid)
path = Path(json.loads(source['source_json'])['normalized_audio'])
audio_before = hashlib.sha256(path.read_bytes()).hexdigest()
report = {'backend':os.environ.get('QT_MEDIA_BACKEND'), 'audio':str(path), 'source_id':uid,
          'start_ms':source['start_ms'], 'end_ms':source['end_ms'], 'routes':[]}
with wave.open(str(path),'rb') as w:
    report['wave'] = dict(zip(['channels','sample_width','rate','frames','compression','compression_name'],w.getparams()))
for route in ['registry', 'transcription']:
    messages = []; positions = []; peaks = []
    window.playback.message.connect(messages.append)
    window.playback.positionChanged.connect(positions.append)
    if route == 'registry':
        window.tabs.setCurrentWidget(registry)
        next(b for b in registry.findChildren(QPushButton) if b.text()=='Écouter la citation sélectionnée').click()
    else:
        window.tabs.setCurrentIndex(2)  # Transcription et voix
        app.processEvents()
        row = next(i for i,u in enumerate(window.state['utterances']) if u['id']==uid)
        window.transcript_table.selectRow(row)
        next(b for b in window.findChildren(QPushButton) if b.text()=='Écouter le passage').click()
    excerpt = window.playback.last_excerpt
    assert excerpt and excerpt['start_ms']==source['start_ms'] and excerpt['end_ms']==source['end_ms']
    loaded_path = Path(window.player.source().toLocalFile())
    with wave.open(str(loaded_path),'rb') as w:
        w.setpos(0); pcm=w.readframes(w.getnframes())
    with wave.open(str(path),'rb') as w:
        w.setpos(excerpt['first_frame']); expected=w.readframes(excerpt['frames'])
    assert pcm == expected
    start = time.monotonic()
    while window.playback._active and time.monotonic()-start < 15:
        QTest.qWait(50)
        try:
            peaks.append(meter.peak())
        except OSError as error:
            window.playback.close()
            raise RuntimeError('Le contrôle Core Audio de recette a été refusé ; lecteur arrêté proprement.') from error
    elapsed = time.monotonic()-start
    QTest.qWait(200)
    report['routes'].append({'route':route,'elapsed_s':elapsed, 'messages':messages, 'positions':positions,
        'process_peak_max':max(peaks, default=0), 'nonzero_meter_samples':sum(p>0 for p in peaks),
        'excerpt':excerpt, 'pcm_exact':pcm==expected, 'temp_removed':not loaded_path.exists(),
        'stopped':window.player.playbackState()==QMediaPlayer.StoppedState})
    assert not window.playback._active and any('Fin du passage' in m for m in messages)
    assert max(peaks, default=0)>0 and positions[-1]==source['end_ms']
    window.playback.message.disconnect(messages.append)
    window.playback.positionChanged.disconnect(positions.append)
    window.grab().save(str(args.output/(route+'.png')))
# Replacing a request must release the one native file handle, without allocating
# more players/processes/clip filenames. Then exercise a stereo PCM copy too.
for _ in range(4):
    window.playback.play(path, source['start_ms'], source['end_ms'])
    QTest.qWait(75)
window.playback.stop(); QTest.qWait(100)
assert not window.playback._active and not window.playback.watchdog.isActive()
assert not list(Path(window.playback._temp.name).glob('*.wav'))
stereo = args.output/'stereo-fixture-from-municipal.wav'
with wave.open(str(path),'rb') as w:
    w.setpos(source['start_ms']*w.getframerate()//1000)
    mono = w.readframes(w.getframerate())
    rate = w.getframerate()
with wave.open(str(stereo),'wb') as w:
    w.setparams((2,2,rate,0,'NONE','not compressed'))
    w.writeframes(b''.join(mono[i:i+2]*2 for i in range(0,len(mono),2)))
window.playback.play(stereo,0,1000)
stereo_peaks = []
start = time.monotonic()
while window.playback._active and time.monotonic()-start < 6:
    QTest.qWait(50); stereo_peaks.append(meter.peak())
assert not window.playback._active and max(stereo_peaks,default=0)>0
report['stereo_pcm_peak'] = max(stereo_peaks)
report['rapid_replacements'] = 4
report['remaining_temp_clips'] = len(list(Path(window.playback._temp.name).glob('*.wav')))
window.close(); app.processEvents(); meter.close()
report['original_db_unchanged'] = hashlib.sha256(original.read_bytes()).hexdigest()==before
report['source_audio_unchanged'] = hashlib.sha256(path.read_bytes()).hexdigest()==audio_before
report['python_network_attempts'] = attempts
report['physical_listening_verified_by_human'] = False
(args.output/'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
assert report['original_db_unchanged'] and report['source_audio_unchanged'] and not attempts
print(json.dumps({'routes':[{k:r[k] for k in ['route','elapsed_s','process_peak_max','nonzero_meter_samples','temp_removed','stopped']} for r in report['routes']],
    'original_db_unchanged':report['original_db_unchanged']}, indent=2))
