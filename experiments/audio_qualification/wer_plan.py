"""Derived WER portions. Never writes the original human-reference database."""
import copy
import json
import re
import sqlite3
import unicodedata
import uuid
from .core import WORK,QualificationError,digest,read,review_valid,tokens,utc

PLAN_PATH=WORK/'decoupages-wer.sqlite'
EPS=1e-7


def merge(ranges):
    result=[]
    for a,b in sorted(ranges):
        if b<=a+EPS:continue
        if result and a<=result[-1][1]+EPS:result[-1][1]=max(result[-1][1],b)
        else:result.append([a,b])
    return result


def subtract(ranges,excluded):
    result=[]
    for a,b in merge(ranges):
        cursor=a
        for c,d in merge(excluded):
            if d<=cursor or c>=b:continue
            if c>cursor:result.append([cursor,min(c,b)])
            cursor=max(cursor,d)
        if cursor<b-EPS:result.append([cursor,b])
    return result


def overlaps(zone):
    # Distinct simultaneous human voices only. A broad tag does not exclude 40 s.
    return merge((max(a['start'],b['start']),min(a['end'],b['end'])) for i,a in enumerate(zone['turns'])
                 for b in zone['turns'][i+1:] if a['speaker']!=b['speaker'])


def token_view(text):
    """NFC display + token spans; indices refer to the immutable human token list."""
    view=unicodedata.normalize('NFC',text)
    spans=[(m.start(),m.end()) for m in re.finditer(r"[^\W_]+(?:\s*['’]\s*[^\W_]+)*",view)]
    if [tokens(view[a:b])[0] for a,b in spans]!=tokens(text):
        raise QualificationError('Le texte contient une forme lexicale inhabituelle ; corrigez-la humainement dans le verbatim avant le découpage.')
    return view,spans


def selection_tokens(text,start,end):
    view,spans=token_view(text)
    selected=[i for i,(a,b) in enumerate(spans) if a<end and b>start]
    if not selected:raise QualificationError('Sélectionnez les mots humains correspondant au passage écouté.')
    return selected[0],selected[-1]+1


def coverage(project,dataset):
    result=[];h=project['audio']['sha256']
    for z in project['zones']:
        if not (review_valid(z,'text',h) or review_valid(z,'diarization',h)):continue
        speech=merge((t['start'],t['end']) for t in z['turns']);ov=overlaps(z)
        gaps=[] if z['silence'] else subtract([[z['start'],z['end']]],speech)
        holes=[]
        for a,b in gaps:
            engines={}
            for key,c in dataset['chains'].items():
                intervals=merge((max(a,s['start']),min(b,s['end'])) for s in c['asr'] if s.get('text','').strip())
                if intervals:engines[key]=intervals
            holes.append({'start':a,'end':b,'duration':b-a,'speech_detected_by':engines,
                'status':'parole détectée sans annotation de voix' if engines else 'silence ou parole non annotée à vérifier',
                'not_human_confirmed_silence':True})
        result.append({'zone':z['id'],'start':z['start'],'end':z['end'],
            'human_speech_union':speech,'real_human_overlaps':ov,'sequential_speech':subtract(speech,ov),
            'uncovered':holes,'uncovered_seconds':sum(b-a for a,b in gaps),
            'annotation_is_unchanged':True})
    return result


def suggest_tokens(zone,a,b,chain):
    # A MODEL-guided proposal only, never a scored reference until human approval.
    from .scoring import lexical_clock,words_in_zone,edit_alignment
    words,_=words_in_zone(lexical_clock(chain['asr']),zone)
    ref=tokens(zone['verbatim']);hyp=[w['text'] for w in words]
    pairs=edit_alignment(ref,hyp)['operations'];chosen=[]
    for op,i,j in pairs:
        if i is not None and j is not None and words[j]['start'] is not None:
            if a<=(words[j]['start']+words[j]['end'])/2<b:chosen.append(i)
    return (min(chosen),max(chosen)+1) if chosen else (0,0)


