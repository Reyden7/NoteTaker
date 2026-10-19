"""Create a reviewable isolated copy after inference; never approves the real draft."""
import argparse
import json
import sqlite3
import sys
import uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from notetaker.services.storage import SessionStore
from notetaker.services.session_export import export_session
from notetaker.infrastructure.atomic import atomic_json,sha256_file

p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True)
args=p.parse_args();work=args.work.resolve(strict=True);snapshot=args.snapshot.resolve(strict=True)
state=json.loads((work/'state.json').read_text(encoding='utf-8'));draft=json.loads((work/'draft.json').read_text(encoding='utf-8'))
comparison=json.loads((work/'comparison.json').read_text(encoding='utf-8'));assert comparison['status']=='passed'
before=sha256_file(snapshot);destination=work.parent/('review-copy-'+uuid.uuid4().hex);destination.mkdir()
with sqlite3.connect(snapshot.as_uri()+'?mode=ro',uri=True) as source:
    with sqlite3.connect(destination/'notetaker.sqlite3') as target:
        source.backup(target)
        # A review copy must never recover/write an original capture directory.
        interrupted=target.execute("UPDATE audio_take SET status='interrupted' WHERE kind='capture' AND status='recording'").rowcount
store=SessionStore(destination);sid=state['id']
try:
    previous=store.get(sid)
    assert previous['utterances']==state['utterances']
    history_before=list(store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY id',(sid,)))
    store.save_draft(sid,draft)
    current=store.get(sid)
    assert current['utterances']==previous['utterances'] and current['speakers']==previous['speakers']
    assert current['draft']['review'] is None
    assert [tuple(row) for row in history_before]==[tuple(store.db.execute('SELECT id,review_json FROM draft_minutes WHERE id=?',(row['id'],)).fetchone()) for row in history_before]
    blocked=False
    try:export_session(store,sid,destination/'forbidden-without-review.pdf')
    except ValueError as error:
        assert 'HUMAN_REVIEW' in str(error);blocked=True
    assert blocked
    report={'scope':'isolated snapshot copy only; all original corrections preserved; no live writes',
        'data_directory':str(destination),'session_id':sid,'new_draft_review':None,
        'transcription_and_names_unchanged':True,'production_export_without_review_blocked':blocked,
        'historical_review_records_preserved':True,
        'original_snapshot_unchanged':sha256_file(snapshot)==before,
        'recording_flags_frozen_in_copy_only':interrupted,
        'draft_history_entries':len(store.draft_history(sid)),'human_semantic_validation':False}
    launcher=destination/'ouvrir-relecture.ps1'
    quote=lambda value:"'"+str(value).replace("'","''")+"'"
    launcher.write_text('& '+quote(ROOT/'dist/topic-summary/NoteTaker/NoteTaker.exe')+' --data-dir '+quote(destination)+'\n',encoding='utf-8-sig')
    report['isolated_review_launcher']=str(launcher)
    atomic_json(ROOT/'docs/evidence/topic-review-copy.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2))
finally:store.close()
