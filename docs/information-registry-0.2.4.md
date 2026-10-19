# Registre des informations — 0.2.4.dev0

## Évolution d'architecture

Le plan préalable est dans `information-registry-plan.md`. La sélection de six
notes par fenêtre de 0.2.3 pouvait perdre un sujet avant même le catalogue
thématique. Les refus détaillés restaient principalement dans le dossier du
job. Le nouveau parcours sépare **préparation du registre**, **vérification
opérateur**, **rédaction**, puis **relecture finale du document**.

Les moteurs Whisper/sherpa, leurs modèles et leurs paramètres ne changent pas.
Qwen et llama restent locaux, CPU, sans nouvelle dépendance ni téléchargement.
L'ancien moteur `task=summary` demeure pour reproduire les preuves 0.2.3 ;
l'interface passe par `registry_prepare`, puis `registry_write`.

## Données et migration

SQLite v5 ajoute uniquement `information_registry` et un index. Chaque ligne
est une révision immuable complète avec séance, numéro, ID, empreinte source,
auteur, motif et date. La migration sauvegarde la base avant mise à niveau,
dans une transaction avec contrôle d'intégrité. Elle ne réécrit aucun ancien
brouillon ni aucune relecture. Un ancien exécutable v4 refuse une base v5 :
ne jamais diminuer manuellement `user_version`. Les essais utilisent des copies.

Le document de registre v1 conserve :

- Tous les segments originaux, y compris les blancs, avec texte, voix,
  horaires et métadonnées de correspondance audio.
- Une fiche source par segment, avec les candidats associés, le texte non
  représenté par leurs citations et le diagnostic d'extraction.
- Les informations : ID, sujet, type, auteur, état de l'attribution, contenu
  attribué, nature du discours, citations exactes, horaires de segment,
  vérification machine, état humain, motifs, origine et historique.
- Un graphe de relations directionnelles : réponse, accord, désaccord,
  objection, contexte. Les deux extraits doivent rester disponibles ; les
  opinions machine sont distinctes des confirmations humaines.
- Les omissions et refus de rédaction, sans effacer les informations.

Les IDs source sont déterministes par séance/segment ; les IDs d'information
sont ancrés aux sources, à la citation et au contenu candidat. Une répétition
identique réutilise l'ID. Une variante machine différente est une nouvelle
fiche reliée à la proposition initiale, qui reste conservée. Une correction
humaine conserve son ID et crée une révision. Cela ne constitue pas un
appariement sémantique parfait entre des reformulations différentes.

## Préparation et contrôles

1. Persister d'abord l'inventaire complet. Une erreur IA ne peut pas le faire
   disparaître. Le worker écrit des points de reprise atomiques ; les services
   les récupèrent en cas d'erreur ou d'annulation, sans écraser un registre
   modifié entre-temps.
2. Examiner toutes les unités de tours de parole, par petits lots. Le schéma
   exige une réponse pour chaque unité, même sans note. Il n'y a plus de
   sélection globale de six notes par fenêtre. La borne technique reste de
   quatre candidats par tour borné ; les résidus et la limite atteinte sont
   explicitement conservés, sans prétendre à une extraction exhaustive.
3. Résoudre les citations exactes sur la même voix. Les propositions restent
   en attente par défaut, ou refusées avec leur motif. Le contrôle approfondi
   se demande fiche par fiche : classifier séparément le propos original,
   puis proposer si nécessaire une variante depuis les seules citations.
   La première proposition et ses refus restent visibles. Pour devenir
   admissible automatiquement, la variante doit passer les contrôles
   déterministes et les quatre axes Qwen :
   sens, modalité, attribution, relation. Une question n'est pas une assertion,
   un avis cité n'est pas l'avis du rapporteur, une anecdote n'est pas une
   proposition officielle. Les contrôles financiers, d'identité et de rôle
   existants sont conservés.
4. Construire le plan thématique depuis les passages originaux de toute la
   transcription, puis rattacher les groupes d'intitulés provisoires au plan,
   y compris les doutes. L'extrait de classement peut être tronqué à 400
   caractères ; le registre conserve les textes et citations complets. Cette
   affectation provisoire n'est pas une validation de la pertinence du groupe.
   Un candidat erroné ne doit pas devenir la preuve d'un nouveau sujet. Un
   classement impossible reste « À classer ». Un classement humain est conservé.
   Les schémas bornent les propositions à quinze intitulés par bloc puis
   quarante au catalogue automatique. Cette borne peut aussi favoriser un
   regroupement excessif ; elle n'est pas une preuve de couverture. L'opérateur
   peut saisir d'autres sujets, sans supprimer les sources ou les fiches.
5. Proposer et contrôler les relations entre les informations déjà admissibles,
   par sujet, y compris après des interventions sur d'autres sujets, à partir
   des deux extraits et du contexte chronologique. La recherche est bornée à
   huit fiches par lot avec deux fiches de recouvrement ; elle n'est pas
   exhaustive sur toutes les paires du débat. L'opérateur peut
   également créer ou corriger les liens depuis les fiches à vérifier. Même
   sujet ou proximité ne prouve ni réponse ni consensus.
   Le graphe est consultable et corrigeable ; sa pertinence reste à qualifier.

