"""Report actual calls/CPU separately from unavailable independent quality scores."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.domain.minutes import content_digest
from notetaker.domain.information_registry import coverage
from notetaker.domain.summary import PROFILES
from notetaker.services.pipeline import assemble_summary
from notetaker.services.storage import SessionStore

p = argparse.ArgumentParser()
p.add_argument('--legacy', type=Path, required=True)
p.add_argument('--direct', type=Path, required=True)
p.add_argument('--prepare', type=Path)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
read = lambda path: json.loads(path.read_text(encoding='utf-8'))
old, new = read(args.legacy/'report.json'), read(args.direct/'cold-report.json')
assert old['status'] == new['status'] == 'completed'
old_response, old_request = read(args.legacy/'stdout.json'), read(args.legacy/'request.json')
run_id = new['service_result']['run_id']
data = args.direct/'data'
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
artifact = data/'sessions'/sid/'direct-experiments'/run_id/'result.json'
record = read(artifact)
assert old_request['utterances'] == record['input']['utterances']
assert old_request['registry']['speakers'] == record['input']['speakers']
assert old_request.get('lexicon', []) == record['input']['lexicon']
assert old_response['python_network_attempts'] == 0
assert new['python_network_attempts'] == 0
store = SessionStore(data)
state = store.get(sid)
new_draft = assemble_summary(state, record['result'])
if new['service_result']['draft_saved']:
    assert state['draft']['content']['experimental_summary']['run_id'] == run_id
    new_draft = state['draft']['content']
old_draft = assemble_summary(state, old_response['result'])
store.close()
phases = defaultdict(lambda: {'fresh_calls': 0, 'cached_calls': 0, 'wall_seconds': 0., 'cpu_seconds': 0.})
for call in new['profile']['calls']:
    phase = phases[call['stage']]
    phase['cached_calls' if call['cache_hit'] else 'fresh_calls'] += 1
    phase['wall_seconds'] += call['wall_seconds']
    phase['cpu_seconds'] += sum((call.get('cpu') or {}).values())
old_phases = defaultdict(lambda: {'calls': 0, 'wall_seconds': 0., 'cpu_seconds': None})
for path in (args.legacy/'inference').glob('*.timing.json'):
    stage = next((key for key in ('heading', 'check', 'write') if '-'+key+'-' in path.name), 'other')
    old_phases[stage]['calls'] += 1
    old_phases[stage]['wall_seconds'] += read(path)['wall_seconds']
cpu = lambda values: values.get('user_seconds', 0) + values.get('kernel_seconds', 0)
inventory = record['result']['ledger']['inventory']
report = {'scope': 'same 670 utterances, stored voices and lexicon; sequential native CPU; no new ASR/diarization',
    'input_rows_sha256': content_digest(old_request['utterances']), 'input_rows': len(inventory),
    'legacy': {'wall_seconds': old['wall_seconds'], 'cpu_seconds': cpu(old['cpu']),
        'qwen_calls': old['qwen_calls_completed'], 'phases': dict(old_phases),
        'paragraphs': len(old_draft['points']), 'registry_before': coverage(old_request['registry']),
        'registry_after': coverage(old_response['result']['registry']),
        'subjects_written': [point['title'] for point in old_draft['points']],
        'diagnostics': old_response['result']['diagnostics'],
        'preparation_and_previous_verification_excluded': True},
    'direct': {'wall_seconds': new['worker_wall_seconds'], 'service_wall_seconds': new['wall_seconds'],
        'cpu_seconds': cpu(new['worker_cpu']), 'qwen_calls': new['profile']['fresh_calls'],
        'phases': dict(phases), 'paragraphs': new['paragraphs'], 'operator_alerts': new['operator_alerts'],
        'candidates': new['candidates'], 'sources_not_cited': new['sources_not_cited'],
        'subjects_written': [point['title'] for point in new_draft['points']],
        'source_text_outside_quotes_rows': sum(bool(row.get('uncited_text')) for row in inventory),
        'diagnostics': record['result']['diagnostics']},
    'human_reference': {'status': 'awaiting user annotation', 'excerpts_prepared': 12, 'human_annotations': 0},
    'quality_scores': {key: None for key in ('theme_coverage', 'grouping', 'fidelity', 'important_omissions', 'attribution', 'writing')},
    'source_preservation': {key: new[key] for key in ('source_db_unchanged', 'copied_rows_unchanged', 'registry_unchanged', 'draft_history_preserved')},
    'model_sha256': new['profile']['runtime']['model_sha256'],
    'runtime_sha256': new['profile']['runtime']['binary_sha256'],
    'decoding': {'legacy': {'temperature': 0, 'seed_requested': 42},
                 'direct_runtime_arguments': new['profile']['runtime']['arguments'],
                 'same_decoding_parameters': False},
    'direct_output_budget': {'length': record['result']['diagnostics']['summary_length'],
        'maximum_sentences_per_context': PROFILES[record['result']['diagnostics']['summary_length']]['sentences'],
        'contexts': len(record['result']['ledger']['context_inventory']),
        'all_input_rows_preserved': True, 'semantic_coverage_measured': False},
    'cold_definition': 'new processes; empty application response caches; Windows disk cache not flushed',
    'host_isolated_for_benchmark': False, 'commercial_validation': False, 'clean_offline_windows_validation': False}
if args.prepare and (args.prepare/'report.json').exists():
    prep = read(args.prepare/'report.json')
    report['legacy_fresh_preparation'] = {key: prep.get(key) for key in ('status', 'wall_seconds', 'cpu', 'qwen_calls_completed')}
    if prep['status'] == 'completed':
        result = read(args.prepare/'stdout.json')['result']['registry']
        report['legacy_fresh_preparation']['coverage'] = coverage(result)
        report['legacy_fresh_preparation']['writing_without_human_work_available'] = coverage(result)['eligible_information_entries'] > 0
resume_path = args.direct/'resume-profile.json'
if resume_path.exists():
    warm = read(resume_path)
    report['resume'] = {'fresh_calls': warm['fresh_calls'], 'cached_calls': warm['cached_calls'],
                        'native_calls_wall_seconds': sum(c['wall_seconds'] for c in warm['calls'])}
lines = ['# Comparaison expérimentale 0.2.4 / 0.2.5 — documents non validés', '',
    '**Annoter les extraits indépendants avant de lire les textes comparés pour éviter de biaiser la référence.**', '',
    'Même transcription figée de 670 passages, mêmes noms sauvegardés et lexique. '
    'Aucun nouveau traitement Whisper/sherpa. Les appels Qwen des deux pipelines sont séquentiels. '
    'Le poste a également servi au développement ; ces temps ne sont pas une garantie commerciale.', '',
    'Les paramètres de décodage diffèrent : 0.2.4 utilise temperature=0 ; le laboratoire utilise '
    'les valeurs Instruct-2507 conseillées dans sa fiche locale (0,7 / top-p 0,8 / top-k 20 / min-p 0). '
    'Les mesures comparent ces configurations complètes et ne permettent pas d’isoler le seul effet de l’architecture.', '',
    'La sortie directe est bornée par le profil de longueur pour chaque contexte ; tous les passages restent en entrée. '
    'Cette compression peut omettre des informations. Une durée plus courte avec moins de contenu restitué '
    'ne démontre pas une amélioration du produit : la couverture et la fidélité attendent la référence humaine.', '',
    '| Mesure | 0.2.4 : rédaction seule | 0.2.5 : chaîne directe complète |',
    '|---|---:|---:|',
    f"| Temps écoulé worker | {old['wall_seconds']:.2f} s | {new['worker_wall_seconds']:.2f} s |",
    f"| CPU utilisateur + noyau de l’arbre | {cpu(old['cpu']):.2f} s | {cpu(new['worker_cpu']):.2f} s |",
    f"| Appels Qwen neufs | {old['qwen_calls_completed']} | {new['profile']['fresh_calls']} |",
    f"| Paragraphes conservés | {len(old_draft['points'])} | {new['paragraphs']} |",
    f"| Charge affichée, unités différentes | {coverage(old_request['registry'])['to_verify_information_entries']} fiches à vérifier | {new['operator_alerts']} alertes regroupées |", '',
    '0.2.4 utilise le registre antérieurement contrôlé : préparation et travail humain exclus. '
    'La différence de nombre d’alertes ne mesure pas une réduction du temps humain. '
    'La présence d’une citation ou le nombre de paragraphes ne mesure pas la fidélité ni la couverture des thèmes.', '',
    'À froid applicatif : réponses absentes et processus neufs ; cache disque Windows non purgé. '
    'Le CPU agrège quatre threads, il peut dépasser le temps écoulé.', '', '## Étapes 0.2.5', '',
    '| Étape | Appels neufs | Temps écoulé natif | CPU natif |', '|---|---:|---:|---:|']
for stage, stats in phases.items():
    lines.append(f"| {stage} | {stats['fresh_calls']} | {stats['wall_seconds']:.2f} s | {stats['cpu_seconds']:.2f} s |")
lines += ['', 'Le CPU par sous-étape 0.2.4 n’est pas disponible avec ce worker conservé ; '
          'son CPU total est mesuré par Job Windows. Ses durées par appel sont dans le JSON.', '',
          '## Référence indépendante et limites', '',
          'Douze contextes de 40 secondes sont préparés, sans réponse Qwen. Aucune annotation humaine reçue. '
          '**Fidélité, regroupement, erreurs d’attribution, qualité rédactionnelle et informations importantes omises : non mesurés.** '
          'L’échantillon ne suffit pas à évaluer les omissions de toute la réunion.', '',
          f"Inventaire direct : {len(inventory)} passages intacts ; {new['sources_not_cited']} non cités dans le document. "
          'Le texte hors citation des passages partiellement cités est également conservé. '
          'Les sorties et les refus restent consultables dans l’onglet expérimental.', '']
if 'legacy_fresh_preparation' in report:
    lines += ['## Préparation neuve 0.2.4 mesurée séparément', '',
              '```json', json.dumps(report['legacy_fresh_preparation'], ensure_ascii=False, indent=2), '```', '']
for label, draft in [('Rédaction 0.2.4 — non validée', old_draft), ('Synthèse directe 0.2.5 — non validée', new_draft)]:
    lines += ['## '+label, '']
    for point in draft['points']:
        lines += ['### '+point['title'], '', point['summary'], '', 'Sources : '+', '.join(point['sources']), '']
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text('\n'.join(lines), encoding='utf-8')
atomic_json(args.output.with_suffix('.json'), report)
atomic_json(ROOT/'docs/evidence/direct-summary-real-comparison.json', report)
print(json.dumps({'report': str(args.output), 'legacy_calls': old['qwen_calls_completed'],
                  'direct_calls': new['profile']['fresh_calls'], 'quality_validated': False}))
