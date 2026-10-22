"""Append-only registry revisions and explicit human changes with optimistic locks."""
import copy
import json
import uuid
from notetaker.domain.information_registry import (seed_registry,source_fingerprint,validate_registry,
    evidence_issues,author_state,TYPES,RELATIONS,ambiguous_origin)
from notetaker.services.storage import encoded


class RegistryService:
    def __init__(self,store):self.store=store

    def latest(self,sid):
        row=self.store.db.execute('SELECT * FROM information_registry WHERE session_id=? ORDER BY revision DESC LIMIT 1',(sid,)).fetchone()
        if not row:return None
        result=dict(row);result['content']=json.loads(result.pop('content_json'))
        result['stale']=result['source_sha256']!=source_fingerprint(self.store.get(sid))
        return result

    def history(self,sid):
        return [dict(r) for r in self.store.db.execute('SELECT id,revision,actor,reason,created_at FROM information_registry WHERE session_id=? ORDER BY revision DESC',(sid,))]

    def version(self,sid,revision_id):
        row=self.store.db.execute('SELECT content_json FROM information_registry WHERE session_id=? AND id=?',(sid,revision_id)).fetchone()
        if not row:raise ValueError('REGISTRY_DOCUMENT_REFERENCE_INVALID')
        return json.loads(row[0])

    def save(self,sid,document,*,expected_id,actor,reason,_manual_change=False):
        if not actor.strip() or not reason.strip():raise ValueError('REGISTRY_ACTOR_REASON_REQUIRED')
        if document['session_id']!=sid:raise ValueError('REGISTRY_WRONG_SESSION')
        validate_registry(document)
        db=self.store.db
        from contextlib import nullcontext
        with nullcontext() if db.in_transaction else db:
            db.execute('UPDATE session SET revision=revision WHERE id=?',(sid,))
            current=db.execute('SELECT id,revision,content_json FROM information_registry WHERE session_id=? ORDER BY revision DESC LIMIT 1',(sid,)).fetchone()
            if (current['id'] if current else None)!=expected_id:raise ValueError('REGISTRY_CONCURRENT_CHANGE')
            if current and not _manual_change:
                previous=json.loads(current['content_json']);incoming={e['id']:e for e in document['entries']}
                for old in previous['entries']:
                    if old['category']!='information' or not old.get('human_lock'):continue
                    new=incoming.get(old['id'])
                    fields=['content','subject','type','discourse','evidence','speaker','author_status']
                    if previous['source_sha256']==document['source_sha256']:fields+=['human_status','verification']
                    if new is None or any(new.get(k)!=old.get(k) for k in fields):raise ValueError('REGISTRY_HUMAN_CHANGE_PROTECTED')
            if source_fingerprint(self.store.get(sid))!=document['source_sha256']:raise ValueError('REGISTRY_STALE')
            rid=str(uuid.uuid4());revision=current['revision']+1 if current else 1
            db.execute('INSERT INTO information_registry(id,session_id,revision,source_sha256,content_json,actor,reason) VALUES(?,?,?,?,?,?,?)',
                (rid,sid,revision,document['source_sha256'],encoded(document),actor.strip(),reason.strip()))
        return rid

    def initialize(self,sid):
        current=self.latest(sid)
        if current and not current['stale']:return current
        state=self.store.get(sid)
        if not state['utterances']:raise ValueError('TRANSCRIPT_REQUIRED')
        document=seed_registry(sid,state)
        if current:
            for old in current['content']['entries']:
                if old['category']!='information':continue
                entry=copy.deepcopy(old)
                entry.update(verification='insufficient',human_status='excluded' if old['human_status']=='excluded' else 'pending',
                    reasons=list(dict.fromkeys(old['reasons']+['source_snapshot_changed_requires_review'])))
                document['entries'].append(entry)
            document['processing']['previous_registry_id']=current['id']
            document['relations']=[{**copy.deepcopy(r),'verification':'pending','human_status':'pending',
                'reason':'Sources modifiées ; relation à revérifier'} for r in current['content']['relations']]
        self.save(sid,document,expected_id=current['id'] if current else None,
            actor='NoteTaker — inventaire local',reason='Inventaire intégral ; aucune information approuvée automatiquement')
        return self.latest(sid)

    def change(self,sid,expected_id,entry_id,action,*,actor,reason,updates=None):
        current=self.latest(sid)
        if not current or current['stale']:raise ValueError('REGISTRY_STALE')
        if current['id']!=expected_id:raise ValueError('REGISTRY_CONCURRENT_CHANGE')
        document=copy.deepcopy(current['content']);state=self.store.get(sid)
        entry=next(e for e in document['entries'] if e['id']==entry_id)
        before=copy.deepcopy({k:v for k,v in entry.items() if k!='history'})
        if action=='edit':
            updates=updates or {}
            if not set(updates)<={'content','subject','type','discourse','evidence'}:raise ValueError('REGISTRY_EDIT_INVALID')
            if entry['category']=='source':
                # A source inventory row is immutable. Derive a new information instead.
                entry=copy.deepcopy(entry);entry['id']=str(uuid.uuid4());entry['category']='information';entry['history']=[]
                entry['derived_from_source_id']=entry_id
                for field in ('unrepresented_text','candidate_ids','unlinked_candidate_ids','inspection'):
                    entry.pop(field,None)
                document['entries'].append(entry)
            entry.update(copy.deepcopy(updates))
            by_id={u['id']:u for u in state['utterances']}
            for e in entry['evidence']:
                if e['id'] not in by_id:raise ValueError('REGISTRY_INVALID_SOURCE')
                e.update(start_ms=by_id[e['id']]['start_ms'],end_ms=by_id[e['id']]['end_ms'])
            voices={by_id[e['id']].get('speaker_id') or 'unattributed' for e in entry['evidence']}
            entry['speaker']=next(iter(voices)) if len(voices)==1 else 'unattributed'
            entry['author_status']=author_state(entry['evidence'],state)
            entry.update(human_status='pending',verification='pending',checks={},reasons=['human_edit_requires_approval'])
        elif action=='approve':
            if entry['category']!='information':raise ValueError('REGISTRY_SOURCE_REQUIRES_INFORMATION')
            if evidence_issues(entry,state) or ambiguous_origin(entry,state):raise ValueError('REGISTRY_INVALID_SOURCE')
            if not entry['content'].strip():raise ValueError('REGISTRY_EDIT_INVALID')
            from .registry_workflow import approval_blockers
            blockers=approval_blockers(entry,state)
            if blockers:raise ValueError('REGISTRY_APPROVAL_BLOCKED:'+','.join(blockers))
            entry['human_status']='approved'
        elif action=='exclude':entry['human_status']='excluded'
        elif action=='reopen':
            entry.update(human_status='pending',verification='pending',checks={},
                reasons=list(dict.fromkeys(entry['reasons']+['operator_requested_verification'])))
        else:raise ValueError('REGISTRY_EDIT_INVALID')
        if entry['type'] not in TYPES:raise ValueError('REGISTRY_EDIT_INVALID')
        entry['human_lock']=True
        entry.pop('previous_extraction',None)
        entry['history'].append({'action':action,'actor':actor,'reason':reason,'before':before})
        document['writing']={'status':'outdated_by_registry_edit','previous_revision_id':current['id'],
            'used_information_ids':[],'not_written_information_ids':[e['id'] for e in document['entries'] if e['category']=='information' and e['human_status']!='excluded']}
        # Changed endpoint content invalidates only relation opinions, never rewrites their proof.
        if action in {'edit','exclude','reopen'}:
            for relation in document['relations']:
                if entry_id in (relation['from'],relation['to']):
                    relation.update(verification='pending',human_status='pending',reason='endpoint_changed')
        self.save(sid,document,expected_id=expected_id,actor=actor,reason=reason,_manual_change=True)
        return entry['id']

    def relation(self,sid,expected_id,*,actor,reason,source_id=None,target_id=None,kind=None,relation_id=None,exclude=False):
        from notetaker.domain.information_registry import stable_id
        current=self.latest(sid)
        if not current or current['stale']:raise ValueError('REGISTRY_STALE')
        if current['id']!=expected_id:raise ValueError('REGISTRY_CONCURRENT_CHANGE')
        document=copy.deepcopy(current['content']);state=self.store.get(sid)
        if relation_id:
            row=next(r for r in document['relations'] if r['id']==relation_id)
        else:
            entries={e['id']:e for e in document['entries'] if e['category']=='information'}
            if source_id not in entries or target_id not in entries or source_id==target_id or kind not in RELATIONS:
                raise ValueError('REGISTRY_RELATION_INVALID')
            endpoints=[entries[source_id],entries[target_id]]
            if any(evidence_issues(e,state) for e in endpoints):raise ValueError('REGISTRY_INVALID_SOURCE')
            row={'id':stable_id(sid,'relation',[source_id,target_id,kind]),'from':source_id,'to':target_id,'kind':kind,
                'verification':'pending','human_status':'pending','reason':reason,'checks':{},
                'evidence':list({(r['id'],r['quote']):r for e in endpoints for r in e['evidence']}.values())}
            existing=next((r for r in document['relations'] if r['id']==row['id']),None)
            if existing:row=existing
            else:document['relations'].append(row)
        row['human_status']='excluded' if exclude else 'approved'
        row.setdefault('history',[]).append({'actor':actor,'reason':reason,'action':row['human_status']})
        document['writing']={'status':'outdated_by_registry_edit','previous_revision_id':current['id'],
            'used_information_ids':[],'not_written_information_ids':[e['id'] for e in document['entries'] if e['category']=='information' and e['human_status']!='excluded']}
        self.save(sid,document,expected_id=expected_id,actor=actor,reason=reason)
