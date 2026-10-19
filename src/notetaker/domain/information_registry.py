"""Loss-aware information ledger. A machine opinion is never human approval."""
import copy
import json
import uuid
from notetaker.domain.minutes import content_digest

TYPES = {'argument':'Argument','question':'Question','answer':'Réponse',
         'proposal':'Proposition','objection':'Objection','potential_decision':'Décision potentielle',
         'context':'Contexte','position':'Position'}
RELATIONS = {'answers':'Répond à','agrees':'Accord avec','disagrees':'Désaccord avec',
             'objects_to':'Objection à','context':'Contexte de'}
VERIFICATION = {'supported','ambiguous','insufficient','rejected','pending'}
HUMAN = {'pending','approved','excluded'}


def stable_id(session_id, category, value):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'notetaker:registry:'+session_id+':'+category+':'+content_digest(value)))


def source_fingerprint(state):
    return content_digest({'utterances':state['utterances'],'speakers':state['speakers']})


def source_metadata(u):
    value=u.get('source',u.get('source_json',{}))
    return json.loads(value) if isinstance(value,str) else value


def author_state(refs, state):
    by_id={u['id']:u for u in state['utterances']}
    sources=[by_id[e['id']] for e in refs if e['id'] in by_id]
    voices={u.get('speaker_id') or 'unattributed' for u in sources}
    if len(voices)!=1 or 'unattributed' in voices:return 'unknown'
    if any(u.get('uncertain',True) for u in sources):return 'uncertain'
    return 'confirmed' if all(source_metadata(u).get('automatic_attribution',True) is False for u in sources) else 'automatic'


def seed_registry(session_id,state):
    sources=copy.deepcopy(state['utterances'])
    entries=[]
    for u in sources:
        entries.append({'id':stable_id(session_id,'source',u['id']),'category':'source',
            'subject':'À classer','type':'context','speaker':u.get('speaker_id') or 'unattributed',
            'author_status':author_state([{'id':u['id']}],state),'content':u['text'],
            'evidence':[{'id':u['id'],'quote':u['text'],'start_ms':u['start_ms'],'end_ms':u['end_ms']}],
            'verification':'pending','human_status':'pending','reasons':['not_analyzed'],
            'checks':{},'relations':[],'history':[]})
    return {'schema_version':1,'session_id':session_id,'source_sha256':source_fingerprint(state),
            'sources':sources,'speakers':copy.deepcopy(state['speakers']),
            'entries':entries,'relations':[],'processing':{'status':'seeded'},'writing':{}}


def evidence_issues(entry,state):
    issues=[];by_id={u['id']:u for u in state['utterances']}
    if not entry.get('evidence'):return ['missing_evidence']
    normalize=lambda s:' '.join(s.split())
    for e in entry['evidence']:
        source=by_id.get(e.get('id'))
        if source is None:issues.append('missing_source');continue
        if not e.get('quote','').strip() or normalize(e['quote']) not in normalize(source['text']):issues.append('quote_not_in_source')
        if (source.get('speaker_id') or 'unattributed')!=entry.get('speaker'):issues.append('mixed_or_wrong_speaker')
        if e.get('start_ms')!=source['start_ms'] or e.get('end_ms')!=source['end_ms']:issues.append('source_time_changed')
    return list(dict.fromkeys(issues))


def admissible(entry,state):
    if entry['category']!='information' or entry['human_status']=='excluded':return False
    if entry['type']=='potential_decision':return False  # Remains a manual municipal decision.
    if evidence_issues(entry,state) or ambiguous_origin(entry,state):return False
    if entry['speaker']=='unattributed':return False
    if entry['author_status'] in {'uncertain','unknown'} and entry['human_status']!='approved':return False
    # Approval may resolve a machine doubt, never a missing/wrong source.
    return entry['human_status']=='approved' or entry['verification']=='supported'


def ambiguous_origin(entry,state):
    if any(h['action']=='edit' for h in entry.get('history',[])):return False
    origin=entry.get('origin',{});ids=origin.get('unit_source_ids',[])
    quote=' '.join(origin.get('raw_candidate',{}).get('quote','').strip().strip('«»"').split())
    if not ids or not quote:return False
    by_id={u['id']:u for u in state['utterances']}
    text=' '.join(' '.join(by_id[sid]['text'].split()) for sid in ids if sid in by_id)
    start=text.find(quote)
    return start>=0 and text.find(quote,start+1)>=0


