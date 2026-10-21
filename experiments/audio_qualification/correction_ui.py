"""Operator-driven local repairs: immutable text, explicit actions and history."""
import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QLabel,
    QPushButton,QLineEdit,QCheckBox,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox)
from .core import QualificationError
from .wer_plan import PlanStore,load_saved_plan
from .corrections import tasks,TaskLog,read_task_log,add_reviewed_gap,carry_unchanged_plan


class CorrectionDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.setWindowTitle('Corrections ciblées · verbatims conservés');self.resize(1000,650)
        self.log=TaskLog(window.workspace/'corrections.sqlite');self.started=time.monotonic()
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Quelques vérifications ciblées. Aucun résultat moteur n’est une annotation humaine. Le texte reste inchangé.'))
        self.list=QListWidget();layout.addWidget(self.list);self.detail=QLabel();self.detail.setWordWrap(True);layout.addWidget(self.detail)
        self.list.currentRowChanged.connect(self.describe)
        self.reviewer=QLineEdit(window.reviewer.text());self.reviewer.setPlaceholderText('Votre nom');layout.addWidget(self.reviewer)
        row=QHBoxLayout()
        for title,action in [('Écouter le passage',self.listen),('Corriger le rattachement / les voix',self.edit)]:
            b=QPushButton(title);b.clicked.connect(lambda checked=False,f=action:self.safe(f));row.addWidget(b)
        layout.addLayout(row)
        self.notes=QLineEdit();self.notes.setPlaceholderText('Correction constatée ou raison de conservation ; mentionner vote/proposition si l’attribution change le sens.');layout.addWidget(self.notes)
        row=QHBoxLayout()
        self.outcome=QComboBox()
        for label,value in [('Corrigé par moi','corrected'),('Vérifié, pas de correction nécessaire','verified_unchanged'),('À revoir plus tard','deferred')]:self.outcome.addItem(label,value)
        row.addWidget(self.outcome);save=QPushButton('Consigner mon contrôle');save.clicked.connect(lambda:self.safe(self.record));row.addWidget(save);layout.addLayout(row)
        row=QHBoxLayout();self.chains={}
        for k in ('small','large','whisperx'):
            box=QCheckBox(k);self.chains[k]=box;row.addWidget(box)
        important=QPushButton('Signaler une attribution importante erronée');important.clicked.connect(lambda:self.safe(self.record_important));row.addWidget(important);layout.addLayout(row)
        layout.addWidget(QLabel('Les nombres de signalements ne sont pas des taux exhaustifs. Une absence de signalement ne prouve pas l’absence d’erreur.'))
        close=QPushButton('Fermer');close.clicked.connect(self.accept);layout.addWidget(close);self.refresh()
    def safe(self,fn):
        try:return fn()
        except (ValueError,OSError,__import__('sqlite3').Error) as e:QMessageBox.warning(self,'Correction à vérifier',str(e))
    def refresh(self):
        _,plan=load_saved_plan(self.window.project,self.window.plan_path)
        self.entries=tasks(self.window.project,self.window.dataset,plan)
        events=read_task_log(self.window.project,self.log.path);latest={e['task']['id']:e for e in events if e['outcome']!='important_attribution'}
        self.list.clear()
        for task in self.entries:
            state=latest.get(task['id'],{}).get('outcome','à vérifier')
            label={'corrected':'corrigé déclaré','verified_unchanged':'vérifié sans changement','deferred':'différé'}.get(state,state)
            item=QListWidgetItem(task['title']+' · '+label);self.list.addItem(item)
        if self.entries:self.list.setCurrentRow(0)
        else:self.detail.setText('Aucune correction ciblée préparée. Les cas non signalés ne sont pas automatiquement validés.')
    def task(self):
        i=self.list.currentRow()
        if i<0:raise QualificationError('Choisissez une vérification.')
        return self.entries[i]
    def describe(self,*args):
        if self.list.currentRow()>=0:self.detail.setText(self.task()['detail'])
    def listen(self):
        t=self.task();self.window.select_zone_id(t['zone']);self.window.seek(max(self.window.zone()['start'],t['start']-1),True)
    def edit(self):
        t=self.task();self.window.player.pause()
        if t['kind'] in ('reference','qualitative'):
            self.window.select_zone_id(t['zone']);self.window.tabs.setCurrentIndex(0 if t['kind']=='reference' else 3);self.accept();return
        if t['kind']=='wer':
            from .wer_review import WERReviewDialog
            from .wer_plan import block_payload,approved
            _,before=load_saved_plan(self.window.project,self.window.plan_path)
            d=WERReviewDialog(self.window.project,self.window.dataset,self,store=PlanStore(self.window.plan_path),
                media=self.window.media_enabled,focus=t['portion'],suggested_range=t.get('suggested_range'))
            d.exec();self.window.update_report_view()
            _,after=load_saved_plan(self.window.project,self.window.plan_path)
            if before and after:
                old={b['id']:b for b in before['blocks']}
                changed=[b for b in after['blocks'] if b['id'] in old and approved(b) and block_payload(b)!=block_payload(old[b['id']])]
                if changed:
                    refreshed=next((entry for entry in tasks(self.window.project,self.window.dataset,after) if entry['id']==t['id']),t)
                    self.log.append(self.window.project,refreshed,changed[0]['approval']['reviewer'],'corrected',time.monotonic()-self.started,'Sélection/bornes corrigées et approuvées explicitement.')
        else:
            self.window.select_zone_id(t['zone']);GapDialog(self.window,t,self.reviewer.text()).exec()
        self.started=time.monotonic()
        self.refresh()
    def record(self):
        self.log.append(self.window.project,self.task(),self.reviewer.text(),self.outcome.currentData(),time.monotonic()-self.started,self.notes.text())
        self.started=time.monotonic();self.refresh()
    def record_important(self):
        self.log.append(self.window.project,self.task(),self.reviewer.text(),'important_attribution',time.monotonic()-self.started,
            self.notes.text(),[k for k,v in self.chains.items() if v.isChecked()])
        self.started=time.monotonic();self.notes.clear()


