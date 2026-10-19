"""Real native classification/rewrite on the failed, known fictional worker input."""
import sys,json,uuid,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.engines.topic_summary import classify_notes,rephrase_notes,discourse_problem
from notetaker.engines.hierarchical_summary import grounded_claim
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.atomic import atomic_json
failed=ROOT/'output/bundle-validation/4e94fe0d-182a-4218-af4c-d39aabf01687'
original=json.loads((failed/'llm.json').read_text(encoding='utf-8'))
notes=[r['claim'] for r in json.loads((failed/'argument-audit.json').read_text(encoding='utf-8'))['rejected']]
out=ROOT/'output/topic-classification'/uuid.uuid4().hex;out.mkdir(parents=True)
request={**original,'workspace':str(out)};by_id={u['id']:u for u in request['utterances']}
started=time.perf_counter();types=classify_notes(request,notes,by_id,'classify')
for c in notes:c.update(types[c['id']])
rewritten=rephrase_notes(request,notes,by_id,'rewrite')
issues=[]
for c in notes:
    c['text']=rewritten[c['id']]
    valid,reason=grounded_claim(c,request['utterances'])
    problem=discourse_problem(c['kind'],c['discourse'],c['text'],[e['quote'] for e in c['evidence']]) or (None if valid else reason)
    if problem:issues.append({'id':c['id'],'reason':problem})
report={'scope':'authored fictional worker input that failed before; actual local CPU classification and rewrite only',
    'types':types,'structural_rejections':issues,'wall_seconds':round(time.perf_counter()-started,3),
    'field_fidelity_measured':False,'data_directory':str(out)}
atomic_json(out/'rewritten-notes.json',notes);atomic_json(ROOT/'docs/evidence/topic-classification-controls.json',report)
print(json.dumps(report,ensure_ascii=True,indent=2))
