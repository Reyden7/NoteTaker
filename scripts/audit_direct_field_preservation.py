"""Real field-copy persistence and export refusal, without inventing a review."""
import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.services.storage import SessionStore
from notetaker.services.evidence import require_valid_evidence
from notetaker.services.direct_summary import validate_provenance
from notetaker.services.session_export import export_session
from notetaker.domain.minutes import validate_minutes

p = argparse.ArgumentParser()
p.add_argument('--work', type=Path, required=True)
work = p.parse_args().work.resolve()
source = ROOT/'output/direct-summary/input-024.sqlite3'
target = work/'data/notetaker.sqlite3'
report = json.loads((work/'cold-report.json').read_text(encoding='utf-8'))
assert report['status'] == 'completed'
source_sha = sha256_file(source)
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
directory = work/'data/sessions'/sid/'direct-experiments'/report['service_result']['run_id']
artifact = json.loads((directory/'result.json').read_text(encoding='utf-8'))
ledger = artifact['result']['ledger']
refs = {ref['id']: ref for ref in ledger['reference_manifest']}
originals = {u['id']: ' '.join(u['text'].split()) for u in artifact['input']['utterances']}
voices = list(dict.fromkeys(u.get('speaker_id') or 'unattributed' for u in artifact['input']['utterances']))
aliases = {voice: f'V{i+1}' for i,voice in enumerate(voices)}
covered = {key:set() for key in originals}
prompt_count = 0
for path in sorted((directory/'inference').glob('context-*.prompt.txt')):
    prompt = path.read_text(encoding='utf-8')
    raw = prompt.split('<|im_start|>user\n', 1)[1].rsplit('\n<|im_end|>\n<|im_start|>assistant\n', 1)[0]
    inputs = json.loads(raw)
    for unit in inputs['core']:
        for part in unit['parts']:
            ref = refs[part['id']]
            assert part['text'] == ref['text']
            assert unit['speaker'] == aliases[ref['speaker']]
            for span in ref['source_spans']:
                a, b = max(ref['offset'],span['start']), min(ref['offset']+len(part['text']),span['end'])
                if b <= a:
                    continue
                start, stop = a-span['start'], b-span['start']
                assert part['text'][a-ref['offset']:b-ref['offset']] == originals[span['id']][start:stop]
                covered[span['id']].update(range(start,stop))
    prompt_count += 1
for key, text in originals.items():
    assert {i for i,c in enumerate(text) if not c.isspace()} <= covered[key], 'Source text not supplied to Qwen: '+key
assert prompt_count == len(ledger['parts']) == len(ledger['context_inventory'])

def rows(connection, name):
    # Names originate in sqlite_master, still quote identifiers correctly.
    name = name.replace('"', '""')
    return Counter(tuple((type(value).__name__, value) for value in row)
                   for row in connection.execute('SELECT * FROM "'+name+'"'))

tables = {}
with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True) as old, sqlite3.connect(target.as_uri()+'?mode=ro', uri=True) as new:
    for (name,) in old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        before, after = rows(old, name), rows(new, name)
        assert not before-after, 'An original row was removed or changed: '+name
        added = sum((after-before).values())
        assert name == 'draft_minutes' or added == 0, 'Unexpected mutation: '+name
        tables[name] = {'original_rows': sum(before.values()), 'all_original_rows_identical': True,
                        'added_rows': added}
    assert old.execute('PRAGMA user_version').fetchone() == new.execute('PRAGMA user_version').fetchone()
assert sha256_file(source) == source_sha

store = SessionStore(work/'data')
state = store.get(sid)
draft = state['draft']
new_draft = report['service_result']['draft_saved']
valid = False
if new_draft:
    assert draft['content']['experimental_summary']['run_id'] == report['service_result']['run_id']
    validate_provenance(store, sid, draft['content'])
    require_valid_evidence(draft['content'], state)
    validate_minutes(draft['content'], {u['id'] for u in state['utterances']}, {v['id']:v for v in state['votes']})
    assert draft['review'] is None
    valid = True
refusals = {}
for extension in ('pdf', 'docx'):
    destination = work/('export-without-human-review-refused.'+extension)
    assert not destination.exists()
    try:
        export_session(store, sid, destination)
    except ValueError as error:
        refusals[extension] = str(error)
        assert not new_draft or 'HUMAN_REVIEW' in str(error)
    else:
        raise AssertionError('An unreviewed field document was exported')
    assert not destination.exists()
assert store.get(sid) == state
store.close()
store = SessionStore(work/'data')
assert store.get(sid) == state
store.close()
evidence = {'scope': 'real 670-row field copy; every original SQLite row compared, no human approval created',
    'all_nonblank_source_characters_found_in_actual_model_prompts': True,
    'stored_voice_labels_preserved_in_actual_model_prompts': True,
    'input_rows': len(originals), 'context_prompts_checked': prompt_count,
    'nonwhitespace_source_characters': sum(not c.isspace() for text in originals.values() for c in text),
    'source_db_sha256': source_sha, 'source_db_unchanged': sha256_file(source) == source_sha,
    'tables': tables, 'sqlite_schema_version_unchanged': True,
    'new_draft_saved': new_draft, 'new_draft_provenance_and_evidence_valid': valid,
    'same_state_after_close_reopen': True, 'real_export_refusals': refusals,
    'pdf_or_docx_written': False, 'human_review_created': False, 'quality_validated': False}
atomic_json(ROOT/'docs/evidence/direct-summary-field-preservation.json', evidence)
print(json.dumps(evidence, ensure_ascii=True, indent=2))
