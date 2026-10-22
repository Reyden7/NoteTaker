"""Optional enrollment and explicit legal authorization; disabled by default."""
import threading
from datetime import date,timedelta
from PySide6.QtCore import QThread,Signal,QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLineEdit,QCheckBox,QPushButton,QLabel,
    QDialogButtonBox,QSpinBox,QDoubleSpinBox,QMessageBox,QComboBox,QListWidget,QFileDialog)
from notetaker.services.voice_profiles import VoiceProfiles,enroll
from notetaker.services.voice_capture import EncryptedVoiceCapture,import_voice
from notetaker.services.recording import input_devices
from notetaker.infrastructure.paths import ModelPaths


def info(text):
    label=QLabel(text);label.setWordWrap(True);return label


class VoicePolicyDialog(QDialog):
    def __init__(self,root,parent=None):
        super().__init__(parent);self.vault=VoiceProfiles(root)
        self.setWindowTitle('Identification vocale facultative — autorisation');self.resize(650,600)
        layout=QVBoxLayout(self)
        layout.addWidget(info('L’identification par empreinte vocale est désactivée par défaut. '
            'Le cadre juridique doit avoir été validé par la collectivité avec son DPO avant toute collecte. '
            'Ce formulaire enregistre une décision externe ; il ne valide pas la licéité du traitement. '
            'Le compte Windows courant pourra ouvrir le coffre chiffré.'))
        policy=self.vault.policy();self.enabled=QCheckBox('La collectivité autorise ce traitement et mon accès à ce coffre')
        self.enabled.setChecked(policy.get('enabled',False));layout.addWidget(self.enabled)
        form=QFormLayout();self.fields={}
        for key,title,default in [('legal_reference','Référence de la décision / dossier DPO',''),('authorized_by','Responsable habilité',''),
            ('expires','Autorisation valable jusqu’au (AAAA-MM-JJ)',(date.today()+timedelta(days=365)).isoformat()),
            ('calibration_reference','Référence des essais de calibration (vide = aucune identification)','')]:
            value=QLineEdit(str(policy.get(key,default)));self.fields[key]=value;form.addRow(title,value)
        self.retention=QSpinBox();self.retention.setRange(1,3650);self.retention.setValue(policy.get('retention_days',90));form.addRow('Conservation des prises (jours, à décider)',self.retention)
        self.threshold=QDoubleSpinBox();self.threshold.setRange(.01,1);self.threshold.setSingleStep(.01);self.threshold.setValue(policy.get('threshold',.8));form.addRow('Seuil cosinus (non calibré par défaut)',self.threshold)
        self.margin=QDoubleSpinBox();self.margin.setRange(.01,1);self.margin.setSingleStep(.01);self.margin.setValue(policy.get('margin',.12));form.addRow('Marge minimale entre candidats',self.margin)
        layout.addLayout(form);layout.addWidget(info('Un score n’est pas une probabilité. Renseigner une référence de calibration exige des essais réels indépendants ; aucune précision n’est garantie par ces valeurs. '
            'Sans activation, l’annuaire civil et le compte rendu restent utilisables avec des voix non identifiées.'))
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def save(self):
        try:
            self.vault.configure({k:v.text().strip() for k,v in self.fields.items()}|{'enabled':self.enabled.isChecked(),
                'retention_days':self.retention.value(),'threshold':self.threshold.value(),'margin':self.margin.value()})
            self.accept()
        except Exception as error: QMessageBox.warning(self,'Autorisation non enregistrée',str(error))


class EnrollmentTask(QThread):
    done=Signal(object);failed=Signal(str)
    def __init__(self,vault,sid,parent):
        super().__init__(parent);self.vault,self.sid=vault,sid;self.cancel=threading.Event()
    def run(self):
        try:self.done.emit(enroll(self.vault,self.sid,ModelPaths(),self.cancel))
        except Exception as error:self.failed.emit(str(error))


