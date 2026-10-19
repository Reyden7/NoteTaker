"""Find and repair evidence explicitly; no automatic bypass of reference checks."""
import copy
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTextEdit,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QPushButton,QComboBox,QMessageBox,QListWidget)
from notetaker.services.evidence import draft_issues, render_claims


def stamp(ms):
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}'


def text_label(text):
    widget=QLabel(text);widget.setWordWrap(True);return widget


def table(headers):
    widget=QTableWidget(0,len(headers));widget.setHorizontalHeaderLabels(headers)
    widget.setSelectionBehavior(QAbstractItemView.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SingleSelection)
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    widget.verticalHeader().hide()
    return widget


class NarrativeSources(QDialog):
    """Sentence-to-claim-to-quote navigation, including nonconsecutive audio."""
    def __init__(self,point,state,play,parent=None,stop=None):
        super().__init__(parent)
        self.point=point;self.state=state;self.play=play;self.stop=stop or (lambda:None)
        self.setWindowTitle('Traçabilité du paragraphe');self.resize(1050,740)
        layout=QVBoxLayout(self)
        layout.addWidget(text_label('Sélectionnez une phrase puis un extrait. Une citation présente ne prouve pas à elle seule que la reformulation, son auteur ou le rapprochement sont fidèles. Vérifiez à l’écoute.'))
        self.sentences=QListWidget();self.sentences.setWordWrap(True)
        for i,row in enumerate(point['narrative']):self.sentences.addItem(f"{i+1}. {row['text']}")
        layout.addWidget(self.sentences,2)
        self.sources=table(['Passage audio','Intervenant','Citation exacte'])
        self.sources.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(self.sources,2)
        self.context=QTextEdit();self.context.setReadOnly(True);self.context.setMaximumHeight(150);layout.addWidget(self.context)
        actions=QHBoxLayout();listen=QPushButton('Écouter cet extrait');listen.clicked.connect(self.listen);actions.addWidget(listen)
        stop_button=QPushButton('Arrêter l’écoute');stop_button.clicked.connect(self.stop);actions.addWidget(stop_button)
        close=QPushButton('Fermer');close.clicked.connect(self.close);actions.addWidget(close);layout.addLayout(actions)
        self.sentences.currentRowChanged.connect(self.choose_sentence);self.sources.itemSelectionChanged.connect(self.choose_source)
        self.sources.cellDoubleClicked.connect(lambda *args:self.listen())
        self.finished.connect(lambda *args:self.stop())
        self.sentences.setCurrentRow(0)

    def choose_sentence(self,index):
        if index<0:return
        selected=set(self.point['narrative'][index]['claim_ids'])
        by_id={u['id']:u for u in self.state['utterances']}
        rows=[];seen=set()
        for c in self.point.get('claims',[]):
            if c['id'] not in selected:continue
            for e in c['evidence']:
                if (e['id'],e['quote']) not in seen:rows.append(e);seen.add((e['id'],e['quote']))
        self.sources.blockSignals(True);self.sources.setRowCount(len(rows))
        for i,e in enumerate(rows):
            u=by_id.get(e['id'])
            for j,text in enumerate([stamp(u['start_ms'])+'–'+stamp(u['end_ms']) if u else 'Source absente',
                self.state['speakers'].get(u['speaker_id'],'Voix inconnue') if u else 'À corriger',e['quote']]):
                item=QTableWidgetItem(text);item.setData(Qt.UserRole,e['id']);item.setToolTip(e['id']+'\n'+text);self.sources.setItem(i,j,item)
        self.sources.blockSignals(False);self.context.clear()
        if rows:self.sources.selectRow(0);self.choose_source()

    def choose_source(self):
        row=self.sources.currentRow()
        if row<0:return
        uid=self.sources.item(row,0).data(Qt.UserRole)
        source=next((u for u in self.state['utterances'] if u['id']==uid),None)
        self.context.setPlainText(source['text'] if source else 'Le passage source est absent. Corrigez le lien avant de relire ce document.')

    def listen(self):
        row=self.sources.currentRow()
        if row>=0:self.play(self.sources.item(row,0).data(Qt.UserRole))


