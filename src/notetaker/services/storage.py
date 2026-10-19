"""Persistent session workspace. Each thread opens its own SQLite connection."""
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from notetaker.domain.minutes import content_digest, record_human_review, HumanReview, validate_minutes
from notetaker.infrastructure.database import open_database, recover_jobs

def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)

def validate_votes(votes):
    ids = set()
    for vote in votes:
        if not vote.get("id") or vote["id"] in ids or not vote.get("title", "").strip():
            raise ValueError("INVALID_VOTE")
        ids.add(vote["id"])
        if vote.get("status") not in {"unknown", "entered"}:
            raise ValueError("INVALID_VOTE_STATUS")
        counts = [vote.get(k) for k in ("for_count", "against_count", "abstain_count", "nonparticipating_count")]
        if vote["status"] == "entered" and (not vote.get("source", "").strip() or any(type(n) is not int or n < 0 for n in counts)):
            raise ValueError("VOTE_COUNTS_AND_SOURCE_REQUIRED")
        if vote["status"] == "unknown" and any(n is not None for n in counts):
            raise ValueError("UNKNOWN_VOTE_CANNOT_HAVE_COUNTS")

class SessionStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = open_database(self.root / "notetaker.sqlite3")
        self.db.row_factory = __import__("sqlite3").Row

    def close(self):
        self.db.close()

    def recover(self):
        return recover_jobs(self.db)

    def create(self, title, metadata=None):
        if not title.strip():
            raise ValueError("SESSION_TITLE_REQUIRED")
        sid = str(uuid.uuid4())
        with self.db:
            self.db.execute("INSERT INTO session(id,title,metadata_json) VALUES(?,?,?)", (sid, title.strip(), encoded(metadata or {})))
            self.db.execute("INSERT INTO manual_record(session_id) VALUES(?)", (sid,))
        return sid

    def list_sessions(self, query=""):
        return [dict(r) for r in self.db.execute("SELECT id,title,created_at,archived,metadata_json FROM session WHERE title LIKE ? ORDER BY created_at DESC,rowid DESC", (f"%{query}%",))]

    def get(self, sid):
        row = self.db.execute("SELECT * FROM session WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise KeyError("SESSION_NOT_FOUND")
        value = dict(row)
        value["metadata"] = json.loads(value.pop("metadata_json"))
        value["takes"] = [dict(r) for r in self.db.execute("SELECT * FROM audio_take WHERE session_id=? ORDER BY rowid", (sid,))]
        value["speakers"] = {r["id"]: r["label"] for r in self.db.execute("SELECT * FROM speaker WHERE session_id=? ORDER BY id", (sid,))}
        value["utterances"] = [dict(r) for r in self.db.execute("SELECT * FROM utterance WHERE session_id=? ORDER BY start_ms,id", (sid,))]
        manual = self.db.execute("SELECT * FROM manual_record WHERE session_id=?", (sid,)).fetchone()
        value["votes"] = json.loads(manual["votes_json"]) if manual else []
        value["decisions"] = json.loads(manual["decisions_json"]) if manual else []
        draft = self.db.execute("SELECT * FROM draft_minutes WHERE session_id=? ORDER BY revision DESC LIMIT 1", (sid,)).fetchone()
        value["draft"] = None if draft is None else {**dict(draft), "content": json.loads(draft["content_json"]), "review": json.loads(draft["review_json"]) if draft["review_json"] else None}
        from .directory import DirectoryService
        value['participants'] = DirectoryService(self).participants(sid)
        return value

    def _changed(self, sid):
        self.db.execute("UPDATE session SET revision=revision+1 WHERE id=?", (sid,))
        self.db.execute("UPDATE draft_minutes SET review_json=NULL WHERE session_id=?", (sid,))

    def save_details(self, sid, title, metadata):
        if not title.strip():
            raise ValueError("SESSION_TITLE_REQUIRED")
        with self.db:
            self.db.execute("UPDATE session SET title=?,metadata_json=? WHERE id=?", (title.strip(), encoded(metadata), sid))
            self._changed(sid)

    def archive(self, sid, value=True):
        with self.db:
            self.db.execute("UPDATE session SET archived=? WHERE id=?", (int(value), sid))

    def add_take(self, sid, kind, path, status="ready", sha256=None):
        tid = str(uuid.uuid4())
        with self.db:
            self.db.execute("INSERT INTO audio_take(id,session_id,kind,path,status,sha256) VALUES(?,?,?,?,?,?)", (tid, sid, kind, str(path), status, sha256))
            self._changed(sid)
        return tid

    def finish_take(self, tid, status):
        with self.db:
            sid = self.db.execute("SELECT session_id FROM audio_take WHERE id=?", (tid,)).fetchone()[0]
            self.db.execute("UPDATE audio_take SET status=? WHERE id=?", (status, tid))
            self._changed(sid)

    def set_take_enabled(self, tid, enabled):
        with self.db:
            sid = self.db.execute("SELECT session_id FROM audio_take WHERE id=?", (tid,)).fetchone()[0]
            self.db.execute("UPDATE audio_take SET enabled=? WHERE id=?", (int(enabled), tid))
            self._changed(sid)

    def start_job(self, sid, kind):
        jid = str(uuid.uuid4())
        with self.db:
            self.db.execute("INSERT INTO job VALUES(?,?,?,'running',NULL)", (jid, sid, kind))
        return jid

    def finish_job(self, jid, ok, error_code=None):
        with self.db:
            self.db.execute("UPDATE job SET status=?,error_code=? WHERE id=?", ("completed" if ok else ("cancelled" if error_code == "CANCELLED" else "failed"), error_code, jid))

    def jobs(self, sid):
        return [dict(r) for r in self.db.execute("SELECT * FROM job WHERE session_id=? ORDER BY rowid DESC", (sid,))]

    def save_analysis(self, sid, utterances, speakers, expected_revision, *, preserve_manual=True):
        with self.db:
            # Lock the write transaction before checking optimistic concurrency.
            self.db.execute("UPDATE session SET revision=revision WHERE id=?", (sid,))
            state = self.get(sid)
            if state["revision"] != expected_revision:
                raise ValueError("SESSION_CHANGED_DURING_ANALYSIS")
            if preserve_manual and state['utterances']:
                from .transcript import preserve_corrections
                utterances,speakers=preserve_corrections(state,utterances,speakers)
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?, 'analysis', ?)", (sid, encoded({"utterances": state["utterances"], "speakers": state["speakers"]})))
            self.db.execute("DELETE FROM utterance WHERE session_id=?", (sid,))
            self.db.execute("DELETE FROM speaker WHERE session_id=?", (sid,))
            for key, label in speakers.items():
                self.db.execute("INSERT INTO speaker VALUES(?,?,?)", (key, sid, label))
            for u in utterances:
                self.db.execute("INSERT INTO utterance VALUES(?,?,?,?,?,?,?,?)", (u["id"], sid, u.get("speaker_id"), u["start_ms"], u["end_ms"], u["text"], int(u["uncertain"]), encoded(u.get("source", {}))))
            self._changed(sid)

    def edit_utterance(self, sid, uid, text, speaker_id, confirm=False):
        with self.db:
            if speaker_id and not self.db.execute("SELECT 1 FROM speaker WHERE session_id=? AND id=?", (sid, speaker_id)).fetchone():
                raise ValueError("UNKNOWN_SPEAKER")
            current = self.db.execute("SELECT * FROM utterance WHERE session_id=? AND id=?", (sid, uid)).fetchone()
            if not current:
                raise ValueError("UTTERANCE_NOT_FOUND")
            source = json.loads(current["source_json"])
            if text != current['text']:
                source['manual_text'] = True
            confirmed = confirm or speaker_id != current["speaker_id"]
            if confirmed:
                source["automatic_attribution"] = False
            if speaker_id != current['speaker_id']:
                source.pop('directory_person_id', None)
                source.pop('directory_snapshot', None)
            uncertain = int(speaker_id is None) if confirmed else current["uncertain"]
            self.db.execute("UPDATE utterance SET text=?,speaker_id=?,uncertain=?,source_json=? WHERE session_id=? AND id=?", (text, speaker_id, uncertain, encoded(source), sid, uid))
            self._changed(sid)

    def analysis_history(self, sid):
        return [dict(r) for r in self.db.execute("SELECT id,kind,created_at,content_json FROM edit_history WHERE session_id=? AND kind IN ('analysis','restore_analysis','directory_assignment','split','merge_segments','merge_speakers') ORDER BY id DESC", (sid,))]

    def restore_analysis(self, sid, history_id):
        row = self.db.execute("SELECT content_json FROM edit_history WHERE id=? AND session_id=? AND kind IN ('analysis','restore_analysis','directory_assignment','split','merge_segments','merge_speakers')", (history_id, sid)).fetchone()
        if not row:
            raise ValueError("ANALYSIS_REVISION_NOT_FOUND")
        content = json.loads(row[0])
        if 'utterances' not in content:
            raise ValueError('Cette ancienne scission ne contient pas un instantané complet. Consultez la version précédente.')
        utterances = [{**u, "source": json.loads(u["source_json"]) if "source_json" in u else u.get("source", {})} for u in content["utterances"]]
        self.save_analysis(sid, utterances, content["speakers"], self.get(sid)["revision"], preserve_manual=False)

    def speaker_diagnostics(self, sid):
        state = self.get(sid)
        stats = {key: {"name": label, "seconds": 0, "segments": 0, "short_segments": 0, "uncertain_segments": 0} for key, label in state["speakers"].items()}
        for u in state["utterances"]:
            key = u["speaker_id"] or "unattributed"
            item = stats.setdefault(key, {"name": "Non attribué", "seconds": 0, "segments": 0, "short_segments": 0, "uncertain_segments": 0})
            seconds = (u["end_ms"] - u["start_ms"]) / 1000
            item["seconds"] += seconds
            item["segments"] += 1
            item["short_segments"] += seconds < 1
            item["uncertain_segments"] += bool(u["uncertain"])
        return stats

    def split_utterance(self, sid, uid, at_ms, text_position):
        state = self.get(sid)
        current = next(u for u in state["utterances"] if u["id"] == uid)
        if not current["start_ms"] < at_ms < current["end_ms"] or not 0 < text_position < len(current["text"]):
            raise ValueError("SPLIT_REQUIRES_INTERIOR_TIME_AND_TEXT_POSITION")
        left,right=current['text'][:text_position].strip(),current['text'][text_position:].strip()
        if not left or not right:
            raise ValueError('La scission doit conserver du texte dans chacun des deux passages.')
        new_id = "s-" + uuid.uuid4().hex
        source=json.loads(current['source_json'])
        source.update({'manual_text':True,'split_from':uid})
        right_source=dict(source)
        source['split_join_next']={'id':new_id,'left':left,'right':right,
            'separator':' ' if current['text'][text_position-1].isspace() or current['text'][text_position].isspace() else ''}
        with self.db:
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'split',?)", (sid, encoded({'utterances':state['utterances'],'speakers':state['speakers']})))
            self.db.execute("UPDATE utterance SET end_ms=?,text=?,uncertain=1,source_json=? WHERE session_id=? AND id=?", (at_ms, left, encoded(source), sid, uid))
            self.db.execute("INSERT INTO utterance VALUES(?,?,?,?,?,?,?,?)", (new_id, sid, current["speaker_id"], at_ms, current["end_ms"], right, 1, encoded(right_source)))
            self._remap_draft_sources(sid,{uid:{'ids':[uid,new_id],'original_text':current['text'],
                'split':[(uid,0,text_position),(new_id,text_position,len(current['text']))]}})
            self._changed(sid)
        return new_id

    def _remap_draft_sources(self, sid, mapping):
        from .evidence import remap_sources
        draft=self.get(sid)['draft']
        if draft:
            content=remap_sources(draft['content'],mapping)
            if content != draft['content']:
                self.save_draft(sid,content,allow_invalid=True)

    def merge_utterances(self, sid, ids):
        with self.db:
            state=self.get(sid)
            selected=[(i,u) for i,u in enumerate(state['utterances']) if u['id'] in set(ids)]
            if len(selected)<2 or len(selected)!=len(set(ids)) or [i for i,_ in selected] != list(range(selected[0][0],selected[-1][0]+1)):
                raise ValueError('Sélectionnez au moins deux interventions consécutives à regrouper.')
            rows=[u for _,u in selected]
            if len({u['speaker_id'] for u in rows})!=1 or rows[0]['speaker_id'] is None:
                raise ValueError('Attribuez d’abord la même voix aux passages ; des voix inconnues ne peuvent pas être regroupées par supposition.')
            if any(a['end_ms']>b['start_ms'] for a,b in zip(rows,rows[1:])):
                raise ValueError('Ces passages se chevauchent. Corrigez-les séparément.')
            audio={json.loads(u['source_json']).get('normalized_audio') for u in rows}
            if len(audio)>1:
                raise ValueError('Ces passages utilisent des références audio différentes.')
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'merge_segments',?)",(sid,encoded({'utterances':state['utterances'],'speakers':state['speakers']})))
            first=rows[0]
            source=json.loads(first['source_json'])
            source.update({'automatic_attribution':False,'manual_text':True,'merged_segments':[
                {'id':u['id'],'start_ms':u['start_ms'],'end_ms':u['end_ms'],'text':u['text']} for u in rows]})
            text=first['text'].strip()
            for previous,current in zip(rows,rows[1:]):
                join=json.loads(previous['source_json']).get('split_join_next',{})
                separator=join.get('separator',' ') if join.get('id')==current['id'] and join.get('left')==previous['text'] and join.get('right')==current['text'] else ' '
                text+=separator+current['text'].strip()
            source.pop('split_join_next',None)
            self.db.execute('UPDATE utterance SET text=?,end_ms=?,uncertain=?,source_json=? WHERE session_id=? AND id=?',
                (text,rows[-1]['end_ms'],int(any(u['uncertain'] for u in rows)),encoded(source),sid,first['id']))
            for u in rows[1:]:
                self.db.execute('DELETE FROM utterance WHERE session_id=? AND id=?',(sid,u['id']))
            self._remap_draft_sources(sid,{u['id']:{'ids':[first['id']]} for u in rows[1:]})
            self._changed(sid)
        return first['id']

    def merge_speakers(self, sid, source_id, target_id):
        state = self.get(sid)
        if source_id == target_id or source_id not in state["speakers"] or target_id not in state["speakers"]:
            raise ValueError("TWO_EXISTING_SPEAKERS_REQUIRED")
        with self.db:
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'merge_speakers',?)", (sid, encoded({"utterances": state["utterances"], "speakers": state["speakers"]})))
            self.db.execute("UPDATE utterance SET speaker_id=?,uncertain=1 WHERE session_id=? AND speaker_id=?", (target_id, sid, source_id))
            for u in state['utterances']:
                if u['speaker_id'] == source_id:
                    source = json.loads(u['source_json'])
                    source.pop('directory_person_id', None)
                    source.pop('directory_snapshot', None)
                    source['automatic_attribution'] = False
                    self.db.execute('UPDATE utterance SET source_json=? WHERE session_id=? AND id=?', (encoded(source), sid, u['id']))
            self.db.execute("DELETE FROM speaker WHERE session_id=? AND id=?", (sid, source_id))
            self._changed(sid)

    def rename_speaker(self, sid, speaker_id, label):
        if not label.strip():
            raise ValueError("SPEAKER_LABEL_REQUIRED")
        with self.db:
            state = self.get(sid)
            if speaker_id not in state['speakers']:
                raise ValueError('UNKNOWN_SPEAKER')
            if state['speakers'][speaker_id] == label.strip():
                return
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'directory_assignment',?)",
                            (sid, encoded({'utterances': state['utterances'], 'speakers': state['speakers']})))
            for row in self.db.execute('SELECT id,source_json FROM utterance WHERE session_id=? AND speaker_id=?', (sid, speaker_id)).fetchall():
                source = json.loads(row['source_json'])
                if 'directory_person_id' in source:
                    source.pop('directory_person_id', None)
                    source.pop('directory_snapshot', None)
                    self.db.execute('UPDATE utterance SET source_json=? WHERE session_id=? AND id=?', (encoded(source), sid, row['id']))
                source['automatic_attribution']=False
                self.db.execute('UPDATE utterance SET source_json=? WHERE session_id=? AND id=?',(encoded(source),sid,row['id']))
            self.db.execute("UPDATE speaker SET label=? WHERE session_id=? AND id=?", (label.strip(), sid, speaker_id))
            self._changed(sid)

    def save_manual(self, sid, votes, decisions):
        validate_votes(votes)
        with self.db:
            self.db.execute("INSERT INTO manual_record VALUES(?,?,?) ON CONFLICT(session_id) DO UPDATE SET votes_json=excluded.votes_json,decisions_json=excluded.decisions_json", (sid, encoded(votes), encoded(decisions)))
            self._changed(sid)

    def context_hash(self, sid):
        s = self.get(sid)
        context = {k: s[k] for k in ("title", "metadata", "takes", "speakers", "utterances", "votes", "decisions")}
        # Preserve the exact context of legacy reviewed sessions without structured participants.
        if s['participants']:
            context['participants'] = s['participants']
        registry=self.db.execute('SELECT id FROM information_registry WHERE session_id=? ORDER BY revision DESC LIMIT 1',(sid,)).fetchone()
        if registry:
            context['information_registry_revision']=registry['id']
        return content_digest(context)

    def draft_history(self, sid):
        return [dict(r) for r in self.db.execute("SELECT id,revision,created_at,content_json FROM draft_minutes WHERE session_id=? ORDER BY revision DESC", (sid,))]

    def restore_draft(self, sid, draft_id):
        row = self.db.execute("SELECT content_json FROM draft_minutes WHERE id=? AND session_id=?", (draft_id, sid)).fetchone()
        if not row:
            raise ValueError("DRAFT_REVISION_NOT_FOUND")
        return self.save_draft(sid, json.loads(row[0]),allow_invalid=True)

    def save_draft(self, sid, content, expected_context=None, *, allow_invalid=False):
        state = self.get(sid)
        from .evidence import require_valid_evidence
        if not allow_invalid:
            self._check_registry_reference(sid,content)
            require_valid_evidence(content,state)
            validate_minutes(content, {u["id"] for u in state["utterances"]}, {v["id"]: v for v in state["votes"]})
        else:
            # An unfinished revision can be saved/reopened; it is never approved.
            from jsonschema import Draft202012Validator
            from notetaker.domain.minutes import SCHEMA
            import copy
            schema=copy.deepcopy(SCHEMA)
            schema['properties']['points']['items']['properties']['sources']['minItems']=0
            Draft202012Validator(schema).validate(content)
        context = self.context_hash(sid)
        if expected_context and context != expected_context:
            raise ValueError("SESSION_CHANGED_DURING_GENERATION")
        revision = (state["draft"]["revision"] + 1) if state["draft"] else 1
        did = str(uuid.uuid4())
        # A source remap belongs to its caller's split/merge transaction.
        # Entering a nested sqlite context would commit that transaction early.
        from contextlib import nullcontext
        with nullcontext() if self.db.in_transaction else self.db:
            self.db.execute("INSERT INTO draft_minutes(id,session_id,revision,content_json,context_sha256) VALUES(?,?,?,?,?)", (did, sid, revision, encoded(content), context))
        return did

    def _check_registry_reference(self,sid,content):
        if content.get('experimental_summary'):
            from .direct_summary import validate_provenance
            validate_provenance(self,sid,content)
        reference=content.get('information_registry')
        if not reference:return
        row=self.db.execute('SELECT content_json FROM information_registry WHERE id=? AND session_id=?',
            (reference['revision_id'],sid)).fetchone()
        if not row:raise ValueError('REGISTRY_DOCUMENT_REFERENCE_INVALID')
        document=json.loads(row[0])
        latest=self.db.execute('SELECT id FROM information_registry WHERE session_id=? ORDER BY revision DESC LIMIT 1',(sid,)).fetchone()
        if not latest or latest['id']!=reference['revision_id']:raise ValueError('REGISTRY_DOCUMENT_REFERENCE_INVALID')
        from notetaker.domain.information_registry import source_fingerprint
        if document['source_sha256']!=source_fingerprint(self.get(sid)):raise ValueError('REGISTRY_STALE')
        if content_digest(document)!=reference['content_sha256']:raise ValueError('REGISTRY_DOCUMENT_REFERENCE_INVALID')
        known={e['id'] for e in document['entries'] if e['category']=='information'}
        if not set(reference['information_ids'])<=known:raise ValueError('REGISTRY_DOCUMENT_REFERENCE_INVALID')
        for point in content.get('points',[]):
            if not {c['id'] for c in point.get('claims',[])}<=set(reference['information_ids']):
                raise ValueError('REGISTRY_DOCUMENT_REFERENCE_INVALID')

    def approve(self, sid, reviewer, role=None):
        state = self.get(sid)
        draft = state["draft"]
        if not draft or draft["context_sha256"] != self.context_hash(sid):
            raise ValueError("DRAFT_STALE_REVIEW_SOURCES_AND_SAVE_AGAIN")
        from .evidence import require_valid_evidence
        self._check_registry_reference(sid,draft['content'])
        require_valid_evidence(draft['content'],state)
        validate_minutes(draft['content'],{u['id'] for u in state['utterances']},{v['id']:v for v in state['votes']})
        if draft["content"].get("document_mode") == "municipal" and role != "secretary":
            raise ValueError("MUNICIPAL_SECRETARY_REVIEW_REQUIRED")
        review = {**asdict(record_human_review(draft["content"], reviewer)), "context_sha256": self.context_hash(sid), "reviewer_role": role or "reviewer"}
        with self.db:
            self.db.execute("UPDATE draft_minutes SET review_json=? WHERE id=?", (encoded(review), draft["id"]))
        return review

    def reviewed_content(self, sid):
        s = self.get(sid)
        d = s["draft"]
        if not d or not d["review"] or d["review"]["context_sha256"] != self.context_hash(sid):
            raise ValueError("HUMAN_REVIEW_REQUIRED_FOR_CURRENT_SESSION")
        from .evidence import require_valid_evidence
        self._check_registry_reference(sid,d['content'])
        require_valid_evidence(d['content'],s)
        validate_minutes(d['content'],{u['id'] for u in s['utterances']},{v['id']:v for v in s['votes']})
        if d["content"].get("document_mode") == "municipal" and d["review"].get("reviewer_role") != "secretary":
            raise ValueError("MUNICIPAL_SECRETARY_REVIEW_REQUIRED")
        return s, HumanReview(**{k: d["review"][k] for k in ("content_sha256", "reviewer", "reviewed_at")})

    def record_export(self, sid, draft_id, path, digest):
        with self.db:
            self.db.execute("INSERT INTO export(id,session_id,draft_id,format,path,sha256) VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), sid, draft_id, path.suffix[1:], str(path), digest))
