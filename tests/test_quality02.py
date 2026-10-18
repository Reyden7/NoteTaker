import json
import subprocess
from pathlib import Path
import numpy as np
import pytest
from notetaker.engines.speaker_refinement import cluster_vectors, assign_observations, clean_intervals
from notetaker.engines.hierarchical_summary import coherent_blocks, grounded_claim, scrutiny_signal, source_units, resolve_evidence
from notetaker.services.pipeline import align_transcript, integral_transcript
from notetaker.services.storage import SessionStore
from notetaker.services.export import export_draft
from notetaker.services.session_export import export_session
from notetaker.domain.minutes import record_human_review


def test_global_clustering_has_no_six_speaker_cap_and_is_scale_invariant():
    vectors = np.eye(9)
    duplicated = np.repeat(vectors, 3, axis=0)
    labels = cluster_vectors(duplicated, 0.4, "complete")
    assert len(set(labels)) == 9
    assert np.array_equal(labels, cluster_vectors(duplicated * np.arange(1, 28)[:, None], 0.4, "complete"))
    assert len(cluster_vectors([])) == 0
    with pytest.raises(ValueError, match="INVALID_SPEAKER"):
        cluster_vectors([[0, 0], [1, 0]])


def test_short_or_overlapping_observations_cannot_create_an_identity():
    observations = [{"start": i * 4, "end": i * 4 + 3, "clean_seconds": seconds, "vector_index": i} for i, seconds in enumerate([3, 3, 0.6])]
    result = assign_observations(observations, [[1, 0, 0], [0, 1, 0], [0, 0, 1]], 0.4, "complete")
    assert result["diagnostics"]["speakers"] == 2
    assert result["turns"][-1]["speaker"] is None and result["turns"][-1]["uncertain"]
    assert clean_intervals(0, 5, [{"start": 1, "end": 3}]) == [(0, 1), (3, 5)]


def test_word_timestamps_split_a_change_inside_a_whisper_segment():
    rows, _ = align_transcript([{"id": "s0", "start": 0, "end": 4, "text": "Bonjour. Non.", "words": [
        {"start": 0, "end": 1, "word": "Bonjour."}, {"start": 2.5, "end": 3, "word": " Non."}]}],
        {"turns": [{"start": 0, "end": 2, "speaker": "a"}, {"start": 2, "end": 4, "speaker": "b"}]})
    assert [r["speaker_id"] for r in rows] == ["a", "b"]
    assert " ".join(r["text"] for r in rows) == "Bonjour. Non."
    assert all(r["source"]["alignment"] == "word_timestamps" for r in rows)


@pytest.mark.parametrize("text", ["Je suis contre cette proposition.", "Les jeunes veulent faire entendre leur voix.", "Le droit de vote est important.", "La voix de Louise est claire."])
def test_political_opinions_do_not_create_vote_alerts(text):
    assert not scrutiny_signal(text)


@pytest.mark.parametrize("text", ["Je mets cette délibération au vote.", "Le résultat du scrutin est annoncé.", "Le vote donne douze voix pour."])
def test_explicit_scrutiny_is_only_a_signal(text):
    assert scrutiny_signal(text)


def test_blocks_keep_all_sources_and_bound_context_overlap():
    utterances = [{"id": str(i), "text": str(i) * 500, "speaker_id": "a", "start_ms": i * 10000, "end_ms": i * 10000 + 9000} for i in range(12)]
    blocks = list(coherent_blocks(utterances, max_characters=1500))
    assert {u["id"] for b in blocks for u in b} == {u["id"] for u in utterances}
    for left, right in zip(blocks, blocks[1:]):
        assert len({u["id"] for u in left} & {u["id"] for u in right}) <= 1


def test_exact_quote_and_single_speaker_are_required_but_not_proof_of_entailment():
    sources = [{"id": "s0", "speaker_id": "a", "text": "Je propose une rénovation de la bibliothèque."}]
    claim = {"kind": "proposal", "speaker": "a", "text": "Une rénovation est proposée.", "evidence": [{"id": "s0", "quote": "une rénovation de la bibliothèque"}]}
    assert grounded_claim(claim, sources)[0]
    claim["speaker"] = "b"
    assert grounded_claim(claim, sources)[1] == "mixed_or_wrong_speaker"
    claim["speaker"] = "a"
    claim["kind"] = "reported_decision"
    assert grounded_claim(claim, sources)[1] == "decision_not_explicit"
    claim["evidence"][0]["quote"] = "Le conseil décide de rénover."
    assert grounded_claim(claim, sources)[1] == "quote_not_in_source"


