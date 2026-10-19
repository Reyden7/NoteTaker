"""Open actual copied debate in Qt; preserve source, draft and reviews; no inference."""
import json
import os
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
os.environ['QT_QPA_PLATFORM'] = 'windows'
from PySide6.QtWidgets import QApplication
from notetaker.ui.window import MainWindow
from notetaker.services.storage import SessionStore
from notetaker.domain.information_registry import source_fingerprint
from notetaker.infrastructure.atomic import atomic_json

work = ROOT / 'output/information-registry/field-670'
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
store = SessionStore(work / 'data')
before = store.get(sid)
source = source_fingerprint(before)
reviews = [tuple(r) for r in store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision', (sid,))]
store.close()
app = QApplication([])
app.setStyle('Fusion')
window = MainWindow(work / 'data')
window.resize(1550, 1000)
window.sid = sid
window.load_session()
window.tabs.setCurrentWidget(window.registry_page)
window.show()
app.processEvents()
out = work / 'ui'
out.mkdir(exist_ok=True)
window.grab().save(str(out / 'registry-real.png'))
page = window.registry_page
page.filter.setCurrentIndex(page.filter.findData('review'))
app.processEvents()
page.detail_tabs.setCurrentIndex(1)
app.processEvents()
window.grab().save(str(out / 'review-real.png'))
window.close()
app.processEvents()
store = SessionStore(work / 'data')
assert source_fingerprint(store.get(sid)) == source
assert store.get(sid)['draft'] == before['draft']
assert reviews == [tuple(r) for r in store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision', (sid,))]
store.close()
report = {'scope': 'actual source Qt UI opened on complete isolated debate copy; compiled modules matched separately',
    'source_rows': len(before['utterances']), 'source_draft_reviews_unchanged': True,
    'inference_performed': False, 'human_review_created': False,
    'images': [str(out / name) for name in ['registry-real.png', 'review-real.png']],
    'visually_inspected': False}
atomic_json(ROOT / 'docs/evidence/information-registry-field-ui.json', report)
print(json.dumps(report, ensure_ascii=True, indent=2))
