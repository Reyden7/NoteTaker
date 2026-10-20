"""Tests of actual experimental preservation and authored edge cases, not quality."""
import pytest
from experiments.parcoursup_20261020.prepare import OUT, read, sha
from experiments.parcoursup_20261020.import_human import V2, HUMAN, parse_human, group_turns
from experiments.parcoursup_20261020.run_compact import COMPACT_INSTRUCTION
from experiments.parcoursup_20261020.resolve_sources import resolve_quote


def test_human_bytes_preserved_and_changed_ids_fully_inventoried():
    assert (V2/'correction-humaine-originale.txt').read_bytes() == HUMAN.read_bytes()
    a = read(V2/'inputs/A-original.json')['passages']
    b = read(V2/'inputs/B-corrigee-humaine.json')['passages']
    receipt = read(V2/'provenance-humaine.json')
    omitted = receipt['omitted_rows_in_human_file']
    assert len(a)==109 and len(b)==103 and len(omitted)==6
    assert {r['id'] for r in b} | {r['id'] for r in omitted} == {r['id'] for r in a}
    assert {r['id'] for r in b}.isdisjoint({r['id'] for r in omitted})
    assert b == parse_human(HUMAN.read_text(encoding='utf-8-sig'),a)
    before = {r['id']:r for r in a}
    assert all((r['start_ms'],r['end_ms']) == (before[r['id']]['start_ms'],before[r['id']]['end_ms']) for r in b)


def test_grouping_preserves_every_row_word_id_and_author_in_order():
    for name in ('A-original','B-corrigee-humaine','C-corrigee-contexte'):
        data = read(V2/'inputs'/(name+'.json'))
        rows, turns = data['passages'], data['turns']
        assert turns == group_turns(rows)
        assert [key for t in turns for key in t['source_ids']] == [r['id'] for r in rows]
        assert ' '.join(t['text'] for t in turns) == ' '.join(r['text'] for r in rows)
        by_id = {r['id']:r for r in rows}
        assert all(by_id[key]['speaker_label']==t['speaker_label'] for t in turns for key in t['source_ids'])


def test_wider_condition_has_identical_corrected_core_and_only_original_extension():
    a = read(V2/'inputs/A-original.json')
    b = read(V2/'inputs/B-corrigee-humaine.json')
    c = read(V2/'inputs/C-corrigee-contexte.json')
    assert c['passages'][-len(b['passages']):] == b['passages']
    assert len(c['passages'])-len(b['passages']) == 58
    assert all(r['start_ms']<a['focus_start_ms'] for r in c['passages'][:-len(b['passages'])])
    assert COMPACT_INSTRUCTION.count('Lis TOUS ses passages') == 1


def test_human_parser_rejects_untraceable_duplicate_and_reordered_sources():
    rows = [{'id':'s1-0','start_ms':1000,'end_ms':2000,'text':'Original','speaker_label':'A'},
            {'id':'s2-0','start_ms':2000,'end_ms':3000,'text':'Suite','speaker_label':'A'}]
    good = '- **00:01.000 · s1-0 · B** : Correction'
    assert parse_human(good,rows)[0]['speaker_label']=='B'
    for bad in [good.replace('s1-0','s99-0'),good.replace('00:01.000','00:00.999'),good+'\n'+good,
                '- **00:02.000 · s2-0 · A** : Suite\n'+good]:
        with pytest.raises(ValueError): parse_human(bad,rows)


def test_protected_production_sources_still_match_original_manifest():
    assert all(sha(path)==digest for path,digest in read(OUT/'manifest.json')['protected_files'].items())


def test_literal_quote_resolution_crosses_fragments_without_inventing_alignment():
    rows = [{'id':'s1','text':'une plateforme avec','start_ms':0,'end_ms':1000,'speaker_label':'A'},
            {'id':'s2','text':'une centralisation des vœux','start_ms':1000,'end_ms':2000,'speaker_label':'A'}]
    turn = group_turns(rows)[0]; by_id={r['id']:r for r in rows}
    result=resolve_quote('plateforme avec une centralisation',turn,by_id)
    assert result['status']=='literal_unique'
    assert result['matches'][0]['source_ids']==['s1','s2']
    assert result['matches'][0]['end_ms_marker']==2000
    assert resolve_quote('une autre plateforme',turn,by_id)['status']=='not_literal'