def prepare(project,dataset):
    info=coverage(project,dataset);blocks=[];h=project['audio']['sha256']
    for entry in info:
        z=next(z for z in project['zones'] if z['id']==entry['zone'])
        if not review_valid(z,'text',h):continue
        needs=bool(entry['real_human_overlaps']) or ('chevauchement' in z['tags'] and not review_valid(z,'diarization',h))
        if not needs:continue
        ranges=[(a,b,'sequential') for a,b in entry['sequential_speech']]
        ranges += [(r['start'],r['end'],'uncovered') for r in entry['uncovered']]
        if not ranges:ranges=[(z['start'],z['end'],'uncovered')]
        for i,(a,b,kind) in enumerate(sorted(ranges)):
            first,last=suggest_tokens(z,a,b,dataset['chains'].get('large',next(iter(dataset['chains'].values()))))
            blocks.append({'id':z['id']+f'-P{i+1:02d}','zone':z['id'],'start':a,'end':b,'kind':kind,
                'first_token':first,'last_token':last,'approval':None,'proposal_origin':'ASR-guided boundaries in human text; not truth',
                'classification':'sequential'})
    return {'schema':1,'reference_sha256':digest(project),'audio_sha256':h,'blocks':blocks,'coverage':info}


def block_payload(block):return {k:block[k] for k in ('id','zone','start','end','kind','first_token','last_token','classification')}


def approved(block):
    r=block.get('approval')
    return bool(r and r.get('reviewer','').strip() and r.get('heard_complete') is True and r.get('content_sha256')==digest(block_payload(block)))


def validate_plan(project,plan):
    if plan['reference_sha256']!=digest(project) or plan['audio_sha256']!=project['audio']['sha256']:
        raise QualificationError('Ce découpage appartient à une autre révision humaine. Préparez un nouveau découpage ; les anciens accords restent conservés.')
    zones={z['id']:z for z in project['zones']};accepted=[];ids=[]
    for block in plan['blocks']:
        ids.append(block['id']);z=zones.get(block['zone'])
        if z is None or not z['start']<=block['start']<block['end']<=z['end']:raise QualificationError('Le passage doit rester dans sa zone d’origine.')
        if block['classification'] not in ('sequential','silence'):raise QualificationError('Classification de passage inconnue.')
        if not 0<=block['first_token']<=block['last_token']<=len(tokens(z['verbatim'])):raise QualificationError('Sélection de texte invalide.')
        if block.get('approval') is not None and not approved(block):raise QualificationError('Validation de passage périmée.')
        if block.get('approval') is not None and block['approval'].get('reference_sha256')!=digest(project):
            raise QualificationError('Cette validation de passage appartient à une autre référence humaine.')
        if not approved(block):continue
        if any(min(block['end'],b)>max(block['start'],a)+EPS for a,b in overlaps(z)):
            raise QualificationError('Ce passage recouvre deux voix humaines simultanées. Ajustez ses bornes ; aucune annotation ne sera changée automatiquement.')
        if block['classification']=='sequential' and block['first_token']==block['last_token']:
            raise QualificationError('Rattachez le passage séquentiel aux mots correspondants du verbatim humain.')
        if block['classification']=='silence' and block['first_token']!=block['last_token']:
            raise QualificationError('Un silence vérifié ne doit pas contenir de mots sélectionnés.')
        if block['classification']=='silence' and any(min(block['end'],t['end'])>max(block['start'],t['start'])+EPS for t in z['turns']):
            raise QualificationError('Ce silence contredit un tour de parole humain. Corrigez vous-même ce tour si nécessaire ; il ne sera pas effacé automatiquement.')
        for previous in accepted:
            if min(block['end'],previous['end'])>max(block['start'],previous['start'])+EPS:raise QualificationError('Deux passages validés se recouvrent dans l’audio.')
            if block['zone']==previous['zone'] and min(block['last_token'],previous['last_token'])>max(block['first_token'],previous['first_token']):
                raise QualificationError('Les mêmes mots humains sont utilisés dans deux passages ; corrigez la sélection.')
        accepted.append(block)
    if len(ids)!=len(set(ids)):raise QualificationError('Identifiants de passages dupliqués.')


def approve_block(project,plan,identifier,reviewer,heard):
    if not reviewer.strip() or heard is not True:raise QualificationError('Indiquez votre nom et confirmez l’écoute du passage, ses bornes et le texte sélectionné.')
    candidate=copy.deepcopy(plan);block=next(b for b in candidate['blocks'] if b['id']==identifier)
    block['approval']={'reviewer':reviewer.strip(),'utc':utc(),'heard_complete':True,
        'content_sha256':digest(block_payload(block)),'reference_sha256':digest(project),
        'word_times_required':False}
    validate_plan(project,candidate);return candidate


