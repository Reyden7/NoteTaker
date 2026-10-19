"""Read-only experiment ledger; the ordinary document editor performs review."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTextEdit, QSplitter)
from notetaker.services.direct_summary import experiments
from notetaker.domain.direct_summary import source_inventory
from notetaker.ui.evidence import stamp
from notetaker.domain.summary import render_template, voice_registry
from notetaker.ui.information_registry import REASONS as REGISTRY_REASONS
from notetaker.services.evidence import REASONS as EVIDENCE_REASONS

SECTION = {'context': 'Contexte', 'arguments': 'Arguments', 'divergences': 'Divergences',
           'proposals': 'Propositions', 'potential_decisions': 'Décisions évoquées — à vérifier'}
REASONS = {'generation_budget_reached': 'Des informations peuvent manquer : budget de génération atteint.',
    'duplicate_candidate_preserved': 'Doublon strict de formulation, voix et citations : proposition brute conservée, sans nouvelle vérification IA.',
    'unbound_voice_alias': 'La notation de la voix ne correspond pas à l’auteur déclaré. Vérifier l’attribution et les sources.',
    'agenda_item_not_represented_in_document': 'Ce point de l’ordre du jour n’a pas de paragraphe rédigé. Vérifier s’il a été abordé ; aucune absence n’est déduite.',
    'grouping_failed_local_groups_preserved': 'Regroupement global incohérent : les groupes locaux sont conservés.',
    'rejected_or_uncertain_information': 'Des formulations ont été écartées ou des voix restent incertaines.',
    'uncited_sources_preserved': 'Passages sans citation dans le document : texte intégral conservé ; couverture à évaluer.',
    'potential_decision_requires_operator': 'Décision évoquée : contrôler puis saisir dans Décisions et votes.',
    'quote_missing_ambiguous_or_wrong_voice': 'Citation introuvable, répétée ou attribuée à une autre voix.'}
REASONS = {**EVIDENCE_REASONS, **REGISTRY_REASONS, **REASONS,
    'absence_of_opposition_changed_to_support': 'Une absence d’opposition a été transformée à tort en soutien.'}


class DirectSummaryPage(QWidget):
    def __init__(self, store, generate, edit, play, parent=None, resume=None, reuse=None):
        super().__init__(parent)
        self.store, self.generate, self.edit, self.play = store, generate, edit, play
        self.sid, self.records, self.items = None, [], []
        self.resume_callback = resume
        self.reuse_callback = reuse
        layout = QVBoxLayout(self)
        notice = QLabel('LABORATOIRE 0.2.5 — copie de test uniquement. Qualité non validée. '
                        'Le registre 0.2.4 est conservé. La relecture finale reste obligatoire.')
        notice.setWordWrap(True)
        notice.setObjectName('warning')
        layout.addWidget(notice)
        actions = QHBoxLayout()
        self.length = QComboBox()
        for label, key in [('Courte', 'short'), ('Standard', 'standard'), ('Détaillée', 'detailed')]:
            self.length.addItem(label, key)
        self.length.setCurrentIndex(1)
        self.start = QPushButton('Nouvel essai CPU à froid')
        self.start.clicked.connect(lambda: generate(self.length.currentData()))
        actions.addWidget(self.length)
        actions.addWidget(self.start)
        open_editor = QPushButton('Ouvrir le brouillon courant à relire')
        open_editor.clicked.connect(edit)
        actions.addWidget(open_editor)
        layout.addLayout(actions)
        recovery = QHBoxLayout()
        self.pending = QComboBox()
        self.pending.setToolTip('Les résultats partiels restent consultables dans l’historique ci-dessous.')
        self.resume_button = QPushButton('Reprendre cet essai interrompu')
        self.resume_button.clicked.connect(self.resume_selected)
        recovery.addWidget(self.pending, 1)
        recovery.addWidget(self.resume_button)
        layout.addLayout(recovery)
        self.banner = QLabel('Aucun essai sur cette séance.')
        self.banner.setWordWrap(True)
        layout.addWidget(self.banner)
        self.history = QComboBox()
        layout.addWidget(self.history)
        self.reuse_button = QPushButton('Rétablir cet essai comme nouveau brouillon — sans IA')
        self.reuse_button.setToolTip('Le brouillon courant reste dans l’historique. La nouvelle révision devra être relue.')
        self.reuse_button.clicked.connect(self.reuse_selected)
        layout.addWidget(self.reuse_button)
        filters = QHBoxLayout()
        self.view = QComboBox()
        for label, key in [('Alertes prioritaires', 'alerts'), ('Paragraphes proposés', 'topics'),
                           ('Toutes les informations et rejets', 'candidates'), ('Toutes les sources / omissions', 'inventory')]:
            self.view.addItem(label, key)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Rechercher un sujet, un texte ou un motif…')
        filters.addWidget(self.view)
        filters.addWidget(self.search)
        layout.addLayout(filters)
        split = QSplitter()
        self.rows = QTableWidget(0, 3)
        self.rows.setHorizontalHeaderLabels(['Sujet / horaire', 'État / section', 'Information'])
        self.rows.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rows.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rows.setSelectionMode(QAbstractItemView.SingleSelection)
        self.rows.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.rows.setWordWrap(True)
        self.rows.setColumnWidth(0, 170)
        self.rows.setColumnWidth(1, 155)
        self.rows.verticalHeader().setDefaultSectionSize(88)
        split.addWidget(self.rows)
        detail = QWidget()
        dl = QVBoxLayout(detail)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        dl.addWidget(self.details)
        self.source = QComboBox()
        dl.addWidget(self.source)
        self.listen = QPushButton('Écouter le passage source')
        self.listen.clicked.connect(self.listen_source)
        dl.addWidget(self.listen)
        split.addWidget(detail)
        split.setSizes([780, 400])
        layout.addWidget(split, 1)
        footer = QLabel('Les citations vérifient les liens, pas la fidélité du sens. Les scores de qualité '
                        'attendent les annotations humaines indépendantes. Aucune fiche du registre n’est approuvée ici.')
        footer.setWordWrap(True)
        layout.addWidget(footer)
        self.history.currentIndexChanged.connect(self.populate)
        self.view.currentIndexChanged.connect(self.populate)
        self.search.textChanged.connect(self.populate)
        self.rows.itemSelectionChanged.connect(self.select)

    def load(self, sid):
        self.sid = sid
        self.records = experiments(self.store.root, sid)
        self.pending.clear()
        directory = self.store.root/'sessions'/sid/'direct-experiments'
        for request_path in sorted(directory.glob('*/request.json')):
            if (request_path.parent/'result.json').exists():
                continue
            try:
                request = json.loads(request_path.read_text(encoding='utf-8'))
                checkpoint_path = request_path.parent/'inference'/'direct-checkpoint.json'
                ledger = json.loads(checkpoint_path.read_text(encoding='utf-8')) if checkpoint_path.exists() else {
                    'candidates': [], 'alerts': [], 'rejected': [], 'all_sources': request['utterances']}
                ledger.setdefault('inventory', source_inventory(request['utterances'], ledger['candidates'], set()))
                ledger.setdefault('alerts', [])
                run = request_path.parent.name
                self.records.append({'run_id': run, 'partial': True,
                                     'result': {'topics': [], 'ledger': ledger}, 'profile': {}})
                self.pending.addItem(run, {'run_id': run, 'length': request.get('summary_length', 'standard')})
            except (OSError, ValueError, KeyError):
                continue
        self.resume_button.setEnabled(bool(self.pending.count() and self.resume_callback))
        self.history.blockSignals(True)
        self.history.clear()
        for record in self.records:
            self.history.addItem(('Interrompu — ' if record.get('partial') else '') + record['run_id'])
        self.history.blockSignals(False)
        self.start.setEnabled(bool(sid))
        self.populate()

    def populate(self, *args):
        self.items = []
        index = self.history.currentIndex()
        record = self.records[index] if 0 <= index < len(self.records) else None
        self.reuse_button.setEnabled(bool(record and not record.get('partial') and self.reuse_callback))
        self.rows.setRowCount(0)
        self.details.clear()
        self.source.clear()
        if not record:
            self.banner.setText('Aucun essai terminé. Les interruptions gardent leurs fichiers dans le dossier direct-experiments de la séance.')
            return
        result, profile = record['result'], record.get('profile') or {}
        ledger = result['ledger']
        self.banner.setText(f"{len(result['topics'])} paragraphes · {len(ledger['alerts'])} alertes regroupées · "
                            f"{len(ledger['inventory'])} sources conservées · {profile.get('fresh_calls', '?')} inférences, "
                            f"{profile.get('cached_calls', 0)} reprises. Aucune validation humaine créée.")
        view = self.view.currentData()
        needle = self.search.text().casefold()
        for item in (result['topics'] if view == 'topics' else ledger.get(view, [])):
            if view == 'alerts':
                values = [item['subject'], 'Prioritaire' if item['priority'] == 'high' else 'À examiner', REASONS.get(item['reason'], item['reason'])]
            elif view == 'topics':
                values = [item['title'], 'Paragraphe proposé', ' '.join(self.readable(s['text'], record) for s in item['sentences'])]
            elif view == 'candidates':
                status = {'written': 'Rédigée', 'rejected': 'Écartée', 'omitted': 'Non retenue'}.get(item.get('status'), 'À examiner')
                values = [item['topic'], status + ' · ' + SECTION[item['section']], self.readable(item['template'], record)]
            else:
                values = [stamp(item['start_ms']), 'Citée' if item['written_ids'] else 'Non citée / conservée', item['text']]
            if needle and needle not in (json.dumps(item, ensure_ascii=False) + ' '.join(values)).casefold():
                continue
            row = self.rows.rowCount()
            self.rows.insertRow(row)
            for col, value in enumerate(values):
                self.rows.setItem(row, col, QTableWidgetItem(value))
            self.items.append(item)
        if self.items:
            self.rows.selectRow(0)

    def select(self):
        row = self.rows.currentRow()
        if row < 0 or row >= len(self.items):
            return
        item = self.items[row]
        record = self.records[self.history.currentIndex()]
        ledger = record['result']['ledger']
        ids = set(item.get('claims', item.get('uncertain_ids', [])))
        ids.update(r['id'] for r in item.get('rejected', []) if 'id' in r)
        ids.update(cid for r in item.get('rejected', []) for cid in r.get('ids', []))
        evidence = list(item.get('evidence', []))
        for c in ledger['candidates']:
            if c['id'] in ids:
                evidence.extend(c['evidence'])
        if 'start_ms' in item:
            evidence.append({'id': item['id'], 'quote': item['text']})
        sources = {u['id']: u for u in ledger['inventory']}
        lines = []
        if item.get('template'):
            lines += [item['topic'], SECTION[item['section']], self.readable(item['template'], record), '',
                'État : ' + {'candidate': 'Proposition non retenue dans le document', 'written': 'Rédigée — relecture requise',
                            'rejected': 'Écartée par les contrôles', 'omitted': 'Conservée hors du document'}.get(item.get('status'), 'À examiner')]
            lines += ['Motif : ' + REASONS.get(reason, reason) for reason in item.get('reasons', [])]
            lines += ['Motif : ' + REASONS.get(r['reason'], r['reason']) for r in ledger.get('rejected', []) if r.get('id') == item['id']]
        elif item.get('sentences'):
            lines += [item['title'], '', ' '.join(self.readable(s['text'], record) for s in item['sentences'])]
        elif 'reason' in item:
            lines += [item.get('subject', ''), REASONS.get(item['reason'], item['reason'])]
            lines += ['Écarté : ' + REASONS.get(r['reason'], r['reason']) for r in item.get('rejected', [])]
        else:
            lines += [item.get('text', ''), '', 'Texte hors citation (couverture sémantique non mesurée) :']
            lines += [r['text'] for r in item.get('uncited_text', [])]
            lines += ['Motif proposé : ' + reason for reason in item.get('generation_omission_reasons', [])]
        lines += ['', 'Citations et passages sources :']
        for e in evidence:
            source = sources.get(e['id'])
            if source:
                lines += [stamp(source['start_ms']) + ' → ' + stamp(source['end_ms']), '« ' + e['quote'] + ' »']
        self.details.setPlainText('\n'.join(lines))
        self.source.clear()
        for sid in dict.fromkeys(e['id'] for e in evidence):
            source = sources.get(sid)
            if source:
                self.source.addItem(stamp(source['start_ms']) + ' — ' + source['text'][:100], source)
        self.listen.setEnabled(self.source.count() > 0)

    def listen_source(self):
        source = self.source.currentData()
        if source:
            self.play(source)

    def resume_selected(self):
        selection = self.pending.currentData()
        if selection and self.resume_callback:
            self.resume_callback(selection['length'], selection['run_id'])

    def reuse_selected(self):
        index = self.history.currentIndex()
        if self.reuse_callback and 0 <= index < len(self.records) and not self.records[index].get('partial'):
            self.reuse_callback(self.records[index]['run_id'])

    def readable(self, template, record):
        snapshot = record.get('input') or {'utterances': record['result']['ledger']['inventory'],
                                           'speakers': self.store.get(self.sid)['speakers']}
        aliases = {value['alias']: key for key, value in voice_registry(snapshot).items()}
        try:
            return render_template(template, aliases, snapshot)
        except ValueError:
            return template
