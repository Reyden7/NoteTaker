import json
import shutil
import threading
import uuid
import time
from pathlib import Path
from notetaker.ui.playback import LocalPlayback
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QDate
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QTabWidget, QSplitter, QComboBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QDateEdit, QMessageBox, QFileDialog, QInputDialog, QSpinBox, QDialog, QDialogButtonBox, QScrollArea, QCheckBox)
from notetaker.domain.minutes import content_digest
from notetaker.infrastructure.paths import session_directory
from notetaker.services.storage import SessionStore
from notetaker.services.recording import MicrophoneRecorder, input_devices, recover_capture
from notetaker.services.audio import import_audio, prepare_audio
from notetaker.services.pipeline import Pipeline
from notetaker.services.session_export import export_session
from notetaker.services.directory import DirectoryService, person_name
from notetaker.ui.directory import DirectoryDialog, ParticipantsPage
from notetaker.services.evidence import DraftEvidenceError, draft_issues, propose_attribution_refresh
from notetaker.ui.evidence import EvidenceDiagnostics, ClaimEditor, SourcePicker,NarrativeSources
from notetaker.domain.summary import PROFILES,lexicon_from_text,lexicon_text,manual_narrative
from notetaker.ui.information_registry import RegistryPage

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
    def __init__(self, data_root, *, experimental_direct=False):
        super().__init__()
        self.experimental_direct = experimental_direct
        if experimental_direct:
            from notetaker.domain.direct_summary import test_workspace
            test_workspace(data_root)
        self.store = SessionStore(Path(data_root))
        self.voice_vault_warning=None
        if (Path(data_root)/'voice-vault.sqlite3').exists():
            try:
                from notetaker.services.voice_profiles import VoiceProfiles
                VoiceProfiles(data_root).purge_expired()
            except Exception:
                self.voice_vault_warning='Le coffre vocal est inaccessible. Le compte rendu reste disponible sans identification ; vérifiez les droits du compte Windows.'
        interrupted = self.store.recover()
        self.sid = None
        self.state = None
        self.task = None
        self.recorder = None
        self.recording_take = None
        self.edit_uid = None
        self.point_index = None
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
        elif self.voice_vault_warning:
            self.status.setText(self.voice_vault_warning)

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
        self.directory_button = button('Annuaire des intervenants', self.open_directory)
        side.addWidget(self.directory_button)
        self.audio_settings_button = button('Paramètres audio — CPU / GPU', self.audio_settings)
        side.addWidget(self.audio_settings_button)
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
        side.addWidget(paragraph("Version de travail 0.2.5\nSynthèse expérimentale en qualification"))
        outer.addWidget(sidebar)
        body = QVBoxLayout()
        body.setContentsMargins(24, 20, 24, 16)
        self.heading = QLabel("Préparez votre prochaine séance")
        self.heading.setObjectName("heading")
        body.addWidget(self.heading)
        actions = QHBoxLayout()
        self.analyse_button = button("1. Transcrire et distinguer les voix", self.analyse, True)
        self.generate_button = button("2. Registre / rédaction", self.generate)
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
        self.participants_page = ParticipantsPage(self.store, self)
        self.participants_page.saved.connect(self.participants_saved)
        self.tabs.addTab(self.participants_page, 'Participants')
        self.registry_page=RegistryPage(self.store,self.prepare_information_registry,self.write_from_registry,self.play_source,self.report_error,
            before_change=self.flush_edits,parent=self,play_snapshot=self.play_registry_snapshot,verify=self.verify_registry_information)
        self.registry_page.changed.connect(self.load_session)
        self.tabs.addTab(self.registry_page,'Registre des informations')
        if self.experimental_direct:
            from notetaker.ui.direct_summary import DirectSummaryPage
            self.direct_page = DirectSummaryPage(self.store, self.generate_direct,
                lambda: self.tabs.setCurrentIndex(3), self.play_registry_snapshot, self,
                resume=self.generate_direct, reuse=self.reuse_direct)
            self.tabs.addTab(self.direct_page, 'Laboratoire de synthèse')
        from notetaker.ui.simple_report import SimpleReportPage
        self.simple_page=SimpleReportPage(self)
        self.advanced_mode=QCheckBox('Mode avancé — transcription, registre, citations et validation')
        body.addWidget(self.advanced_mode)
        body.addWidget(self.simple_page,1)
        body.addWidget(self.tabs, 1)
        self.advanced_mode.toggled.connect(self.toggle_advanced)
        self.toggle_advanced(False)
        self.status = paragraph("Créez une séance ou rouvrez-la dans l’historique. Tous les traitements se font sur cet ordinateur.")
        body.addWidget(self.status)
        self.engine_status = paragraph('Moteur audio : ' + self.audio_mode_label())
        body.addWidget(self.engine_status)
        self.cpu_retry = button('Relancer explicitement avec Small + sherpa sur CPU', lambda: self.analyse('cpu'))
        self.cpu_retry.hide()
        body.addWidget(self.cpu_retry)
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
        self.participants_edit.setPlaceholderText("Notes conservées des séances existantes. Utilisez l’onglet Participants pour les présences structurées.")
        self.agenda_edit.setPlaceholderText("Un point de l’ordre du jour par ligne")
        self.notes_edit.setPlaceholderText("Notes de l’opérateur")
        for label, field in [("Notes de présence (texte libre)", self.participants_edit), ("Ordre du jour", self.agenda_edit), ("Notes", self.notes_edit)]:
            field.setMaximumHeight(110)
            form.addRow(label, field)
        layout.addLayout(form)
        layout.addWidget(button("Enregistrer les informations", self.save_details, True))
        layout.addWidget(button('Lexique local de la séance…',self.edit_lexicon))
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
        play.addWidget(button("Arrêter la lecture", lambda: self.playback.stop()))
        layout.addLayout(play)
        self.playback_label = QLabel("Lecture locale")
        layout.addWidget(self.playback_label)
        self.playback = LocalPlayback(self)
        self.player = self.playback.player
        self.audio_output = self.playback.output
        self.playback.positionChanged.connect(lambda pos: self.playback_label.setText(f"Lecture : {pos // 60000:02d}:{pos // 1000 % 60:02d}"))
        self.playback.message.connect(self.playback_message)
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
        tools = QHBoxLayout()
        tools.addWidget(button("Diagnostic des intervenants…", self.show_speaker_diagnostics))
        tools.addWidget(button("Restaurer une transcription précédente…", self.restore_analysis))
        tools.addWidget(button('Écouter le passage', self.play_selected))
        tools.addWidget(button('Regrouper la sélection…', self.merge_selected_segments))
        layout.addLayout(tools)
        splitter = QSplitter()
        self.transcript_table = QTableWidget(0, 4)
        self.transcript_table.setHorizontalHeaderLabels(["Début", "Intervenant", "Attribution", "Texte"])
        self.transcript_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for col,width in [(0,85),(1,170),(2,165)]:self.transcript_table.setColumnWidth(col,width)
        self.transcript_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.transcript_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.transcript_table.setWordWrap(True)
        self.transcript_table.verticalHeader().setDefaultSectionSize(58)
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
        self.utterance_edit.setMinimumHeight(140)
        self.utterance_edit.textChanged.connect(self.schedule_transcript_save)
        self.speaker_combo.currentIndexChanged.connect(self.schedule_transcript_save)
        edit.addWidget(self.utterance_edit, 1)
        edit.addWidget(button("Enregistrer et confirmer l’attribution", lambda: self.save_utterance(confirm=True), True))
        edit.addWidget(button('Confirmer cette voix sur la sélection', self.confirm_selected_voice))
        edit.addWidget(button("Scinder le passage au curseur…", self.split_utterance))
        edit.addWidget(paragraph('Attribution manuelle depuis les participants de la séance'))
        self.person_combo = QComboBox()
        edit.addWidget(self.person_combo)
        self.person_scope = QComboBox()
        self.person_scope.addItems(['Ce passage uniquement', 'Toutes les interventions de cette voix', 'Interventions sélectionnées'])
        edit.addWidget(self.person_scope)
        self.assign_person_button = button('Attribuer à cette personne', self.assign_directory_person)
        edit.addWidget(self.assign_person_button)
        self.speaker_table = QTableWidget(0, 2)
        self.speaker_table.setMinimumHeight(120)
        self.speaker_table.setHorizontalHeaderLabels(["Voix", "Nom attribué"])
        self.speaker_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        edit.addWidget(self.speaker_table)
        edit.addWidget(button("Enregistrer les noms", self.save_speakers))
        edit.addWidget(button("Fusionner la voix sélectionnée…", self.merge_speakers))
        editor_scroll=QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setWidget(editor)
        splitter.addWidget(editor_scroll)
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
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Document à préparer"))
        self.document_mode = QComboBox()
        self.document_mode.addItem("Compte rendu synthétique", "summary")
        self.document_mode.addItem("Transcription intégrale", "transcript")
        self.document_mode.addItem("Procès-verbal municipal — relecture par le secrétaire", "municipal")
        mode_row.addWidget(self.document_mode, 1)
        self.summary_length=QComboBox()
        for key,profile in PROFILES.items():self.summary_length.addItem(profile['label'],key)
        self.summary_length.setCurrentIndex(1)
        self.summary_length.setToolTip('Longueur de rédaction par sujet ; la fidélité reste prioritaire. Le mode transcription reste intégral.')
        self.document_mode.currentIndexChanged.connect(lambda:self.summary_length.setEnabled(self.document_mode.currentData()!='transcript'))
        mode_row.addWidget(QLabel('Longueur'))
        mode_row.addWidget(self.summary_length)
        mode_row.addWidget(button("Préparer ce document", self.generate, True))
        layout.addLayout(mode_row)
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
        panel.addWidget(button("Consulter les extraits sources…", self.show_point_sources))
        panel.addWidget(button('Passages écartés ou incertains…',self.show_unreliable_sources))
        evidence_actions=QHBoxLayout()
        evidence_actions.addWidget(button('Contrôler les références…', self.check_draft_references))
        evidence_actions.addWidget(button('Corriger une affirmation…', self.edit_selected_claim))
        panel.addLayout(evidence_actions)
        panel.addWidget(button('Actualiser les attributions depuis les sources…',self.refresh_claim_attributions))
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
        controls.addWidget(button("Anciennes révisions…", self.restore_draft))
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
        if isinstance(error,DraftEvidenceError):
            self.show_evidence_diagnostics(error.issues)
            return
        message = explain_error(error)
        self.status.setText(message)
        QMessageBox.warning(self, "Action non effectuée", message)

    def enable_session(self, enabled):
        self.simple_page.generate.setEnabled(enabled and not self.task)
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
        if self.registry_page.editor_changed():
            self.status.setText('Enregistrez la correction du registre ou annulez la saisie avant de changer de séance.');return
        title, ok = QInputDialog.getText(self, "Nouvelle séance", "Titre", text="Conseil municipal")
        if ok and title.strip():
            self.flush_edits()
            self.sid = self.store.create(title, {"date": QDate.currentDate().toString(Qt.ISODate), "agenda": []})
            self.reload_history()
            self.load_session()

    def select_session(self, item, previous=None):
        if self.loading or not item:
            return
        if self.registry_page.editor_changed():
            self.status.setText('Enregistrez la correction du registre ou annulez la saisie avant de changer de séance.')
            self.reload_history();return
        try:
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            self.reload_history()
            return
        self.playback.stop()
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
        self.participants_page.load(self.sid)
        self.refresh_person_choices()
        self.registry_page.load(self.sid)
        if self.experimental_direct:
            self.direct_page.load(self.sid)
        self.agenda_edit.setPlainText("\n".join(m.get("agenda", [])))
        self.notes_edit.setPlainText(m.get("notes", ""))
        self.summary_length.setCurrentIndex(max(0,self.summary_length.findData(m.get('summary_length','standard'))))
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
        self.document_mode.setCurrentIndex(max(0, self.document_mode.findData(self.draft_content.get("document_mode", "summary"))))
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
        review_current=bool(review and s['draft']['context_sha256']==self.store.context_hash(self.sid))
        review_text=('relecture enregistrée par '+review['reviewer'] if review_current else
            'ancienne relecture conservée — nouvelle relecture requise' if review else 'relecture requise')
        self.review_status.setText(f"Révision {s['draft']['revision']} — "+review_text if s['draft'] else 'Aucun brouillon généré')
        self.loading = False
        self.simple_page.load(s)
        self.enable_session(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        if self.draft_content["points"]:
            self.points.setCurrentRow(0)

    def metadata(self):
        values={**(self.state['metadata'] if self.state else {}), "municipality": self.commune_edit.text(), "location": self.location_edit.text(), "date": self.date_edit.date().toString(Qt.ISODate),
                "participants": self.participants_edit.toPlainText(), "agenda": [x.strip() for x in self.agenda_edit.toPlainText().splitlines() if x.strip()], "notes": self.notes_edit.toPlainText()}
        if self.summary_length.currentData()!='standard' or 'summary_length' in values:
            values['summary_length']=self.summary_length.currentData()
        return values

    def save_details(self):
        if not self.sid or self.loading:
            return
        current = self.store.get(self.sid)
        if current["title"] != self.title_edit.text().strip() or current["metadata"] != self.metadata():
            self.store.save_details(self.sid, self.title_edit.text(), self.metadata())
            self.heading.setText(self.title_edit.text())
            self.reload_history()
            self.status.setText("Informations sauvegardées. Toute modification impose une nouvelle relecture du brouillon.")

    def edit_lexicon(self):
        if not self.sid:return
        self.flush_edits()
        dialog=QDialog(self);dialog.setWindowTitle('Lexique local de la séance');dialog.resize(780,520)
        layout=QVBoxLayout(dialog)
        layout.addWidget(paragraph('Une forme retenue par ligne, éventuellement suivie de | puis des variantes séparées par ;. Ce lexique corrige la graphie, sans identifier une voix ni modifier les citations sources.'))
        editor=QTextEdit(lexicon_text(self.store.get(self.sid)['metadata'].get('lexicon',[])));layout.addWidget(editor)
        feedback=paragraph('Exemple : Médiathèque Simone Veil | médiathèque Simone Veille');layout.addWidget(feedback)
        def save():
            try:
                entries=lexicon_from_text(editor.toPlainText())
                state=self.store.get(self.sid)
                self.store.save_details(self.sid,state['title'],{**state['metadata'],'lexicon':entries})
                self.state=self.store.get(self.sid);dialog.accept()
                self.review_status.setText('Lexique modifié — régénérez et relisez le document si nécessaire.')
            except ValueError as error:feedback.setText(str(error))
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(save);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        dialog.exec()

    def archive_session(self):
        if self.sid:
            self.flush_edits()
            self.store.archive(self.sid, not self.store.get(self.sid)["archived"])
            self.reload_history()

    def open_directory(self):
        if self.task or self.recorder:
            self.status.setText('Terminez la capture ou le traitement avant de modifier l’annuaire.')
            return
        self.flush_edits()
        self.playback.stop()
        DirectoryDialog(self.store, self).exec()
        if self.sid:
            self.refresh_person_choices()

    def toggle_advanced(self, enabled):
        if hasattr(self,'simple_page') and self.simple_page.dirty:
            self.simple_page.save()
        self.tabs.setVisible(enabled)
        self.simple_page.setVisible(not enabled)
        self.analyse_button.setVisible(enabled)
        self.generate_button.setVisible(enabled)
        if not enabled and self.sid and hasattr(self,'draft_content'):
            self.flush_edits()
            self.simple_page.load(self.store.get(self.sid))

    def open_review(self):
        self.simple_page.save()
        self.advanced_mode.setChecked(True)
        self.tabs.setCurrentIndex(3)

    def generate_automatic(self):
        if not self.sid or self.task or self.recorder:return
        self.flush_edits()
        sid=self.sid
        self.run_task('automatic',lambda progress,cancel:Pipeline(self.store.root,progress=progress,cancel=cancel).automatic_report(sid))

    def export_working(self, extension):
        if not self.sid:return
        try:
            self.flush_edits()
            path,_=QFileDialog.getSaveFileName(self,'Exporter un brouillon NON OFFICIEL','Compte-rendu-BROUILLON.'+extension,extension.upper()+' (*.'+extension+')')
            if path:
                from notetaker.services.working_export import export_working_copy
                export_working_copy(self.store,self.sid,Path(path))
                self.status.setText('Brouillon NON RELU exporté ; aucune validation officielle créée.')
        except Exception as error:self.report_error(error)

    def show_automatic_diagnostics(self):
        if not self.sid:return
        jobs=[j for j in self.store.jobs(self.sid) if j['kind']=='automatic-report']
        if not jobs:
            self.status.setText('Aucun dossier de génération automatique pour cette séance.');return
        # SessionStore.jobs is newest first. Prefer the last successful report;
        # a failed retry must not make an older, unrelated inventory look current.
        completed=[j for j in jobs if j['status']=='completed']
        directory=session_directory(self.store.root,self.sid)/'jobs'/(completed or jobs)[0]['id']
        path=directory/'automatic-inventory.json'
        dialog=QDialog(self);dialog.setWindowTitle('Génération — formulations, refus et sources non reprises');dialog.resize(850,650)
        layout=QVBoxLayout(dialog);text=QTextEdit();text.setReadOnly(True)
        report=directory/'verification-report.md'
        if report.exists():text.setPlainText(report.read_text(encoding='utf-8'))
        elif path.exists():text.setPlainText(json.dumps(json.loads(path.read_text(encoding='utf-8')),ensure_ascii=False,indent=2))
        else:text.setPlainText('Le traitement est interrompu ou n’a pas encore produit son inventaire. Les sources et anciens brouillons sont conservés.\nDossier : '+str(directory))
        layout.addWidget(text);close=QDialogButtonBox(QDialogButtonBox.Close);close.rejected.connect(dialog.reject);layout.addWidget(close);dialog.exec()

    def refresh_person_choices(self):
        selected = self.person_combo.currentData()
        self.person_combo.clear()
        self.person_combo.addItem('Choisir un participant…', None)
        if self.sid:
            for p in DirectoryService(self.store).participants(self.sid):
                civil = p['snapshot']
                title = ' · '.join(filter(None, [person_name(civil), civil.get('position'), civil.get('municipality')]))
                self.person_combo.addItem(title, p['person_id'])
        self.person_combo.setCurrentIndex(max(0, self.person_combo.findData(selected)))
        self.assign_person_button.setEnabled(self.person_combo.count() > 1)

    def participants_saved(self):
        self.state = self.store.get(self.sid)
        self.refresh_person_choices()
        self.review_status.setText('Participants modifiés — nouvelle relecture requise')

    def assign_directory_person(self):
        pid, uid = self.person_combo.currentData(), self.edit_uid
        if not pid or not uid:
            self.status.setText('Sélectionnez un passage et une personne ajoutée dans l’onglet Participants.')
            return
        self.flush_edits()
        state = self.store.get(self.sid)
        utterance = next(u for u in state['utterances'] if u['id'] == uid)
        ids = [uid]
        if self.person_scope.currentIndex() == 2:
            ids=self.selected_utterance_ids()
        if self.person_scope.currentIndex() == 1:
            if utterance['speaker_id'] is None:
                self.status.setText('Les passages non attribués peuvent appartenir à plusieurs voix. Attribuez-les séparément.')
                return
            ids = [u['id'] for u in state['utterances'] if u['speaker_id'] == utterance['speaker_id']]
            if QMessageBox.question(self, 'Attribution de la voix', f'Attribuer manuellement ces {len(ids)} interventions à la personne sélectionnée ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        DirectoryService(self.store).assign_person(self.sid, ids, pid)
        self.load_session()
        row = next(i for i, u in enumerate(self.state['utterances']) if u['id'] == uid)
        self.transcript_table.selectRow(row)
        self.status.setText('Attribution manuelle enregistrée. Les autres passages et la fiche permanente sont conservés ; le brouillon doit être relu.')

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
        self.playback.stop()
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
        if self.recorder or self.task:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Importer un enregistrement", "", "Audio (*.wav *.mp3 *.m4a)")
        if not path:
            return
        if not self.sid:
            self.sid=self.store.create(Path(path).stem,{'date':QDate.currentDate().toString(Qt.ISODate),'agenda':[]})
            self.reload_history();self.load_session()
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
        self.playback.toggle()

    def playback_message(self, message):
        self.status.setText(message)
        self.playback_label.setText(message)

    def populate_transcript(self):
        self.transcript_table.clearSelection()
        self.transcript_table.setCurrentCell(-1, -1)
        self.transcript_table.setRowCount(len(self.state["utterances"]))
        for row, u in enumerate(self.state["utterances"]):
            automatic = json.loads(u["source_json"]).get("automatic_attribution", True)
            status='Voix inconnue' if not u['speaker_id'] else ('Incertaine' if u['uncertain'] else ('Automatique à vérifier' if automatic else 'Confirmée manuellement'))
            texts = [f"{u['start_ms'] // 60000:02d}:{u['start_ms'] // 1000 % 60:02d}", self.state["speakers"].get(u["speaker_id"], "Voix inconnue"), status, u["text"]]
            for col, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if u["uncertain"]:
                    item.setBackground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#fff3d6"))
                self.transcript_table.setItem(row, col, item)
        self.speaker_table.setRowCount(len(self.state["speakers"]))
        for row, (key, label) in enumerate(self.state["speakers"].items()):
            item = QTableWidgetItem(f'Voix {row+1}')
            item.setData(Qt.UserRole,key)
            item.setToolTip('Identifiant interne : '+key)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.speaker_table.setItem(row, 0, item)
            self.speaker_table.setItem(row, 1, QTableWidgetItem(label))
        self.utterance_edit.clear()
        self.speaker_combo.clear()
        self.uncertainty.setText('Sélectionnez un passage')

    def filter_transcript(self, text):
        for row in range(self.transcript_table.rowCount()):
            self.transcript_table.setRowHidden(row, text.casefold() not in self.transcript_table.item(row, 3).text().casefold())

    def show_private_text(self, title, text):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(860, 600)
        layout = QVBoxLayout(dialog)
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        layout.addWidget(editor)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()

    def show_speaker_diagnostics(self):
        if not self.sid:
            return
        self.flush_edits()
        stats = self.store.speaker_diagnostics(self.sid)
        rows = [f"{len(self.store.get(self.sid)['speakers'])} identifiants ; les durées attribuées ne sont pas une référence humaine.\n"]
        for key, item in stats.items():
            rows.append(f"{item['name']} ({key}) : {item['seconds']:.1f} s ; {item['segments']} passages ; {item['short_segments']} < 1 s ; {item['uncertain_segments']} incertains")
        self.show_private_text("Diagnostic de la séance", "\n".join(rows))

    def restore_analysis(self):
        if not self.sid or self.task or self.recorder:
            return
        self.flush_edits()
        versions = self.store.analysis_history(self.sid)
        versions = [v for v in versions if json.loads(v["content_json"])["utterances"]]
        if not versions:
            self.status.setText("Aucune transcription antérieure à restaurer.")
            return
        options = [f"Version {v['id']} — {v['created_at']} — {len(json.loads(v['content_json'])['utterances'])} passages" for v in versions]
        choice, ok = QInputDialog.getItem(self, "Restaurer une transcription", "La version active sera elle aussi conservée ; une nouvelle relecture sera requise.", options, 0, False)
        if ok:
            self.store.restore_analysis(self.sid, versions[options.index(choice)]["id"])
            self.load_session()

    def show_unreliable_sources(self):
        if not self.sid:return
        entries=self.draft_content.get('generation_diagnostics',{}).get('unreliable_passages',[])
        if not entries:
            self.status.setText('Ce brouillon ne comporte pas de liste détaillée de passages incertains. Consultez les alertes et la transcription complète.');return
        state=self.store.get(self.sid);by_id={u['id']:u for u in state['utterances']}
        dialog=QDialog(self);dialog.setWindowTitle('Passages écartés ou incertains');dialog.resize(1050,700)
        layout=QVBoxLayout(dialog);layout.addWidget(paragraph('Ces passages n’ont pas permis une rédaction sûre ou portent une attribution/chronologie incertaine. Les corriger ne valide pas automatiquement le compte rendu. La liste décrit l’état lors de sa génération.'))
        sources=QTableWidget(len(entries),3);sources.setHorizontalHeaderLabels(['Horodatage','Cause à vérifier','Texte actuel'])
        sources.setEditTriggers(QAbstractItemView.NoEditTriggers);sources.setSelectionBehavior(QAbstractItemView.SelectRows)
        sources.setSelectionMode(QAbstractItemView.SingleSelection);sources.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        labels={'information_rejected':'Rédaction ou citation à vérifier avant reprise','voice_or_timing_uncertain':'Voix, chevauchement ou horaire incertain','note_not_selected':'Note non reprise dans le paragraphe choisi'}
        for i,entry in enumerate(entries):
            u=by_id.get(entry['source_id'])
            for j,text in enumerate([f"{entry['start_ms']//60000:02d}:{entry['start_ms']//1000%60:02d}",
                ' ; '.join(labels.get(r,r) for r in entry['reasons']),u['text'] if u else 'Source ancienne absente de la transcription actuelle']):
                item=QTableWidgetItem(text);item.setToolTip(text);item.setData(Qt.UserRole,entry['source_id']);sources.setItem(i,j,item)
        layout.addWidget(sources,1)
        full=QTextEdit();full.setReadOnly(True);full.setMaximumHeight(180);layout.addWidget(full)
        def selected():
            row=sources.currentRow()
            if row>=0:full.setPlainText(sources.item(row,2).text())
        def listen():
            row=sources.currentRow()
            if row>=0:self.play_source(sources.item(row,0).data(Qt.UserRole))
        sources.itemSelectionChanged.connect(selected);sources.cellDoubleClicked.connect(lambda *a:listen())
        actions=QHBoxLayout();actions.addWidget(button('Écouter ce passage',listen));actions.addWidget(button('Arrêter l’écoute',self.playback.stop));actions.addWidget(button('Fermer',dialog.close));layout.addLayout(actions)
        dialog.finished.connect(lambda *a:self.playback.stop())
        sources.selectRow(0);selected();dialog.exec()

    def show_point_sources(self):
        if not self.sid or self.point_index is None:
            return
        self.store_point_fields()
        point = self.draft_content["points"][self.point_index]
        state = self.store.get(self.sid)
        if point.get('narrative'):
            NarrativeSources(point,state,self.play_source,self,stop=self.playback.stop).exec()
            return
        sources = {u["id"]: u for u in state["utterances"]}
        rows = ["Références internes. Contrôlez le sens complet et l'attribution à l'écoute.\n"]
        for claim in point.get("claims", []):
            status = 'contrôle IA — relecture humaine requise' if claim.get('machine_verdict') == 'supported_not_human_verified' else 'à vérifier'
            rows += [f"Reformulation ({status}) : {claim['text']}"]
            rows += [f"Extrait cité : {e['quote']}" for e in claim["evidence"]]
        for key in point["sources"]:
            u = sources.get(key)
            if u:
                rows += [f"\n{u['start_ms'] / 1000:.2f}–{u['end_ms'] / 1000:.2f} s — {state['speakers'].get(u['speaker_id'], 'Non attribué')} [{key}]", u["text"]]
        self.show_private_text("Sources du point sélectionné", "\n".join(rows))

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
        if source.get('simultaneous_turns'):
            voices = sorted({s for turn in source['simultaneous_turns'] for s in turn['speakers']})
            self.uncertainty.setText(self.uncertainty.text() + ' Voix simultanées détectées : ' +
                ', '.join(self.state['speakers'].get(s, 'Voix non attribuée') for s in voices) + '. Le texte commun reste à attribuer à l’écoute.')
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
            key, label = self.speaker_table.item(row, 0).data(Qt.UserRole), self.speaker_table.item(row, 1).text()
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
        self.flush_edits()
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
        self.flush_edits()
        source = self.speaker_table.item(row, 0).data(Qt.UserRole)
        options = {f"{label} — voix {i+1}": key for i,(key,label) in enumerate(self.state['speakers'].items()) if key != source}
        if not options:
            self.report_error("Deux voix sont nécessaires pour une fusion.")
            return
        target, ok = QInputDialog.getItem(self, "Fusionner les voix", "Attribuer les passages de cette voix à", list(options), editable=False)
        if ok:
            self.store.merge_speakers(self.sid, source, options[target])
            self.load_session()

    def play_utterance(self, row, col=0):
        self.play_registry_snapshot(self.state['utterances'][row])

    def play_registry_snapshot(self,u):
        try:
            source = json.loads(u["source_json"])
            path = Path(source.get("normalized_audio", ""))
            if not path.is_file():
                raise ValueError('L’audio préparé associé à cette source est absent. Vérifiez son emplacement ou restaurez la copie audio conservée.')
            self.playback.play(path, u['start_ms'], u['end_ms'])
        except (ValueError, KeyError, TypeError) as error:
            self.playback.stop()
            self.playback_message('Lecture impossible : ' + str(error))

    def store_point_fields(self):
        if self.point_index is not None and 0 <= self.point_index < len(self.draft_content["points"]):
            old = self.draft_content["points"][self.point_index]
            changed = old["summary"] != self.point_text.toPlainText() or old["sources"] != [x.strip() for x in self.point_sources.text().split(",") if x.strip()]
            self.draft_content["points"][self.point_index] = {**old, "title": self.point_title.text(), "summary": self.point_text.toPlainText(),
                "sources": [x.strip() for x in self.point_sources.text().split(",") if x.strip()], "vote_id": self.point_vote.currentData()}
            if 'narrative' in old and old['summary']!=self.point_text.toPlainText():
                manual_narrative(self.draft_content['points'][self.point_index],self.point_text.toPlainText())
            # Editing prose must never silently discard its checked assertions.

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
        if (self.draft_content['points'] or current) and (not current or current["content"] != self.draft_content):
            self.store.save_draft(self.sid, self.draft_content,allow_invalid=True)
            issues=draft_issues(self.draft_content,self.store.get(self.sid))
            self.review_status.setText(f'Brouillon de travail sauvegardé — {len(issues)} incohérence(s) à corriger' if issues else 'Brouillon sauvegardé — relecture requise')
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
            self.simple_page.save()
            self.participants_page.save_if_dirty()
            self.save_utterance()
            self.save_details()
            self.save_speakers()
            self.save_manual()
            self.save_draft()

    def selected_utterance_ids(self):
        return [self.state['utterances'][i]['id'] for i in sorted({index.row() for index in self.transcript_table.selectionModel().selectedRows()})]

    def confirm_selected_voice(self):
        ids=self.selected_utterance_ids();speaker=self.speaker_combo.currentData()
        if not ids:return
        self.save_utterance()
        for u in self.store.get(self.sid)['utterances']:
            if u['id'] in ids:self.store.edit_utterance(self.sid,u['id'],u['text'],speaker,confirm=True)
        self.load_session()
        self.status.setText(f'{len(ids)} attribution(s) corrigée(s) manuellement. Vérifiez le brouillon avant sa relecture.')

    def merge_selected_segments(self):
        ids=self.selected_utterance_ids()
        if len(ids)<2:
            self.status.setText('Sélectionnez plusieurs interventions consécutives avec Ctrl ou Maj.');return
        self.flush_edits()
        if QMessageBox.question(self,'Regrouper les interventions','Regrouper ces passages de la même voix ? Les horaires et sources seront conservés dans l’historique ; le brouillon sera à relire.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        try:
            uid=self.store.merge_utterances(self.sid,ids);self.load_session()
            row=next(i for i,u in enumerate(self.state['utterances']) if u['id']==uid)
            self.transcript_table.selectRow(row)
        except Exception as error:self.report_error(error)

    def play_selected(self):
        row=self.transcript_table.currentRow()
        if row>=0:self.play_utterance(row)

    def play_source(self,uid):
        row=next((i for i,u in enumerate(self.state['utterances']) if u['id']==uid),None)
        if row is None:
            self.status.setText('Cette source n’existe plus. Consultez l’historique ou rattachez l’affirmation à un passage actuel.');return
        self.play_utterance(row)

    def focus_issue_point(self,index):
        self.tabs.setCurrentIndex(3)
        if 0<=index<self.points.count():self.points.setCurrentRow(index)

    def show_evidence_diagnostics(self,issues):
        self.status.setText(f'{len(issues)} incohérence(s) de sources empêchent la relecture. Corrigez les éléments indiqués.')
        previous=getattr(self,'evidence_dialog',None)
        if previous:previous.close()
        self.evidence_dialog=EvidenceDiagnostics(issues,self.store.get(self.sid),self.edit_claim_at,self.focus_issue_point,self.play_source,self)
        self.evidence_dialog.show()

    def check_draft_references(self):
        self.save_draft()
        issues=draft_issues(self.draft_content,self.store.get(self.sid))
        if issues:self.show_evidence_diagnostics(issues)
        else:self.status.setText('Les références sont cohérentes. La fidélité du texte et les attributions restent à relire avant export.')

    def edit_selected_claim(self):
        self.store_point_fields()
        pi=self.points.currentRow()
        if pi<0:return
        claims=self.draft_content['points'][pi].get('claims',[])
        if not claims:self.edit_claim_at(pi,None);return
        choices=[f"{i+1}. {c.get('text','Affirmation incomplète')[:150]}" for i,c in enumerate(claims)]
        chosen,ok=QInputDialog.getItem(self,'Affirmation à corriger','Choisir une affirmation',choices,0,False)
        if ok:self.edit_claim_at(pi,choices.index(chosen))

    def edit_claim_at(self,pi,ci):
        self.save_draft()
        if not 0<=pi<len(self.draft_content['points']):return
        point=self.draft_content['points'][pi]
        if ci is None:
            self.focus_issue_point(pi)
            picker=SourcePicker(self.store.get(self.sid),self)
            if picker.exec()==QDialog.Accepted:
                if point.get('claims'):
                    self.status.setText('Corrigez les citations de chaque affirmation avec « Corriger une affirmation ».');return
                self.point_sources.setText(picker.chosen['id']);self.save_draft()
            return
        dialog=ClaimEditor(point,ci,self.store.get(self.sid),self)
        if dialog.exec()==QDialog.Accepted:
            if dialog.result_point is None:self.draft_content['points'].pop(pi)
            else:self.draft_content['points'][pi]=dialog.result_point
            self.point_index=None
            self.store.save_draft(self.sid,self.draft_content,allow_invalid=True)
            self.load_session();self.focus_issue_point(min(pi,len(self.draft_content['points'])-1))

    def refresh_claim_attributions(self):
        self.flush_edits()
        proposed,changed=propose_attribution_refresh(self.draft_content,self.store.get(self.sid))
        if not changed:
            self.check_draft_references();return
        preview='\n\n'.join(proposed['points'][i]['title']+'\n'+proposed['points'][i]['summary'] for i in changed)
        self.show_private_text('Attributions proposées — à contrôler',preview)
        if QMessageBox.question(self,'Appliquer ces attributions',f'Appliquer la mise à jour de {len(changed)} point(s) depuis les sources actuelles ? Les textes des affirmations restent inchangés ; une nouvelle révision sera créée et devra être relue.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        self.store.save_draft(self.sid,proposed,allow_invalid=True)
        self.load_session();self.check_draft_references()

    def approve(self):
        try:
            self.flush_edits()
            state = self.store.get(self.sid)
            if not state["draft"]:
                raise ValueError("Préparez et sauvegardez un brouillon avant la relecture.")
            issues=draft_issues(state['draft']['content'],state)
            if issues:raise DraftEvidenceError(issues)
            reviewer, ok = QInputDialog.getText(self, "Relecture humaine", "Nom de la personne ayant relu cette révision")
            if not ok or not reviewer.strip():
                return
            if QMessageBox.question(self, "Confirmer la relecture", "Confirmez-vous avoir relu les textes, intervenants, décisions, sources et votes de cette révision ? Cette action autorise son export et ne vaut pas adoption officielle.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
            # Explicit confirmation rebases the reviewed edited document to current sources.
            if state["draft"]["context_sha256"] != self.store.context_hash(self.sid):
                self.store.save_draft(self.sid, state["draft"]["content"])
            role = None
            if state["draft"]["content"].get("document_mode") == "municipal":
                if QMessageBox.question(self, "Secrétaire de séance", "Confirmez-vous être le secrétaire chargé de relire ce projet de procès-verbal municipal ?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                    return
                role = "secretary"
            self.store.approve(self.sid, reviewer, role)
            self.load_session()
            self.status.setText("Relecture enregistrée pour cette révision. Le document reste un projet non officiel.")
        except Exception as error:
            self.report_error(error)

    def restore_draft(self):
        if not self.sid or self.task or self.recorder:
            return
        self.flush_edits()
        versions = self.store.draft_history(self.sid)
        if not versions:
            return
        choices = [f"Révision {v['revision']} — {v['created_at']}" for v in versions]
        choice, ok = QInputDialog.getItem(self, "Révisions conservées", "Choisir une révision à consulter", choices, 0, False)
        if not ok:
            return
        selected = versions[choices.index(choice)]
        content = json.loads(selected["content_json"])
        text = "\n\n".join(p["title"] + "\n" + p["summary"] for p in content["points"])
        self.show_private_text("Ancienne révision — lecture seule", text)
        if QMessageBox.question(self, "Restaurer le brouillon", "Créer une nouvelle révision avec ce contenu ? La version active reste conservée. Si ses sources ne correspondent plus, restaurez d’abord la transcription associée.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                self.store.restore_draft(self.sid, selected["id"])
                self.load_session()
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

    def audio_mode_label(self):
        from notetaker.services.audio_engine import read_mode
        return {'auto':'Automatique — compatibilité CUDA vérifiée avant traitement',
                'cpu':'CPU — Small + sherpa', 'gpu':'GPU NVIDIA — Large-v3 + Community-1'}[read_mode(self.store.root)]

    def audio_settings(self):
        from notetaker.services.audio_engine import read_mode, save_mode
        dialog = QDialog(self)
        dialog.setWindowTitle('Paramètres du traitement audio local')
        dialog.resize(620, 250)
        layout = QVBoxLayout(dialog)
        layout.addWidget(paragraph('Le mode automatique vérifie les modèles locaux, les bibliothèques CUDA, un calcul réel et la mémoire GPU libre. Aucun téléchargement. Les noms restent attribués par un opérateur.'))
        choice = QComboBox(dialog)
        choice.setObjectName('audio_engine_choice')
        for label, mode in [('Automatique (recommandé)', 'auto'), ('CPU — Compatible avec tous les PC pris en charge', 'cpu'), ('GPU NVIDIA — Meilleures performances potentielles', 'gpu')]:
            choice.addItem(label, mode)
        choice.setCurrentIndex(choice.findData(read_mode(self.store.root)))
        layout.addWidget(choice)
        layout.addWidget(paragraph('Après un échec GPU, le basculement CPU doit être demandé explicitement. Les performances dépendent du PC et de l’enregistrement.'))
        actions = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        actions.button(QDialogButtonBox.Save).setText('Enregistrer')
        actions.button(QDialogButtonBox.Cancel).setText('Annuler')
        actions.accepted.connect(dialog.accept)
        actions.rejected.connect(dialog.reject)
        layout.addWidget(actions)
        if dialog.exec() == QDialog.Accepted:
            save_mode(self.store.root, choice.currentData())
            self.engine_status.setText('Moteur audio : ' + self.audio_mode_label())

    def analyse(self, mode=None):
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
        self.cpu_retry.hide()
        requested = mode if isinstance(mode, str) else None
        self.run_task("analysis", lambda progress, cancel: Pipeline(self.store.root, progress=progress, cancel=cancel).analyse(sid, requested))

    def generate(self):
        if not self.sid or self.recorder or self.task:
            return
        try:
            if self.registry_page.editor_changed():raise ValueError('Enregistrez la correction de la fiche du registre avant de rédiger.')
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            return
        from notetaker.services.information_registry import RegistryService
        current=RegistryService(self.store).latest(self.sid)
        if self.document_mode.currentData()!='transcript' and (not current or current['stale']):
            self.tabs.setCurrentWidget(self.registry_page)
            self.status.setText('Préparez le registre puis contrôlez ses informations avant de lancer la rédaction.');return
        if self.store.get(self.sid)["draft"] and QMessageBox.question(self, "Nouveau brouillon", "Créer une nouvelle révision depuis le registre avec Qwen3 ? L’ancienne révision est conservée.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        sid = self.sid
        mode = self.document_mode.currentData()
        length=self.summary_length.currentData()
        state=self.store.get(sid)
        if mode!='transcript' and state['metadata'].get('summary_length','standard')!=length:
            self.store.save_details(sid,state['title'],{**state['metadata'],'summary_length':length})
            self.state=self.store.get(sid)
        self.run_task("minutes", lambda progress, cancel: Pipeline(self.store.root, progress=progress, cancel=cancel).generate(sid, mode, length))

    def prepare_information_registry(self):
        if not self.sid or self.recorder or self.task:return
        try:
            if self.registry_page.editor_changed():raise ValueError('Enregistrez la correction de la fiche avant de reprendre la préparation.')
            self.flush_edits()
        except Exception as error:self.report_error(error);return
        sid=self.sid
        self.run_task('registry',lambda progress,cancel:Pipeline(self.store.root,progress=progress,cancel=cancel).prepare_registry(sid))

    def write_from_registry(self):
        if self.document_mode.currentData()=='transcript':
            self.document_mode.setCurrentIndex(self.document_mode.findData('summary'))
        self.generate()

    def verify_registry_information(self,information_id):
        if not self.sid or self.recorder or self.task:return
        try:self.flush_edits()
        except Exception as error:self.report_error(error);return
        sid=self.sid
        self.run_task('registry_check',lambda progress,cancel:Pipeline(self.store.root,progress=progress,cancel=cancel).verify_information(sid,information_id))

    def generate_direct(self, length, resume_id=None):
        if not self.experimental_direct or not self.sid or self.recorder or self.task:
            return
        try:
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            return
        from notetaker.services.direct_summary import DirectSummaryService
        sid = self.sid
        self.run_task('direct', lambda progress, cancel: DirectSummaryService(self.store.root,
            enabled=True, progress=progress, cancel=cancel).generate(sid, summary_length=length, resume_id=resume_id))

    def reuse_direct(self, run_id):
        if not self.experimental_direct or not self.sid or self.recorder or self.task:
            return
        try:
            self.flush_edits()
            from notetaker.services.direct_summary import DirectSummaryService
            DirectSummaryService(self.store.root, enabled=True).reuse(self.sid, run_id)
            self.load_session()
            self.tabs.setCurrentIndex(3)
            self.status.setText('Résultat réutilisé sans appel IA. Nouvelle révision à relire ; le brouillon précédent reste dans l’historique.')
        except Exception as error:
            self.report_error(error)

    def run_task(self, kind, function):
        if self.task:
            return
        if kind!='stop' and self.registry_page.editor_changed():
            self.status.setText('Enregistrez la correction du registre ou annulez la saisie avant de lancer ce traitement.');return
        self.task = Task(function, self)
        self.task_started = time.monotonic()
        self.task_kind = kind
        self.active_audio_engine = 'Vérification en cours'
        self.audio_settings_button.setEnabled(False)
        self.cpu_retry.hide()
        self.tabs.setEnabled(False)
        self.simple_page.setEnabled(False)
        self.advanced_mode.setEnabled(False)
        self.history.setEnabled(False)
        self.new_button.setEnabled(False)
        self.archive_button.setEnabled(False)
        self.analyse_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.cancel_button.setEnabled(kind not in {"stop", "import", "preview"})
        self.progress.setRange(0, 0)
        self.progress.show()
        self.task.progress.connect(self.task_progress)
        self.task.succeeded.connect(lambda value: self.task_success(kind, value))
        self.task.failed.connect(lambda error: self.task_failure(kind, error))
        self.task.finished.connect(self.task_finished)
        self.task.start()

    def task_progress(self, message):
        if message.startswith('REGISTRY_PROGRESS:'):
            data=json.loads(message.removeprefix('REGISTRY_PROGRESS:'))
            completed,total=data.get('completed',0),data.get('total',0)
            if isinstance(total,int) and total>0 and isinstance(completed,int):
                self.progress.setRange(0,total);self.progress.setValue(min(total,completed))
                phase_label={'automatic_report':'Rédaction du compte rendu','registry':'Extraction des informations','registry_grouping':'Classement des sujets',
                    'registry_relations':'Contrôle des relations','registry_complete':'Préparation conservée'}.get(data.get('phase'),'Préparation du registre')
                message=f"{phase_label} : {completed}/{total}"
                if data.get('batch'):message+=f" — lot {data['batch']}/{data['batches']} en cours"
                self.registry_page.guide.setText(message+' ; les propositions restent à vérifier.')
            else:message='Préparation du registre : '+str(data.get('phase','contrôles'))
        self.status.setText(message)
        if message.startswith('Moteur utilisé : '):
            self.active_audio_engine = message.removeprefix('Moteur utilisé : ')

    def cancel_task(self):
        if self.task:
            self.task.cancel.set()
            self.status.setText("Arrêt du traitement demandé. Les enregistrements restent conservés.")

    def task_success(self, kind, value):
        if kind == 'analysis':
            self.engine_status.setText(self.audio_mode_label() + f" | Moteur utilisé : {value['engine']} — {value['device'].upper()} — {value['elapsed_seconds']:.1f} s")
        if kind == "stop":
            self.store.finish_take(self.recording_take, "interrupted" if value else "ready")
            self.recorder = None
            self.microphone.setEnabled(True)
            self.record_button.setEnabled(True)
        self.load_session()
        if kind=='automatic':
            self.advanced_mode.setChecked(False)
            self.status.setText(f"Brouillon généré : {value['points']} point(s). "+
                f"{value.get('paraphrase_claims',0)} reformulation(s), {value.get('quoted_fallback_points',0)} extrait(s) à vérifier. "+
                ('Transcription existante réutilisée. ' if value.get('transcription_reused') else '')+
                'Relisez et corrigez ; aucune approbation automatique.')
            return
        if kind=='registry':
            self.tabs.setCurrentWidget(self.registry_page)
            self.registry_page.preparation_complete(value)
        if kind == 'direct':
            self.tabs.setCurrentWidget(self.direct_page)
        if kind=='registry_check':
            self.tabs.setCurrentWidget(self.registry_page)
            self.registry_page.focus_entry(value.get('focus_id',''))
        if kind == "preview":
            self.playback.play(value)
            return  # Keep any explicit playback error instead of overwriting it.
        self.status.setText({"stop": "Prise sauvegardée." if not value else f"Prise préservée avec incident : {value}", "import": "Original importé et vérifié. Vous pouvez lancer la transcription.",
            "analysis": "Transcription et voix disponibles. Relisez les textes et attribuez les noms avant de préparer le registre.",
            "registry":"Registre préparé. Consultez les informations À vérifier, les sources et les relations avant de rédiger.",
            "registry_check":"Contrôle Qwen enregistré comme avis provisoire. Examinez les sources et toute variante avant approbation ; le document reste à relire.",
            "direct": "Essai conservé. Examinez les alertes et omissions, puis ouvrez le brouillon pour le corriger et le relire.",
            "minutes": "Brouillon préparé. Vérifiez les extraits, complétez décisions et votes puis enregistrez votre relecture.", "preview": "Lecture de l’audio préparé."}.get(kind, "Action effectuée."))
        if kind == 'direct' and not value.get('draft_saved'):
            self.status.setText('Essai conservé, mais aucun nouveau brouillon : aucun paragraphe admissible. '
                                'Consultez les rejets et les sources du laboratoire. Le brouillon précédent reste conservé.')
        if kind=='registry':
            self.status.setText(f"Préparation terminée : {value.get('created_information_entries',0)} nouvelle(s) fiche(s), "
                f"{value.get('proposed_information_entries',0)} propositions à vérifier et {value.get('blocked_information_entries',0)} à corriger / rattacher. "
                'Les passages sources sont dans une vue séparée. Écoutez puis approuvez les informations fidèles avant la rédaction.')

    def task_failure(self, kind, error):
        if kind in ('analysis','automatic') and 'GPU_AUDIO_UNAVAILABLE' in str(error):
            self.cpu_retry.show()
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
        self.audio_settings_button.setEnabled(True)
        self.simple_page.setEnabled(True)
        self.advanced_mode.setEnabled(True)

    def tick(self):
        if self.task and getattr(self, 'task_kind', '') == 'analysis':
            self.engine_status.setText(self.audio_mode_label() + ' | ' + self.active_audio_engine + f" — traitement : {time.monotonic()-self.task_started:.0f} s")
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
        if self.registry_page.editor_changed():
            self.status.setText('Enregistrez la correction du registre ou annulez la saisie avant de fermer.')
            event.ignore();return
        try:
            self.flush_edits()
        except Exception as error:
            self.report_error(error)
            event.ignore()
            return
        self.playback.close()
        self.store.close()
        event.accept()

def explain_error(error):
    text = str(error)
    if 'REGISTRY_APPROVAL_BLOCKED:' in text:
        from notetaker.ui.information_registry import REASONS
        codes=text.split('REGISTRY_APPROVAL_BLOCKED:',1)[1].split(',')
        return 'Cette information ne peut pas être approuvée : '+' '.join(REASONS.get(c,c) for c in codes)+' Corrigez la fiche ou ses sources, puis enregistrez-la.'
    if 'GPU_AUDIO_UNAVAILABLE' in text:
        code = text.split('GPU_AUDIO_UNAVAILABLE:', 1)[-1]
        from notetaker.services.audio_engine import GPU_DIAGNOSTICS as reasons
        return reasons.get(code, 'Le traitement GPU a échoué (diagnostic : '+code+').') + ' Les prises et corrections sont conservées. Vous pouvez relancer explicitement sur CPU.'
    from jsonschema import ValidationError
    if isinstance(error,ValidationError):
        path=' / '.join(str(p) for p in error.absolute_path) or 'document'
        return f'Le champ « {path} » est incomplet ou mal renseigné. Corrigez-le avant de poursuivre.'
    messages = {
        "DIRECT_TEST_COPY_REQUIRED": "Le laboratoire exige une copie de test marquée et une activation explicite. Ouvrez le lanceur de test ; les séances habituelles restent conservées.",
        "DIRECT_PROVENANCE_INVALID": "L’artefact de cet essai est absent ou altéré. Retrouvez le dossier complet de l’essai ou relancez la synthèse sur la copie ; l’export reste bloqué.",
        "DIRECT_SOURCES_CHANGED": "Les sources, noms ou l’ordre du jour ont changé depuis cet essai. Relancez la synthèse puis relisez la nouvelle révision.",
        "DIRECT_CONTEXT_BUDGET_EXCEEDED": "Le contexte dépasse la capacité du moteur expérimental. Les sources et résultats intermédiaires sont conservés ; consultez le dossier de l’essai.",
        "DIRECT_COLD_WORKSPACE_NOT_EMPTY": "Cet essai possède déjà des résultats intermédiaires. Démarrez un nouvel essai à froid ou reprenez explicitement l’essai interrompu.",
        "DIRECT_COMPLETED_RUN_IMMUTABLE": "Cet essai est terminé et conservé dans l’historique. Démarrez un nouvel essai pour produire une nouvelle révision.",
        "DIRECT_EXPERIMENT_VERSION_CHANGED": "Cet essai a été créé avec une autre version expérimentale. Ses résultats restent conservés. Démarrez un nouvel essai pour utiliser le moteur actuel.",
        "DIRECT_MODEL_RESPONSE_INCOMPLETE": "Qwen n’a pas terminé une réponse exploitable. Les sources et résultats partiels sont conservés. Consultez l’essai interrompu puis reprenez-le ou démarrez un nouvel essai.",
        "DIRECT_MODEL_RESPONSE_SCHEMA_INVALID": "La réponse de Qwen ne respecte pas le format attendu. Elle reste dans le dossier de l’essai pour diagnostic ; le brouillon précédent est conservé.",
        "DIRECT_MODEL_TIMEOUT": "Le délai de calcul est dépassé. La sortie partielle, les sources et le brouillon précédent sont conservés. Consultez l’essai interrompu avant de le reprendre.",
        'REGISTRY_REQUIRED':'Préparez le registre des informations puis contrôlez ses sources avant de rédiger.',
        'REGISTRY_INFORMATION_NOT_FOUND':'La fiche à vérifier n’existe plus dans cette révision. Rechargez le registre courant et sélectionnez une information.',
        'REGISTRY_STALE':'La transcription ou les attributions ont changé. Le registre précédent reste conservé ; préparez sa nouvelle version puis revérifiez les informations.',
        'REGISTRY_CONCURRENT_CHANGE':'Le registre a été modifié pendant cette opération. Rechargez sa dernière révision avant de poursuivre ; vos sources sont conservées.',
        'REGISTRY_HUMAN_CHANGE_PROTECTED':'Le résultat du moteur tenterait de remplacer une information vérifiée ou corrigée par l’opérateur. Le résultat est refusé ; vos choix restent conservés.',
        'REGISTRY_ACTOR_REASON_REQUIRED':'Renseignez votre nom et le motif de la vérification ou de la correction.',
        'REGISTRY_INVALID_SOURCE':'Une citation est absente, modifiée ou attribuée à une autre voix. Corrigez les liens dans « Sources et contexte » avant d’approuver.',
        'REGISTRY_SOURCE_REQUIRES_INFORMATION':'Ce texte est un passage source intégral. Rédigez une information, rattachez ses citations puis enregistrez-la avant de l’approuver.',
        'REGISTRY_NO_ELIGIBLE_INFORMATION':'Aucune information ne peut être rédigée avec les contrôles actuels. Consultez « À vérifier », corrigez le sens et les citations puis approuvez les informations vérifiées.',
        'REGISTRY_DOCUMENT_REFERENCE_INVALID':'Le document référence une révision ou une information de registre incohérente. Conservez-le dans l’historique et régénérez depuis le registre courant.',
        'REGISTRY_EDIT_INVALID':'L’information est incomplète. Vérifiez son contenu, son type, son sujet et ses citations.',
        'REGISTRY_RELATION_INVALID':'Cette relation ne peut pas être confirmée. Vérifiez les deux informations et leurs sources ; une information ne peut pas se répondre à elle-même.',
        'REGISTRY_RELATION_SOURCES_REQUIRED':'Le lien doit conserver les sources des deux informations. Rattachez-les avant de confirmer.',
        'REGISTRY_WRITER_CHANGED_INFORMATION':'La rédaction a tenté de changer une information du registre. Le nouveau texte est refusé ; corrigez l’information dans le registre avant de relancer.',
        'REGISTRY_SCHEMA_INVALID':'Le registre contient une fiche incomplète ou un état inconnu. Conservez la copie et reprenez sa préparation ; les transcriptions restent disponibles.',
        'REGISTRY_SNAPSHOT_CHANGED':'L’empreinte de l’instantané source du registre ne correspond plus à son contenu. Ce registre est refusé ; restaurez une version intacte ou préparez-en une nouvelle.',
        'REGISTRY_SOURCE_INVENTORY_INCOMPLETE':'L’inventaire du registre ne contient pas tous les passages sources. Le résultat est refusé ; reprenez sa préparation depuis la transcription conservée.',
        'REGISTRY_INVALID_APPROVED_SOURCE':'Une information déclarée fiable possède une citation ou une attribution invalide. Corrigez sa source avant de l’approuver.',
        'REGISTRY_DUPLICATE_ID':'Deux fiches partagent un identifiant dans le résultat reçu. Le registre précédent reste conservé ; reprenez le traitement.',
        'REGISTRY_WRONG_SESSION':'Le registre reçu appartient à une autre séance. Le résultat est refusé ; rouvrez la bonne séance avant de poursuivre.',
        'REGISTRY_EXTRACTION_INCOMPLETE':'Le moteur n’a pas rendu de diagnostic pour tous les tours de parole. Les résultats partiels et les sources sont conservés ; reprenez la préparation.',
        'REGISTRY_ROUTING_INCOMPLETE':'Le classement a omis une information. Le résultat est refusé ; le registre conserve les fiches pour reprendre leur classement.',
        'CLAIM_EVIDENCE_INVALID':'Les références du brouillon sont incohérentes. Utilisez « Contrôler les références » puis corrigez l’affirmation, sa citation ou son intervenant.',
        'MANUAL_ALIGNMENT_REQUIRES_REVIEW':'Les nouvelles prises ou les nouveaux horaires ne permettent pas de replacer sûrement les corrections humaines. La transcription corrigée est conservée ; vérifiez les prises sélectionnées ou préparez une séance distincte.',
        'ANALYSIS_REVISION_NOT_FOUND':'Cette version de transcription n’est pas disponible dans l’historique de la séance.',
        'SPLIT_REQUIRES_INTERIOR_TIME_AND_TEXT_POSITION':'Placez le curseur à l’intérieur du texte et choisissez un instant compris dans le passage.',
        'TWO_EXISTING_SPEAKERS_REQUIRED':'Choisissez deux voix distinctes de la séance avant de les fusionner.',
        'DATABASE_NEWER_THAN_APPLICATION':'Cette base a été ouverte avec une version plus récente de NoteTaker. Utilisez le dernier exécutable ou une copie de sauvegarde compatible.',
        'INVALID_SUMMARY_LENGTH':'Choisissez une longueur courte, standard ou détaillée avant de générer le compte rendu.',
        'SUMMARY_CONTEXT_BUDGET_EXCEEDED':'Le dossier de synthèse dépasse la capacité locale du modèle. La transcription et le précédent brouillon sont conservés ; préparez des extraits plus courts dans une séance distincte.',
        'NO_SUPPORTED_TOPIC_PARAGRAPHS':'Aucun paragraphe n’a passé les contrôles de sens et d’attribution. La transcription et l’ancien brouillon sont conservés. Vérifiez les passages incertains avant de relancer.',
        'SUMMARY_INVALID_ID_SET':'Le moteur a perdu ou répété des références pendant la synthèse. Le nouveau résultat est refusé ; l’ancien brouillon et les sources sont conservés.',
        'NARRATIVE_UNKNOWN_VOICE':'Une phrase désigne une voix absente de ses sources. Le nouveau texte est refusé ; vérifiez les attributions de transcription.',
        'JSONDecodeError':'Le moteur a rendu une réponse incomplète ou illisible. L’ancien brouillon et les sources sont conservés ; relancez la génération après vérification des passages incertains.',
        'ValidationError':'La réponse du moteur ne respecte pas le format attendu. Le nouveau résultat est refusé ; le brouillon précédent et ses sources sont conservés.',
        'UNEXPECTED_LLM_OUTPUT':'Le moteur a ajouté du texte hors du format attendu. La génération est refusée ; vous pouvez la relancer sans perdre les sources ni le précédent brouillon.',
        'LLAMA_NATIVE_PROCESS_FAILED':'Le moteur de rédaction s’est arrêté. Le précédent brouillon et les enregistrements sont conservés ; vérifiez les modèles locaux et relancez la génération.',
        'WORKER_TIMEOUT':'Le traitement a dépassé le délai autorisé. Les sources et le précédent brouillon sont conservés ; relancez sur une séance plus courte si nécessaire.',
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
        "DAMAGED_TRANSCRIPT_RETRANSCRIBE_ORIGINAL": "La transcription contient des caractères perdus par l’ancienne version. Relancez l’analyse depuis l’audio original ; les corrections précédentes restent restaurables.",
        "UNSUPPORTED_EXPORT_GLYPHS": "Un caractère n’est pas couvert par la police embarquée. L’export est arrêté pour éviter des carrés noirs. Corrigez le caractère signalé : " + text,
        "MUNICIPAL_SECRETARY_REVIEW_REQUIRED": "Le projet de procès-verbal municipal exige une relecture explicitement confirmée par le secrétaire de séance.",
        "NO_SUPPORTED_SUMMARY_CLAIMS": "Aucune synthèse suffisamment sourcée n’a été produite. La transcription et le brouillon précédent sont conservés.",
        "SUMMARY_GROUPING_LOST_OR_DUPLICATED_CLAIMS": "Le regroupement a omis ou répété des informations. Le résumé est refusé ; la transcription et le brouillon précédent restent conservés.",
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
