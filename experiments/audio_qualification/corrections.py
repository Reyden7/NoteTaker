"""Small operator task list and explicit incremental corrections. No inference."""
import copy
import json
import sqlite3
import uuid
from contextlib import closing
from .core import (digest,utc,tokens,review_valid,update_zone,approve,validate_project,QualificationError)
from .wer_plan import approved,validate_plan,wer_units
from .audit_metrics import qualified_activity

BFMTV_SHA='95da1f0787fd22ad313acfd367fda3012b47587660cb9b1a2d6e6001bf0e708a'


def tasks(project,dataset,plan=None):
    result=[];byid={b['id']:b for b in (plan or {}).get('blocks',[])}
    if project['audio']['sha256']==BFMTV_SHA:
        b=byid.get('E11-P01');z=next((z for z in project['zones'] if z['id']=='E11'),None)
        if b and z and b['last_token']==60 and len(tokens(z['verbatim']))>=99:
            result.append({'id':'bfmtv-E11-selection','kind':'wer','zone':'E11','portion':'E11-P01','start':b['start'],'end':b['end'],
                'title':'E11-P01 · 39 mots hors sélection','suggested_range':[b['first_token'],99],
                'detail':'Écouter notamment 18:26–18:34. Les mots [60,99), « non non atendez… mais avant », sont dans le verbatim mais hors WER. Vérifier leur rattachement ; la proposition élargie reste à valider. Aucun mot à retaper.'})
        for ids,title in [(['E12-P01','E12-P03'],'E12 · question initiale et début de réponse'),
                          (['E12-P04','E12-P05','E12-P06'],'E12 · frontières question, exemple et réponse sur les notes')]:
            blocks=[byid[k] for k in ids if k in byid]
            if blocks:result.append({'id':'bfmtv-'+ids[0]+'-boundaries','kind':'wer','zone':'E12','portion':blocks[0]['id'],
                'portions':[b['id'] for b in blocks],'start':blocks[0]['start'],'end':blocks[-1]['end'],'title':title,
                'detail':'Vérifier les bornes et les mots déjà sélectionnés, en particulier « c’est une vraie question » et le passage à « la sélection ne se fait… ». Ne pas réécrire le verbatim. Corriger uniquement si l’écoute confirme le décalage.'})
    _,holes,_=qualified_activity(project,plan)
    for gap in holes:
        result.append({'id':f"voices-{gap['zone']}-{gap['start']:.3f}-{gap['end']:.3f}",'kind':'voices',
            'zone':gap['zone'],'start':gap['start'],'end':gap['end'],
            'title':f"{gap['zone']} · voix non attribuées ({gap['seconds']:.3f} s)",
            'detail':'Écouter cette plage, ajouter les tours et choisir les voix humaines. Plusieurs lignes si elles se chevauchent. Le texte validé est conservé. Ne pas déduire un nom d’un identifiant moteur.'})
    if 'municipal_source' in project:
        for z in project['zones']:
            reviewed=all(review_valid(z,d,project['audio']['sha256']) for d in ('text','diarization'))
            result.append({'id':'municipal-'+z['id'],'kind':'qualitative' if reviewed else 'reference','zone':z['id'],
                'start':z['start'],'end':z['end'],'title':z['id']+(' · attribution et informations importantes' if reviewed else ' · première annotation courte'),
                'detail':'Écouter les mots et les voix sans choisir un moteur comme vérité. Vérifier surtout les propositions, la délibération et le vote s’ils sont présents. Consigner séparément les attributions qui changent le sens. Aucun vote n’est supposé.'})
    from .wer_plan import block_payload
    for t in result:
        z=next(z for z in project['zones'] if z['id']==t['zone'])
        ids=t.get('portions',[t.get('portion')])
        t['context_sha256']=digest({'text':z['verbatim'],'task':{k:v for k,v in t.items() if k!='context_sha256'},
            'blocks':[block_payload(byid[i]) for i in ids if i in byid]})
    return result


def add_reviewed_gap(project,zone_id,start,end,turns,reviewer,heard):
    """Explicit human act: retain reviewed activity, add heard turns only in a gap."""
    from .wer_plan import subtract
    validate_project(project);z=next(z for z in project['zones'] if z['id']==zone_id)
    if not review_valid(z,'diarization',project['audio']['sha256']):
        raise QualificationError('Les tours existants doivent être revus avant une correction locale. Le verbatim reste conservé.')
    gaps=subtract([(z['start'],z['end'])],[(t['start'],t['end']) for t in z['turns']])
    if not any(a<=start<end<=b for a,b in gaps):raise QualificationError('La correction doit rester dans une plage sans tour humain existant.')
    if not turns:raise QualificationError('Ajouter au moins un tour de voix ; aucun silence ne sera supposé.')
    for t in turns:
        if not start<=t['start']<t['end']<=end:raise QualificationError('Chaque nouveau tour doit rester dans la plage écoutée.')
    new=copy.deepcopy(project);index=next(i for i,t in enumerate(new['zones']) if t['id']==zone_id)
    new['zones'][index]=update_zone(z,turns=sorted(z['turns']+copy.deepcopy(turns),key=lambda t:(t['start'],t['end'])))
    new=approve(new,zone_id,'diarization',reviewer,heard)
    new['zones'][index]['reviews']['diarization']['incremental_review']={
        'base_review':copy.deepcopy(z['reviews']['diarization']),'unchanged_existing_turns_sha256':digest(z['turns']),
        'heard_interval':[start,end],'new_turns':copy.deepcopy(turns),
        'scope':'Earlier reviewed turns retained verbatim; new gap activity explicitly reviewed by operator.'}
    validate_project(new);return new