def test_reanalysis_restores_previous_manual_text_names_and_sources(tmp_path):
    store = SessionStore(tmp_path)
    sid = store.create("Séance")
    rows = [{"id": "s0", "start_ms": 0, "end_ms": 1000, "text": "Correction humaine", "speaker_id": "a", "uncertain": False, "source": {"normalized_audio": "original-derived.wav"}}]
    store.save_analysis(sid, rows, {"a": "Mme Exemple"}, 0)
    store.save_analysis(sid, [{**rows[0], "text": "Nouvelle analyse"}], {"a": "Intervenant 1"}, store.get(sid)["revision"])
    previous = store.analysis_history(sid)[0]
    store.restore_analysis(sid, previous["id"])
    restored = store.get(sid)
    assert restored["utterances"][0]["text"] == "Correction humaine"
    assert restored["speakers"]["a"] == "Mme Exemple"
    assert json.loads(restored["utterances"][0]["source_json"])["normalized_audio"] == "original-derived.wav"
    assert len(store.analysis_history(sid)) == 3
    store.close()


def test_municipal_review_requires_explicit_secretary_role(tmp_path):
    store = SessionStore(tmp_path)
    sid = store.create("Conseil")
    rows = [{"id": "s0", "start_ms": 0, "end_ms": 1000, "text": "Discussion", "speaker_id": "a", "uncertain": True}]
    store.save_analysis(sid, rows, {"a": "Intervenant"}, 0)
    draft = integral_transcript(store.get(sid))
    draft["document_mode"] = "municipal"
    store.save_draft(sid, draft)
    with pytest.raises(ValueError, match="SECRETARY"):
        store.approve(sid, "Nom test")
    store.approve(sid, "Secrétaire test", role="secretary")
    state, review = store.reviewed_content(sid)
    assert state["draft"]["review"]["reviewer_role"] == "secretary"
    with pytest.raises(ValueError, match="SECRETARY"):
        export_draft(draft, review, tmp_path / "missing-role.pdf", session_id=sid, municipality="Test", session_date="2026-10-16")
    assert export_session(store, sid, tmp_path / "secretary-reviewed.pdf").exists()
    store.close()


def test_pdf_embeds_unicode_font_and_keeps_ids_internal(tmp_path):
    from pypdf import PdfReader
    text = "Élèves, cœur, œuvre, l’étudiante, 20\u202f€, « débat » — À vérifier."
    draft = {"document_mode": "summary", "points": [{"title": "Éducation", "summary": text, "sources": ["private-technical-id-123"], "vote_id": None}], "to_verify": []}
    path = export_draft(draft, record_human_review(draft, "Test fixture"), tmp_path / "unicode.pdf", session_id="private-uuid", municipality="Commune", session_date="2026-10-16")
    reader = PdfReader(path)
    extracted = "\n".join(p.extract_text() for p in reader.pages)
    assert "cœur" in extracted and "l’étudiante" in extracted and "œuvre" in extracted
    assert "private-technical-id" not in extracted and "private-uuid" not in extracted
    assert "Scrutins" not in extracted and "vote : à compléter" not in extracted
    font_objects = [f.get_object() for p in reader.pages for f in p["/Resources"]["/Font"].get_object().values()]
    assert any("NotoSans" in str(f.get("/BaseFont")) and f.get("/FontDescriptor") and f["/FontDescriptor"].get_object().get("/FontFile2") for f in font_objects)


def test_worker_protocol_is_ascii_and_restores_unicode(monkeypatch, tmp_path, capsys):
    from notetaker.workers import probe
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"engine": "asr"}), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["worker", str(request)])
    monkeypatch.setattr(probe, "transcribe", lambda req: {"text": "Élèves, œuvre, l’étudiante"})
    assert probe.main() == 0
    raw = capsys.readouterr().out
    assert raw.isascii()
    assert json.loads(raw)["result"]["text"] == "Élèves, œuvre, l’étudiante"


def test_damaged_historical_text_requires_retranscription_before_summary_or_export(tmp_path):
    from notetaker.engines.hierarchical_summary import summarize
    with pytest.raises(ValueError, match="DAMAGED_TRANSCRIPT"):
        summarize({"utterances": [{"text": "L’\ufffdtudiante"}]})
    draft = {"points": [{"title": "Éducation", "summary": "L’\ufffdtudiante", "sources": ["s0"], "vote_id": None}], "to_verify": []}
    with pytest.raises(ValueError, match="DAMAGED_TRANSCRIPT"):
        export_draft(draft, record_human_review(draft, "Test fixture"), tmp_path / "damaged.pdf", session_id="fixture", municipality="Test", session_date="2026-10-16")
    assert not (tmp_path / "damaged.pdf").exists()


