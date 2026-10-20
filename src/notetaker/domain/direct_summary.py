"""Contracts for the opt-in experiment; no registry mutation or approval."""
import json
import re
import uuid
from pathlib import Path
from notetaker.domain.minutes import content_digest
from notetaker.infrastructure.paths import default_data_root

VERSION = 'direct-topics-025-v5'
MARKER = 'EXPERIMENTAL-TEST-WORKSPACE.json'
SECTIONS = ['context', 'arguments', 'divergences', 'proposals', 'potential_decisions']


def input_snapshot(state):
    return {key: state.get(key, {} if key == 'speakers' else []) for key in
            ('utterances', 'speakers')} | {'agenda': state.get('metadata', {}).get('agenda', []),
                'lexicon': state.get('metadata', {}).get('lexicon', [])}


def fingerprint(state):
    return content_digest(input_snapshot(state))


def test_workspace(root):
    root = Path(root).resolve()
    if root == default_data_root().resolve():
        raise ValueError('DIRECT_TEST_COPY_REQUIRED')
    try:
        marker = json.loads((root / MARKER).read_text(encoding='utf-8'))
        uuid.UUID(marker['id'])
        if marker['purpose'] != 'direct-summary-test':
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('DIRECT_TEST_COPY_REQUIRED') from None
    return marker


def contexts(utterances, max_characters=7800, max_seconds=300):
    """All nonblank text is processed; full inventory separately retains blanks.

    Compact same-voice turns first. Bound pathological merged turns with exact
    offsets; no token truncation. Previous unit is context only, never core.
    """
    from notetaker.engines.hierarchical_summary import source_units
    records = []
    for unit in source_units(utterances):
        for offset in range(0, len(unit['text']), 2200):
            records.append({**unit, 'id': f"U{len(records)+1}", 'full_text': unit['text'],
                            'text': unit['text'][offset:offset+2200], 'offset': offset})
    index = 0
    while index < len(records):
        core, size = [], 0
        while index < len(records):
            unit = records[index]
            if core and (size + len(unit['text']) > max_characters or
                         unit['end_ms'] - core[0]['start_ms'] > max_seconds * 1000):
                break
            core.append(unit)
            size += len(unit['text'])
            index += 1
        yield {'core': core, 'previous': records[index-len(core)-1:index-len(core)]
               if index > len(core) else []}


def resolve_quote(evidence, speaker, units):
    """Require the stated context ID and a unique exact occurrence, same voice."""
    from notetaker.engines.hierarchical_summary import normalized
    unit = units.get(evidence['id'])
    quote = normalized(evidence['quote']).strip('«»"').strip()
    if not unit or (unit.get('speaker_id') or 'unattributed') != speaker or not quote:
        return None
    if unit['text'].count(quote) != 1:
        return None
    start = unit['text'].index(quote) + unit['offset']
    end = start + len(quote)
    # spans address the unsplit, normalized full unit.
    full = unit['full_text']
    resolved = []
    for span in unit['source_spans']:
        a, b = max(start, span['start']), min(end, span['end'])
        if b > a and full[a:b].strip():
            resolved.append({'id': span['id'], 'quote': full[a:b].strip()})
    return resolved or None


def reference_spans(units, max_characters=360):
    """Short, exact references covering all source text; no model quotation copy.

    Prefer a sentence boundary, then a word boundary. Offsets still address the
    original normalized full turn, including pathological split turns.
    """
    result = []
    for unit in units:
        text, offset, part = unit['text'], 0, 0
        while offset < len(text):
            end = min(len(text), offset + max_characters)
            if end < len(text):
                boundary = max(text.rfind(mark, offset+80, end) for mark in ('. ', '? ', '! ', '; '))
                if boundary >= offset+80:
                    end = boundary+1
                else:
                    space = text.rfind(' ', offset+80, end)
                    if space > offset:
                        end = space
            raw = text[offset:end]
            left = len(raw)-len(raw.lstrip())
            if raw.strip():
                part += 1
                result.append({**unit, 'id': f"{unit['id']}S{part}", 'unit_id': unit['id'], 'text': raw.strip(),
                               'offset': unit['offset']+offset+left})
            offset = end
    return result


def normalize_voice_template(text, alias):
    """Normalize only an explicit matching technical subject, never add one."""
    from notetaker.domain.summary import TOKEN
    pattern = r'^(?:\{\{'+re.escape(alias)+r'\}\}|\{'+re.escape(alias)+r'\}|'+re.escape(alias)+r')(?=\s|[,—:])'
    match = re.match(pattern, text)
    candidate = '{{'+alias+'}}'+text[match.end():] if match else text
    if re.search(r'\bV\d+\b', TOKEN.sub('', candidate)):
        return candidate, 'unbound_voice_alias'
    return candidate, None


