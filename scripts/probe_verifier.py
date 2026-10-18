"""Real CPU verifier regression: a global budget must not become a roof budget."""
import json
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.engines.hierarchical_summary import call_json, object_schema, VERIFY_INSTRUCTION
from notetaker.infrastructure.paths import ModelPaths
from notetaker.infrastructure.atomic import atomic_json

parser = argparse.ArgumentParser()
parser.add_argument('--field', action='store_true')
parser.add_argument('--model', type=Path)
args = parser.parse_args()
models = ModelPaths()
workspace = ROOT / 'output/quality-02/verifier-study'
if args.model:
    workspace = workspace / args.model.stem
workspace.mkdir(parents=True, exist_ok=True)
request = {'binary': str(models.llama), 'model': str(args.model.resolve() if args.model else models.llm), 'workspace': str(workspace)}
source = 'Les travaux de la bibliothèque sont estimés à vingt mille euros. Je propose de commencer par réparer la toiture.'
items = [
    {'id': 'wrong-scope', 'kind': 'proposal', 'speaker': 'a',
     'claim': 'Les travaux de réparation de la toiture de la bibliothèque sont estimés à vingt mille euros.',
     'sources': [{'id': 's0', 'speaker': 'a', 'text': source}]},
    {'id': 'faithful', 'kind': 'proposal', 'speaker': 'a',
     'claim': 'Une priorité donnée à la réparation de la toiture est proposée pour les travaux de la bibliothèque.',
     'sources': [{'id': 's0', 'speaker': 'a', 'text': source}]},
]
if args.field:
    work = ROOT / 'output/quality-02'
    from notetaker.engines.hierarchical_summary import source_units, coherent_blocks, resolve_evidence, grounded_claim
    # These regression claims belong to the first rejected run, whose IDs must
    # never be matched against a later realignment of the same recording.
    rows = json.loads((work / 'summary-request.json').read_text(encoding='utf-8'))['utterances']
    units = source_units(rows); by_id = {u['id']: u for u in units}; blocks = list(coherent_blocks(units)); claims = []
    for p in sorted((work / 'summary').glob('block-*.result.json')):
        index = int(p.stem.split('-')[1].split('.')[0])
        for c in json.loads(p.read_text(encoding='utf-8'))['claims']:
            c = resolve_evidence(c, [by_id[i] for i in {u['id'] for u in blocks[index]}])
            if c and grounded_claim(c, rows, False)[0]:
                claims.append(c)
    rewritten = json.loads((work / 'summary/rewrite-000.result.json').read_text(encoding='utf-8'))['reformulations']
    items = [{'id': c['id'], 'kind': c['kind'], 'speaker': claims[int(c['id'][1:])]['speaker'], 'claim': c['text'],
              'sources': [{'text': e['quote']} for e in claims[int(c['id'][1:])]['evidence']]} for c in rewritten]
schema = object_schema({'checks': {'type': 'array', 'minItems': len(items), 'maxItems': len(items), 'items': object_schema({
    'id': {'type': 'string', 'enum': [i['id'] for i in items]},
    'verdict': {'type': 'string', 'enum': ['supported', 'contradicted', 'not_explicit', 'mixed_speakers', 'vote_result', 'uncertain']}})}})
instruction = VERIFY_INSTRUCTION
result = call_json(request, 'strict-field' if args.field else 'strict-scope', instruction, items, schema, tokens=500)
mapping = {c['id']: c['verdict'] for c in result['checks']}
expected = ({'c0': ['not_explicit', 'uncertain'], 'c1': ['supported'],
             'c2': ['not_explicit', 'uncertain'], 'c3': ['not_explicit', 'uncertain']} if args.field
            else {'wrong-scope': ['not_explicit'], 'faithful': ['supported']})
proof = {'real_cpu_result': result, 'expected': expected,
         'scope_regression_passed': all(mapping.get(i) in values for i, values in expected.items()),
         'not_a_field_accuracy_measure': True}
if args.field:
    proof['oracle_note'] = ('Developer text-consistency cases, not human audio annotations. The initial c3 expectation was corrected: '
        'a recollection of adolescence does not establish a statement made during adolescence; uncertainty must prevent acceptance.')
name = 'quality-02-verifier' + ('-field' if args.field else '') + ('-instruct-candidate' if args.model else '') + '.json'
existing = ROOT / 'docs/evidence' / name
if args.field and existing.exists():
    old = json.loads(existing.read_text(encoding='utf-8'))
    archived = existing.with_stem(existing.stem + '-initial-oracle')
    if 'oracle_note' not in old and not archived.exists():
        atomic_json(archived, old)
atomic_json(ROOT / 'docs/evidence' / name, proof)
print(json.dumps(proof, ensure_ascii=True, indent=2))
