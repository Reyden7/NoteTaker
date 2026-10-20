# Laboratoire de synthèse directe 0.2.5

## Périmètre et activation

Expérience locale CPU, désactivée par défaut. Le pipeline du registre 0.2.4,
ses sources, corrections et révisions restent conservés. Aucune modification
Whisper/sherpa, aucun profil vocal. Pas de migration SQLite : schéma v5.
Les brouillons JSON ajoutent une provenance facultative `experimental_summary` ;
utiliser la nouvelle version pour les ouvrir. Voir le plan préalable dans
`direct-summary-0.2.5-plan.md` et les résultats effectifs dans `progress.md`.

Ne jamais marquer le dossier habituel `%LOCALAPPDATA%/NoteTaker` : les services
le refusent même avec un marqueur. Faire une sauvegarde SQLite cohérente dans
un nouveau dossier et conserver l'audio référencé. Le fichier
`EXPERIMENTAL-TEST-WORKSPACE.json` doit contenir un UUID et le motif :

```json
{"id":"un UUID à générer", "purpose":"direct-summary-test"}
```

Lancer `NoteTaker.exe --data-dir "CHEMIN_COPIE" --experimental-direct-summary`.
Sans activation explicite, aucun nouvel onglet n'apparaît. Le bouton habituel
de rédaction utilise toujours le registre. La copie contient des données
personnelles : la protéger et ne pas la distribuer avec l'application.

Dans **Laboratoire de synthèse**, choisir la longueur puis **Nouvel essai CPU
à froid**. L'ordre du jour et le lexique viennent des métadonnées de séance.
Le débat a un seul intitulé général, « Manif etudiante » ; ses sous-sujets sont
donc proposés par le modèle, sans prétendre disposer d'un ordre du jour détaillé.

Consulter les alertes par sujet, les paragraphes, toutes les informations et
rejets, toutes les sources/omissions. Écouter la source sélectionnée puis ouvrir
l'éditeur habituel pour corriger et confirmer explicitement la relecture.
Aucune approbation n'est créée par l'essai. Les décisions évoquées restent à
vérifier et saisir séparément ; aucun résultat de vote n'est déduit.

Une interruption garde requête, sorties et checkpoint. La reprise réutilise
uniquement les réponses ayant les mêmes prompt, schéma, budget, modèle et runtime.
Une modification des sources, noms, ordre du jour, lexique ou longueur interdit
la reprise de cette requête. Un résultat terminé est immuable : créer un nouvel
essai pour le remplacer.

**Rétablir cet essai comme nouveau brouillon — sans IA** réutilise un résultat
terminé dont les entrées sont toujours actuelles. Le brouillon courant reste
dans l'historique. Cette nouvelle révision perd toute approbation et doit être
relue ; zéro appel Qwen n'est présenté comme une nouvelle inférence.

## Traitement

### Contrat v5 après les essais réels

Le premier contexte v1 a demandé 403,986 s : 63,364 s d'évaluation de prompt,
337,294 s de génération, 2 315 tokens générés. Sur 7 667 caractères de sortie,
4 001 recopiaient les citations. Huit propositions ont été refusées : quatre
pour notation de voix incompatible, trois pour citations non remappables et
une par le contrôle des votes/adoptions. L'essai a été interrompu au contexte
suivant et reste conservé avec son code. **Ce n'est pas une mesure complète
sur 670 passages ni un résultat de qualité.**

Le contrat v2 fournit des extraits courts repérés par identifiant. Le modèle
sélectionne ces identifiants et rédige la prose ; le logiciel extrait ensuite
les citations littérales depuis les offsets enregistrés. Tous les caractères
non blancs restent fournis, dans les mêmes contextes longs. Le manifeste relie
chaque extrait aux segments originaux. Aucun passage initial ou final n'est
écarté pour accélérer.

Un code explicite `V2` est converti en gabarit `{{V2}}` uniquement s'il correspond
à la voix déclarée. Aucun sujet n'est ajouté à une phrase sans attribution ;
un code contradictoire reste refusé. La proposition brute est conservée.
Une reprise entre versions incompatibles est refusée avant remplacement des fichiers.

