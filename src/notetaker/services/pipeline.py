"""Persistent real ASR, diarization and Qwen jobs. Originals are never modified."""
import json
import re
import threading
import uuid
from pathlib import Path
from notetaker.engines.router import run_with_fallback
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.infrastructure.paths import ModelPaths, session_directory
from notetaker.infrastructure.process import run_worker, JobCancelled
from .audio import prepare_audio
from .storage import SessionStore

def align_transcript(segments, diarization):
    turns = diarization.get("turns", [])
    speakers = {key: f"Intervenant {i + 1}" for i, key in enumerate(sorted({t["speaker"] for t in turns}))}
    result = []
    for index, s in enumerate(segments):
        duration = max(s["end"] - s["start"], 0.001)
        coverage = {}
        for t in turns:
            amount = max(0, min(s["end"], t["end"]) - max(s["start"], t["start"]))
            coverage[t["speaker"]] = coverage.get(t["speaker"], 0) + amount
        ordered = sorted(coverage, key=coverage.get, reverse=True)
        primary = ordered[0] if ordered and coverage[ordered[0]] > 0 else None
        overlap = any(o["start"] < s["end"] and o["end"] > s["start"] for o in diarization.get("possible_overlaps", []))
        uncertain = not primary or coverage[primary] / duration < 0.65 or (len(ordered) > 1 and coverage[ordered[1]] / duration > 0.15) or overlap
        result.append({"id": s.get("id", f"s{index}"), "start_ms": round(s["start"] * 1000), "end_ms": round(s["end"] * 1000),
                       "text": s["text"].strip(), "speaker_id": primary, "uncertain": uncertain,
                       "source": {"avg_logprob": s.get("avg_logprob"), "no_speech_prob": s.get("no_speech_prob"),
                                  "possible_overlap": overlap, "candidates": ordered, "automatic_attribution": True}})
    return result, speakers

VOTE_TEXT = re.compile(r"\b(vot\w*|contre|abstention\w*|unanimit\w*|adopt\w*|approuv\w*|quorum|voix)\b", re.IGNORECASE)

def assemble_draft(state, selection):
    agenda = state["metadata"].get("agenda", []) or ["Discussion générale"]
    groups = {i: [] for i in range(len(agenda))}
    unassigned, used = [], set()
    for u in state["utterances"]:
        placed = False
        for key, ids in selection["selections"].items():
            if u["id"] in ids:
                groups[int(key)].append(u)
                placed = True
        if not placed:
            unassigned.append(u)
    points, to_verify = [], ["Brouillon composé d’extraits de transcription à relire ; aucun vote n’est déduit par le modèle."]
    if unassigned:
        groups[len(agenda)] = unassigned
        agenda = [*agenda, "Échanges restant à classer"]
    for i, records in groups.items():
        text, refs = [], []
        def finish():
            if refs:
                points.append({"title": agenda[i], "summary": "\n\n".join(text), "sources": list(dict.fromkeys(refs)), "vote_id": None})
        for u in records:
            if VOTE_TEXT.search(u["text"]):
                to_verify.append(f"Passage relatif à un vote à contrôler dans la transcription : {u['id']}. Saisir le résultat dans Votes.")
                continue
            speaker = state["speakers"].get(u["speaker_id"], "Intervenant à attribuer")
            quote = f"{speaker} — {u['text']}"
            # The model cannot supply a name or narrative fact: text is copied from stored sources.
            if len("\n\n".join([*text, quote])) > 9000 and refs:
                finish()
                text, refs = [], []
            # A source longer than the schema limit is represented by referenced excerpts.
            for start in range(0, len(quote), 8000):
                part = quote[start:start + 8000]
                if text and len("\n\n".join([*text, part])) > 9000:
                    finish()
                    text, refs = [], []
                text.append(part)
                refs.append(u["id"])
        finish()
    if not points and state["utterances"]:
        first = state["utterances"][0]
        points = [{"title": "Éléments à compléter", "summary": "Compléter le projet après vérification de la transcription et des votes saisis.", "sources": [first["id"]], "vote_id": None}]
    return {"points": points, "to_verify": list(dict.fromkeys(to_verify))}