def to_claim(entry):
    return {'id':entry['id'],'speaker':entry['speaker'],
        'kind':{'answer':'argument','objection':'argument','potential_decision':'reported_decision'}.get(entry['type'],entry['type']),
        'discourse':entry.get('discourse','own'),'text':entry['content'],
        'evidence':[{'id':e['id'],'quote':e['quote']} for e in entry['evidence']],
        'machine_verdict':'supported_not_human_verified' if entry['human_status']!='approved' else 'registry_human_checked_requires_document_review'}


def validate_registry(document):
    if document.get('schema_version')!=1:raise ValueError('REGISTRY_SCHEMA_INVALID')
    state={'utterances':document['sources'],'speakers':document['speakers']}
    if source_fingerprint(state)!=document['source_sha256']:raise ValueError('REGISTRY_SNAPSHOT_CHANGED')
    ids=[e['id'] for e in document['entries']]
    if len(ids)!=len(set(ids)):raise ValueError('REGISTRY_DUPLICATE_ID')
    raw=[e['evidence'][0]['id'] for e in document['entries'] if e['category']=='source']
    if sorted(raw)!=sorted(u['id'] for u in document['sources']):raise ValueError('REGISTRY_SOURCE_INVENTORY_INCOMPLETE')
    by_id={e['id']:e for e in document['entries']}
    for entry in document['entries']:
        if entry['verification'] not in VERIFICATION or entry['human_status'] not in HUMAN or entry['type'] not in TYPES:
            raise ValueError('REGISTRY_SCHEMA_INVALID')
        if not isinstance(entry['content'],str) or not entry['subject'].strip():raise ValueError('REGISTRY_SCHEMA_INVALID')
        issues=evidence_issues(entry,state)
        if entry['category']=='source' and not entry['content'].strip():issues=[i for i in issues if i!='quote_not_in_source']
        if issues and (entry['verification']=='supported' or entry['human_status']=='approved'):
            raise ValueError('REGISTRY_INVALID_APPROVED_SOURCE')
    for relation in document['relations']:
        if relation['from'] not in by_id or relation['to'] not in by_id or relation['from']==relation['to'] or relation['kind'] not in RELATIONS:
            raise ValueError('REGISTRY_RELATION_INVALID')
        if relation['verification']=='supported' or relation['human_status']=='approved':
            endpoints=[by_id[relation[k]] for k in ['from','to']]
            key=lambda e:(e.get('id'),e.get('quote'),e.get('start_ms'),e.get('end_ms'))
            cited={key(e) for e in relation.get('evidence',[])}
            if not all({key(e) for e in endpoint['evidence']}<=cited for endpoint in endpoints):
                raise ValueError('REGISTRY_RELATION_SOURCES_REQUIRED')
            if any(evidence_issues(endpoint,state) for endpoint in endpoints):raise ValueError('REGISTRY_RELATION_INVALID')
    return document


def coverage(document):
    """Exact citation accounting only: no assertion of thematic completeness."""
    entries=[e for e in document['entries'] if e['category']=='information']
    cited={e['id'] for entry in entries for e in entry['evidence'] if not evidence_issues(entry,{'utterances':document['sources']})}
    eligible=[e for e in entries if admissible(e,{'utterances':document['sources']})]
    return {'source_segments':len(document['sources']),'source_segments_with_candidate_citation':len(cited),
        'source_segments_without_candidate_citation':len(document['sources'])-len(cited),
        'information_entries':len(entries),'eligible_information_entries':len(eligible),
        'to_verify_information_entries':sum(e['human_status']!='excluded' and not admissible(e,{'utterances':document['sources']}) for e in entries),
        'excluded_information_entries':sum(e['human_status']=='excluded' for e in entries),
        'semantic_coverage_measured':False}


def validate_generation_input(request):
    """Retain legacy input gates at the new worker boundary, before inference."""
    from notetaker.domain.summary import PROFILES,validate_lexicon
    utterances=request.get('utterances',[])
    if not utterances:raise ValueError('TRANSCRIPT_REQUIRED')
    if any('\ufffd' in u['text'] for u in utterances):raise ValueError('DAMAGED_TRANSCRIPT_RETRANSCRIBE_ORIGINAL')
    validate_lexicon(request.get('lexicon',[]))
    if request.get('task')=='registry_write' and request.get('summary_length','standard') not in PROFILES:
        raise ValueError('INVALID_SUMMARY_LENGTH')
    document=request['registry'];validate_registry(document)
    fields=['id','text','speaker_id','start_ms','end_ms','uncertain']
    project=lambda values:[{k:u.get(k) for k in fields} for u in values]
    if project(utterances)!=project(document['sources']):raise ValueError('REGISTRY_SNAPSHOT_CHANGED')