Les essais v2 et v3 ont révélé des répétitions en boucle, pas seulement un coût
de recopie : le premier contexte v3 a expiré à 900 s avec une phrase répétée
58 fois. Les essais incomplets et leurs sorties restent conservés et exclus
des mesures finales. Le contrat v4 explicite le format dans le prompt et conserve
chaque tour de parole avec ses références internes. Il a encore produit 46 phrases
partielles sur dix sujets après 723,675 s ; arrêt de ce seul test pour diagnostic.
La limite par sujet permettait de multiplier les sujets redondants. Cet essai
reste conservé et exclu des mesures complètes.

Le contrat v5 borne la **sortie du contexte entier** à 4, 7 ou 11 phrases selon
le profil, avec un sujet par phrase puis regroupement global. Tous les contextes
et textes sources continuent d'être fournis ; aucune sélection des premiers N
passages. Le nombre de sujets de la réunion n'est pas imposé. L'atteinte de la
limite déclenche systématiquement une alerte de couverture à examiner, même si
le modèle ne signale pas son budget. Le choix de longueur peut omettre des
informations : cet effet doit être évalué sur la référence humaine et ne doit
pas être présenté comme un gain de fidélité ou de couverture.

Une proposition strictement identique en texte, voix, type, origine, rubrique,
ordre du jour et citations reste dans le journal avec lien vers son doublon.
Elle ne reçoit pas une nouvelle vérification Qwen ni une seconde phrase rédigée.

Le décodage glouton est remplacé uniquement dans ce laboratoire par les valeurs
conseillées dans `models/llm/qwen3-4b-instruct-2507/README.md`, lignes 183–195 :
température 0,7, top-p 0,8, top-k 20, min-p 0, graine demandée 42. Les paramètres
sont enregistrés et participent à l'identité de cache. Le format illustre les
champs attendus sans préremplir le contenu de la réunion. Les listes de plan
sont bornées par le nombre réel de candidats. Cela ne démontre aucune qualité
sémantique ; la référence humaine reste nécessaire.

**Une référence sélectionnée peut être hors sujet. L'extraction exacte d'une
citation ne prouve jamais le soutien du sens.** Les contrôles statiques, les
contrôles Qwen ciblés provisoires et la relecture finale demeurent nécessaires.
Le mode municipal conserve l'exigence existante de rôle secrétaire pour
l'approbation ; une synthèse ne reçoit jamais l'étiquette transcription intégrale.

### Contextes, rédaction et inventaire

`domain/direct_summary.py` compacte les tours de la même voix puis constitue
des contextes de cinq minutes au plus et de 7 800 caractères environ. Un tour
pathologique est découpé avec ses offsets exacts. Aucun début/fin de réunion
n'est retiré pour accélérer. Le tour précédent est fourni comme contexte,
pas comme source à citer deux fois. Les blancs restent dans l'inventaire.

Le moteur rédige directement des phrases sourcées : contexte, arguments,
divergences, propositions, décisions potentielles. Un plan global regroupe et
ordonne leurs IDs sans réécriture. Chaque ID est retenu une fois ou écarté avec
motif. Un plan incomplet/dupliqué conserve les groupes locaux avec une alerte
visible ; cela ne valide pas leur pertinence.

Le premier rejeu complet v5 a effectivement rencontré ce défaut d'inventaire :
certains IDs apparaissaient plusieurs fois ou dans les retenus et les exclusions.
La réponse de plan utilise désormais `assignments`, avec une propriété obligatoire
par candidat : sujet `g`, point d'ordre du jour `a`, rang `o`, motif `why`. Une
exclusion impose un sujet vide et un motif non vide. Le logiciel reconstruit le
plan puis exécute encore `validate_dispositions` : aucun contrôle n'est supprimé.
Un rang identique garde l'ordre initial ; il n'implique aucune relation logique.
Les réponses brutes et toutes les exclusions restent conservées. Le sous-contrat
est inscrit dans les diagnostics. Le changement de prompt et de schéma invalide
le cache du plan ; il ne change pas les entrées des contextes.

Toutes les phrases passent les contrôles statiques existants : citations
exactes, même voix, modalités, montants, attribution, rôles acteur/patient,
identités, votes et cohérence narrative. Le contrôle LLM est groupé sur les
titres et affirmations risquées : chiffres, négations, questions, propos
rapportés, propositions, divergences, attributions incertaines. Les autres
phrases n'ont qu'un contrôle statique, sans soutien sémantique établi.
Une phrase refusée n'est pas automatiquement réécrite pour obtenir un avis
favorable : le refus et sa formulation restent dans le journal.

