"""Text comparisons to the user's references, NOT an audio annotation or a scorer."""

EXCERPTS={
 'E01':('Présentation de Louise par Sonia (§1).',
        'A et B conservent la présentation. A écrit Bordeaux-Montagne ; B écrit ici Bordeaux-Montaigne. Les deux déforment Manès Nadel. Les réponses brèves et retours de Sonia sont mêlés aux groupes de Louise : écouter les frontières. Le nom dans le texte ne constitue pas une identité reconnue.'),
 'E02':('Blocus de mars 2023, retour en septembre ; Louise et relance de Sonia (§2–3).',
        'Les deux conservent le récit. A écrit « grande graine » ; B « gangrène », cohérent avec la référence narrative. B rattache la fin de la question « de travailler tranquillement ? » au groupe de Louise. Attribution au mot près non validée par écoute.'),
 'E03':('Dénonciation par Louise de violences et du laxisme ; relance de Sonia (§3).',
        'A : « étoiléance », « s’envoi » ; B : « doléances », « sans voix », cohérents avec le récit humain. B sépare la relance avec SPEAKER_04 ; A conserve son début dans speaker_1. Ce sont des propos rapportés de Louise, pas des faits politiques validés par le laboratoire.'),
 'E04':('Arthur questionne le changement politique de Louise et son âge ; Louise répond (§4).',
        'La question et la réponse longue sont présentes. Dans les deux sorties, « J’avais 16 ans » porte le même groupe que la question d’Arthur, malgré la réponse de Louise indiquée par la référence. B transcrit Alain Finkielkraut ; A « à l’infin de quel compte ». Le récit humain ne suffit pas à certifier toutes les paroles brèves.'),
 'E05':('Récit de Louise à Bordeaux, agressions décrites et amis (§5).',
        'Les deux couvrent le récit, B écrit « rencontre des étudiants antifas » contre A « rends compte ». Les interruptions de Sonia sont fragmentées ; quelques mots de la question restent dans le groupe de Louise. L’orthographe Bordeaux-Montagne reste fautive dans les deux à cet endroit.'),
 'E06':('Lectures de Louise ; introduction de Manès par Sonia (§6).',
        'Le contenu principal est conservé. Manès Nadel devient « Manette Sandel » dans A, « Vanessa Nadel » dans B ; B écrit aussi « présidente ». Des mots de l’introduction de Sonia changent de groupe dans B. Les noms propres ne sont fiables dans aucun moteur sans correction.'),
 'E07':('Question de Sonia sur les moyens d’action ; refus par Louise de brûler un lycée (§7).',
        'Les deux restituent la position de Louise. B conserve « je ne dis pas que vous l’avez dit » : ne pas attribuer l’approbation des incendies à Manès. A écrit « Nelson demandait là », B « Nelson Mandela ». Les interruptions courtes exigent une écoute de référence.'),
 'E08':('Manès propose cours et ramassage une heure plus tard, puis solidarité (§8).',
        'La proposition concrète est présente dans A et B. A attribue le passage à speaker_2, également employé pour Arthur dans E04 : fusion incompatible avec les deux auteurs distincts du récit humain. B emploie SPEAKER_03 et conserve les propositions, mais la question de Sonia est découpée entre ses groupes et celui de Louise.'),
 'E09':('Intervenante évoquant ruralité/Outre-mer, puis accord partiel et objection de Louise (§9).',
        'B regroupe la plupart des propos de l’intervenante et Louise dans SPEAKER_00 : fusion contraire à la référence. A sépare speaker_0 et speaker_1, mais speaker_0 est aussi celui de Sonia ailleurs. A « 200 lycées » contre B « 200 lycéens » : différence de sens à contrôler ; pas de validation acoustique. L’identité exacte de la première intervenante reste à vérifier.'),
 'E10':('Accusations et contestations sur les organisations ; recentrage de Sonia (§10).',
        'Les accusations principales figurent dans les deux. A a plusieurs plages sans groupe et des répétitions ; B distribue davantage de paroles, mais attribue « Non, mais là, on n’est pas sur ce débat » au groupe de Manès utilisé en E08, alors que le récit décrit un recentrage de Sonia. « Je n’y appartiens pas » reste dans le groupe de Louise dans B : attribution suspecte, à écouter. Aucune accusation n’est certifiée comme fait.'),
 'E11':('Parcoursup : Manès, Arthur (premier arrivé), Bruno (tirage au sort). Correction humaine détaillée prioritaire sur le récit général (§11).',
        'Dans A complet, le groupe de Manès speaker_2 poursuit la remarque d’Arthur ; Bruno reçoit speaker_4. B complet distingue SPEAKER_03, SPEAKER_02 et SPEAKER_01 pour ces trois séquences, mais rattache des réponses brèves et une contestation au groupe de Bruno. Dans C trois minutes : S02 Manès, S03 Arthur, S04 Bruno, puis S05 « Absolument » et S06 une interruption : fragmentation à vérifier. A écrit Parcoursuc, B Parcoursup ; C « premier serviteur » contre référence « premier servi ».'),
 'E12':('Louise demande le remplacement de Parcoursup ; Manès centralisation des vœux et sélection sur les notes (§12 + correction humaine).',
        'A, B et C conservent la centralisation des vœux. A complet mêle certaines interruptions et perd des groupes à la fin. B complet écrit bien « notes » mais alterne artificiellement les groupes à l’intérieur de réponses (« vœux », « divers », « lettres »). Le B trois minutes écrit « noms », autre portée d’inférence : ne pas généraliser cette erreur au fichier complet. C trois minutes écrit « notes », mais S01 désigne ici Louise et désignait Sonia au début du même clip : fusion de voix. C écrit aussi « on approche Parcour sup » contre « on abroge Parcoursup ».')
}

