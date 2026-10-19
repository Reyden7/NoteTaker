"""Experimental direct topic writing; existing safety checks remain mandatory.

Intermediate prose is reused verbatim by the global plan. Rejections, missing
assignments and uncited source text remain visible in an independent ledger.
"""
import time
from pathlib import Path
from .hierarchical_summary import object_schema, grounded_claim
from .topic_summary import sentence_problem, identity_problem
from .direct_runtime import DirectRuntime
from notetaker.domain.direct_summary import (VERSION, SECTIONS, contexts, resolve_quote,
    risk_reasons, validate_dispositions, source_inventory, test_workspace, reference_spans, normalize_voice_template)
from notetaker.domain.minutes import content_digest
from notetaker.domain.summary import TOKEN, validate_lexicon, PROFILES
from notetaker.infrastructure.atomic import atomic_json

TEXT = {'type': 'string', 'minLength': 1}
VERDICTS = ['supported', 'contradicted', 'not_explicit', 'uncertain']


def enum(values):
    return {'type': 'string', 'enum': list(values)}


def array(item):
    return {'type': 'array', 'items': item}


def critic_payload(items, source_catalogue, context_catalogue):
    """Share identical literal excerpts/turns instead of repeating them per claim."""
    refs = dict.fromkeys(rid for item in items for rid in item['source_refs'])
    turns = dict.fromkeys(uid for item in items for uid in item.get('context_refs', []))
    return {'items': items, 'sources': {rid: source_catalogue[rid] for rid in refs},
            'contexts': {uid: context_catalogue[uid] for uid in turns}}


def validate_request(request):
    if request.get('experimental_direct') is not True:
        raise ValueError('DIRECT_TEST_COPY_REQUIRED')
    if request.get('pipeline_version') != VERSION:
        raise ValueError('DIRECT_EXPERIMENT_VERSION_CHANGED')
    test_workspace(request['test_root'])
    if not request.get('utterances'):
        raise ValueError('TRANSCRIPT_REQUIRED')
    ids = [u['id'] for u in request['utterances']]
    if len(ids) != len(set(ids)):
        raise ValueError('DIRECT_SOURCE_IDS_INVALID')
    if any('\ufffd' in u['text'] for u in request['utterances']):
        raise ValueError('DAMAGED_TRANSCRIPT_RETRANSCRIBE_ORIGINAL')
    validate_lexicon(request.get('lexicon', []))
    if request.get('summary_length', 'standard') not in PROFILES:
        raise ValueError('DIRECT_INVALID_LENGTH')


