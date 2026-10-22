"""Reviewable source ledger; no information approval implies document approval."""
import copy
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QLabel,QLineEdit,QComboBox,
    QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QTextEdit,QFormLayout,
    QTabWidget,QInputDialog,QDialog,QDialogButtonBox,QProgressBar,QScrollArea)
from PySide6.QtGui import QColor
from notetaker.domain.information_registry import TYPES,RELATIONS,admissible,coverage,ambiguous_origin
from notetaker.services.information_registry import RegistryService
from notetaker.services.registry_workflow import approval_blockers,preparation_report
from notetaker.ui.evidence import SourcePicker,stamp

STATUS={'supported':'Soutien IA provisoire','ambiguous':'Ambiguë','insufficient':'Sources insuffisantes',
        'rejected':'Refusée par les contrôles','pending':'À vérifier'}
AUTHOR={'confirmed':'Attribution confirmée','automatic':'Voix automatique','uncertain':'Attribution incertaine','unknown':'Auteur inconnu'}
REASONS={'not_analyzed':'Passage non encore analysé','no_candidate_citation':'Aucune citation exploitable rattachée à ce passage',
    'source_remainder_not_interpreted':'Texte source non représenté par une citation',
    'no_unique_exact_quote_for_speaker':'Citation non retrouvée pour cette voix',
    'contextual_entailment_rejected':'Sens, modalité, auteur ou relation non soutenu',
    'source_classification_disagrees':'Le classement du propos est incertain',
    'human_edit_requires_approval':'Correction à approuver explicitement','subject_unresolved':'Sujet à classer',
    'internal_voice_alias_in_content':'Un code de voix interne a été introduit dans le contenu',
    'unsupported_proper_name':'Un nom propre n’est pas soutenu par les citations',
    'unsupported_political_identity':'Une identité ou affiliation politique est absente des sources',
    'anecdote_or_description_changed_to_proposal':'Une description ou une anecdote est transformée en proposition',
    'question_changed_to_assertion':'Une question est transformée en affirmation',
    'reported_opinion_assigned_to_reporting_voice':'Un avis cité est attribué à la personne qui le rapporte',
    'financial_scope_requires_literal_source':'La portée du montant doit être vérifiée et la clause financière reprise exactement',
    'listener_actor_changed_to_patient':'La personne qui agit est confondue avec celle qui subit l’action',
    'source_snapshot_changed_requires_review':'Les sources ou leurs attributions ont changé ; contrôler la version actuelle',
    'operator_requested_verification':'Une personne a demandé une nouvelle vérification ; l’information est retirée de la rédaction automatique',
    'decision_not_explicit':'La décision n’est pas explicite dans la source',
    'vote_or_adoption_requires_operator':'Un résultat de vote ou une adoption exige une saisie humaine distincte',
    'greeting_not_substantive':'Formule de présentation sans information substantielle',
    'verbatim_transcription_not_a_summary':'La note copie une longue transcription ; reformuler sans déformer le sens',
    'source_is_not_information':'Ce passage est une source conservée, pas une fiche à approuver. Ouvrez ses informations liées ou créez une fiche distincte.',
    'missing_evidence':'Ajoutez une citation exacte depuis un passage source.',
    'missing_source':'Le passage cité n’existe plus dans la transcription courante.',
    'quote_not_in_source':'La citation n’est pas retrouvée mot pour mot dans le passage. Corrigez ou rattachez la citation.',
    'mixed_or_wrong_speaker':'Les citations ne correspondent pas au même intervenant. Séparez les informations ou corrigez leurs sources.',
    'source_time_changed':'Les horaires sources ont changé ; rattachez la citation à la transcription actuelle.',
    'source_interval_empty':'Ce fragment n’a pas de durée audio exploitable. Choisissez une source correctement horodatée.',
    'unknown_source_voice':'Attribuez d’abord cette voix dans la transcription, sans deviner son identité.',
    'ambiguous_source_occurrence':'La citation se répète. Choisissez explicitement son passage source.',
    'missing_content':'Rédigez une formulation fidèle avant de l’approuver.'}


def push(text,slot):
    b=QPushButton(text);b.clicked.connect(slot);return b


