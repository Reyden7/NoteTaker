"""Standalone PySide6 audio comparison and independent human-reference editor."""
import argparse
import copy
import json
import sqlite3
import os
import math
import sys
import uuid
from pathlib import Path
# The lab plays the original PCM WAV only. Native Windows Media Foundation avoids
# the observed Qt 6.8 FFmpeg resampler failure on the default 8-channel headset.
# This setting is process-local; the production application is unchanged.
if os.name=='nt':os.environ.setdefault('QT_MEDIA_BACKEND','windows')
from PySide6.QtCore import Qt,QTimer,QUrl,QProcess,QProcessEnvironment,QRect
from PySide6.QtGui import QColor,QDesktopServices,QKeySequence,QShortcut
from PySide6.QtMultimedia import QAudioOutput,QMediaPlayer,QMediaDevices
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
    QPushButton,QCheckBox,QComboBox,QListWidget,QListWidgetItem,QSplitter,QTableWidget,
    QTableWidgetItem,QHeaderView,QPlainTextEdit,QLineEdit,QTabWidget,QSlider,QMessageBox,
    QInputDialog,QDialog,QDialogButtonBox,QDoubleSpinBox,QFormLayout,QAbstractItemView,QTextBrowser)
from .core import (ROOT,WORK,TAGS,DOMAINS,QualificationError,ReferenceStore,initial_project,
    load_dataset,verify_inputs,blank_zone,update_zone,validate_project,approve,review_valid,tokens,digest,read)
from .export import save_reference


def stamp(seconds):
    return f'{int(seconds)//60:02d}:{seconds%60:06.3f}'