Les noms sont résolus depuis les libellés sauvegardés, le modèle ne reçoit que
des alias. Les alertes d'attribution incertaine restent présentes. La qualité
des voix du débat n'est pas validée par cette expérience.

L'inventaire garde le texte intégral et le texte hors citation de chaque
segment partiellement cité. Ces décomptes ne mesurent pas la couverture
sémantique. Le signal `budget_reached` déclenche une alerte, mais le modèle
peut ignorer ses omissions. Les longs plans dépassant le budget sont refusés
avec conservation des intermédiaires ; ils ne sont pas tronqués silencieusement.

## Provenance et export

Chaque essai conserve un `result.json` sous
`sessions/UUID/direct-experiments/UUID/` avec instantané des entrées, ledger et
profil. Le brouillon référence son empreinte et l'identité de la copie.
L'enregistrement normal, l'approbation et l'export vérifient l'intégrité du
fichier et l'actualité des sources, noms, ordre du jour et lexique. Une révision
inachevée reste sauvegardable sans devenir exportable. Les anciens documents
sans provenance nouvelle gardent les contrôles existants.

## Mesures

Le runtime conserve prompts/schémas/sorties/stderr et distingue inférences neuves
et reprises. Chaque appel a son temps écoulé et les temps CPU noyau/utilisateur
du processus llama ; agrégation par contexte, regroupement et contrôle.
Le benchmark du worker 0.2.4 conservé mesure le CPU de tout son arbre Windows,
y compris les descendants terminés. Quatre threads peuvent consommer plus de
secondes CPU que de secondes écoulées.

API : [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes),
[QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject),
[comptabilité des Jobs](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).
Un test de sous-processus réel vérifie l'inclusion des enfants terminés.

« À froid » : nouveaux processus, réponses applicatives absentes, aucun cache KV
conservé. Le cache disque Windows n'est pas purgé. Les benchmarks Qwen sont
séquentiels. Le poste n'est pas un laboratoire isolé : développement, tests et
compilation ont également utilisé le poste ; ne pas extrapoler un temps en garantie commerciale.
Séparer la préparation neuve 0.2.4 de sa rédaction depuis un registre déjà
contrôlé. Le coût humain et les anciens contrôles ne sont pas inclus dans cette
dernière mesure et ne doivent pas être présentés comme gratuits.

## Référence humaine et qualification

`scripts/prepare_direct_reference.py` prépare douze WAV de quarante secondes,
répartis sur le débat, la transcription et un formulaire JSON vierge. Aucune
réponse Qwen n'est affichée. L'utilisateur a accepté de les annoter. Renseigner
sujets, auteurs vérifiés, faits importants, modalités, relations et ambiguïtés
après écoute. Les scores restent indisponibles avant ces annotations.
Un échantillon ne mesure pas les omissions de toute la réunion : une référence
complémentaire sur le reste des vingt minutes est nécessaire.
La grille et les dénominateurs sont précisés dans
`direct-summary-human-evaluation.md`. La référence ne valide jamais un document
et ne déclenche aucun export.

Les tests automatisés utilisent des réponses **rédigées comme fixtures** pour
tester les contrats ; ce ne sont pas des mesures de qualité IA. Les rejeux natifs
sont rapportés séparément. Windows vierge déconnecté, qualification commerciale,
licences du payload final et installateur unique restent ouverts.

### Catalogue de sujets — ajustement en qualification

Le plan à clés obligatoires de `direct-cold-04` affecte vingt candidats à dix-neuf
sujets avant les contrôles. Son intégrité structurelle ne résout donc pas la
fragmentation. Cette mesure a terminé, ses sources et sorties restent conservées.

