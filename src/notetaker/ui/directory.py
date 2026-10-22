"""Municipal directory widgets; no biometric capability is instantiated here."""
import json
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QDialogButtonBox, QTextEdit, QSplitter)
from notetaker.services.directory import DirectoryService, PERSON_FIELDS, ATTENDANCE, person_name


def label(text):
    widget = QLabel(text)
    widget.setWordWrap(True)
    return widget


def read_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setAlternatingRowColors(True)
    return table


class PersonPicker(QDialog):
    def __init__(self, service, excluded=(), parent=None):
        super().__init__(parent)
        self.service, self.excluded, self.selected = service, set(excluded), set()
        self.setWindowTitle('Ajouter des personnes à la séance')
        self.resize(800, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(label('Sélectionnez les fiches actives. Leur présence sera à renseigner ; aucun nom ne sera reconnu automatiquement.'))
        self.search = QLineEdit(placeholderText='Nom, prénom, fonction ou commune…')
        layout.addWidget(self.search)
        self.table = read_table(['Sélection', 'Intervenant', 'Fonction permanente', 'Commune'])
        layout.addWidget(self.table)
        self.table.itemChanged.connect(self.check_changed)
        self.search.textChanged.connect(self.refresh)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('Ajouter la sélection')
        buttons.button(QDialogButtonBox.Cancel).setText('Annuler')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh()

    def refresh(self):
        people = [p for p in self.service.list_people(self.search.text()) if p['id'] not in self.excluded]
        self.table.blockSignals(True)
        self.table.setRowCount(len(people))
        for row, p in enumerate(people):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            check.setData(Qt.UserRole, p['id'])
            check.setCheckState(Qt.Checked if p['id'] in self.selected else Qt.Unchecked)
            self.table.setItem(row, 0, check)
            for col, text in enumerate([person_name(p), p['position'], p['municipality']], 1):
                self.table.setItem(row, col, QTableWidgetItem(text))
        self.table.blockSignals(False)

    def check_changed(self, item):
        if item.column() == 0:
            pid = item.data(Qt.UserRole)
            self.selected.add(pid) if item.checkState() == Qt.Checked else self.selected.discard(pid)


class DirectoryDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.service = DirectoryService(store)
        self.pid, self.revision, self.dirty, self.loading = None, None, False, False
        self.setWindowTitle('Annuaire municipal — intervenants')
        self.resize(1120, 700)
        self.setMinimumSize(900, 600)
        layout = QVBoxLayout(self)
        title = QLabel('Annuaire des intervenants')
        title.setObjectName('heading')
        layout.addWidget(title)
        layout.addWidget(label('Des fiches réutilisables pour vos séances. Les rôles et les présences se renseignent séparément dans chaque séance.'))
        filters = QHBoxLayout()
        self.search = QLineEdit(placeholderText='Rechercher un nom, une fonction, une commune…')
        self.status_filter = QComboBox()
        for text, code in [('Fiches actives', 'active'), ('Fiches archivées', 'archived'), ('Toutes les fiches', 'all')]:
            self.status_filter.addItem(text, code)
        self.city_filter = QComboBox()
        self.city_filter.setMinimumWidth(160)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.city_filter)
        filters.addWidget(self.status_filter)
        layout.addLayout(filters)
        split = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.table = read_table(['Intervenant', 'Fonction permanente', 'Commune', 'Fiche'])
        left_layout.addWidget(self.table)
        self.count = QLabel()
        left_layout.addWidget(self.count)
        split.addWidget(left)
        right = QWidget()
        form_layout = QVBoxLayout(right)
        self.form_title = QLabel('Nouvelle fiche')
        self.form_title.setObjectName('heading')
        form_layout.addWidget(self.form_title)
        form = QFormLayout()
        self.fields = {}
        for key, text in zip(PERSON_FIELDS, ['Prénom *', 'Nom *', 'Fonction permanente', 'Commune']):
            field = QLineEdit()
            field.setMaxLength(200)
            field.textChanged.connect(self.edited)
            self.fields[key] = field
            form.addRow(text, field)
        form_layout.addLayout(form)
        self.feedback = label('Les champs marqués * sont obligatoires.')
        form_layout.addWidget(self.feedback)
        self.save_button = QPushButton('Enregistrer la fiche')
        self.save_button.setProperty('primary', True)
        self.save_button.clicked.connect(self.save)
        form_layout.addWidget(self.save_button)
        self.new_button = QPushButton('+ Nouvelle fiche')
        self.new_button.clicked.connect(self.new_person)
        form_layout.addWidget(self.new_button)
        self.archive_button = QPushButton('Archiver la fiche')
        self.archive_button.clicked.connect(self.toggle_archive)
        form_layout.addWidget(self.archive_button)
        self.history_button = QPushButton('Historique de la fiche…')
        self.history_button.clicked.connect(self.show_history)
        form_layout.addWidget(self.history_button)
        form_layout.addStretch()
        form_layout.addWidget(label('Références vocales facultatives — autorisation juridique requise.\nL’annuaire reste utilisable sans biométrie.'))
        policy_button=QPushButton('Autorisation et paramètres des références vocales…')
        policy_button.clicked.connect(self.configure_voice)
        form_layout.addWidget(policy_button)
        self.voice_button = QPushButton('Enregistrer / gérer les références vocales')
        self.voice_button.setEnabled(False)
        self.voice_button.setToolTip('Enregistrer d’abord la fiche, puis renseigner l’autorisation de la collectivité.')
        self.voice_button.clicked.connect(self.open_voice)
        form_layout.addWidget(self.voice_button)
        split.addWidget(right)
        split.setSizes([670, 370])
        layout.addWidget(split, 1)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.button(QDialogButtonBox.Close).setText('Fermer l’annuaire')
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self.search.textChanged.connect(self.refresh)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        self.city_filter.currentIndexChanged.connect(self.refresh)
        self.table.currentCellChanged.connect(self.select_person)
        self.update_cities()
        self.refresh()
        self.fill(None)

    def edited(self):
        if not self.loading:
            self.dirty = True
            self.feedback.setText('Modifications non enregistrées')

    def configure_voice(self):
        from .voice_profiles import VoicePolicyDialog
        VoicePolicyDialog(self.service.store.root,self).exec()
        self.refresh_voice_state()

    def refresh_voice_state(self):
        from pathlib import Path
        enabled=False
        if self.pid and (Path(self.service.store.root)/'voice-vault.sqlite3').exists():
            try:
                from notetaker.services.voice_profiles import VoiceProfiles
                vault=VoiceProfiles(self.service.store.root)
                if vault.samples(self.pid):enabled=True  # deletion after revocation
                else:vault.require_authorization();enabled=True
            except Exception:pass
        self.voice_button.setEnabled(enabled)

    def open_voice(self):
        if not self.pid or not self.can_leave():return
        from .voice_profiles import VoiceEnrollmentDialog
        VoiceEnrollmentDialog(self.service.store.root,self.service.get_person(self.pid),self).exec()

    def can_leave(self):
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, 'Fiche non enregistrée', 'Enregistrer les modifications de cette fiche ?',
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save()
        return answer == QMessageBox.Discard

    def fill(self, person):
        self.loading = True
        self.pid = person['id'] if person else None
        self.revision = person['revision'] if person else None
        for k, widget in self.fields.items():
            widget.setText(person[k] if person else '')
        self.form_title.setText('Modifier la fiche' if person else 'Nouvelle fiche')
        self.archive_button.setEnabled(person is not None)
        self.archive_button.setText('Réactiver la fiche' if person and person['archived'] else 'Archiver la fiche')
        self.history_button.setEnabled(person is not None)
        self.feedback.setText('Fiche archivée — historique conservé.' if person and person['archived'] else 'Les champs marqués * sont obligatoires.')
        self.loading, self.dirty = False, False
        self.refresh_voice_state()

    def new_person(self):
        if self.can_leave():
            self.table.blockSignals(True)
            self.table.clearSelection()
            self.table.setCurrentCell(-1, -1)
            self.table.blockSignals(False)
            self.fill(None)
            self.fields['first_name'].setFocus()

    def update_cities(self):
        selected = self.city_filter.currentData()
        self.city_filter.blockSignals(True)
        self.city_filter.clear()
        self.city_filter.addItem('Toutes les communes', '')
        for city in sorted({p['municipality'] for p in self.service.list_people(status='all') if p['municipality']}):
            self.city_filter.addItem(city, city)
        self.city_filter.setCurrentIndex(max(0, self.city_filter.findData(selected)))
        self.city_filter.blockSignals(False)

    def refresh(self):
        people = self.service.list_people(self.search.text(), self.city_filter.currentData() or '', self.status_filter.currentData())
        self.table.blockSignals(True)
        self.table.setRowCount(len(people))
        for row, p in enumerate(people):
            for col, text in enumerate([person_name(p), p['position'], p['municipality'], 'Archivée' if p['archived'] else 'Active']):
                item = QTableWidgetItem(text)
                item.setData(Qt.UserRole, p['id'])
                self.table.setItem(row, col, item)
            if p['id'] == self.pid:
                self.table.setCurrentCell(row, 0)
        self.table.blockSignals(False)
        self.count.setText(f'{len(people)} fiche(s) affichée(s) • sélectionnez une ligne pour la modifier')

    def select_person(self, row, *args):
        if row < 0 or not self.table.item(row, 0):
            return
        pid = self.table.item(row, 0).data(Qt.UserRole)
        if pid != self.pid:
            if self.can_leave():
                self.fill(self.service.get_person(pid))
            else:
                self.refresh()

    def save(self):
        try:
            pid = self.service.save_person({k: w.text() for k, w in self.fields.items()}, self.pid, self.revision)
            self.fill(self.service.get_person(pid))
            self.update_cities()
            self.refresh()
            self.feedback.setText('Fiche enregistrée. Les séances antérieures conservent leurs informations.')
            return True
        except ValueError as error:
            self.feedback.setText(str(error))
            return False

    def toggle_archive(self):
        if self.pid and self.can_leave():
            try:
                p = self.service.get_person(self.pid)
                self.service.archive_person(self.pid, not p['archived'], self.revision)
                self.fill(self.service.get_person(self.pid))
                self.refresh()
            except ValueError as error:
                self.feedback.setText(str(error))

    def show_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Historique de la fiche')
        dialog.resize(650, 450)
        layout = QVBoxLayout(dialog)
        view = QTextEdit()
        view.setReadOnly(True)
        names = {'create': 'Création', 'edit': 'Avant modification', 'archive': 'Archivage', 'reactivate': 'Réactivation'}
        view.setPlainText('\n\n'.join(f"{r['created_at']} — {names[r['action']]}\n" + '\n'.join(
            f"{k} : {v}" for k, v in json.loads(r['content_json']).items() if k in PERSON_FIELDS)
            for r in self.service.history(self.pid)))
        layout.addWidget(view)
        dialog.exec()

    def reject(self):
        if self.can_leave():
            super().reject()

    def closeEvent(self, event):
        event.accept() if self.can_leave() else event.ignore()


