"""Prepare unlabelled, model-blind excerpts for an independent human reference."""
import argparse
import json
import sys
import wave
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from notetaker.infrastructure.atomic import atomic_json, sha256_file
from notetaker.domain.minutes import content_digest

p = argparse.ArgumentParser()
p.add_argument('--request', type=Path, required=True)
p.add_argument('--audio', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
request = json.loads(args.request.read_text(encoding='utf-8'))
utterances = request['utterances']
voices = list(dict.fromkeys(u.get('speaker_id') or 'unattributed' for u in utterances))
end = max(u['end_ms'] for u in utterances)
pack = {'source_rows_sha256': content_digest(utterances), 'audio_sha256': sha256_file(args.audio),
        'selection': '12 deterministic 40-second contexts, evenly spaced; no model outputs displayed',
        'human_reference_completed': False, 'reviewer': '', 'excerpts': []}
lines = ['# Référence humaine indépendante — NoteTaker', '',
    'Aucun texte généré par Qwen ne figure dans ce dossier. Écoutez chaque WAV, puis renseignez les champs du fichier annotations.json.', '',
    'Les libellés Voix N sont des repères techniques issus de la transcription, pas des identités validées. '
    'Corrigez les erreurs de transcription et d’attribution en vous appuyant sur l’audio. '
    'Si une identité ou un propos ne peut pas être établi, inscrivez « inconnu / incertain ».', '',
    'Pour chaque extrait : sujet(s), faits importants avec texte exact et horaires, auteur vérifié ou inconnu, '
    'nature du propos, question/réponse, avis rapporté, opposition, proposition, éventuelle décision explicite. '
    'Indiquez le contexte manquant et les ambiguïtés. Ne déduisez aucun vote.', '',
    'Renseignez reviewer et human_reference_completed uniquement après cette vérification réelle. '
    'Les 12 extraits ne suffisent pas à mesurer la couverture de toutes les 20 minutes ; '
    'une évaluation des omissions globales demande une annotation du reste de l’enregistrement.', '']
with wave.open(str(args.audio), 'rb') as audio:
    rate = audio.getframerate()
    for i in range(12):
        start = round(max(0, end-40000) * i / 11)
        stop = min(end, start+40000)
        name = f'extrait-{i+1:02d}.wav'
        audio.setpos(round(start*rate/1000))
        samples = audio.readframes(round((stop-start)*rate/1000))
        with wave.open(str(out/name), 'wb') as target:
            target.setparams(audio.getparams())
            target.writeframes(samples)
        rows = [u for u in utterances if u['start_ms'] < stop and u['end_ms'] > start]
        pack['excerpts'].append({'id': f'E{i+1:02d}', 'audio': name, 'start_ms': start, 'end_ms': stop,
            'source_ids': [u['id'] for u in rows], 'subjects': [], 'important_information': [],
            'verified_speakers': [], 'relations': [], 'uncertainties': [], 'human_checked': False})
        lines += [f'## E{i+1:02d} — {start/60000:.2f} à {stop/60000:.2f} minutes', '', f'Audio : [{name}]({name})', '']
        for u in rows:
            alias = f"Voix {voices.index(u.get('speaker_id') or 'unattributed')+1}"
            lines.append(f"- {u['start_ms']/1000:.3f}–{u['end_ms']/1000:.3f} s · {alias} · {u['id']} : {u['text']}")
        lines += ['', 'Sujet(s) :', '', 'Informations importantes et auteur vérifié :', '', 'Questions / avis cités / désaccords / ambiguïtés :', '']
atomic_json(out/'annotations.json', pack)
(out/'A_LIRE_ET_ANNOTER.md').write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'excerpts': len(pack['excerpts']), 'output': str(out), 'human_annotations': 0}))