def risk_reasons(claim, sources):
    text = claim['text'] + ' ' + ' '.join(e['quote'] for e in claim['evidence'])
    risks = []
    if re.search(r'\d|\b(?:aucun|jamais|sans|ne|pas|contre|mais|contraire)\b', text, re.I):
        risks.append('numbers_negation_or_opposition')
    if re.search(r"\?|\b(?:selon|cite|citent|dites|reproche|raconte|anecdote|décid\w*|propos\w*)\b", text, re.I):
        risks.append('source_modality_or_context')
    if re.search(r'\b(?:maire|adjoint\w*|président\w*|ministre\w*|élus?|secrétaire\w*|parti|droite|gauche|centriste\w*|extrême)\b', text, re.I):
        risks.append('role_or_political_attribution')
    if claim['discourse'] != 'own' or claim['kind'] in ('question', 'proposal'):
        risks.append('modality_or_reported_position')
    if claim['section'] in ('divergences', 'potential_decisions', 'proposals'):
        risks.append('relation_proposal_or_decision')
    if claim['speaker'] == 'unattributed' or any(sources[e['id']].get('uncertain') for e in claim['evidence']):
        risks.append('uncertain_source_attribution')
    return risks


def validate_dispositions(plan, expected):
    selected = [cid for topic in plan['topics'] for cid in topic['sentences']]
    omitted = [row['id'] for row in plan['omitted']]
    all_ids = selected + omitted
    if set(all_ids) != set(expected) or len(all_ids) != len(set(all_ids)):
        raise ValueError('DIRECT_GROUPING_INVENTORY_INVALID')
    if any(not row['reason'].strip() for row in plan['omitted']):
        raise ValueError('DIRECT_OMISSION_REASON_REQUIRED')


def plan_from_assignments(result, expected):
    """One required object key per candidate prevents duplicated dispositions.

    Ranking is layout only. A tied rank keeps the original candidate order;
    it never implies a relation, a consensus or evidential support.
    """
    assignments = result.get('assignments', {})
    if set(assignments) != set(expected):
        raise ValueError('DIRECT_GROUPING_INVENTORY_INVALID')
    plan = {'topics': [], 'omitted': []}
    ordered = sorted(enumerate(expected), key=lambda pair: (assignments[pair[1]]['o'], pair[0]))
    groups = {}
    for _, cid in ordered:
        row = assignments[cid]
        title = row['g'].strip()
        if not title:
            if not row['why'].strip():
                raise ValueError('DIRECT_OMISSION_REASON_REQUIRED')
            plan['omitted'].append({'id': cid, 'reason': row['why']})
            continue
        if len(title) < 3:
            raise ValueError('DIRECT_GROUPING_INVENTORY_INVALID')
        key = row['a'], title
        if key not in groups:
            groups[key] = {'title': title, 'agenda_id': row['a'], 'sentences': []}
            plan['topics'].append(groups[key])
        groups[key]['sentences'].append(cid)
    validate_dispositions(plan, expected)
    return plan


def plan_from_catalogue(result, expected):
    """Resolve a shared subject catalogue, then apply the same inventory gate.

    Catalogue membership is a provisional model classification, never evidence
    of agreement, a logical relationship or faithful paraphrasing.
    """
    subjects = result.get('subjects', [])
    assignments = result.get('assignments', {})
    if set(assignments) != set(expected) or len(subjects) > len(expected):
        raise ValueError('DIRECT_GROUPING_INVENTORY_INVALID')
    converted = {}
    for cid, row in assignments.items():
        index = row['g']
        if type(index) is not int or index < -1 or index >= len(subjects):
            raise ValueError('DIRECT_GROUPING_INVENTORY_INVALID')
        subject = subjects[index] if index >= 0 else {'title': '', 'agenda_id': 'outside'}
        converted[cid] = {'g': subject['title'], 'a': subject['agenda_id'],
                          'o': row['o'], 'why': row['why']}
    return plan_from_assignments({'assignments': converted}, expected)


def source_inventory(utterances, claims, retained):
    """Literal citation accounting, never semantic completeness."""
    result = []
    for source in utterances:
        cited = [(c['id'], e['quote']) for c in claims for e in c.get('evidence', []) if e['id'] == source['id']]
        normalized = ' '.join(source['text'].split())
        covered = [False] * len(normalized)
        for cid, quote in cited:
            quote = ' '.join(quote.split())
            start = normalized.find(quote)
            if cid in retained and start >= 0 and normalized.count(quote) == 1:
                covered[start:start+len(quote)] = [True] * len(quote)
        remainders = []
        start = None
        for i in range(len(normalized)+1):
            if i < len(normalized) and not covered[i]:
                if start is None:
                    start = i
            elif start is not None:
                if normalized[start:i].strip():
                    remainders.append({'start_character': start, 'end_character': i, 'text': normalized[start:i]})
                start = None
        result.append({**source, 'candidate_ids': list(dict.fromkeys(cid for cid, _ in cited)),
            'written_ids': list(dict.fromkeys(cid for cid, _ in cited if cid in retained)),
            'citations': [quote for _, quote in cited],
            'status': 'blank_preserved' if not source['text'].strip() else
                      'cited' if any(cid in retained for cid, _ in cited) else 'not_cited_in_document',
            'uncited_text': remainders, 'citation_character_coverage': sum(covered),
            'semantic_coverage': 'not_measured'})
    return result