class RegistryPage(QWidget):
    changed=Signal()

    def __init__(self,store,prepare,write,play,error,before_change=lambda:None,parent=None,play_snapshot=None,verify=None):
        super().__init__(parent);self.store=store;self.service=RegistryService(store)
        self.prepare_callback=prepare;self.write_callback=write;self.play_callback=play
        self.error=error;self.before_change=before_change;self.sid=None;self.current=None;self.entry=None
        self.play_snapshot=play_snapshot
        self.verify_callback=verify
        self._loading_editor=False
        layout=QVBoxLayout(self)
        self.guide=QLabel();self.guide.setWordWrap(True);layout.addWidget(self.guide)
        self.workflow_progress=QProgressBar();self.workflow_progress.setRange(0,6);self.workflow_progress.setTextVisible(False);layout.addWidget(self.workflow_progress)
        actions=QHBoxLayout();actions.addWidget(push('Initialiser sans IA',self.initialize))
        self.prepare_button=push('Préparer / reprendre le registre',prepare);actions.addWidget(self.prepare_button)
        self.write_button=push('Rédiger depuis ce registre',write);actions.addWidget(self.write_button)
        actions.addWidget(push('Historique du registre',self.history));actions.addWidget(push('Bilan de préparation',self.show_preparation_report));layout.addLayout(actions)
        self.banner=QLabel('Aucun registre. La transcription et les anciens documents sont conservés.');self.banner.setWordWrap(True);layout.addWidget(self.banner)
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Rechercher un sujet, une information, un intervenant…')
        self.filter=QComboBox()
        for label,key in [('Toutes les informations','all'),('Propositions à vérifier','proposed'),('À corriger / rattacher','corrections'),('À vérifier — informations','review'),('Admissibles à la rédaction','eligible'),('Approuvées humainement','approved'),('Exclues','excluded'),('Passages sources uniquement','sources'),('Propositions antérieures conservées','previous'),('Non rédigées','unwritten')]:self.filter.addItem(label,key)
        filters.addWidget(self.search,1);filters.addWidget(self.filter);layout.addLayout(filters)
        split=QSplitter();self.rows=QTableWidget(0,4);self.rows.setHorizontalHeaderLabels(['Horaire','Sujet / type','Auteur / état','Information'])
        self.rows.setEditTriggers(QAbstractItemView.NoEditTriggers);self.rows.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rows.setSelectionMode(QAbstractItemView.SingleSelection);self.rows.setWordWrap(True)
        self.rows.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch)
        for col,width in [(0,75),(1,135),(2,160)]:self.rows.setColumnWidth(col,width)
        self.rows.verticalHeader().setDefaultSectionSize(70);split.addWidget(self.rows)
        panel=QWidget();right=QVBoxLayout(panel)
        self.category=QLabel();self.category.setWordWrap(True);right.addWidget(self.category)
        source_navigation=QHBoxLayout()
        self.linked_button=push('Voir les informations liées',self.show_linked);source_navigation.addWidget(self.linked_button)
        self.create_button=push('Créer une fiche depuis ce passage',self.start_information);source_navigation.addWidget(self.create_button)
        right.addLayout(source_navigation)
        right.addWidget(push('Écouter la citation sélectionnée',self.listen))
        self.action_hint=QLabel();self.action_hint.setWordWrap(True);right.addWidget(self.action_hint)
        self.detail_tabs=QTabWidget()
        detail_scroll=QScrollArea();detail_scroll.setWidgetResizable(True);detail_scroll.setWidget(self.detail_tabs)
        right.addWidget(detail_scroll,1)
        detail=QWidget();form=QFormLayout(detail)
        self.subject=QLineEdit();self.kind=QComboBox()
        for key,title in TYPES.items():self.kind.addItem(title,key)
        self.discourse=QComboBox()
        for label,key in [('Propos direct','own'),('Question','question'),('Avis cité ou critiqué','reported'),('Récit personnel','anecdote')]:self.discourse.addItem(label,key)
        self.content=QTextEdit();self.content.setMinimumHeight(110);self.author=QLabel();self.author.setWordWrap(True)
        self.reason=QTextEdit();self.reason.setReadOnly(True);self.reason.setMinimumHeight(90);self.reason.setMaximumHeight(130)
        form.addRow('Sujet',self.subject);form.addRow('Type',self.kind);form.addRow('Nature',self.discourse)
        form.addRow(self.author);form.addRow('Contenu attribué',self.content);form.addRow('Diagnostic',self.reason)
        self.verify_button=push('Demander un contrôle Qwen de cette fiche',self.verify_selected);form.addRow(self.verify_button)
        self.detail_tabs.addTab(detail,'Information')
        sources=QWidget();sl=QVBoxLayout(sources)
        sl.addWidget(QLabel('Les citations doivent rester exactes. Les horaires sont ceux des segments, pas des mots.'))
        self.sources=QTableWidget(0,2);self.sources.setHorizontalHeaderLabels(['Passage','Citation exacte — modifiable'])
        self.sources.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.sources.setWordWrap(True);sl.addWidget(self.sources)
        source_actions=QHBoxLayout();source_actions.addWidget(push('Ajouter une source…',self.add_source));source_actions.addWidget(push('Retirer ce lien',self.remove_source))
        source_actions.addWidget(push('Écouter',self.listen));sl.addLayout(source_actions)
        self.context=QTextEdit();self.context.setReadOnly(True);sl.addWidget(self.context,1)
        self.detail_tabs.addTab(sources,'Sources et contexte')
        relation_page=QWidget();rl=QVBoxLayout(relation_page);self.relations=QTableWidget(0,3)
        self.relations.setHorizontalHeaderLabels(['Relation','Information liée','État'])
        self.relations.setEditTriggers(QAbstractItemView.NoEditTriggers);self.relations.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.relations.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);rl.addWidget(self.relations)
        ra=QHBoxLayout();ra.addWidget(push('Ajouter un lien…',self.add_relation));ra.addWidget(push('Confirmer le lien',lambda:self.review_relation(False)))
        ra.addWidget(push('Écarter le lien',lambda:self.review_relation(True)));rl.addLayout(ra)
        self.entry_history=QTextEdit();self.entry_history.setReadOnly(True);rl.addWidget(self.entry_history)
        self.detail_tabs.addTab(relation_page,'Relations et historique')
        identity=QFormLayout();self.actor=QLineEdit();self.actor.setPlaceholderText('Nom de la personne qui vérifie')
        self.justification=QLineEdit();self.justification.setPlaceholderText('Motif de cette modification ou de cette vérification')
        identity.addRow('Opérateur',self.actor);identity.addRow('Motif',self.justification);right.addLayout(identity)
        edit_actions=QHBoxLayout();self.save_button=push('Enregistrer la correction',lambda:self.apply('edit'));edit_actions.addWidget(self.save_button)
        self.approve_button=push('Approuver cette information',lambda:self.apply('approve'));edit_actions.addWidget(self.approve_button);right.addLayout(edit_actions)
        exclude_actions=QHBoxLayout();exclude_actions.addWidget(push('Exclure avec motif',lambda:self.apply('exclude')))
        exclude_actions.addWidget(push('Remettre à vérifier',lambda:self.apply('reopen')))
        exclude_actions.addWidget(push('Annuler la saisie',self.discard_changes));right.addLayout(exclude_actions)
        note=QLabel('Approuver une information ne valide pas le compte rendu. Les décisions et votes restent à saisir et vérifier séparément.');note.setWordWrap(True);right.addWidget(note)
        self.detail_tabs.setMinimumHeight(450)
        split.addWidget(panel);split.setSizes([570,700]);layout.addWidget(split,1)
        self.search.textChanged.connect(self.populate);self.filter.currentIndexChanged.connect(self.populate)
        self.rows.itemSelectionChanged.connect(self.select);self.sources.itemSelectionChanged.connect(self.show_context)
        self.rows.cellDoubleClicked.connect(lambda *a:self.listen())
        self.subject.textChanged.connect(self.update_actions);self.content.textChanged.connect(self.update_actions)
        self.kind.currentIndexChanged.connect(self.update_actions);self.discourse.currentIndexChanged.connect(self.update_actions)
        self.sources.itemChanged.connect(self.update_actions)

    def initialize(self):
        if not self.sid:return
        try:
            self.before_change();self.service.initialize(self.sid);self.changed.emit();self.load(self.sid)
            if not any(e['category']=='information' for e in self.current['content']['entries']):
                self.filter.setCurrentIndex(self.filter.findData('sources'))
                self.banner.setText(self.banner.text()+' Sélectionnez un passage, rédigez son information puis enregistrez la correction pour créer une fiche distincte.')
        except Exception as error:self.error(error)

    def load(self,sid,force=False):
        if not force and self.editor_changed():
            self.banner.setText('Modifications non enregistrées : enregistrez la correction ou utilisez « Annuler la saisie ».');return
        self.sid=sid;self.state=self.store.get(sid);self.current=self.service.latest(sid);self.entry=None
        if self.current:
            c=coverage(self.current['content'])
            phase=self.current['content']['processing'].get('status','seeded')
            phase_label={'seeded':'Inventaire créé, analyse à lancer','interrupted':'Analyse interrompue, résultats partiels conservés',
                'partial':'Analyse partielle','extracting':'Extraction partielle','extracted':'Extraction terminée, classement à reprendre',
                'partial_extraction':'Certains lots sont extraits ; poursuivre la préparation',
                'ready_for_review':'Préparation terminée, vérification humaine disponible'}.get(phase,phase)
            report=preparation_report(self.current['content'],self.state)
            self.banner.setText(('REGISTRE OBSOLÈTE : reprenez la préparation.\n' if self.current['stale'] else '')+
                f"Révision {self.current['revision']} · {c['source_segments']} passages sources · {report['active_information_entries']} fiches actuelles · "
                f"{report['previous_information_entries']} propositions antérieures conservées. "+phase_label+'.')
        else:self.banner.setText('Aucun registre. Préparez-le avant la rédaction ; les documents existants restent conservés.')
        self.update_guide()
        self.populate()

    def update_guide(self):
        if not self.current:
            self.guide.setText('3/6 — Transcription disponible : préparez le registre pour obtenir des fiches sourcées.');self.workflow_progress.setValue(2)
            self.write_button.setEnabled(False);return
        if self.current['stale']:
            self.guide.setText('3/6 — La transcription ou les voix ont changé. Reprenez la préparation ; les fiches et révisions antérieures sont conservées.')
            self.workflow_progress.setValue(2);self.write_button.setEnabled(False);return
        report=preparation_report(self.current['content'],self.state)
        ready=report['ready_to_write'] if not self.current['stale'] else 0
        self.write_button.setEnabled(bool(ready))
        self.write_button.setToolTip('Rédiger les informations admissibles ; le document restera à relire.' if ready else
            'Vérifiez une information proposée et sa citation, corrigez les blocages, puis approuvez-la. Aucun contrôle de source n’est contourné.')
        draft=self.state.get('draft')
        final=bool(draft and draft['content'].get('information_registry',{}).get('revision_id')==self.current['id'])
        step=6 if final else 5 if ready else 4 if report['proposed_information_entries'] or report['blocked_information_entries'] else 3
        messages={3:'Préparer automatiquement les fiches ; les passages originaux restent séparés.',
            4:'Écouter et vérifier les propositions. Corriger les fiches signalées, puis approuver explicitement celles qui sont fidèles.',
            5:'Des informations sont admissibles. Vous pouvez rédiger ; les éléments non retenus resteront consultables.',
            6:'Relire et corriger le projet, puis confirmer la relecture avant tout export.'}
        self.guide.setText(f"{step}/6 — {messages[step]}\n{report['proposed_information_entries']} propositions à vérifier · "
            f"{report['blocked_information_entries']} à corriger / rattacher · {report['approved_information_entries']} approuvées · {ready} admissibles.")
        self.workflow_progress.setValue(step-1)

    def preparation_complete(self,result):
        self.entry=None;self.load(self.sid,force=True)
        self.search.clear()
        self.filter.setCurrentIndex(self.filter.findData('proposed' if result.get('proposed_information_entries',0) else 'corrections'))
        self.populate()
        self.banner.setText(self.banner.text()+f"\nCette préparation a créé {result.get('created_information_entries',0)} fiche(s) distincte(s). "
            'Les sources et les anciennes propositions restent conservées. Aucun avis Qwen ne vaut validation humaine.')

    def show_preparation_report(self):
        if not self.current:return
        report=preparation_report(self.current['content'],self.state)
        last=self.current['content']['processing'].get('preparation_report',{})
        lines=[f"Passages originaux conservés : {len(self.current['content']['sources'])}",
            f"Fiches créées lors de la dernière préparation : {last.get('created_information_entries','non enregistré pour cette ancienne révision')}",
            f"Unités examinées : {report['inspected_units']}/{report['total_units']}",
            f"Propositions à vérifier : {report['proposed_information_entries']}",
            f"Fiches à corriger / rattacher : {report['blocked_information_entries']}",
            f"Passages sans citation exploitable rattachée : {report['sources_without_usable_citation']}",
            '\nBlocages actuels :']
        lines.extend(f"{n} — {REASONS.get(code,code)}" for code,n in report['approval_blockers'].items())
        lines.append('\nMotifs des passages sources sans citation rattachée (avis du moteur, à examiner) :')
        for e in self.current['content']['entries']:
            if e['category']=='source' and not e.get('candidate_ids'):
                lines.append(stamp(e['evidence'][0]['start_ms'])+' — '+e.get('inspection',{}).get('reason','Passage non examiné'))
        lines.append('\nLes citations rattachées ne prouvent pas la fidélité du sens ni la couverture du débat. Aucune approbation humaine automatique.')
        dialog=QDialog(self);dialog.setWindowTitle('Bilan de préparation du registre');dialog.resize(850,620)
        layout=QVBoxLayout(dialog);view=QTextEdit();view.setReadOnly(True);view.setPlainText('\n'.join(lines));layout.addWidget(view)
        close=QDialogButtonBox(QDialogButtonBox.Close);close.button(QDialogButtonBox.Close).setText('Fermer')
        close.rejected.connect(dialog.reject);layout.addWidget(close);dialog.exec()

    def update_actions(self,*args):
        if self._loading_editor:return
        e=self.entry
        raw=bool(e and e['category']=='source')
        self.linked_button.setVisible(raw);self.create_button.setVisible(raw)
        blockers=approval_blockers(e,self.state) if e else []
        dirty=self.editor_changed()
        self.approve_button.setEnabled(bool(e and not raw and not blockers and not dirty and not self.current['stale']))
        self.verify_button.setEnabled(bool(e and not raw and e['evidence'] and not dirty and not self.current['stale']))
        self.save_button.setEnabled(bool(e and (not raw or dirty) and not self.current['stale']))
        if raw:self.action_hint.setText(REASONS['source_is_not_information'])
        elif not e:self.action_hint.setText('Sélectionnez une information proposée, ou un passage dans la vue Sources.')
        elif dirty:self.action_hint.setText('Enregistrez la correction et ses citations avant le contrôle ou l’approbation.')
        elif blockers:self.action_hint.setText('Approbation bloquée : '+ ' '.join(REASONS.get(v,v) for v in blockers))
        else:self.action_hint.setText('Vérifiez le sens et l’auteur à l’écoute, renseignez votre nom et le motif, puis approuvez explicitement. Le projet final restera à relire.')

    def start_information(self):
        if not self.entry or self.entry['category']!='source':return
        self.subject.clear();self.content.clear();self.discourse.setCurrentIndex(self.discourse.findData('own'))
        self.detail_tabs.setCurrentIndex(0);self.content.setFocus()
        self.action_hint.setText('Rédigez une information et son sujet. Ajustez la citation dans Sources et contexte, puis enregistrez : le passage original sera conservé séparément.')

    def show_linked(self):
        if not self.entry:return
        uid=self.entry['evidence'][0]['id']
        candidates=[e for e in self.current['content']['entries'] if e['category']=='information' and
            (any(r['id']==uid for r in e['evidence']) or uid in e.get('origin',{}).get('unit_source_ids',[]))]
        if not candidates:
            self.action_hint.setText('Aucune fiche liée. Préparez le registre ou créez une information depuis ce passage.');return
        if len(candidates)>1:
            labels=[e['subject']+' — '+e['content'][:100]+' ['+e['id'][:8]+']' for e in candidates]
            label,ok=QInputDialog.getItem(self,'Informations liées au passage','Choisir la fiche proposée :',labels,0,False)
            if not ok:return
            target=candidates[labels.index(label)]
        else:target=candidates[0]
        self.focus_entry(target['id'])

    def populate(self,*args):
        if self.editor_changed():
            self.banner.setText('Enregistrez la correction ou annulez la saisie avant de filtrer les fiches.');return
        self.rows.setRowCount(0);self.entry=None
        if not self.current:return
        document=self.current['content'];query=self.search.text().casefold();mode=self.filter.currentData()
        unwritten=set(document['writing'].get('not_written_information_ids',[]));used=set(document['writing'].get('used_information_ids',[]))
        self.visible=[]
        for entry in document['entries']:
            raw=entry['category']=='source';blockers=approval_blockers(entry,self.state) if not raw else []
            eligible=admissible(entry,self.state) and not blockers and not self.current['stale']
            if mode=='sources' and not raw:continue
            if mode!='sources' and raw:continue
            if mode=='previous' and not entry.get('previous_extraction'):continue
            if mode not in {'all','previous','sources'} and entry.get('previous_extraction'):continue
            if mode=='proposed' and (entry['human_status']!='pending' or blockers):continue
            if mode=='corrections' and (entry['human_status']=='excluded' or not blockers):continue
            if mode=='review' and (entry['human_status']=='excluded' or (raw and not entry.get('unrepresented_text',entry['content'])) or (not raw and eligible and entry['id'] not in unwritten)):continue
            if mode=='eligible' and not eligible:continue
            if mode=='approved' and entry['human_status']!='approved':continue
            if mode=='excluded' and entry['human_status']!='excluded':continue
            if mode=='unwritten' and entry['id'] not in unwritten:continue
            name=document['speakers'].get(entry['speaker'],'Intervenant inconnu')
            if query not in (entry['id']+' '+entry['subject']+' '+entry['content']+' '+name).casefold():continue
            self.visible.append(entry);row=self.rows.rowCount();self.rows.insertRow(row)
            status='Exclue' if entry['human_status']=='excluded' else 'Approuvée — document à relire' if entry['human_status']=='approved' else STATUS[entry['verification']]
            if raw:status='Source intégrale — '+('exclue de l’examen' if entry['human_status']=='excluded' else 'texte à examiner' if entry['verification']=='pending' else 'citations repérées')
            elif blockers:status='Correction nécessaire — '+status
            elif entry['human_status']=='pending':status=('Proposée par l’IA' if entry.get('origin') else 'Fiche opérateur')+' — '+status
            if entry['id'] in unwritten:status+=' · non rédigée'
            if entry.get('previous_extraction'):status='Proposition antérieure conservée — '+status
            start=min((r['start_ms'] for r in entry['evidence']),default=None)
            for col,text in enumerate([stamp(start) if start is not None else 'À rattacher',('Passage source conservé' if raw else entry['subject']+'\n'+TYPES[entry['type']]),name+'\n'+status,entry['content']]):
                item=QTableWidgetItem(text);item.setToolTip(text)
                item.setBackground(QColor('#eef1f5' if raw else '#e5f4eb' if entry['human_status']=='approved' else '#fff0df' if blockers else '#edf4ff'))
                self.rows.setItem(row,col,item)
        if self.visible:self.rows.selectRow(0)
        else:
            self.subject.clear();self.content.clear();self.reason.clear();self.author.clear();self.context.clear()
            self.sources.setRowCount(0);self.relations.setRowCount(0);self.entry_history.clear()
            self.category.setText('Aucune fiche dans cette vue');self.update_actions()

    def select(self):
        if self.editor_changed():
            previous=next((i for i,e in enumerate(self.visible) if e['id']==self.entry['id']),None)
            if previous is not None:
                blocked=self.rows.blockSignals(True);self.rows.selectRow(previous);self.rows.blockSignals(blocked)
            self.banner.setText('Enregistrez la correction ou annulez la saisie avant de changer de fiche.');return
        row=self.rows.currentRow()
        if row<0 or row>=len(getattr(self,'visible',[])):return
        self.entry=self.visible[row];e=self.entry
        self._loading_editor=True
        self.category.setText('PASSAGE SOURCE CONSERVÉ — créez ou ouvrez une information distincte' if e['category']=='source' else
            'INFORMATION VÉRIFIÉE PAR UN OPÉRATEUR' if e['human_status']=='approved' else 'INFORMATION PROPOSÉE — validation humaine requise')
        self.subject.setText(e['subject']);self.kind.setCurrentIndex(max(0,self.kind.findData(e['type'])))
        self.subject.setCursorPosition(0)
        self.discourse.setCurrentIndex(max(0,self.discourse.findData(e.get('discourse','own'))));self.content.setPlainText(e['content'])
        self.author.setText(self.current['content']['speakers'].get(e['speaker'],'Intervenant inconnu')+' — '+AUTHOR[e['author_status']])
        details=[REASONS.get(r,r) for r in e['reasons']]
        if e['author_status'] in {'uncertain','unknown'}:
            details.append('Attribution source incertaine ou inconnue : écouter et corriger la transcription si nécessaire. Aucun nom ne peut être déduit automatiquement.')
        if e['category']=='information' and e['verification']=='pending' and not e['reasons']:
            details.append('Cette proposition n’a pas reçu de contrôle de sens. Demandez un contrôle Qwen ou vérifiez le propos et son contexte à l’audio avant approbation.')
        if ambiguous_origin(e,{'utterances':self.current['content']['sources']}):details.append('La citation apparaît plusieurs fois dans le tour d’origine. Choisir explicitement les bons segments avant approbation.')
        verdicts={'supported':'étayé selon le moteur','contradicted':'contradit par la source','not_explicit':'non explicite','uncertain':'incertain'}
        axes={'meaning':'Sens','modality':'Modalité','attribution':'Attribution','relation':'Relation'}
        details.extend(axes.get(axis,axis)+' : '+verdicts.get(value,value) for axis,value in e.get('checks',{}).items())
        if e.get('advisory'):
            details.append('Avis Qwen consultatif : le choix opérateur et la nécessité de relecture restent conservés.')
            details.extend(axes.get(axis,axis)+' : '+verdicts.get(value,value) for axis,value in e['advisory']['checks'].items())
            if e['advisory'].get('static_reason'):details.append(REASONS.get(e['advisory']['static_reason'],e['advisory']['static_reason']))
        if e.get('inspection'):details.append('Avis d’extraction : '+e['inspection']['reason'])
        if e.get('origin') and not e['evidence']:details.append('Citation proposée non retrouvée : '+e['origin']['raw_candidate']['quote'])
        parent_id=e.get('origin',{}).get('alternative_of')
        if parent_id:
            original=next((v for v in self.current['content']['entries'] if v['id']==parent_id),None)
            if original:details.append('Variante contrôlée séparément. Proposition initiale conservée : '+original['content']+
                '\nMotif initial : '+ ' ; '.join(REASONS.get(r,r) for r in original['reasons']))
        if e.get('unrepresented_text'):details.append('Texte non représenté : '+e['unrepresented_text'])
        writing=self.current['content']['writing']
        if e['id'] in writing.get('not_written_information_ids',[]):details.append('Information conservée mais absente de la dernière rédaction courante.')
        for omission in writing.get('omissions',[])+writing.get('rejected',[]):
            if omission['id']==e['id']:
                details.append('Rédaction : '+{'not_selected_in_paragraph':'Non sélectionnée dans le paragraphe',
                    'not_reliable_enough':'Paragraphe refusé par les contrôles','unresolved_source_referent':'Référent source non résolu'}.get(omission['reason'],omission['reason']))
        self.reason.setPlainText('\n'.join(details));self.sources.setRowCount(0)
        refs=e['evidence']
        for ref in refs:self.insert_source(ref)
        self.relations.setRowCount(0);by_id={v['id']:v for v in self.current['content']['entries']}
        for relation in self.current['content']['relations']:
            if e['id'] not in (relation['from'],relation['to']):continue
            i=self.relations.rowCount();self.relations.insertRow(i)
            other=relation['to'] if relation['from']==e['id'] else relation['from']
            for col,text in enumerate([('→ ' if relation['from']==e['id'] else '← ')+RELATIONS[relation['kind']],by_id[other]['content'],
                'Confirmée' if relation['human_status']=='approved' else 'Exclue' if relation['human_status']=='excluded' else STATUS[relation['verification']]]):
                item=QTableWidgetItem(text);item.setData(Qt.UserRole,relation['id']);item.setToolTip(relation['reason']);self.relations.setItem(i,col,item)
        self.entry_history.setPlainText('\n\n'.join(h['action']+' — '+h['actor']+' : '+h['reason'] for h in e['history']))
        if self.sources.rowCount():self.sources.selectRow(0)
        else:
            ids=e.get('origin',{}).get('unit_source_ids',[])
            self.context.setPlainText('\n\n'.join(u['text'] for u in self.current['content']['sources'] if u['id'] in ids))
        self._loading_editor=False;self.update_actions()

    def insert_source(self,ref):
        i=self.sources.rowCount();self.sources.insertRow(i);item=QTableWidgetItem(stamp(ref['start_ms']))
        item.setData(Qt.UserRole,ref['id']);item.setFlags(item.flags() & ~Qt.ItemIsEditable);item.setToolTip(ref['id'])
        self.sources.setItem(i,0,item);self.sources.setItem(i,1,QTableWidgetItem(ref['quote']));self.sources.setRowHeight(i,70)

    def add_source(self):
        if not self.entry:return
        dialog=SourcePicker(self.state,self)
        if dialog.exec()==QDialog.Accepted:
            u=next(u for u in self.state['utterances'] if u['id']==dialog.chosen['id'])
            self.insert_source({'id':u['id'],'quote':dialog.chosen['quote'],'start_ms':u['start_ms']})

    def remove_source(self):
        row=self.sources.currentRow()
        if row>=0:self.sources.removeRow(row);self.update_actions()

    def show_context(self):
        row=self.sources.currentRow()
        if row<0:return
        uid=self.sources.item(row,0).data(Qt.UserRole)
        snapshot=self.current['content']
        index=next((i for i,u in enumerate(snapshot['sources']) if u['id']==uid),None)
        if index is None:return
        self.context.setPlainText('\n\n'.join(stamp(u['start_ms'])+' — '+snapshot['speakers'].get(u['speaker_id'],'Inconnu')+'\n'+u['text']
            for u in snapshot['sources'][max(0,index-2):index+3]))

    def listen(self):
        if not self.entry:return
        row=self.sources.currentRow()
        uid=self.sources.item(row,0).data(Qt.UserRole) if row>=0 else next(iter(self.entry.get('origin',{}).get('unit_source_ids',[])),None)
        if not uid:return
        source=next((u for u in self.current['content']['sources'] if u['id']==uid),None)
        if not source:
            self.error(ValueError('Cette source historique est absente de l’instantané courant. Consultez la révision précédente du registre.'));return
        if self.play_snapshot:self.play_snapshot(source)
        elif self.current['stale']:self.error(ValueError('Le registre est obsolète. Reprenez sa préparation avant une écoute sur la transcription actuelle.'))
        else:self.play_callback(uid)

    def verify_selected(self):
        if not self.entry or self.entry['category']!='information':
            self.error(ValueError('Créez une fiche d’information depuis la source avant de demander sa vérification.'));return
        if self.editor_changed():
            self.error(ValueError('Enregistrez la correction avant de demander sa vérification par Qwen.'));return
        if self.verify_callback:self.verify_callback(self.entry['id'])

    def editor_changed(self):
        if not self.entry:return False
        if any(self.sources.item(i,j) is None for i in range(self.sources.rowCount()) for j in (0,1)):return True
        plain=lambda value:value.replace('\r\n','\n').replace('\r','\n').replace('\u00a0',' ').replace('\u2028','\n').replace('\u2029','\n')
        return (self.subject.text()!=self.entry['subject'] or plain(self.content.toPlainText())!=plain(self.entry['content']) or
            self.kind.currentData()!=self.entry['type'] or self.discourse.currentData()!=self.entry.get('discourse','own') or
            [(self.sources.item(i,0).data(Qt.UserRole),self.sources.item(i,1).text()) for i in range(self.sources.rowCount())]!=
            [(e['id'],e['quote']) for e in self.entry['evidence']])

    def focus_entry(self,entry_id):
        if not any(e['id']==entry_id for e in getattr(self,'visible',[])):
            self.filter.setCurrentIndex(self.filter.findData('all'));self.search.clear();self.populate()
        row=next((i for i,e in enumerate(getattr(self,'visible',[])) if e['id']==entry_id),None)
        if row is not None:self.rows.selectRow(row)

    def discard_changes(self):
        if not self.sid:return
        entry_id=self.entry['id'] if self.entry else None
        self.entry=None;self.load(self.sid,force=True)
        if entry_id:self.focus_entry(entry_id)

    def apply(self,action):
        if not self.entry or not self.current:return
        try:
            self.before_change()
            updates=None
            if action=='edit':
                updates={'subject':self.subject.text().strip(),'type':self.kind.currentData(),'discourse':self.discourse.currentData(),
                    'content':self.content.toPlainText().strip(),'evidence':[{'id':self.sources.item(i,0).data(Qt.UserRole),
                    'quote':self.sources.item(i,1).text()} for i in range(self.sources.rowCount())]}
            elif action=='approve' and self.editor_changed():
                raise ValueError('Enregistrez la correction avant d’approuver cette information.')
            entry_id=self.service.change(self.sid,self.current['id'],self.entry['id'],action,
                actor=self.actor.text(),reason=self.justification.text(),updates=updates)
            self.entry=None;self.changed.emit();self.load(self.sid,force=True);self.focus_entry(entry_id)
        except Exception as error:self.error(error)

    def add_relation(self):
        if not self.entry or self.entry['category']!='information':return
        targets=[e for e in self.current['content']['entries'] if e['category']=='information' and e['id']!=self.entry['id']]
        labels=[e['subject']+' — '+e['content'][:130]+' ['+e['id'][:8]+']' for e in targets]
        chosen,ok=QInputDialog.getItem(self,'Information visée','Ce propos réagit à :',labels,0,False)
        if not ok:return
        kind,ok=QInputDialog.getItem(self,'Relation explicite','Relation depuis cette information :',list(RELATIONS.values()),0,False)
        if not ok:return
        try:
            self.before_change();self.service.relation(self.sid,self.current['id'],actor=self.actor.text(),reason=self.justification.text(),
                source_id=self.entry['id'],target_id=targets[labels.index(chosen)]['id'],kind=list(RELATIONS)[list(RELATIONS.values()).index(kind)])
            self.changed.emit();self.load(self.sid)
        except Exception as error:self.error(error)

    def review_relation(self,exclude):
        row=self.relations.currentRow()
        if row<0:return
        try:
            self.before_change();self.service.relation(self.sid,self.current['id'],actor=self.actor.text(),reason=self.justification.text(),
                relation_id=self.relations.item(row,0).data(Qt.UserRole),exclude=exclude)
            self.changed.emit();self.load(self.sid)
        except Exception as error:self.error(error)

    def history(self):
        if not self.sid:return
        rows=self.service.history(self.sid)
        labels=[f"Révision {r['revision']} — {r['created_at']} — {r['actor']} : {r['reason']}" for r in rows]
        chosen,ok=QInputDialog.getItem(self,'Historique conservé du registre','Consulter une révision immuable :',labels,0,False)
        if not ok:return
        document=self.service.version(self.sid,rows[labels.index(chosen)]['id'])
        dialog=QDialog(self);dialog.setWindowTitle('Registre archivé — lecture seule');dialog.resize(900,650)
        layout=QVBoxLayout(dialog);text=QTextEdit();text.setReadOnly(True)
        text.setPlainText('\n\n'.join(e['subject']+' — '+TYPES[e['type']]+' — '+e['verification']+' / '+e['human_status']+'\n'+e['content']+
            '\n'+ '\n'.join(stamp(r['start_ms'])+' ['+r['id']+'] '+r['quote'] for r in e['evidence'])
            for e in document['entries']))
        layout.addWidget(text);close=QDialogButtonBox(QDialogButtonBox.Close);close.rejected.connect(dialog.reject);layout.addWidget(close);dialog.exec()