def carry_unchanged_plan(old,new,plan,reviewer,confirmed,dataset=None):
    """User must explicitly authorize carrying unchanged approvals to a new ref."""
    validate_plan(old,plan)
    if not confirmed or not reviewer.strip():raise QualificationError('Confirmez explicitement la conservation des validations WER inchangées et indiquez votre nom.')
    if old['audio']!=new['audio']:raise QualificationError('Audio différent : nouvel examen WER nécessaire.')
    oz={z['id']:z for z in old['zones']};nz={z['id']:z for z in new['zones']}
    for zid in {b['zone'] for b in plan['blocks']}:
        if zid not in nz or any(oz[zid][k]!=nz[zid][k] for k in ('verbatim','start','end','silence','unintelligible')):
            raise QualificationError('Le texte ou les bornes ont changé : les validations ne peuvent pas être transférées en bloc.')
    result=copy.deepcopy(plan);result.update(reference_sha256=digest(new),audio_sha256=new['audio']['sha256'])
    from .wer_plan import coverage
    result['coverage']=coverage(new,dataset if dataset is not None else {'chains':{}})
    result['coverage_without_model_evidence']=dataset is None
    for b in result['blocks']:b['approval']=None
    invalid=[]
    for oldb,b in zip(plan['blocks'],result['blocks']):
        if not approved(oldb):continue
        b['approval']={**copy.deepcopy(oldb['approval']),'reference_sha256':digest(new),
            'carried_forward':{'by':reviewer.strip(),'utc':utc(),'base_reference_sha256':digest(old),
                'original_approval':copy.deepcopy(oldb['approval']),'explicit_operator_confirmation':True}}
        try:validate_plan(new,result)
        except QualificationError as e:
            b['approval']=None;b['invalidation_reason']=str(e);invalid.append({'portion':b['id'],'reason':str(e)})
    validate_plan(new,result);return result,invalid


class TaskLog:
    """Separate append-only operator actions, never a reference or metric truth."""
    def __init__(self,path):
        from pathlib import Path
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            with closing(sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)) as c:
                if c.execute('PRAGMA application_id').fetchone()[0]!=0x4E545443:raise QualificationError('Ce fichier n’est pas un journal de corrections du laboratoire.')
        with closing(sqlite3.connect(self.path)) as c,c:
            c.execute('PRAGMA application_id=0x4E545443')
            c.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,created TEXT NOT NULL,payload TEXT NOT NULL)')
    def append(self,project,task,reviewer,outcome,seconds,notes='',chains=()):
        if not reviewer.strip() or outcome not in ('corrected','verified_unchanged','deferred','important_attribution'):
            raise QualificationError('Nom et résultat de vérification explicite requis.')
        if outcome=='important_attribution' and (not notes.strip() or not chains):
            raise QualificationError('Décrivez l’erreur importante et indiquez les chaînes concernées.')
        if not set(chains)<= {'small','large','whisperx'}:raise QualificationError('Chaîne inconnue.')
        import math
        if not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<0:raise QualificationError('Durée de correction invalide.')
        value={'id':uuid.uuid4().hex,'created':utc(),'audio_sha256':project['audio']['sha256'],'reference_sha256':digest(project),
            'task':copy.deepcopy(task),'reviewer':reviewer.strip(),'outcome':outcome,'operator_elapsed_seconds':seconds,
            'notes':notes,'chains':list(chains),'human_action_not_automatic_quality_judgment':True}
        with closing(sqlite3.connect(self.path)) as c,c:c.execute('INSERT INTO events VALUES(?,?,?)',(value['id'],value['created'],json.dumps(value,ensure_ascii=False,allow_nan=False)))
        return value


def read_task_log(project,path):
    from pathlib import Path
    path=Path(path)
    if not path.exists():return []
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as c:
        if c.execute('PRAGMA application_id').fetchone()[0]!=0x4E545443:raise QualificationError('Journal de corrections invalide.')
        return [v for (payload,) in c.execute('SELECT payload FROM events ORDER BY rowid')
                if (v:=json.loads(payload))['audio_sha256']==project['audio']['sha256']]


def operator_summary(events):
    latest={e['task']['id']:e for e in events if e['outcome']!='important_attribution'}
    protocol={k:e for k,e in latest.items() if e['task'].get('kind') not in ('reference','qualitative')}
    # Unique report IDs avoid double-counting repeated exports of the same event.
    important={e['id']:e for e in events if e['outcome']=='important_attribution'}
    return {'protocol_tasks_corrected':sum(e['outcome']=='corrected' for e in protocol.values()),
        'protocol_tasks_verified_unchanged':sum(e['outcome']=='verified_unchanged' for e in protocol.values()),
        'protocol_tasks_deferred':sum(e['outcome']=='deferred' for e in protocol.values()),
        'reference_tasks_checked':sum(e['task'].get('kind') in ('reference','qualitative') and e['outcome']!='deferred' for e in latest.values()),
        'important_attribution_reports':{k:sum(k in e['chains'] for e in important.values()) for k in ('small','large','whisperx')},
        'operator_elapsed_seconds':sum(e['operator_elapsed_seconds'] for e in {e['id']:e for e in events}.values()),
        'events':events,'scope':'Operator-reported counts, not exhaustive accuracy rates. No reports means not assessed, not zero proven errors.'}
