"""Readable technical comparison, explicitly distinct from a human quality assessment."""
import json
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from notetaker.services.storage import SessionStore
from notetaker.services.information_registry import RegistryService
from notetaker.domain.information_registry import coverage
from notetaker.domain.information_registry import admissible

work = ROOT / 'output/information-registry/field-670'
report = json.loads((work / 'comparison.json').read_text(encoding='utf-8'))
assert report['status'] in {'passed', 'failed'}, 'Actual comparison is still running'
store = SessionStore(work / 'data')
record = RegistryService(store).latest('0ce77b44-c8a0-482f-be0d-ef5a68b80aa2')
registry = json.loads((work / 'registry.json').read_text(encoding='utf-8'))
post_path = work / 'post-writing-observations.json'
post = json.loads(post_path.read_text(encoding='utf-8')) if post_path.exists() else None
baseline = json.loads((ROOT / 'output/summary-paragraphs/38a6b4c9d8704b669d4acd8a49c2ff8e/standard-4min/draft.json').read_text(encoding='utf-8'))
counts = coverage(registry)
lines = ['# NoteTaker 0.2.3 / 0.2.4 — comparaison technique', '',
    '**Document de développement, non validé humainement. Aucun procès-verbal approuvé.**', '',
    '## Conditions réelles', '',
    'Même instantané de 670 passages du débat français, sans nouveau calcul Whisper ou sherpa. '
    'Qwen local CPU ; copie SQLite isolée. Les noms et les horodatages initiaux sont conservés. '
    'Les réponses natives réutilisées ont une identité de prompt, schéma et modèle vérifiée ; '
    'ces durées ne constituent pas un benchmark à froid. Le code a évolué pendant la préparation.', '',
    'Les requêtes worker conservent tout l’instantané pour les contrôles, mais les prompts '
    'natifs d’extraction reçoivent six unités bornées. Le plan parcourt des blocs de sources '
    'puis consolide leurs intitulés ; il ne voit pas simultanément toute la transcription.', '',
    f"Résultat de rédaction : **{report['status']}**. Temps de la dernière passe : "
    f"{report['wall_seconds']} s ; nouveaux appels natifs : {report['native_calls_executed_this_run']}.", '',
    'La vérification approfondie est partielle et demandée par fiche. Les candidats en attente '
    'sont exclus de la rédaction automatique. Ce registre partiellement vérifié ne permet pas '
    'une comparaison équitable de la complétude finale des deux textes.', '',
    'Les fiches admissibles de cette copie proviennent de contrôles natifs antérieurs conservés '
    'pendant les essais et du contrôle supplémentaire avec le worker compilé. Sur une séance '
    'nouvelle, la préparation conserve les nouvelles propositions en attente ; demander un '
    'contrôle ou effectuer une vérification humaine explicite avant rédaction.', '',
    '## Comptes techniques — aucune mesure de couverture sémantique', '',
    '| Élément | 0.2.3 archivé | 0.2.4 registre courant |', '|---|---:|---:|',
    f"| Segments transcrits en entrée | 670 | {counts['source_segments']} conservés |",
    f"| Paragraphes produits | {len(baseline['points'])} | {report.get('new_paragraphs', 'aucun nouveau document accepté')} |",
    f"| Caractères de synthèse | {sum(len(p['summary']) for p in baseline['points'])} | {report.get('new_characters', '—')} |",
    f"| Segments cités dans la synthèse | {len({s for p in baseline['points'] for s in p['sources']})} | {report.get('new_source_segments', '—')} |",
    f"| Informations / variantes conservées | pas de registre éditable | {counts['information_entries']} |",
    f"| Admissibles avant contrôles de rédaction | — | {counts['eligible_information_entries']} |",
    f"| Informations à vérifier | fichiers de diagnostic | {counts['to_verify_information_entries']} |",
    f"| Segments avec citation candidate | — | {counts['source_segments_with_candidate_citation']} |",
    f"| Segments sans citation candidate, texte conservé | — | {counts['source_segments_without_candidate_citation']} |", '',
    'Une variante n’est pas nécessairement un fait supplémentaire. Une citation exacte ne '
    'garantit pas la fidélité de sa reformulation. Tous les refus, résidus et informations '
    'non rédigées restent dans la copie consultable par l’interface.', '',
    '## Six dimensions demandées', '', '| Dimension | Résultat |', '|---|---|']
for dimension in ['Couverture des thèmes', 'Informations sémantiquement perdues',
    'Erreurs d’attribution', 'Inversions de sens', 'Pertinence des regroupements', 'Qualité rédactionnelle']:
    lines.append(f'| {dimension} | Non mesurée : référence humaine indépendante absente |')
lines += ['', '## Plans à comparer — propositions, pas thèmes de référence', '',
    '### Titres du brouillon 0.2.3 archivé', '']
lines.extend('- ' + p['title'] for p in baseline['points'])
lines += ['', '### Classement provisoire du registre 0.2.4', '',
    'Un intitulé peut être tronqué, trop large ou erroné. Le classement automatique '
    'ne certifie pas que les fiches traitent réellement du même sujet.', '',
    '| Intitulé stocké | Fiches / variantes | Admissibles avant rédaction |', '|---|---:|---:|']
