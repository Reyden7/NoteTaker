"""Independent import/run/open workflow, QProcess transport, no model in GUI."""
import uuid
from pathlib import Path
from PySide6.QtCore import QProcess,QProcessEnvironment,Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,
    QLineEdit,QComboBox,QPlainTextEdit,QListWidget,QListWidgetItem,QMessageBox)
from .core import ROOT,read,QualificationError
from .municipal import MUNICIPAL_ROOT


class MunicipalDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.folder=None;self.process=None;self.setWindowTitle('Test municipal indépendant');self.resize(1000,660)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Importer un conseil réel ou joué, idéalement 10–15 minutes. Aucun moteur ni résultat BFMTV n’est remplacé.'))
        self.label=QLineEdit('Qualification municipale');layout.addWidget(self.label)
        self.kind=QComboBox()
        for label,value in [('Conseil réel','real'),('Simulation jouée par plusieurs personnes','human_simulation'),('Test technique sans portée représentative','technical_test')]:self.kind.addItem(label,value)
        layout.addWidget(self.kind)
        self.device=QComboBox();self.device.addItem('A : CPU ; B / WhisperX : GPU CUDA (erreur explicite si indisponible)','cuda');self.device.addItem('Toutes les chaînes : CPU (temps potentiellement long)','cpu');layout.addWidget(self.device)
        row=QHBoxLayout()
        self.import_button=QPushButton('Importer WAV / MP3 / M4A…');self.import_button.clicked.connect(self.choose_audio);row.addWidget(self.import_button)
        self.choose_button=QPushButton('Ouvrir un projet municipal existant…');self.choose_button.clicked.connect(self.choose_folder);row.addWidget(self.choose_button);layout.addLayout(row)
        self.description=QLabel('Aucun projet choisi.');self.description.setWordWrap(True);layout.addWidget(self.description)
        self.log=QPlainTextEdit();self.log.setReadOnly(True);layout.addWidget(self.log)
        row=QHBoxLayout();self.run_button=QPushButton('Exécuter les trois chaînes · 60 s → 3 min → fichier complet');self.run_button.setEnabled(False);self.run_button.clicked.connect(lambda:self.safe(self.run));row.addWidget(self.run_button)
        self.cancel_button=QPushButton('Annuler');self.cancel_button.setEnabled(False);self.cancel_button.clicked.connect(self.cancel);row.addWidget(self.cancel_button);layout.addLayout(row)
        self.open_button=QPushButton('Ouvrir les résultats et la référence humaine');self.open_button.setEnabled(False);self.open_button.clicked.connect(lambda:self.safe(self.open_result));layout.addWidget(self.open_button)
    def safe(self,fn):
        try:return fn()
        except (ValueError,OSError) as e:QMessageBox.warning(self,'Projet à vérifier',str(e))
    def choose_audio(self):
        source,_=QFileDialog.getOpenFileName(self,'Enregistrement municipal local','','Audio (*.wav *.mp3 *.m4a)')
        if not source:return
        self.folder=MUNICIPAL_ROOT/uuid.uuid4().hex
        self.start(['import',str(self.folder),'--source',source,'--kind',self.kind.currentData(),'--label',self.label.text()])
    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Projet municipal',str(MUNICIPAL_ROOT))
        if folder:self.folder=Path(folder);self.safe(self.refresh)
    def start(self,arguments):
        if self.process is not None:raise QualificationError('Un calcul est déjà en cours.')
        p=QProcess(self);self.process=p;p.setWorkingDirectory(str(ROOT));p.setProcessChannelMode(QProcess.MergedChannels)
        env=QProcessEnvironment.systemEnvironment();env.insert('PYTHONUTF8','1');env.insert('PYTHONIOENCODING','utf-8')
        for key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN','HUGGINGFACE_TOKEN'):env.remove(key)
        p.setProcessEnvironment(env);p.readyReadStandardOutput.connect(lambda:self.log.appendPlainText(bytes(p.readAllStandardOutput()).decode('utf-8',errors='replace')))
        p.finished.connect(self.process_finished);p.errorOccurred.connect(lambda error:self.process_finished(2) if error==QProcess.FailedToStart else None)
        for b in (self.import_button,self.choose_button,self.run_button,self.open_button):b.setEnabled(False)
        self.cancel_button.setEnabled(True);p.start(str(ROOT/'.venv/Scripts/python.exe'),['-m','experiments.audio_qualification.municipal_runner',*arguments])
    def process_finished(self,code,*args):
        if self.process is None:return
        self.process.deleteLater();self.process=None;self.cancel_button.setEnabled(False);self.import_button.setEnabled(True);self.choose_button.setEnabled(True)
        if code:self.log.appendPlainText('Échec ou annulation : originaux et sorties partielles conservés. Aucun résultat n’est simulé.')
        self.safe(self.refresh)
    def refresh(self):
        if self.folder is None:return
        audio=read(self.folder/'audio.json');meta=read(self.folder/'source.json')
        self.description.setText(f"{meta['label']} · {audio['duration']:.1f} s · {self.folder}\n"+('Durée dans la cible 10–15 min.' if audio['recommended_10_to_15_minutes'] else 'Durée hors cible 10–15 min : comparaison possible, représentativité à compléter.'))
        self.run_button.setEnabled(True);self.ready=sorted(self.folder.glob('runs/*/ready.json'),key=lambda p:p.stat().st_mtime)
        self.open_button.setEnabled(bool(self.ready))
    def run(self):
        if self.folder is None:return
        cancel=self.folder/'CANCEL'
        if cancel.exists():cancel.rename(self.folder/('CANCEL-historique-'+uuid.uuid4().hex))
        self.start(['run',str(self.folder),'--device',self.device.currentData()])
    def cancel(self):
        if self.folder is not None:(self.folder/'CANCEL').write_text('Annulation explicite opérateur',encoding='utf-8')
        self.log.appendPlainText('Annulation demandée ; arrêt du processus moteur au prochain contrôle du Job Windows.')
    def open_result(self):
        self.refresh()
        if not self.ready:raise QualificationError('Les trois chaînes ne sont pas complètes.')
        project_path=Path(read(self.ready[-1])['project']);project=read(project_path)
        from .app import QualificationWindow
        if not hasattr(self.window,'municipal_windows'):self.window.municipal_windows=[]
        w=QualificationWindow(project_path.parent/'reference-humaine.sqlite',project=project,media=self.window.media_enabled)
        self.window.municipal_windows.append(w);w.show();w.raise_()
    def reject(self):
        if self.process is not None:
            QMessageBox.information(self,'Calcul en cours','Annulez puis attendez la fin du processus avant de fermer. Les sorties seront conservées.');return
        super().reject()