def test_docx_contains_real_font_parts_and_relationships(tmp_path):
    import zipfile
    from importlib.resources import files
    from lxml import etree
    draft = {"points": [{"title": "Travaux", "summary": "Élèves et bibliothèque", "sources": ["internal-reference"], "vote_id": None}], "to_verify": []}
    path = export_draft(draft, record_human_review(draft, "Test fixture"), tmp_path / "fonts.docx", session_id="fixture", municipality="Test", session_date="2026-10-16")
    with zipfile.ZipFile(path) as package:
        for name in ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf"):
            assert package.read("word/fonts/" + name) == files("notetaker").joinpath("assets/fonts", name).read_bytes()
        root = etree.fromstring(package.read("word/fontTable.xml"))
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        assert len(root.xpath("//w:font[@w:name='Noto Sans']/w:embedRegular", namespaces=ns)) == 1
        assert b"application/x-font-ttf" in package.read("[Content_Types].xml")


@pytest.mark.parametrize("suffix", [".pdf", ".docx"])
def test_both_exports_refuse_uncovered_glyphs_without_replacing_an_existing_file(tmp_path, suffix):
    draft = {"points": [{"title": "Essai", "summary": "Texte 汉", "sources": ["s0"], "vote_id": None}], "to_verify": []}
    destination = tmp_path / ("existing" + suffix)
    destination.write_bytes(b"previous export retained")
    with pytest.raises(ValueError, match="UNSUPPORTED_EXPORT_GLYPHS"):
        export_draft(draft, record_human_review(draft, "Test fixture"), destination, session_id="fixture", municipality="Test", session_date="2026-10-16")
    assert destination.read_bytes() == b"previous export retained"


def test_restoring_an_edited_draft_preserves_both_versions_and_requires_new_review(tmp_path):
    store = SessionStore(tmp_path)
    sid = store.create("Séance")
    store.save_analysis(sid, [{"id": "s0", "speaker_id": "a", "start_ms": 0, "end_ms": 1000, "text": "Correction humaine", "uncertain": False}], {"a": "Mme Exemple"}, 0)
    draft = integral_transcript(store.get(sid))
    first = store.save_draft(sid, draft)
    store.approve(sid, "Test fixture")
    draft["points"][0]["summary"] = "Nouveau brouillon"
    store.save_draft(sid, draft)
    store.restore_draft(sid, first)
    assert len(store.draft_history(sid)) == 3
    assert store.get(sid)["draft"]["content"]["points"][0]["summary"] == "Correction humaine"
    with pytest.raises(ValueError, match="HUMAN_REVIEW"):
        store.reviewed_content(sid)
    store.close()


def test_source_units_preserve_spans_and_resolve_only_exact_same_voice_citations():
    rows = [
        {"id": "s0-0", "text": "Je conteste cette mesure.", "speaker_id": "a", "start_ms": 0, "end_ms": 1000},
        {"id": "s1-0", "text": "Elle bloque l'accès à la bibliothèque.", "speaker_id": "a", "start_ms": 1100, "end_ms": 3000},
        {"id": "s2-0", "text": "Je suis favorable à la mesure.", "speaker_id": "b", "start_ms": 4000, "end_ms": 5000},
    ]
    units = source_units(rows)
    assert len(units) == 2 and len(units[0]["source_spans"]) == 2
    claim = {"kind": "argument", "speaker": "a", "text": "L'accès à la bibliothèque motive une objection.",
             "evidence": [{"id": "bad-model-reference", "quote": "cette mesure. Elle bloque l'accès"}]}
    corrected = resolve_evidence(claim, units)
    assert [e["id"] for e in corrected["evidence"]] == ["s0-0", "s1-0"]
    assert grounded_claim(corrected, rows)[0]
    claim["speaker"] = "b"
    assert resolve_evidence(claim, units) is None


def test_reformatting_punctuation_does_not_turn_a_long_copy_into_a_summary():
    text = "Je pense que les étudiants doivent pouvoir accéder à la bibliothèque pendant toute la durée des examens."
    claim = {"kind": "position", "speaker": "a", "text": text.upper().replace(".", "!"), "evidence": [{"id": "s0", "quote": text}]}
    assert grounded_claim(claim, [{"id": "s0", "speaker_id": "a", "text": text}])[1] == "verbatim_transcription_not_a_summary"