subjects = Counter(e['subject'] for e in registry['entries'] if e['category'] == 'information')
eligible = Counter(e['subject'] for e in registry['entries'] if admissible(e, {'utterances': registry['sources']}))
for subject, total in subjects.items():
    lines.append(f"| {subject.replace('|', '/')} | {total} | {eligible[subject]} |")
lines += ['', '## Observations et limites', '',
    'La lecture de développement a repéré une généralisation d’un récit personnel vers '
    'des observateurs non cités et un commentaire sur un fragment de transcription incomplet. '
    'Qwen les avait acceptés ; ces deux fiches ont été remises à vérifier avant cette rédaction. '
    'Il s’agit d’observations du développement, pas d’annotations humaines ni d’un taux de précision.', '',
    'Les sujets proposés restent provisoires : certains intitulés sont longs, tronqués ou '
    'discutables. Leur déplacement/correction est disponible dans le registre. Les relations '
    'automatiques sont cherchées par sujet sur des lots bornés ; leur absence ne prouve pas '
    'l’absence d’un lien question-réponse ou d’un désaccord.', '',
    f"Relations conservées : {len(registry['relations'])}. Répartition des avis machine : "
    f"{dict(Counter(r['verification'] for r in registry['relations']))}.", '',
    '## Rédaction depuis le registre', '']
if post:
    lines += ['**Après examen du résultat, huit fiches ont été remises à vérifier dans la copie. '
        'Le brouillon ci-dessous est conservé pour comparaison et sa provenance est désormais '
        'obsolète. Corriger les fiches et leurs sujets, puis régénérer et relire un nouveau '
        'brouillon avant export. Aucune approbation humaine n’a été créée.**', '',
        'Les comptes de comparaison ci-dessus correspondent à la révision utilisée pour rédiger. '
        f"Le registre courant conserve {post['current_coverage']['information_entries']} fiches, "
        f"dont {post['current_coverage']['to_verify_information_entries']} à vérifier et "
        f"{post['current_coverage']['eligible_information_entries']} admissibles avant rédaction.", '',
        'Les observations de développement concernent notamment le rattachement de propos sur '
        'un emploi étudiant, le salaire et le prélèvement à un sujet de sélection universitaire, '
        'une question vague sous un sujet de chiffres du mouvement, et un lien douteux entre '
        'révolution et expérience personnelle. Elles restent des doutes à examiner sur les '
        'sources, sans référence humaine indépendante ni taux de précision.', '']
if report['status'] == 'passed':
    draft = json.loads((work / 'draft.json').read_text(encoding='utf-8'))
    lines += ['**Brouillon non relu. Export bloqué : corriger le registre, régénérer puis relire explicitement.**'
        if post else '**Brouillon non relu. Export de production bloqué sans relecture explicite.**', '']
    if any('durerant' in point['summary'].lower() for point in draft['points']):
        lines += ['Observation rédactionnelle du développement : la forme incorrecte « durerant » '
            'subsiste dans un paragraphe accepté par les contrôles machine. Une correction '
            'rédactionnelle humaine reste nécessaire ; aucun taux de qualité n’en est déduit.', '']
    for point in draft['points']:
        lines += ['### ' + point['title'], '', point['summary'], '',
            'Sources : ' + ', '.join(point['sources']) + '.', '']
else:
    lines += ['La rédaction a été refusée ou interrompue : `' + report.get('error', 'inconnu') + '`.', '',
        'Aucun nouveau document accepté n’est présenté à la place de l’ancien. Les informations '
        'et points de reprise restent disponibles. Les contrôles n’ont pas été contournés.', '']
writing = registry.get('writing', {})
lines += ['## Éléments non repris', '',
    f"Informations non rédigées : {len(writing.get('not_written_information_ids', []))}. "
    f"Omissions explicites : {len(writing.get('omissions', []))}.", '']
for topic in writing.get('topics', []):
    if not topic.get('sentences'):
        reasons = list(dict.fromkeys(x.get('reason', 'non précisé') for x in topic.get('rejected_attempts', [])))
        lines += ['- Sujet refusé : ' + topic['title'] + '. Diagnostics : ' + ', '.join(reasons) + '.']
lines += ['', '## Accès à la copie', '',
    'Fermer toute instance utilisant cette copie, puis lancer `Ouvrir-NoteTaker.cmd` dans '
    'ce dossier. Choisir « Conseil municipal », puis « Registre des informations ». '
    'Le dossier de données est `data`, distinct des données originales AppData. '
    'Les liens de lecture audio pointent vers les enregistrements originaux existants, '
    'qui restent nécessaires et ne sont pas modifiés. Cette copie n’est donc pas portable.', '',
    'La nouvelle version SQLite v5 ne doit pas être ouverte avec un ancien exécutable. '
    'Ne jamais diminuer le numéro de schéma. La recette Windows vierge déconnecté, '
    'la qualification de redistribution et l’installateur commercial restent à réaliser.', '']
path = work / 'Comparaison-registre-0.2.4.md'
path.write_text('\n'.join(lines), encoding='utf-8')
store.close()
print(path)
