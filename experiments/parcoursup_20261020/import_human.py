"""Archive the human correction; prepare a versioned, non-destructive protocol."""
import re
from pathlib import Path
from experiments.parcoursup_20261020.prepare import OUT, CORE, WIDE, read, sha, stamp, write_new

HUMAN = Path('C:/Users/quent/Desktop/correction.txt')
V2 = OUT/'comparaison-v2'


def parse_human(text, original):
    by_id = {r['id']: r for r in original}
    rows = []
    for line in text.splitlines():
        match = re.fullmatch(r'- \*\*(\d{2}:\d{2}\.\d{3}) · (s\d+-\d+) · (.*?)\*\* : (.*)', line)
        if not match:
            if line.startswith('- **'): raise ValueError('Unparsed human row: '+line)
            continue
        timestamp, source_id, author, words = match.groups()
        if source_id not in by_id or timestamp != stamp(by_id[source_id]['start_ms']):
            raise ValueError('Human timestamp/source mismatch: '+source_id)
        rows.append({**by_id[source_id], 'speaker_label': author, 'text': words})
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Empty or duplicate human sources')
    positions = {r['id']:i for i,r in enumerate(original)}
    if [positions[r['id']] for r in rows] != sorted(positions[r['id']] for r in rows):
        raise ValueError('Human order changed')
    return rows


def group_turns(rows):
    """Lossless adjacent-author grouping, never model-directed selection."""
    turns = []
    for row in rows:
        if not turns or turns[-1]['speaker_label'] != row['speaker_label']:
            turns.append({'id':f'T{len(turns)+1:03}', 'speaker_label':row['speaker_label'],
                          'start_ms':row['start_ms'], 'end_ms':row['end_ms'], 'source_ids':[], 'texts':[]})
        turn = turns[-1]
        turn['end_ms'] = max(turn['end_ms'], row['end_ms'])
        turn['source_ids'].append(row['id']); turn['texts'].append(row['text'])
    return [{**{k:v for k,v in t.items() if k != 'texts'}, 'text':' '.join(t['texts'])} for t in turns]


def main():
    source_bytes = HUMAN.read_bytes()
    write_new(V2/'correction-humaine-originale.txt', source_bytes.decode('utf-8-sig'))
    # Preserve exact bytes, including a possible BOM and original newlines.
    (V2/'correction-humaine-originale.txt').write_bytes(source_bytes)
    a = read(OUT/'inputs/A-original.json')['passages']
    b = parse_human(source_bytes.decode('utf-8-sig'), a)
    frozen = read(OUT/'source-670.json')
    if isinstance(frozen,dict): frozen = frozen['utterances']
    # Reconstruct the wider ORIGINAL context. Only the focal correction was supplied by the human.
    from experiments.parcoursup_20261020.prepare import REQUEST
    speakers = read(REQUEST)['registry']['speakers']
    extra = [{k:r[k] for k in ('id','speaker_id','start_ms','end_ms','text')} |
             {'speaker_label':speakers.get(r['speaker_id'],'Intervenant non attribué')}
             for r in frozen if r['end_ms'] > WIDE[0] and r['start_ms'] < CORE[0]]
    cases = {'A-original':a, 'B-corrigee-humaine':b, 'C-corrigee-contexte':extra+b}
    retained = {r['id'] for r in b}
    omitted = [r for r in a if r['id'] not in retained]
    receipt = {'human_file':str(HUMAN),'human_file_sha256':sha(HUMAN),
        'receipt_basis':'User provided this corrected excerpt in response to the audio-review request.',
        'reviewer_identity':'Utilisateur de cette conversation (nom non fourni)',
        'agent_listened_to_audio':False,'human_review_scope':'Focal excerpt only; supplied corrections preserved verbatim.',
        'context_extension_status':'Original saved transcription, NOT human-audio-corrected.',
        'timing_status':'Original ASR timing retained, not re-aligned to corrected words.',
        'omitted_rows_in_human_file':omitted,
        'omission_note':'These IDs are absent from the supplied human revision. Their raw text is preserved here; no intent or exact merge boundary is inferred. Some words recur in adjacent corrected rows.',
        'baseline_manifest_sha256':sha(OUT/'manifest.json'), 'cases':{}}
    for name, rows in cases.items():
        turns = group_turns(rows)
        payload = {'focus_start_ms':CORE[0],'focus_end_ms':CORE[1],
                   'context_status': 'Additional context is uncorrected original transcription; do not infer identities across ambiguous labels.',
                   'passages':rows, 'turns':turns}
        path = V2/'inputs'/(name+'.json')
        write_new(path,payload)
        receipt['cases'][name] = {'sha256':sha(path),'row_count':len(rows),'turn_count':len(turns)}
        lines = [f'# Transcription expérimentale {name}', '',
                 'Horodatages de la transcription originale : repères de recherche audio, précision mot à mot non revue.', '']
        for t in turns:
            lines += [f"## {t['id']} · {stamp(t['start_ms'])}–{stamp(t['end_ms'])} · {t['speaker_label']}",
                      '',t['text'],'','Sources : '+', '.join(t['source_ids']), '']
        write_new(V2/(name+'.md'),'\n'.join(lines))
    write_new(V2/'provenance-humaine.json',receipt)
    print(receipt['cases']); print('Human omitted IDs:',[r['id'] for r in omitted])


if __name__ == '__main__': main()
