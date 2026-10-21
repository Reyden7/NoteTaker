"""Real Qt render/decode/seek check. Muted playback is NOT human audio validation."""
import json
import time
import uuid
from .app import QualificationWindow
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from .core import WORK,initial_project,load_dataset,verify_inputs


def main():
    root=WORK/'qa'/uuid.uuid4().hex;root.mkdir(parents=True)
    app=QApplication.instance() or QApplication([]);p=initial_project();dataset=load_dataset(p)
    window=QualificationWindow(root/'reference-test.sqlite',project=p,dataset=dataset,media=True)
    window.show();app.processEvents();QTest.qWait(100)
    window.grab().save(str(root/'annotation-masquee.png'))
    window.select_zone_id('E11');window.show_hypotheses.setChecked(True);app.processEvents();QTest.qWait(100)
    window.grab().save(str(root/'comparaison-E11.png'))
    window.audio.setMuted(True)
    deadline=time.monotonic()+12
    while window.player.mediaStatus() not in (QMediaPlayer.LoadedMedia,QMediaPlayer.BufferedMedia,QMediaPlayer.InvalidMedia) and time.monotonic()<deadline:
        QTest.qWait(100)
    window.seek(1090);QTest.qWait(100);before=window.player.position();window.player.play();QTest.qWait(900)
    after=window.player.position();window.player.pause()
    record={'scope':'UI render + real local WAV decode and muted transport; no acoustic fidelity or human annotation claimed',
        'audio_source':window.player.source().toLocalFile(),'audio_sha256':p['audio']['sha256'],
        'media_status':str(window.player.mediaStatus()),'media_error':window.player.errorString(),
        'playback_backend':__import__('os').environ.get('QT_MEDIA_BACKEND','default'),
        'output_name':window.audio.device().description(),'output_null':window.audio.device().isNull(),
        'position_before_ms':before,'position_after_ms':after,'position_advanced':after>before+200,
        'active_rows':{k:sorted(v.active) for k,v in window.views.items()},
        'visible_rows':{k:v.table.rowCount() for k,v in window.views.items()},
        'reference_empty':all(not z['verbatim'] and not z['turns'] for z in window.project['zones']),
        'screenshots':[str(root/'annotation-masquee.png'),str(root/'comparaison-E11.png')]}
    window.start_scoring();deadline=time.monotonic()+30
    while window.scoring_process is not None and time.monotonic()<deadline:QTest.qWait(100)
    record['score_report']=str(window.last_report) if window.last_report else None
    if window.last_report:
        scores=json.loads(window.last_report.with_name('scores.json').read_text(encoding='utf-8'))
        record['unannotated_scores_remain_null']=all(r['transcription']['WER'] is None and r['diarization']['DER'] is None for r in scores['results'].values())
        record['score_network_attempts']=scores['python_network_attempts']
        record['report_visible_in_interface']=window.tabs.currentWidget() is window.results and 'non mesuré' in window.results.toPlainText()
    window.close();verify_inputs(p)
    record['inputs_unchanged']=True;(root/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=True,indent=2),flush=True)
    assert record['position_advanced'] and record['reference_empty'] and not record['media_error'] and not record['output_null']
    assert record['score_report'] and record['unannotated_scores_remain_null'] and record['score_network_attempts']==0
    assert record['report_visible_in_interface']


if __name__=='__main__':main()
