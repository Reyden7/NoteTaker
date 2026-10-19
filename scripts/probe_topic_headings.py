"""Actual CPU checks of authored title controls, not a meeting accuracy measure."""
import json
import sys
import time
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.engines.topic_summary import verify_heading
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.atomic import atomic_json
source='Les travaux de la bibliothèque sont estimés globalement à vingt mille euros. Je propose de réparer la toiture.'
row={'id':'s0','speaker_id':'a','start_ms':0,'end_ms':10000,'text':source}
claim={'id':'c0','speaker':'a','kind':'proposal','discourse':'own','text':source,'evidence':[{'id':'s0','quote':source}]}
cases=[('neutral',True,'Travaux de la bibliothèque'),('invented_vote',False,'Adoption unanime des travaux de la bibliothèque'),
    ('budget_scope',False,'Réparation de la seule toiture pour vingt mille euros'),
    ('political_identity',False,'Proposition du parti Exemple pour la bibliothèque')]
models=ModelPaths();workspace=ROOT/'output/topic-headings'/uuid.uuid4().hex;workspace.mkdir(parents=True)
request={'binary':str(models.llama),'model':str(models.llm),'workspace':str(workspace),'utterances':[row]}
started=time.perf_counter();results=[]
for name,expected,title in cases:
    checks=verify_heading(request,name,title,[claim],{'s0':row},[row])
    accepted=all(v=='supported' for v in checks.values())
    raw=json.loads((workspace/(name+'.result.json')).read_text(encoding='utf-8'))['checks']
    results.append({'case':name,'expected_supported':expected,'accepted_by_combined_controls':accepted,
        'raw_model_accepted':all(v=='supported' for v in raw.values()),'checks_after_source_guard':checks,'passed':accepted==expected})
report={'scope':'authored known textual controls; no human meeting reference or quality percentage',
    'actual_cpu_inference':True,'human_fidelity_improvement_measured':None,'results':results,
    'wall_seconds':round(time.perf_counter()-started,3),'passed':all(r['passed'] for r in results)}
atomic_json(ROOT/'docs/evidence/topic-heading-controls.json',report);print(json.dumps(report,indent=2))
if not report['passed']:raise SystemExit(1)