class GapDialog(QDialog):
    def __init__(self,window,task,reviewer=''):
        super().__init__(window);self.window=window;self.task=task;self.started=time.monotonic();self.setWindowTitle('Ajouter seulement les tours manquants');self.resize(850,450)
        layout=QVBoxLayout(self);layout.addWidget(QLabel(task['detail']))
        self.reviewer=QLineEdit(reviewer);self.reviewer.setPlaceholderText('Votre nom');layout.addWidget(self.reviewer)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['Début absolu (s)','Fin absolue (s)','Voix humaine'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);layout.addWidget(self.table)
        add=QPushButton('Ajouter un tour');add.clicked.connect(self.add_row);layout.addWidget(add)
        listen=QPushButton('Écouter avec le lecteur commun');listen.clicked.connect(lambda:window.seek(task['start'],True));layout.addWidget(listen)
        self.heard=QCheckBox('J’ai écouté cette plage et vérifié les voix ajoutées. Les tours déjà revus restent exactement conservés.');layout.addWidget(self.heard)
        self.carry=QCheckBox('Je confirme aussi la conservation des validations WER dont les bornes et mots sont inchangés.');layout.addWidget(self.carry)
        save=QPushButton('Enregistrer ma correction sous une nouvelle révision');save.clicked.connect(self.apply_safe);layout.addWidget(save)
        self.add_row()
    def add_row(self):
        i=self.table.rowCount();self.table.insertRow(i)
        for j,k in enumerate(('start','end')):self.table.setItem(i,j,QTableWidgetItem(f"{self.task[k]:.3f}"))
        voices=QComboBox();voices.addItem('Choisir une voix humaine',None)
        for v in self.window.project['voices']:voices.addItem(v['name'],v['id'])
        self.table.setCellWidget(i,2,voices)
    def apply_safe(self):
        try:self.apply()
        except (ValueError,OSError,__import__('sqlite3').Error) as e:QMessageBox.warning(self,'Voix à vérifier',str(e))
    def apply(self):
        turns=[]
        for i in range(self.table.rowCount()):
            turns.append({'start':float(self.table.item(i,0).text().replace(',','.')),'end':float(self.table.item(i,1).text().replace(',','.')),
                          'speaker':self.table.cellWidget(i,2).currentData()})
        w=self.window;old=w.project
        new=add_reviewed_gap(old,self.task['zone'],self.task['start'],self.task['end'],turns,self.reviewer.text(),self.heard.isChecked())
        _,plan=load_saved_plan(old,w.plan_path);invalid=[]
        if plan is not None and self.carry.isChecked():
            carried,invalid=carry_unchanged_plan(old,new,plan,self.reviewer.text(),True,w.dataset)
            store=PlanStore(w.plan_path);parent,_=store.load(new);store.save(new,carried,parent)
        w.reviewer.setText(self.reviewer.text());w.commit(new,'Correction humaine ciblée des voix sans modifier le verbatim')
        TaskLog(w.workspace/'corrections.sqlite').append(new,self.task,self.reviewer.text(),'corrected',time.monotonic()-self.started,'Ajout explicite de tours manquants ; verbatim conservé.')
        w.fill_editor(w.zone());w.status.setText('Voix ajoutées, texte conservé. '+(f'{len(invalid)} portions WER incompatibles restent à revoir.' if invalid else 'Historique conservé.'))
        w.player.pause();self.accept()