class HypothesisView(QWidget):
    def __init__(self,name,seek,parent=None):
        super().__init__(parent);layout=QVBoxLayout(self);layout.setContentsMargins(4,4,4,4)
        title=QLabel(name);title.setStyleSheet('font-size:14px;font-weight:600;color:#164e63');layout.addWidget(title)
        self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels(['Temps absolu','Voix technique','Transcription'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.verticalHeader().hide();self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
        self.table.setColumnWidth(0,112);self.table.setColumnWidth(1,108)
        self.table.horizontalHeader().sectionResized.connect(lambda *args:QTimer.singleShot(0,self.fit_rows))
        self.table.cellDoubleClicked.connect(lambda row,col:seek(self.rows[row]['start'],True))
        layout.addWidget(self.table);self.rows=[];self.active=set()
    def populate(self,rows,start,end):
        self.rows=[r for r in rows if r['end']>start-2 and r['start']<end+2]
        self.table.setRowCount(len(self.rows));self.active=set()
        for i,r in enumerate(self.rows):
            flag=' ⚠' if r.get('uncertain') or r['start']==r['end'] else ''
            for j,text in enumerate([stamp(r['start'])+'\n'+stamp(r['end']),str(r.get('speaker') or 'Inconnue'),r['text']+flag]):
                item=QTableWidgetItem(text);item.setToolTip(text);self.table.setItem(i,j,item)
        self.fit_rows();QTimer.singleShot(0,self.fit_rows)
    def fit_rows(self):
        width=max(30,self.table.columnWidth(2)-12)
        for i in range(self.table.rowCount()):
            item=self.table.item(i,2)
            if item:
                height=self.table.fontMetrics().boundingRect(QRect(0,0,width,100000),Qt.TextWordWrap,item.text()).height()
                self.table.setRowHeight(i,max(48,height+16))
    def resizeEvent(self,event):
        super().resizeEvent(event);QTimer.singleShot(0,self.fit_rows)
    def position(self,seconds,follow):
        active={i for i,r in enumerate(self.rows) if r['start']<=seconds<r['end']}
        if active==self.active:return
        for i in self.active|active:
            for j in range(3):
                item=self.table.item(i,j)
                item.setBackground(QColor('#bae6fd') if i in active else QColor('transparent'))
        self.active=active
        if follow and active:self.table.scrollToItem(self.table.item(min(active),2),QAbstractItemView.PositionAtCenter)


class QualificationWindow(QMainWindow):
    def __init__(self,store_path=WORK/'reference-humaine.sqlite',*,dataset=None,project=None,media=True):
        super().__init__();self.setWindowTitle('NoteTaker · laboratoire de qualification audio')
        self.resize(1580,1000);self.store=ReferenceStore(store_path)
        self.workspace=self.store.path.parent;self.plan_path=self.workspace/'decoupages-wer.sqlite'
        self.revision,self.project=self.store.load()
        if self.project is not None and project is not None and self.project['audio']['sha256']!=project['audio']['sha256']:
            raise QualificationError('Cette référence appartient à un autre audio. Choisissez le fichier de référence propre à ce test.')
        if self.project is None:
            self.project=copy.deepcopy(project) if project is not None else initial_project()
            self.revision=self.store.save(self.project,None,'','Création : référence humaine vide')
        retained=self.store.retain_exposure(self.project)
        if retained!=self.project:
            self.revision=self.store.save(retained,self.revision,'','Conservation de l’exposition passée aux hypothèses');self.project=retained
        self.dataset=dataset if dataset is not None else load_dataset(self.project)
        self.zone_id=None;self.loading=False;self.dirty=False;self.last_report=None;self.scoring_process=None;self.last_draft_saved=False
        self.report_markdown='';self.report_reference_hash=None;self.report_plan_hash=None;self.report_operator_hash=None
        self.media_enabled=media;self.player=QMediaPlayer(self);self.audio=QAudioOutput(self)
        self.player.setAudioOutput(self.audio);self.audio.setVolume(0.65)
        self.build_ui()
        self.media_devices=QMediaDevices(self);self.media_devices.audioOutputsChanged.connect(self.refresh_outputs);self.refresh_outputs()
        self.autosave=QTimer(self);self.autosave.setSingleShot(True);self.autosave.setInterval(650);self.autosave.timeout.connect(self.save_quietly)
        self.player.positionChanged.connect(self.on_position)
        self.player.playbackStateChanged.connect(lambda state:self.play_button.setText('Pause' if state==QMediaPlayer.PlayingState else 'Écouter'))
        self.player.errorOccurred.connect(lambda *a:self.status.setText('Lecture audio impossible : '+self.player.errorString()+'. Les annotations sont conservées.'))
        if media:self.player.setSource(QUrl.fromLocalFile(self.project['audio']['path']))
        self.refresh_zones();self.zone_list.setCurrentRow(0)
        draft=self.store.recover_draft(self.revision)
        if draft:
            zone,raw=draft
            if any(z['id']==zone for z in self.project['zones']):
                self.select_zone_id(zone);self.fill_editor(raw);self.dirty=True
                self.status.setText('Saisie interrompue récupérée. Vérifiez les horaires puis enregistrez ; les dernières références validées restent conservées.')
        self.shortcut('Ctrl+S',lambda:self.try_action(self.save))
        self.shortcut('F5',self.toggle_play)
        self.shortcut('F6',lambda:self.mark_time('start'))
        self.shortcut('F7',lambda:self.mark_time('end'))
    def shortcut(self,key,callback):
        action=QShortcut(QKeySequence(key),self);action.activated.connect(callback)
    def zone(self):return next(z for z in self.project['zones'] if z['id']==self.zone_id)
    def try_action(self,callback):
        try:return callback()
        except (QualificationError,ValueError,OSError,sqlite3.Error) as e:
            QMessageBox.warning(self,'Action à corriger',str(e));return None
    def build_ui(self):
        self.setStyleSheet('''QMainWindow,QDialog{background:#f3f6fa} QWidget{font-family:Segoe UI;font-size:13px;color:#172b40}
            QPushButton{background:#e3eef6;border:1px solid #b7cbd9;border-radius:5px;padding:7px 11px}
            QPushButton:hover{background:#cce7f5} QPushButton:disabled{color:#8796a5}
            QLineEdit,QPlainTextEdit,QTableWidget,QListWidget{background:white;border:1px solid #ced8e3;border-radius:4px}
            QHeaderView::section{background:#eaf1f7;padding:5px;border:0px} QTabBar::tab{padding:8px 12px}
            QSplitter::handle{background:#dce5ed} QLabel#title{font-size:20px;font-weight:600;color:#123c55}''')
        central=QWidget();self.setCentralWidget(central);outer=QVBoxLayout(central)
        heading=QLabel('Qualifier les mots, les voix et leurs horaires');heading.setObjectName('title');outer.addWidget(heading)
        outer.addWidget(QLabel('Laboratoire indépendant · même audio et temps absolus · aucune modification des moteurs ou des séances NoteTaker'))
        bar=QHBoxLayout();self.reviewer=QLineEdit();self.reviewer.setPlaceholderText('Votre nom pour les validations humaines');bar.addWidget(self.reviewer,1)
        self.save_button=QPushButton('Enregistrer');self.save_button.clicked.connect(lambda:self.try_action(self.save));bar.addWidget(self.save_button)
        self.export_button=QPushButton('Exporter la référence');self.export_button.clicked.connect(lambda:self.try_action(self.export_reference));bar.addWidget(self.export_button)
        self.history_button=QPushButton('Historique');self.history_button.clicked.connect(lambda:self.try_action(self.show_history));bar.addWidget(self.history_button)
        self.score_button=QPushButton('Calculer la comparaison');self.score_button.clicked.connect(lambda:self.try_action(self.start_scoring));bar.addWidget(self.score_button)
        self.wer_review_button=QPushButton('WER sans horaires de mots…');self.wer_review_button.clicked.connect(lambda:self.try_action(self.review_wer_portions));bar.addWidget(self.wer_review_button)
        self.cancel_button=QPushButton('Annuler le calcul');self.cancel_button.setEnabled(False);self.cancel_button.clicked.connect(self.cancel_scoring);bar.addWidget(self.cancel_button)
        self.open_report_button=QPushButton('Ouvrir le rapport');self.open_report_button.setEnabled(False);self.open_report_button.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_report))));bar.addWidget(self.open_report_button)
        outer.addLayout(bar)
        workflow=QHBoxLayout()
        repairs=QPushButton('Corrections ciblées…');repairs.clicked.connect(lambda:self.try_action(self.open_corrections));workflow.addWidget(repairs)
        municipal=QPushButton('Nouveau test municipal / ouvrir un test…');municipal.clicked.connect(lambda:self.try_action(self.open_municipal));workflow.addWidget(municipal)
        sampling=QPushButton('Choisir quelques extraits…');sampling.setEnabled('municipal_source' in self.project);sampling.clicked.connect(lambda:self.try_action(self.open_sampling));workflow.addWidget(sampling)
        workflow.addWidget(QLabel('BFMTV reste un projet distinct. Les nouvelles références sont vierges et non validées.'));workflow.addStretch();outer.addLayout(workflow)
        middle=QSplitter();outer.addWidget(middle,1)
        left=QWidget();ll=QVBoxLayout(left);ll.setContentsMargins(0,0,4,0)
        ll.addWidget(QLabel('Zones à annoter'));self.zone_list=QListWidget();self.zone_list.currentItemChanged.connect(self.zone_changed);ll.addWidget(self.zone_list)
        bounds=QPushButton('Ajuster les limites…');bounds.clicked.connect(lambda:self.try_action(self.change_bounds));ll.addWidget(bounds)
        new=QPushButton('Ajouter une zone…');new.clicked.connect(lambda:self.try_action(self.add_zone));ll.addWidget(new)
        self.coverage=QLabel();self.coverage.setWordWrap(True);ll.addWidget(self.coverage);middle.addWidget(left)
        right=QWidget();rl=QVBoxLayout(right);rl.setContentsMargins(3,0,0,0)
        audio_bar=QHBoxLayout();self.play_button=QPushButton('Écouter');self.play_button.clicked.connect(self.toggle_play);audio_bar.addWidget(self.play_button)
        previous=QPushButton('−2 s');previous.clicked.connect(lambda:self.seek(self.player.position()/1000-2));audio_bar.addWidget(previous)
        next_button=QPushButton('+2 s');next_button.clicked.connect(lambda:self.seek(self.player.position()/1000+2));audio_bar.addWidget(next_button)
        self.clock=QLabel('00:00.000');audio_bar.addWidget(self.clock)
        self.slider=QSlider(Qt.Horizontal);self.slider.sliderMoved.connect(lambda p:self.seek(p/1000));audio_bar.addWidget(self.slider,1)
        self.speed=QComboBox()
        for text,rate in [('0,65×',.65),('0,8×',.8),('1×',1.0),('1,25×',1.25)]:self.speed.addItem(text,rate)
        self.speed.setCurrentIndex(2);self.speed.currentIndexChanged.connect(lambda:self.player.setPlaybackRate(self.speed.currentData()));audio_bar.addWidget(self.speed)
        self.loop=QCheckBox('Boucle');audio_bar.addWidget(self.loop)
        self.follow=QCheckBox('Suivre la lecture');self.follow.setChecked(True);audio_bar.addWidget(self.follow);rl.addLayout(audio_bar)
        compare_bar=QHBoxLayout();self.show_hypotheses=QCheckBox('Afficher les trois hypothèses');self.show_hypotheses.toggled.connect(self.visibility_changed);compare_bar.addWidget(self.show_hypotheses)
        compare_bar.addWidget(QLabel('Voix de la transcription affichée :'))
        self.variant=QComboBox();self.variant.addItem('Exclusive (lecture)', 'exclusive');self.variant.addItem('Standard (chevauchements)', 'standard')
        self.variant.currentIndexChanged.connect(self.populate_views);compare_bar.addWidget(self.variant)
        compare_bar.addStretch();compare_bar.addWidget(QLabel('Sortie audio :'));self.output_combo=QComboBox();self.output_combo.setMaximumWidth(240)
        self.output_combo.currentIndexChanged.connect(self.change_output);compare_bar.addWidget(self.output_combo)
        volume=QSlider(Qt.Horizontal);volume.setRange(0,100);volume.setValue(65);volume.setMaximumWidth(85);volume.setToolTip('Volume du comparateur')
        volume.valueChanged.connect(lambda value:self.audio.setVolume(value/100));compare_bar.addWidget(volume);rl.addLayout(compare_bar)
        vertical=QSplitter(Qt.Vertical);rl.addWidget(vertical,1)
        self.hypotheses_widget=QWidget();hl=QVBoxLayout(self.hypotheses_widget);hl.setContentsMargins(0,0,0,0)
        self.blind_notice=QLabel('Annotation indépendante : écoutez et saisissez d’abord la référence humaine.\nLes hypothèses sont masquées ; aucun texte de moteur ne préremplit votre référence.')
        self.blind_notice.setAlignment(Qt.AlignCenter);self.blind_notice.setMinimumHeight(110);hl.addWidget(self.blind_notice)
        self.columns=QSplitter();self.views={}
        for key,name in [('small','Small + sherpa'),('large','Large-v3 + Community-1'),('whisperx','WhisperX + Community-1')]:
            view=HypothesisView(name,self.seek);self.columns.addWidget(view);self.views[key]=view
        hl.addWidget(self.columns);self.columns.hide();vertical.addWidget(self.hypotheses_widget)
        editor=QWidget();el=QVBoxLayout(editor);el.setContentsMargins(0,3,0,0)
        voicebar=QHBoxLayout();voicebar.addWidget(QLabel('Voix humaines :'));self.voices=QComboBox();voicebar.addWidget(self.voices,1)
        add_voice=QPushButton('Ajouter une voix…');add_voice.clicked.connect(lambda:self.try_action(self.add_voice));voicebar.addWidget(add_voice)
        rename=QPushButton('Renommer…');rename.clicked.connect(lambda:self.try_action(self.rename_voice));voicebar.addWidget(rename)
        voicebar.addWidget(QLabel('Nom vérifié ou pseudonyme stable ; aucune identité déduite.'));el.addLayout(voicebar)
        self.tabs=QTabWidget();el.addWidget(self.tabs,1)
        text_page=QWidget();tl=QVBoxLayout(text_page);tl.setContentsMargins(4,4,4,4)
        self.verbatim=QPlainTextEdit();self.verbatim.setPlaceholderText('Saisissez exactement les paroles entendues, sans résumer. Aucun texte de moteur n’est importé.');self.verbatim.textChanged.connect(self.changed);tl.addWidget(self.verbatim)
        flags=QHBoxLayout();self.silence=QCheckBox('Zone entièrement silencieuse');self.silence.toggled.connect(self.changed);flags.addWidget(self.silence)
        self.unintelligible=QCheckBox('Inaudible / incomplet : ne pas noter');self.unintelligible.toggled.connect(self.changed);flags.addWidget(self.unintelligible);flags.addStretch();tl.addLayout(flags)
        self.text_heard=QCheckBox('J’ai écouté toute la zone : verbatim exhaustif, silences et paroles simultanées signalés.');tl.addWidget(self.text_heard)
        self.text_review_button=QPushButton('Valider le texte de cette zone');self.text_review_button.clicked.connect(lambda:self.try_action(lambda:self.review('text')));tl.addWidget(self.text_review_button)
        self.tabs.addTab(text_page,'1 · Verbatim humain')
        self.turn_table,self.turn_heard,self.turn_review_button=self.make_timed_tab('2 · Voix et chevauchements',False)
        self.word_table,self.word_heard,self.word_review_button=self.make_timed_tab('3 · Horaires des mots',True)
        note_page=QWidget();nl=QVBoxLayout(note_page);nl.setContentsMargins(4,4,4,4)
        tags=QHBoxLayout();self.tag_boxes={}
        for tag in TAGS:
            box=QCheckBox(tag);box.toggled.connect(self.changed);tags.addWidget(box);self.tag_boxes[tag]=box
        tags.addStretch();nl.addLayout(tags)
        line=QHBoxLayout();self.note_chain=QComboBox();self.note_chain.addItems(['commun','small','large','whisperx']);line.addWidget(self.note_chain)
        self.note_type=QComboBox();self.note_type.addItems(['transcription','attribution','alignement','nom propre','interruption','chevauchement','proposition','délibération','vote effectif','vote absent / non couvert']);line.addWidget(self.note_type)
        self.note_text=QLineEdit();self.note_text.setPlaceholderText('Écart précis constaté à l’écoute, avec le passage concerné');line.addWidget(self.note_text,1)
        add_note=QPushButton('Ajouter');add_note.clicked.connect(lambda:self.try_action(self.add_note));line.addWidget(add_note);nl.addLayout(line)
        self.notes=QPlainTextEdit();self.notes.setReadOnly(True);nl.addWidget(self.notes);self.tabs.addTab(note_page,'4 · Écarts et cas difficiles')
        self.results=QTextBrowser();self.results.setPlainText('Les scores resteront non mesurés tant que les domaines correspondants ne sont pas annotés et validés humainement.')
        self.results.setOpenLinks(False);self.results.anchorClicked.connect(self.open_result_link)
        self.tabs.addTab(self.results,'5 · Résultats de comparaison')
        self.tabs.setTabText(2,'3 · Mots horodatés (facultatif)')
        self.review_status=QLabel();self.review_status.setWordWrap(True);el.addWidget(self.review_status)
        vertical.addWidget(editor);vertical.setSizes([440,340]);middle.addWidget(right);middle.setSizes([180,1380])
        self.status=QLabel('Prêt · F5 écouter/pause · F6 début au curseur · F7 fin au curseur · Ctrl+S enregistrer');self.status.setWordWrap(True);outer.addWidget(self.status)
    def make_timed_tab(self,title,words):
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(4,4,4,4)
        layout.addWidget(QLabel('Horaires en secondes absolues. Les tours peuvent se chevaucher pour des voix distinctes.' if not words else
            'Facultatif pour WER/DER. Horodatez chaque mot à l’écoute pour mesurer l’apport de WhisperX ; aucun horaire n’est deviné.'))
        table=QTableWidget(0,4 if words else 3);table.setHorizontalHeaderLabels(['Début (s)','Fin (s)']+(['Mot'] if words else [])+['Voix humaine'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection);table.itemChanged.connect(self.changed);layout.addWidget(table)
        bar=QHBoxLayout()
        for title_,action in [('Ajouter',lambda:self.add_timed_row(words)),('Supprimer sélection',lambda:self.remove_timed_rows(table)),
                              ('Début au curseur',lambda:self.mark_time('start',table)),('Fin au curseur',lambda:self.mark_time('end',table))]:
            b=QPushButton(title_);b.clicked.connect(lambda checked=False,f=action:self.try_action(f));bar.addWidget(b)
        if words:
            split=QPushButton('Recréer depuis le verbatim');split.setToolTip('Horaires laissés vides ; ancienne liste conservée dans l’historique.');split.clicked.connect(lambda:self.try_action(self.make_words));bar.addWidget(split)
        layout.addLayout(bar)
        heard=QCheckBox('J’ai vérifié tous les horaires et auteurs des mots à l’écoute.' if words else 'J’ai écouté toute la zone et annoté toutes les voix, interruptions, silences et chevauchements.');layout.addWidget(heard)
        approve_button=QPushButton('Valider les horaires des mots' if words else 'Valider la diarisation humaine')
        approve_button.clicked.connect(lambda:self.try_action(lambda:self.review('word_times' if words else 'diarization')));layout.addWidget(approve_button)
        self.tabs.addTab(page,title);return table,heard,approve_button
    def refresh_zones(self):
        current=self.zone_id;self.zone_list.blockSignals(True);self.zone_list.clear()
        for z in self.project['zones']:
            n=sum(review_valid(z,d,self.project['audio']['sha256']) for d in DOMAINS)
            item=QListWidgetItem(f"{z['title']}  ·  {n}/3\n{stamp(z['start'])}–{stamp(z['end'])}");item.setData(Qt.UserRole,z['id']);self.zone_list.addItem(item)
            if z['id']==current:self.zone_list.setCurrentItem(item)
        self.zone_list.blockSignals(False)
        h=self.project['audio']['sha256'];text=sum(review_valid(z,'text',h) for z in self.project['zones']);diar=sum(review_valid(z,'diarization',h) for z in self.project['zones'])
        self.coverage.setText(f'{text} zones texte revues\n{diar} zones voix revues\n\nWER sans horaires humains des mots. Découpage à valider si chevauchement.\n\nLe 3e domaine mesure seulement l’alignement.')
    def refresh_outputs(self):
        current=self.audio.device().id();devices=QMediaDevices.audioOutputs();self.output_combo.blockSignals(True);self.output_combo.clear()
        for device in devices:self.output_combo.addItem(device.description(),device)
        selected=next((i for i,d in enumerate(devices) if d.id()==current),next((i for i,d in enumerate(devices) if d.isDefault()),0))
        self.output_combo.setCurrentIndex(selected);self.output_combo.blockSignals(False)
        self.play_button.setEnabled(bool(devices))
        if devices:self.audio.setDevice(devices[selected])
        else:self.status.setText('Aucune sortie audio disponible. Branchez un casque ou des haut-parleurs ; les annotations restent accessibles.')
    def change_output(self):
        device=self.output_combo.currentData()
        if device is not None:self.audio.setDevice(device)
    def select_zone_id(self,identifier):
        for i in range(self.zone_list.count()):
            if self.zone_list.item(i).data(Qt.UserRole)==identifier:self.zone_list.setCurrentRow(i);return
    def zone_changed(self,current,previous):
        if current is None:return
        target=current.data(Qt.UserRole)
        try:
            if self.zone_id and self.dirty:self.save()
        except (QualificationError,ValueError,OSError,sqlite3.Error) as e:
            self.zone_list.blockSignals(True);self.zone_list.setCurrentItem(previous);self.zone_list.blockSignals(False)
            QMessageBox.warning(self,'Saisie à compléter',str(e));return
        self.player.pause();self.zone_id=target
        self.zone_list.blockSignals(True);self.select_zone_id(target);self.zone_list.blockSignals(False)
        z=self.zone();self.fill_editor(z)
        self.slider.setRange(round(z['start']*1000),round(z['end']*1000));self.player.setPosition(round(z['start']*1000))
        if self.show_hypotheses.isChecked():self.try_action(self.expose_zone)
        self.populate_views();self.update_statuses()
    def voice_combo(self,speaker=None):
        box=QComboBox();box.addItem('À renseigner',None)
        for v in self.project['voices']:box.addItem(v['name'],v['id'])
        index=box.findData(speaker);box.setCurrentIndex(max(0,index));box.currentIndexChanged.connect(self.changed);return box
    def fill_table(self,table,rows,words):
        table.setRowCount(0)
        for row in rows:
            i=table.rowCount();table.insertRow(i)
            for j,key in enumerate(['start','end']+(['text'] if words else [])):
                value=row.get(key);table.setItem(i,j,QTableWidgetItem('' if value is None else str(value)))
            table.setCellWidget(i,3 if words else 2,self.voice_combo(row.get('speaker')))
    def fill_editor(self,z):
        self.loading=True
        self.verbatim.setPlainText(z['verbatim']);self.silence.setChecked(z['silence']);self.unintelligible.setChecked(z['unintelligible'])
        for tag,box in self.tag_boxes.items():box.setChecked(tag in z['tags'])
        self.voices.clear()
        for v in self.project['voices']:self.voices.addItem(v['name'],v['id'])
        self.fill_table(self.turn_table,z['turns'],False);self.fill_table(self.word_table,z['words'],True)
        self.notes.setPlainText('\n'.join(f"{n['chain']} / {n['type']} : {n['text']}" for n in z['notes']))
        for box in (self.text_heard,self.turn_heard,self.word_heard):box.setChecked(False)
        self.loading=False;self.dirty=False
    def raw_editor(self):
        def rows(table,words):
            result=[]
            for i in range(table.rowCount()):
                row={key:table.item(i,j).text() if table.item(i,j) else '' for j,key in enumerate(['start','end']+(['text'] if words else []))}
                row['speaker']=table.cellWidget(i,3 if words else 2).currentData();result.append(row)
            return result
        return {**copy.deepcopy(self.zone()),'verbatim':self.verbatim.toPlainText(),'silence':self.silence.isChecked(),
            'unintelligible':self.unintelligible.isChecked(),'tags':[tag for tag,box in self.tag_boxes.items() if box.isChecked()],
            'turns':rows(self.turn_table,False),'words':rows(self.word_table,True)}
    def capture(self):
        raw=self.raw_editor();self.store.save_draft(self.revision,self.zone_id,raw);self.last_draft_saved=True
        for group in ('turns','words'):
            for row in raw[group]:
                for key in ('start','end'):
                    try:row[key]=float(str(row[key]).replace(',','.')) if str(row[key]).strip() else None
                    except ValueError:raise QualificationError('Un horaire est incomplet. Saisissez des secondes, par exemple 1088,709. Votre saisie est sauvegardée pour récupération.')
        candidate=update_zone(self.zone(),**{k:raw[k] for k in ('verbatim','turns','words','silence','unintelligible','tags')})
        project=copy.deepcopy(self.project);index=next(i for i,z in enumerate(project['zones']) if z['id']==self.zone_id);project['zones'][index]=candidate
        validate_project(project);self.project=project
    def changed(self,*args):
        if self.loading or not self.zone_id:return
        self.dirty=True;self.last_draft_saved=False;self.review_status.setText('Saisie modifiée : les validations concernées seront retirées. Sauvegarde progressive…');self.autosave.start()
        self.update_report_view(force_stale=True)
    def save_quietly(self):
        try:self.save()
        except (QualificationError,ValueError,OSError,sqlite3.Error) as e:self.status.setText(str(e))
    def save(self):
        self.autosave.stop()
        if not self.dirty:return
        self.capture();self.revision=self.store.save(self.project,self.revision,self.reviewer.text(),'Modification humaine')
        self.dirty=False;self.refresh_zones();self.update_statuses();self.update_report_view();self.status.setText('Corrections enregistrées localement ; historique conservé.')
    def commit(self,project,event):
        project=self.store.retain_exposure(project)
        validate_project(project);rid=self.store.save(project,self.revision,self.reviewer.text(),event)
        previous_zone=self.zone_id;self.project=project;self.revision=rid
        if self.zone_id not in {z['id'] for z in project['zones']}:self.zone_id=project['zones'][0]['id']
        self.refresh_zones();self.update_statuses();self.update_report_view()
        if previous_zone!=self.zone_id:
            self.fill_editor(self.zone());self.slider.setRange(round(self.zone()['start']*1000),round(self.zone()['end']*1000));self.seek(self.zone()['start']);self.populate_views()
    def update_report_view(self,force_stale=False):
        if not self.report_markdown:return
        stale=force_stale or self.dirty or self.report_reference_hash!=digest(self.project)
        if not stale:
            from .wer_plan import load_saved_plan
            _,current_plan=load_saved_plan(self.project,self.plan_path)
            stale=self.report_plan_hash!=(digest(current_plan) if current_plan is not None else None)
        if not stale and self.report_operator_hash is not None:
            from .corrections import read_task_log
            stale=self.report_operator_hash!=digest(read_task_log(self.project,self.workspace/'corrections.sqlite'))
        banner='> **Rapport d’une ancienne révision. Les corrections récentes ne sont pas évaluées : relancez le calcul.**\n\n' if stale else ''
        self.results.setMarkdown(banner+self.report_markdown)
        self.open_report_button.setText('Ouvrir le rapport précédent' if stale else 'Ouvrir le rapport')
    def open_result_link(self,url):
        if not self.last_report:return
        base=self.last_report.parent.resolve()
        resolved=QUrl.fromLocalFile(str(base)+os.sep).resolved(url)
        if not resolved.isLocalFile():return  # Qualification stays offline.
        path=Path(resolved.toLocalFile()).resolve()
        if path.is_relative_to(base) and path.is_file():QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def update_statuses(self):
        if not self.zone_id:return
        z=self.zone();h=self.project['audio']['sha256'];labels={'text':'Texte','diarization':'Voix','word_times':'Alignement des mots (facultatif pour WER)'}
        self.review_status.setText(' · '.join(labels[d]+(' : revu par '+z['reviews'][d]['reviewer'] if review_valid(z,d,h) else ' : non validé') for d in DOMAINS)
            +'\n'+('Hypothèses déjà affichées pour cette zone ; exposition conservée dans la provenance.' if z['hypotheses_seen'] else 'Hypothèses non affichées dans cet outil pour cette zone.'))
    def review(self,domain):
        self.save();box={'text':self.text_heard,'diarization':self.turn_heard,'word_times':self.word_heard}[domain]
        candidate=approve(self.project,self.zone_id,domain,self.reviewer.text(),box.isChecked())
        self.commit(candidate,'Validation humaine : '+domain);box.setChecked(False)
    def expose_zone(self):
        self.save()
        if not self.zone()['hypotheses_seen']:
            candidate=copy.deepcopy(self.project);next(z for z in candidate['zones'] if z['id']==self.zone_id)['hypotheses_seen']=True
            self.commit(candidate,'Hypothèses affichées : provenance enregistrée')
    def visibility_changed(self,visible):
        if not self.zone_id:return
        if visible:
            try:self.expose_zone()
            except (QualificationError,ValueError,OSError,sqlite3.Error) as e:
                self.show_hypotheses.blockSignals(True);self.show_hypotheses.setChecked(False);self.show_hypotheses.blockSignals(False)
                QMessageBox.warning(self,'Affichage impossible',str(e));return
        self.columns.setVisible(visible);self.blind_notice.setVisible(not visible);self.populate_views()
    def populate_views(self,*args):
        if not self.zone_id or not self.show_hypotheses.isChecked():return
        z=self.zone()
        for key,view in self.views.items():view.populate(self.dataset['chains'][key][self.variant.currentData()],z['start'],z['end'])
        self.on_position(self.player.position())
    def seek(self,seconds,play=False):
        if not self.zone_id:return
        z=self.zone();seconds=max(z['start'],min(seconds,z['end']))
        self.player.setPosition(round(seconds*1000));self.on_position(round(seconds*1000))
        if play and self.media_enabled:self.player.play()
    def toggle_play(self):
        if self.player.playbackState()==QMediaPlayer.PlayingState:self.player.pause()
        else:
            if self.zone_id and (self.player.position()<round(self.zone()['start']*1000) or self.player.position()>=round(self.zone()['end']*1000)-10):self.seek(self.zone()['start'])
            if self.media_enabled:self.player.play()
    def on_position(self,position):
        seconds=position/1000;self.clock.setText(stamp(seconds));self.slider.setValue(position)
        if self.show_hypotheses.isChecked():
            for view in self.views.values():view.position(seconds,self.follow.isChecked())
        if getattr(self,'preview_end',None) is not None:
            if seconds>=self.preview_end:self.player.pause()
            return
        if self.zone_id and seconds>=self.zone()['end'] and self.player.playbackState()==QMediaPlayer.PlayingState:
            if self.loop.isChecked():self.seek(self.zone()['start'])
            else:self.player.pause()
    def add_voice(self):
        self.save();name,ok=QInputDialog.getText(self,'Voix humaine','Nom confirmé, ou pseudonyme stable (ex. Voix A) :')
        if ok and name.strip():
            candidate=copy.deepcopy(self.project);candidate['voices'].append({'id':'v'+uuid.uuid4().hex,'name':name.strip()})
            self.commit(candidate,'Ajout d’une voix humaine');self.fill_editor(self.zone())
    def rename_voice(self):
        self.save();identifier=self.voices.currentData()
        if identifier is None:raise QualificationError('Ajoutez d’abord une voix humaine.')
        voice=next(v for v in self.project['voices'] if v['id']==identifier)
        name,ok=QInputDialog.getText(self,'Nom de la voix','Nom confirmé ou pseudonyme :',text=voice['name'])
        if ok and name.strip():
            candidate=copy.deepcopy(self.project);next(v for v in candidate['voices'] if v['id']==identifier)['name']=name.strip()
            self.commit(candidate,'Correction du nom d’une voix, identifiant conservé');self.fill_editor(self.zone())
    def add_timed_row(self,words):
        if not words and not self.project['voices']:raise QualificationError('Ajoutez d’abord une voix humaine, avec un nom confirmé ou un pseudonyme.')
        table=self.word_table if words else self.turn_table;self.loading=True
        i=table.rowCount();table.insertRow(i);t=max(self.zone()['start'],min(self.player.position()/1000,self.zone()['end']-.001))
        for j,value in enumerate(['','', ''] if words else [f'{t:.3f}',f'{min(t+1,self.zone()["end"]):.3f}']):table.setItem(i,j,QTableWidgetItem(value))
        table.setCellWidget(i,3 if words else 2,self.voice_combo(self.voices.currentData()));self.loading=False;table.setCurrentCell(i,0);self.changed()
    def remove_timed_rows(self,table):
        self.loading=True
        for i in sorted({index.row() for index in table.selectedIndexes()},reverse=True):table.removeRow(i)
        self.loading=False;self.changed()
    def mark_time(self,key,table=None):
        table=table or (self.word_table if self.tabs.currentIndex()==2 else self.turn_table)
        row=table.currentRow()
        if row<0:return
        table.setItem(row,0 if key=='start' else 1,QTableWidgetItem(f'{self.player.position()/1000:.3f}'))
    def make_words(self):
        self.save();candidate=copy.deepcopy(self.project);z=next(z for z in candidate['zones'] if z['id']==self.zone_id)
        new=update_zone(z,words=[{'text':word,'start':None,'end':None,'speaker':None} for word in tokens(z['verbatim'])]);candidate['zones'][candidate['zones'].index(z)]=new
        self.commit(candidate,'Liste lexicale humaine recréée, horaires non inventés');self.fill_editor(self.zone());self.tabs.setCurrentIndex(2)
    def add_note(self):
        self.save();text=self.note_text.text().strip()
        if not text:return
        candidate=copy.deepcopy(self.project);z=next(z for z in candidate['zones'] if z['id']==self.zone_id)
        z['notes'].append({'chain':self.note_chain.currentText(),'type':self.note_type.currentText(),'text':text})
        self.commit(candidate,'Écart constaté à l’écoute');self.note_text.clear();self.fill_editor(self.zone())
    def range_dialog(self,title,start,end):
        dialog=QDialog(self);dialog.setWindowTitle(title);layout=QFormLayout(dialog)
        a,b=QDoubleSpinBox(),QDoubleSpinBox()
        for box,value in ((a,start),(b,end)):
            box.setDecimals(3);box.setRange(0,math.floor(self.project['audio']['duration']*1000)/1000);box.setValue(value);box.setSuffix(' s absolues')
        layout.addRow('Début',a);layout.addRow('Fin',b)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addRow(buttons)
        return (a.value(),b.value()) if dialog.exec()==QDialog.Accepted else None
    def change_bounds(self):
        self.save();z=self.zone();bounds=self.range_dialog('Portée réellement annotée',z['start'],z['end'])
        if bounds:
            candidate=copy.deepcopy(self.project);i=next(i for i,z in enumerate(candidate['zones']) if z['id']==self.zone_id)
            candidate['zones'][i]=update_zone(z,start=bounds[0],end=bounds[1]);self.commit(candidate,'Modification de la portée, validations retirées')
            self.fill_editor(self.zone());self.slider.setRange(round(bounds[0]*1000),round(bounds[1]*1000));self.seek(bounds[0]);self.populate_views()
    def add_zone(self):
        self.save();t=self.player.position()/1000;bounds=self.range_dialog('Nouvelle zone sans recouvrement',t,min(t+10,self.project['audio']['duration']))
        if bounds:
            identifier='Z'+uuid.uuid4().hex[:8];candidate=copy.deepcopy(self.project);candidate['zones'].append(blank_zone(identifier,*bounds))
            candidate['zones'].sort(key=lambda z:z['start']);self.commit(candidate,'Nouvelle zone humaine vide');self.select_zone_id(identifier)
    def export_reference(self):
        self.save();verify_inputs(self.project);folder=self.workspace/'references-exportees'/uuid.uuid4().hex
        save_reference(self.project,folder);self.status.setText('Référence humaine exportée avec sa provenance : '+str(folder))
        return folder
    def show_history(self):
        self.save();history=self.store.history();labels=[f'{date} · {author or "saisie"} · {event}' for rid,date,author,event in history]
        chosen,ok=QInputDialog.getItem(self,'Historique préservé','Choisir une révision à restaurer (la version actuelle reste dans l’historique) :',labels,0,False)
        if ok:
            old=self.store.snapshot(history[labels.index(chosen)][0]);verify_inputs(old);self.commit(old,'Restauration d’une révision humaine')
            self.fill_editor(self.zone());self.populate_views()
    def start_scoring(self):
        self.save();verify_inputs(self.project)
        if self.scoring_process is not None:raise QualificationError('Un calcul est déjà en cours.')
        interpreter=ROOT/'.venv-lab-b/Scripts/python.exe'
        if not interpreter.is_file():raise QualificationError('L’environnement isolé de calcul .venv-lab-b est absent. Aucun téléchargement automatique ne sera effectué.')
        from .wer_plan import prepare,load_saved_plan,approved
        _,plan=load_saved_plan(self.project,self.plan_path)
        if prepare(self.project,self.dataset)['blocks'] and not (plan and any(approved(b) for b in plan['blocks'])):
            if not self.review_wer_portions():return
            _,plan=load_saved_plan(self.project,self.plan_path)
        export=self.export_reference();self.run_folder=self.workspace/'comparaisons'/uuid.uuid4().hex
        if plan is not None:(export/'wer-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        from .corrections import read_task_log
        (export/'operator-events.json').write_text(json.dumps(read_task_log(self.project,self.workspace/'corrections.sqlite'),ensure_ascii=False,indent=2),encoding='utf-8')
        process=QProcess(self);self.scoring_process=process;process.setWorkingDirectory(str(ROOT))
        env=QProcessEnvironment.systemEnvironment();env.insert('PYTHONUTF8','1');env.remove('HF_TOKEN');env.remove('HUGGING_FACE_HUB_TOKEN');process.setProcessEnvironment(env)
        process.finished.connect(self.scoring_finished);process.errorOccurred.connect(self.scoring_error)
        self.score_button.setEnabled(False);self.cancel_button.setEnabled(True)
        arguments=['-m','experiments.audio_qualification.controller',str(export/'reference.json'),str(self.run_folder),'--variant',self.variant.currentData()]
        if plan is not None:arguments+=['--plan',str(export/'wer-plan.json')]
        arguments+=['--operator-events',str(export/'operator-events.json')]
        process.start(str(ROOT/'.venv/Scripts/python.exe'),arguments)
        self.status.setText('Calcul local dans un processus limité à 2 GiB et 120 s. Les annotations non validées seront exclues.')
    def review_wer_portions(self):
        self.save();self.player.pause()
        from .wer_review import WERReviewDialog
        from .wer_plan import PlanStore
        dialog=WERReviewDialog(self.project,self.dataset,self,store=PlanStore(self.plan_path),media=self.media_enabled)
        if not dialog.plan['blocks']:
            self.status.setText('Aucun découpage WER supplémentaire nécessaire pour les zones validées. Les horaires des mots ne sont pas requis.');return True
        accepted=dialog.exec()==QDialog.Accepted
        self.update_report_view()
        self.status.setText('Découpage WER conservé séparément ; verbatim, voix et relectures d’origine inchangés.')
        return accepted
    def open_corrections(self):
        self.save();self.player.pause()
        from .correction_ui import CorrectionDialog
        CorrectionDialog(self).exec();self.update_report_view()
    def open_municipal(self):
        self.save();self.player.pause()
        from .municipal_ui import MunicipalDialog
        MunicipalDialog(self).exec()
    def open_sampling(self):
        self.save();self.player.pause()
        from .municipal_ui import SamplingDialog
        SamplingDialog(self).exec();self.preview_end=None;self.player.pause()
    def cancel_scoring(self):
        if self.scoring_process:
            self.run_folder.mkdir(parents=True,exist_ok=True);(self.run_folder/'CANCEL').write_text('cancel',encoding='utf-8')
            self.status.setText('Annulation demandée ; référence humaine et fichiers partiels conservés.')
    def scoring_finished(self,exit_code,status):
        process=self.scoring_process;self.scoring_process=None;self.score_button.setEnabled(True);self.cancel_button.setEnabled(False)
        report=self.run_folder/'report/rapport.md'
        if exit_code==0 and report.is_file():
            self.last_report=report;self.open_report_button.setEnabled(True);self.status.setText('Comparaison enregistrée : '+str(report)+'. Les domaines non annotés restent non mesurés.')
            self.report_markdown=report.read_text(encoding='utf-8');metadata=read(report.with_name('scores.json'))
            self.report_reference_hash=metadata['reference_sha256'];self.report_plan_hash=metadata.get('wer_plan_sha256')
            self.report_operator_hash=digest(metadata['operator_review']['events']) if 'operator_review' in metadata else None
            self.update_report_view();self.tabs.setCurrentWidget(self.results)
        else:self.status.setText('Calcul interrompu ou en erreur. Référence conservée ; diagnostic : '+str(self.run_folder/'process/stderr.txt'))
        if process:process.deleteLater()
    def scoring_error(self,error):
        if self.scoring_process and error==QProcess.FailedToStart:
            message=self.scoring_process.errorString();self.scoring_finished(2,QProcess.CrashExit)
            self.status.setText('Impossible de lancer le calcul : '+message+'. La référence est conservée.')
    def closeEvent(self,event):
        try:self.save()
        except (QualificationError,ValueError,OSError,sqlite3.Error) as e:
            # The raw editor draft was saved before parsing; allow closing without
            # throwing away an incomplete numeric cell. It will be recovered.
            if not self.last_draft_saved:
                QMessageBox.critical(self,'Sauvegarde impossible','La saisie n’a pas pu être sauvegardée. La fenêtre reste ouverte pour préserver vos corrections.\n'+str(e));event.ignore();return
            self.status.setText('Saisie incomplète conservée pour récupération : '+str(e))
        self.player.stop()
        if self.scoring_process:
            self.cancel_scoring()
            if not self.scoring_process.waitForFinished(4000):self.scoring_process.kill();self.scoring_process.waitForFinished(1000)
        event.accept()


def main():
    p=argparse.ArgumentParser();p.add_argument('--store',type=Path);p.add_argument('--project',type=Path);args=p.parse_args()
    app=QApplication(sys.argv[:1]);app.setApplicationName('Qualification audio NoteTaker')
    try:
        project=read(args.project) if args.project else None
        store=args.store or (args.project.parent/'reference-humaine.sqlite' if args.project else WORK/'reference-humaine.sqlite')
        window=QualificationWindow(store,project=project)
    except (QualificationError,ValueError,OSError,sqlite3.Error) as e:
        QMessageBox.critical(None,'Ouverture du laboratoire impossible',str(e));return 2
    window.show();return app.exec()


if __name__=='__main__':raise SystemExit(main())
