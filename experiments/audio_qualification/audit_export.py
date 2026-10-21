"""Comparative audit tables; no human decision is inferred from model agreement."""
import csv
import wave
from pathlib import Path
from .core import tokens


def percent(value):return 'non mesuré' if value is None else f'{value*100:.2f} %'
def stamp(value):return f'{int(value)//60:02d}:{value%60:06.3f}'
def safe(value):return str(value).replace('|','\\|').replace('\n',' ')


def lines(project,report):
    coverage=report['coverage'];duration=coverage['total_audio_seconds'];reviewed=coverage['DER_audio_seconds']
    rows=['## Audit du protocole : résultats provisoires','',
        '**Ces scores conservent les sélections humaines validées, y compris celles signalées comme douteuses. Aucune correction ni approbation automatique.**','',
        '| Chaîne | WER strict | N strict | Erreurs S+D+I | WER normalisé | N norm. | Erreurs norm. | DER historique | DER qualifié partiel |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in report['results'].values():
        w,n,d,q=r['transcription'],r['transcription_normalized'],r['diarization'],r['diarization_qualified']
        rows.append(f"| {r['name']} | {percent(w['WER'])} | {w['reference_words']} | {w['errors'] if w['zones'] else 'non mesuré'} | {percent(n['WER'])} | {n['reference_words']} | {n['errors'] if n['zones'] else 'non mesuré'} | {percent(d['DER'])} | {percent(q['DER'])} |")
    baseline=report.get('baseline_comparison')
    if baseline:
        rows += ['','### Vérification du rapport précédent','',
                 f"- Même référence humaine : {baseline['same_reference']}. Même audio : {baseline['same_audio']}.",
                 f"- Même sélection audio–texte : **{baseline['same_scoring_selection']}**. Rapport précédent conservé : `{baseline['report_path']}`."]
        for change in baseline['portion_changes']:
            rows.append(f"- **{change['id']}** : "+'; '.join(f"{k} : {v['before']} → {v['after']}" for k,v in change['fields'].items())+'. Ce changement existait dans le découpage sauvegardé ; il n’a pas été fait par cet audit.')
        for k,v in baseline['historical_rates'].items():
            rows.append(f"- {report['results'][k]['name']} : ancien WER {percent(v['WER'])}, N={v['N']}. Reproduction exacte sur ce découpage : {baseline['strict_historical_reproduced'][k]}. DER historique reproduit : {baseline['historical_DER_reproduced'][k]}.")
        if not baseline['same_scoring_selection']:rows.append('- **La variation du taux strict ne prouve aucun gain moteur** : la sélection humaine diffère. Une reproduction avec le plan historique est fournie séparément.')
    rows += ['',
        '**N strict et N normalisé diffèrent** : élisions, noms composés et nombres peuvent changer la tokenisation. Le WER normalisé complète le strict ; il ne remplace pas une correction humaine du verbatim.',
        'Large-v3 et WhisperX partagent texte et diarisation : leurs WER/DER identiques ne constituent pas deux résultats indépendants.','',
        '### Couverture réellement retenue','',
        f"- WER : **{coverage['WER_audio_seconds']:.3f} s / {duration:.3f} s ({percent(coverage['WER_audio_seconds']/duration)})** du fichier ; "
        f"{percent(coverage['WER_audio_seconds']/reviewed) if reviewed else 'non mesuré'} des zones voix revues. Cette portée est approuvée, mais son rattachement lexical reste soumis aux alertes ci-dessous.",
        f"- Référence lexicale sélectionnée : {next(iter(report['results'].values()))['transcription']['reference_words']} mots stricts sur {coverage['human_reviewed_reference_words']} mots des verbatims revus ({percent(next(iter(report['results'].values()))['transcription']['reference_words']/coverage['human_reviewed_reference_words']) if coverage['human_reviewed_reference_words'] else 'non mesuré'}). Les mots non retenus ne sont pas tous des omissions : certains sont simultanés.",
        f"- DER historique : {reviewed:.3f} s. DER qualifié : **{coverage['DER_qualified_audio_seconds']:.3f} s ({percent(coverage['DER_qualified_audio_seconds']/duration)} du fichier ; {percent(coverage['DER_qualified_audio_seconds']/reviewed) if reviewed else 'non mesuré'} des zones voix revues)**.",
        f"- Activité inconnue exclue du DER qualifié **dans les zones voix déjà revues** : **{coverage['DER_unknown_audio_seconds']:.3f} s**. La validation WER d'une parole ne renseigne pas son identité et n'étend donc pas ce masque.",
        f"- Audio hors des zones voix revues : **{duration-reviewed:.3f} s**, exclu lui aussi, jamais noté automatiquement.",
        '- Le DER qualifié est conditionnel à ce masque : il ne mesure pas les erreurs de détection dans les plages inconnues exclues. Même UEM pour tous, permutation optimale globale sur ce seul UEM ; pas de permutation par portion.',
        '- Les faux positifs dans un silence humain explicitement validé restent comptés. Les chevauchements humains restent inclus dans le DER.','',
        '### Confusion, omission et fausse alarme vocales','',
        '| Chaîne | Portée | Confusion (s de voix) | Omission (s de voix) | Fausse alarme (s de voix) | Référence (s de voix) |',
        '|---|---|---:|---:|---:|---:|']
    for r in report['results'].values():
        for name,key in (('Historique','diarization'),('Qualifiée partielle','diarization_qualified')):
            d=r[key]
            rows.append(f"| {r['name']} | {name} | "+' | '.join(f"{d[k]:.3f}" if k in d else 'non mesuré' for k in ('confusion','missed detection','false alarm','total'))+' |')
    rows += ['', 'Les confusions vocales sont mesurées en secondes de voix, pas en nombre de mots ni en nombre arbitraire d’épisodes. Les secondes des deux voix simultanées comptent séparément au dénominateur.','',
        '### WER par zone et par portion','',
        '| Chaîne | Portée | N strict | S / D / I stricts | WER strict | N norm. | S / D / I norm. | WER norm. |',
        '|---|---|---:|---|---:|---:|---|---:|']
    for r in report['results'].values():
        for field in ('by_source_zone','zones'):
            normalized={z['id']:z for z in r['transcription_normalized'][field]}
            for w in r['transcription'][field]:
                n=normalized[w['id']];parts=lambda x:f"{x['substitute']} / {x['delete']} / {x['insert']}"
                rows.append(f"| {r['name']} | {w['id']} | {w['reference_words']} | {parts(w)} | {percent(w['WER'])} | {n['reference_words']} | {parts(n)} | {percent(n['WER'])} |")
    rows += ['','### Audit des onze rattachements audio–texte','',
        'Les correspondances ci-dessous proviennent d’un alignement lexical contextuel déterministe avec les sorties existantes. Elles servent à cibler l’écoute, **pas à établir la vérité audio**. Les répétitions et les erreurs ASR peuvent déplacer cet alignement. Chaque mot et horaire source est conservé dans `scores.json`.','',
        '| Portion | Bornes | N humain / Small / Large | Mots humains hors sélection mais appariés dans la portion (S / L) | Mots sélectionnés appariés hors bornes (S / L) | Frontières traversées par des mots (S / L) |',
        '|---|---|---|---|---|---|']
    audits=report['boundary_audit']['portions']
    for a in audits:
        engines=a['engines'];count=lambda field:' / '.join(str(len(engines[k][field])) for k in ('small','large'))
        rows.append(f"| {a['id']} | {stamp(a['start'])}–{stamp(a['end'])} | {a['reference_words']} / {engines['small']['hypothesis_words']} / {engines['large']['hypothesis_words']} | {count('matching_unselected_human_tokens_inside')} | {count('matching_selected_human_tokens_outside')} | {count('words_crossing_boundaries')} |")
    rows += ['', 'Les nombres dans ce tableau sont des indices de découpage, jamais des corrections automatiques ou des erreurs ASR certifiées. Un mot traversant une frontière est sélectionné selon son milieu ; il peut induire une insertion/suppression si le texte humain suit une autre borne.','']
    for a in audits:
        rows += [f"#### {a['id']} — écoute et corrections proposées",'',
            f"- Référence validée, inchangée : « {a['reference_text']} ».",
            f"- Chevauchement humain inclus dans cette portion : **{a['real_overlap_seconds_in_portion']:.3f} s**."]
        if a.get('listening_clip'):
            clip=a['listening_clip']
            rows.append(f"- [Écouter cette portion avec son contexte]({clip['relative_path']}) : copie PCM du WAV original, **{stamp(clip['absolute_start'])}–{stamp(clip['absolute_end'])}**. Le temps local 0 du fichier correspond à {stamp(clip['absolute_start'])} dans le débat.")
        if a['id']=='E11-P01':
            gaps=[g for g in report['boundary_audit']['unselected_reference_runs'] if g['zone']=='E11' and g['first_token']==60]
            if gaps:
                g=gaps[0];rows += [f"- **Anomalie prioritaire : {g['words']} mots humains d’indices [{g['first_token']},{g['last_token']}) ne sont sélectionnés nulle part** : « {g['text']} ».",
                    '- Les bornes de P01 englobent les deux premiers tours humains, sans chevauchement. Les sorties Small et Large localisent une partie de cette suite vers 18:26–18:33. Une omission de sélection est donc fortement suspectée ; elle ne se déduit pas du seul écart 60 contre 91 mots.',
                    '- **Proposition à confirmer à l’écoute :** rattacher la suite pertinente à P01 ou scinder au changement de voix, en vérifiant la frontière avec P02. Ne pas ajouter automatiquement les 39 mots : leurs débuts/fins exacts et les interjections doivent être écoutés.']
        for k,label in (('small','Small'),('large','Large')):
            e=a['engines'][k]
            text=lambda key:' '.join(t['text'] for t in e[key]) or '(aucun indice)'
            rows += [f"- {label}, mots humains hors sélection appariés à l’intérieur : « {text('matching_unselected_human_tokens_inside')} ».",
                     f"- {label}, mots sélectionnés appariés hors bornes : « {text('matching_selected_human_tokens_outside')} »."]
            for w in e['words_crossing_boundaries']:
                rows.append(f"- {label}, mot « {w['word']} » {stamp(w['start'])}–{stamp(w['end'])} traversant la borne {stamp(w['boundary'])} : écouter la pause et faire suivre les bornes **et** le texte. Aucun déplacement effectué.")
        rows+=['- Vérifier seulement les mots et frontières signalés à l’écoute ; conserver la sélection si elle est fidèle. Toute correction doit être faite puis validée par l’opérateur dans l’assistant.','']
    rows += ['### Mots de la référence hors sélection WER','']
    for gap in report['boundary_audit']['unselected_reference_runs']:
        rows.append(f"- {gap['zone']} [{gap['first_token']},{gap['last_token']}) : {gap['words']} mots — « {gap['text']} ». {gap['reason']}")
    rows+=['','### Activité inconnue exclue du DER qualifié','']
    first=next(iter(report['results'].values()))
    for gap in first['diarization_qualified']['excluded_unknown_activity']:
        rows.append(f"- **{gap['zone']} {stamp(gap['start'])}–{stamp(gap['end'])} ({gap['seconds']:.3f} s)** : {gap['reason']} Ajouter les tours de toutes les voix après écoute, sans déduire les noms des moteurs.")
    rows+=['','### Règles de normalisation : '+report['normalization']['version'],'']
    rows += [f'- **{key}** : {text}' for key,text in report['normalization']['rules'].items()]
    rows+=['','### Conclusion expérimentale','',
        'Le WER strict conserve le protocole précédent et la sélection figée du présent rapport. Comparer aussi les empreintes du découpage avant d’attribuer une variation à un moteur. Le score normalisé retire seulement les différences prévues par les règles publiées ; il ne répare pas un mauvais rattachement audio–texte. Le DER qualifié exclut l’activité inconnue, mais reste partiel et dépend de la justesse des tours humains.',
        '**Le choix d’un moteur n’est pas validé automatiquement par ces scores.** Résoudre les anomalies de sélection par écoute ciblée, puis recalculer sur une nouvelle révision humaine et comparer la couverture commune. Quelques extraits ne suffisent pas à généraliser ; distinguer le débat de stress test, le conseil réel et une simulation jouée.','']
    review=report.get('operator_review')
    if review is not None:
        rows+=['### Travail humain et erreurs importantes','',
            f"- Corrections de protocole déclarées : {review['protocol_tasks_corrected']} ; contrôles sans changement : {review['protocol_tasks_verified_unchanged']} ; différés : {review['protocol_tasks_deferred']}.",
            f"- Extraits municipaux annotés/contrôlés déclarés séparément : {review.get('reference_tasks_checked',0)} (pas comptés comme corrections d’un moteur).",
            f"- Temps opérateur consigné : {review['operator_elapsed_seconds']:.1f} s. Ce compteur mesure le temps écoulé dans les contrôles, pas un chronométrage de l’activité humaine exclusive.",
            f"- Vérifications ciblées encore proposées : {len(review.get('tasks_remaining',[]))}. Aucune n’est approuvée automatiquement.",
            '- Les corrections de protocole sont communes aux moteurs. Les signalements d’attribution ci-dessous sont déclaratifs, liés aux révisions indiquées dans le JSON ; ils ne constituent pas un taux exhaustif ni un nombre de faux votes détectés automatiquement.','',
            '| Chaîne | Signalements humains d’attribution importante |','|---|---|']
        for k,r in report['results'].items():
            count=review['important_attribution_reports'][k]
            rows.append(f"| {r['name']} | {str(count)+' signalement(s)' if count else 'Aucun signalement enregistré — non évalué exhaustivement'} |")
        rows+=['','### Ressources mesurées (sorties existantes)','',
            '| Chaîne / route | Temps écoulé (s) | Temps CPU (s) | Pic mémoire engagée hôte (octets) |','|---|---:|---:|---:|']
        for name,m in report.get('performance',{}).items():
            rows.append(f"| {name} | {m.get('wall_seconds','non mesuré')} | {m.get('cpu_total_seconds','non mesuré')} | {m.get('peak_committed_bytes','non mesuré')} |")
        rows+=['','Les temps sont ceux des moteurs, distincts du calcul des scores. Les composantes partagées Large/Community ne sont pas inférées deux fois ; le pic mémoire hôte n’est pas la VRAM. Les caches fichiers du système ne sont pas purgés. Les paliers pilotes sont conservés à part du temps du fichier complet.','']
    return rows


def write_tables(report,folder):
    fields=['chain','scope','id','N_strict','S','D','I','WER_strict','N_normalized','S_normalized','D_normalized','I_normalized','WER_normalized']
    with (folder/'wer-strict-normalise.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(fields)
        for key,r in report['results'].items():
            for field in ('by_source_zone','zones'):
                for w,n in zip(r['transcription'][field],r['transcription_normalized'][field]):
                    writer.writerow([key,field,w['id'],w['reference_words'],w['substitute'],w['delete'],w['insert'],w['WER'],
                        n['reference_words'],n['substitute'],n['delete'],n['insert'],n['WER']])


def listening_pack(project,report,folder):
    """Lossless copies for operator listening, not agent acoustic verification."""
    root=Path(folder);(root/'audio').mkdir(exist_ok=False)
    zones={z['id']:z for z in project['zones']}
    with wave.open(project['audio']['path'],'rb') as original:
        rate=original.getframerate();params=original.getparams()
        for a in report['boundary_audit']['portions']:
            if not a['alerts']:continue
            z=zones[a['zone']];start=max(z['start'],a['start']-1.5);end=min(z['end'],a['end']+1.5)
            first=round(start*rate);last=round(end*rate);original.setpos(first)
            # File name uses only an index; untrusted annotation IDs never become paths.
            name=f"portion-{len(list((root/'audio').iterdir()))+1:02d}.wav"
            with wave.open(str(root/'audio'/name),'wb') as output:
                output.setparams(params);output.writeframes(original.readframes(last-first))
            a['listening_clip']={'relative_path':'audio/'+name,'absolute_start':first/rate,'absolute_end':last/rate,
                                 'source_first_frame':first,'source_last_frame':last,'sample_rate':rate}
