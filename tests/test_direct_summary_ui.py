import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import uuid
from PySide6.QtWidgets import QApplication
from notetaker.infrastructure.atomic import atomic_json
from notetaker.domain.direct_summary import MARKER
from notetaker.services.storage import SessionStore
from notetaker.services.direct_summary import artifact_path
from notetaker.ui.direct_summary import DirectSummaryPage
from notetaker.ui.window import MainWindow


def test_test_tab_is_absent_by_default_and_requires_marked_copy(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path/'normal')
    assert not hasattr(window, 'direct_page')
    window.close()
    atomic_json(tmp_path/'test'/MARKER, {'id': str(uuid.uuid4()), 'purpose': 'direct-summary-test'})
    window = MainWindow(tmp_path/'test', experimental_direct=True)
    assert window.tabs.indexOf(window.direct_page) >= 0
    assert window.direct_page.length.currentData() == 'standard'
    window.close()
    app.processEvents()


def test_real_widgets_show_rejections_omissions_history_and_play_exact_source(tmp_path):
    app = QApplication.instance() or QApplication([])
    store = SessionStore(tmp_path)
    sid = store.create('Fixture interface')
    source = {'id': 's0', 'text': 'Je propose une consultation.', 'start_ms': 23000,
              'end_ms': 27000, 'speaker_id': 'a', 'uncertain': False}
    candidate = {'id': 'D1', 'topic': 'Consultation', 'section': 'proposals', 'status': 'rejected',
                 'template': '{{V1}} propose une consultation.', 'evidence': [{'id': 's0', 'quote': source['text']}]}
    result = {'topics': [], 'ledger': {'inventory': [{**source, 'written_ids': []}],
              'candidates': [candidate], 'alerts': [{'subject': 'Consultation', 'priority': 'high',
                  'reason': 'rejected_or_uncertain_information', 'rejected': [{'id': 'D1', 'reason': 'fixture'}]}]}}
    for _ in range(2):
        run = str(uuid.uuid4())
        atomic_json(artifact_path(tmp_path, sid, run), {'run_id': run, 'result': result, 'profile': {'fresh_calls': 3}})
    played, generated, edited = [], [], []
    page = DirectSummaryPage(store, generated.append, lambda: edited.append(True), played.append)
    page.load(sid)
    page.show()
    app.processEvents()
    assert page.history.count() == 2
    assert page.rows.rowCount() == 1 and page.source.count() == 1
    page.listen.click()
    assert played[0]['start_ms'] == 23000 and played[0]['id'] == 's0'
    page.view.setCurrentIndex(page.view.findData('inventory'))
    assert page.rows.rowCount() == 1 and 'Non citée' in page.rows.item(0, 1).text()
    page.search.setText('Introuvable')
    assert page.rows.rowCount() == 0
    page.start.click()
    assert generated == ['standard']
    page.close()
    store.close()
    app.processEvents()
