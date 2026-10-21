"""Portable, immutable human references and evidence-linked scoring reports."""
import csv
import json
from pathlib import Path
from .core import canonical,digest,review_valid


def save_reference(project,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    (folder/'reference.json').write_text(json.dumps(project,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    hash=project['audio']['sha256'];uem=[];rttm=[];verbatim=[];words=[]
    for z in project['zones']:
        if review_valid(z,'text',hash):verbatim.append({'zone':z['id'],'start':z['start'],'end':z['end'],'text':z['verbatim'],'review':z['reviews']['text']})
        if review_valid(z,'diarization',hash):
            uem.append(f"debate 1 {z['start']:.6f} {z['end']:.6f}")
            for t in z['turns']:rttm.append(f"SPEAKER debate 1 {t['start']:.6f} {t['end']-t['start']:.6f} <NA> <NA> {t['speaker']} <NA> <NA>")
        if review_valid(z,'word_times',hash):words.extend({'zone':z['id'],**w} for w in z['words'])
    (folder/'reference.uem').write_text('\n'.join(uem)+'\n',encoding='utf-8')
    (folder/'reference.rttm').write_text('\n'.join(rttm)+'\n',encoding='utf-8')
    (folder/'verbatim-revu.json').write_text(json.dumps(verbatim,ensure_ascii=False,indent=2),encoding='utf-8')
    with (folder/'mots-revus.tsv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['zone','start','end','text','speaker'],delimiter='\t');writer.writeheader();writer.writerows(words)
    (folder/'provenance.json').write_text(canonical({'reference_sha256':digest(project),'audio':project['audio'],
        'no_hypothesis_automatically_imported':True,'human_review_required':True,
        'hypothesis_exposure_recorded_in_reviews':True}),encoding='utf-8')
    return folder


def write_report(project,report,folder):
    folder=Path(folder);save_reference(project,folder/'reference-humaine')
    percent=lambda x:'non mesuré' if x is None else f'{100*x:.2f} %'
    milliseconds=lambda x:'non mesuré' if x is None else f'{1000*x:.1f} ms'
    coverage=report['coverage']
    lines=['# Qualification comparative — référence humaine','',
        '**Aucun moteur de production modifié. Aucun gagnant choisi automatiquement.**','',
        f"Référence figée : `{report['reference_sha256']}`. Audio commun : `{report['audio_sha256']}`.",
        f"Texte revu : {coverage['text_reviewed_zones']} zones ; WER exploitable : {coverage['WER_eligible_zones']} ; "
        f"DER : {coverage['DER_zones']} zones ({coverage['DER_audio_seconds']:.3f} s / {coverage['total_audio_seconds']:.3f} s) ; "
        f"mots horodatés revus : {coverage['word_timing_zones']} zones.",
        f"{coverage['text_reviewed_before_hypotheses_seen']} zones de texte ont été validées avant affichage des hypothèses dans l’outil. "
        'Cette provenance ne garantit pas que l’annotateur n’a jamais vu d’autres résultats auparavant. Les zones exposées sont signalées séparément.','',
        f"**WER sans horaires humains de chaque mot** : {coverage.get('WER_eligible_portions',coverage['WER_eligible_zones'])} portions / {coverage.get('WER_audio_seconds',0):.3f} s évaluées. "
        f"{coverage.get('WER_pending_portions',0)} propositions attendent une validation du découpage ou une correction de bornes. La validation 2/3 du texte et des voix est suffisante ; le troisième domaine mesure seulement l’alignement.",
        'Aucun mot ni tour de parole humain n’a été corrigé automatiquement. Les résultats précédents restent conservés.','',
        '## Couverture de la parole et chevauchements','',
        'Les chevauchements ci-dessous sont déduits de voix humaines simultanées, pas d’une simple étiquette appliquée à l’extrait entier. '
        'Les plages sans tour humain ne sont pas déclarées silencieuses automatiquement. Les indications ASR sont des alertes à écouter, pas une vérité humaine.','']
    for d in report.get('coverage_diagnostics',[]):
        lines += [f"### {d['zone']}",'']
        for a,b in d['real_human_overlaps']:lines.append(f'- Chevauchement humain : **{a:.3f}–{b:.3f} s** ({b-a:.3f} s), exclu du WER séquentiel uniquement sur cette plage.')
        for hole in d['uncovered']:
            lines.append(f"- **Non couvert par les tours humains : {hole['start']:.3f}–{hole['end']:.3f} s ({hole['duration']:.3f} s)** — {hole['status']}. "
                         'Auteurs/activité à compléter ou silence à confirmer ; une validation WER locale ne complète pas les voix de la référence.')
        if not d['uncovered']:lines+=['- Pas de trou de couverture entre les tours humains sur cette zone.']
        lines+=['']
    if any(hole['speech_detected_by'] for d in report.get('coverage_diagnostics',[]) for hole in d['uncovered']):
        lines += ['**DER de zone indicatif : couverture incomplète.** Le calcul historique du DER est conservé pour comparaison : '
            'les trous entre les tours humains y sont implicitement traités comme silence. La parole moteur sur ces plages peut donc '
            'être comptée comme fausse alarme sans que le silence soit réellement annoté. Ne pas qualifier ces valeurs comme une précision '
            'validée avant de compléter ou confirmer humainement ces plages. Les annotations et les anciens rapports restent inchangés.','']
    lines += [
        '## Transcription et attribution : mesures séparées','',
        '| Chaîne | WER | S / D / I | DER brut | Confusion / omission / fausse alarme (s) |',
        '|---|---:|---|---:|---|']
    for key,r in report['results'].items():
        w,d=r['transcription'],r['diarization']
        parts=' / '.join(f"{d[k]:.3f}" for k in ('confusion','missed detection','false alarm')) if 'total' in d else 'non mesuré'
        errors=f"{w['substitute']} / {w['delete']} / {w['insert']}" if w['zones'] else 'non mesurés'
        lines.append(f"| {r['name']} | {percent(w['WER'])} | {errors} | {percent(d['DER'])} | {parts} |")
    lines += ['',
        'WER : erreurs de mots, sans tenir compte de l’identité. DER : activité et regroupement vocal ; la confusion, '
        'les omissions et fausses alarmes sont présentées séparément. Les voix techniques sont appariées aux voix humaines '
        'par une permutation optimale globale sur les zones DER revues de cet enregistrement, pas par leur nom ni extrait par extrait. '
        'Une zone de silence peut contribuer des fausses alarmes/insertions ; sans dénominateur humain, son taux reste non mesuré.','',
        '## Apport propre de WhisperX','',
        '| Chaîne | Erreur moyenne début / fin | Mots corrects avec horaires / mots humains | 2 bornes à ±100 ms, sur tous mots humains | Mauvaise attribution conditionnelle |',
        '|---|---|---:|---:|---:|']
    for r in report['results'].values():
        a=r['alignment_and_word_attribution']
        lines += [f"| {r['name']} | {milliseconds(a['mean_start_absolute_error_seconds'])} / {milliseconds(a['mean_end_absolute_error_seconds'])} | {a['matched_words_with_times']} / {a['reference_words']} | {percent(a['both_boundaries_within_100ms_fraction_of_reference'])} | {percent(a['conditional_attribution_error_rate'])} |"]
    perf=report.get('performance',{});baseline=perf.get('B complet CUDA, sans WhisperX',{}).get('wall_seconds')
    aligned=perf.get('B complet CUDA, avec WhisperX',{}).get('wall_seconds')
    if baseline is not None and aligned is not None:
        lines += ['',f"Surcoût observé WhisperX sur le benchmark GPU complet : **{aligned-baseline:.2f} s**, "
                  f"soit **{100*(aligned-baseline)/baseline:.2f} %** des étapes Large-v3 + Community-1 sans alignement. "
                  'Une seule exécution sur le poste de développement, caches non purgés ; pas de comparaison statistique ni CPU/GPU à matériel égal.']
    lines += ['',
        'Large-v3 et WhisperX partagent le même texte reconnu et la même diarisation brute : WER et DER bruts doivent être identiques. '
        'Les gains éventuels concernent les horaires et les mots attribués dans la transcription finale. Les moyennes d’erreur temporelle '
        'portent seulement sur les mots reconnus correctement avec horaires disponibles ; le ratio de couverture est affiché pour éviter '
        'de présenter l’exclusion de mots difficiles comme un progrès. La mauvaise attribution conditionnelle porte sur les mots lexicalement '
        'corrects, après appariement vocal global. Seules les plages de chevauchement sont exclues du WER séquentiel ; leur découpage exige '
        'une sélection du texte approuvée à l’écoute. Les diagnostics de mots restent exclus sur les zones chevauchantes sans annotation lexicale dédiée.','',
        '## Protocole reproductible','']
    for key,text in report['protocol'].items():lines.append(f'- **{key}** : {text if text is not None else "non mesuré"}')
    lines += ['','## Cas difficiles annotés','',
        '| Chaîne | Catégorie | WER (mots humains) | DER (secondes de voix humaines) |',
        '|---|---|---:|---:|']
    for result in report['results'].values():
        for tag,s in result['difficult_cases'].items():lines.append(f"| {result['name']} | {tag} | {percent(s['WER'])} ({s['human_words']}) | {percent(s['DER'])} ({s['human_speaker_seconds']:.3f}) |")
    lines += ['','Une même zone peut appartenir à plusieurs catégories : ces sous-ensembles ne doivent pas être additionnés. '
        'Les noms propres ne sont pas automatiquement reconnus comme tels ; la catégorie est fournie par l’annotateur.','',
        '## Erreurs de mots relevées','']
    for result in report['results'].values():
        lines += ['### '+result['name'],'']
        for z in result['transcription']['zones']:
            errors=[]
            for op,i,j in z['operations']:
                if op=='substitute':errors.append(f"substitution « {z['reference'][i]} » → « {z['hypothesis'][j]} »")
                elif op=='delete':errors.append(f"omis « {z['reference'][i]} »")
                elif op=='insert':errors.append(f"ajouté « {z['hypothesis'][j]} »")
            lines += [f"- **{z['id']}** ({z['start']:.3f}–{z['end']:.3f} s) : "+('; '.join(errors) if errors else 'aucune erreur de mot selon cette référence et cette normalisation.')]
        if not result['transcription']['zones']:lines+=['Aucune portion exploitable annotée.']
        lines+=['']
    lines += ['## Erreurs de voix par zone','',
        '| Chaîne | Zone | Confusion s | Parole manquée s | Fausse alarme s | DER |','|---|---|---:|---:|---:|---:|']
    for result in report['results'].values():
        for z in result['diarization']['zones']:lines.append(f"| {result['name']} | {z['id']} | {z['confusion']:.3f} | {z['missed detection']:.3f} | {z['false alarm']:.3f} | {percent(z['DER'])} |")
    lines += ['','## Zones exclues et écarts qualitatifs','']
    for s in report['scope']:lines.append(f"- {s['zone']} : {s['reason']}")
    proposals=report.get('wer_plan') or report.get('wer_proposals')
    if proposals and proposals['blocks']:
        from .wer_plan import token_view,approved
        lines += ['','## Découpage WER : validation humaine attendue','',
            'Ouvrir « WER sans horaires de mots… ». Écouter la portion, vérifier ses bornes, sélectionner ses mots dans le verbatim '
            'existant, puis valider. Les rattachements proposés sont guidés par l’ASR et ne sont pas approuvés automatiquement.','',
            '| Portion | Bornes audio (s) | Statut | Texte humain proposé, à vérifier |','|---|---|---|---|']
        for b in proposals['blocks']:
            z=next(z for z in project['zones'] if z['id']==b['zone']);view,spans=token_view(z['verbatim'])
            text=view[spans[b['first_token']][0]:spans[b['last_token']-1][1]] if b['last_token']>b['first_token'] else '(sélection à faire)'
            text=text.replace('|','\\|').replace('\n',' ')
            lines.append(f"| {b['id']} | {b['start']:.3f}–{b['end']:.3f} | {'Validée' if approved(b) else 'À valider'} | {text} |")
    for z in project['zones']:
        if z['tags']:lines.append(f"- {z['id']} — catégories : {', '.join(z['tags'])}.")
        for n in z['notes']:lines.append(f"- {z['id']} — {n.get('chain','commun')} / {n.get('type','observation')} : {n['text']}")
    lines += ['','## Recommandation CPU / GPU : conditions restant à satisfaire','',
        '- **CPU** : Small + sherpa reste la référence opérationnelle testée sur le fichier entier. '
        'Large-v3/Community-1 ont seulement un pilote CPU de 60 s ; leurs mesures CPU longues restent nécessaires. '
        'Un taux sur quelques extraits ne suffit pas à remplacer ce moteur.',
        '- **GPU** : Large-v3 + Community-1 est une candidate techniquement testée sur le fichier entier. '
        'Conserver WhisperX seulement si les horaires/attributions revus montrent un gain justifiant son surcoût. '
        'Examiner ensemble les erreurs de noms, voix courtes, interruptions et chevauchements, sans se limiter à un taux agrégé.',
        '- **Qualité** : les zones non revues ne sont jamais évaluées. Les résultats sur ces extraits ne valident pas '
        'le reste du débat ni une réunion municipale naturelle. La décision finale attend une couverture représentative '
        'et une revue humaine des écarts.',
        '- **Redistribution / hors ligne** : réserves du dossier `docs/audio-benchmark-20261020-licenses.md` inchangées '
        '(DLL NVIDIA/FFmpeg, données NLTK, notices). Tests sur Windows vierge déconnecté toujours requis. '
        'Les modèles téléchargés et le benchmark sont conservés ; aucun installateur construit.','']
    if report.get('boundary_audit'):
        from .audit_export import lines as audit_lines,write_tables
        audit=audit_lines(project,report)
        lines[3:3]=audit+['---','']
        (folder/'audit.md').write_text('# Audit audio NoteTaker — '+report['evaluation_protocol_version']+'\n\n'+'\n'.join(audit),encoding='utf-8')
        write_tables(report,folder)
    (folder/'rapport.md').write_text('\n'.join(lines),encoding='utf-8')
    with (folder/'wer-par-zone.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['chaine','zone','start','end','N','S','D','I','WER','hypotheses_vues_avant_validation'])
        for key,r in report['results'].items():
            for z in r['transcription']['zones']:writer.writerow([key,z['id'],z['start'],z['end'],z['reference_words'],z['substitute'],z['delete'],z['insert'],z['WER'],z['hypotheses_seen_before_review']])
