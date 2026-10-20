"""Protocol checks only: no AI quality score and no native inference fixture."""
import copy
import json
import wave
from pathlib import Path
import pytest
from experiments.parcoursup_20261020.prepare import OUT, read, selected, CORE, sha
from experiments.parcoursup_20261020.run_case import literal_audit, require_audio_review, schema


def test_actual_input_alignment_preserves_every_core_id_time_and_extension():
    a = read(OUT/'inputs/A-original.json')['passages']
    b = read(OUT/'inputs/B-correction-proposee.json')['passages']
    c = read(OUT/'inputs/C-correction-contexte-large.json')['passages']
    assert [(r['id'],r['start_ms'],r['end_ms']) for r in a] == [(r['id'],r['start_ms'],r['end_ms']) for r in b]
    assert selected(c, CORE) == b
    assert len(a) == 109 and len(c) == 167


def test_citation_audit_exposes_invalid_quotes_and_ids_without_removing_results():
    result = {'questions': [], 'participants': [], 'propositions': [], 'desaccords': [],
        'arguments': [{'auteur':'A','texte':'Propos à vérifier','sources':['s1','invented']}],
        'citations_sources':[{'source_id':'s1','citation':'Citation inventée.'}]}
    before = copy.deepcopy(result)
    inputs = {'focus_start_ms':0,'focus_end_ms':1000,
        'passages':[{'id':'s1','text':'Je propose une consultation.','start_ms':0,'end_ms':1000}]}
    audit = literal_audit(result, inputs)
    assert result == before and audit['quality_validated'] is False
    assert audit['issues'][0]['reason'] == 'quote_not_literal'
    assert audit['issues'][1]['unknown_source_ids'] == ['invented']


def test_review_gate_requires_real_review_receipt_and_exact_input_hash(tmp_path):
    transcript = tmp_path/'input.json'; transcript.write_text('{}',encoding='utf-8')
    receipt = tmp_path/'review.json'
    require_audio_review('A-original',transcript,receipt)
    with pytest.raises(ValueError,match='REAL_HUMAN'): require_audio_review('B',transcript,receipt)
    receipt.write_text(json.dumps({'human_audio_review_completed':True,'reviewer':'Authored test fixture',
        'input_sha256':{'B':sha(transcript)}}),encoding='utf-8')
    require_audio_review('B',transcript,receipt)
    transcript.write_text('{"changed":true}',encoding='utf-8')
    with pytest.raises(ValueError,match='REAL_HUMAN'): require_audio_review('B',transcript,receipt)


def test_actual_audio_excerpt_is_exact_original_pcm_for_the_focal_interval():
    manifest = read(OUT/'manifest.json')
    with wave.open(manifest['source_audio'],'rb') as source, wave.open(str(OUT/'extrait-focal-17m32-20m38.wav'),'rb') as clip:
        rate = source.getframerate()
        source.setpos(round(CORE[0]*rate/1000))
        expected = source.readframes(round((CORE[1]-CORE[0])*rate/1000))
        assert clip.getframerate() == rate and clip.getnchannels() == source.getnchannels()
        assert clip.readframes(clip.getnframes()) == expected
