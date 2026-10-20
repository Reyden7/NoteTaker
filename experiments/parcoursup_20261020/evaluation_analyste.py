"""Explicit analyst coding against independent human material, never Qwen-as-judge.

Entries are recorded only after reading the actual outputs. No model call here.
Exact means the named information is present, not that every generated claim is safe.
"""

EVALUATIONS = {
    'A-original': {
        'H01': ('déformé/partiel','questions[0]','Sélection taboue et relance présentes ; la demande de remplacement devient une question de suppression/pourquoi, sans restituer clairement « par quoi ». L’ASR original contient déjà « pourquoi ». Chaque Pourquoi supplémentaire n’est pas dans ces sources.'),
        'H02': ('exact avec réserve lexicale','arguments[1]','Parcoursup comme véhicule de sélection présent ; « sélection par parcours » est une approximation de sélection par formation.'),
        'H03': ('absent de la synthèse','citations_sources T002/T003/T005','Histoire premier arrivé/tirage au sort seulement dans le catalogue recopié. Pas d’argument structuré, d’objection d’Arthur ni de doute de Bruno restitué.'),
        'H04': ('exact','questions[0]','La relance de la présentatrice sur injustice/angoisse est présente.'),
        'H05': ('exact','propositions[0]','Ouverture de dizaines de milliers de places explicite.'),
        'H06': ('exact, portée condensée','propositions[0]','Sectorisation des vœux explicite ; réserve « dans certains endroits » non restituée.'),
        'H07': ('exact','propositions[0]','Garantie de formation, droit donné comme exemple.'),
        'H08': ('exact','arguments[2]','Inadéquation candidats/places bien restituée.'),
        'H09': ('exact','questions[1]','Question du remplacement posée par Louise présente, avec graphie erronée de l’entrée A conservée.'),
        'H10': ('exact mais rubrique incohérente','propositions[1]; questions[3]','Centralisation des vœux enfin explicite comme proposition ; la même réponse est aussi classée parmi les questions.'),
        'H11': ('présent, relation déformée','arguments[5]; desaccords[0]','L’exemple russe figure sous l’auteur Louise. Le désaccord réel porte sur le caractère faible de la sélection et les critères ; le texte de désaccord le remplace par une interrogation générale sur la pertinence du système.'),
        'V01': ('déformé/partiel','arguments[4]; arguments[6]; questions[4]; desaccords[1]','Réponse unique de Manès scindée entre deux étiquettes et décrite comme désaccord. Exception des formations utilisant la lettre absente du relevé. T017 seul ne contient pas les notes, malgré ces affirmations sourcées uniquement T017.'),
        'V02': ('absent','desaccords','Réaction interrogative incrédule de Manès absente ; attribution initiale erronée dans A et fin de phrase fragmentée.')
    },
    'B-corrigee-humaine': {
        'H01': ('déformé/partiel','questions[0]','Projet de société/école et relance pratique présents, mais la question sur sélection taboue et celle du remplacement ne sont pas restituées pour Sonia.'),
        'H02': ('présent, généralisation ajoutée','arguments[0]; arguments[1]','Véhicule de sélection et extension aux formations non sélectives présents ; « pas une innovation » est une généralisation ajoutée et brouille cette extension.'),
        'H03': ('présent mais relations déformées','arguments[3]; arguments[4]; desaccords[1]','Arthur et son exemple sont enfin nommés correctement, ainsi que le rappel de Bruno. Mais le modèle invente ensuite une position de Manès sur le tirage au sort et change le doute personnel de Bruno en jugement d’inefficacité.'),
        'H04': ('exact','questions[0]','Relance explicite sur injustice/angoisse. Source T006 existante, mais citation littérale T006 absente du catalogue demandé.'),
        'H05': ('exact','propositions[0]','Dizaines de milliers de places présentes.'),
        'H06': ('exact, portée condensée','propositions[0]','Sectorisation présente, sans la restriction « dans certains endroits ».'),
        'H07': ('exact','propositions[0]','Garantie pour les bacheliers, licence en droit donnée comme exemple.'),
        'H08': ('exact, mauvaise catégorie','propositions[2]','Inadéquation candidats/places fidèle, mais diagnostic classé comme proposition.'),
        'H09': ('exact, citation manquante','questions[1]','Question de Louise fidèle ; T008 existe dans l’entrée, mais manque dans le catalogue des citations.'),
        'H10': ('déformé, position inventée','propositions[1]','La réponse sur une plateforme avec vœux centralisés devient une obligation de conserver Parcoursup. « Il ne doit pas être supprimé » est absent de T009 et ne découle pas de « supprimer ne suffirait pas » dans T007.'),
        'H11': ('présent, relation déformée','arguments[5]; desaccords[0]','Anecdote correctement donnée comme argument de Louise ; la ligne de désaccord attribue toutefois à Manès la sélection faible affirmée par Louise.'),
        'V01': ('exact sur le principal, exception absente','arguments[2]; incertitudes[2]','Critère principal notes présent et attribué à Manès. Exception des lettres de motivation non restituée en argument. L’incertitude transforme sa réponse en débat indifférencié sur notes/lettres.'),
        'V02': ('inversion de position','questions[2]; desaccords[0]','La réaction incrédule de Manès est perdue. La question de Louise devient « devenue très grande », puis le modèle attribue la sélection faible à Manès au lieu de Louise.')
    },
    'C-corrigee-contexte': {
        'H01': ('déformé/partiel','questions[0]','Projet de société/école présent, mais remplacement transformé en justification de suppression et sélection taboue omise.'),
        'H02': ('exact sur le principal','arguments[2]','Parcoursup comme outil de sélection, distinct du problème global, bien présent. La remarque sur la moindre capacité est traitée ailleurs.'),
        'H03': ('présent, relations ajoutées','arguments[4]; arguments[5]; desaccords[1]; desaccords[3]; incertitudes[4]','Arthur et Bruno correctement distingués dans les arguments. Le modèle ajoute une opposition/distance avec Manès, puis affirme que Manès conteste la pertinence du rappel d’Arthur : aucune réponse de ce type n’est fournie.'),
        'H04': ('exact, citations manquantes','questions[0]','Relance injustice/angoisse présente. T016/T021 existent, mais ne sont pas cités littéralement dans le catalogue.'),
        'H05': ('exact','propositions[0]','Dizaines de milliers de places explicites.'),
        'H06': ('exact, portée condensée','propositions[0]','Sectorisation explicite, restriction locale absente.'),
        'H07': ('présent, condition omise','propositions[0]','Licence en droit présente, mais le souhait du bachelier et le statut d’exemple ne sont pas explicités ; la garantie devient générale dans cette formulation condensée.'),
        'H08': ('exact','arguments[6]','Déséquilibre entre demande et places bien restitué dans les arguments.'),
        'H09': ('partiellement exact, puis déformé','questions[1]; propositions[2]','« Vers quoi » conservé après « pourquoi abroger », mais sa vraie question de remplacement est ensuite transformée en proposition d’abrogation.'),
        'H10': ('absent, remplacé par un contresens','desaccords[2]','Centralisation des vœux absente du relevé. T024 contient pourtant la réponse exacte. La sortie lui substitue des solutions « sans abroger le système », non soutenues.'),
        'H11': ('présent, généralisation ajoutée','arguments[0]; arguments[8]','Anecdote de Louise présente ; « sans critères réels de qualification » généralise le cas allégué. L’argument sur les filières censées non sélectives est ajouté à Louise alors que ce thème était porté par Manès ailleurs.'),
        'V01': ('exact mais rubrique incohérente','arguments[3]; questions[7]','Critère principal et exception de certaines lettres explicitement restitués. La même réponse est aussi transformée en question.'),
        'V02': ('déformé','questions[6]; desaccords[0]','La réaction incrédule est reprise comme question orientée vers une sélection déjà faible. Surtout le modèle ajoute que Manès défend Parcoursup, alors que décrire ses critères ne vaut pas adhésion à cet outil.')
    }
}