def test_integral_mode_handles_empty_whisper_segments_and_keeps_timestamps():
    state = {"speakers": {"a": "Mme Exemple"}, "utterances": [
        {"id": "s0", "text": "", "speaker_id": None, "start_ms": 0, "end_ms": 100},
        {"id": "s1", "text": "Texte à conserver.", "speaker_id": "a", "start_ms": 1000, "end_ms": 2500}]}
    draft = integral_transcript(state)
    assert len(draft["points"]) == 1 and draft["points"][0]["summary"] == "Texte à conserver."
    assert "00:00:01" in draft["points"][0]["title"] and "Mme Exemple" in draft["points"][0]["title"]
    from notetaker.domain.minutes import validate_minutes
    validate_minutes(draft, {"s0", "s1"}, {})


@pytest.mark.parametrize('topics', [
    [{'title': 'Début', 'claims': ['c0']}],
    [{'title': 'Sujet', 'claims': ['c0', 'c1']}, {'title': 'Répétition', 'claims': ['c0']}],
    [{'title': 'Sujet', 'claims': ['c0', 'unknown']}],
])
def test_global_summary_cannot_silently_omit_or_duplicate_supported_information(topics):
    from notetaker.engines.hierarchical_summary import validate_grouping
    with pytest.raises(ValueError, match='SUMMARY_GROUPING_LOST_OR_DUPLICATED'):
        validate_grouping({'topics': topics}, ['c0', 'c1'])


def test_global_summary_accepts_complete_grouping_across_the_meeting():
    from notetaker.engines.hierarchical_summary import validate_grouping
    validate_grouping({'topics': [{'title': 'Fin', 'claims': ['c2']}, {'title': 'Début et milieu', 'claims': ['c0', 'c1']}]}, ['c0', 'c1', 'c2'])


def test_french_elisions_and_zero_duration_words_do_not_create_false_speakers():
    segments = [{'id': 's0', 'start': 0, 'end': 3, 'text': "C'est là qu'il y a débat.", 'words': [
        {'start': 0, 'end': .2, 'word': 'C'}, {'start': .2, 'end': .2, 'word': "'est"},
        {'start': .2, 'end': 1, 'word': ' là'}, {'start': 1, 'end': 1.2, 'word': ' qu'},
        {'start': 1.2, 'end': 1.4, 'word': "'il"}, {'start': 1.4, 'end': 1.6, 'word': ' y'},
        {'start': 1.6, 'end': 1.6, 'word': ' a'}, {'start': 1.6, 'end': 3, 'word': ' débat.'}]}]
    rows, _ = align_transcript(segments, {'turns': [{'start': 0, 'end': 3, 'speaker': 'a'}]})
    assert len(rows) == 1 and rows[0]['text'] == segments[0]['text'] and rows[0]['speaker_id'] == 'a'
    assert rows[0]['uncertain'] and rows[0]['source']['word_timing_inferred']


def test_zero_duration_word_at_a_real_voice_boundary_remains_uncertain():
    segments = [{'id': 's0', 'start': 0, 'end': 2, 'text': 'Oui et non.', 'words': [
        {'start': 0, 'end': 1, 'word': 'Oui'}, {'start': 1, 'end': 1, 'word': ' et'}, {'start': 1, 'end': 2, 'word': ' non.'}]}]
    rows, _ = align_transcript(segments, {'turns': [{'start': 0, 'end': 1, 'speaker': 'a'}, {'start': 1, 'end': 2, 'speaker': 'b'}]})
    assert [u['speaker_id'] for u in rows] == ['a', None, 'b']
    assert rows[1]['uncertain'] and ' '.join(u['text'] for u in rows) == 'Oui et non.'


def test_reported_opinion_is_not_silently_attributed_to_the_reporting_voice():
    from notetaker.services.pipeline import assemble_summary
    state = {'speakers': {'a': 'Présentateur'}, 'utterances': [{'id': 's0', 'uncertain': False}]}
    claim = {'id': 'c0', 'kind': 'argument', 'speaker': 'a', 'text': 'Le maintien des cours est invoqué.',
             'evidence': [{'id': 's0', 'quote': 'Vous estimez que les cours doivent continuer.'}]}
    result = {'claims': [claim], 'topics': [{'title': 'Cours', 'claims': ['c0']}], 'diagnostics': {}}
    # Assembly also scans transcript text for procedural vote signals.
    state['utterances'][0]['text'] = claim['evidence'][0]['quote']
    draft = assemble_summary(state, result)
    assert 'opinion rapportée — auteur à confirmer' in draft['points'][0]['summary']
    assert any('autre personne' in warning for warning in draft['to_verify'])
    claim['evidence'][0]['quote'] = 'Je souhaite que les cours continuent.'
    state['utterances'][0]['text'] = claim['evidence'][0]['quote']
    direct = assemble_summary(state, result)
    assert 'opinion rapportée' not in direct['points'][0]['summary']


