"""Human validation of audio/text portions, without individual word timestamps."""
import copy
import json
import sqlite3
import sys
import uuid
from .app import stamp  # sets only this process's Windows playback backend
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QTextCursor
from PySide6.QtMultimedia import QAudioOutput,QMediaPlayer,QMediaDevices
from PySide6.QtWidgets import (QApplication,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QLineEdit,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QPlainTextEdit,QDoubleSpinBox,QCheckBox,QComboBox,QMessageBox,QSplitter,QWidget)
from .core import WORK,QualificationError,digest,load_dataset,validate_project,verify_inputs
from .wer_plan import (PlanStore,prepare,approve_block,approved,validate_plan,token_view,selection_tokens)


def readonly_reference(path=WORK/'reference-humaine.sqlite'):
    c=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:r=c.execute('SELECT r.payload,r.sha256 FROM head h JOIN revisions r ON r.id=h.revision').fetchone()
    finally:c.close()
    if not r:raise QualificationError('Aucune référence humaine enregistrée.')
    p=json.loads(r[0])
    if digest(p)!=r[1]:raise QualificationError('Référence humaine altérée ; aucun fichier modifié.')
    validate_project(p);return p


class WERReviewDialog(QDialog):
    def __init__(self,project,dataset,parent=None,store=None,media=True):
        super().__init__(parent);self.project=copy.deepcopy(project);self.dataset=dataset;self.store=store or PlanStore()
        self.revision,self.plan=self.store.load(project)
        if self.plan is None:
            self.plan=prepare(project,dataset);self.revision=self.store.save(project,self.plan,None)
        self.current=None;self.loading=False;self.dirty=False;self.media=media
        self.setWindowTitle('WER sans horaires de mots · validation du découpage');self.resize(1280,900)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio);self.audio.setVolume(.65)
        if media:self.player.setSource(QUrl.fromLocalFile(project['audio']['path']))
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('<b>Le texte et les voix d’origine restent inchangés.</b> Écoutez chaque portion puis sélectionnez ses mots dans votre verbatim.'))
        layout.addWidget(QLabel('Seules les portions validées seront notées. Les vrais chevauchements restent exclus du WER séquentiel ; les silences et trous de couverture restent visibles.'))
        header=QHBoxLayout();self.reviewer=QLineEdit();self.reviewer.setPlaceholderText('Votre nom pour valider le découpage');header.addWidget(self.reviewer)
        self.output=QComboBox()
        for d in QMediaDevices.audioOutputs():self.output.addItem(d.description(),d)
        default=next((i for i in range(self.output.count()) if self.output.itemData(i).isDefault()),0);self.output.setCurrentIndex(default)
        self.output.currentIndexChanged.connect(self.set_output);self.set_output();header.addWidget(self.output);layout.addLayout(header)
        splitter=QSplitter(Qt.Vertical);layout.addWidget(splitter,1)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['Portion','Temps absolu','Durée','Couverture humaine','Validation WER'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.table.currentCellChanged.connect(self.change_row);splitter.addWidget(self.table)
        editor=QWidget();el=QVBoxLayout(editor);self.explanation=QLabel();self.explanation.setWordWrap(True);el.addWidget(self.explanation)
        controls=QHBoxLayout();self.start=QDoubleSpinBox();self.end=QDoubleSpinBox()
        for box in (self.start,self.end):box.setDecimals(3);box.setRange(0,project['audio']['duration']);box.valueChanged.connect(self.changed)
        controls.addWidget(QLabel('Début (s)'));controls.addWidget(self.start);controls.addWidget(QLabel('Fin (s)'));controls.addWidget(self.end)
        listen=QPushButton('Écouter cette portion');listen.clicked.connect(self.listen);controls.addWidget(listen)
        pause=QPushButton('Pause');pause.clicked.connect(self.player.pause);controls.addWidget(pause)
        back=QPushButton('−2 s');back.clicked.connect(lambda:self.player.setPosition(max(round(self.start.value()*1000),self.player.position()-2000)));controls.addWidget(back)
        self.clock=QLabel();controls.addWidget(self.clock);self.speed=QComboBox()
        for label,speed in [('1×',1),('0,8×',.8),('0,65×',.65)]:self.speed.addItem(label,speed)
        self.speed.currentIndexChanged.connect(lambda:self.player.setPlaybackRate(self.speed.currentData()));controls.addWidget(self.speed);el.addLayout(controls)
        self.player.positionChanged.connect(self.position);self.player.errorOccurred.connect(lambda *a:self.explanation.setText('Lecture impossible : '+self.player.errorString()+'. Les références sont conservées.'))
        self.full_text=QPlainTextEdit();self.full_text.setReadOnly(True);self.full_text.setMinimumHeight(150);el.addWidget(self.full_text)
        select=QPushButton('Utiliser les mots sélectionnés du verbatim humain');select.clicked.connect(lambda:self.safe(self.select_text));el.addWidget(select)
        self.snippet=QPlainTextEdit();self.snippet.setReadOnly(True);self.snippet.setMaximumHeight(85);el.addWidget(self.snippet)
        flags=QHBoxLayout();self.classification=QComboBox();self.classification.addItem('Parole séquentielle','sequential');self.classification.addItem('Silence vérifié','silence');self.classification.currentIndexChanged.connect(self.class_changed);flags.addWidget(self.classification)
        self.heard=QCheckBox('J’ai écouté : bornes, absence de voix simultanées et mots sélectionnés sont exacts.');flags.addWidget(self.heard);el.addLayout(flags)
        actions=QHBoxLayout();save=QPushButton('Conserver comme proposition');save.clicked.connect(lambda:self.safe(self.save_pending));actions.addWidget(save)
        self.approve_button=QPushButton('Valider cette portion pour le WER');self.approve_button.clicked.connect(lambda:self.safe(self.validate_current));actions.addWidget(self.approve_button)
        split=QPushButton('Scinder au curseur audio');split.clicked.connect(lambda:self.safe(self.split_current));actions.addWidget(split);el.addLayout(actions)
        splitter.addWidget(editor);splitter.setSizes([250,580])
        bottom=QHBoxLayout();self.status=QLabel();self.status.setWordWrap(True);bottom.addWidget(self.status,1)
        self.calculate=QPushButton('Calculer les portions validées');self.calculate.clicked.connect(lambda:self.safe(self.accept));bottom.addWidget(self.calculate)
        close=QPushButton('Fermer sans calcul');close.clicked.connect(lambda:self.safe(self.reject));bottom.addWidget(close);layout.addLayout(bottom)
        self.fill_table();self.table.setCurrentCell(0,0)
    def safe(self,fn):
        try:return fn()
        except (QualificationError,ValueError,OSError,sqlite3.Error) as e:QMessageBox.warning(self,'Découpage à vérifier',str(e))
    def block(self):return next(b for b in self.plan['blocks'] if b['id']==self.current)
    def zone(self):return next(z for z in self.project['zones'] if z['id']==self.block()['zone'])
    def set_output(self):
        if self.output.currentData() is not None:self.audio.setDevice(self.output.currentData())
    def fill_table(self):
        self.table.blockSignals(True);self.table.setRowCount(len(self.plan['blocks']))
        for i,b in enumerate(self.plan['blocks']):
            for j,value in enumerate([b['id'],stamp(b['start'])+'–'+stamp(b['end']),f"{b['end']-b['start']:.3f} s",
                'Absente / à vérifier' if b['kind']=='uncovered' else 'Parole humaine séquentielle',
                'Validée par '+b['approval']['reviewer'] if approved(b) else 'À valider']):self.table.setItem(i,j,QTableWidgetItem(value))
            if b['id']==self.current:self.table.setCurrentCell(i,0)
        self.table.blockSignals(False);n=sum(approved(b) for b in self.plan['blocks']);self.calculate.setEnabled(n>0)
        self.status.setText(f'{n} portions validées. Les propositions utilisent les mots humains existants ; aucune annotation d’origine n’est modifiée.')
    def change_row(self,row,*args):
        if row<0:return
        target=self.plan['blocks'][row]['id']
        try:
            if self.current and self.dirty:self.save_pending()
        except (QualificationError,ValueError,OSError,sqlite3.Error) as e:
            self.fill_table();QMessageBox.warning(self,'Bornes à corriger',str(e));return
        self.current=target;self.load_fields()
    def load_fields(self):
        self.loading=True;b=self.block();z=self.zone();self.start.setValue(b['start']);self.end.setValue(b['end'])
        self.full_text.setPlainText(token_view(z['verbatim'])[0]);self.classification.setCurrentIndex(self.classification.findData(b['classification']))
        self.first,self.last=b['first_token'],b['last_token'];self.update_selection();self.heard.setChecked(False)
        self.explanation.setText('⚠ Plage sans tour de parole humain : il faut confirmer à l’écoute s’il s’agit de silence ou de parole séquentielle. La validation WER ne nomme aucune voix.' if b['kind']=='uncovered' else
            'Proposition de rattachement guidée par l’ASR, NON validée. Vérifiez à l’écoute et ajustez les mots sélectionnés si nécessaire. Aucun horaire de chaque mot n’est demandé.')
        self.player.pause();self.player.setPosition(round(b['start']*1000));self.loading=False;self.dirty=False
    def update_selection(self):
        view,spans=token_view(self.zone()['verbatim']);text=''
        if self.last>self.first:
            a,b=spans[self.first][0],spans[self.last-1][1];text=view[a:b]
            cursor=self.full_text.textCursor();cursor.setPosition(len(view[:a].encode('utf-16-le'))//2)
            cursor.setPosition(len(view[:b].encode('utf-16-le'))//2,QTextCursor.KeepAnchor);self.full_text.setTextCursor(cursor)
        self.snippet.setPlainText(text)
    def select_text(self):
        cursor=self.full_text.textCursor();view=self.full_text.toPlainText();encoded=view.encode('utf-16-le')
        a=len(encoded[:cursor.selectionStart()*2].decode('utf-16-le'));b=len(encoded[:cursor.selectionEnd()*2].decode('utf-16-le'))
        self.first,self.last=selection_tokens(self.zone()['verbatim'],a,b);self.update_selection();self.changed()
    def changed(self,*args):
        if not self.loading:self.dirty=True;self.heard.setChecked(False);self.status.setText('Modification du découpage : validation à refaire pour cette portion uniquement.')
    def class_changed(self):
        if not self.loading and self.classification.currentData()=='silence':self.first=self.last=0;self.update_selection()
        self.changed()
    def candidate(self):
        result=copy.deepcopy(self.plan);b=next(b for b in result['blocks'] if b['id']==self.current)
        if self.dirty:b.update(start=self.start.value(),end=self.end.value(),first_token=self.first,last_token=self.last,classification=self.classification.currentData(),approval=None)
        return result
    def persist(self,value):
        self.revision=self.store.save(self.project,value,self.revision);self.plan=value;self.dirty=False;self.fill_table()
    def save_pending(self):
        if self.current and self.dirty:self.persist(self.candidate())
    def validate_current(self):
        candidate=approve_block(self.project,self.candidate(),self.current,self.reviewer.text(),self.heard.isChecked())
        self.persist(candidate);self.heard.setChecked(False)
    def split_current(self):
        self.save_pending();point=self.player.position()/1000;b=self.block()
        if not b['start']<point<b['end']:raise QualificationError('Placez le curseur audio à l’intérieur de cette portion.')
        from .wer_plan import suggest_tokens
        result=copy.deepcopy(self.plan);index=next(i for i,r in enumerate(result['blocks']) if r['id']==self.current);new=[]
        for a,end in ((b['start'],point),(point,b['end'])):
            first,last=suggest_tokens(self.zone(),a,end,self.dataset['chains']['large'])
            new.append({**b,'id':b['id']+'-'+uuid.uuid4().hex[:4],'start':a,'end':end,'first_token':first,'last_token':last,'approval':None})
        result['blocks'][index:index+1]=new;self.current=new[0]['id'];self.persist(result);self.load_fields()
    def listen(self):
        if self.media:self.player.setPosition(round(self.start.value()*1000));self.player.play()
    def position(self,p):
        self.clock.setText(stamp(p/1000))
        if p>=round(self.end.value()*1000):self.player.pause()
    def accept(self):
        self.save_pending()
        if not any(approved(b) for b in self.plan['blocks']):raise QualificationError('Validez au moins une portion à l’écoute avant le calcul. Les propositions seules ne produisent pas de WER.')
        self.player.stop();super().accept()
    def reject(self):
        self.save_pending();self.player.stop();super().reject()


def main():
    app=QApplication(sys.argv[:1]);p=readonly_reference();verify_inputs(p)
    dialog=WERReviewDialog(p,load_dataset(p));dialog.exec()


if __name__=='__main__':main()
