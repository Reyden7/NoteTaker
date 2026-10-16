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

    def save_analysis(self, sid, utterances, speakers, expected_revision):
        with self.db:
            # Lock the write transaction before checking optimistic concurrency.
            self.db.execute("UPDATE session SET revision=revision WHERE id=?", (sid,))
            state = self.get(sid)
            if state["revision"] != expected_revision:
                raise ValueError("SESSION_CHANGED_DURING_ANALYSIS")
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
            confirmed = confirm or speaker_id != current["speaker_id"]
            if confirmed:
                source["automatic_attribution"] = False
            uncertain = int(speaker_id is None) if confirmed else current["uncertain"]
            self.db.execute("UPDATE utterance SET text=?,speaker_id=?,uncertain=?,source_json=? WHERE session_id=? AND id=?", (text, speaker_id, uncertain, encoded(source), sid, uid))
            self._changed(sid)

    def split_utterance(self, sid, uid, at_ms, text_position):
        state = self.get(sid)
        current = next(u for u in state["utterances"] if u["id"] == uid)
        if not current["start_ms"] < at_ms < current["end_ms"] or not 0 < text_position < len(current["text"]):
            raise ValueError("SPLIT_REQUIRES_INTERIOR_TIME_AND_TEXT_POSITION")
        new_id = "s-" + uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'split',?)", (sid, encoded(current)))
            self.db.execute("UPDATE utterance SET end_ms=?,text=?,uncertain=1 WHERE session_id=? AND id=?", (at_ms, current["text"][:text_position].strip(), sid, uid))
            self.db.execute("INSERT INTO utterance VALUES(?,?,?,?,?,?,?,?)", (new_id, sid, current["speaker_id"], at_ms, current["end_ms"], current["text"][text_position:].strip(), 1, current["source_json"]))
            self._changed(sid)
        return new_id

    def merge_speakers(self, sid, source_id, target_id):
        state = self.get(sid)
        if source_id == target_id or source_id not in state["speakers"] or target_id not in state["speakers"]:
            raise ValueError("TWO_EXISTING_SPEAKERS_REQUIRED")
        with self.db:
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'merge_speakers',?)", (sid, encoded({"utterances": state["utterances"], "speakers": state["speakers"]})))
            self.db.execute("UPDATE utterance SET speaker_id=?,uncertain=1 WHERE session_id=? AND speaker_id=?", (target_id, sid, source_id))
            self.db.execute("DELETE FROM speaker WHERE session_id=? AND id=?", (sid, source_id))
            self._changed(sid)

    def rename_speaker(self, sid, speaker_id, label):
        if not label.strip():
            raise ValueError("SPEAKER_LABEL_REQUIRED")
        with self.db:
            self.db.execute("UPDATE speaker SET label=? WHERE session_id=? AND id=?", (label.strip(), sid, speaker_id))
            self._changed(sid)

    def save_manual(self, sid, votes, decisions):
        validate_votes(votes)
        with self.db:
            self.db.execute("INSERT INTO manual_record VALUES(?,?,?) ON CONFLICT(session_id) DO UPDATE SET votes_json=excluded.votes_json,decisions_json=excluded.decisions_json", (sid, encoded(votes), encoded(decisions)))
            self._changed(sid)

    def context_hash(self, sid):
        s = self.get(sid)
        return content_digest({k: s[k] for k in ("title", "metadata", "takes", "speakers", "utterances", "votes", "decisions")})

    def save_draft(self, sid, content, expected_context=None):
        state = self.get(sid)
        validate_minutes(content, {u["id"] for u in state["utterances"]}, {v["id"]: v for v in state["votes"]})
        context = self.context_hash(sid)
        if expected_context and context != expected_context:
            raise ValueError("SESSION_CHANGED_DURING_GENERATION")
        revision = (state["draft"]["revision"] + 1) if state["draft"] else 1
        did = str(uuid.uuid4())
        with self.db:
            self.db.execute("INSERT INTO draft_minutes(id,session_id,revision,content_json,context_sha256) VALUES(?,?,?,?,?)", (did, sid, revision, encoded(content), context))
        return did

    def approve(self, sid, reviewer):
        state = self.get(sid)
        draft = state["draft"]
        if not draft or draft["context_sha256"] != self.context_hash(sid):
            raise ValueError("DRAFT_STALE_REVIEW_SOURCES_AND_SAVE_AGAIN")
        review = {**asdict(record_human_review(draft["content"], reviewer)), "context_sha256": self.context_hash(sid)}
        with self.db:
            self.db.execute("UPDATE draft_minutes SET review_json=? WHERE id=?", (encoded(review), draft["id"]))
        return review

    def reviewed_content(self, sid):
        s = self.get(sid)
        d = s["draft"]
        if not d or not d["review"] or d["review"]["context_sha256"] != self.context_hash(sid):
            raise ValueError("HUMAN_REVIEW_REQUIRED_FOR_CURRENT_SESSION")
        return s, HumanReview(**{k: d["review"][k] for k in ("content_sha256", "reviewer", "reviewed_at")})

    def record_export(self, sid, draft_id, path, digest):
        with self.db:
            self.db.execute("INSERT INTO export(id,session_id,draft_id,format,path,sha256) VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), sid, draft_id, path.suffix[1:], str(path), digest))
