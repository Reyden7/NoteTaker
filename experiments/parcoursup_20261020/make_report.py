"""Publish measured artifacts and explicit analyst judgments after all real calls."""
import csv
import io
from .prepare import OUT, read, sha, write_new
from .import_human import V2, HUMAN
from .resolve_sources import resolve_result
from .evaluation_analyste import EVALUATIONS, ANOMALIES

CASES = ['A-original','B-corrigee-humaine','C-corrigee-contexte']


def main():
    measurements=[]; comparisons=[]; instruction_hashes=set(); schema_hashes=set(); runtime_ids=[]
    reference=read(V2/'reference-independante-v2.json')
    points=reference['points']+reference['additional_human_verbatim_points']
    for name in CASES:
        work=V2/'runs'/name
        report=read(work/'report.json'); profile=read(work/'direct-profile.json')
        if report['status']!='completed' or len(profile['calls'])!=1: raise ValueError('Not a complete single fresh call: '+name)
        if set(EVALUATIONS.get(name,{})) != {p['id'] for p in points}: raise ValueError('Analyst reading missing: '+name)
        call=profile['calls'][0]
        assert profile['cache_mode']=='cold' and profile['fresh_calls']==1 and profile['cached_calls']==0
        assert call['cache_hit'] is False and call['exit_code']==0 and call['token_budget']==3000
        instruction_hashes.add(sha(work/'instruction.txt')); schema_hashes.add(sha(work/'isolated-000.schema.json'))
        runtime_ids.append(profile['runtime'])
        cpu=call['cpu']
        measurements.append({'case':name,'native_wall_seconds':call['wall_seconds'],
            'cpu_user_seconds':cpu['user_seconds'],'cpu_kernel_seconds':cpu['kernel_seconds'],
            'cpu_total_seconds':sum(cpu.values()),'total_wall_including_hashes':report['wall_seconds_including_model_hashes'],
            'prompt_eval_seconds':call.get('prompt_eval_seconds'),'generation_eval_seconds':call.get('generation_eval_seconds'),
            'prompt_tokens':call.get('prompt_tokens'),'generation_tokens':call.get('generation_tokens'),
            'literal_issue_count':report['literal_issue_count'],'structured_counts':report['counts'],
            'fresh_calls':1,'cached_calls':0,
            'input_sha256':report['input_sha256'],'result_sha256':sha(work/'isolated-000.result.json')})
        result=read(work/'isolated-000.result.json'); inputs=read(V2/'inputs'/(name+'.json'))
        write_new(work/'citations-resolues.json',resolve_result(result,inputs))
    assert len(instruction_hashes)==len(schema_hashes)==1
    assert all(identity==runtime_ids[0] for identity in runtime_ids)
    for p in points:
        row={'reference_id':p['id'],'human_content':p['content'],'cases':{}}
        for name in CASES:
            state,path,note=EVALUATIONS[name][p['id']]
            row['cases'][name]={'analyst_status':state,'output_path':path,'reason':note}
        comparisons.append(row)
    preservation={p:sha(p)==digest for p,digest in read(OUT/'manifest.json')['protected_files'].items()}
    receipt=read(V2/'provenance-humaine.json')
    preservation['human_correction_original_and_copy']=sha(HUMAN)==sha(V2/'correction-humaine-originale.txt')==receipt['human_file_sha256']
    manifest=read(OUT/'manifest.json')
    preservation['source_audio']=sha(manifest['source_audio'])==manifest['audio_sha256']
    assert all(preservation.values())
    output={'quality_validated':False,'assessment_author':'Codex analyst, checking independent human sources; not a new blinded human evaluation',
            'measurements':measurements,'comparison':comparisons,'anomalies':ANOMALIES,
            'identical_instruction_sha256':next(iter(instruction_hashes)),
            'identical_schema_sha256':next(iter(schema_hashes)),'runtime':runtime_ids[0],
            'preservation':preservation,'production_modified':False,'reintroduced_claims':0,
            'disk_cache_flushed':False,'repeated_trials':False}
    write_new(V2/'comparaison.json',output)
    stream=io.StringIO(newline='')
    writer=csv.writer(stream,delimiter=';')
    writer.writerow(['Référence','Information humaine','Variante','État selon analyste','Rubrique réelle','Justification'])
    for row in comparisons:
        for name,value in row['cases'].items():
            writer.writerow([row['reference_id'],row['human_content'],name,value['analyst_status'],value['output_path'],value['reason']])
    write_new(V2/'comparaison.csv',stream.getvalue())
    lines=['# Diagnostic expérimental Parcoursup — résultats du 20 octobre 2026','',
        '**Expérience hors application ; aucune qualité produit validée, aucune autorisation d’export accordée.**','',
        '## Sources et protocole','',
        'Référence narrative fournie par l’utilisateur, puis extrait corrigé `correction.txt` reçu après demande de relecture audio. Copies et empreintes conservées. L’agent n’a pas écouté l’audio. Les jugements ci-dessous sont son analyse des sources humaines, pas de nouvelles notes aveugles données par un humain, ni l’avis de Qwen sur ses propres réponses.','',
        '- Fenêtre focale : **17:31.960–20:37.580**, 185,620 s. A = 109 fragments/18 tours ; B = 103 fragments/13 tours ; C = B + 58 fragments de contexte, 161 fragments/28 tours.',
        '- A est l’instantané réel utilisé pour les 670 passages, avec les libellés et corrections déjà sauvegardés. Il n’est pas une sortie Whisper acoustique brute jamais modifiée.',
        '- B utilise la correction humaine telle quelle : 20 textes changés, 103 libellés changés, six fragments absents inventoriés sans déduire silencieusement leur fusion. Aucun original remplacé.',
        '- C ajoute le contexte original précédent, à partir de 16:00.660. Cette extension **n’est pas corrigée à l’écoute**. Le noyau B est identique. Le corpus transcrit finit à 20:37.580 : aucun contexte transcrit postérieur disponible ici. Le bénéfice d’un contexte propre avant ET après n’est donc pas évalué.',
        '- Tous les fragments de chaque entrée sont transmis, uniquement regroupés par libellés consécutifs identiques. Aucun tri thématique ni filtrage applicatif. IDs Txxx propres à chaque variante, catalogue original conservé.',
        '- Instruction, schéma et paramètres identiques entre A/B/C : Qwen3-4B-Instruct-2507 Q4_K_M, llama CPU b11681, GPU 0 couche, 4 threads, contexte 12288, température 0,7 / top-p 0,8 / top-k 20 / min-p 0 / graine 42, maximum 3000 tokens.',
        '- Trois processus neufs, un appel neuf chacun, aucune réponse réutilisée. Cache disque Windows non purgé ; un seul essai par condition, poste non isolé. Les durées ne sont pas des moyennes reproductibles ni une mesure de vitesse produit sur toute la réunion.',
        '- La référence humaine, les corrections attendues et les réponses des autres variantes ne sont jamais ajoutées au prompt. Les paroles et leurs noms corrigés sont naturellement l’entrée B/C.','',
        '## Trois sorties réelles','']
    for name in CASES: lines.append(f'- [{name} — sortie Qwen non filtrée](runs/{name}/synthese.md) · [texte et catalogue des sources]({name}.md) · [citations résolues](runs/{name}/citations-resolues.json).')
    lines += ['', 'Écouter l’[extrait focal](../extrait-focal-17m32-20m38.wav) ou le [contexte élargi](../contexte-large-16m00-20m40.wav). Les horaires sont les repères ASR sauvegardés, pas des limites acoustiques recalées sur les mots corrigés.','',
        '## Performances réellement mesurées','',
        '| Variante | Temps natif écoulé (s) | CPU user + kernel (s) | Évaluation entrée (s / tokens) | Génération (s / tokens) | Appels neufs / cache |',
        '|---|---:|---:|---:|---:|---:|']
    for m in measurements:
        lines.append(f"| {m['case']} | {m['native_wall_seconds']:.3f} | {m['cpu_total_seconds']:.3f} | {m['prompt_eval_seconds']:.3f} / {m['prompt_tokens']} | {m['generation_eval_seconds']:.3f} / {m['generation_tokens']} | 1 / 0 |")
    lines += ['', 'CPU = compteurs Windows réels du processus natif, cumulés sur les threads ; ils peuvent dépasser le temps écoulé. Le JSON conserve aussi le temps total incluant les empreintes du modèle. L’option native `--offline` est active et les tentatives réseau Python sont bloquées.',
        'Une réponse plus courte peut être plus rapide tout en omettant davantage d’éléments ou de citations : la différence de durée A/B/C n’est donc pas à elle seule un gain de traitement utile.','',
        '**Échec conservé :** le premier A, protocole v1 à fragments séparés et budget 3500, a atteint 900,409 s natives / 3526,922 s CPU, réponse incomplète. Son brut et son profil restent dans `../runs/A-original/`. Il n’est pas inclus dans la comparaison A/B/C v2 ni présenté comme une réussite. Le protocole v2 diffère du v1 : on ne peut pas imputer sa durée à la seule correction du texte.','',
        '## Comparaison avec la référence humaine','',
        'Onze points de la référence narrative H01–H11, puis deux points V01–V02 explicitement vérifiables dans la copie humaine. « Exact » qualifie la présence de ce point, pas la fidélité de toutes les sorties. Les réserves et défauts de citation restent décrits. Un thème figurant uniquement dans les citations recopiées, sans synthèse, est signalé absent du relevé. Aucun score global de fiabilité ou gain statistique n’est calculé.','',
        '| Point humain | A original | B corrigée | C corrigée + contexte original |', '|---|---|---|---|']
    for row in comparisons:
        statuses=[row['cases'][n]['analyst_status'] for n in CASES]
        lines.append('| '+row['reference_id']+' — '+row['human_content']+' | '+' | '.join(statuses)+' |')
    for row in comparisons:
        lines += ['',f"### {row['reference_id']} — justification",'']
        for name,value in row['cases'].items():
            lines.append(f"- **{name} · {value['output_path']}** : {value['reason']}")
    lines += ['', '## Déformations, ajouts et mauvais rattachements','']
    for name in CASES:
        lines += ['### '+name,'']
        for a in ANOMALIES[name]: lines.append(f"- **{a['classification']} · {a['path']}** : {a['reason']}")
    lines += ['', '### Contrôles mécaniques, distincts du sens','',
        '| Variante | Éléments signalés par l’audit littéral/rattachement | Citations produites | Propositions produites |',
        '|---|---:|---:|---:|']
    for m in measurements:
        lines.append(f"| {m['case']} | {m['literal_issue_count']} | {m['structured_counts']['citations_sources']} | {m['structured_counts']['propositions']} |")
    lines += ['', 'Les résultats de l’audit littéral sont conservés par variante. Une citation exacte prouve seulement qu’un texte existe. L’exemple des fausses relations entre deux voix dans A démontre pourquoi l’examen du sens et de l’auteur reste nécessaire. Une source existante mais non citée dans le catalogue est signalée ; ce n’est pas un ID inexistant. Le catalogue audio et les références complètes ne sont ni filtrés ni supprimés.','',
        '## Diagnostic des 24 refus de 0.2.5','',
        '[Analyse de chaque refus, textes et citations exactes](diagnostic-24-refus.md) · [données complètes](diagnostic-24-refus.json). **18 formulations refusées à juste titre en l’état ; six motifs potentiellement excessifs ou mixtes**, selon cette analyse. Les six ne sont pas six formulations admissibles : plusieurs ont encore des ajouts ou des références insuffisantes. Aucun arbitrage humain des 24 refus ni aucune réintroduction automatique.','',
        '- Le groupe sur la sélection contient deux thèmes étrangers ; son rejet collectif entraîne onze refus, dont neuf candidats en rapport avec Parcoursup/les relances. C’est une cause réelle de perte, mais certains candidats sont aussi erronés en eux-mêmes.',
        '- Le déclencheur vote/adoption sur majorité/minorité d’étudiants est hors contexte ; il n’y a aucun vote dans cet échange.',
        '- L’extraction perd déjà la centralisation des vœux et la solution +1 h pour cours/ramassage (s331-0/s332-0) avant les contrôles. Il serait insuffisant de ne corriger que les refus.',
        '- « Supprimer ne suffirait pas » ne signifie pas « conserver Parcoursup ». Deux anciens avis individuels Qwen soutenaient pourtant des reformulations non démontrées : ces avis ne servent pas de vérité terrain.',
        '- Les critiques sur l’échec en licence et la santé mentale mentionnées dans la référence se situent après les 670 fragments : pas de score d’omission pour ces informations sur cet instantané.','',
        '## Recommandation','', (V2/'recommandation.md').read_text(encoding='utf-8'),'',
        '## Tests, conservation et limites','',
        '- Dix tests du protocole et des citations réussis (`tests-protocole-citations.xml`, 0,33 s) : PCM focal exact, copie humaine exacte, fragments absents inventoriés, regroupement sans perte, contexte identique au noyau B, rejets du parseur, conservation des sources et détection de citations non littérales. Ce ne sont pas des scores de qualité IA.',
        '- Premier lancement de tests : erreur d’import relatif du nouveau test, corrigée. Second : huit tests réussis et une erreur de répertoire temporaire sandbox ; relance avec répertoire temporaire dédié dans le dépôt, neuf tests réussis, puis dix avec le test de résolution des citations. Les rapports échoués sont conservés.',
        f'- {len(preservation)} vérifications de conservation finales vraies : code applicatif, sources figées, ancienne base, ancien résultat, bundle, audio et correction humaine. Aucune migration ou base de séance ouverte en écriture par ces scripts.',
        '- Suite applicative de 268 tests non relancée : aucun code de production n’a changé. Aucun nouveau bundle compilé pour cette expérience. Whisper et sherpa inchangés ; biométrie non commencée.',
        '- Relecture et export applicatifs non appelés, aucun document approuvé ou vote créé. Les garde-fous existants restent intacts.',
        '- Un extrait, trois inférences, une évaluation par l’analyste sur des sources humaines ; pas de seconde annotation humaine aveugle, pas de score WER/DER, pas de validation d’un PV municipal ou de Windows vierge hors ligne.','']
    write_new(V2/'rapport-comparatif.md','\n'.join(lines))
    print('Wrote comparison, measurements and preservation report.')


if __name__=='__main__': main()