DIAGNOSTICS=[
 {'id':'D01','scope':'A, fichier complet, E04/E08/E11','type':'attribution',
  'finding':'speaker_2 couvre des séquences attribuées à Arthur et à Manès par la référence humaine. Le nombre de cinq groupes ne prouve pas leur correspondance aux personnes.'},
 {'id':'D02','scope':'B, fichier complet, E09','type':'attribution',
  'finding':'SPEAKER_00 couvre la première intervenante et la réponse de Louise. Cinq groupes ne signifient pas cinq identités correctement séparées.'},
 {'id':'D03','scope':'C, trois minutes, début et 144–173 s','type':'attribution',
  'finding':'S01 couvre Sonia puis Louise ; six groupes incluent aussi des réponses courtes séparées. Le comptage sursegmente et fusionne simultanément.'},
 {'id':'D04','scope':'B, trois minutes / fichier complet, E12','type':'transcription_context',
  'finding':'Le mot « notes » humain devient « noms » sur le clip de trois minutes, mais est reconnu « notes » dans le fichier complet. La portée du contexte influe ; pas de score global déduit.'},
 {'id':'D05','scope':'B avec WhisperX, fichier complet','type':'alignment',
  'finding':'Texte ASR conservé à espaces près dans les quatre variantes. Dix segments sans alignement lexical complet restent à horaires approximatifs et signalés incertains. La disparition des durées nulles ne démontre pas une justesse des frontières.'},
 {'id':'D06','scope':'C, fichier complet','type':'technical_failure',
  'finding':'OutOfMemoryError CUDA au préremplissage SDPA : tentative supplémentaire de 15,96 GiB sur une carte 11,91 GiB. Aucun résultat complet C ; pas de découpage silencieux, ni troncature assimilée à une réussite.'},
 {'id':'D07','scope':'A/B/C','type':'reference_limit',
  'finding':'Comparaison textuelle à des documents humains, pas écoute manuelle par l’agent. Les répétitions, interruptions additionnelles et chevauchements sans annotation restent non vérifiés ; ils ne sont ni des récupérations prouvées ni des hallucinations établies.'}
]