Une vérification machine « supported » reste provisoire. Une information
inconnue, mal sourcée ou une décision potentielle ne devient pas une décision
municipale. Les décisions et votes restent saisis séparément. Les limites
conservatrices peuvent encore empêcher de rédiger une information fidèle.

## Services et rédaction

`RegistryService` assure les révisions, les modifications explicites avec nom
et motif, la consultation des versions et les conflits de concurrence. Une
source modifiée, fusionnée, scindée ou renommée rend le registre obsolète.
La nouvelle version conserve les anciennes informations à revérifier, et
les versions antérieures restent consultables. Aucun réentraînement vocal.

Une approbation humaine peut résoudre un doute de contenu, jamais une citation
absente ou une autre voix. Les contrôles statiques de rédaction continuent
de s'appliquer. Les corrections ne remplacent pas silencieusement les sources.

`Pipeline.generate` utilise uniquement le registre courant. Les dossiers sont
regroupés par sujet, avec des parties bornées à huit notes pour le contexte du
modèle, sans éliminer les parties suivantes. Les relations admissibles sont
transmises avec leurs références ; les titres du registre sont conservés et
contrôlés. Une phrase refusée entraîne encore le refus du paragraphe, après
deux tentatives au maximum. Les notes non reprises restent dans le registre.
Une relation traversant plusieurs parties reste dans le graphe ; sa restitution
dans la prose n'est pas garantie. Aucun gain de pertinence n'en est déduit.

Le brouillon référence l'ID et l'empreinte de sa révision de registre. Registre
et nouveau brouillon sont enregistrés atomiquement après contrôle de concurrence.
Une nouvelle révision de registre invalide le contexte du document lié, sans
effacer la relecture historique. Une ancienne provenance ou un registre obsolète
ne peut pas être rebaptisé courant pour autoriser l'export. Les documents
anciens sans registre restent utilisables avec leurs contrôles existants.

## Interface et usage

**Initialiser sans IA** crée immédiatement l'inventaire complet et ouvre les
sources intégrales. L'opérateur peut créer et vérifier ses fiches sans attendre
les calculs Qwen. La préparation automatique reste une action séparée et
coûteuse sur CPU ; elle n'est pas nécessaire pour utiliser le registre manuel.

Onglet **Registre des informations** : préparer/reprendre, rechercher un sujet,
une personne, un texte ou un ID, puis filtrer Tout / À vérifier / Admissibles /
Approuvées / Exclues / Sources intégrales / Non rédigées. Le détail expose le
contenu, le type et la nature du propos, les diagnostics, citations, voisins
chronologiques, accès audio, relations et historique.

Renseigner opérateur et motif, puis enregistrer une correction, approuver une
information vérifiée, l'exclure ou la remettre à vérifier. Modifier le sujet
déplace la fiche ; l'auteur est déduit des sources sélectionnées. Pour corriger
un nom, utiliser la transcription et l'annuaire, puis reprendre le registre.
Une fiche source reste immuable : son édition crée une information distincte.
Une correction de contenu ou de citation doit être enregistrée avant approbation.
Le bouton Rédiger utilise une synthèse, même si le précédent document était
une transcription intégrale. La préparation ne rédige pas automatiquement.

**Demander un contrôle Qwen de cette fiche** travaille sur la version
enregistrée. Une correction visible non sauvegardée bloque ce lancement.
Une fiche corrigée ou remise à vérifier par l'opérateur reste verrouillée :
le contrôle donne un avis consultatif, sans changer le choix humain. Une
demande explicite de nouvelle vérification retire l'information de la rédaction
automatique et invalide les opinions sur ses relations. Le service refuse
également un résultat IA qui remplacerait une information verrouillée.

La catégorie « À vérifier » contient aussi les résidus sources et les informations
non rédigées. Une fiche originale rejetée et sa variante peuvent coexister ;
les comptes désignent des fiches/candidats, pas autant de faits distincts.
**Approuver une information ne valide jamais le document final.**

## Recette et comparaison

Tests rapides : `tests/test_information_registry.py`,
`test_information_registry_ui.py`, `test_registry_pipeline.py`, plus la suite
existante. Les réponses IA des tests unitaires sont construites et déclarées
comme telles. Les widgets Qt et les exports de fixtures sont réels.

Le rejeu natif est `scripts/compare_information_registry.py`, sur une copie
isolée de l'instantané du débat : 670 passages, même texte/noms/horaires,
sans nouveau calcul audio. Les reprises utilisent seulement les réponses
dont prompt, schéma, modèle et budget sont identiques. Elles ne sont pas un
benchmark à froid. Les premiers essais interrompus volontairement sont
conservés, et ne sont pas décrits comme des plantages spontanés.

