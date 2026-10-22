"""Resume the real recipe through the application service, preserving revisions."""
import argparse
import json
import time
from pathlib import Path
from notetaker.infrastructure.offline import enforce_offline
from notetaker.services.storage import SessionStore
from notetaker.services.pipeline import Pipeline
from notetaker.services.working_export import export_working_copy
from notetaker.services.session_export import export_session

parser=argparse.ArgumentParser()
parser.add_argument('--data-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--session-id',required=True)
args=parser.parse_args();enforce_offline()
args.output.mkdir(exist_ok=False,parents=True)
store=SessionStore(args.data_root);store.recover();state=store.get(args.session_id)
preserved={k:state[k] for k in ('utterances','speakers','votes','decisions','participants')}
started=time.perf_counter()
result=Pipeline(args.data_root,progress=lambda s:print(s,flush=True)).automatic_report(args.session_id)
after=store.get(args.session_id)
assert all(after[k]==v for k,v in preserved.items()) and after['draft']['review'] is None
for suffix in ('pdf','docx'):export_working_copy(store,args.session_id,args.output/('Compte-rendu-BROUILLON.'+suffix))
try:export_session(store,args.session_id,args.output/'OFFICIEL-INTERDIT.pdf')
except ValueError:blocked=True
else:blocked=False
assert blocked
result.update(content=after['draft']['content'],session_sources_unchanged=True,official_export_blocked=True,
              elapsed_total_seconds=time.perf_counter()-started)
(args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
store.close();print(json.dumps({k:v for k,v in result.items() if k!='content'},ensure_ascii=False),flush=True)
