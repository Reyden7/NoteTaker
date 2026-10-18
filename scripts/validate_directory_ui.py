"""Exercise and render the real Qt directory on fictional data, never user sessions."""
import json
import os
import sys
import uuid
from pathlib import Path
os.environ['QT_QPA_PLATFORM'] = 'windows' if os.name == 'nt' else 'offscreen'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from notetaker.ui.window import MainWindow
from notetaker.ui.directory import DirectoryDialog
from notetaker.services.directory import DirectoryService

destination = ROOT/'output/directory-validation'/uuid.uuid4().hex
destination.mkdir(parents=True)
app = QApplication([])
app.setStyle('Fusion')
window = MainWindow(destination/'data')
window.resize(1440, 920)
dialog = DirectoryDialog(window.store, window)
dialog.resize(1200, 760)
people = []
for first, last, position, city in [
    ('Élodie', 'Martin', 'Conseillère municipale', 'Saint-Rémy'),
    ('Paul', 'Bernard', 'Maire', 'Saint-Rémy'),
    ('Nadia', 'Benali', 'Adjointe aux finances', 'Saint-Rémy'),
    ('Luc', 'Moreau', 'Conseiller municipal', 'Saint-Rémy'),
    ('Anne', 'Lefèvre', 'Directrice générale des services', 'Châtillon')]:
    dialog.new_person()
    for k, value in zip(('first_name','last_name','position','municipality'), (first,last,position,city)):
        dialog.fields[k].setText(value)
    QTest.mouseClick(dialog.save_button, Qt.LeftButton)
    assert dialog.pid
    people.append(dialog.pid)
assert not dialog.voice_button.isEnabled()
dialog.ensurePolished()
app.processEvents()
assert dialog.grab().save(str(destination/'directory.png'))
dialog.close()
service = DirectoryService(window.store)
sid = window.store.create('Conseil municipal — données fictives de recette', {'date':'2026-10-18','municipality':'Saint-Rémy'})
service.save_participants(sid, [
    {'person_id':people[0],'attendance':'represented','proxy_to_person_id':people[1], 'proxy_note':'Pouvoir remis au secrétariat — séance entière'},
    {'person_id':people[1],'attendance':'present','session_role':'Présidence de séance'},
    {'person_id':people[2],'attendance':'excused'}, {'person_id':people[3],'attendance':'absent'},
    {'person_id':people[4],'attendance':'unconfirmed','session_role':'Invitée'}])
window.store.save_analysis(sid, [
    {'id':'u0','start_ms':0,'end_ms':6000,'text':'La séance est ouverte. Nous abordons les travaux de la bibliothèque.','speaker_id':'a','uncertain':True},
    {'id':'u1','start_ms':7000,'end_ms':12000,'text':'Le devis doit être vérifié avant toute décision.','speaker_id':'b','uncertain':True}],
    {'a':'Intervenant 1','b':'Intervenant 2'}, window.store.get(sid)['revision'])
window.sid = sid
window.load_session()
window.tabs.setCurrentWidget(window.participants_page)
window.ensurePolished()
app.processEvents()
assert window.grab().save(str(destination/'participants.png'))
window.tabs.setCurrentIndex(2)
window.transcript_table.selectRow(0)
window.person_combo.setCurrentIndex(window.person_combo.findData(people[1]))
QTest.mouseClick(window.assign_person_button, Qt.LeftButton)
app.processEvents()
assert window.transcript_table.item(0,1).text() == 'Paul Bernard'
assert window.grab().save(str(destination/'manual-assignment.png'))
assert len(window.store.get(sid)['participants']) == 5
assert window.store.get(sid)['draft'] is None
report={'scope':'fictional fixture; actual Qt widgets, civil directory only',
    'data_directory':str(destination/'data'),'session_id':sid,
    'directory_form_saved':len(people),'participants':5,'proxy_to_present_person':True,
    'manual_assignment_passed':True,'voice_enrollment_button_disabled':True,
    'review_created':False,'screenshots':[str(destination/name) for name in ['directory.png','participants.png','manual-assignment.png']]}
window.close()
(ROOT/'docs/evidence/directory-ui.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