La comparaison distingue impérativement : inventaire physique conservé,
passages portant une citation candidate, informations admissibles/refusées,
relations et informations rédigées. **Aucun de ces comptes ne mesure la
couverture sémantique.** Pour qualifier les six dimensions demandées, annoter
indépendamment les sujets et unités de sens du débat, leurs auteurs et les
relations attendues ; comparer ensuite à la fois le registre et les paragraphes.
Les jugements de sens, de regroupement et de rédaction doivent être humains.
Sans cette annotation, les six scores restent « non mesurés ».

Le harnais `parallel_registry_field.py` répartit les lots indépendants entre
trois processus Qwen CPU locaux. Chaque requête worker conserve l'instantané
des 670 passages, nécessaire aux contrôles et à la réunion. Le prompt natif
d'extraction reçoit six unités bornées, pas toute la transcription ; le plan
lit des blocs de sources puis consolide les intitulés. Les relations et la
rédaction utilisent également des dossiers bornés. La réunion contrôle les empreintes sources, l'union des IDs et
l'examen de toutes les unités avant une seule planification globale. Aucun
résultat IA n'est remplacé par une simulation. Le produit reste séquentiel ;
ce harnais de recette ne qualifie pas un parallélisme de production.

Les résultats réels sont consignés dans `docs/progress.md` et
`evidence/information-registry-real-comparison.json`. La suite finale compte
226 tests réussis. Le premier worker compilé a exécuté un contrôle réel de fiche
(3 appels CPU, 53,732 s), sans changer les sources ni créer de relecture.
La correction finale d'interface remplace l'horaire fictif zéro par « À rattacher »
quand aucune citation n'est retrouvée. Un second correctif garde le contexte
historique des citations rejetées après correction de la transcription.
Ces deux cas ont leurs tests de non-régression. Après
recompilation, le worker a rejoué le contrôle avec trois réponses natives en
cache strict, zéro nouvelle inférence, résultat identique. Ses algorithmes
ont été comparés à ceux du worker ayant exécuté l'inférence fraîche ; aucune
ancienne réponse n'a remplacé le registre courant.
Les trois captures Qt actuelles ont été inspectées. L'égalité des modules
gelés et des sources est vérifiée dans les deux exécutables du bundle
`dist/information-registry/NoteTaker` ; son démarrage et sa fermeture ont été
testés sur le PC de développement. Les poids joints utilisent des liens NTFS
immuables ; ne jamais les modifier en place.

La préparation réelle conserve 670 segments et 354 informations/variantes
avant le contrôle supplémentaire d'une fiche. 508 segments portent une
citation candidate, 162 n'en portent pas mais gardent tout leur texte.
Les avis favorables déjà présents proviennent des premières vérifications
natives conservées pendant les essais. Une séance nouvelle démarre avec les
propositions en attente ; elle nécessite une vérification ou une approbation
explicite de fiches avant rédaction.
L'extraction a repris des réponses antérieures à identité vérifiée pendant
le développement ; elle ne constitue pas un benchmark intégral à froid des
sources finales. La vérification approfondie reste partielle, sur demande.
Deux reformulations que Qwen avait acceptées ont été signalées par la lecture
du développement et remises à vérifier, sans approbation humaine. Leur preuve
est `information-registry-agent-observations.json`. Aucun taux de précision
n'est déduit de ces observations.

La recette Windows vierge
déconnecté, la redistribution native et le Setup commercial restent ouverts.

### Résultat de la rédaction réelle et doutes conservés

46 nouveaux appels natifs CPU, 1 996,973 s ; 14 parties de 13 sujets examinés.
Le worker a accepté cinq paragraphes, neuf fiches, 30 segments cités. Le
brouillon archivé 0.2.3 comportait six paragraphes et 34 segments cités.
Ces comptes ne mesurent aucune amélioration de couverture ni de fidélité.
346 fiches/variantes ne sont pas rédigées dans cet instantané, toutes conservées.

La lecture du développement a révélé des regroupements incohérents malgré
les avis favorables de Qwen : propos sur salaire/emploi sous un sujet de
sélection universitaire, et une question vague sous un sujet de chiffres du
mouvement. Une faute de rédaction subsiste aussi. Huit fiches ont été remises
à vérifier sans approbation ni effacement ; le registre courant contient
355 fiches, 322 à vérifier, 33 admissibles avant rédaction. Le brouillon généré
reste consultable mais sa provenance est devenue obsolète après ces doutes.
Corriger/reclasser les fiches, puis régénérer et relire avant export.

La copie privée se lance par
`output/information-registry/field-670/Ouvrir-NoteTaker.cmd` ; ses liens audio
utilisent encore le fichier original. La comparaison lisible et les observations
restent dans ce même dossier. La qualité de classement, le traitement des
rejets techniques, le temps CPU et les six dimensions sémantiques restent
à améliorer/qualifier. L'architecture est implémentée ; ce résultat ne
constitue pas encore un compte rendu municipal fiable.
