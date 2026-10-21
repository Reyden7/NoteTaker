"""Independent human annotations. No inference, no NoteTaker session imports."""
import copy
import hashlib
import json
import math
import re
import sqlite3
import unicodedata
import uuid
from datetime import datetime,timezone
from contextlib import contextmanager
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BENCH=ROOT/'output/audio-benchmark/2026-10-20-01'
WORK=ROOT/'output/audio-qualification/2026-10-20-01'
TAGS=('interruption','chevauchement','passage court','nom propre')
DOMAINS=('text','diarization','word_times')
SOURCES={
    'small_asr':BENCH/'runs/A-cpu-v2/full/asr-result.json',
    'small_diar':BENCH/'runs/A-cpu-v2/full/sherpa-result.json',
    'small_display':BENCH/'runs/A-cpu-v2/full/transcript.json',
    'large_asr':BENCH/'runs/large-cuda-main/full/result.json',
    'community':BENCH/'runs/community-cuda-main/full/result.json',
    'whisperx':BENCH/'runs/alignment-cuda-main/full/result.json',
    'performance':BENCH/'chain-totals.json',
    **{v:BENCH/f'combined/B-cuda/full/{v}.json' for v in
       ('without-whisperx-standard','without-whisperx-exclusive','with-whisperx-standard','with-whisperx-exclusive')},
}


class QualificationError(ValueError):pass


def utc():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()


def tokens(text):
    text=unicodedata.normalize('NFC',text).casefold().replace('’',"'")
    text=re.sub(r"\s*'\s*","'",text)
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*",text,re.UNICODE)


def blank_zone(identifier,start,end,title=''):
    return {'id':identifier,'title':title or identifier,'start':float(start),'end':float(end),
        'verbatim':'','turns':[],'words':[],'tags':[],'notes':[],
        'silence':False,'unintelligible':False,'hypotheses_seen':False,
        'reviews':{d:None for d in DOMAINS}}


def initial_project():
    manifest=read(BENCH/'manifest.json')
    audio=BENCH/'audio/full.wav'
    if sha(audio)!=manifest['source_audio_sha256']:raise QualificationError('Le fichier audio a changé depuis le benchmark.')
    selection=read(BENCH/'references/annotations-12-extraits-originales.json')
    return {'schema':1,'id':str(uuid.uuid4()),'created_utc':utc(),
        'audio':{'path':str(audio),'sha256':sha(audio),'duration':manifest['cases']['full']['duration_seconds']},
        'sources':{key:{'path':str(path),'sha256':sha(path)} for key,path in SOURCES.items()},
        'voices':[], 'zones':[blank_zone(e['id'],e['start_ms']/1000,e['end_ms']/1000,e['id']+' · extrait de 40 s') for e in selection['excerpts']],
        'human_reference_origin':'Blank manual annotation; narrative/corrections are not imported as scoring truth.'}


def verify_inputs(project):
    for value in [project['audio'],*project['sources'].values()]:
        path=Path(value['path'])
        if not path.is_file() or sha(path)!=value['sha256']:
            raise QualificationError('Source absente ou modifiée : '+str(path)+'. Les annotations sont conservées ; le calcul est bloqué.')


def domain_payload(zone,domain):
    base={k:zone[k] for k in ('id','start','end','silence','unintelligible')}
    fields={'text':['verbatim'],'diarization':['turns'],'word_times':['verbatim','turns','words']}[domain]
    return {**base,**{k:zone[k] for k in fields}}


def review_valid(zone,domain,audio_hash):
    r=zone['reviews'].get(domain)
    return bool(r and r.get('reviewer','').strip() and r.get('heard_complete') is True
                and r.get('audio_sha256')==audio_hash and r.get('content_sha256')==digest(domain_payload(zone,domain)))


def update_zone(zone,**changes):
    result=copy.deepcopy(zone);result.update(copy.deepcopy(changes))
    for d in DOMAINS:
        if domain_payload(zone,d)!=domain_payload(result,d):result['reviews'][d]=None
    return result


