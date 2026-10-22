"""First-draft workspace; no per-information approval before generation."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QListWidget,QTextEdit,QSplitter
from PySide6.QtCore import Qt


class SimpleReportPage(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.loading=False;self.index=-1;self.dirty=False
        layout=QVBoxLayout(self)
        title=QLabel('Votre réunion → un premier compte rendu');title.setObjectName('heading');layout.addWidget(title)
        text=QLabel('Importez votre audio, puis générez un brouillon. L’annuaire vocal est facultatif ; les voix inconnues restent non identifiées.');text.setWordWrap(True);layout.addWidget(text)
        actions=QHBoxLayout()
        for label,slot in [('Annuaire et références vocales',window.open_directory),('Importer un enregistrement',window.import_recording)]:
            button=QPushButton(label);button.clicked.connect(slot);actions.addWidget(button)
        self.generate=QPushButton('Générer le compte rendu');self.generate.setProperty('primary',True);self.generate.clicked.connect(window.generate_automatic)
        actions.addWidget(self.generate);layout.addLayout(actions)
        self.state=QLabel('Importez un audio pour créer une séance, ou rouvrez une séance dans la colonne de gauche.');self.state.setWordWrap(True);layout.addWidget(self.state)
        split=QSplitter();self.points=QListWidget();self.points.setWordWrap(True);self.points.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text=QTextEdit();self.text.setPlaceholderText('Le brouillon apparaîtra ici. Vous pourrez le corriger.');split.addWidget(self.points);split.addWidget(self.text);split.setSizes([260,700]);layout.addWidget(split,1)
        self.warnings=QTextEdit();self.warnings.setReadOnly(True);self.warnings.setMaximumHeight(115);self.warnings.setPlaceholderText('À vérifier');layout.addWidget(self.warnings)
        actions=QHBoxLayout()
        for label,slot in [('Enregistrer mes corrections',self.save),('Écouter les sources',self.listen),
            ('Rapport de vérification…',window.show_automatic_diagnostics)]:
            button=QPushButton(label);button.clicked.connect(slot);actions.addWidget(button)
        layout.addLayout(actions)
        exports=QHBoxLayout()
        for label,slot in [('Exporter le brouillon PDF',lambda:window.export_working('pdf')),
            ('Exporter le brouillon DOCX',lambda:window.export_working('docx')),('Relecture et validation…',window.open_review)]:
            button=QPushButton(label);button.clicked.connect(slot);exports.addWidget(button)
        layout.addLayout(exports)
        self.points.currentRowChanged.connect(self.select);self.text.textChanged.connect(self.edited)
    def edited(self):
        if not self.loading:self.dirty=True
    def load(self,state):
        self.loading=True;self.index=-1;self.dirty=False;self.points.clear();self.text.clear()
        draft=state['draft']
        if draft:
            self.points.addItems([p['title'] for p in draft['content']['points']])
            self.warnings.setPlainText('À vérifier\n'+'\n'.join(draft['content']['to_verify']))
        else:self.warnings.clear()
        self.state.setText(f"{len(state['takes'])} prise(s) conservée(s) · {len(state['utterances'])} passage(s) transcrit(s) · "+
            ('BROUILLON NON OFFICIEL — relecture requise' if draft and not draft['review'] else 'Relecture enregistrée — aucune adoption officielle automatique' if draft else 'Prêt pour la génération'))
        self.loading=False
        if self.points.count():self.points.setCurrentRow(0)
    def select(self,index):
        if self.loading:return
        self.save();self.index=index;self.loading=True
        points=self.window.draft_content['points']
        self.text.setPlainText(points[index]['summary'] if 0<=index<len(points) else '')
        self.loading=False;self.dirty=False
    def save(self):
        if self.loading or not self.dirty or self.index<0:return
        window=self.window
        window.points.setCurrentRow(self.index)
        window.point_text.setPlainText(self.text.toPlainText())
        window.save_draft();self.dirty=False
        self.state.setText('Corrections sauvegardées — BROUILLON NON OFFICIEL à relire.')
    def listen(self):
        if self.index<0:return
        window=self.window
        window.points.setCurrentRow(self.index)
        window.show_point_sources()