class SourcePicker(QDialog):
    def __init__(self,state,parent=None):
        super().__init__(parent)
        self.state=state;self.chosen=None
        self.setWindowTitle('Rattacher à un passage de transcription');self.resize(950,650)
        layout=QVBoxLayout(self)
        layout.addWidget(text_label('Choisissez le passage, puis conservez uniquement la citation exacte qui justifie l’affirmation.'))
        self.search=QLineEdit(placeholderText='Rechercher dans le texte ou les noms…');layout.addWidget(self.search)
        self.sources=table(['Horodatage','Intervenant','Texte'])
        self.sources.setEditTriggers(QAbstractItemView.NoEditTriggers);layout.addWidget(self.sources,1)
        self.quote=QTextEdit();self.quote.setMaximumHeight(150);layout.addWidget(self.quote)
        self.feedback=text_label('La citation doit rester présente dans le passage choisi.');layout.addWidget(self.feedback)
        apply=QPushButton('Utiliser cet extrait');apply.clicked.connect(self.use_source);layout.addWidget(apply)
        self.search.textChanged.connect(self.refresh)
        self.sources.itemSelectionChanged.connect(self.select_source)
        self.refresh()

    def refresh(self):
        q=self.search.text().casefold()
        rows=[u for u in self.state['utterances'] if q in (u['text']+' '+self.state['speakers'].get(u['speaker_id'],'Voix inconnue')).casefold()]
        self.sources.blockSignals(True);self.sources.setRowCount(len(rows))
        for i,u in enumerate(rows):
            for j,t in enumerate([stamp(u['start_ms']),self.state['speakers'].get(u['speaker_id'],'Voix inconnue'),u['text']]):
                item=QTableWidgetItem(t);item.setData(Qt.UserRole,u['id']);item.setToolTip(u['id']+'\n'+u['text']);self.sources.setItem(i,j,item)
        self.sources.blockSignals(False)
        self.quote.clear()

    def select_source(self):
        row=self.sources.currentRow()
        if row>=0:self.quote.setPlainText(self.sources.item(row,2).text())

    def use_source(self):
        from notetaker.engines.hierarchical_summary import normalized
        row=self.sources.currentRow()
        if row<0:return
        quote=self.quote.toPlainText().strip()
        if not quote or normalized(quote) not in normalized(self.sources.item(row,2).text()):
            self.feedback.setText('Cet extrait ne correspond pas au texte du passage. Copiez une citation exacte.');return
        self.chosen={'id':self.sources.item(row,0).data(Qt.UserRole),'quote':quote};self.accept()


