"""A focused real-model test of indirect-speech reformulation on field excerpts."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.engines.hierarchical_summary import call_json, object_schema
from notetaker.infrastructure.atomic import atomic_json
work = ROOT / 'output/quality-02'
request = json.loads((work / 'paraphrase-probe/request.json').read_text(encoding='utf-8'))
claims = json.loads((work / 'paraphrase-probe/response.json').read_text(encoding='utf-8'))['result']['claims']
folder = work / 'rephrase-study'
folder.mkdir(exist_ok=True)
request['workspace'] = str(folder)
schema = object_schema({'reformulations': {'type': 'array', 'minItems': len(claims), 'maxItems': len(claims), 'items': object_schema({
    'id': {'type': 'string', 'enum': [c['id'] for c in claims]}, 'text': {'type': 'string', 'minLength': 10, 'maxLength': 240}})}})
result = call_json(request, 'indirect-speech',
    "Réécris les informations au style INDIRECT d'un compte rendu professionnel, avec tes propres mots, en une phrase de 15 à 30 mots. "
    "Aucun je, nous, vous, aucun guillemet. Ne copie pas la citation : explique l'idée avec une autre construction. "
    "Exemple : 'Je suis contre ces travaux parce que je ne pourrai plus accéder à la bibliothèque.' devient "
    "'Le projet de travaux suscite une opposition liée au maintien de l’accès à la bibliothèque.' "
    "Garde strictement les faits, dates, réserves et négations de chaque information, sans ajouter de cause, intention ou résultat.",
    [{'id': c['id'], 'information_a_reformuler': c['text']} for c in claims], schema, tokens=700)
atomic_json(folder / 'comparison.json', {'before': claims, 'after': result})
print(json.dumps(result, ensure_ascii=True))