class ParticipantsPage(QWidget):
    saved = Signal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.service, self.sid = DirectoryService(store), None
        self.records, self.baseline, self.dirty, self.loading = [], [], False, False
        layout = QVBoxLayout(self)
        title = QLabel('Participants et présences')
        title.setObjectName('heading')
        layout.addWidget(title)
        layout.addWidget(label('La fonction vient de la fiche permanente ; le rôle concerne uniquement cette séance. Les présences ne déterminent ni le nombre de voix ni un résultat de vote.'))
        tools = QHBoxLayout()
        self.add_button, self.remove_button = QPushButton('Ajouter depuis l’annuaire…'), QPushButton('Retirer la sélection')
        self.add_button.clicked.connect(self.add_people)
        self.remove_button.clicked.connect(self.remove_person)
        tools.addWidget(self.add_button)
        tools.addWidget(self.remove_button)
        tools.addStretch()
        layout.addLayout(tools)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Intervenant', 'Fonction permanente', 'Présence', 'Rôle dans la séance', 'Procuration à', 'Référence du pouvoir'])
        self.table.horizontalHeaderItem(5).setToolTip('Référence et période de validité de la procuration, si nécessaire.')
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self.mark_dirty)
        layout.addWidget(self.table, 1)
        layout.addWidget(label('Une procuration exige un autre participant déclaré présent. Renseignez sa référence ou sa période si utile. La régularité des pouvoirs reste à vérifier par l’opérateur.'))
        self.feedback = label('Ajoutez les participants, puis renseignez leur présence.')
        layout.addWidget(self.feedback)
        self.save_button = QPushButton('Enregistrer les participants et présences')
        self.save_button.setProperty('primary', True)
        self.save_button.clicked.connect(self.save_clicked)
        layout.addWidget(self.save_button)

    def mark_dirty(self, *args):
        if not self.loading:
            self.dirty = True
            self.feedback.setText('Présences modifiées — enregistrement requis')

    def load(self, sid):
        self.sid = sid
        self.baseline = self.service.participants(sid)
        self.records = [dict(r) for r in self.baseline]
        self.render()
        self.dirty = False
        self.feedback.setText(f'{len(self.records)} participant(s) • attribution des voix entièrement manuelle')

    def collect(self):
        return [{**p, 'attendance': self.table.cellWidget(row, 2).currentData(),
                 'session_role': self.table.item(row, 3).text(),
                 'proxy_to_person_id': self.table.cellWidget(row, 4).currentData(),
                 'proxy_note': self.table.item(row, 5).text()} for row, p in enumerate(self.records)]

    def render(self):
        self.loading = True
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.records))
        for row, p in enumerate(self.records):
            for col, text in [(0, person_name(p['snapshot'])), (1, p['snapshot']['position']),
                              (3, p.get('session_role', '')), (5, p.get('proxy_note', ''))]:
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                if col in (0, 1):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)
            attendance = QComboBox()
            for code, text in ATTENDANCE.items():
                attendance.addItem(text, code)
            attendance.setCurrentIndex(attendance.findData(p.get('attendance', 'unconfirmed')))
            attendance.currentIndexChanged.connect(self.mark_dirty)
            self.table.setCellWidget(row, 2, attendance)
            proxy = QComboBox()
            proxy.addItem('Aucune', None)
            for other in self.records:
                if other['person_id'] != p['person_id']:
                    proxy.addItem(person_name(other['snapshot']), other['person_id'])
            proxy.setCurrentIndex(max(0, proxy.findData(p.get('proxy_to_person_id'))))
            proxy.currentIndexChanged.connect(self.mark_dirty)
            self.table.setCellWidget(row, 4, proxy)
        self.loading = False

    def add_people(self):
        picker = PersonPicker(self.service, [p['person_id'] for p in self.records], self)
        if picker.exec() == QDialog.Accepted:
            self.records = self.collect()
            for pid in sorted(picker.selected):
                p = self.service.get_person(pid)
                self.records.append({'person_id': pid, 'snapshot': {k: p[k] for k in PERSON_FIELDS}, 'attendance': 'unconfirmed'})
            self.render()
            self.mark_dirty()

    def remove_person(self):
        row = self.table.currentRow()
        if row >= 0:
            self.records = self.collect()
            pid = self.records[row]['person_id']
            if any(p.get('proxy_to_person_id') == pid for p in self.records):
                self.feedback.setText('Cette personne porte une procuration. Modifiez d’abord la représentation concernée.')
                return
            self.records.pop(row)
            self.render()
            self.mark_dirty()

    def save_if_dirty(self):
        if self.sid and self.dirty:
            self.service.save_participants(self.sid, self.collect(), expected=self.baseline)
            self.load(self.sid)
            self.saved.emit()

    def save_clicked(self):
        try:
            self.save_if_dirty()
            self.feedback.setText('Participants enregistrés. Toute modification impose une nouvelle relecture du brouillon.')
        except ValueError as error:
            self.feedback.setText(str(error))