class PlanStore:
    """Own append-only database; the original annotation DB is never opened here."""
    def __init__(self,path=PLAN_PATH):
        from pathlib import Path
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            c=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)
            try:
                if c.execute('PRAGMA application_id').fetchone()[0]!=0x4E545750:raise QualificationError('Ce fichier n’est pas un registre de découpages WER.')
            finally:c.close()
        c=sqlite3.connect(self.path)
        try:
            c.execute('PRAGMA application_id=0x4E545750')
            c.executescript('CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,base TEXT NOT NULL,parent TEXT,created TEXT NOT NULL,payload TEXT NOT NULL,sha TEXT NOT NULL); CREATE TABLE IF NOT EXISTS heads(base TEXT PRIMARY KEY,id TEXT NOT NULL);')
            c.commit()
        finally:c.close()
    def load(self,project):return load_saved_plan(project,self.path)
    def save(self,project,value,parent):
        validate_plan(project,value);base=digest(project);rid=uuid.uuid4().hex;c=sqlite3.connect(self.path,timeout=10)
        try:
            c.execute('BEGIN IMMEDIATE');head=c.execute('SELECT id FROM heads WHERE base=?',(base,)).fetchone()
            if (head[0] if head else None)!=parent:raise QualificationError('Le découpage a changé dans une autre fenêtre. Fermez puis rouvrez ; aucune validation ne sera écrasée.')
            c.execute('INSERT INTO plans VALUES(?,?,?,?,?,?)',(rid,base,parent,utc(),json.dumps(value,ensure_ascii=False,allow_nan=False),digest(value)))
            c.execute('INSERT INTO heads VALUES(?,?) ON CONFLICT(base) DO UPDATE SET id=excluded.id',(base,rid));c.commit()
        except BaseException:c.rollback();raise
        finally:c.close()
        return rid


def load_saved_plan(project,path=PLAN_PATH):
    from pathlib import Path
    path=Path(path)
    if not path.exists():return None,None
    c=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        row=c.execute('SELECT p.id,p.payload,p.sha FROM heads h JOIN plans p ON h.id=p.id WHERE h.base=?',(digest(project),)).fetchone()
    finally:c.close()
    if not row:return None,None
    value=json.loads(row[1])
    if digest(value)!=row[2]:raise QualificationError('L’intégrité du découpage WER a échoué ; fichier conservé.')
    validate_plan(project,value);return row[0],value


def wer_units(project,dataset,plan=None):
    """Human zone review suffices without overlaps; splits need explicit approval."""
    from .scoring import lexical_clock,words_in_zone
    if plan is not None:validate_plan(project,plan)
    diagnostics=coverage(project,dataset);by_zone={d['zone']:d for d in diagnostics}
    clocks={k:lexical_clock(c['asr']) for k,c in dataset['chains'].items()}
    units=[];pending=[];h=project['audio']['sha256']
    proposed=prepare(project,dataset)
    for z in project['zones']:
        if not review_valid(z,'text',h) or z['unintelligible']:continue
        d=by_zone[z['id']]
        needs=bool(d['real_human_overlaps']) or ('chevauchement' in z['tags'] and not review_valid(z,'diarization',h))
        if not needs:candidates=[{**z,'source_zone':z['id'],'reference_token_range':[0,len(tokens(z['verbatim']))],'portion_review':None}]
        else:
            candidates=[]
            for block in (plan or proposed)['blocks']:
                if block['zone']!=z['id']:continue
                if not approved(block):
                    pending.append({'zone':z['id'],'portion':block['id'],'start':block['start'],'end':block['end'],
                        'reason':'Découpage et texte à valider à l’écoute, sans horodater les mots.','WER':None});continue
                ref=tokens(z['verbatim'])[block['first_token']:block['last_token']]
                candidates.append({**z,'id':block['id'],'source_zone':z['id'],'start':block['start'],'end':block['end'],
                    'verbatim':' '.join(ref),'reference_token_range':[block['first_token'],block['last_token']],
                    'portion_review':block['approval'],'silence':block['classification']=='silence'})
        for part in candidates:
            if any(words_in_zone(words,part)[1] for words in clocks.values()):
                pending.append({'zone':z['id'],'portion':part['id'],'start':part['start'],'end':part['end'],
                    'reason':'Un moteur ne fournit pas les horaires de mots traversant une borne : ajustez et validez les bornes sur une pause. Aucun horaire humain de mot requis.','WER':None})
            else:units.append(part)
    return units,pending,diagnostics,proposed