L'ajustement construit d'abord un catalogue de sujets partagés, puis
affecte chaque candidat à un indice de ce catalogue (ou à une exclusion motivée).
Les titres locaux sont des indications à réexaminer, pas des catégories immuables.
Un objet débattu peut réunir arguments opposés, questions et propositions ; un
domaine général ne permet toujours pas de fusionner des objets incompatibles.
Aucun quota arbitraire de sujets ni réduction des entrées. Les clés obligatoires,
le contrôle exhaustif des dispositions, les citations, les contrôles ciblés et
la relecture restent requis. `plan_from_catalogue` résout les indices et réutilise
`plan_from_assignments` puis le contrôle exhaustif `validate_dispositions`.
Les indices absents, négatifs autres que -1 ou incompatibles sont refusés.
Le premier sous-contrat `required-catalogue-assignments-v2` a été refusé lors de
l'essai réel : douze sujets, mais indices renvoyés jusqu'à quatorze. Aucun indice
n'a été deviné ou remappé ; le brut et le profil sont dans `group-catalogue-probe-01`.
Le sous-contrat actuel est `catalogue-then-required-assignments-v3` : un appel
établit le catalogue, puis un second utilise un enum limité aux indices réellement
créés. Ce coût supplémentaire est comptabilisé. Les intitulés locaux restent
dans le registre de génération et les contrôles, mais ne sont plus donnés comme
catégories au planificateur, qui reçoit le contenu de tous les candidats.
Sans migration SQLite ni modification des artefacts historiques ; les anciens
plans restent consultables. La version publique v5 reste compatible.
Un plan comportant au moins quatre candidats et une majorité de sujets à un seul
candidat déclenche une alerte de fragmentation : c'est un signal de relecture,
pas une mesure sémantique ni une obligation de fusionner.

**268 tests réussis en 8,79 s**, dont catalogue partagé, regroupement non consécutif,
exclusion motivée, indices invalides et fragmentation visible. Le bundle distinct
`dist/direct-summary-catalogue-final/NoteTaker` démarre, se ferme normalement et
contient les modèles locaux vérifiés. L'essai `group-catalogue-probe-02` termine
deux appels natifs en 162,528 s : vingt candidats affectés à deux sujets, sans
indice invalide, sans vérification sémantique complète ni création de brouillon.
Ce plan peut contenir des groupes trop larges ou mal classés ; ce n'est ni une
mesure de fidélité ni un temps complet à froid. Le rejeu complet `direct-cold-05`
a ensuite été exécuté avec un nouveau répertoire et ses contrôles ciblés.

### Résultat complet du dernier contrat — insuffisant

Sur les 670 mêmes passages : **1 844,612 s écoulées worker, 7 031,297 s CPU cumulées,
dix inférences neuves**, cinq contextes complets. Contextes : 966,522 s ; organisation
en deux appels : 162,641 s ; trois contrôles : 711,474 s. Aucun cache de réponses
réutilisé à froid. Rejeu distinct compilé : dix réponses en cache, zéro inférence,
2,470 s, résultat identique hors durée ; ne pas comparer ce temps au calcul neuf.

**Un seul paragraphe de neuf phrases**, 24 propositions refusées, 18 alertes.
Le contrôle de cohésion a refusé le deuxième sujet et ses onze candidats ; ils
restent consultables avec leur motif. 552 passages sans citation dans le document,
texte hors citation conservé : aucune mesure de couverture sémantique.
Le regroupement est structurellement cohérent mais la restitution est insuffisante.
Ni amélioration de fidélité, ni réduction du travail humain, ni gain de produit
démontrés. Le débat et son unique point d'ordre du jour général ne qualifient pas
un procès-verbal municipal. La référence humaine indépendante est la prochaine
étape d'évaluation ; ne pas multiplier les ajustements en les appelant validés.

Toutes les anciennes lignes SQLite sont identiques, 17 révisions de registre et
quatre brouillons précédents compris ; un brouillon non relu est ajouté. Les
22 421 caractères non blancs sont retrouvés dans les prompts réels, provenance
et citations valides, réouverture identique. Les deux exports réellement tentés
sans nouvelle relecture sont refusés. Les cinq vues Qt sur copie secondaire sont
inspectées visuellement ; aucune écoute audio n'est déduite de ces captures.

Lancer la copie avec `output/direct-summary/direct-cold-05/Ouvrir-NoteTaker-0.2.5.cmd`.
Lire `output/direct-summary/reference-humaine/A_LIRE_ET_ANNOTER.md` avant les réponses
Qwen de `output/direct-summary/comparaison-0.2.5.md`. Le formulaire reste vierge.
Windows vierge déconnecté et qualification commerciale demeurent non validés.
