import json
import shutil
import threading
import uuid
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QDate, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QTabWidget, QSplitter, QComboBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QDateEdit, QMessageBox, QFileDialog, QInputDialog, QSpinBox)
from notetaker.domain.minutes import content_digest
from notetaker.infrastructure.paths import session_directory
from notetaker.services.storage import SessionStore
from notetaker.services.recording import MicrophoneRecorder, input_devices, recover_capture
from notetaker.services.audio import import_audio, prepare_audio
from notetaker.services.pipeline import Pipeline
from notetaker.services.session_export import export_session

class Task(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function
        self.cancel = threading.Event()
    def run(self):
        try:
            self.succeeded.emit(self.function(self.progress.emit, self.cancel))
        except Exception as error:
            self.failed.emit(f"{type(error).__name__} : {error}")

def button(text, slot, primary=False):
    value = QPushButton(text)
    value.clicked.connect(slot)
    if primary:
        value.setProperty("primary", True)
    return value

def paragraph(text):
    value = QLabel(text)
    value.setWordWrap(True)
    return value

class MainWindow(QMainWindow):
    def __init__(self, data_root):
        super().__init__()
        self.store = SessionStore(Path(data_root))
        interrupted = self.store.recover()
        self.sid = None
        self.state = None
        self.task = None
        self.recorder = None
        self.recording_take = None
        self.edit_uid = None
        self.point_index = None
        self.pending_seek = None
        self.loading = False
        self.setWindowTitle("NoteTaker — séances et procès-verbaux")
        self.resize(1280, 850)
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(STYLE)
        self._build()
        self._recover_recordings()
        self.reload_history()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(100)
        self.transcript_timer = QTimer(self)
        self.transcript_timer.setSingleShot(True)
        self.transcript_timer.timeout.connect(self.save_utterance)
        if interrupted:
            self.status.setText(f"{interrupted} traitement(s) interrompu(s). Les prises originales sont conservées ; relancez l’analyse si nécessaire.")

    def _build(self):
        shell = QWidget()
        outer = QHBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)
        side = QVBoxLayout(sidebar)
        brand = QLabel("NoteTaker")
        brand.setObjectName("brand")
        side.addWidget(brand)
        side.addWidget(paragraph("Vos séances, conservées localement"))
        self.new_button = button("+  Nouvelle séance", self.new_session, True)
        side.addWidget(self.new_button)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher une séance…")
        self.search.textChanged.connect(self.reload_history)
        side.addWidget(self.search)
        self.history = QListWidget()
        self.history.setWordWrap(True)
        self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history.currentItemChanged.connect(self.select_session)
        side.addWidget(self.history, 1)
        self.archive_button = button("Archiver / réactiver", self.archive_session)
        side.addWidget(self.archive_button)
        side.addWidget(paragraph("Version de travail 0.1\nRecette terrain non validée"))
        outer.addWidget(sidebar)
        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 16)
        self.heading = QLabel("Préparez votre prochaine séance")
        self.heading.setObjectName("heading")
        body.addWidget(self.heading)
        actions = QHBoxLayout()
        self.analyse_button = button("1. Transcrire et distinguer les voix", self.analyse, True)
        self.generate_button = button("2. Préparer le brouillon", self.generate)
        self.cancel_button = button("Annuler le traitement", self.cancel_task)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.analyse_button)
        actions.addWidget(self.generate_button)
        actions.addStretch()
        actions.addWidget(self.cancel_button)
        body.addLayout(actions)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_details(), "Séance")
        self.tabs.addTab(self.build_audio(), "Audio")
        self.tabs.addTab(self.build_transcript(), "Transcription et voix")
        self.tabs.addTab(self.build_minutes(), "Projet de procès-verbal")
        self.tabs.addTab(self.build_votes(), "Décisions et votes")
        body.addWidget(self.tabs, 1)
        self.status = paragraph("Créez une séance ou rouvrez-la dans l’historique. Tous les traitements se font sur cet ordinateur.")
        body.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.hide()
        body.addWidget(self.progress)
        outer.addLayout(body, 1)
        self.setCentralWidget(shell)
        self.enable_session(False)

    def build_details(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.title_edit, self.commune_edit, self.location_edit = QLineEdit(), QLineEdit(), QLineEdit()
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        for label, field in [("Titre", self.title_edit), ("Commune", self.commune_edit), ("Date", self.date_edit), ("Lieu", self.location_edit)]:
            form.addRow(label, field)
        self.participants_edit, self.agenda_edit, self.notes_edit = QTextEdit(), QTextEdit(), QTextEdit()
        self.participants_edit.setPlaceholderText("Une personne par ligne ; fonctions, absences et pouvoirs à préciser si nécessaire.")
        self.agenda_edit.setPlaceholderText("Un point de l’ordre du jour par ligne")
        self.notes_edit.setPlaceholderText("Notes de l’opérateur")
        for label, field in [("Participants et présences", self.participants_edit), ("Ordre du jour", self.agenda_edit), ("Notes", self.notes_edit)]:
            field.setMaximumHeight(110)
            form.addRow(label, field)
        layout.addLayout(form)
        layout.addWidget(button("Enregistrer les informations", self.save_details, True))
        layout.addStretch()
        return page

    def build_audio(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(paragraph("Choisissez un microphone et vérifiez le niveau pendant la prise. L’audio est sauvegardé progressivement. Les analyses démarrent après l’arrêt de la prise."))
        row = QHBoxLayout()
        self.microphone = QComboBox()
        row.addWidget(self.microphone, 1)
        row.addWidget(button("Actualiser les microphones", self.refresh_devices))
        layout.addLayout(row)
        controls = QHBoxLayout()
        self.record_button = button("●  Enregistrer", self.start_recording, True)
        self.pause_button = button("Pause / reprendre", self.pause_recording)
        self.stop_button = button("Arrêter et sauvegarder", self.stop_recording)
        for b in [self.record_button, self.pause_button, self.stop_button]:
            controls.addWidget(b)
        layout.addLayout(controls)
        self.record_label = QLabel("Aucune prise en cours")
        layout.addWidget(self.record_label)
        self.level = QProgressBar()
        self.level.setRange(0, 100)
        self.level.setFormat("Niveau micro : %p%")
        layout.addWidget(self.level)
        self.disk_label = QLabel()
        layout.addWidget(self.disk_label)
        layout.addWidget(button("Importer un enregistrement WAV, MP3 ou M4A", self.import_recording))
        self.takes = QListWidget()
        self.takes.itemChanged.connect(self.take_enabled_changed)
        layout.addWidget(self.takes, 1)
        play = QHBoxLayout()
        play.addWidget(button("Préparer / écouter toutes les prises", self.preview_audio))
        play.addWidget(button("Lecture / pause", self.toggle_playback))
        play.addWidget(button("Arrêter la lecture", lambda: self.player.stop()))
        layout.addLayout(play)
        self.playback_label = QLabel("Lecture locale")
        layout.addWidget(self.playback_label)
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self.media_ready)
        self.player.positionChanged.connect(lambda pos: self.playback_label.setText(f"Lecture : {pos // 60000:02d}:{pos // 1000 % 60:02d}"))
        self.player.errorOccurred.connect(lambda *args: self.status.setText("Lecture impossible : " + self.player.errorString()))
        self.refresh_devices()
        return page

    def build_transcript(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(paragraph("Relisez le texte et attribuez les noms à la main. Les couleurs signalent une attribution incertaine ou un chevauchement possible. Double-cliquez une ligne pour écouter le passage."))
        self.transcript_search = QLineEdit()
        self.transcript_search.setPlaceholderText("Rechercher dans la transcription")
        self.transcript_search.textChanged.connect(self.filter_transcript)
        layout.addWidget(self.transcript_search)
        splitter = QSplitter()
        self.transcript_table = QTableWidget(0, 4)
        self.transcript_table.setHorizontalHeaderLabels(["Début", "Intervenant", "Attribution", "Texte"])
        self.transcript_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.transcript_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transcript_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.transcript_table.itemSelectionChanged.connect(self.select_utterance)
        self.transcript_table.cellDoubleClicked.connect(self.play_utterance)
        splitter.addWidget(self.transcript_table)
        editor = QWidget()
        edit = QVBoxLayout(editor)
        self.speaker_combo = QComboBox()
        edit.addWidget(self.speaker_combo)
        self.uncertainty = paragraph("Sélectionnez un passage")
        edit.addWidget(self.uncertainty)
        self.utterance_edit = QTextEdit()
        self.utterance_edit.textChanged.connect(self.schedule_transcript_save)
        self.speaker_combo.currentIndexChanged.connect(self.schedule_transcript_save)
        edit.addWidget(self.utterance_edit, 1)
        edit.addWidget(button("Enregistrer et confirmer l’attribution", lambda: self.save_utterance(confirm=True), True))
        edit.addWidget(button("Scinder le passage au curseur…", self.split_utterance))
        self.speaker_table = QTableWidget(0, 2)
        self.speaker_table.setHorizontalHeaderLabels(["Voix", "Nom attribué"])
        self.speaker_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        edit.addWidget(self.speaker_table)
        edit.addWidget(button("Enregistrer les noms", self.save_speakers))
        edit.addWidget(button("Fusionner la voix sélectionnée…", self.merge_speakers))
        splitter.addWidget(editor)
        splitter.setSizes([700, 380])
        layout.addWidget(splitter, 1)
        return page

    def build_minutes(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        warning = paragraph("BROUILLON NON OFFICIEL — les extraits, décisions et votes doivent être relus. La validation autorise l’export de cette révision ; elle ne vaut pas adoption du procès-verbal.")
        warning.setObjectName("warning")
        layout.addWidget(warning)
        self.review_status = QLabel("Aucun brouillon")
        layout.addWidget(self.review_status)
        row = QHBoxLayout()
        self.points = QListWidget()
        self.points.currentRowChanged.connect(self.select_point)
        row.addWidget(self.points, 1)
        panel = QVBoxLayout()
        self.point_title = QLineEdit()
        self.point_text = QTextEdit()
        self.point_sources = QLineEdit()
        self.point_sources.setPlaceholderText("Identifiants sources séparés par des virgules")
        self.point_vote = QComboBox()
        panel.addWidget(self.point_title)
        panel.addWidget(self.point_text, 1)
        panel.addWidget(QLabel("Sources audio et transcription"))
        panel.addWidget(self.point_sources)
        panel.addWidget(QLabel("Vote saisi associé, si applicable"))
        panel.addWidget(self.point_vote)
        row.addLayout(panel, 3)
        layout.addLayout(row, 1)
        self.to_verify = QTextEdit()
        self.to_verify.setMaximumHeight(100)
        self.to_verify.setPlaceholderText("Éléments à vérifier, un par ligne")
        layout.addWidget(self.to_verify)
        controls = QHBoxLayout()
        controls.addWidget(button("Ajouter un point", self.add_point))
        controls.addWidget(button("Sauvegarder le brouillon", self.save_draft, True))
        controls.addWidget(button("J’ai relu cette révision…", self.approve))
        self.pdf_button = button("Exporter PDF", lambda: self.export("pdf"))
        self.docx_button = button("Exporter DOCX", lambda: self.export("docx"))
        controls.addWidget(self.pdf_button)
        controls.addWidget(self.docx_button)
        layout.addLayout(controls)
        return page

    def build_votes(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(paragraph("Saisissez les résultats connus et leur source. Un vote inconnu reste « À compléter ». Les quatre nombres doivent être saisis pour enregistrer un résultat ; aucune majorité ou décision n’est calculée automatiquement."))
        self.votes = QTableWidget(0, 7)
        self.votes.setHorizontalHeaderLabels(["Objet", "État", "Pour", "Contre", "Abst.", "Non-part.", "Source de la saisie"])
        self.votes.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.votes.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        for col in [2, 3, 4, 5]:
            self.votes.setColumnWidth(col, 70)
        layout.addWidget(self.votes, 1)
        controls = QHBoxLayout()
        controls.addWidget(button("Ajouter un vote", lambda: self.add_vote()))
        controls.addWidget(button("Retirer le vote sélectionné", self.remove_vote))
        layout.addLayout(controls)
        self.decisions = QTextEdit()
        self.decisions.setPlaceholderText("Décisions saisies manuellement, une par ligne. Aucune décision n’est considérée comme adoptée automatiquement.")
        self.decisions.setMaximumHeight(150)
        layout.addWidget(self.decisions)
        layout.addWidget(button("Enregistrer les décisions et les votes", self.save_manual, True))
        return page

    def report_error(self, error):
        message = explain_error(error)
        self.status.setText(message)
        QMessageBox.warning(self, "Action non effectuée", message)

    def enable_session(self, enabled):
        self.tabs.setEnabled(enabled)
        self.analyse_button.setEnabled(enabled)
        self.generate_button.setEnabled(enabled)
        self.archive_button.setEnabled(enabled)

    def reload_history(self, *args):
        current = self.sid
        self.history.blockSignals(True)
        self.history.clear()
        for record in self.store.list_sessions(self.search.text()):
            meta = json.loads(record["metadata_json"])
            item = QListWidgetItem(("[Archivée] " if record["archived"] else "") + record["title"] + "\n" + meta.get("date", ""))
            item.setData(Qt.UserRole, record["id"])
            self.history.addItem(item)
            if record["id"] == current:
                self.history.setCurrentItem(item)
        self.history.blockSignals(False)

    def new_session(self):
        title, ok = QInputDialog.getText(self, "Nouvelle séance", "Titre", text="Conseil municipal")
        if ok and title.strip():
            self.flush_edits()
            self.sid = self.store.create(title, {"date": QDate.currentDate().toString(Qt.ISODate), "agenda": []})
            self.reload_history()
            self.load_session()

    def select_session(self, item, previous=None):
        if self.loading or not item:
            return
        try:
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            self.reload_history()
            return
        self.player.stop()
        self.sid = item.data(Qt.UserRole)
        self.load_session()

    def load_session(self):
        if not self.sid:
            return
        self.loading = True
        self.edit_uid, self.point_index = None, None
        self.state = self.store.get(self.sid)
        s, m = self.state, self.state["metadata"]
        self.heading.setText(s["title"])
        self.title_edit.setText(s["title"])
        self.commune_edit.setText(m.get("municipality", ""))
        self.location_edit.setText(m.get("location", ""))
        date = QDate.fromString(m.get("date", ""), Qt.ISODate)
        self.date_edit.setDate(date if date.isValid() else QDate.currentDate())
        self.participants_edit.setPlainText(m.get("participants", ""))
        self.agenda_edit.setPlainText("\n".join(m.get("agenda", [])))
        self.notes_edit.setPlainText(m.get("notes", ""))
        self.takes.clear()
        for take in s["takes"]:
            item = QListWidgetItem(f"{'Import' if take['kind'] == 'import' else 'Microphone'} — {take['status']} — {Path(take['path']).name}")
            item.setData(Qt.UserRole, take["id"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if take.get("enabled", 1) else Qt.Unchecked)
            item.setToolTip("Cocher pour inclure dans l’analyse. Décocher conserve toujours l’original.")
            self.takes.addItem(item)
        self.populate_transcript()
        self.draft_content = json.loads(json.dumps(s["draft"]["content"])) if s["draft"] else {"points": [], "to_verify": []}
        self.points.clear()
        self.points.addItems([p["title"] for p in self.draft_content["points"]])
        self.point_title.clear()
        self.point_text.clear()
        self.point_sources.clear()
        self.to_verify.setPlainText("\n".join(self.draft_content["to_verify"]))
        self.votes.setRowCount(0)
        for vote in s["votes"]:
            self.add_vote(vote)
        self.decisions.setPlainText("\n".join(s["decisions"]))
        review = s["draft"]["review"] if s["draft"] else None
        self.review_status.setText(f"Révision {s['draft']['revision']} — " + ("relecture enregistrée par " + review["reviewer"] if review else "relecture requise") if s["draft"] else "Aucun brouillon généré")
        self.loading = False
        self.enable_session(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        if self.draft_content["points"]:
            self.points.setCurrentRow(0)

    def metadata(self):
        return {"municipality": self.commune_edit.text(), "location": self.location_edit.text(), "date": self.date_edit.date().toString(Qt.ISODate),
                "participants": self.participants_edit.toPlainText(), "agenda": [x.strip() for x in self.agenda_edit.toPlainText().splitlines() if x.strip()], "notes": self.notes_edit.toPlainText()}

    def save_details(self):
        if not self.sid or self.loading:
            return
        current = self.store.get(self.sid)
        if current["title"] != self.title_edit.text().strip() or current["metadata"] != self.metadata():
            self.store.save_details(self.sid, self.title_edit.text(), self.metadata())
            self.heading.setText(self.title_edit.text())
            self.reload_history()
            self.status.setText("Informations sauvegardées. Toute modification impose une nouvelle relecture du brouillon.")

    def archive_session(self):
        if self.sid:
            self.flush_edits()
            self.store.archive(self.sid, not self.store.get(self.sid)["archived"])
            self.reload_history()

    def refresh_devices(self):
        if self.recorder:
            return
        self.microphone.clear()
        try:
            devices = input_devices()
            devices.sort(key=lambda d: ("WASAPI" not in d["api"], d["name"]))
            for device in devices:
                self.microphone.addItem(f"{device['name']} — {device['api']}", device)
        except Exception:
            self.microphone.addItem("Aucun microphone accessible", None)

    def start_recording(self):
        if not self.sid or self.task or self.recorder:
            return
        device = self.microphone.currentData()
        if not device:
            self.report_error("Sélectionnez un microphone disponible.")
            return
        self.flush_edits()
        directory = session_directory(self.store.root, self.sid) / "captures" / str(uuid.uuid4())
        directory.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(str(directory.parent)).free < 512 * 1024**2:
            self.report_error("Espace libre inférieur à 512 Mo. Libérez de l’espace avant d’enregistrer.")
            return
        self.player.stop()
        self.recording_take = self.store.add_take(self.sid, "capture", directory, "recording")
        self.recorder = MicrophoneRecorder()
        try:
            self.recorder.start(directory, device)
        except Exception as error:
            self.store.finish_take(self.recording_take, "interrupted")
            self.recorder = None
            self.report_error("Le microphone n’a pas démarré : " + str(error))
            return
        self.record_button.setEnabled(False)
        self.microphone.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.history.setEnabled(False)
        self.new_button.setEnabled(False)
        self.analyse_button.setEnabled(False)
        self.generate_button.setEnabled(False)

    def pause_recording(self):
        if self.recorder:
            self.recorder.paused = not self.recorder.paused

    def stop_recording(self):
        if not self.recorder or self.task:
            return
        recorder = self.recorder
        def stop(progress, cancel):
            progress("Finalisation de l’audio sur disque")
            recorder.stop()
            return recorder.error
        self.run_task("stop", stop)

    def import_recording(self):
        if self.recorder or self.task or not self.sid:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Importer un enregistrement", "", "Audio (*.wav *.mp3 *.m4a)")
        if not path:
            return
        sid = self.sid
        directory = session_directory(self.store.root, sid)
        def perform(progress, cancel):
            progress("Copie et vérification de l’enregistrement original")
            target, digest = import_audio(Path(path), directory)
            store = SessionStore(self.store.root)
            try:
                store.add_take(sid, "import", target, sha256=digest)
            finally:
                store.close()
            return target
        self.run_task("import", perform)

    def _recover_recordings(self):
        for session in self.store.list_sessions():
            for take in self.store.get(session["id"])["takes"]:
                if take["kind"] == "capture" and take["status"] == "recording":
                    try:
                        recover_capture(Path(take["path"]))
                    except Exception:
                        pass
                    self.store.finish_take(take["id"], "interrupted")

    def preview_audio(self):
        if not self.sid or self.recorder or self.task:
            return
        self.flush_edits()
        takes = [t for t in self.store.get(self.sid)["takes"] if t.get("enabled", 1)]
        target = session_directory(self.store.root, self.sid) / "previews" / (str(uuid.uuid4()) + ".wav")
        self.run_task("preview", lambda progress, cancel: prepare_audio(takes, target, progress))

    def take_enabled_changed(self, item):
        if self.loading or not self.sid or self.task or self.recorder:
            return
        self.store.set_take_enabled(item.data(Qt.UserRole), item.checkState() == Qt.Checked)
        self.review_status.setText("Sélection audio modifiée — analyse et relecture à vérifier")

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def populate_transcript(self):
        self.transcript_table.setRowCount(len(self.state["utterances"]))
        for row, u in enumerate(self.state["utterances"]):
            automatic = json.loads(u["source_json"]).get("automatic_attribution", True)
            texts = [f"{u['start_ms'] // 60000:02d}:{u['start_ms'] // 1000 % 60:02d}", self.state["speakers"].get(u["speaker_id"], "À attribuer"), "À vérifier" if u["uncertain"] else ("Automatique" if automatic else "Confirmée"), u["text"]]
            for col, text in enumerate(texts):
                item = QTableWidgetItem(text)
                if u["uncertain"]:
                    item.setBackground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#fff3d6"))
                self.transcript_table.setItem(row, col, item)
        self.speaker_table.setRowCount(len(self.state["speakers"]))
        for row, (key, label) in enumerate(self.state["speakers"].items()):
            item = QTableWidgetItem(key)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.speaker_table.setItem(row, 0, item)
            self.speaker_table.setItem(row, 1, QTableWidgetItem(label))
        self.utterance_edit.clear()

    def filter_transcript(self, text):
        for row in range(self.transcript_table.rowCount()):
            self.transcript_table.setRowHidden(row, text.casefold() not in self.transcript_table.item(row, 3).text().casefold())

    def select_utterance(self):
        if self.loading:
            return
        self.save_utterance()
        row = self.transcript_table.currentRow()
        if row < 0:
            return
        u = self.state["utterances"][row]
        self.loading = True
        self.edit_uid = u["id"]
        self.speaker_combo.clear()
        self.speaker_combo.addItem("Attribution incertaine", None)
        for key, name in self.state["speakers"].items():
            self.speaker_combo.addItem(name, key)
        self.speaker_combo.setCurrentIndex(max(0, self.speaker_combo.findData(u["speaker_id"])))
        self.utterance_edit.setPlainText(u["text"])
        source = json.loads(u["source_json"])
        self.uncertainty.setText(("Chevauchement possible. Vérifiez les voix à l’écoute. " if source.get("possible_overlap") else "") + ("Attribution automatique à vérifier." if source.get("automatic_attribution", True) else "Attribution corrigée manuellement."))
        self.loading = False

    def schedule_transcript_save(self, *args):
        if not self.loading and self.edit_uid:
            self.transcript_timer.start(600)

    def save_utterance(self, confirm=False):
        if self.loading or not self.sid or not self.edit_uid:
            return
        self.transcript_timer.stop()
        u = next((u for u in self.state["utterances"] if u["id"] == self.edit_uid), None)
        if u and (confirm or u["text"] != self.utterance_edit.toPlainText() or u["speaker_id"] != self.speaker_combo.currentData()):
            self.store.edit_utterance(self.sid, self.edit_uid, self.utterance_edit.toPlainText(), self.speaker_combo.currentData(), confirm=confirm)
            changed = next(x for x in self.store.get(self.sid)["utterances"] if x["id"] == self.edit_uid)
            u.update(changed)
            row = self.state["utterances"].index(u)
            self.transcript_table.item(row, 3).setText(u["text"])
            self.transcript_table.item(row, 1).setText(self.state["speakers"].get(u["speaker_id"], "À attribuer"))
            self.transcript_table.item(row, 2).setText("À vérifier" if u["uncertain"] else ("Automatique" if json.loads(u["source_json"]).get("automatic_attribution", True) else "Confirmée"))
            self.review_status.setText("Transcription modifiée — nouvelle relecture requise")

    def save_speakers(self):
        if not self.sid:
            return
        self.save_utterance()
        for row in range(self.speaker_table.rowCount()):
            key, label = self.speaker_table.item(row, 0).text(), self.speaker_table.item(row, 1).text()
            if self.state["speakers"].get(key) != label:
                self.store.rename_speaker(self.sid, key, label)
                self.state["speakers"][key] = label
                index = self.speaker_combo.findData(key)
                if index >= 0:
                    self.speaker_combo.setItemText(index, label)
                for table_row, u in enumerate(self.state["utterances"]):
                    if u["speaker_id"] == key:
                        self.transcript_table.item(table_row, 1).setText(label)
        self.status.setText("Noms sauvegardés pour cette séance. Vérifiez à nouveau le brouillon après modification des intervenants.")

    def split_utterance(self):
        if not self.edit_uid:
            return
        self.save_utterance()
        u = next(x for x in self.state["utterances"] if x["id"] == self.edit_uid)
        cursor = self.utterance_edit.textCursor()
        cursor.setPosition(0, __import__("PySide6.QtGui", fromlist=["QTextCursor"]).QTextCursor.KeepAnchor)
        position = len(cursor.selectedText().replace("\u2029", "\n"))
        if not 0 < position < len(u["text"]) or u["end_ms"] - u["start_ms"] < 200:
            self.report_error("Placez le curseur entre les deux interventions dans le texte avant de scinder.")
            return
        at, ok = QInputDialog.getDouble(self, "Scinder le passage", "Instant de coupure en secondes dans la séance", (u["start_ms"] + u["end_ms"]) / 2000, (u["start_ms"] + 1) / 1000, (u["end_ms"] - 1) / 1000, 3)
        if ok:
            self.store.split_utterance(self.sid, self.edit_uid, round(at * 1000), position)
            self.load_session()

    def merge_speakers(self):
        row = self.speaker_table.currentRow()
        if row < 0:
            return
        self.save_speakers()
        source = self.speaker_table.item(row, 0).text()
        options = {f"{label} ({key})": key for key, label in self.state["speakers"].items() if key != source}
        if not options:
            self.report_error("Deux voix sont nécessaires pour une fusion.")
            return
        target, ok = QInputDialog.getItem(self, "Fusionner les voix", "Attribuer les passages de cette voix à", list(options), editable=False)
        if ok:
            self.store.merge_speakers(self.sid, source, options[target])
            self.load_session()

    def play_utterance(self, row, col=0):
        u = self.state["utterances"][row]
        source = json.loads(u["source_json"])
        path = Path(source.get("normalized_audio", ""))
        if not path.is_file():
            self.report_error("L’audio préparé est absent. Relancez l’analyse depuis les prises originales.")
            return
        url = QUrl.fromLocalFile(str(path))
        if self.player.source() == url:
            self.player.setPosition(u["start_ms"])
            self.player.play()
        else:
            self.pending_seek = u["start_ms"]
            self.player.setSource(url)

    def media_ready(self, status):
        if self.pending_seek is not None and status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            self.player.setPosition(self.pending_seek)
            self.pending_seek = None
            self.player.play()

    def store_point_fields(self):
        if self.point_index is not None and 0 <= self.point_index < len(self.draft_content["points"]):
            self.draft_content["points"][self.point_index] = {"title": self.point_title.text(), "summary": self.point_text.toPlainText(),
                "sources": [x.strip() for x in self.point_sources.text().split(",") if x.strip()], "vote_id": self.point_vote.currentData()}

    def select_point(self, row):
        if self.loading:
            return
        self.store_point_fields()
        if row < 0:
            self.point_index = None
            return
        self.point_index = row
        p = self.draft_content["points"][row]
        self.point_title.setText(p["title"])
        self.point_text.setPlainText(p["summary"])
        self.point_sources.setText(", ".join(p["sources"]))
        self.point_vote.clear()
        self.point_vote.addItem("Aucun vote associé", None)
        for v in self.store.get(self.sid)["votes"]:
            self.point_vote.addItem(v["title"], v["id"])
        self.point_vote.setCurrentIndex(max(0, self.point_vote.findData(p["vote_id"])))

    def add_point(self):
        if not self.sid:
            return
        self.store_point_fields()
        source = self.state["utterances"][0]["id"] if self.state["utterances"] else ""
        self.draft_content["points"].append({"title": "Point à compléter", "summary": "À compléter", "sources": [source] if source else [], "vote_id": None})
        self.points.addItem("Point à compléter")
        self.points.setCurrentRow(len(self.draft_content["points"]) - 1)

    def save_draft(self):
        if not self.sid or self.loading:
            return
        self.store_point_fields()
        self.draft_content["to_verify"] = [x for x in self.to_verify.toPlainText().splitlines() if x.strip()]
        current = self.store.get(self.sid)["draft"]
        if self.draft_content["points"] and (not current or current["content"] != self.draft_content):
            self.store.save_draft(self.sid, self.draft_content)
            self.review_status.setText("Brouillon sauvegardé — relecture requise")
        for row, p in enumerate(self.draft_content["points"]):
            self.points.item(row).setText(p["title"])

    def add_vote(self, vote=None):
        vote = vote if isinstance(vote, dict) else {"id": str(uuid.uuid4()), "title": "Vote à compléter", "status": "unknown", "source": ""}
        row = self.votes.rowCount()
        self.votes.insertRow(row)
        title = QTableWidgetItem(vote["title"])
        title.setData(Qt.UserRole, vote["id"])
        self.votes.setItem(row, 0, title)
        status = QComboBox()
        status.addItem("À compléter", "unknown")
        status.addItem("Résultat saisi", "entered")
        status.setCurrentIndex(1 if vote["status"] == "entered" else 0)
        self.votes.setCellWidget(row, 1, status)
        for col, key in enumerate(["for_count", "against_count", "abstain_count", "nonparticipating_count"], 2):
            count = QSpinBox()
            count.setRange(-1, 100000)
            count.setSpecialValueText("—")
            count.setValue(vote.get(key) if vote.get(key) is not None else -1)
            self.votes.setCellWidget(row, col, count)
        self.votes.setItem(row, 6, QTableWidgetItem(vote.get("source", "")))

    def remove_vote(self):
        if self.votes.currentRow() >= 0:
            self.votes.removeRow(self.votes.currentRow())

    def manual_fields(self):
        votes = []
        for row in range(self.votes.rowCount()):
            value = {"id": self.votes.item(row, 0).data(Qt.UserRole), "title": self.votes.item(row, 0).text(),
                     "status": self.votes.cellWidget(row, 1).currentData(), "source": self.votes.item(row, 6).text()}
            for col, key in enumerate(["for_count", "against_count", "abstain_count", "nonparticipating_count"], 2):
                n = self.votes.cellWidget(row, col).value()
                value[key] = None if n < 0 else n
            votes.append(value)
        return votes, [x for x in self.decisions.toPlainText().splitlines() if x.strip()]

    def save_manual(self):
        if not self.sid or self.loading:
            return
        votes, decisions = self.manual_fields()
        current = self.store.get(self.sid)
        if votes != current["votes"] or decisions != current["decisions"]:
            self.store.save_manual(self.sid, votes, decisions)
            self.review_status.setText("Décisions ou votes modifiés — relecture requise")

    def flush_edits(self):
        if self.sid and not self.loading:
            self.save_utterance()
            self.save_details()
            self.save_speakers()
            self.save_manual()
            self.save_draft()

    def approve(self):
        try:
            self.flush_edits()
            state = self.store.get(self.sid)
            if not state["draft"]:
                raise ValueError("Préparez et sauvegardez un brouillon avant la relecture.")
            reviewer, ok = QInputDialog.getText(self, "Relecture humaine", "Nom de la personne ayant relu cette révision")
            if not ok or not reviewer.strip():
                return
            if QMessageBox.question(self, "Confirmer la relecture", "Confirmez-vous avoir relu les textes, intervenants, décisions, sources et votes de cette révision ? Cette action autorise son export et ne vaut pas adoption officielle.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            # Explicit confirmation rebases the reviewed edited document to current sources.
            if state["draft"]["context_sha256"] != self.store.context_hash(self.sid):
                self.store.save_draft(self.sid, state["draft"]["content"])
            self.store.approve(self.sid, reviewer)
            self.load_session()
            self.status.setText("Relecture enregistrée pour cette révision. Le document reste un projet non officiel.")
        except Exception as error:
            self.report_error(error)

    def export(self, suffix):
        try:
            self.flush_edits()
            self.store.reviewed_content(self.sid)
            path, _ = QFileDialog.getSaveFileName(self, "Exporter le projet relu", f"NoteTaker-projet.{suffix}", f"{suffix.upper()} (*.{suffix})")
            if path:
                target = Path(path)
                if target.suffix.lower() != "." + suffix:
                    target = target.with_suffix("." + suffix)
                export_session(self.store, self.sid, target)
                self.status.setText(f"Export créé : {target}. Une copie et son instantané sont conservés dans la séance.")
        except Exception as error:
            self.report_error(error)

    def analyse(self):
        if not self.sid or self.recorder or self.task:
            return
        try:
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            return
        if self.store.get(self.sid)["utterances"] and QMessageBox.question(self, "Nouvelle analyse", "Remplacer la transcription courante ? La version précédente et les prises brutes seront conservées.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        sid = self.sid
        self.run_task("analysis", lambda progress, cancel: Pipeline(self.store.root, progress=progress, cancel=cancel).analyse(sid, "cpu"))

    def generate(self):
        if not self.sid or self.recorder or self.task:
            return
        try:
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            return
        if self.store.get(self.sid)["draft"] and QMessageBox.question(self, "Nouveau brouillon", "Créer une nouvelle révision avec Qwen3 ? L’ancienne révision est conservée.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        sid = self.sid
        self.run_task("minutes", lambda progress, cancel: Pipeline(self.store.root, progress=progress, cancel=cancel).generate(sid))

    def run_task(self, kind, function):
        if self.task:
            return
        self.task = Task(function, self)
        self.tabs.setEnabled(False)
        self.history.setEnabled(False)
        self.new_button.setEnabled(False)
        self.archive_button.setEnabled(False)
        self.analyse_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(kind not in {"stop", "import", "preview"})
        self.progress.setRange(0, 0)
        self.progress.show()
        self.task.progress.connect(self.status.setText)
        self.task.succeeded.connect(lambda value: self.task_success(kind, value))
        self.task.failed.connect(lambda error: self.task_failure(kind, error))
        self.task.finished.connect(self.task_finished)
        self.task.start()

    def cancel_task(self):
        if self.task:
            self.task.cancel.set()
            self.status.setText("Arrêt du traitement demandé. Les enregistrements restent conservés.")

    def task_success(self, kind, value):
        if kind == "stop":
            self.store.finish_take(self.recording_take, "interrupted" if value else "ready")
            self.recorder = None
            self.microphone.setEnabled(True)
            self.record_button.setEnabled(True)
        self.load_session()
        if kind == "preview":
            self.player.setSource(QUrl.fromLocalFile(str(value)))
            self.player.play()
        self.status.setText({"stop": "Prise sauvegardée." if not value else f"Prise préservée avec incident : {value}", "import": "Original importé et vérifié. Vous pouvez lancer la transcription.",
            "analysis": "Transcription et voix disponibles. Relisez les textes et attribuez les noms avant de préparer le brouillon.", "minutes": "Brouillon préparé. Vérifiez les extraits, complétez décisions et votes puis enregistrez votre relecture.", "preview": "Lecture de l’audio préparé."}.get(kind, "Action effectuée."))

    def task_failure(self, kind, error):
        if kind == "stop":
            self.store.finish_take(self.recording_take, "interrupted")
            self.recorder = None
        self.load_session()
        self.status.setText("Action interrompue. Les prises sont conservées. " + explain_error(error))

    def task_finished(self):
        old = self.task
        self.task = None
        old.deleteLater()
        self.enable_session(bool(self.sid))
        self.history.setEnabled(True)
        self.new_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.hide()

    def tick(self):
        free = shutil.disk_usage(str(self.store.root)).free / 1024**3
        self.disk_label.setText(f"Espace libre : {free:.1f} Go. Prévoir environ 0,7 Go/heure pour une prise stéréo 48 kHz et de l’espace pour les copies de traitement.")
        if self.recorder:
            seconds = int(self.recorder.seconds)
            self.record_label.setText(f"{'En pause' if self.recorder.paused else 'Enregistrement'} — {seconds // 60:02d}:{seconds % 60:02d} — sauvegarde progressive")
            self.level.setValue(min(100, int(self.recorder.level * 100)))
            if (self.recorder.error or free < 0.1) and not self.task:
                self.stop_recording()
        else:
            self.record_label.setText("Aucune prise en cours")
            self.level.setValue(0)

    def closeEvent(self, event):
        if self.task:
            self.cancel_task()
            self.status.setText("Attendez la fin de l’opération avant de fermer. L’annulation est demandée pour les traitements IA.")
            event.ignore()
            return
        if self.recorder:
            self.stop_recording()
            event.ignore()
            return
        try:
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            event.ignore()
            return
        self.player.stop()
        self.store.close()
        event.accept()

def explain_error(error):
    text = str(error)
    messages = {
        "HUMAN_REVIEW_REQUIRED": "Relisez cette révision puis cliquez sur « J’ai relu cette révision » avant l’export.",
        "DRAFT_STALE": "Les sources ont changé. Vérifiez le brouillon et enregistrez une nouvelle relecture.",
        "VOTE_COUNTS_AND_SOURCE_REQUIRED": "Saisissez les quatre nombres du vote et la source du résultat, ou laissez le vote « À compléter ».",
        "UNKNOWN_VOTE_CANNOT_HAVE_COUNTS": "Un vote « À compléter » doit conserver ses quatre champs numériques vides.",
        "UNKNOWN_STRUCTURED_VOTE": "Le brouillon référence un vote supprimé. Corrigez le vote associé dans l’éditeur.",
        "UNKNOWN_SOURCE_SEGMENT": "Un identifiant source du brouillon est absent de la transcription. Corrigez la référence avant de sauvegarder.",
        "TRANSCRIPT_REQUIRED": "Importez ou enregistrez de l’audio, puis lancez la transcription avant de préparer le brouillon.",
        "STOP_RECORDING_OR_IMPORT_AUDIO_FIRST": "Arrêtez la prise ou importez un enregistrement et cochez les prises à analyser.",
        "NO_RECOVERABLE_AUDIO": "Les prises sélectionnées ne contiennent pas encore d’audio récupérable.",
        "INTEGRITY_FAILED": "Un fichier audio a changé depuis sa sauvegarde. L’original est conservé ; vérifiez la prise et décochez-la si nécessaire.",
        "DIARIZATION_FAILED_TRANSCRIPT_PRESERVED": "La différenciation des voix a échoué. La transcription est conservée ; vous pouvez la corriger ou relancer l’analyse.",
        "JOB_CANCELLED": "Traitement annulé. Les prises et résultats déjà enregistrés sont conservés.",
        "SESSION_CHANGED_DURING": "La séance a été modifiée pendant le traitement. Les fichiers sont conservés ; relancez l’opération après sauvegarde.",
        "AGENDA_TOO_LARGE": "Raccourcissez l’ordre du jour à vingt intitulés concis pour préparer ce brouillon.",
        "ALL_ENGINE_ATTEMPTS_FAILED": "Le moteur n’a pas pu traiter cet enregistrement. Les prises sont conservées. Vérifiez les modèles locaux et relancez l’analyse.",
        "WORKER_EXIT_": "Le moteur s’est arrêté avec une erreur. Les prises sont conservées ; vous pouvez relancer le traitement.",
        "SESSION_TITLE_REQUIRED": "Donnez un titre à cette séance avant de la sauvegarder.",
        "SPEAKER_LABEL_REQUIRED": "Saisissez un nom ou un libellé pour chaque intervenant.",
    }
    for key, message in messages.items():
        if key in text:
            return message
    return text

STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #233247; background: #f5f7fb; }
QWidget#sidebar { background: #e9eef7; border-right: 1px solid #d8e0ed; }
QLabel#brand { font-size: 27px; font-weight: 700; padding: 16px 6px; color: #183760; }
QLabel#heading { font-size: 24px; font-weight: 650; padding-bottom: 12px; }
QLabel#warning { background: #fff3d7; color: #6a4b12; padding: 12px; border-radius: 8px; }
QPushButton { padding: 9px 13px; background: #ffffff; border: 1px solid #cbd5e3; border-radius: 6px; }
QPushButton:hover { background: #e5edf9; }
QPushButton:disabled { color: #8a95a5; background: #edf0f5; }
QPushButton[primary=true] { background: #225bb1; color: white; border: none; }
QPushButton[primary=true]:hover { background: #194b94; }
QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox { background: white; padding: 7px; border: 1px solid #cbd5e3; border-radius: 5px; }
QListWidget, QTableWidget { background: white; border: 1px solid #d4deeb; border-radius: 6px; }
QListWidget::item { padding: 12px 8px; border-bottom: 1px solid #e8edf5; }
QListWidget::item:selected { background: #d8e7ff; color: #153b70; }
QTabWidget::pane { border: 1px solid #d4deeb; border-radius: 6px; }
QTabBar::tab { padding: 12px; margin-right: 3px; }
QTabBar::tab:selected { color: #225bb1; background: white; border-bottom: 3px solid #225bb1; }
QHeaderView::section { padding: 8px; background: #edf2fa; border: none; }
QProgressBar { border: 1px solid #d2ddea; border-radius: 4px; text-align: center; min-height: 16px; }
QProgressBar::chunk { background: #3676c8; }
"""
