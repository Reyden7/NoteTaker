"""Prepare isolated diagnostic inputs. Never write to a NoteTaker data store.

Corrections below are proposals based on the supplied narrative reference.
This session cannot audition audio; they MUST NOT be labelled audio verified.
"""
import hashlib
import json
import re
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/diagnostic-parcoursup/2026-10-20-01'
REFERENCE = Path('C:/Users/quent/Desktop/1) Presentation de louise Montangon.txt')
REQUEST = ROOT / 'output/information-registry/field-670/write.request.json'
ARTIFACT = ROOT / 'output/direct-summary/direct-cold-05/data/sessions/0ce77b44-c8a0-482f-be0d-ef5a68b80aa2/direct-experiments/7f0ffeac-46f8-4f3e-b600-4fa332a14354/result.json'
CORE = (1051960, 1237580)
WIDE = (960000, 1240016)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))


def selected(rows, bounds):
    return [row for row in rows if row['end_ms'] > bounds[0] and row['start_ms'] < bounds[1]]


def stamp(ms):
    return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


def correct(row, speakers):
    """Draft spelling and attribution proposals, explicitly awaiting audio review."""
    text = re.sub(r'parcours suque|parcours-tup', 'Parcoursup', row['text'], flags=re.I)
    label = speakers.get(row['speaker_id'], 'Intervenant non attribué')
    replacements = {
        'directory-59715eee-f75f-4bff-8cf5-b347e9971583': 'Louise Montangon',
        'directory-caa9d17a-1005-4c37-be53-21237ced0202': 'Sonia (présentatrice, nom non précisé)',
        'speaker_2': 'Manès Nadel',
        'speaker_4': 'Bruno (nom de la référence « Jodir » à confirmer)',
    }
    label = replacements.get(row['speaker_id'], label)
    # These fragments continue an adjacent turn, but are not verified by hearing.
    if row['id'] in {'s555-1', 's556-0'}:
        label = 'Louise Montangon'
    if row['id'] in {'s562-1', 's563-0', 's564-0', 's565-0', 's566-0', 's567-0'}:
        label = 'Manès Nadel'
    # Do not reconstruct garbled clauses, annual figures, implied intentions,
    # or move the start of the historical-selection interruption by guessing.
    return {**row, 'speaker_label': label, 'text': text}


def main():
    request = read(REQUEST)
    original = request['utterances']
    speakers = request['registry']['speakers']
    audio = Path(json.loads(original[0]['source_json'])['normalized_audio'])
    original_input = [{k: row[k] for k in ('id', 'speaker_id', 'start_ms', 'end_ms', 'text')} |
                      {'speaker_label': speakers.get(row['speaker_id'], 'Intervenant non attribué')}
                      for row in original]
    corrected = [correct(row, speakers) for row in original_input]
    inputs = {'A-original': selected(original_input, CORE),
              'B-correction-proposee': selected(corrected, CORE),
              'C-correction-contexte-large': selected(corrected, WIDE)}
    assert [r['id'] for r in inputs['A-original']] == [r['id'] for r in inputs['B-correction-proposee']]
    assert selected(inputs['C-correction-contexte-large'], CORE) == inputs['B-correction-proposee']
    baseline_files = [REQUEST, ARTIFACT, REFERENCE,
        ROOT/'output/direct-summary/input-024.sqlite3',
        ROOT/'dist/direct-summary-catalogue-final/NoteTaker/NoteTaker.exe',
        ROOT/'dist/direct-summary-catalogue-final/NoteTaker/NoteTaker-worker.exe']
    baseline_files.extend(p for p in (ROOT/'src').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    manifest = {'human_reference': str(REFERENCE), 'core_ms': CORE, 'wide_ms': WIDE,
        'source_audio': str(audio), 'audio_sha256': sha(audio),
        'protected_files': {str(p): sha(p) for p in baseline_files},
        'source_rows': len(original), 'case_rows': {k: len(v) for k,v in inputs.items()},
        'correction_status': 'proposed_from_human_narrative_NOT_audio_verified',
        'audio_listening_available_to_agent': False,
        'audio_review_completed_by_human': False,
        'scope_warning': 'The frozen 670 rows end at 20:37.580. Later licence failure/mental health discussion in reference section 12 is outside this corpus.',
        'original_condition': 'frozen 670-row comparison transcript with stored diarization/manual labels; not claimed to be pristine raw Whisper output'}
    write_new(OUT/'manifest.json', manifest)
    for name, rows in inputs.items():
        write_new(OUT/'inputs'/f'{name}.json', {'focus_start_ms': CORE[0], 'focus_end_ms': CORE[1], 'passages': rows})
    changes = []
    old = {r['id']:r for r in original_input}
    for row in inputs['C-correction-contexte-large']:
        fields = {k: {'before': old[row['id']][k], 'proposed': row[k]} for k in ('text','speaker_label') if old[row['id']][k] != row[k]}
        if fields: changes.append({'id': row['id'], 'start_ms': row['start_ms'], 'changes': fields,
            'basis': 'reference sections 10-12 / obvious ASR spelling; pending audio review'})
    write_new(OUT/'corrections-proposees.json', changes)
    lines = ['# Transcription proposée — vérification audio requise', '',
        '**Cette proposition utilise la référence narrative et les textes existants. Aucun contrôle auditif effectué par l’agent.**',
        'La graphie « Bruno Jodir » et le début de son interruption restent à confirmer. Les phrases mal reconnues sont conservées, sans inventer leur réparation.', '',
        'Audio : [extrait focal](extrait-focal-17m32-20m38.wav)', '']
    for row in inputs['B-correction-proposee']:
        lines += [f"- **{stamp(row['start_ms'])} · {row['id']} · {row['speaker_label']}** : {row['text']}"]
    lines += ['', '## Points à vérifier particulièrement', '',
        '- 17:41 : « pourquoi vous le remplacer » signifie-t-il « par quoi vous le remplacez » ?',
        '- 18:05–18:45 : formulation des chiffres et moment exact du changement Manès / Bruno (premier arrivé / tirage au sort).',
        '- 19:08 : graphie de Parcoursup ; 19:23 : « sectorisation » ou autre terme ?',
        '- 19:54 : fin de phrase mal reconnue (« d’un apportement »), ne pas reconstruire sans écoute.',
        '- 20:27–20:38 : attribution de la fin de réponse sur les notes à Manès, graphie du mot mal reconnu « Néja ».']
    write_new(OUT/'transcription-corrigee-A-VERIFIER.md', '\n'.join(lines))
    with wave.open(str(audio),'rb') as src:
        rate = src.getframerate()
        for name, bounds in [('extrait-focal-17m32-20m38.wav', CORE), ('contexte-large-16m00-20m40.wav', WIDE)]:
            src.setpos(round(bounds[0]*rate/1000))
            frames = src.readframes(round((bounds[1]-bounds[0])*rate/1000))
            path = OUT/name
            assert not path.exists()
            with wave.open(str(path),'wb') as dst:
                dst.setparams(src.getparams()); dst.writeframes(frames)
    print(json.dumps({'output': str(OUT), 'case_rows': manifest['case_rows'], 'manual_audio_review': False}))


if __name__ == '__main__':
    main()
