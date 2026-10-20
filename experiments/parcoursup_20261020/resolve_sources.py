"""Resolve literal model quotes back to corrected/original fragment markers.

This resolves text spans, never proves that an argument follows from its citation.
Corrected words retain the original ASR time markers; no acoustic re-alignment.
"""
import re


def normalize(text):
    return ' '.join(text.split())


def resolve_quote(quote, turn, by_id):
    words = normalize(quote)
    if not words:
        return {'status':'empty_quote','matches':[]}
    spans, parts, position = [], [], 0
    for source_id in turn['source_ids']:
        piece = normalize(by_id[source_id]['text'])
        if parts: position += 1
        spans.append((position,position+len(piece),source_id))
        parts.append(piece); position += len(piece)
    text = ' '.join(parts)
    matches = []
    for found in re.finditer('(?='+re.escape(words)+')',text):
        start,end=found.start(),found.start()+len(words)
        ids=[key for left,right,key in spans if right>start and left<end]
        matches.append({'source_ids':ids,'start_ms_marker':min(by_id[k]['start_ms'] for k in ids),
                        'end_ms_marker':max(by_id[k]['end_ms'] for k in ids)})
    return {'status':'literal_unique' if len(matches)==1 else 'literal_ambiguous' if matches else 'not_literal',
            'matches':matches,'time_precision':'Original segment markers, not corrected-word alignment.'}


def resolve_result(result, inputs):
    turns={r['id']:r for r in inputs['turns']}
    by_id={r['id']:r for r in inputs['passages']}
    return {'semantic_fidelity_proved':False,'citations':[
        {'index':i,**q,**(resolve_quote(q['citation'],turns[q['source_id']],by_id)
            if q['source_id'] in turns else {'status':'unknown_turn','matches':[]})}
        for i,q in enumerate(result['citations_sources'])]}
