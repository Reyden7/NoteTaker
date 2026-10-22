# Rédaction municipale par sujet

## Audit du parcours précédent

Le contrat v3 demandait trois à six paragraphes sans inventaire des arguments
importants. La borne encourageait une sélection partielle. Le modèle choisissait
en même temps sujets, contenu et sources ; une proximité de sujets ne garantissait
pas leur cohérence. Le regroupement final exigeait l’égalité littérale des titres.
Le prompt donnait « La personne… » comme exemple à imiter. Les refus devenaient
des points de citations longues ; les raisons internes et identifiants sources
étaient ajoutés à `to_verify`, donc imprimés dans PDF et DOCX.

Une citation exacte prouvait le rattachement, pas la fidélité : le même Qwen
avait accepté des inversions de contexte. Le compte rendu omettait notamment
l’intention de vote, la banalité alléguée des ventes, plusieurs réponses et la
défense de la gestion antérieure. Les anecdotes et l’ironie étaient mal séparées
des arguments. Ces constats proviennent de la comparaison des textes disponibles,
pas d’une nouvelle écoute humaine de l’enregistrement.

## Modifications ciblées

1. Reconstruire les tours adjacents d’une même voix, sans fusionner un changement
   de voix, un chevauchement ou une plage de durée nulle. Garder les segments,
   textes, identifiants et horodatages d’origine dans chaque tour reconstruit.
2. Demander un plan de sujets et leurs identifiants sources sous forme compacte.
   L’ordre du jour, lorsqu’il existe, guide ce plan. Une consolidation bornée
   intervient en cas de doublons, de fragmentation ou d’oubli prioritaire, puis
   une reprise bornée traite les passages non classés. Dédupliquer une proposition
   de classement ne doit pas jeter ses nouveaux identifiants avec ses doublons.
   Les formules de séance strictement reconnues, fragments incomplets, passages
   non classés et informations restant à reprendre sont distingués, jamais effacés.
3. Rédiger un sujet à la fois. L’auteur du paragraphe est un identifiant distinct
   du texte, remplacé ensuite par le nom humain confirmé ou une voix inconnue.
   Qwen reçoit des alias ; le corps est rendu avec les noms confirmés et les
   bindings existants, sans l’étiquette Opinion/Argument ni « La personne ».
   Les opinions, faits évoqués et intentions gardent leurs modalités.
4. Contrôler les phrases internes séparément, puis les réunir dans le même sujet.
   Une conclusion ajoutée ne doit pas éliminer sa phrase voisine étayée. Les
   subordonnées ambiguës restent à contrôler, sans transformer une incertitude
   ou une négation du parent en affirmation. Conserver les contrôles de sources
   et de sens existants, plus un avis Qwen contextuel. Une formulation refusée reste dans le rapport de vérification.
   Le document indique brièvement qu’un argument nécessite une reprise ; il ne
   transforme pas le refus en longue citation brute ni en affirmation sûre.
5. Tenir un inventaire exhaustif des passages : repris par référence, importants
   à vérifier, secondaires proposés ou non classés. Un signal prioritaire dans
   une source dite secondaire la remet à examiner. Ces classes restent des avis
   machine : ni la fidélité ni la couverture sémantique ne sont mesurées ainsi.
6. Exporter uniquement prose et points de vigilance destinés au lecteur.
   Citations exactes complètes, horaires, refus, variantes et erreurs techniques
   sont séparés dans `verification-report.md` et `automatic-inventory.json`,
   accessibles depuis le bouton **Rapport de vérification**.

Des ancres textuelles conservatrices séparent les questions portant sur un objet
explicitement nommé, les demandes d’explicitation précédées d’un souhait du même
auteur, les déclarations de gestion avec honneur/probité et les intentions de vote
à la première personne. Deux reprises de formulation fixe
(demande de précisions et intention) sont signalées comme **règles textuelles**
dans l’inventaire ; elles ne sont pas présentées comme une découverte de Qwen.
Une citation d’autrui ou une négation ne crée pas d’intention positive. Aucun
« pour », « contre », résultat ou adoption n’est inféré de « je vais la voter ».
Ces ancres ne sont pas une compréhension générale du français ; elles sont
couvertes par des tests et restent soumises à la relecture habituelle.

Les notes d’incertitude Qwen restent dans le rapport : elles peuvent elles-mêmes
contenir une affirmation non étayée. Le document de lecture utilise des points
de vigilance courts, sans raisons techniques, alias de modèle ou codes internes.
La présentation compacte sans page de couverture forcée s’applique au seul
contrat éditorial v4 ; les exports historiques gardent leur présentation.

Pas de migration SQLite. Une nouvelle révision du brouillon est ajoutée par le
service existant. Anciens documents, registre et annotations conservés. Le contrat
v3 demeure lisible ; les exports officiels et leur relecture ne sont pas modifiés.
Qwen et les moteurs audio ne sont ni changés ni réentraînés.

## Points de comparaison préparés avant le résultat du nouvel essai

Liste d’analyse fondée sur la transcription existante, **pas référence humaine
indépendante**, et ne corrigeant aucun nom ou mot de la source :

| Élément à vérifier | Sources |
| --- | --- |
| Ventes présentées comme gestion ordinaire et non nouvelle politique | s2-0, s3-0, s34-0, s37-0, s38-0 |
| Comparaison de 200 000 euros de recettes avec 300 000 euros d’éclairage | s6-0 |
| Véhicules amortis et tractopelle de 1997, coût selon l’intervenante | s10-0, s11-0 |
| Intention de voter la délibération, sans résultat constaté | s13-0 |
| Critique de la communication et comparaison avec Laurent Wauquiez | s14-0, s16-0, s18-0 |
| Communication avant délibération et demande de vote préalable | s20-0, s22-0 |
| Demande d’explicitation du projet politique | s24-1, s27-0 |
| Demande de réponses sur RESS, sans inventer ce que désigne ce sigle | s28-0, s29-0, s30-0 |
| Ventes antérieures et absence de débat ou conférence à chaque fois | s39-0, s41-0 |
| Contestation d’insinuations, défense de la probité et choix associatifs | s44-0, s47-0, s49-0 |

La liste sert à relever les reprises, absences et déformations. Une revue de code
ou une analyse de texte par l’agent ne remplace pas la relecture humaine demandée
pour qualifier le sens, l’audio, les attributions et le nombre réel de corrections.