def validate_project(project):
    if project.get('schema')!=1:raise QualificationError('Format d’annotation non pris en charge.')
    duration=project['audio']['duration']
    if not math.isfinite(duration) or duration<=0:raise QualificationError('Durée audio invalide.')
    voice_ids=[v['id'] for v in project['voices']]
    if len(set(voice_ids))!=len(voice_ids):raise QualificationError('Identifiants de voix humaines dupliqués.')
    ids=[];ranges=[]
    for z in project['zones']:
        ids.append(z['id']);a,b=z['start'],z['end']
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (a,b)) or not 0<=a<b<=duration:
            raise QualificationError(f"{z['id']} : limites de zone invalides (secondes absolues).")
        ranges.append((a,b,z['id']))
        if z['silence'] and (z['verbatim'].strip() or z['turns'] or z['words']):
            raise QualificationError(f"{z['id']} : une zone déclarée silencieuse contient du texte ou de la parole.")
        for row in z['turns']:
            if not all(isinstance(row.get(k),(int,float)) and math.isfinite(row[k]) for k in ('start','end')) or not a<=row['start']<row['end']<=b:
                raise QualificationError(f"{z['id']} : un tour de parole sort de la zone ou a une durée nulle.")
            if row.get('speaker') not in voice_ids:raise QualificationError(f"{z['id']} : sélectionnez une voix humaine pour chaque tour.")
        for w in z['words']:
            if len(tokens(w.get('text','')))!=1:raise QualificationError(f"{z['id']} : chaque ligne de mot doit contenir un seul mot lexical.")
            if w.get('speaker') is not None and w['speaker'] not in voice_ids:raise QualificationError(f"{z['id']} : voix de mot inconnue.")
            if (w.get('start') is None)!=(w.get('end') is None):raise QualificationError(f"{z['id']} : renseignez début ET fin du mot, ou laissez les deux vides.")
            if w.get('start') is not None and (not all(isinstance(w[k],(int,float)) and math.isfinite(w[k]) for k in ('start','end')) or not a<=w['start']<w['end']<=b):
                raise QualificationError(f"{z['id']} : horaires de mot invalides.")
        for d in DOMAINS:
            r=z['reviews'].get(d)
            if r is not None and not review_valid(z,d,project['audio']['sha256']):raise QualificationError(f"{z['id']} : validation périmée pour {d}.")
    if len(ids)!=len(set(ids)):raise QualificationError('Identifiants de zones dupliqués.')
    for previous,current in zip(sorted(ranges),sorted(ranges)[1:]):
        if current[0]<previous[1]-1e-8:raise QualificationError(f'Les zones {previous[2]} et {current[2]} se recouvrent. Réduisez leurs limites pour éviter un double comptage.')


def approve(project,zone_id,domain,reviewer,heard_complete):
    result=copy.deepcopy(project);z=next(z for z in result['zones'] if z['id']==zone_id)
    validate_project(result)
    if domain not in DOMAINS:raise QualificationError('Type de relecture inconnu.')
    if not reviewer.strip() or heard_complete is not True:raise QualificationError('Indiquez votre nom et confirmez l’écoute complète de cette zone.')
    if z['unintelligible']:raise QualificationError('Cette zone contient de l’inaudible : réduisez/scindez sa portée avant de la noter, sans deviner les mots.')
    if domain=='text' and not z['silence'] and not tokens(z['verbatim']):raise QualificationError('Saisissez le verbatim exhaustif, ou déclarez une zone entièrement silencieuse.')
    if domain=='diarization' and not z['silence'] and not z['turns']:raise QualificationError('Annotez tous les tours de parole et les silences par leurs frontières.')
    if domain=='word_times':
        if not review_valid(z,'text',result['audio']['sha256']) or not review_valid(z,'diarization',result['audio']['sha256']):
            raise QualificationError('Validez d’abord le texte et les tours de parole de cette zone.')
        if not z['words'] or [tokens(w['text'])[0] for w in z['words']]!=tokens(z['verbatim']):
            raise QualificationError('La liste des mots doit correspondre exactement au verbatim validé.')
        for w in z['words']:
            if w['start'] is None or w['speaker'] is None:raise QualificationError('Chaque mot doit avoir des horaires et une voix humaine, y compris pendant les chevauchements.')
            if not any(t['speaker']==w['speaker'] and t['start']<=w['start'] and t['end']>=w['end'] for t in z['turns']):
                raise QualificationError('Un mot ne se trouve pas dans un tour de parole de sa voix humaine.')
    z['reviews'][domain]={'reviewer':reviewer.strip(),'utc':utc(),'heard_complete':True,
        'content_sha256':digest(domain_payload(z,domain)),'audio_sha256':result['audio']['sha256'],
        'hypotheses_seen_before_review':z['hypotheses_seen'],
        'origin':'manual_audio_annotation_not_engine_selected_as_truth'}
    return result


