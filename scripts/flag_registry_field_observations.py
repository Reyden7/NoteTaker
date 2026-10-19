"""Record development doubts after real prose, without approval or semantic scores."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.infrastructure.atomic import atomic_json
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService
from notetaker.domain.information_registry import coverage, source_fingerprint

work = ROOT / 'output/information-registry/field-670'
draft = json.loads((work / 'draft.json').read_text(encoding='utf-8'))
store = SessionStore(work / 'data')
sid = '0ce77b44-c8a0-482f-be0d-ef5a68b80aa2'
service = RegistryService(store)
before = source_fingerprint(store.get(sid))
reviews = [tuple(r) for r in store.db.execute('SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision', (sid,))]
observations = []
for point in draft['points']:
    if point['title'].startswith("L'efficacité ou l'existence de systèmes de sélection"):
        reason = "Regroupement douteux : ces extraits parlent d'emploi étudiant, de salaire ou de prélèvement, alors que le sujet annoncé concerne la sélection."
    elif point['title'].startswith("Évaluation de l'ampleur du mouvement"):
        reason = "Sujet et contenu semblent incompatibles : la question rédigée ne renseigne pas l'ampleur du mouvement ni ses chiffres."
    elif point['title'].startswith('Nature des moyens de changement'):
        reason = "Articulation douteuse : la rédaction relie une formule générale sur la révolution à un premier emploi personnel. Vérifier ce lien et le sens du propos."
    elif point['title'] == 'À classer':
        reason = "Objet de la question insuffisamment déterminé : la rédaction décrit une affirmation sans préciser son contenu."
    else:
        continue
    for claim in point['claims']:
        active = service.latest(sid)
        entry = next(e for e in active['content']['entries'] if e['id'] == claim['id'])
        observation = {'information_id': entry['id'], 'subject': entry['subject'],
            'content': entry['content'], 'evidence': entry['evidence'], 'reason': reason,
            'human_annotation': False, 'disposition': 'requires_verification_not_excluded_or_deleted'}
        if not entry.get('human_lock'):
            service.change(sid, active['id'], entry['id'], 'reopen',
                actor='Audit de développement automatisé — non humain',
                reason=reason + ' Doute du développement, sans approbation humaine.')
        observations.append(observation)
active = service.latest(sid)
report = {'scope': 'development-agent qualitative reading after real prose; not a human benchmark',
    'human_annotation': False, 'semantic_accuracy_rate': None, 'human_review_created': False,
    'observations': observations, 'current_coverage': coverage(active['content']),
    'comparison_draft_retained': store.get(sid)['draft']['content'] == draft,
    'comparison_draft_registry_revision_id': draft['information_registry']['revision_id'],
    'current_registry_revision_id': active['id'],
    'comparison_draft_obsolete_after_doubts': draft['information_registry']['revision_id'] != active['id'],
    'source_rows_unchanged': before == source_fingerprint(store.get(sid)),
    'historical_reviews_unchanged': reviews == [tuple(r) for r in store.db.execute(
        'SELECT id,review_json FROM draft_minutes WHERE session_id=? ORDER BY revision', (sid,))]}
assert report['comparison_draft_retained'] and report['source_rows_unchanged'] and report['historical_reviews_unchanged']
try:
    store._check_registry_reference(sid, draft)
except ValueError as error:
    assert str(error) == 'REGISTRY_DOCUMENT_REFERENCE_INVALID'
    report['obsolete_draft_reference_preflight_refused'] = True
else:
    raise AssertionError('Obsolete comparison draft unexpectedly accepted')
atomic_json(ROOT / 'docs/evidence/information-registry-post-writing-observations.json', report)
atomic_json(work / 'post-writing-observations.json', report)
store.close()
print(json.dumps({key: value for key, value in report.items() if key != 'observations'}, ensure_ascii=True, indent=2))
