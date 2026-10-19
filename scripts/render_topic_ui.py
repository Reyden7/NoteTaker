"""Inspect actual Qt widgets with authored fictional data, no model inference."""
import json
import os
import sys
import uuid
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='windows' if os.name=='nt' else 'offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from PySide6.QtWidgets import QApplication,QDialog,QVBoxLayout,QTextEdit
from notetaker.ui.window import MainWindow,paragraph
from notetaker.ui.evidence import NarrativeSources
from notetaker.services.pipeline import assemble_summary
from notetaker.infrastructure.atomic import atomic_json

app=QApplication([]);app.setStyle('Fusion')
out=ROOT/'output/topic-summary-ui'/uuid.uuid4().hex;out.mkdir(parents=True)
window=MainWindow(out/'data');window.resize(1440,960)
sid=window.store.create('Conseil fictif — synthèse thématique',{'municipality':'Commune fictive','summary_length':'standard'})
source='Je propose une expertise du bâtiment avant les travaux pour vérifier les risques liés à la toiture.'
window.store.save_analysis(sid,[{'id':'s0','text':source,'speaker_id':'a','start_ms':10000,'end_ms':23000,'uncertain':False}],{'a':'Élodie Exemple'},0)
claim={'id':'c0','speaker':'a','kind':'proposal','discourse':'own','text':'Une expertise préalable du bâtiment est proposée pour vérifier les risques.', 'evidence':[{'id':'s0','quote':source}]}
result={'strategy':'contextual-topic-paragraphs-v1','claims':[claim],
    'topics':[{'title':'Préparation des travaux de la bibliothèque','claims':['c0'],'sentences':[
        {'text':'Au sujet des travaux de la bibliothèque, {{V1}} propose une expertise préalable du bâtiment afin d’évaluer les risques liés à la toiture.',
         'voice_bindings':{'V1':'a'},'claim_ids':['c0'],'relation':'proposal','machine_verdict':'fixture_not_model_generated'}]}],
    'diagnostics':{'summary_length':'standard','rejected_claims':0,'omitted_claims':0,'topics_not_written':[]}}
draft=assemble_summary(window.store.get(sid),result);window.store.save_draft(sid,draft)
window.sid=sid;window.load_session();window.ensurePolished();window.tabs.setCurrentIndex(3);app.processEvents()
window.grab().save(str(out/'summary.png'))
dialog=NarrativeSources(draft['points'][0],window.store.get(sid),lambda uid:None,window);dialog.ensurePolished();app.processEvents()
dialog.grab().save(str(out/'sentence-sources.png'));dialog.close()
window.tabs.setCurrentIndex(0);app.processEvents();window.grab().save(str(out/'settings.png'))
window.close()
report={'scope':'actual Qt Windows widgets; authored fictional data; no human meeting review or machine quality claim',
    'images':[str(out/name) for name in ['summary.png','sentence-sources.png','settings.png']],
    'review_created':False,'biometrics_active':False}
atomic_json(ROOT/'docs/evidence/topic-summary-ui.json',report);print(json.dumps(report,ensure_ascii=True,indent=2))