def test_verification_sees_nearby_numeric_corrections_with_distinct_voices():
    from notetaker.engines.hierarchical_summary import verification_context
    rows = [
        {'id': 's0', 'speaker_id': 'a', 'start_ms': 10000, 'end_ms': 12000, 'text': 'Trente mille lycées.'},
        {'id': 's1', 'speaker_id': 'b', 'start_ms': 12000, 'end_ms': 13000, 'text': 'Quel est le nombre ?'},
        {'id': 's2', 'speaker_id': 'a', 'start_ms': 13000, 'end_ms': 16000, 'text': 'Trente mille personnes sur deux cents blocages.'},
        {'id': 's3', 'speaker_id': 'a', 'start_ms': 60000, 'end_ms': 62000, 'text': 'Autre sujet.'},
    ]
    claim = {'evidence': [{'id': 's0', 'quote': rows[0]['text']}]}
    context = verification_context(claim, rows)
    assert [u['id'] for u in context['turns']] == ['s0', 's1', 's2']
    assert [u['speaker'] for u in context['turns']] == ['a', 'b', 'a']
    assert claim['evidence'][0]['quote'] == 'Trente mille lycées.'


def test_real_topic_assignment_repair_covers_missing_ids_and_removes_duplicate_selection():
    from notetaker.engines.hierarchical_summary import apply_topic_assignments
    topics = [{'title': 'Début', 'claims': ['c0']}, {'title': 'Fin', 'claims': ['c0']}]
    result = apply_topic_assignments(topics, [{'id': 'c0'}, {'id': 'c1'}], {'c0': 't0', 'c1': 't1'})
    assert [t['claims'] for t in result['topics']] == [['c0'], ['c1']]


def test_topic_assignment_repair_refuses_missing_or_unknown_assignments():
    from notetaker.engines.hierarchical_summary import apply_topic_assignments
    for assignment in [{'c0': 't0'}, {'c0': 't0', 'c1': 'unknown'}]:
        with pytest.raises(ValueError, match='SUMMARY_GROUPING_LOST_OR_DUPLICATED'):
            apply_topic_assignments([{'title': 'Sujet'}], [{'id': 'c0'}, {'id': 'c1'}], assignment)


def test_summary_duplicate_ids_reach_assignment_repair_before_final_acceptance(monkeypatch, tmp_path):
    """Regression of the compiled-worker failure; model responses are test doubles."""
    from jsonschema import validate
    from notetaker.engines import hierarchical_summary as engine
    source = 'Je suis opposé à ce calendrier car la bibliothèque doit rester ouverte pendant les travaux.'
    calls = []

    def model_response(request, label, instruction, inputs, schema, tokens=1600):
        calls.append(label)
        if label.startswith('block-'):
            result = {'claims': [{'topic': 'Accès à la bibliothèque', 'kind': 'argument', 'speaker': 'a',
                'text': source, 'evidence': [{'id': 'u0', 'quote': source}]}]}
        elif label.startswith('rewrite-'):
            result = {'reformulations': [{'id': 'c0', 'kind': 'argument',
                'text': 'Le calendrier suscite une opposition motivée par le maintien de l’accès à la bibliothèque.'}]}
        elif label.startswith('verify-'):
            result = {'checks': [{'id': 'c0', 'verdict': 'supported'}]}
        elif label == 'global-topics':
            result = {'topics': [{'title': 'Accès à la bibliothèque', 'claims': ['c0', 'c0']}]}
        elif label == 'global-assignment-repair':
            result = {'assignments': {'c0': 't0'}}
        else:
            raise AssertionError(label)
        validate(result, schema)
        return result

    monkeypatch.setattr(engine, 'call_json', model_response)
    result = engine.summarize({'workspace': str(tmp_path), 'utterances': [
        {'id': 's0', 'speaker_id': 'a', 'start_ms': 0, 'end_ms': 10000, 'text': source}]})
    assert 'global-assignment-repair' in calls
    assert result['topics'][0]['claims'] == ['c0']
    assert result['diagnostics']['topic_assignment_repair'] is True
    assert json.loads((tmp_path/'global-topics-rejected.json').read_text(encoding='utf-8'))['topics'][0]['claims'] == ['c0', 'c0']
