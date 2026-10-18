import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import pytest
from notetaker.ui.window import MainWindow

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def window(app, tmp_path):
    win = MainWindow(tmp_path / "ui-data")
    win.show()
    app.processEvents()
    yield win
    win.close()
    app.processEvents()

def test_create_save_reopen_and_archive_via_widgets(window, app, monkeypatch):
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Conseil de test", True))
    QTest.mouseClick(window.new_button, Qt.LeftButton)
    app.processEvents()
    assert window.sid and window.history.count() == 1
    sid = window.sid
    window.commune_edit.setText("Commune exemple")
    window.agenda_edit.setPlainText("Travaux\nBudget")
    window.save_details()
    window.archive_session()
    window.load_session()
    assert window.commune_edit.text() == "Commune exemple"
    assert window.store.get(sid)["metadata"]["agenda"] == ["Travaux", "Budget"]
    assert window.store.get(sid)["archived"] == 1

def test_review_is_never_set_by_loading_or_editing(window, app, monkeypatch):
    sid = window.store.create("Contrôle humain", {"agenda": ["Travaux"]})
    window.store.save_analysis(sid, [{"id": "s0", "start_ms": 0, "end_ms": 1000, "text": "Discussion", "speaker_id": "a", "uncertain": True}], {"a": "Intervenant 1"}, 0)
    window.store.save_draft(sid, {"points": [{"title": "Travaux", "summary": "Discussion", "sources": ["s0"], "vote_id": None}], "to_verify": []})
    window.sid = sid
    window.load_session()
    assert window.store.get(sid)["draft"]["review"] is None
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Test reviewer", True))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.No)
    window.approve()
    assert window.store.get(sid)["draft"]["review"] is None
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    window.approve()
    assert window.store.get(sid)["draft"]["review"] is not None
    window.point_text.setPlainText("Correction humaine")
    window.save_draft()
    assert window.store.get(sid)["draft"]["review"] is None

def test_ui_export_requires_explicit_review_action(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    sid = window.store.create("Export UI", {"agenda": ["Travaux"]})
    window.store.save_analysis(sid, [{"id": "s0", "start_ms": 0, "end_ms": 1000, "text": "Texte contrôlé", "speaker_id": "a", "uncertain": True}], {"a": "Intervenant 1"}, 0)
    window.store.save_draft(sid, {"points": [{"title": "Travaux", "summary": "Texte contrôlé", "sources": ["s0"], "vote_id": None}], "to_verify": []})
    window.sid = sid
    window.load_session()
    target = tmp_path / "ui-export.pdf"
    errors = []
    monkeypatch.setattr(window, "report_error", lambda error: errors.append(str(error)))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), "PDF"))
    window.export("pdf")
    assert errors and not target.exists()
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Automated UI test reviewer", True))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    window.approve()
    window.export("pdf")
    assert target.is_file()


def test_municipal_ui_requires_secretary_confirmation(window, monkeypatch):
    from notetaker.services.pipeline import integral_transcript
    sid = window.store.create("PV test")
    window.store.save_analysis(sid, [{"id": "s0", "start_ms": 0, "end_ms": 1000, "text": "Texte fictif", "speaker_id": "a", "uncertain": False}], {"a": "Voix test"}, 0)
    draft = integral_transcript(window.store.get(sid))
    draft["document_mode"] = "municipal"
    window.store.save_draft(sid, draft)
    window.sid = sid
    window.load_session()
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Test fixture secretary", True))
    answers = iter([QMessageBox.Yes, QMessageBox.No])
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: next(answers))
    window.approve()
    assert window.store.get(sid)["draft"]["review"] is None
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    window.approve()
    assert window.store.get(sid)["draft"]["review"]["reviewer_role"] == "secretary"