class ReferenceStore:
    """Dedicated SQLite file: append-only snapshots, transaction + optimistic locking."""
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            check=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)
            try:
                if check.execute('PRAGMA application_id').fetchone()[0]!=0x4E544151:
                    raise QualificationError('Ce fichier n’est pas une référence du laboratoire. Choisissez un nouveau fichier ; aucune base NoteTaker ne doit être réutilisée.')
                if check.execute('PRAGMA user_version').fetchone()[0]!=1:raise QualificationError('Version de référence humaine incompatible ; fichier conservé.')
            finally:check.close()
        with self.connect() as c:
            c.execute('PRAGMA application_id=0x4E544151');c.execute('PRAGMA user_version=1')
            c.executescript('''CREATE TABLE IF NOT EXISTS revisions(
                id TEXT PRIMARY KEY,parent TEXT REFERENCES revisions(id),created TEXT NOT NULL,
                author TEXT NOT NULL,event TEXT NOT NULL,payload TEXT NOT NULL,sha256 TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS head(singleton INTEGER PRIMARY KEY CHECK(singleton=1),revision TEXT NOT NULL REFERENCES revisions(id));''')
            c.execute('CREATE TABLE IF NOT EXISTS drafts(id INTEGER PRIMARY KEY,base_revision TEXT NOT NULL,zone TEXT NOT NULL,payload TEXT NOT NULL,created TEXT NOT NULL)')
            # Monotonic provenance survives restoring an older reference snapshot.
            c.execute('CREATE TABLE IF NOT EXISTS exposures(audio_sha256 TEXT NOT NULL,zone TEXT NOT NULL,first_seen TEXT NOT NULL,PRIMARY KEY(audio_sha256,zone))')
            for payload,created in c.execute('SELECT payload,created FROM revisions WHERE event LIKE ?',('%Hypothèses affichées%',)).fetchall():
                old=json.loads(payload)
                for z in old['zones']:
                    if z['hypotheses_seen']:c.execute('INSERT OR IGNORE INTO exposures VALUES(?,?,?)',(old['audio']['sha256'],z['id'],created))
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=10);c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA synchronous=FULL')
        try:
            with c:yield c
        finally:c.close()
    def load(self):
        with self.connect() as c:
            row=c.execute('SELECT r.id,r.payload,r.sha256 FROM head h JOIN revisions r ON h.revision=r.id').fetchone()
        if row is None:return None,None
        value=json.loads(row[1])
        if digest(value)!=row[2]:raise QualificationError('Le contrôle d’intégrité de la référence humaine a échoué. Conservez le fichier pour récupération.')
        return row[0],value
    def save(self,value,parent,author,event):
        validate_project(value);rid=str(uuid.uuid4());payload=canonical(value)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            current=c.execute('SELECT revision FROM head WHERE singleton=1').fetchone()
            if (current[0] if current else None)!=parent:raise QualificationError('La référence a été modifiée dans une autre fenêtre. Fermez puis rouvrez pour retrouver la dernière révision ; votre saisie reste affichée.')
            c.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?,?)',(rid,parent,utc(),author,event,payload,digest(value)))
            c.execute('INSERT INTO head VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET revision=excluded.revision',(rid,))
            for z in value['zones']:
                if z['hypotheses_seen']:c.execute('INSERT OR IGNORE INTO exposures VALUES(?,?,?)',(value['audio']['sha256'],z['id'],utc()))
        return rid
    def retain_exposure(self,value):
        value=copy.deepcopy(value)
        with self.connect() as c:seen={r[0] for r in c.execute('SELECT zone FROM exposures WHERE audio_sha256=?',(value['audio']['sha256'],))}
        for z in value['zones']:
            if z['id'] in seen:z['hypotheses_seen']=True
        return value
    def history(self):
        with self.connect() as c:return c.execute('SELECT id,created,author,event FROM revisions ORDER BY rowid DESC').fetchall()
    def snapshot(self,rid):
        with self.connect() as c:r=c.execute('SELECT payload,sha256 FROM revisions WHERE id=?',(rid,)).fetchone()
        if not r:raise QualificationError('Révision absente.')
        value=json.loads(r[0])
        if digest(value)!=r[1]:raise QualificationError('Révision endommagée.')
        return value
    def save_draft(self,parent,zone,payload):
        with self.connect() as c:c.execute('INSERT INTO drafts(base_revision,zone,payload,created) VALUES(?,?,?,?)',(parent,zone,canonical(payload),utc()))
    def recover_draft(self,parent):
        with self.connect() as c:r=c.execute('SELECT zone,payload FROM drafts WHERE base_revision=? ORDER BY id DESC LIMIT 1',(parent,)).fetchone()
        return (r[0],json.loads(r[1])) if r else None


def load_dataset(project):
    verify_inputs(project)
    raw={k:read(v['path']) for k,v in project['sources'].items()}
    def result(key):return raw[key]['result']
    small=result('small_asr')['segments'];large=result('large_asr')['segments']
    return {'audio':project['audio'],'performance':raw['performance'],'chains':{
        'small':{'name':'Small + sherpa','asr':small,'clock':small,'diarization':result('small_diar')['turns'],
                 'standard':raw['small_display']['segments'],'exclusive':raw['small_display']['segments']},
        'large':{'name':'Large-v3 + Community-1','asr':large,'clock':large,'diarization':result('community')['turns'],
                 'standard':raw['without-whisperx-standard']['segments'],'exclusive':raw['without-whisperx-exclusive']['segments']},
        'whisperx':{'name':'Large-v3 + WhisperX + Community-1','asr':large,'clock':result('whisperx')['segments'],
                 'diarization':result('community')['turns'],'standard':raw['with-whisperx-standard']['segments'],
                 'exclusive':raw['with-whisperx-exclusive']['segments']}}}
