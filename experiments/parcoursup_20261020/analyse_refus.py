"""Textual case-by-case analysis, not a new human gold annotation or repair."""
import argparse
import json
from collections import Counter
from .prepare import OUT, ARTIFACT, read, write_new, stamp

# Explicit analyst judgments against the supplied narrative AND the frozen
# quoted sources. Never used to rewrite a draft or to approve/export it.
NOTES = [
('justifié en l’état','§1','Nom composé absent des citations sélectionnées : elles s’arrêtent à « Université Bordeaux ». La suite est portée par un autre tour. Le thème de présentation existe ; la référence ne justifie pas cette citation incomplète.'),
('justifié en l’état','§1, §5','Deux extraits appartiennent à la présentatrice alors que la phrase est liée à Louise. Certaines informations sont plausibles, mais mélanger leurs voix ne fournit pas une attribution sûre.'),
('justifié en l’état','§1–2','Deux voix fusionnées dans une seule affirmation et code V3 non lié. Il faut séparer les paroles avant d’examiner un accord, pas autoriser ce consensus implicite.'),
('justifié en l’état','§2, §5','Les sources contiennent des extraits d’une autre voix et ne soutiennent pas toute la généralisation « systématiquement » ni toute la causalité. La référence confirme le thème, pas ce raccourci exact.'),
('motif potentiellement excessif','§9','Le déclencheur vote/adoption est hors contexte : majorité/minorité d’étudiants, aucun scrutin ni résultat de vote. Le mot « brillante » vient déjà de l’ASR et demande écoute ; ce diagnostic du déclencheur ne valide pas la reformulation.'),
('justifié en l’état','§4–6','Un parcours politique est classé dans le sujet Parcoursup. La référence attribue le changement à Louise, pas à une identité masculine V5 assimilée à Manès. Les citations/voix de ce passage sont à réexaminer.'),
('justifié en l’état','§5–6','Le nom propre ajouté n’apparaît pas dans les citations retenues ; une reformulation lie aussi plusieurs idées. La référence confirme lectures/échanges, pas tous les détails de cette phrase.'),
('justifié en l’état','§9','Codes V5/V6 laissés non liés ; surtout 200 blocages et 30 000 personnes sont des unités différentes, pas deux estimations concurrentes du nombre de blocages. Refus utile malgré le motif technique initial.'),
('justifié en l’état','§9','Une affirmation collective est attribuée à une seule voix tout en référençant une autre. L’origine du mouvement existe dans la référence, mais sa graphie/identité ne doit pas être inventée et un accord doit être sourcé.'),
('justifié en l’état','§8','Louise et Manès sont fusionnés alors que les sources les distinguent. La référence donne une solution précise (décaler les cours d’une heure), perdue dans cette formulation générale : corriger les unités d’information, pas lever le contrôle.'),
('motif potentiellement excessif','§6,5, §8–9','Le « vous dites » cité introduit aussi une objection propre de Manès et sa solidarité : le détecteur de propos rapporté peut être trop large. Mais « l’histoire de lutte est un pilier de légitimité » dépasse ces citations. Motif à examiner, phrase non réintroduisible en l’état.'),
('justifié en l’état','§7, §9','Phrase collective Louise/présentatrice, sources de voix différentes et conséquences ajoutées sur l’impact durable. La référence ne transforme pas ces échanges en reconnaissance commune de toute la phrase.'),
('justifié en l’état','§9–10','Le mouvement et une organisation politique sont mêlés dans un groupe sur Parcoursup. Le lien de fondation/disparition est à vérifier séparément ; ce paquet n’est pas un argument sur la sélection universitaire.'),
('justifié en l’état','§10','Plusieurs voix, une voix inconnue et des identités d’organisations mal reconnues sont fusionnées. La référence indique des interruptions/désaccords ; elle ne valide pas cette attribution composite ni les graphies.'),
('justifié en l’état','§10–11','La question sur les solutions/sélection est bien réelle, mais la première partie sur le débat public qui écouterait les non-bloqueurs n’est pas soutenue par les citations indiquées. Un refus collectif manque de précision, sans rendre cette phrase entière fidèle.'),
('justifié en l’état','§11','Le tirage au sort n’est pas dans ces citations ; la référence le place dans l’intervention de Bruno. « Réduction de l’offre » n’équivaut pas à « moindre investissement » ; propos, auteur et faits sont amalgamés.'),
('justifié en l’état','§11','Voix mélangées et contresens temporel : « avant la mise en place de l’enseignement supérieur » reprend une ASR corrompue, pas la chronologie Parcoursup. Le propos doit être retranscrit correctement.'),
('justifié en l’état','§10–11','Relance pratique de Sonia bien établie, mais « motivations profondes », société et sélection taboue ne figurent pas tous dans les citations de cette seconde relance. Rattacher correctement ou retirer les ajouts est nécessaire.'),
('motif potentiellement excessif','§11','L’idée centrale manque de places/demande est explicitement dans la référence et les lignes sources voisines. Le rejet global du titre masque cette information pertinente. Les références s’arrêtent toutefois avant le second terme complet et « abusive » est ajouté : attachement/formulation à corriger avant toute reprise.'),
('motif potentiellement excessif','§12','La question de Louise sur ce qui remplacera Parcoursup et la moindre sélection est confirmée par la référence et ces sources. Le retrait au seul niveau du sujet peut être excessif. Conserver la modalité interrogative et ne pas amplifier « fondamentales ».'),
('motif potentiellement excessif','complément source, non annoté précisément en §12','Les citations disent notes/critère quantitatif et mentionnent l’exception des lettres de motivation. Cette information utile disparaît avec le groupe. La référence narrative ne détaille pas cette réponse et l’identité reste inconnue dans ces sources : fidélité fine/attribution à vérifier humainement.'),
('motif potentiellement excessif','§12','L’anecdote de candidature avec recette en russe est confirmée par la référence et les citations. La perdre à cause du titre global est dommageable ; « transparence » n’est toutefois pas explicite et l’exemple doit rester un propos de Louise, pas un fait vérifié.'),
('justifié en l’état','§11–12','Ouverture de places et sectorisation sont soutenues ; « sans supprimer la plateforme » ne l’est pas. Critiquer l’idée que supprimer suffirait n’équivaut pas à vouloir conserver Parcoursup. La référence décrit justement une plateforme de remplacement avec vœux centralisés.'),
('justifié en l’état','§12 + réponse dans la source','Une seule citation (« la plupart fonctionnent sur les notes ») ne soutient ni l’opposition à la suppression ni le diagnostic de sur-sélection. Contrôle individuel Qwen « supported » non fiable ici ; conserver le refus et isoler la phrase sur les critères.')
]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--human-revision',action='store_true')
    args=parser.parse_args()
    notes=list(NOTES)
    destination=OUT
    if args.human_revision:
        from .import_human import V2
        destination=V2
        # The actual human corrected excerpt refines the broad narrative.
        notes[15]=('justifié en l’état','§11 + correction humaine s499–s511',
            'La correction humaine distingue Arthur (premier arrivé/premier servi) et Bruno (tirage au sort). Le candidat attribue à Manès une chronologie qui n’est pas dans ses citations. « Réduction de l’offre » ne se déduit pas non plus d’un moindre investissement. Refus justifié, sans effacer les arguments réellement présents.')
        notes[16]=('justifié en l’état','§11 + correction humaine s499–s511',
            'La copie humaine distingue Arthur et Bruno ; ce candidat les confond. La formulation de la copie autour de « mise en place de l’enseignement supérieur » reste peu claire et ne démontre pas la chronologie affirmée. Ne pas transformer un fragment ambigu en fait historique certain.')
        notes[20]=('motif potentiellement excessif','correction humaine s560–s567',
            'La correction fournie attribue explicitement à Manès la réponse sur les notes/critère quantitatif et les exceptions des lettres de motivation. Ce contenu est vérifiable dans le verbatim humain ; son retrait avec tout le groupe est potentiellement excessif. Les anciennes sources gardent cependant des voix non liées : l’amélioration du diagnostic ne répare pas automatiquement le candidat ni son rattachement.')
    record = read(ARTIFACT)
    ledger = record['result']['ledger']
    rejected = [c for c in ledger['candidates'] if c['status']=='rejected']
    assert len(rejected)==len(notes)==24
    refs = {r['id']:r for r in ledger['reference_manifest']}
    rows=[]
    for number,(candidate,note) in enumerate(zip(rejected,notes),1):
        category, human_section, analysis = note
        bad_refs=[{'id':rid,'expected_voice':candidate['speaker'],'actual_voice':refs.get(rid,{}).get('speaker')}
                  for rid in candidate['reference_ids'] if rid not in refs or refs[rid]['speaker']!=candidate['speaker']]
        times=[(refs[rid]['start_ms'],refs[rid]['end_ms']) for rid in candidate['reference_ids'] if rid in refs]
        rows.append({'number':number,'candidate':candidate,'automatic_reason':candidate['reasons'],
            'category':category,'human_reference_section':human_section,'analyst_reason':analysis,
            'bad_voice_refs':bad_refs,'span_ms':[min(t[0] for t in times),max(t[1] for t in times)] if times else None,
            'old_qwen_individual_check':ledger.get('targeted_checks',{}).get(candidate['id']),
            'automatic_reintroduction':False,'human_adjudication_completed':False})
    report={'scope':'Codex textual assessment using supplied human narrative and exact frozen evidence; not a human annotation of every claim',
        'human_corrected_focal_excerpt_used':args.human_revision,
        'categories':dict(Counter(row['category'] for row in rows)),
        'static_refusals':13,'collective_heading_refusals':11,
        'important_warning':'A potentially excessive trigger is NOT an admissible sentence. Some such sentences have other citation or meaning defects.',
        'cases':rows,'production_modified':False,'reintroduced_count':0}
    write_new(destination/'diagnostic-24-refus.json',report)
    lines=['# Diagnostic des 24 refus — analyse textuelle, sans réintroduction','',
        ('Référence humaine narrative et extrait focal corrigé par l’utilisateur reçus. Hors extrait focal, pas de nouveau verbatim humain. ' if args.human_revision else 'Référence humaine narrative reçue ; vérification audio fine encore requise. ')+
        'Les avis ci-dessous sont ceux de Codex, pas un arbitrage humain des 24 refus ni les avis du même Qwen comme vérité terrain.','',
        '**13 refus statiques + 11 refus par un titre collectif. 18 refus justifiés en l’état ; 6 motifs potentiellement excessifs ou mixtes. Ces six cas ne sont pas six phrases déclarées exportables.**','',
        'Le groupe « Sélection universitaire et accessibilité » contient aussi deux sujets étrangers (parcours politique et légitimité du mouvement). Le contrôle collectif refuse onze candidats, dont neuf sur Parcoursup ou les relances associées. Certains de ces neuf ajoutent néanmoins des détails non soutenus.','',
        '| N° / ID | Sujet initial | Motif automatique | Diagnostic | Référence humaine |','|---|---|---|---|---|']
    for row in rows:
        c=row['candidate'];title=c.get('initial_topic') or c['topic']
        reason=' ; '.join(row['automatic_reason']).replace('|','/')
        lines.append(f"| {row['number']} · {c['id']} | {title} | {reason} | {row['category']} | {row['human_reference_section']} |")
    for row in rows:
        c=row['candidate'];span=row['span_ms']
        lines+=['',f"## {row['number']} — {c['id']}",'',
            '**Formulation refusée :** '+c['template'],'',
            '**Analyse :** '+row['analyst_reason'],'',
            'Horaires des références : '+(stamp(span[0])+'–'+stamp(span[1]) if span else 'indisponibles'),
            'Référence narrative : '+row['human_reference_section'],
            'État : aucun élément réintroduit ; arbitrage humain non réalisé.','', 'Sources exactes :','']
        lines += [f"- {e['id']} : « {e['quote']} »" for e in c['evidence']]
        if row['bad_voice_refs']:
            lines+=['', 'Références d’une autre voix : '+', '.join(x['id'] for x in row['bad_voice_refs'])]
        if row['old_qwen_individual_check']:
            lines+=['','Ancien avis Qwen (simple constat, **pas une preuve**) : '+str(row['old_qwen_individual_check'])]
    lines+=['','## Omissions antérieures aux refus','',
        '- La solution de centralisation des vœux est dans s549-0/s550-0 et la référence §12. La réponse brute context-004 ne la restitue pas comme solution explicite ; son titre « Critique de la centralisation » ne suffit pas à la restituer.',
        '- La solution d’une heure plus tard pour le ramassage (référence §8) est réduite à une discussion générale des transports dans le candidat D02be33a2bd148fd576dc. Le problème commence à l’extraction, avant tout refus.',
        '- Les candidats D5012b4e5c52f7d9b8ec9 et Da44703ebd23091e57ff0 montrent que l’ancien Qwen a déclaré « supported » des formulations ajoutant une opposition à la suppression non démontrée. Ne pas employer cet avis comme référence indépendante.',
        '- La critique d’une sélection faible, la réponse sur les critères et la question du remplacement ont des sources présentes : pertes par reformulation, rattachement ou refus collectif à distinguer.',
        '- Échec en licence / santé mentale : décrit dans la référence, mais absent des 670 passages figés ; ne pas compter cette suite comme omission démontrée du pipeline sur cet instantané.']
    write_new(destination/'diagnostic-24-refus.md','\n'.join(lines))
    print(json.dumps(report['categories'],ensure_ascii=True))


if __name__=='__main__': main()
