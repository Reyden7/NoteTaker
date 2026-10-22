"""Detailed reference checks, without guessing sources or relaxing export gates."""
import copy
import re
from notetaker.engines.hierarchical_summary import grounded_claim, normalized

REASONS = {
    'missing_source': 'Le passage source n’existe plus dans la transcription actuelle.',
    'missing_evidence': 'Cette affirmation n’a aucun extrait justificatif.',
    'quote_not_in_source': 'La citation ne figure plus dans le texte du passage indiqué.',
    'mixed_or_wrong_speaker': 'L’intervenant de l’affirmation diffère de celui de sa source.',
    'source_not_in_point': 'La source de cette affirmation n’est pas rattachée au point.',
    'missing_point_sources': 'Ce point n’a aucune source.',
    'malformed_claim': 'L’affirmation est incomplète : texte, type ou intervenant manquant.',
    'verbatim_transcription_not_a_summary': 'Le texte copie une longue transcription au lieu d’une reformulation.',
    'greeting_not_substantive': 'Cette affirmation contient une formule de présentation à corriger.',
    'action_not_explicitly_assigned': 'La source n’établit pas explicitement cette action ou responsabilité.',
    'decision_not_explicit': 'La source n’établit pas explicitement cette décision.',
    'vote_or_adoption_requires_operator': 'Un résultat de scrutin ou une adoption doit être vérifié et saisi séparément.',
    'empty_document': 'Le document ne contient aucun point.',
    'stale_attribution_text':'Le texte du point affiche encore une ancienne attribution. Utilisez « Actualiser les attributions depuis les sources » puis relisez la proposition.',
    'narrative_text_changed':'Le paragraphe ne correspond plus aux phrases sourcées. Enregistrez votre modification dans l’éditeur puis relisez cette nouvelle révision.',
    'narrative_missing_claim':'Une phrase du paragraphe référence une affirmation absente ou non rattachée. Corrigez les affirmations du point avant relecture.',
    'narrative_voice_changed':'Le paragraphe affiche une ancienne attribution ou une voix sans source. Actualisez les attributions depuis les sources, puis contrôlez la proposition.',
}


class DraftEvidenceError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('CLAIM_EVIDENCE_INVALID — ' + str(len(issues)) + ' référence(s) à corriger')


def draft_issues(content, state):
    sources = {u['id']: u for u in state['utterances']}
    issues = []
    def add(pi, p, ci, c, sid, reason):
        source = sources.get(sid)
        issues.append({'point_index': pi, 'point_title': p.get('title', ''), 'claim_index': ci,
            'claim_id': c.get('id'), 'claim_text': c.get('text', ''), 'source_id': sid,
            'reason': reason, 'message': REASONS.get(reason, reason),
            'expected_speaker': c.get('speaker'), 'actual_speaker': source.get('speaker_id') if source else None,
            'source_start_ms': source.get('start_ms') if source else None})
    if not content.get('points'):
        add(0, {}, None, {}, None, 'empty_document')
    for pi, p in enumerate(content.get('points', [])):
        from notetaker.domain.summary import narrative_problems
        for reason in narrative_problems(p,state):add(pi,p,None,{},None,reason)
        if not p.get('sources'):
            add(pi, p, None, {}, None, 'missing_point_sources')
        for sid in p.get('sources', []):
            if sid not in sources:
                add(pi, p, None, {}, sid, 'missing_source')
        for ci, c in enumerate(p.get('claims', [])):
            if not all(isinstance(c.get(k), str) and c[k] for k in ('speaker', 'kind', 'text')):
                add(pi, p, ci, c, None, 'malformed_claim')
                continue
            if not isinstance(c.get('evidence'),list) or not c['evidence']:
                add(pi, p, ci, c, None, 'missing_evidence')
                continue
            start = len(issues)
            for e in c['evidence']:
                if not isinstance(e,dict) or not isinstance(e.get('quote'),str):
                    add(pi,p,ci,c,None,'malformed_claim')
                    continue
                sid = e.get('id')
                u = sources.get(sid)
                if not u:
                    add(pi, p, ci, c, sid, 'missing_source')
                    continue
                if sid not in p.get('sources', []):
                    add(pi, p, ci, c, sid, 'source_not_in_point')
                quote = normalized(str(e.get('quote', '')).strip().strip('«»'))
                if not quote or quote not in normalized(u['text']):
                    add(pi, p, ci, c, sid, 'quote_not_in_source')
                if (u.get('speaker_id') or 'unattributed') != c['speaker']:
                    add(pi, p, ci, c, sid, 'mixed_or_wrong_speaker')
            if len(issues) == start:
                valid, reason = grounded_claim(c, state['utterances'])
                if not valid:
                    add(pi, p, ci, c, None, reason)
        # Generated display names are part of the document too. Do not approve
        # an old printed name merely because the structured UUID was retained.
        paragraphs=p.get('summary','').split('\n\n')
        claims=p.get('claims',[])
        # Bound templates already check printed names against current voices in
        # narrative_problems. The legacy prose parser cannot interpret qualifiers
        # such as "Intervenant non identifié (Voix 1)" correctly.
        bound_names=bool(p.get('narrative')) and all('template' in row for row in p['narrative'])
        if not bound_names and claims and len(paragraphs)==len(claims):
            for ci,(paragraph,c) in enumerate(zip(paragraphs,claims)):
                if isinstance(c.get('text'),str) and paragraph.endswith(' : '+c['text']) and ' — ' in paragraph:
                    display=paragraph.split(' — ',1)[1][:-len(' : '+c['text'])]
                    display=re.sub(r' \((?:attribution à vérifier|opinion rapportée — auteur à confirmer)(?: ; opinion rapportée — auteur à confirmer)?\)$','',display)
                    current=state['speakers'].get(c.get('speaker'))
                    if current and current!=display:
                        add(pi,p,ci,c,None,'stale_attribution_text')
    return issues


