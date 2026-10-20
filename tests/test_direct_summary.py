"""Authored model fixtures exercise contracts; they are not quality measurements."""
import copy
import json
import os
import subprocess
import sys
import uuid
import pytest
from notetaker.domain.direct_summary import (contexts, resolve_quote, validate_dispositions,
    source_inventory, test_workspace as require_test_workspace, MARKER, fingerprint, risk_reasons,
    VERSION, reference_spans, normalize_voice_template, plan_from_assignments, plan_from_catalogue)
from notetaker.engines.direct_summary import summarize, critic_payload
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.services.storage import SessionStore
from notetaker.services.direct_summary import DirectSummaryService, artifact_path


def row(text='Je propose de consulter les habitants.', *, id='s0', voice='a', start=0):
    return {'id': id, 'speaker_id': voice, 'start_ms': start, 'end_ms': start+4000,
            'text': text, 'uncertain': False}


def mark(root):
    atomic_json(root/MARKER, {'id': str(uuid.uuid4()), 'purpose': 'direct-summary-test'})


class AuthoredRuntime:
    """Deterministic fixture replies only, never a replacement production engine."""
    def __init__(self, *, bad_quote=False, bad_plan=False, rejected=False, budget=False):
        self.calls = []
        self.bad_quote, self.bad_plan, self.rejected, self.budget = bad_quote, bad_plan, rejected, budget

    def call(self, label, instruction, inputs, schema, tokens):
        self.calls.append((label, inputs))
        if label.startswith('context'):
            unit = inputs['core'][0]
            return {'sentences': [
                {'topic': 'Consultation des habitants', 'agenda_id': 'A1',
                 's': 'proposals', 'v': unit['speaker'], 'k': 'proposal', 'd': 'own',
                 't': '{{'+unit['speaker']+'}} propose une consultation des habitants.',
                 'r': ['NOT_IN_CONTEXT' if self.bad_quote else unit['parts'][0]['id']]}],
                'budget_reached': self.budget}
        if label == 'group-catalogue':
            return {'subjects': [{'title': 'Consultation des habitants', 'agenda_id': 'A1'}]}
        if label == 'group-000':
            ids = [p['id'] for p in inputs['phrases']]
            return {'assignments': {} if self.bad_plan else {cid: {
                'g': 0, 'o': i, 'why': ''} for i,cid in enumerate(ids)}}
        return {'checks': {key: {'verdict': 'not_explicit' if self.rejected and key.startswith('D') else 'supported',
                                 'reason': 'Cas de test rédigé manuellement'} for key in schema['properties']['checks']['properties']}}


def run_fixture(tmp_path, runtime, utterances=None):
    mark(tmp_path)
    return summarize({'experimental_direct': True, 'pipeline_version': VERSION, 'test_root': str(tmp_path), 'workspace': str(tmp_path),
        'utterances': utterances or [row()], 'agenda': ['Consultation'], 'lexicon': []}, runtime)


def test_contexts_preserve_every_character_with_pathological_turn_and_blank_inventory():
    rows = [row('Texte ' * 2400), row('', id='blank', start=15000)]
    blocks = list(contexts(rows))
    fragments = [u for b in blocks for u in b['core']]
    assert ''.join(u['text'] for u in fragments) == ' '.join(rows[0]['text'].split())
    assert len({u['id'] for u in fragments}) == len(fragments)
    inventory = source_inventory(rows, [], set())
    assert len(inventory) == 2 and inventory[1]['status'] == 'blank_preserved'
    for b in blocks:
        assert set(u['id'] for u in b['core']).isdisjoint(u['id'] for u in b['previous'])


def test_unique_quotes_remap_across_exact_original_segments():
    rows = [row('Je propose de'), row('consulter les habitants.', id='s1', start=4000)]
    unit = list(contexts(rows))[0]['core'][0]
    resolved = resolve_quote({'id': unit['id'], 'quote': 'de consulter'}, 'a', {unit['id']: unit})
    assert resolved == [{'id': 's0', 'quote': 'de'}, {'id': 's1', 'quote': 'consulter'}]
    assert resolve_quote({'id': unit['id'], 'quote': 'de consulter'}, 'b', {unit['id']: unit}) is None
    unit['text'] = 'oui oui'
    assert resolve_quote({'id': unit['id'], 'quote': 'oui'}, 'a', {unit['id']: unit}) is None


