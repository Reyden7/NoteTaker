"""Conservative segmentation and preservation of explicit human corrections."""
import copy
import json
import re
import uuid


def metadata(row):
    return json.loads(row['source_json']) if 'source_json' in row else row.get('source', {})


def manual(row, labels):
    source = metadata(row)
    name = labels.get(row.get('speaker_id'), '')
    named = name and not re.fullmatch(r'(?:Intervenant|Voix)\s+\d+', name)
    return source.get('automatic_attribution') is False or source.get('manual_text', False) or bool(named)


def compact_rows(rows, max_ms=20000):
    result = []
    for original in rows:
        u = copy.deepcopy(original)
        if not u['text'].strip() or u['end_ms'] < u['start_ms']:
            continue
        source = u.setdefault('source', metadata(u))
        # Non-lexical output is not a speaker turn; the raw ASR remains in the job.
        if not re.search(r'\w', u['text']) and source.get('automatic_attribution', True):
            if result and 0 <= u['start_ms']-result[-1]['end_ms'] <= 750 and u.get('speaker_id') == result[-1].get('speaker_id'):
                result[-1]['text'] += ' '+u['text'].strip()
                result[-1]['end_ms'] = max(result[-1]['end_ms'],u['end_ms'])
            continue
        previous = result[-1] if result else None
        if (previous and u.get('speaker_id') is not None and previous.get('speaker_id') == u.get('speaker_id')
            and previous.get('uncertain') == u.get('uncertain') and 0 <= u['start_ms']-previous['end_ms'] <= 750
            and u['end_ms']-previous['start_ms'] <= max_ms and len(previous['text'])+len(u['text']) <= 1400
            and metadata(previous).get('automatic_attribution', True) and source.get('automatic_attribution', True)
            and not metadata(previous).get('possible_overlap') and not source.get('possible_overlap')
            and metadata(previous).get('normalized_audio') == source.get('normalized_audio')):
            previous['source'].setdefault('merged_source_ids',[previous['id']]).append(u['id'])
            previous['source'].setdefault('word_spans',[]).extend(source.get('word_spans',[]))
            previous['text'] = previous['text'].rstrip()+' '+u['text'].lstrip()
            previous['end_ms'] = u['end_ms']
        else:
            result.append(u)
    return result


def preserve_corrections(old, incoming, labels):
    protected = [u for u in old['utterances'] if manual(u, old['speakers'])]
    # Match anonymous groups by mutual temporal support on the same recording.
    weights = {}
    for new in incoming:
        for previous in old['utterances']:
            if previous in protected or not previous.get('speaker_id') or not new.get('speaker_id'):
                continue
            duration = max(0,min(new['end_ms'],previous['end_ms'])-max(new['start_ms'],previous['start_ms']))
            if duration:
                key=(new['speaker_id'],previous['speaker_id'])
                weights[key]=weights.get(key,0)+duration
    mapping = {}
    for key in labels:
        candidates=sorted(((v,old_id) for (new_id,old_id),v in weights.items() if new_id==key),reverse=True)
        if candidates:
            score,old_id=candidates[0]
            total=sum(v for v,_ in candidates)
            reverse=sorted(((v,n) for (n,o),v in weights.items() if o==old_id),reverse=True)
            reverse_total=sum(v for v,_ in reverse)
            if (score/total >= .75 and (len(candidates)==1 or (score-candidates[1][0])/total >= .2)
                and reverse[0][1]==key and score/reverse_total >= .75
                and (len(reverse)==1 or (score-reverse[1][0])/reverse_total >= .2)):
                mapping[key]=old_id
    used=set(old['speakers'])
    for key in labels:
        if key not in mapping:
            mapping[key]='voice-'+uuid.uuid4().hex if key in used else key
    output=[]
    protected_ids={u['id'] for u in protected}
    spans=[(u['start_ms'],u['end_ms']) for u in protected]
    for original in incoming:
        u=copy.deepcopy(original)
        if u['id'] in protected_ids:
            u['id']='auto-'+uuid.uuid4().hex
        u['speaker_id']=mapping.get(u.get('speaker_id'),u.get('speaker_id'))
        overlaps=[(a,b) for a,b in spans if a<u['end_ms'] and b>u['start_ms']]
        if not overlaps:
            output.append(u);continue
        if any(a<=u['start_ms'] and b>=u['end_ms'] for a,b in overlaps):
            continue
        words=metadata(u).get('word_spans')
        if not words:
            raise ValueError('MANUAL_ALIGNMENT_REQUIRES_REVIEW')
        groups=[]
        for w in words:
            if any(a<w['end']*1000 and b>w['start']*1000 for a,b in overlaps):
                groups.append(None);continue
            if groups and groups[-1] is not None:
                groups[-1].append(w)
            else:
                groups.append([w])
        for group in groups:
            if group:
                output.append({**u,'id':'auto-'+uuid.uuid4().hex,'start_ms':round(group[0]['start']*1000),
                    'end_ms':round(group[-1]['end']*1000),'text':''.join(w['word'] for w in group).strip(),
                    'source':{**metadata(u),'word_spans':group}})
    for row in protected:
        output.append({k:v for k,v in row.items() if k not in ('session_id','source_json')})
        output[-1]['source']=metadata(row)
    new_labels={}
    for key,name in labels.items():
        new_key=mapping[key]
        new_labels[new_key]=old['speakers'].get(new_key,name)
    for row in protected:
        if row.get('speaker_id'):
            new_labels[row['speaker_id']]=old['speakers'][row['speaker_id']]
    names=set(old['speakers'].values())
    for key,name in list(new_labels.items()):
        if key not in old['speakers']:
            number=1
            while f'Intervenant {number}' in names:
                number+=1
            new_labels[key]=f'Intervenant {number}'
            names.add(new_labels[key])
    ids=set()
    for u in output:
        if u['id'] in ids:
            u['id']='auto-'+uuid.uuid4().hex
        ids.add(u['id'])
    return sorted(output,key=lambda u:(u['start_ms'],u['end_ms'],u['id'])),new_labels