class ClaimEditor(QDialog):
    def __init__(self,point,index,state,parent=None):
        super().__init__(parent)
        self.point=copy.deepcopy(point);self.index=index;self.state=state;self.result_point=point
        claim=self.point['claims'][index]
        self.setWindowTitle('Corriger une affirmation et ses sources');self.resize(1000,810)
        layout=QVBoxLayout(self)
        layout.addWidget(text_label(f"{point['title']} — affirmation {index+1}\nLe texte du point sera recomposé à partir des affirmations après prévisualisation. La révision antérieure reste conservée."))
        self.prose=QTextEdit(claim['text']);self.prose.setMaximumHeight(120);layout.addWidget(self.prose)
        controls=QHBoxLayout();self.kind=QComboBox()
        for code,label in [('context','Contexte'),('position','Position'),('argument','Argument'),('proposal','Proposition'),('question','Question'),('reported_action','Action rapportée à confirmer'),('reported_decision','Décision rapportée à confirmer')]:self.kind.addItem(label,code)
        self.kind.setCurrentIndex(max(0,self.kind.findData(claim['kind'])))
        self.speaker=QComboBox();self.speaker.addItem('Voix inconnue','unattributed')
        for key,name in state['speakers'].items():self.speaker.addItem(name,key)
        if self.speaker.findData(claim['speaker'])<0:self.speaker.addItem('Ancienne attribution — à corriger',claim['speaker'])
        self.speaker.setCurrentIndex(self.speaker.findData(claim['speaker']))
        controls.addWidget(self.kind);controls.addWidget(self.speaker,1);layout.addLayout(controls)
        self.evidence=table(['Source','Citation exacte'])
        self.evidence.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
        self.evidence.setRowCount(len(claim.get('evidence',[])))
        for i,e in enumerate(claim.get('evidence',[])):self.put_evidence(i,e)
        layout.addWidget(self.evidence,1)
        actions=QHBoxLayout()
        for label,slot in [('Ajouter une source…',lambda:self.choose_source(False)),('Remplacer la source…',lambda:self.choose_source(True)),('Retirer la source',self.remove_source),('Utiliser la voix des sources',self.use_source_voice)]:
            b=QPushButton(label);b.clicked.connect(slot);actions.addWidget(b)
        layout.addLayout(actions)
        self.feedback=text_label('Contrôlez les citations, la personne et le sens complet à l’écoute.');layout.addWidget(self.feedback)
        self.preview=QTextEdit();self.preview.setReadOnly(True);self.preview.setMaximumHeight(180);layout.addWidget(self.preview)
        buttons=QHBoxLayout()
        check=QPushButton('Prévisualiser et contrôler');check.clicked.connect(self.check);buttons.addWidget(check)
        self.apply=QPushButton('Appliquer cette correction');self.apply.setEnabled(False);self.apply.clicked.connect(self.commit);buttons.addWidget(self.apply)
        delete=QPushButton('Supprimer l’affirmation…');delete.clicked.connect(self.remove_claim);buttons.addWidget(delete)
        cancel=QPushButton('Annuler');cancel.clicked.connect(self.reject);buttons.addWidget(cancel);layout.addLayout(buttons)
        self.prose.textChanged.connect(self.changed);self.kind.currentIndexChanged.connect(self.changed)
        self.speaker.currentIndexChanged.connect(self.changed);self.evidence.itemChanged.connect(self.changed)

    def changed(self,*args):self.apply.setEnabled(False)

    def put_evidence(self,row,e):
        u=next((u for u in self.state['utterances'] if u['id']==e['id']),None)
        caption=(stamp(u['start_ms'])+' — '+self.state['speakers'].get(u['speaker_id'],'Voix inconnue')) if u else 'Source absente'
        item=QTableWidgetItem(caption);item.setData(Qt.UserRole,e['id']);item.setToolTip(e['id']);item.setFlags(item.flags()&~Qt.ItemIsEditable)
        self.evidence.setItem(row,0,item);self.evidence.setItem(row,1,QTableWidgetItem(e['quote']))

    def choose_source(self,replace):
        row=self.evidence.currentRow()
        if replace and row<0:return
        picker=SourcePicker(self.state,self)
        if picker.exec()==QDialog.Accepted:
            if not replace:row=self.evidence.rowCount();self.evidence.insertRow(row)
            self.put_evidence(row,picker.chosen);self.changed()

    def remove_source(self):
        if self.evidence.currentRow()>=0:self.evidence.removeRow(self.evidence.currentRow());self.changed()

    def candidate(self):
        p=copy.deepcopy(self.point)
        c=p['claims'][self.index]
        c.update(text=self.prose.toPlainText().strip(),kind=self.kind.currentData(),speaker=self.speaker.currentData(),
            evidence=[{'id':self.evidence.item(r,0).data(Qt.UserRole),'quote':self.evidence.item(r,1).text()} for r in range(self.evidence.rowCount())],
            machine_verdict='human_edited_requires_review')
        p['sources']=list(dict.fromkeys(e['id'] for claim in p['claims'] for e in claim.get('evidence',[])))
        p['summary']=render_claims(p['claims'],self.state)
        if 'narrative' in p:
            from notetaker.domain.summary import manual_narrative
            manual_narrative(p,p['summary'].replace('\n\n',' '))
        return p

    def use_source_voice(self):
        ids={self.evidence.item(r,0).data(Qt.UserRole) for r in range(self.evidence.rowCount())}
        refs=[u for u in self.state['utterances'] if u['id'] in ids]
        voices={u['speaker_id'] for u in refs}
        if len(refs)!=len(ids) or len(voices)!=1 or None in voices:
            self.feedback.setText('Les sources sont absentes, inconnues ou attribuées à plusieurs voix. Corrigez les citations ou séparez les affirmations.');return
        self.speaker.setCurrentIndex(self.speaker.findData(next(iter(voices))))

    def check(self):
        p=self.candidate();issues=draft_issues({'points':[p]},self.state)
        self.preview.setPlainText(p['summary'])
        self.apply.setEnabled(not issues)
        self.feedback.setText('\n'.join(dict.fromkeys(i['message'] for i in issues)) if issues else 'Sources cohérentes. Relisez la prévisualisation avant d’appliquer ; la relecture finale reste obligatoire.')

    def commit(self):
        p=self.candidate()
        if draft_issues({'points':[p]},self.state):self.check();return
        self.result_point=p;self.accept()

    def remove_claim(self):
        if QMessageBox.question(self,'Supprimer cette affirmation','Retirer cette affirmation et recomposer le point avec celles qui restent ? Le dernier retrait supprime le point. L’ancienne révision reste conservée.',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        p=copy.deepcopy(self.point);p['claims'].pop(self.index)
        if p['claims']:
            p['sources']=list(dict.fromkeys(e['id'] for c in p['claims'] for e in c.get('evidence',[])))
            p['summary']=render_claims(p['claims'],self.state);self.result_point=p
            if 'narrative' in p:
                from notetaker.domain.summary import manual_narrative
                manual_narrative(p,p['summary'].replace('\n\n',' '))
        else:self.result_point=None
        self.accept()


class EvidenceDiagnostics(QDialog):
    def __init__(self,issues,state,edit,focus,play,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Sources à corriger avant la relecture');self.resize(1100,590)
        self.issues=issues
        layout=QVBoxLayout(self)
        layout.addWidget(text_label('La relecture et l’export restent bloqués. Ouvrez le point ou l’affirmation indiquée pour corriger le lien, la citation ou l’attribution.'))
        self.table=table(['Point','Affirmation','Source','Cause'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setRowCount(len(issues))
        for row,i in enumerate(issues):
            for col,text in enumerate([f"{i['point_index']+1}. {i['point_title']}",i['claim_text'] or 'Références du point',str(i['source_id'] or '—'),i['message']]):
                item=QTableWidgetItem(text);item.setToolTip(text);self.table.setItem(row,col,item)
        layout.addWidget(self.table,1)
        self.details=QTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(120);layout.addWidget(self.details)
        def selected():return issues[max(0,self.table.currentRow())]
        actions=QHBoxLayout()
        def open_point():
            i=selected();focus(i['point_index']);self.close()
        def open_claim():
            i=selected();self.close();edit(i['point_index'],i['claim_index'])
        for title,callback in [('Ouvrir le point',open_point),('Corriger l’affirmation…',open_claim),('Écouter la source',lambda:play(selected()['source_id'])),('Fermer',self.close)]:
            b=QPushButton(title);b.clicked.connect(callback);actions.addWidget(b)
        layout.addLayout(actions)
        def detail():
            i=selected()
            self.details.setPlainText(i['message']+'\nAffirmation : '+str(i['claim_id'] or 'point entier')+'\nSource : '+str(i['source_id'] or 'aucune')+
                '\nIntervenant déclaré : '+state['speakers'].get(i['expected_speaker'],str(i['expected_speaker'] or '—'))+
                '\nIntervenant actuel de la source : '+state['speakers'].get(i['actual_speaker'],str(i['actual_speaker'] or '—')))
        self.table.itemSelectionChanged.connect(detail)
        if issues:self.table.selectRow(0);detail()
