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

def lexical_words(words):
    """Whisper can split French elisions into separately timed token pieces."""
    result = []
    for word in words:
        piece = word['word']
        attach = (result and piece and not piece[0].isspace() and
                  (piece[0] in "'’" or result[-1]['word'].endswith(("'", '’')))
                  and word['start'] - result[-1]['end'] <= 0.2)
        if attach:
            result[-1] = {**result[-1], 'word': result[-1]['word'] + piece,
                          'end': max(result[-1]['end'], word['end'])}
        else:
            result.append(dict(word))
    return result

def align_transcript(segments, diarization):
    turns = diarization.get("turns", [])
    speakers = {key: f"Intervenant {i + 1}" for i, key in enumerate(sorted({t["speaker"] for t in turns if t["speaker"] is not None}))}
    expanded = []
    for segment in segments:
        words = lexical_words(segment.get("words") or [])
        if not words:
            expanded.append(segment)
            continue
        groups, identities = [], []
        for word in words:
            matching = [(max(0, min(word["end"], t["end"]) - max(word["start"], t["start"])), t) for t in turns if t["speaker"] is not None]
            score, turn = max(matching, key=lambda x: x[0], default=(0, None))
            identity = turn["speaker"] if turn and score > 0 else None
            identities.append(identity)
        inferred = set()
        for index, word in enumerate(words):
            if word['end'] > word['start']:
                continue
            previous = next((j for j in range(index - 1, -1, -1) if words[j]['end'] > words[j]['start']), None)
            following = next((j for j in range(index + 1, len(words)) if words[j]['end'] > words[j]['start']), None)
            if previous is not None and following is not None and identities[previous] is not None and identities[previous] == identities[following]:
                identities[index] = identities[previous]
                inferred.add(index)
        for index, word in enumerate(words):
            identity = identities[index]
            if groups and groups[-1]["identity"] == identity:
                groups[-1]["end"] = word["end"]
                groups[-1]["text"] += word["word"]
                groups[-1]['word_timing_inferred'] |= index in inferred
            else:
                groups.append({"start": word["start"], "end": word["end"], "text": word["word"], "identity": identity,
                               'word_timing_inferred': index in inferred})
        for j, group in enumerate(groups):
            expanded.append({**segment, **group, "id": f"{segment.get('id', 's')}-{j}"})
    result = []
    for index, s in enumerate(expanded):
        if not s["text"].strip():
            continue
        duration = max(s["end"] - s["start"], 0.001)
        coverage = {}
        for t in turns:
            if t["speaker"] is None:
                continue
            amount = max(0, min(s["end"], t["end"]) - max(s["start"], t["start"]))
            coverage[t["speaker"]] = coverage.get(t["speaker"], 0) + amount
        ordered = sorted(coverage, key=coverage.get, reverse=True)
        primary = ordered[0] if ordered and coverage[ordered[0]] > 0 else None
        overlap = any(o["start"] < s["end"] and o["end"] > s["start"] for o in diarization.get("possible_overlaps", []))
        low_confidence = any(t.get("uncertain", False) and t["speaker"] == primary and t["start"] < s["end"] and t["end"] > s["start"] for t in turns)
        uncertain = not primary or coverage[primary] / duration < 0.65 or (len(ordered) > 1 and coverage[ordered[1]] / duration > 0.15) or overlap or low_confidence or s.get('word_timing_inferred', False)
        result.append({"id": s.get("id", f"s{index}"), "start_ms": round(s["start"] * 1000), "end_ms": round(s["end"] * 1000),
                       "text": s["text"].strip(), "speaker_id": primary, "uncertain": uncertain,
                       "source": {"avg_logprob": s.get("avg_logprob"), "no_speech_prob": s.get("no_speech_prob"),
                                  "possible_overlap": overlap, "candidates": ordered, "automatic_attribution": True,
                                  'word_timing_inferred': s.get('word_timing_inferred', False),
                                  "alignment": "word_timestamps" if s.get("words") else "whole_segment_approximate"}})
    return result, speakers

from notetaker.engines.hierarchical_summary import scrutiny_signal

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
            if scrutiny_signal(u["text"]):
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


