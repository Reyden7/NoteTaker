"""Inspect the real generated experiment in Qt on a secondary isolated copy."""
import argparse
import json
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
os.environ['QT_QPA_PLATFORM'] = 'windows'
from PySide6.QtWidgets import QApplication
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.domain.direct_summary import MARKER
from notetaker.services.storage import SessionStore
from notetaker.services.direct_summary import artifact_path
from notetaker.ui.window import MainWindow

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
args = p.parse_args()
work = args.work.resolve()
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
report = read(work/'cold-report.json')
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
primary = work/'data'
primary_store = SessionStore(primary)
before = primary_store.get(sid)
run = report['service_result']['run_id']
primary_artifact = artifact_path(primary, sid, run)
artifact_digest = sha256_file(primary_artifact)
copy_root = work/'ui'/('data-'+uuid.uuid4().hex)
copy_root.mkdir(parents=True, exist_ok=False)
with sqlite3.connect((primary/'notetaker.sqlite3').as_uri()+'?mode=ro', uri=True) as source, sqlite3.connect(copy_root/'notetaker.sqlite3') as target:
    source.backup(target)
shutil.copy2(primary/MARKER, copy_root/MARKER)
copied_artifact = artifact_path(copy_root, sid, run)
copied_artifact.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(primary_artifact, copied_artifact)
app = QApplication([])
app.setStyle('Fusion')
window = MainWindow(copy_root, experimental_direct=True)
window.resize(1740, 1040)
window.sid = sid
window.load_session()
page = window.direct_page
window.tabs.setCurrentWidget(page)
window.show()
app.processEvents()
images = []
for key in ('alerts', 'topics', 'candidates', 'inventory'):
    page.view.setCurrentIndex(page.view.findData(key))
    page.search.clear()
    app.processEvents()
    path = work/'ui'/('direct-'+key+'.png')
    assert window.grab().save(str(path))
    images.append(str(path))
window.tabs.setCurrentIndex(3)
app.processEvents()
path = work/'ui'/'direct-editor.png'
assert window.grab().save(str(path))
images.append(str(path))
window.close()
app.processEvents()
assert primary_store.get(sid) == before
assert sha256_file(primary_artifact) == artifact_digest
primary_store.close()
evidence = {'scope': 'actual source Qt UI displaying complete generated real debate on secondary copy',
    'rows': len(before['utterances']), 'primary_session_and_artifact_unchanged': True,
    'human_review_created': False, 'inference_performed': False, 'visually_inspected': False, 'images': images}
atomic_json(ROOT/'docs/evidence/direct-summary-field-ui.json', evidence)
print(json.dumps(evidence, ensure_ascii=True, indent=2))