class Pipeline:
    def __init__(self, data_root, models=None, progress=lambda message: None, cancel=None):
        self.root = Path(data_root)
        self.models = models or ModelPaths()
        self.progress = progress
        self.cancel = cancel or threading.Event()

    def _run(self, workspace, request, timeout=7200):
        if self.cancel.is_set():
            raise JobCancelled("JOB_CANCELLED")
        path = workspace / (request["engine"] + "-" + request.get("device", "cpu") + ".request.json")
        atomic_json(path, request)
        response = run_worker(path, timeout=timeout, cancel=self.cancel)
        atomic_json(path.with_suffix(".result.json"), response)
        return response["result"]

    def analyse(self, sid, mode="cpu"):
        store = SessionStore(self.root)
        jid = store.start_job(sid, "analysis")
        workspace = session_directory(self.root, sid) / "jobs" / jid
        workspace.mkdir(parents=True)
        try:
            state = store.get(sid)
            takes = [t for t in state["takes"] if t.get("enabled", 1)]
            if not takes or any(t["status"] == "recording" for t in takes):
                raise ValueError("STOP_RECORDING_OR_IMPORT_AUDIO_FIRST")
            self.progress("Vérification des modèles locaux")
            self.models.verify()
            audio = prepare_audio(takes, workspace / "normalized.wav", self.progress)
            self.progress("Transcription française en cours")
            asr = run_with_fallback(lambda device: self._run(workspace, {"engine": "asr", "device": device, "audio": str(audio), "model": str(self.models.asr)}), mode)
            self.progress("Différenciation des voix et repérage des chevauchements possibles")
            diar_error = None
            try:
                diar = self._run(workspace, {"engine": "diarization-sherpa", "device": "cpu", "audio": str(audio), "segmentation": str(self.models.segmentation), "embedding": str(self.models.embedding), "overlap": True})
            except JobCancelled:
                raise
            except Exception as error:
                diar, diar_error = {"turns": []}, type(error).__name__
            utterances, speakers = align_transcript(asr.value["segments"], diar)
            for u in utterances:
                u["source"]["normalized_audio"] = str(audio)
            store.save_analysis(sid, utterances, speakers, state["revision"])
            if diar_error:
                raise RuntimeError("DIARIZATION_FAILED_TRANSCRIPT_PRESERVED")
            store.finish_job(jid, True)
            return {"utterances": len(utterances), "speakers": len(speakers), "device": asr.device}
        except BaseException as error:
            store.finish_job(jid, False, "CANCELLED" if isinstance(error, JobCancelled) else type(error).__name__)
            raise
        finally:
            store.close()

    def generate(self, sid):
        store = SessionStore(self.root)
        jid = store.start_job(sid, "minutes")
        workspace = session_directory(self.root, sid) / "jobs" / jid
        workspace.mkdir(parents=True)
        try:
            state = store.get(sid)
            if not state["utterances"]:
                raise ValueError("TRANSCRIPT_REQUIRED")
            context = store.context_hash(sid)
            self.progress("Classement des extraits par Qwen3 sur CPU")
            self.models.verify()
            selection = self._run(workspace, {"engine": "llm", "device": "cpu", "binary": str(self.models.llama), "model": str(self.models.llm),
                                     "workspace": str(workspace), "agenda": state["metadata"].get("agenda", []),
                                     "utterances": [{"id": u["id"], "text": u["text"]} for u in state["utterances"]]})
            draft = assemble_draft(state, selection)
            store.save_draft(sid, draft, expected_context=context)
            store.finish_job(jid, True)
            return {"points": len(draft["points"])}
        except BaseException as error:
            store.finish_job(jid, False, "CANCELLED" if isinstance(error, JobCancelled) else type(error).__name__)
            raise
        finally:
            store.close()