def summarize(request, runtime=None):
    validate_request(request)
    started = time.perf_counter()
    runtime = runtime or DirectRuntime(request)
    utterances = request['utterances']
    sources = {u['id']: u for u in utterances}
    voices = list(dict.fromkeys(u.get('speaker_id') or 'unattributed' for u in utterances))
    aliases = {f'V{i+1}': voice for i, voice in enumerate(voices)}
    reverse = {v: a for a, v in aliases.items()}
    agenda = [s.strip() for s in request.get('agenda', []) if isinstance(s, str) and s.strip()]
    agenda_ids = {f'A{i+1}': title for i, title in enumerate(agenda)}
    checkpoint = {'version': VERSION, 'candidates': [], 'parts': [], 'rejected': [],
                  'alerts': [], 'grouping': None, 'all_sources': utterances, 'explicit_omissions': [],
                  'reference_manifest': []}
    work = Path(request['workspace'])
    seen_prose = {}

    def persist():
        atomic_json(work/'direct-checkpoint.json', checkpoint)

    blocks = list(contexts(utterances))
    checkpoint['context_inventory'] = [{'core_ids': [u['id'] for u in block['core']],
        'characters': sum(len(u['text']) for u in block['core']),
        'start_ms': block['core'][0]['start_ms'], 'end_ms': block['core'][-1]['end_ms']}
        for block in blocks]
    persist()
    for index, block in enumerate(blocks):
        atomic_json(work/'summary-progress.json', {'phase': 'direct_contexts', 'completed': index, 'total': len(blocks)})
        units = {u['id']: u for u in reference_spans(block['core'])}
        checkpoint['reference_manifest'].extend({'id': unit['id'], 'block': index,
            'unit_id': unit['unit_id'],
            'speaker': unit.get('speaker_id') or 'unattributed', 'text': unit['text'],
            'offset': unit['offset'], 'source_spans': unit['source_spans'],
            'start_ms': unit['start_ms'], 'end_ms': unit['end_ms']} for unit in units.values())
        persist()
        profile = PROFILES[request.get('summary_length', 'standard')]
        sentence_schema = object_schema({'topic': {'type': 'string', 'minLength': 3, 'maxLength': 100},
            'agenda_id': enum([*agenda_ids, 'outside']),
            't': {'type': 'string', 'minLength': 15, 'maxLength': 700},
            'v': enum(reverse.values()), 'k': enum(['context', 'argument', 'position', 'question', 'proposal']),
            'd': enum(['own', 'question', 'reported', 'anecdote']),
            's': enum(SECTIONS),
            'r': {'type': 'array', 'minItems': 1, 'maxItems': 4, 'items': enum(units)}})
        schema = object_schema({'sentences': {
                'type': 'array', 'maxItems': profile['sentences'], 'items': sentence_schema},
            'budget_reached': {'type': 'boolean'}})
        def payload(u):
            return {'id': u['id'], 'speaker': reverse[u.get('speaker_id') or 'unattributed'],
                    'start_ms': u['start_ms'], 'end_ms': u['end_ms'], 'text': u['text']}
        core = []
        for unit in block['core']:
            core.append({'id': unit['id'], 'speaker': reverse[unit.get('speaker_id') or 'unattributed'],
                'start_ms': unit['start_ms'], 'end_ms': unit['end_ms'],
                'parts': [{'id': ref['id'], 'text': ref['text']} for ref in units.values() if ref['unit_id'] == unit['id']]})
        result = runtime.call(f'context-{index:03d}',
            "Rédige une SYNTHÈSE des discussions de ce contexte, en paragraphes courts par sujet précis. "
            "Chaque objet core est un tour de parole ; ses parts sont des repères de citation du MÊME tour. "
            "Rassemble les arguments et les répétitions dans une formulation dense et fidèle. "
            "Respecte la longueur indicative fournie, en conservant les idées importantes de chaque voix. "
            "Les phrases successives d'un sujet doivent former un paragraphe cohérent. "
            "Le JSON compact utilise s=rubrique, v=voix, k=type, d=origine du propos, t=phrase et r=références. "
            'Structure : {"sentences":[{"topic":"Sujet précis","agenda_id":"outside",'
            '"t":"V1 explique une idée explicitement soutenue par ses sources.","v":"V1","k":"argument",'
            '"d":"own","s":"arguments","r":["identifiant de part"]}],"budget_reached":false}. '
            "Cet exemple décrit le format, pas le contenu à reproduire. Chaque phrase est une synthèse attribuée, jamais une copie brute. "
            "Ne répète aucune phrase. Couvre les sujets et arguments substantiels avec des formulations denses. "
            "La longueur est celle du résumé du CONTEXTE ENTIER, pas un quota par sujet. "
            "Préserve les auteurs et le contexte ; regroupe les répétitions, sans inventer de consensus. "
            "L'ordre du jour est prioritaire : attribue agenda_id lorsque pertinent ; un seul point général sert de cadre, "
            "avec plusieurs sous-sujets. Sans ordre exploitable, repère les changements de sujet. "
            "Chaque phrase concerne UNE voix et commence par son code explicite V1, V2, etc., suivi du verbe. Aucun nom inventé. "
            "Rédige des phrases qui s'enchaînent en paragraphe, avec un référent explicite plutôt qu'un 'cela' isolé. "
            "Varie les verbes ; pas de liste de reformulations décousues. La voix affirme, demande, rapporte, conteste ou propose : "
            "n'énonce jamais son opinion comme un fait établi. Respecte questions, négations, critiques et opinions citées. "
            "L'anecdote reste un récit, jamais une proposition officielle. Ne déduis aucun vote ni décision adoptée. "
            "Les décisions évoquées vont dans potential_decisions pour contrôle humain séparé. "
            "Distingue context, arguments, divergences, proposals et potential_decisions. Une divergence exprime la position "
            "de cette voix, sans inventer une relation d'accord/désaccord avec une autre. "
            "r contient les IDENTIFIANTS des parts nécessaires pour soutenir TOUTE la phrase, de la même voix. "
            "Une phrase reste de portée précise ; si quatre extraits ne suffisent pas, rédige plusieurs phrases distinctes. "
            "Ne recopie pas les citations : le logiciel conserve leur texte exact depuis ces identifiants. "
            "Le contexte previous aide à comprendre, jamais à citer. Le logiciel conserve tous les textes non cités dans l'inventaire. "
            "budget_reached=true si des informations substantielles restent à extraire faute de place. "
            "Ne compense pas un manque de source par une supposition.",
            {'agenda': agenda_ids, 'single_agenda_is_umbrella': len(agenda_ids) == 1,
             'lexicon': request.get('lexicon', []), 'summary_length': request.get('summary_length', 'standard'),
             'target_words_per_topic': profile['words_per_topic'],
             'maximum_sentences_this_context': profile['sentences'],
             'target_total_words_this_context': {'short': 170, 'standard': 300, 'detailed': 500}[request.get('summary_length', 'standard')],
             'previous': [payload(u) for u in block['previous']], 'core': core},
            schema, tokens=5500)
        if result['budget_reached'] or len(result['sentences']) == profile['sentences']:
            checkpoint['alerts'].append({'subject': f'Contexte {index+1}', 'reason': 'generation_budget_reached', 'priority': 'high'})
        checkpoint['parts'].append({'block': index, 'core_ids': list(units), 'raw': result})
        local_topics = {}
        for row in result['sentences']:
            key = (row['topic'], row['agenda_id'])
            topic = local_topics.setdefault(key, {'title': row['topic'], 'agenda_id': row['agenda_id'], 'sentences': []})
            topic['sentences'].append(row)
        for ti, topic in enumerate(local_topics.values()):
            for si, raw_row in enumerate(topic['sentences']):
                row = {key: raw_row[short] for key, short in {
                    'section': 's', 'speaker': 'v', 'kind': 'k', 'discourse': 'd', 'text': 't', 'evidence': 'r'}.items()}
                cid = 'D' + content_digest({'block': index, 'topic': ti, 'sentence': si, 'row': row})[:20]
                speaker = aliases[row['speaker']]
                resolved = [resolve_quote({'id': rid, 'quote': units[rid]['text']}, speaker, units)
                            if rid in units else None for rid in row['evidence']]
                template, format_problem = normalize_voice_template(row['text'], row['speaker'])
                claim = {'id': cid, 'topic': topic['title'], 'section': row['section'],
                    'agenda_id': topic['agenda_id'], 'speaker': speaker, 'kind': row['kind'],
                    'discourse': row['discourse'], 'text': TOKEN.sub('La personne', template),
                    'template': template, 'evidence': [e for batch in resolved if batch for e in batch],
                    'template_format_normalized': template != row['text'],
                    'block': index, 'raw': raw_row, 'reference_ids': row['evidence']}
                # Remove duplicate mapped citations, never change the quotation.
                claim['evidence'] = [dict(id=a, quote=b) for a, b in
                    dict.fromkeys((e['id'], e['quote']) for e in claim['evidence'])]
                sentence = {'text': template, 'claim_ids': [cid], 'relation': 'none'}
                reason = 'quote_missing_ambiguous_or_wrong_voice' if not all(resolved) else format_problem
                if not reason:
                    ok, reason = grounded_claim(claim, utterances)
                    if ok:
                        reason = sentence_problem(sentence, {cid: claim}, aliases, lexicon=request.get('lexicon', []))
                if row['section'] == 'potential_decisions':
                    reason = 'potential_decision_requires_operator'
                claim['risks'] = risk_reasons(claim, sources)
                claim['status'] = 'rejected' if reason else 'candidate'
                claim['reasons'] = [reason] if reason else []
                duplicate_key = content_digest({k: claim[k] for k in
                    ('speaker', 'kind', 'discourse', 'section', 'template', 'evidence', 'agenda_id')})
                if not reason:
                    if duplicate_key in seen_prose:
                        claim.update(status='omitted', duplicate_of=seen_prose[duplicate_key],
                                     reasons=['duplicate_candidate_preserved'])
                        checkpoint['explicit_omissions'].append({'id': cid,
                            'source_ids': list(dict.fromkeys(e['id'] for e in claim['evidence'])),
                            'reason': 'duplicate_candidate_preserved'})
                    else:
                        seen_prose[duplicate_key] = cid
                checkpoint['candidates'].append(claim)
                if reason:
                    checkpoint['rejected'].append({'id': cid, 'reason': reason, 'topic': topic['title'], 'stage': 'static'})
        persist()

    candidates = {c['id']: c for c in checkpoint['candidates'] if c['status'] == 'candidate'}
    if candidates:
        grouping_schema = object_schema({'topics': {'type': 'array', 'maxItems': len(candidates),
            'items': object_schema({'title': {'type': 'string', 'minLength': 3, 'maxLength': 100},
                'agenda_id': enum([*agenda_ids, 'outside']), 'sentences': {
                    'type': 'array', 'maxItems': len(candidates), 'items': enum(candidates)}})},
            'omitted': {'type': 'array', 'maxItems': len(candidates),
                'items': object_schema({'id': enum(candidates), 'reason': TEXT})}})
        # Compact planning payload reuses prose; quotes remain in the ledger and critic.
        planning = [{'id': c['id'], 'topic': c['topic'], 'agenda_id': c['agenda_id'], 'speaker': reverse[c['speaker']],
                     'section': c['section'], 'text': c['template'],
                     'start_ms': min(sources[e['id']]['start_ms'] for e in c['evidence'])} for c in candidates.values()]
        plan = runtime.call('group-000',
            "Organise ces phrases déjà rédigées en paragraphes cohérents par sujet précis. Réutilise leurs IDs, sans réécriture. "
            "L'ordre du jour guide l'ordre. Rapproche des arguments non consécutifs portant sur le même objet, "
            "sans mélanger des contextes ou des référents différents. Un grand thème unique ne suffit pas pour fusionner. "
            "Dans chaque sujet : contexte, arguments opposés, propositions. Ordre lisible des phrases. Titres nominaux neutres, "
            "sans accusation affirmée, décision, nom ou précision ajoutés. N'omets que les répétitions exactes, "
            "éléments hors sujet ou inutilisables, avec un motif explicite. Chaque ID apparaît exactement une fois, "
            "soit dans topics.sentences, soit dans omitted. Ne supprime pas une voix minoritaire. "
            'Format : {"topics":[{"title":"Sujet précis","agenda_id":"outside","sentences":["ID de phrase"]}],'
            '"omitted":[{"id":"ID écarté","reason":"Motif bref"}]}. Utilise les IDs fournis, jamais ceux de cet exemple.',
            {'agenda': agenda_ids, 'phrases': planning}, grouping_schema, tokens=4500)
        try:
            validate_dispositions(plan, candidates)
        except ValueError:
            # Failed planning does not erase candidate prose or hide a partial plan.
            checkpoint['failed_grouping'] = plan
            plan = {'topics': [], 'omitted': []}
            for c in candidates.values():
                key = (c['block'], c['topic'], c['agenda_id'])
                found = next((t for t in plan['topics'] if t['_key'] == key), None)
                if found is None:
                    found = {'title': c['topic'], 'agenda_id': c['agenda_id'], 'sentences': [], '_key': key}
                    plan['topics'].append(found)
                found['sentences'].append(c['id'])
            for t in plan['topics']:
                del t['_key']
            checkpoint['alerts'].append({'subject': 'Regroupement', 'reason': 'grouping_failed_local_groups_preserved', 'priority': 'high'})
    else:
        plan = {'topics': [], 'omitted': []}
    agenda_order = {key: index for index, key in enumerate(agenda_ids)}
    plan['topics'].sort(key=lambda topic: agenda_order.get(topic['agenda_id'], len(agenda_order)))
    checkpoint['grouping'] = plan
    for topic in plan['topics']:
        for cid in topic['sentences']:
            candidates[cid]['initial_topic'] = candidates[cid]['topic']
            candidates[cid]['topic'] = topic['title']
    for omission in plan['omitted']:
        candidates[omission['id']]['status'] = 'omitted'
        candidates[omission['id']]['reasons'].append(omission['reason'])
    persist()

    # One grouped critic for headings and only risky claims, batched by characters.
    checks = []
    reference_lookup = {ref['id']: ref for ref in checkpoint['reference_manifest']}
    source_catalogue = {rid: {'speaker': reverse[ref['speaker']], 'quote': ref['text'],
        'start_ms': ref['start_ms'], 'end_ms': ref['end_ms']} for rid, ref in reference_lookup.items()}
    context_catalogue = {unit['id']: {'speaker': reverse[unit.get('speaker_id') or 'unattributed'],
        'text': unit['text'], 'start_ms': unit['start_ms'], 'end_ms': unit['end_ms']}
        for block in blocks for unit in [*block['previous'], *block['core']]}
    for i, topic in enumerate(plan['topics']):
        selected = [candidates[cid] for cid in topic['sentences']]
        if not selected:
            continue
        checks.append({'id': f'T{i}', 'type': 'heading', 'text': topic['title'],
                       'initial_topics': list(dict.fromkeys(c.get('initial_topic', c['topic']) for c in selected)),
                       'source_refs': list(dict.fromkeys(rid for c in selected for rid in c['reference_ids'])),
                       'context_refs': []})
        for c in selected:
            if c['risks']:
                block = blocks[c['block']]
                context_units = [*block['previous'], *block['core']]
                cited_units = {reference_lookup[rid]['unit_id'] for rid in c['reference_ids']}
                positions = [j for j, u in enumerate(context_units) if u['id'] in cited_units]
                nearby = {k for j in positions for k in range(max(0, j-2), min(len(context_units), j+3))}
                checks.append({'id': c['id'], 'type': 'important_assertion', 'text': c['template'],
                    'kind': c['kind'], 'discourse': c['discourse'], 'section': c['section'], 'risks': c['risks'],
                    'source_refs': list(dict.fromkeys(c['reference_ids'])),
                    'context_refs': [u['id'] for j, u in enumerate(context_units) if j in nearby]})
    verdicts = {}
    batches, batch = [], []
    import json
    for check in checks:
        n = len(json.dumps(critic_payload([check], source_catalogue, context_catalogue), ensure_ascii=False))
        if n > 22500:
            verdicts[check['id']] = {'verdict': 'uncertain', 'reason': 'critic_context_budget_exceeded'}
            continue
        combined = len(json.dumps(critic_payload([*batch, check], source_catalogue, context_catalogue), ensure_ascii=False))
        if batch and combined > 22500:
            batches.append(batch)
            batch = []
        batch.append(check)
    if batch:
        batches.append(batch)
    for index, batch in enumerate(batches):
        schema = object_schema({'checks': object_schema({row['id']: object_schema({
            'verdict': enum(VERDICTS), 'reason': {'type': 'string', 'minLength': 1, 'maxLength': 160}}) for row in batch})})
        result = runtime.call(f'check-{index:03d}',
            "Contrôle ciblé des titres et affirmations importantes contre les sources et leur contexte. "
            "source_refs renvoie aux citations exactes du catalogue sources ; context_refs renvoie aux tours voisins dans contexts. "
            "Les titres initiaux et les phrases sont à contrôler ; ils ne sont jamais des preuves. "
            "supported seulement si TOUS les détails, le sujet, la modalité et l'auteur sont soutenus. "
            "Une citation exacte n'est pas une preuve de fidélité. Vérifie qui agit et qui subit, négations, portée des chiffres, "
            "questions non transformées en faits, avis cité non attribué à celui qui critique, anecdote non officialisée. "
            "Aucune fonction, responsabilité ni appartenance politique ne doit être ajoutée. "
            "Les titres doivent décrire exactement le sujet des citations sans inventer une causalité ou consensus. "
            "Pour un titre, vérifie aussi la cohésion : chaque source traite du même objet précis. "
            "Un domaine très général ne justifie pas de fusionner des sujets distincts ou des contextes incompatibles. "
            "Aucun résultat de vote ou décision adoptée. Au moindre manque : not_explicit ou uncertain. "
            "Le voisinage explique un référent mais ne prouve pas un avis de la voix principale. "
            "Évalue chaque ID ; ton contrôle reste une aide machine provisoire, jamais une validation humaine. "
            'Format : {"checks":{"ID à vérifier":{"verdict":"supported","reason":"Motif bref"}}}. '
            'Remplace chaque ID par celui de items et choisis supported, contradicted, not_explicit ou uncertain.',
            critic_payload(batch, source_catalogue, context_catalogue), schema, tokens=3500)
        verdicts.update(result['checks'])
        checkpoint['targeted_checks'] = verdicts
        persist()

    topics, written = [], set()
    for i, topic in enumerate(plan['topics']):
        selected = [candidates[cid] for cid in topic['sentences']]
        if not selected:
            continue
        title_problem = identity_problem(topic['title'], selected, request.get('lexicon', []))
        heading = verdicts.get(f'T{i}', {'verdict': 'uncertain', 'reason': 'heading_not_checked'})
        if title_problem or heading['verdict'] != 'supported':
            for c in selected:
                c['status'] = 'rejected'
                c['reasons'].append(title_problem or heading['reason'])
            checkpoint['rejected'].append({'topic': topic['title'], 'ids': topic['sentences'],
                'reason': title_problem or heading['reason'], 'stage': 'heading'})
            continue
        kept = []
        for c in selected:
            check = verdicts.get(c['id'])
            if check and check['verdict'] != 'supported':
                c['status'] = 'rejected'
                c['reasons'].append(check['reason'])
                checkpoint['rejected'].append({'id': c['id'], 'topic': topic['title'], 'reason': check['reason'], 'stage': 'targeted'})
                continue
            c['status'] = 'written'
            c['machine_verdict'] = 'targeted_machine_supported' if check else 'static_checks_only_semantics_unconfirmed'
            kept.append(c)
        if kept:
            # Keep long topics below the existing document schema limit, all parts retained.
            groups, part, count = [], [], 0
            for c in kept:
                if part and count + len(c['template']) > 8000:
                    groups.append(part)
                    part, count = [], 0
                part.append(c)
                count += len(c['template']) + 1
            if part:
                groups.append(part)
            for j, group in enumerate(groups):
                topics.append({'title': topic['title'] + (' (suite)' if j else ''), 'agenda_id': topic['agenda_id'],
                    'claims': [c['id'] for c in group], 'sentences': [
                        {'text': c['template'], 'voice_bindings': {a: aliases[a] for a in TOKEN.findall(c['template'])},
                         'claim_ids': [c['id']], 'relation': 'none', 'machine_verdict': c['machine_verdict']}
                        for c in group]})
                written.update(c['id'] for c in group)

    # Group operator alerts by topic. Full candidate/source inventories stay consultable.
    subjects = list(dict.fromkeys([c['topic'] for c in checkpoint['candidates']] + [t['title'] for t in plan['topics']]))
    for subject in subjects:
        rejected = [r for r in checkpoint['rejected'] if r.get('topic') == subject]
        uncertain = [c['id'] for c in checkpoint['candidates'] if c['topic'] == subject and
                     c['id'] in written and 'uncertain_source_attribution' in c['risks']]
        if rejected or uncertain:
            checkpoint['alerts'].append({'subject': subject, 'priority': 'high' if rejected else 'medium',
                'reason': 'rejected_or_uncertain_information', 'rejected': rejected, 'uncertain_ids': uncertain})
    inventory = source_inventory(utterances, checkpoint['candidates'], written)
    for source in inventory:
        source['generation_omission_reasons'] = list(dict.fromkeys(
            omission['reason'] for omission in checkpoint['explicit_omissions'] if source['id'] in omission['source_ids']))
    uncited = sum(r['status'] == 'not_cited_in_document' for r in inventory)
    if uncited:
        checkpoint['alerts'].append({'subject': 'Inventaire des omissions', 'priority': 'medium',
            'reason': 'uncited_sources_preserved', 'count': uncited})
    checkpoint['inventory'] = inventory
    checkpoint['written_ids'] = sorted(written)
    written_agenda = {topic['agenda_id'] for topic in topics}
    for aid, title in agenda_ids.items():
        if aid not in written_agenda:
            checkpoint['alerts'].append({'subject': title, 'priority': 'medium',
                'reason': 'agenda_item_not_represented_in_document', 'agenda_id': aid})
    checkpoint['wall_seconds'] = time.perf_counter()-started
    persist()
    public_claims = [{k: c[k] for k in ('id', 'topic', 'speaker', 'kind', 'discourse', 'text', 'evidence')}
                     for c in checkpoint['candidates'] if c['id'] in written]
    return {'strategy': 'contextual-topic-paragraphs-v1', 'claims': public_claims, 'topics': topics,
        'diagnostics': {'experimental_strategy': VERSION, 'summary_length': request.get('summary_length', 'standard'),
            'rejected_claims': sum(c['status'] == 'rejected' for c in checkpoint['candidates']),
            'rejection_events': len(checkpoint['rejected']),
            'omitted_claims': sum(c['status'] == 'omitted' for c in checkpoint['candidates']),
            'topics_not_written': [r['topic'] for r in checkpoint['rejected'] if r['stage'] == 'heading'],
            'operator_alerts': len(checkpoint['alerts']), 'input_rows': len(utterances),
            'all_source_text_preserved': True, 'semantic_quality_validated': False},
        'ledger': checkpoint}
