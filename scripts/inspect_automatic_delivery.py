"""Read-only source audit and GUI capture on a disposable SQLite backup."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = Path((root/'output/automatic-report-latest.txt').read_text().strip())
original = root/'output/registry-workflow-20261021/4c9f7125b1934a5ab4c3939945cd8bfc/municipal-copy/notetaker.sqlite3'
working = evidence/'municipal-v3/session-copy/notetaker.sqlite3'

def readonly(path):
    return sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)

with readonly(original) as source, readonly(working) as current:
    unchanged = {}
    for name, in source.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        if name.startswith('sqlite_') or name in ('job', 'draft_minutes'):
            continue
        query = 'SELECT * FROM "'+name.replace('"','""')+'"'
        unchanged[name] = sorted(source.execute(query).fetchall(), key=repr) == sorted(current.execute(query).fetchall(), key=repr)
    old_drafts = source.execute('SELECT * FROM draft_minutes').fetchall()
    new_drafts = current.execute('SELECT * FROM draft_minutes').fetchall()
    unchanged['old_drafts_preserved'] = all(row in new_drafts for row in old_drafts)
    unchanged['new_drafts_have_no_review'] = all(row[4] is None for row in new_drafts if row not in old_drafts)
assert all(unchanged.values()), unchanged

previous = json.loads((root/'output/playback-fix-20261021/758d8f8a825a450996c9b9eaed7f23e3/preservation-before.json').read_text())
hashes = {}
for name, expected in previous.items():
    path = Path(name)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes[name] = {'sha256':digest, 'unchanged':digest==expected}
# This earlier task's DB hash is historical, not the start-of-task snapshot.
# The whole logical source DB must also match the first copy of THIS task.
with readonly(original) as source, readonly(evidence/'municipal-real/session-copy/notetaker.sqlite3') as first:
    unchanged['source_matches_first_task_copy'] = all(
        sorted(source.execute('SELECT * FROM "'+name+'"').fetchall(),key=repr)==
        sorted(first.execute('SELECT * FROM "'+name+'"').fetchall(),key=repr)
        for name in unchanged if name not in ('old_drafts_preserved','new_drafts_have_no_review'))
assert unchanged['source_matches_first_task_copy']
assert all(row['unchanged'] for name,row in hashes.items() if Path(name)!=original), hashes

qa = evidence/'ui-final'
qa.mkdir(exist_ok=False)
with readonly(working) as source, sqlite3.connect(qa/'notetaker.sqlite3') as target:
    source.backup(target)

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from notetaker.infrastructure.media import configure_media_backend
configure_media_backend()
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from notetaker.ui.window import MainWindow
from notetaker.services.voice_profiles import VoiceProfiles
app = QApplication([])
app.setStyle('Fusion')
QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
window = MainWindow(qa)
window.sid = '58709d31-6b8f-434e-ac75-73871d745298'
window.load_session()
window.show()
app.processEvents()
window.grab().save(str(evidence/'simple-page-final.png'))
assert window.simple_page.points.count()==7
window.close()
app.processEvents()
vault = VoiceProfiles(working.parent)
assert not vault.policy().get('enabled') and not vault.samples()
result = {'tables_and_history_preserved':unchanged, 'original_hashes':hashes,
          'voice_policy_disabled':True, 'voice_samples':0, 'gui_points':7,
          'screenshot':'simple-page-final.png', 'human_fidelity_measured':False}
(evidence/'delivery-preservation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
