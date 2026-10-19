"""Inspect a read-only SQLite snapshot; repair only an isolated copy, never approve."""
import argparse
import copy
import json
import sqlite3
import sys
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from notetaker.services.storage import SessionStore
from notetaker.services.evidence import draft_issues,propose_attribution_refresh
from notetaker.services.session_export import export_session
from notetaker.infrastructure.atomic import sha256_file,atomic_json

p=argparse.ArgumentParser()
p.add_argument('--snapshot',required=True,type=Path)
p.add_argument('--session',required=True)
args=p.parse_args()
source=args.snapshot.resolve(strict=True)
digest=sha256_file(source)
destination=ROOT/'output/validation-fix-audit'/('repair-'+uuid.uuid4().hex)
destination.mkdir(parents=True)
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as original:
    with sqlite3.connect(destination/'notetaker.sqlite3') as target:original.backup(target)
store=SessionStore(destination)
try:
    state=store.get(args.session)
    old=copy.deepcopy(state['draft']['content'])
    issues=draft_issues(old,state)
    proposed,changed=propose_attribution_refresh(old,state)
    remaining=draft_issues(proposed,state)
    claims=lambda content:[c for point in content['points'] for c in point.get('claims',[])]
    before,after=claims(old),claims(proposed)
    report={'scope':'proposal checked on isolated copy only; no live edits, no human approval',
        'invalid_source_links_before':sum(i['source_id'] is not None for i in issues),
        'invalid_claims_before':len({i['claim_id'] for i in issues if i['source_id'] is not None and i['claim_id']}),
        'printed_name_warnings_before':sum(i['reason']=='stale_attribution_text' for i in issues),
        'reasons_before':{reason:sum(i['reason']==reason for i in issues) for reason in sorted({i['reason'] for i in issues})},
        'invalid_links_after_proposed_attribution_refresh':len(remaining),'changed_points':len(changed),
        'claim_texts_unchanged':[c['text'] for c in before]==[c['text'] for c in after],
        'claim_quotes_and_source_ids_unchanged':[c['evidence'] for c in before]==[c['evidence'] for c in after],
        'review_created':False,'human_semantic_fidelity_measured':False}
    store.save_draft(args.session,proposed)
    assert store.get(args.session)['draft']['review'] is None
    try:export_session(store,args.session,destination/'forbidden.pdf')
    except ValueError as error:report.update(unreviewed_export_blocked=True,export_error=str(error))
    else:raise AssertionError('Unreviewed export allowed')
    report['original_snapshot_unchanged']=sha256_file(source)==digest
    assert not remaining and report['original_snapshot_unchanged']
    atomic_json(ROOT/'docs/evidence/validation-fix-real-audit.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2))
finally:store.close()