ANOMALIES = {
    'A-original': [
        {'classification':'relation inventée','path':'desaccords[1]',
         'reason':'Le relevé oppose Intervenant 3 et non-attribué sur les notes. La copie humaine attribue les deux fragments à Manès, qui tient un seul propos ; aucune opposition de ces deux voix ne figure même dans les textes A.'},
        {'classification':'rattachement insuffisant','path':'arguments[4]; questions[4]',
         'reason':'T017 ne dit pas que la sélection se fait sur les notes : cette précision est dans T018, non cité par ces deux éléments. Zéro erreur littérale ne signifie donc pas source complète.'},
        {'classification':'mauvaise catégorie','path':'questions[3]; questions[4]',
         'reason':'La plateforme de remplacement et la réponse sur les notes sont des réponses, pas des questions.'},
        {'classification':'attribution de référence incohérente','path':'participants[3]',
         'reason':'L’étiquette non-attribuée référence aussi T008 dont l’auteur d’entrée est BFMTV test.'},
        {'classification':'consigne de concision non suivie','path':'citations_sources',
         'reason':'Les 18 tours sont intégralement recopiés malgré la demande de citations courtes. C’est une cause observable de volume de sortie, pas une preuve de couverture sémantique.'}
    ],
    'B-corrigee-humaine': [
        {'classification':'position inventée / contresens','path':'propositions[1]',
         'reason':'« Parcoursup ... ne doit pas être supprimé » ne figure pas dans la réponse T009. Le texte humain parle d’une plateforme de remplacement avec centralisation des vœux. La réserve T007 sur la suppression insuffisante ne justifie pas le maintien.'},
        {'classification':'inversion d’auteur et de position','path':'desaccords[0]',
         'reason':'Le modèle écrit que Manès juge la sélection faible. T010 attribue cette opinion à Louise ; T011 contient justement la réaction incrédule de Manès, omise de ce désaccord.'},
        {'classification':'relation et opinion inventées','path':'desaccords[1]',
         'reason':'T005 n’a que Bruno : son doute sur le bon système ne soutient ni une position de Manès sur le tirage au sort ni l’affirmation que Bruno le jugerait inefficace.'},
        {'classification':'question déformée','path':'questions[2]',
         'reason':'« La sélection est-elle devenue très grande » ne restitue pas « Donc plus de selection ? » et la suite « beaucoup moins ... pas très grande ». La modalité du mot plus peut être ambiguë isolément, pas le sens explicite de la suite.'},
        {'classification':'attribution de référence incohérente','path':'participants[1]',
         'reason':'Manès référence T003 (Arthur) et T005 (Bruno) malgré les libellés humains explicites. Arthur apparaît dans arguments[3], mais manque dans la liste des participants.'},
        {'classification':'incertitude nominale insuffisamment conservée','path':'participants[2]; arguments[4]',
         'reason':'Le patronyme « Jodir » fourni comme incertain devient une partie du nom présenté, statut « nom fourni ». L’incertitude est bien mentionnée en fin de sortie, mais les rubriques principales devraient garder Bruno / nom à confirmer.'},
        {'classification':'catalogue incomplet','path':'citations_sources',
         'reason':'T006, T008 et T011 sont référencés ailleurs mais non cités dans le catalogue : cinq éléments concernés par l’audit mécanique. Ce sont des sources existantes, pas des IDs inventés.'}
    ],
    'C-corrigee-contexte': [
        {'classification':'lien politique inventé et hors fenêtre','path':'arguments[1]',
         'reason':'La phrase générée lie abusivement l’organisation de Parcoursup aux accusations politiques du contexte T011. T011 concerne un échange antérieur sur une organisation et n’établit aucun lien avec Parcoursup. Cette assertion Qwen n’est pas un fait. Aucun passage focal n’est cité.'},
        {'classification':'question transformée en proposition','path':'propositions[2]',
         'reason':'T023 dit « pour quoi ... on va vers quoi ... vraie question ». Il ne dit pas que Louise propose d’abroger Parcoursup. Le modèle transforme une demande d’explication en position normative.'},
        {'classification':'proposition inventée','path':'propositions[1]',
         'reason':'« Rétablir un système ... fondé sur les notes » n’est pas proposé dans T022. Même T028, qui décrit les critères existants, ne serait pas une preuve d’une proposition de rétablissement.'},
        {'classification':'position inventée / contresens','path':'desaccords[2]',
         'reason':'« Sans abroger le système » n’est ni dans la question de Louise T023 ni dans la réponse sur une plateforme centralisant les vœux T024. La proposition explicite de centralisation est perdue.'},
        {'classification':'adhésion inférée sans preuve','path':'desaccords[0]',
         'reason':'Le modèle écrit que Manès défend Parcoursup parce qu’il explique les notes. Décrire le critère principal ne démontre aucune adhésion politique ou normative à l’outil.'},
        {'classification':'opposition et réponse ajoutées','path':'desaccords[1]; desaccords[3]; incertitudes[4]',
         'reason':'Un seul tour d’Arthur puis un seul tour de Bruno ne démontrent pas les réactions attribuées à Manès. L’absence de ralliement explicite ne suffit pas à créer un désaccord ; le dernier doute de sortie invente une contestation de Manès sur le rappel d’Arthur.'},
        {'classification':'attribution/contextualisation déformée','path':'arguments[8]',
         'reason':'Le thème des formations censées non sélectives est dans T022 de Manès, pas les sources T025/T027 de Louise données pour cette phrase. La « sélection non garantie » et l’équité ne sont pas établies par ces deux sources.'},
        {'classification':'citation non littérale','path':'citations_sources[0]',
         'reason':'T004 se termine sur « 24 » ; « heures. » appartient au tour T005, autre libellé de voix. Le modèle complète la citation tout en gardant uniquement T004.'},
        {'classification':'participants hors fenêtre et identité incertaine','path':'participants[4]; participants[5]',
         'reason':'BFMTV test et non-attribué ne citent que le contexte antérieur et ont le statut nom fourni. La présentatrice Sonia nommée dans les questions focales manque dans la liste, tandis que les libellés du contexte créent des entrées distinctes.'},
        {'classification':'rattachements/citations incomplets','path':'literal-audit.json',
         'reason':'Huit signalements mécaniques : une citation complétée, des références sans citation littérale et des éléments sans source focale. Le brut reste intégralement conservé.'}
    ]
}