class VoiceEnrollmentDialog(QDialog):
    def __init__(self,root,person,parent=None):
        super().__init__(parent);self.vault=VoiceProfiles(root);self.person=person;self.capture=None;self.task=None
        self.setWindowTitle('Références vocales — '+person['first_name']+' '+person['last_name']);self.resize(700,640)
        layout=QVBoxLayout(self)
        layout.addWidget(info('Faites plusieurs prises si nécessaire, seul dans une pièce calme. Parlez naturellement 30 à 60 secondes. '
            'Réécoutez et vérifiez l’identité avant extraction. Ne pas lire les données d’autres personnes.'))
        layout.addWidget(info('Texte proposé : « Bonjour. Nous sommes réunis pour examiner les projets de notre commune. '
            'Je vais présenter les différentes étapes, préciser les questions qui restent ouvertes et écouter les observations. '
            'Chaque proposition sera discutée avant toute décision. Nous souhaitons que les explications soient claires et accessibles à tous. » '
            'Continuez ensuite quelques phrases libres sur un sujet neutre.'))
        self.microphone=QComboBox();layout.addWidget(self.microphone)
        try:
            for device in input_devices():self.microphone.addItem(device['name'],device['id'])
        except Exception:pass
        self.status=info('Aucune prise en cours. Les références sont chiffrées pour ce compte Windows.');layout.addWidget(self.status)
        self.samples=QListWidget();layout.addWidget(self.samples);self.rows=[]
        for title,slot in [('Enregistrer au microphone',self.start),('Arrêter et conserver la prise',self.stop),
            ('Importer une prise WAV, MP3 ou M4A',self.import_file),('Réécouter la prise sélectionnée',self.listen),
            ('J’ai vérifié cette voix — extraire les empreintes',self.extract),('Supprimer la prise sélectionnée',self.delete),
            ('Supprimer toutes les références de cette personne',self.delete_all)]:
            button=QPushButton(title);button.clicked.connect(slot);layout.addWidget(button)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(200)
        close=QDialogButtonBox(QDialogButtonBox.Close);close.rejected.connect(self.reject);layout.addWidget(close)
        self.refresh()
        try:self.vault.require_authorization()
        except ValueError:self.status.setText('Identification désactivée : la suppression reste disponible ; capture, écoute et extraction sont bloquées.')
    def refresh(self):
        self.rows=self.vault.samples(self.person['id']);self.samples.clear()
        for row in self.rows:self.samples.addItem(row['created']+' — '+{'ready':'Empreintes techniques, précision non qualifiée','pending':'À écouter / extraire','capturing':'Prise interrompue ou en cours'}.get(row['state'],row['state'])+' — fin de conservation '+row['expires'])
        if self.rows:self.samples.setCurrentRow(len(self.rows)-1)
    def selected(self):
        index=self.samples.currentRow()
        if index<0:raise ValueError('Sélectionnez une prise.')
        return self.rows[index]['id']
    def action(self,function):
        if self.task or self.capture: self.status.setText('Arrêtez la capture ou attendez le traitement en cours.');return
        try:function()
        except Exception as error:self.status.setText(str(error))
    def start(self):
        def execute():
            self.vault.require_authorization()
            if self.microphone.currentData() is None:raise ValueError('Aucun microphone disponible.')
            import sounddevice as sd
            sd.stop()
            capture=EncryptedVoiceCapture(self.vault,self.person['id'])
            capture.start(self.microphone.currentData());self.capture=capture;self.microphone.setEnabled(False)
        self.action(execute)
    def stop(self):
        if self.capture:
            try:
                self.capture.stop();self.status.setText(self.capture.error or 'Prise chiffrée conservée : réécoutez puis extrayez les références.')
                self.capture=None;self.microphone.setEnabled(True);self.refresh()
            except Exception as error:self.status.setText(str(error))
    def tick(self):
        if self.capture:
            self.status.setText(f'Prise vocale : {self.capture.frames/16000:.1f} s — sauvegarde chiffrée progressive')
            if self.capture.error:self.stop()
    def import_file(self):
        def execute():
            self.vault.require_authorization()
            path,_=QFileDialog.getOpenFileName(self,'Importer une prise','','Audio (*.wav *.mp3 *.m4a)')
            if path:import_voice(self.vault,self.person['id'],path);self.refresh()
        self.action(execute)
    def listen(self):
        def execute():
            import sounddevice as sd
            import numpy as np
            sd.play(np.frombuffer(self.vault.pcm(self.selected()),dtype='<i2'),16000)
            self.status.setText('Écoute en mémoire, sans WAV temporaire en clair.')
        self.action(execute)
    def extract(self):
        def execute():
            if QMessageBox.question(self,'Confirmer la référence','Avez-vous réécouté cette prise et vérifié qu’une seule personne, celle de cette fiche, parle ?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
            self.task=EnrollmentTask(self.vault,self.selected(),self)
            self.task.done.connect(lambda result:self.status.setText(f"Empreintes CPU conservées ; {result['speech_seconds']:.1f} s exploitables. Précision nominative non mesurée."))
            self.task.failed.connect(self.status.setText);self.task.finished.connect(self.finished_task)
            self.status.setText('Contrôle des silences, saturation, chevauchements et voix ; extraction CPU…');self.task.start()
        self.action(execute)
    def finished_task(self):
        task=self.task;self.task=None;task.deleteLater();self.refresh()
    def delete(self):
        self.action(lambda:(self.vault.delete(self.person['id'],self.selected()),self.refresh()))
    def delete_all(self):
        def execute():
            if QMessageBox.question(self,'Supprimer les références','Supprimer toutes les prises et empreintes locales de cette personne ?',QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
                self.vault.delete(self.person['id']);self.refresh()
        self.action(execute)
    def reject(self):
        if self.task:
            self.task.cancel.set();self.status.setText('Annulation demandée. Attendez la fin du contrôle CPU avant de fermer.');return
        self.stop()
        if self.capture:return
        import sounddevice as sd
        sd.stop();super().reject()
    def closeEvent(self,event):
        if self.task or self.capture:
            self.reject();event.ignore();return
        self.reject();event.accept()