def assemble_summary(state, result, mode="summary"):
    claims = {c["id"]: c for c in result["claims"]}
    points, used, reported = [], set(), False
    labels = {"position": "Position", "argument": "Argument", "proposal": "Proposition", "context": "Contexte", "question": "Question soulevée",
              "reported_decision": "Décision rapportée à confirmer", "reported_action": "Action rapportée à confirmer"}
    for topic in result["topics"]:
        selected = [claims[c] for c in topic["claims"] if c in claims and c not in used]
        if not selected:
            continue
        used.update(c["id"] for c in selected)
        sources = {u['id']: u for u in state['utterances']}
        paragraphs = []
        for c in selected:
            uncertain = any(sources[e['id']].get('uncertain', True) for e in c['evidence'])
            speaker = state['speakers'].get(c['speaker'], 'Intervenant à attribuer')
            quoted = ' '.join(e['quote'] for e in c['evidence'])
            indirect = bool(re.search(r"\b(?:vous\s+(?:estimez|pensez|considérez|dites|affirmez)|selon\s+(?:vous|lui|elle)|(?:il|elle|ils|elles)\s+(?:estime\w*|pense\w*|affirme\w*|dit|disent))\b", quoted, re.I))
            notes = []
            if uncertain:
                notes.append('attribution à vérifier')
            if indirect:
                notes.append('opinion rapportée — auteur à confirmer')
                reported = True
            if notes:
                speaker += ' (' + ' ; '.join(notes) + ')'
            paragraphs.append(f"{labels[c['kind']]} — {speaker} : {c['text']}")
        points.append({"title": topic["title"], "summary": "\n\n".join(paragraphs),
                       "sources": list(dict.fromkeys(e["id"] for c in selected for e in c["evidence"])),
                       "vote_id": None, "claims": selected})
    warnings = ["Synthèse IA : vérifier la fidélité des reformulations, les attributions et les sources avant export."]
    if reported:
        warnings.append("Certaines paroles reformulent l’avis d’une autre personne. Confirmer l’auteur des positions rapportées ; la voix qui parle n’est pas nécessairement celle qui les défend.")
    if any(c["kind"] in {"reported_decision", "reported_action"} for c in claims.values()):
        warnings.append("Décisions/actions rapportées à confirmer explicitement ; aucune décision métier ni responsabilité n’a été créée automatiquement.")
    if any(scrutiny_signal(u["text"]) for u in state["utterances"]):
        warnings.append("Un acte de scrutin possible est cité dans la transcription. Vérifier sa réalité et saisir séparément les résultats confirmés.")
    return {"document_mode": mode, "points": points, "to_verify": warnings, "generation_diagnostics": result["diagnostics"]}


def integral_transcript(state):
    points = []
    for u in state["utterances"]:
        if not u["text"].strip():
            continue
        def stamp(ms):
            return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}"
        name = state["speakers"].get(u["speaker_id"], "Intervenant à attribuer")
        points.append({"title": f"{stamp(u['start_ms'])} — {name}", "summary": u["text"], "sources": [u["id"]], "vote_id": None})
    return {"document_mode": "transcript", "points": points, "to_verify": ["Transcription corrigée à relire ; les horodatages et attributions automatiques peuvent être incertains."]}

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
                diar = self._run(workspace, {"engine": "diarization-sherpa", "device": "cpu", "audio": str(audio), "segmentation": str(self.models.segmentation), "embedding": str(self.models.embedding),
                                           "refinement_embedding": str(getattr(self.models, 'refinement_embedding', self.models.embedding)), "overlap": True})
            except JobCancelled:
                raise
            except Exception as error:
                diar, diar_error = {"turns": []}, type(error).__name__
            utterances, speakers = align_transcript(asr.value["segments"], diar)
            for u in utterances:
                u["source"]["normalized_audio"] = str(audio)
            store.save_analysis(sid, utterances, speakers, state["revision"])
            atomic_json(workspace / "analysis-diagnostics.json", {**diar.get("diagnostics", {}), "utterances": len(utterances),
                         "uncertain_utterances": sum(bool(u["uncertain"]) for u in utterances)})
            if diar_error:
                raise RuntimeError("DIARIZATION_FAILED_TRANSCRIPT_PRESERVED")
            store.finish_job(jid, True)
            return {"utterances": len(utterances), "speakers": len(speakers), "device": asr.device}
        except BaseException as error:
            store.finish_job(jid, False, "CANCELLED" if isinstance(error, JobCancelled) else type(error).__name__)
            raise
        finally:
            store.close()

    def generate(self, sid, mode="summary"):
        store = SessionStore(self.root)
        jid = store.start_job(sid, "minutes")
        workspace = session_directory(self.root, sid) / "jobs" / jid
        workspace.mkdir(parents=True)
        try:
            state = store.get(sid)
            if not state["utterances"]:
                raise ValueError("TRANSCRIPT_REQUIRED")
            context = store.context_hash(sid)
            if mode == "transcript":
                store.save_draft(sid, integral_transcript(state), expected_context=context)
                store.finish_job(jid, True)
                return {"points": len(state["utterances"]), "mode": mode}
            if mode not in {"summary", "municipal"}:
                raise ValueError("INVALID_DOCUMENT_MODE")
            self.progress("Synthèse hiérarchique et vérification des sources par Qwen3 sur CPU")
            self.models.verify()
            selection = self._run(workspace, {"engine": "llm", "device": "cpu", "binary": str(self.models.llama), "model": str(self.models.llm),
                                     "workspace": str(workspace), "task": "summary",
                                     "utterances": [{k: u[k] for k in ("id", "text", "speaker_id", "start_ms", "end_ms", "uncertain")} for u in state["utterances"]]})
            draft = assemble_summary(state, selection, mode)
            store.save_draft(sid, draft, expected_context=context)
            store.finish_job(jid, True)
            return {"points": len(draft["points"])}
        except BaseException as error:
            store.finish_job(jid, False, "CANCELLED" if isinstance(error, JobCancelled) else type(error).__name__)
            raise
        finally:
            store.close()
