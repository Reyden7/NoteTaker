"""Render real Qt correction widgets on fictional data; does not approve a meeting."""
import sys,json,os,uuid
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='windows' if os.name=='nt' else 'offscreen'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QItemSelectionModel
from notetaker.ui.window import MainWindow
from notetaker.ui.evidence import ClaimEditor
from notetaker.services.directory import DirectoryService
from notetaker.services.evidence import draft_issues

app=QApplication([]);app.setStyle('Fusion')
destination=ROOT/'output/validation-fixes-ui'/uuid.uuid4().hex;destination.mkdir(parents=True)
window=MainWindow(destination/'data');window.resize(1440,960)
sid=window.store.create('Conseil fictif — correction des références',{'municipality':'Commune de recette'})
text='Je propose une rénovation de la bibliothèque municipale pour maintenir le service public. Les infiltrations menacent les livres et les espaces de lecture.'
rows=[{'id':'s0','start_ms':0,'end_ms':14000,'text':text,'speaker_id':'a','uncertain':True},
    {'id':'s1','start_ms':15000,'end_ms':21000,'text':'Je demande deux devis détaillés avant toute décision sur les travaux.','speaker_id':'a','uncertain':True},
    {'id':'s2','start_ms':22000,'end_ms':25000,'text':'Une intervention dont la voix reste à identifier.','speaker_id':None,'uncertain':True}]
window.store.save_analysis(sid,rows,{'a':'Intervenant 1'},0)
claim={'id':'c0','speaker':'a','kind':'proposal','text':'Une rénovation est proposée pour préserver le service de la bibliothèque.',
       'evidence':[{'id':'s0','quote':text}]}
point={'title':'Travaux de la bibliothèque','summary':'Proposition — Intervenant 1 (attribution à vérifier) : '+claim['text'],'sources':['s0'],'vote_id':None,'claims':[claim]}
window.store.save_draft(sid,{'points':[point],'to_verify':['Relire les attributions et les citations avant export.']})
directory=DirectoryService(window.store)
pid=directory.save_person({'first_name':'Élodie','last_name':'Martin','position':'Conseillère','municipality':'Commune de recette'})
directory.save_participants(sid,[{'person_id':pid,'attendance':'present'}]);directory.assign_person(sid,['s0'],pid)
window.sid=sid;window.load_session();window.ensurePolished();window.tabs.setCurrentIndex(2)
window.transcript_table.selectRow(0);app.processEvents()
assert window.grab().save(str(destination/'transcript.png'))
window.tabs.setCurrentIndex(3)
issues=draft_issues(window.draft_content,window.store.get(sid))
window.show_evidence_diagnostics(issues);app.processEvents()
assert window.evidence_dialog.grab().save(str(destination/'diagnostics.png'))
window.evidence_dialog.close()
editor=ClaimEditor(point,0,window.store.get(sid),window);editor.use_source_voice();editor.check();editor.ensurePolished();app.processEvents()
assert editor.apply.isEnabled()
assert editor.grab().save(str(destination/'claim-editor.png'))
editor.close();window.close()
report={'scope':'actual Windows Qt widgets on fictional data only','destination':str(destination),
        'diagnostics_issues':len(issues),'claim_repair_preview_valid':True,'review_created':False,
        'images':[str(destination/name) for name in ['transcript.png','diagnostics.png','claim-editor.png']]}
(ROOT/'docs/evidence/validation-fixes-ui.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