class SamplingDialog(QDialog):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.setWindowTitle('Quelques extraits représentatifs · aucun validé automatiquement');self.resize(1050,550)
        from .sampling import proposals
        self.entries=proposals(window.project,window.dataset)
        layout=QVBoxLayout(self);layout.addWidget(QLabel('Choisir au plus six plages, sans recouvrement. Les indices ASR « vote » / « proposition » peuvent être faux ; écoutez avant de les retenir.'))
        self.list=QListWidget();layout.addWidget(self.list)
        for p in self.entries:
            item=QListWidgetItem(f"{p['start']:.3f}–{p['end']:.3f} s · {p['title']}");item.setFlags(item.flags()|Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if p['origin']=='temporal_blind' else Qt.Unchecked);self.list.addItem(item)
        listen=QPushButton('Écouter la proposition sélectionnée');listen.clicked.connect(self.listen);layout.addWidget(listen)
        save=QPushButton('Utiliser ces extraits vierges sous une nouvelle révision');save.clicked.connect(self.apply);layout.addWidget(save)
    def listen(self):
        i=self.list.currentRow()
        if i>=0:
            # Direct seek: proposal need not be within the currently selected zone.
            w=self.window;w.preview_end=self.entries[i]['end'];w.player.setPosition(round(self.entries[i]['start']*1000))
            if w.media_enabled:w.player.play()
    def apply(self):
        from .sampling import select
        try:
            chosen=[p for i,p in enumerate(self.entries) if self.list.item(i).checkState()==Qt.Checked]
            new=select(self.window.project,chosen);self.window.commit(new,'Choix humain des extraits municipaux non annotés')
            self.window.select_zone_id(new['zones'][0]['id']);self.window.fill_editor(self.window.zone());self.accept()
        except (ValueError,OSError) as e:QMessageBox.warning(self,'Sélection à ajuster',str(e))
    def done(self,result):
        self.window.preview_end=None;self.window.player.pause();super().done(result)