def require_valid_evidence(content, state):
    issues = draft_issues(content, state)
    if issues:
        raise DraftEvidenceError(issues)


def render_claims(claims, state):
    labels = {'position':'Position', 'argument':'Argument', 'proposal':'Proposition', 'context':'Contexte',
              'question':'Question soulevée', 'reported_decision':'Décision rapportée à confirmer',
              'reported_action':'Action rapportée à confirmer'}
    by_id = {u['id']:u for u in state['utterances']}
    paragraphs = []
    for c in claims:
        name = state['speakers'].get(c['speaker'], 'Voix inconnue')
        refs = [by_id.get(e['id']) for e in c.get('evidence', [])]
        notes = []
        if any(not u or u.get('uncertain', True) for u in refs):
            notes.append('attribution à vérifier')
        quotes = ' '.join(e.get('quote','') for e in c.get('evidence',[]))
        if re.search(r"\b(?:vous\s+(?:estimez|pensez|considérez|dites|affirmez)|selon\s+(?:vous|lui|elle)|(?:il|elle|ils|elles)\s+(?:estime\w*|pense\w*|affirme\w*|dit|disent))\b", quotes, re.I):
            notes.append('opinion rapportée — auteur à confirmer')
        if notes:
            name += ' (' + ' ; '.join(notes) + ')'
        paragraphs.append(f"{labels.get(c['kind'], c['kind'])} — {name} : {c['text']}")
    return '\n\n'.join(paragraphs)


def propose_attribution_refresh(content, state):
    """Only a proposal: caller must show it and obtain explicit acceptance."""
    updated = copy.deepcopy(content)
    by_id = {u['id']:u for u in state['utterances']}
    changes = []
    for pi, point in enumerate(updated.get('points', [])):
        changed = False
        for claim in point.get('claims', []):
            refs = [by_id.get(e.get('id')) for e in claim.get('evidence', [])]
            if not refs or any(not u for u in refs):
                continue
            speakers = {u.get('speaker_id') for u in refs}
            if len(speakers) != 1 or None in speakers:
                continue
            candidate = copy.deepcopy(claim)
            candidate['speaker'] = next(iter(speakers))
            if not grounded_claim(candidate, state['utterances'])[0]:
                continue
            if candidate['speaker'] != claim.get('speaker'):
                claim.setdefault('attribution_history', []).append({'from':claim.get('speaker'), 'to':candidate['speaker'], 'reason':'operator_source_refresh'})
                claim['speaker'] = candidate['speaker']
                claim['machine_verdict'] = 'attribution_changed_human_review_required'
                changed = True
        # Rendering is explicitly previewed. Do not silently erase manual prose.
        if 'narrative' in point:
            from notetaker.domain.summary import refresh_narrative
            changed |= refresh_narrative(point,content['points'][pi],state)
        elif point.get('claims'):
            paragraphs = point['summary'].split('\n\n')
            generated = len(paragraphs) == len(point['claims']) and all(p.endswith(' : '+c['text']) for p,c in zip(paragraphs,point['claims']))
            if generated:
                rendered = render_claims(point['claims'], state)
                changed |= rendered != point['summary']
                point['summary'] = rendered
        if changed:
            changes.append(pi)
    return updated, changes


def remap_sources(content, replacements):
    """Map known split/merged lineage only. Never search the whole transcript."""
    result = copy.deepcopy(content)
    for point in result.get('points', []):
        point['sources'] = list(dict.fromkeys(sid for old in point['sources'] for sid in replacements.get(old, {}).get('ids', [old])))
        for c in point.get('claims', []):
            evidence = []
            for e in c.get('evidence', []):
                mapping = replacements.get(e['id'])
                if not mapping:
                    evidence.append(e)
                elif 'split' not in mapping:
                    evidence.append({**e, 'id':mapping['ids'][0]})
                else:
                    old = mapping['original_text']
                    # Map normalized quote positions back to raw character positions.
                    chars, offsets = [], []
                    for match in re.finditer(r'\S+', old):
                        if chars:
                            chars.append(' ');offsets.append(match.start())
                        for j in range(match.start(),match.end()):
                            chars.append(old[j]);offsets.append(j)
                    text, quote = ''.join(chars), normalized(e['quote'].strip().strip('«»'))
                    index = text.find(quote)
                    if index < 0 or text.find(quote,index+1) >= 0:
                        evidence.append(e)  # keep invalid/ambiguous reference visible
                        continue
                    a,b = offsets[index],offsets[index+len(quote)-1]+1
                    for sid,start,end in mapping['split']:
                        excerpt = old[max(a,start):min(b,end)].strip() if min(b,end)>max(a,start) else ''
                        if excerpt:
                            evidence.append({'id':sid,'quote':excerpt})
            c['evidence'] = evidence
    return result
