"""Capture actual Qt widgets on fictional data; no inference or meeting approval."""
import copy
import json
import os
import sys
import uuid
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='windows' if os.name=='nt' else 'offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from PySide6.QtWidgets import QApplication
from notetaker.ui.window import MainWindow
from notetaker.services.information_registry import RegistryService
from notetaker.infrastructure.atomic import atomic_json

app=QApplication([]);app.setStyle('Fusion');out=ROOT/'output/information-registry-ui'/uuid.uuid4().hex;out.mkdir(parents=True)
window=MainWindow(out/'data');window.resize(1550,1000)
sid=window.store.create('Conseil fictif — registre des informations',{'municipality':'Commune fictive'})
window.store.save_analysis(sid,[
    {'id':'s0','speaker_id':'a','start_ms':10000,'end_ms':16000,'text':'Peut-on ouvrir la bibliothèque le dimanche sans recruter ?','uncertain':False,'source':{'automatic_attribution':False}},
    {'id':'s1','speaker_id':'b','start_ms':17000,'end_ms':24000,'text':'Je propose de consulter les agents et les habitants avant de décider.','uncertain':False},
    {'id':'s2','speaker_id':None,'start_ms':24500,'end_ms':25000,'text':'Mais le budget…','uncertain':True}],
    {'a':'Élodie Exemple','b':'Voix 2'},0)
service=RegistryService(window.store);record=service.initialize(sid);doc=record['content']
for index in range(2):
    e=copy.deepcopy(doc['entries'][index]);e.update(id=f'fixture-info-{index}',category='information',subject='Horaires de la bibliothèque',
        type='question' if index==0 else 'proposal',discourse='question' if index==0 else 'own',
        content='Élodie Exemple interroge la possibilité d’ouvrir le dimanche sans recrutement.' if index==0 else 'La personne propose de consulter les agents et les habitants avant toute décision.',
        verification='supported' if index==0 else 'ambiguous',reasons=[] if index==0 else ['contextual_entailment_rejected'])
    doc['entries'].append(e)
doc['processing']['status']='ready_for_review'
service.save(sid,doc,expected_id=record['id'],actor='Fixture Qt',reason='Données fictives pour inspection visuelle')
window.sid=sid;window.load_session();window.tabs.setCurrentWidget(window.registry_page)
window.show();app.processEvents();window.registry_page.rows.selectRow(1);app.processEvents()
window.grab().save(str(out/'registry.png'))
window.registry_page.detail_tabs.setCurrentIndex(1);app.processEvents();window.grab().save(str(out/'sources.png'))
window.registry_page.filter.setCurrentIndex(window.registry_page.filter.findData('review'));app.processEvents()
window.grab().save(str(out/'to-verify.png'))
window.close();app.processEvents()
report={'scope':'actual Windows Qt widgets; authored fictional data, not an AI fidelity test',
    'images':[str(out/p) for p in ['registry.png','sources.png','to-verify.png']],
    'visually_inspected':False,'human_meeting_review_created':False}
atomic_json(ROOT/'docs/evidence/information-registry-ui.json',report);print(json.dumps(report,ensure_ascii=True,indent=2))
