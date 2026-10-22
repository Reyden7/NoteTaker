"""Real Qwen end-to-end qualification on a copy; never creates a human review."""
import argparse
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from notetaker.infrastructure.offline import enforce_offline
from notetaker.services.pipeline import Pipeline
from notetaker.services.storage import SessionStore
from notetaker.services.working_export import export_working_copy
from notetaker.services.session_export import export_session

parser=argparse.ArgumentParser();parser.add_argument('--recipe',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
enforce_offline()
original=args.recipe/'notetaker.sqlite3';before=hashlib.sha256(original.read_bytes()).hexdigest()
root=args.output/'session-copy';root.mkdir()
with sqlite3.connect(original.resolve().as_uri()+'?mode=ro',uri=True) as src:
    with sqlite3.connect(root/'notetaker.sqlite3') as dst: src.backup(dst)
store=SessionStore(root);sid=store.list_sessions()[0]['id']; state=store.get(sid)
preserved={k:state[k] for k in ('utterances','speakers','votes','decisions','participants')};store.close()
started=time.perf_counter()
result=Pipeline(root,progress=lambda text:print(text,flush=True)).automatic_report(sid)
store=SessionStore(root);after=store.get(sid)
assert all(after[k]==v for k,v in preserved.items()) and after['draft']['review'] is None
export_working_copy(store,sid,args.output/'compte-rendu-BROUILLON.pdf')
export_working_copy(store,sid,args.output/'compte-rendu-BROUILLON.docx')
try: export_session(store,sid,args.output/'export-officiel-INTERDIT.pdf')
except ValueError: official_blocked=True
else: official_blocked=False
assert official_blocked and hashlib.sha256(original.read_bytes()).hexdigest()==before
result.update(elapsed_total_seconds=time.perf_counter()-started,original_db_unchanged=True,
    session_sources_unchanged=True,official_export_blocked=official_blocked,human_fidelity_measured=False,
    voice_accuracy_measured=False,content=after['draft']['content'])
(args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
store.close(); print(json.dumps({k:v for k,v in result.items() if k!='content'},ensure_ascii=False),flush=True)