def test_reference_spans_preserve_all_nonblank_characters_with_exact_offsets():
    rows = [row(('Une consultation des habitants est proposée. ' * 90).strip())]
    units = [unit for block in contexts(rows) for unit in block['core']]
    refs = reference_spans(units)
    assert len({ref['id'] for ref in refs}) == len(refs)
    full = units[0]['full_text']
    covered = set()
    for ref in refs:
        assert ref['text'] == full[ref['offset']:ref['offset']+len(ref['text'])]
        covered.update(range(ref['offset'], ref['offset']+len(ref['text'])))
        resolved = resolve_quote({'id': ref['id'], 'quote': ref['text']}, 'a', {ref['id']: ref})
        assert resolved and all(e['quote'] in rows[0]['text'] for e in resolved)
    assert {i for i, character in enumerate(full) if not character.isspace()} <= covered


def test_plain_matching_voice_code_is_normalized_without_inventing_a_subject(tmp_path):
    class PlainAlias(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label.startswith('context'):
                result['sentences'][0]['t'] = 'V1 propose une consultation des habitants.'
            return result
    result = run_fixture(tmp_path, PlainAlias())
    claim = result['ledger']['candidates'][0]
    assert len(result['topics']) == 1 and claim['template_format_normalized']
    assert claim['raw']['t'].startswith('V1 ')
    assert claim['template'].startswith('{{V1}} ')
    assert normalize_voice_template('V2 demande une consultation.', 'V1')[1] == 'unbound_voice_alias'
    assert normalize_voice_template('Une consultation est nécessaire.', 'V1')[0] == 'Une consultation est nécessaire.'


@pytest.mark.parametrize('length,maximum', [('short', 4), ('standard', 7), ('detailed', 11)])
def test_repetitive_paragraph_cannot_grow_without_bound_but_sources_remain_complete(tmp_path, length, maximum):
    from jsonschema import validate, ValidationError
    mark(tmp_path)
    class SchemaProbe(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label.startswith('context'):
                assert inputs['maximum_sentences_this_context'] == maximum
                original = copy.deepcopy(result)
                result['sentences'] *= maximum + 1
                with pytest.raises(ValidationError):
                    validate(result, schema)
                assert ''.join(part['text'] for unit in inputs['core'] for part in unit['parts']) == row()['text']
                return original
            return result
    result = summarize({'experimental_direct': True, 'pipeline_version': VERSION, 'test_root': str(tmp_path),
        'workspace': str(tmp_path), 'utterances': [row()], 'agenda': ['Consultation'],
        'lexicon': [], 'summary_length': length}, SchemaProbe())
    assert result['ledger']['all_sources'] == [row()]


def test_unknown_or_other_voice_is_rejected_even_with_a_valid_reference(tmp_path):
    class WrongAlias(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label.startswith('context'):
                result['sentences'][0]['t'] = 'V2 propose une consultation des habitants.'
            return result
    result = run_fixture(tmp_path, WrongAlias(), [row(), row(id='s1', voice='b', start=5000)])
    assert result['topics'] == []
    assert result['ledger']['candidates'][0]['speaker'] == 'a'
    assert result['ledger']['rejected'][0]['reason'] == 'unbound_voice_alias'


def test_valid_direct_chain_uses_one_context_catalogue_assignment_and_targeted_check(tmp_path):
    runtime = AuthoredRuntime()
    result = run_fixture(tmp_path, runtime)
    assert len(result['topics']) == 1 and len(result['claims']) == 1
    assert [label for label, _ in runtime.calls] == ['context-000', 'group-catalogue', 'group-000', 'check-000']
    assert runtime.calls[0][1]['agenda'] == {'A1': 'Consultation'}
    assert result['ledger']['inventory'][0]['written_ids']
    assert result['diagnostics']['semantic_quality_validated'] is False


def test_context_keeps_long_turn_together_and_supplies_every_reference_part(tmp_path):
    runtime = AuthoredRuntime()
    text = ('Je propose de consulter les habitants. ' * 42).strip()
    run_fixture(tmp_path, runtime, [row(text)])
    payload = runtime.calls[0][1]
    assert len(payload['core']) == 1
    parts = payload['core'][0]['parts']
    assert len(parts) > 4
    assert ' '.join(part['text'] for part in parts) == text
    assert payload['target_total_words_this_context'] == 300
    assert payload['target_words_per_topic'] == 120


def test_critic_shares_context_but_never_merges_identical_words_from_different_voices():
    items = [{'id': 'A', 'source_refs': ['R1'], 'context_refs': ['U1']},
             {'id': 'B', 'source_refs': ['R1', 'R2'], 'context_refs': ['U1', 'U2']}]
    sources = {'R1': {'speaker': 'V1', 'quote': 'Oui.'}, 'R2': {'speaker': 'V2', 'quote': 'Oui.'}}
    contexts_by_id = {'U1': {'speaker': 'V1', 'text': 'Premier propos'},
                      'U2': {'speaker': 'V2', 'text': 'Autre propos'}}
    data = critic_payload(items, sources, contexts_by_id)
    assert data['items'] == items and data['sources'] == sources
    assert len(data['contexts']) == 2
    assert data['sources']['R1']['speaker'] != data['sources']['R2']['speaker']


def test_agenda_order_is_enforced_even_when_the_model_returns_reversed_groups(tmp_path):
    mark(tmp_path)
    class ReversedAgenda(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label.startswith('context'):
                second = copy.deepcopy(result['sentences'][0])
                second['agenda_id'] = 'A2'
                result['sentences'].append(second)
            if label == 'group-catalogue':
                result['subjects'] = [{'title': 'Consultation des habitants', 'agenda_id': aid} for aid in ('A2', 'A1')]
            if label == 'group-000':
                ids = [row['id'] for row in inputs['phrases']]
                result['assignments'] = {cid: {'g': i, 'o': i, 'why': ''}
                    for i,(aid,cid) in enumerate([('A2', ids[1]), ('A1', ids[0])])}
            return result
    result = summarize({'experimental_direct': True, 'pipeline_version': VERSION, 'test_root': str(tmp_path), 'workspace': str(tmp_path),
        'utterances': [row()], 'agenda': ['Premier point', 'Second point', 'Troisième point'], 'lexicon': []}, ReversedAgenda())
    assert [topic['agenda_id'] for topic in result['topics']] == ['A1', 'A2']
    assert any(alert.get('agenda_id') == 'A3' for alert in result['ledger']['alerts'])


@pytest.mark.parametrize('options', [{'bad_quote': True}, {'rejected': True}])
def test_rejected_prose_and_original_text_remain_consultable(tmp_path, options):
    result = run_fixture(tmp_path, AuthoredRuntime(**options))
    assert result['topics'] == []
    assert result['ledger']['candidates'][0]['raw']['t']
    assert result['ledger']['inventory'][0]['text'] == row()['text']
    assert result['ledger']['rejected'] and result['ledger']['alerts']


def test_incomplete_grouping_keeps_every_candidate_in_local_groups_with_alert(tmp_path):
    result = run_fixture(tmp_path, AuthoredRuntime(bad_plan=True, budget=True))
    assert len(result['topics']) == 1
    assert result['ledger']['failed_grouping']
    assert {'generation_budget_reached', 'grouping_failed_local_groups_preserved'} <= {
        a['reason'] for a in result['ledger']['alerts']}
    with pytest.raises(ValueError, match='INVENTORY'):
        validate_dispositions({'topics': [], 'omitted': []}, ['D1'])


def test_keyed_grouping_preserves_every_id_and_separates_justified_omissions():
    result = {'assignments': {
        'D1': {'g': 'Consultation', 'a': 'A1', 'o': 1, 'why': ''},
        'D2': {'g': 'Consultation', 'a': 'A1', 'o': 0, 'why': ''},
        'D3': {'g': '', 'a': 'outside', 'o': 2, 'why': 'Répétition exacte explicitement conservée.'}}}
    plan = plan_from_assignments(result, ['D1','D2','D3'])
    assert plan['topics'] == [{'title': 'Consultation', 'agenda_id': 'A1', 'sentences': ['D2','D1']}]
    assert plan['omitted'][0]['id'] == 'D3'
    validate_dispositions(plan, ['D1','D2','D3'])
    with pytest.raises(ValueError, match='INVENTORY'):
        plan_from_assignments(result, ['D1','D2','D3','D4'])
    result['assignments']['D3']['why'] = ''
    with pytest.raises(ValueError, match='OMISSION_REASON'):
        plan_from_assignments(result, ['D1','D2','D3'])


def test_native_group_schema_cannot_drop_ids_or_repeat_dispositions_in_lists(tmp_path):
    from jsonschema import validate, ValidationError
    class GroupSchemaProbe(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label == 'group-000':
                validate(result, schema)
                first = next(iter(result['assignments']))
                missing = copy.deepcopy(result)
                del missing['assignments'][first]
                with pytest.raises(ValidationError): validate(missing, schema)
                invalid_index = copy.deepcopy(result)
                invalid_index['assignments'][first]['g'] = len(inputs['subjects'])
                with pytest.raises(ValidationError): validate(invalid_index, schema)
                # Reproduces the old array-plan defect: selected twice and omitted.
                duplicated = {'topics':[{'title':'Consultation','agenda_id':'A1','sentences':[first,first]}],
                              'omitted':[{'id':first,'reason':'Doublon'}]}
                with pytest.raises(ValidationError): validate(duplicated, schema)
            return result
    result = run_fixture(tmp_path, GroupSchemaProbe())
    assert 'failed_grouping' not in result['ledger']
    assert len(result['topics']) == 1


def test_shared_subject_catalogue_groups_nonconsecutive_ids_and_preserves_exclusions():
    result = {'subjects': [{'title': 'Consultation', 'agenda_id': 'A1'},
                           {'title': 'Autre objet', 'agenda_id': 'outside'}], 'assignments': {
        'D1': {'g': 0, 'o': 0, 'why': ''}, 'D2': {'g': 1, 'o': 1, 'why': ''},
        'D3': {'g': 0, 'o': 2, 'why': ''}, 'D4': {'g': -1, 'o': 3, 'why': 'Répétition exacte.'}}}
    plan = plan_from_catalogue(result, ['D1', 'D2', 'D3', 'D4'])
    assert plan['topics'][0]['sentences'] == ['D1', 'D3']
    assert plan['topics'][1]['sentences'] == ['D2']
    assert plan['omitted'] == [{'id': 'D4', 'reason': 'Répétition exacte.'}]
    for invalid in (-2, 2, True):
        bad = copy.deepcopy(result); bad['assignments']['D1']['g'] = invalid
        with pytest.raises(ValueError, match='INVENTORY'):
            plan_from_catalogue(bad, ['D1', 'D2', 'D3', 'D4'])
    del result['assignments']['D4']
    with pytest.raises(ValueError, match='INVENTORY'):
        plan_from_catalogue(result, ['D1', 'D2', 'D3', 'D4'])


def test_fragmented_plan_is_visible_without_forcing_merges_or_dropping_sources(tmp_path):
    class Fragmented(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label == 'group-catalogue':
                result['subjects'] = [{'title': f'Consultation partie {i}', 'agenda_id': 'A1'} for i in range(len(inputs['phrases']))]
            if label == 'group-000':
                ids = list(result['assignments'])
                for i, cid in enumerate(ids): result['assignments'][cid]['g'] = i
            return result
    rows = [row(id=f's{i}', start=i*310000) for i in range(5)]
    result = run_fixture(tmp_path, Fragmented(), rows)
    assert result['ledger']['grouping_statistics']['single_candidate_subjects'] == 5
    assert any(a['reason'] == 'fragmented_grouping_requires_review' for a in result['ledger']['alerts'])
    assert len(result['ledger']['inventory']) == len(result['claims']) == 5


def test_exact_duplicate_is_kept_in_ledger_without_redundant_critic_or_written_sentence(tmp_path):
    class RepeatingFixture(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label.startswith('context'):
                result['sentences'] *= 2
            return result
    runtime = RepeatingFixture()
    result = run_fixture(tmp_path, runtime)
    original, duplicate = result['ledger']['candidates']
    assert original['status'] == 'written'
    assert duplicate['status'] == 'omitted' and duplicate['duplicate_of'] == original['id']
    assert duplicate['raw'] == original['raw'] and duplicate['evidence'] == original['evidence']
    assert result['diagnostics']['omitted_claims'] == 1
    assert len(result['topics'][0]['sentences']) == 1
    planned = next(inputs for label, inputs in runtime.calls if label.startswith('group'))
    assert len(planned['phrases']) == 1
    assert result['ledger']['explicit_omissions'][0]['reason'] == 'duplicate_candidate_preserved'


def test_one_heading_rejection_counts_all_affected_claims_and_preserves_them(tmp_path):
    class RejectedHeading(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label.startswith('check'):
                for key, value in result['checks'].items():
                    if key.startswith('T'):
                        value['verdict'] = 'not_explicit'
            return result
    result = run_fixture(tmp_path, RejectedHeading(), [row(), row(id='s1', start=310000)])
    assert result['topics'] == []
    assert result['diagnostics']['rejected_claims'] == 2
    assert result['diagnostics']['rejection_events'] == 1
    assert all(c['status'] == 'rejected' for c in result['ledger']['candidates'])


def test_experiment_rejects_implicit_activation_and_unmarked_roots(tmp_path):
    with pytest.raises(ValueError, match='TEST_COPY'):
        DirectSummaryService(tmp_path)
    with pytest.raises(ValueError, match='TEST_COPY'):
        require_test_workspace(tmp_path)
    with pytest.raises(ValueError, match='TEST_COPY'):
        summarize({'utterances': [row()]}, AuthoredRuntime())


def test_first_native_failure_keeps_source_inventory_and_context_manifest(tmp_path):
    class Failure:
        def call(self, *a, **kw):
            raise RuntimeError('FIXTURE_NATIVE_FAILURE')
    with pytest.raises(RuntimeError, match='FIXTURE_NATIVE_FAILURE'):
        run_fixture(tmp_path, Failure())
    saved = json.loads((tmp_path/'direct-checkpoint.json').read_text(encoding='utf-8'))
    assert saved['all_sources'] == [row()]
    assert len(saved['context_inventory']) == 1


@pytest.mark.parametrize('text,kind,discourse,prose,reason', [
    ('Pourquoi les habitants soutiennent-ils ce projet ?', 'question', 'question',
     '{{V1}} affirme que les habitants soutiennent ce projet.', 'question_changed_to_assertion'),
    ('Vous dites que les travaux sont nécessaires.', 'position', 'reported',
     '{{V1}} estime que les travaux sont nécessaires.', 'reported_opinion_assigned_to_reporting_voice'),
    ('Quand j’étais élève, je prenais ce bus.', 'proposal', 'anecdote',
     '{{V1}} propose de prendre ce bus.', 'anecdote_or_description_changed_to_proposal'),
    ('Je ne suis pas contre ce projet.', 'position', 'own',
     '{{V1}} est favorable au projet.', 'absence_of_opposition_changed_to_support'),
])
def test_observed_semantic_errors_are_rejected_even_with_exact_quotes(tmp_path, text, kind, discourse, prose, reason):
    class FaultyProse(AuthoredRuntime):
        def call(self, label, instruction, inputs, schema, tokens):
            result = super().call(label, instruction, inputs, schema, tokens)
            if label.startswith('context'):
                item = result['sentences'][0]
                item.update(k=kind, d=discourse, t=prose)
            return result
    result = run_fixture(tmp_path, FaultyProse(), [row(text)])
    assert result['topics'] == []
    assert result['ledger']['rejected'][0]['reason'] == reason
    assert result['ledger']['candidates'][0]['raw']['t'] == prose


def test_partial_citation_exposes_the_uncited_text_instead_of_claiming_coverage():
    source = row('Une consultation est proposée. Un autre point important reste à vérifier.')
    claims = [{'id': 'D1', 'evidence': [{'id': 's0', 'quote': 'Une consultation est proposée.'}]}]
    inventory = source_inventory([source], claims, {'D1'})
    assert inventory[0]['written_ids'] == ['D1']
    assert inventory[0]['uncited_text'][0]['text'].strip() == 'Un autre point important reste à vérifier.'
    assert inventory[0]['semantic_coverage'] == 'not_measured'


def test_role_or_political_labels_trigger_targeted_check_even_without_numbers_or_negation():
    source = row('Je veux parler de la consultation.')
    claim = {'speaker': 'a', 'kind': 'position', 'discourse': 'own', 'section': 'arguments',
        'text': 'La personne, maire de gauche, défend une consultation.',
        'evidence': [{'id': 's0', 'quote': source['text']}]}
    assert 'role_or_political_attribution' in risk_reasons(claim, {'s0': source})


def make_service_fixture(tmp_path, monkeypatch):
    mark(tmp_path)
    store = SessionStore(tmp_path)
    sid = store.create('Fixture expérimentale', {'agenda': ['Consultation']})
    store.save_analysis(sid, [row()], {'a': 'Alice Test'}, 0)
    from notetaker.services.information_registry import RegistryService
    RegistryService(store).initialize(sid)
    class Models:
        llama = 'not-executed'; llm = 'not-executed'
        def verify(self): pass
    service = DirectSummaryService(tmp_path, enabled=True, models=Models())
    def fixture_run(request_path):
        request = json.loads(request_path.read_text(encoding='utf-8'))
        return {'result': summarize(request, AuthoredRuntime())}
    monkeypatch.setattr(service, 'run', fixture_run)
    return store, sid, service


def test_provenance_review_exports_history_reopen_and_tamper_block(tmp_path, monkeypatch):
    from notetaker.services.session_export import export_session
    store, sid, service = make_service_fixture(tmp_path, monkeypatch)
    from notetaker.services.information_registry import RegistryService
    registry_before = copy.deepcopy(RegistryService(store).latest(sid))
    result = service.generate(sid)
    assert result['draft_saved']
    assert RegistryService(store).latest(sid) == registry_before
    with pytest.raises(ValueError, match='HUMAN_REVIEW'):
        export_session(store, sid, tmp_path/'refused.pdf')
    # Automated fixture review only; never applied to the debate.
    store.approve(sid, 'Relecture de fixture automatisée')
    export_session(store, sid, tmp_path/'fixture.pdf')
    export_session(store, sid, tmp_path/'fixture.docx')
    did = store.get(sid)['draft']['id']
    store.close()
    store = SessionStore(tmp_path)
    assert store.get(sid)['draft']['id'] == did
    store.reviewed_content(sid)
    artifact = artifact_path(tmp_path, sid, result['run_id'])
    artifact.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='PROVENANCE'):
        store.reviewed_content(sid)
    store.close()


def test_source_name_or_agenda_change_invalidates_experimental_provenance(tmp_path, monkeypatch):
    store, sid, service = make_service_fixture(tmp_path, monkeypatch)
    service.generate(sid)
    content = store.get(sid)['draft']['content']
    store.save_details(sid, 'Fixture expérimentale', {'agenda': ['Autre sujet']})
    with pytest.raises(ValueError, match='SOURCES_CHANGED'):
        store.save_draft(sid, content)
    store.close()


def test_completed_result_reuse_never_calls_ai_and_creates_unreviewed_history_revision(tmp_path, monkeypatch):
    store, sid, service = make_service_fixture(tmp_path, monkeypatch)
    result = service.generate(sid)
    store.approve(sid, 'Relecture de fixture automatisée')
    previous = store.get(sid)['draft']
    monkeypatch.setattr(service, 'run', lambda *a: (_ for _ in ()).throw(AssertionError('AI must not run')))
    reused = service.reuse(sid, result['run_id'])
    assert reused['fresh_calls'] == 0
    assert store.get(sid)['draft']['review'] is None
    assert store.get(sid)['draft']['revision'] == previous['revision'] + 1
    assert previous['id'] in {r['id'] for r in store.draft_history(sid)}
    with pytest.raises(ValueError, match='HUMAN_REVIEW'):
        store.reviewed_content(sid)
    path = artifact_path(tmp_path, sid, result['run_id'])
    data = json.loads(path.read_text(encoding='utf-8'))
    data['quality_validated'] = True
    atomic_json(path, data)
    with pytest.raises(ValueError, match='PROVENANCE'):
        service.reuse(sid, result['run_id'])
    store.close()


def test_old_experimental_request_cannot_be_overwritten_by_a_new_version_resume(tmp_path, monkeypatch):
    store, sid, service = make_service_fixture(tmp_path, monkeypatch)
    run_id = str(uuid.uuid4())
    request_path = artifact_path(tmp_path, sid, run_id).parent/'request.json'
    request_path.parent.mkdir(parents=True)
    atomic_json(request_path, {'pipeline_version': 'direct-topics-025-v1', 'raw_history': 'preserve'})
    before = sha256_file(request_path)
    with pytest.raises(ValueError, match='EXPERIMENT_VERSION_CHANGED'):
        service.generate(sid, resume_id=run_id)
    assert sha256_file(request_path) == before
    assert store.get(sid)['draft'] is None
    store.close()


@pytest.mark.skipif(os.name != 'nt', reason='Native Windows accounting')
def test_real_windows_cpu_accounting_includes_terminated_child():
    from notetaker.infrastructure.windows_job import start_process
    from notetaker.infrastructure.cpu_profile import job_cpu, process_cpu
    code = 'import time; end=time.process_time()+0.15\nwhile time.process_time()<end: pass'
    process, job = start_process([sys.executable, '-c',
        'import sys,subprocess,time;time.sleep(.2);subprocess.run([sys.executable,"-c",'+repr(code)+'])'])
    try:
        process.wait(timeout=10)
        cpu = job_cpu(job)
        own = process_cpu(process)
        # Windows venv launchers may spawn the actual interpreter as a child.
        assert cpu['processes'] >= 2
        assert cpu['user_seconds'] + cpu['kernel_seconds'] > own['user_seconds'] + own['kernel_seconds'] + .08
    finally:
        job.close()
