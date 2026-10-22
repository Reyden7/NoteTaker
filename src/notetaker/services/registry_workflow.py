"""Shared explanations for approval and the source/information review workflow."""
from collections import Counter
from notetaker.domain.information_registry import evidence_issues, ambiguous_origin, to_claim, admissible


def approval_blockers(entry, state):
    if entry['category'] != 'information':
        return ['source_is_not_information']
    issues = evidence_issues(entry, state)
    if ambiguous_origin(entry, state):
        issues.append('ambiguous_source_occurrence')
    if any(e.get('end_ms', 0) <= e.get('start_ms', 0) for e in entry.get('evidence', [])):
        issues.append('source_interval_empty')
    if entry.get('speaker') == 'unattributed':
        issues.append('unknown_source_voice')
    if not entry['content'].strip():
        issues.append('missing_content')
    if not issues:
        from notetaker.engines.registry_summary import static_reason
        reason = static_reason(to_claim(entry), {'utterances':state['utterances'],
            'lexicon':state.get('metadata', {}).get('lexicon', [])})
        if reason:
            issues.append(reason)
    return list(dict.fromkeys(issues))


def preparation_report(document, state, previous=None):
    all_infos = [e for e in document['entries'] if e['category'] == 'information']
    infos = [e for e in all_infos if not e.get('previous_extraction')]
    previous_ids = {e['id'] for e in (previous or {}).get('entries', [])}
    reasons = Counter(reason for e in infos for reason in approval_blockers(e, state))
    sources = [e for e in document['entries'] if e['category'] == 'source']
    return {'created_information_entries':sum(e['id'] not in previous_ids for e in infos),
        'active_information_entries':len(infos),'previous_information_entries':len(all_infos)-len(infos),
        'processing_status':document['processing'].get('status','seeded'),
        'proposed_information_entries':sum(e['human_status']=='pending' and not approval_blockers(e,state) for e in infos),
        'blocked_information_entries':sum(bool(approval_blockers(e,state)) for e in infos),
        'approved_information_entries':sum(e['human_status']=='approved' for e in infos),
        'approval_blockers':dict(reasons),
        'inspected_units':len(document['processing'].get('inspected_units', [])),
        'total_units':document['processing'].get('total_units', 0),
        'uninspected_sources':sum('inspection' not in e for e in sources),
        'sources_without_usable_citation':sum(not e.get('candidate_ids') for e in sources),
        'extraction_reasons':dict(Counter(e.get('inspection',{}).get('reason','Non examiné')
            for e in sources if not e.get('candidate_ids'))),
        'ready_to_write':sum(admissible(e,state) and not approval_blockers(e,state) for e in infos)}
