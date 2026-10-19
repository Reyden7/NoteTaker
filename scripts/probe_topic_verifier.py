"""Authored semantic regression controls, explicitly not a human field benchmark."""
import json
import sys
import time
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.engines.topic_summary import verify
from notetaker.infrastructure.atomic import atomic_json,sha256_file
from notetaker.infrastructure.paths import ModelPaths

fixtures=[
 ('budget_scope',False,'Les travaux sont estimés globalement à vingt mille euros, avec la toiture et les fenêtres.','La seule toiture coûte vingt mille euros.','context'),
 ('question',False,'Approuvez-vous le blocage de la bibliothèque ?','Le journaliste approuve le blocage de la bibliothèque.','position'),
 ('reported_opinion',False,'Vous estimez que le blocage est nécessaire ; je vous demande pourquoi.','Le journaliste estime le blocage nécessaire.','position'),
 ('anecdote',False,'Quand j’étais au lycée, mon trajet en bus durait deux heures.','Un trajet de deux heures est proposé comme nouvelle règle scolaire.','proposal'),
 ('political_identity',False,'Je participe au blocage depuis mardi.','Cette personne est militante du parti Exemple.','context'),
 ('faithful_question',True,'Approuvez-vous le blocage de la bibliothèque ?','La personne demande si le blocage de la bibliothèque est approuvé.','question'),
 ('faithful_proposal',True,'Je propose une expertise préalable du bâtiment pour vérifier les risques.','Une expertise préalable du bâtiment est proposée afin de vérifier les risques.','proposal'),
]
models=ModelPaths();destination=ROOT/'output/topic-verifier'/uuid.uuid4().hex;destination.mkdir(parents=True)
request={'binary':str(models.llama),'model':str(models.llm),'workspace':str(destination)}
items=[{'id':key,'kind':kind,'speaker':'a','claim':claim,
        'sources':[{'id':key,'speaker':'a','quote':source,'source_text':source}]} for key,_,source,claim,kind in fixtures]
started=time.perf_counter();checks=verify(request,'semantic-controls',items)
results=[]
for key,expected,source,claim,kind in fixtures:
    accepted=all(v=='supported' for v in checks[key].values())
    results.append({'case':key,'expected_supported':expected,'machine_accepted':accepted,'checks':checks[key],'matches_authored_control':accepted==expected})
report={'scope':'developer-authored textual regression controls; known failure patterns; not a blind field evaluation or human meeting annotation',
    'actual_local_cpu_inference':True,'human_field_reference':False,'human_fidelity_improvement_measured':None,
    'model_sha256':sha256_file(models.llm),'wall_seconds':round(time.perf_counter()-started,3),'results':results,
    'all_authored_controls_passed':all(r['matches_authored_control'] for r in results)}
atomic_json(ROOT/'docs/evidence/topic-verifier-controls.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
if not report['all_authored_controls_passed']:raise SystemExit(1)
