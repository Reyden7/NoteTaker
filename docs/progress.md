# Avancement NoteTaker 0.2 — qualité en évaluation

Dernier lot sources : **0.2.5.dev0, laboratoire de synthèse directe en qualification**.
Plan préalable : `direct-summary-0.2.5-plan.md` ; utilisation et limites :
`direct-summary-0.2.5.md`. Le parcours 0.2.4 et le schéma SQLite v5 sont conservés.

## Bilan actuel — expérimentation livrée, résultat rédactionnel insuffisant

Bundle de travail : **`dist/direct-summary-catalogue-final/NoteTaker`**.
Lancement sur la copie du débat :
`output/direct-summary/direct-cold-05/Ouvrir-NoteTaker-0.2.5.cmd`.
Le laboratoire reste facultatif, réservé à une copie marquée ; le parcours 0.2.4
reste disponible. Aucun changement Whisper/sherpa, aucune biométrie, aucune migration
SQLite supplémentaire et aucune approbation de séance créée par ces essais.

Dernier test complet CPU, **mêmes 670 passages**, profil standard, réponses absentes
et processus neufs (`direct-cold-05`) : **1 844,612 s écoulées worker (30 min 45 s),
7 031,297 s CPU cumulées, 10 appels neufs**. Source du moteur inchangée pendant
la mesure. Étapes natives : contextes 966,522 s / 5 appels ; catalogue et affectation
162,641 s / 2 appels ; contrôles ciblés 711,474 s / 3 appels. Cache disque Windows
non purgé ; le poste de développement n'est pas un laboratoire isolé.

Résultat : **33 propositions, 24 refus, 1 paragraphe de 9 phrases, 18 alertes**.
Le catalogue affecte vingt candidats à deux sujets sans incohérence d'indices.
Le contrôle machine refuse le sujet « Sélection universitaire et accessibilité »
et ses onze candidats pour cohésion insuffisante ; cela ne prouve pas que chacun
de ces propos est faux. Les textes, références et motifs restent dans le journal.
**552 passages ne sont pas cités** et 553 contiennent du texte hors citation ;
ce comptage n'est pas une mesure de couverture sémantique. La synthèse est très
incomplète : **objectif rédactionnel non atteint, aucun gain de fiabilité ni de
temps humain annoncé**. Le temps légèrement inférieur à la rédaction seule 0.2.4
ne démontre pas un gain de produit avec une restitution aussi différente.

Comparaison détaillée : **`output/direct-summary/comparaison-0.2.5.md`** et JSON.
Rédaction seule 0.2.4 : 1 985,427 s, 46 appels, cinq paragraphes, depuis l'ancien
registre déjà travaillé ; préparation/anciens contrôles exclus. Préparation neuve
0.2.4 mesurée séparément : 3 750,575 s, 45 appels, 270 éléments à vérifier, zéro
encore admissible. Ne pas additionner ces mesures issues de registres différents
en les présentant comme un parcours complet mesuré.

Vérifications réellement exécutées :

- **268 tests automatisés réussis en 8,79 s** au gate de compilation ; fixtures
  explicitement rédigées, exports PDF/DOCX et réouverture avec relecture de fixture.
- Exécutables compilés conformes aux sources testées ; modèles et runtime locaux
  vérifiés, démarrage/fermeture Windows normaux. Rejeu compilé des 670 passages :
  **zéro appel neuf, dix réponses réutilisées, 2,470 s**, résultat identique hors
  durée. Ce rejeu n'est pas une mesure à froid.
- Toutes les anciennes lignes de chaque table SQLite comparées et identiques,
  dont les 17 registres et quatre anciens brouillons ; un seul brouillon ajouté.
  Même état après fermeture/réouverture ; base source inchangée.
- **22 421 caractères non blancs** des 670 sources retrouvés dans les cinq prompts
  réellement envoyés ; voix sauvegardées conservées. Provenance/citations valides.
  Exports PDF et DOCX sans nouvelle relecture réellement tentés et refusés ; aucun
  fichier de séance non relue créé.
- Cinq vues Qt réelles capturées sur copie secondaire et inspectées visuellement ;
  aucune écoute audio manuelle effectuée par ce contrôle visuel.
- Douze extraits de 40 s comparés octet par octet au PCM original ; formulaire
  inchangé, **zéro annotation humaine**. Modules 0.2.4 et fonctions ASR/diarisation
  comparés au worker conservé : inchangés.

Preuves : `evidence/pytest-direct-summary.xml`,
`evidence/direct-summary-real-comparison.json`, `evidence/direct-summary-field-preservation.json`,
`evidence/direct-summary-frozen-replay.json`, `evidence/direct-summary-field-ui.json`,
`evidence/direct-summary-bundle-sources.json`, `evidence/direct-summary-preserved-engines.json`.
Les essais incomplets, refusés et versions précédentes restent conservés ci-dessous.

Référence indépendante prête : **`output/direct-summary/reference-humaine/A_LIRE_ET_ANNOTER.md`**.
Annoter avant de lire les réponses Qwen comparées ; les douze extraits ne suffisent
pas à mesurer toutes les omissions des vingt minutes. Fidélité, erreurs
d'attribution, inversions de sens et pertinence des groupes : **non mesurées**.
Le débat et son ordre du jour très général ne valident pas un PV municipal réel.
La suite utile est cette annotation, puis une évaluation des regroupements et des
omissions ; ne pas poursuivre les ajustements aveugles en annonçant des gains.

Produit non terminé : recette sur Windows vierge déconnecté, qualification
commerciale des dépendances (dont la réserve `cudnn64_9.dll`), installateur unique
et qualité rédactionnelle réelle restent ouverts.

## Lot 0.2.5.dev0 — travaux du 19 octobre 2026

Implémentation séparée, activée uniquement avec option CLI et copie de données
marquée. Contextes longs couvrant toutes les entrées, rédaction par sujet,
regroupement sans réécriture des phrases et contrôles ciblés. Conservation des
candidats, refus, omissions et textes hors citation. Provenance vérifiée avant
approbation/export ; aucune approbation automatique. L'interface permet de
consulter l'inventaire, écouter les passages et reprendre un essai interrompu.
Whisper et sherpa ne sont pas modifiés ; aucune biométrie.

Premier passage de suite complète : **239 tests réussis en 10,23 s**,
`docs/evidence/pytest-direct-summary-initial.xml`. Les premiers essais ciblés
avaient révélé deux erreurs dans les tests (nom d'une méthode de stockage et
nombre de processus créé par le lanceur Python Windows), corrigées avant ce
passage. Les fixtures ne constituent pas une validation de qualité IA.

Rejeux CPU natifs comparatifs **en cours** sur les 670 mêmes passages, avec
le worker 0.2.4 préservé et des répertoires de réponses neufs. Temps/appels et
résultats finaux à compléter ; aucun gain annoncé à ce stade.
Le premier essai `legacy-cold-01` a été interrompu après 41 appels terminés
(1 706,909 s au dernier point de mesure) par WinError 5 lors du remplacement du
rapport de mesure. Il est conservé et **exclu des mesures complètes à froid**.
Le remplacement JSON atomique attend désormais brièvement les lecteurs Windows
qui n'autorisent pas la suppression ; il ne tronque jamais l'ancien fichier.
Un test avec un vrai handle Windows sans partage de suppression passe.
Le nouveau rejeu `legacy-cold-02` utilise un répertoire neuf.

Suite complète au lancement de compilation : **247 tests réussis en 9,08 s**,
`docs/evidence/pytest-direct-summary.xml`. Compilation de développement en cours
avec analyse PyInstaller actuelle et partage NTFS uniquement des dépendances
dont les empreintes correspondent. Le poste a 14 cœurs physiques / 20 logiques ;
le build et le développement ne sont pas isolés des mesures. Les inférences
Qwen entre pipelines restent séquentielles ; ces temps ne sont pas des garanties.

La référence de **rédaction seule 0.2.4** a terminé sur les 670 passages :
**46 appels Qwen, 1 985,427 s écoulées, 7 539,547 s CPU cumulées** dans l'arbre
du worker. Préparation du registre et contrôles antérieurs exclus de cette mesure.
Rapport : `output/direct-summary/legacy-cold-02/report.json`.

Le premier essai direct v1 est **incomplet et exclu de la comparaison finale**.
Premier contexte : 403,986 s, 8 propositions toutes refusées (4 notations de
voix, 3 citations non remappables, 1 contrôle vote/adoption). Les citations
recopiées occupaient 4 001 des 7 667 caractères de sortie. Arrêt contrôlé du
processus natif pendant le contexte suivant ; source, registre et historique
inchangés. Code et résultats v1 conservés dans `output/direct-summary/direct-v1-code`
et `direct-cold-01`. Ce n'est pas une mesure complète de 670 passages.

Contrat v2 : références à des extraits indexés, extraction déterministe des
citations exactes et normalisation du code de voix explicite correspondant,
sans inventer de sujet. Tous les contrôles restent appliqués ; la présence
d'une citation ne prouve pas la fidélité. La reprise entre contrats incompatibles
est refusée. Le mode municipal conserve la validation par secrétaire.
**257 tests réussis en 8,59 s** : `docs/evidence/pytest-direct-v2-initial.xml`.
Le rejeu v2 `output/direct-summary/direct-cold-02` a été arrêté pendant le
premier contexte après 893,158 s : sortie inachevée, 54 phrases proposées mais
21 textes distincts seulement. Aucune synthèse exploitable ni relecture créée.
Le test de contrat v3 a atteint le délai de 900 s : 63 phrases partielles,
dont une répétée 58 fois. Les sorties partielles, profils et versions de code
v2/v3 restent conservés. Ces essais sont **exclus des comparaisons complètes**.

Contrat v4 testé : tours de parole conservés avec références
internes, format JSON illustré, longueur de paragraphe bornée selon les trois
profils existants (4/7/11 phrases), sans retirer aucune entrée source. Décodage
`temperature=0.7, top_p=0.8, top_k=20, min_p=0` selon la fiche locale du modèle
Instruct-2507, au lieu du décodage glouton qui boucle réellement ici. Ces
paramètres font partie de l'identité de cache. Une limite de sortie ne prouve
ni la fidélité ni la couverture : le texte complet reste dans l'inventaire.
Les expirations conservent désormais les sorties natives partielles et le CPU.
**259 tests réussis en 16,14 s**, avant les tests additionnels de bornage et
d'expiration : `docs/evidence/pytest-direct-v4.xml`.
La suite a ensuite passé **263 tests en 9,86 s**. Le test natif v4 a été arrêté
à 723,675 s : 46 phrases partielles, 42 textes distincts et dix sujets, dont
des sujets redondants et des formulations douteuses. La limite par sujet ne
bornait pas le volume total. Preuves des essais refusés/interrompus :
`evidence/direct-summary-contract-failures.json` ; aucun gain de qualité déduit.

Contrat v5 en test natif : budget de **sortie par contexte entier**, 4/7/11
phrases selon la longueur, même transcription intégrale fournie, regroupement
global par sujet. Une limite atteinte crée une alerte de couverture même si
Qwen ne la signale pas. Ce changement de longueur peut omettre des informations
et doit être évalué ; il ne prouve aucune amélioration de couverture. Les
doublons stricts restent conservés avec leur motif et leur lien, sans nouveau
contrôle Qwen. Tests ciblés : **37 réussis en 3,28 s**,
`evidence/pytest-direct-v5-initial.xml`.
Le test natif de contrat v5 a terminé **un seul contexte en 195,249 s** :
7 propositions, 4 refus statiques (1 nom propre non soutenu, 3 références de
voix incohérentes), 3 candidats avant contrôle ciblé. Aucun avis de qualité
ni brouillon approuvé. Les 670 entrées restent dans la requête ; ce test ne
traite pas toute la réunion. Preuve :
`output/direct-summary/context-v5-probe-01/probe.json`.
Suite complète v5 : **264 tests réussis en 8,67 s**,
`evidence/pytest-direct-v5-all.xml`. Essai intégral neuf lancé dans
`output/direct-summary/direct-cold-03`, sans réutiliser la réponse du probe.
Une compilation finale distincte est lancée pendant cette mesure : poste non
isolé, CPU par arbre de processus mesuré séparément ; ne pas extrapoler le
temps écoulé à une garantie sur un autre poste.
Compilation finale effectuée : **264 tests réussis en 10,26 s** au gate de build,
analyse PyInstaller actuelle, 529 fichiers de dépendances partagés uniquement
après égalité d'empreinte, 2 ressources actuelles copiées. Dossier :
`dist/direct-summary-final/NoteTaker`. Les poids et le runtime CPU locaux sont
attachés et vérifiés sans téléchargement ; ne pas modifier ces fichiers partagés.
Les deux exécutables correspondent aux sources testées, schéma JSON compris.
Le démarrage compilé avec laboratoire, fenêtre réactive et fermeture normale
réussit sur une base de test vide du poste de développement. Preuves :
`evidence/direct-summary-bundle-sources.json`,
`evidence/direct-summary-final-desktop.json`,
`evidence/direct-summary-shared-build.json`.
Audit natif : 292 PE, aucun composant optionnel interdit, présence conservée
de `cudnn64_9.dll`. Cet inventaire ne vaut pas autorisation de redistribution :
les réserves commerciales et la recette Windows vierge déconnecté restent ouvertes.

### Premier rejeu intégral v5 et correction du plan

`direct-cold-03` a terminé : **9 appels neufs, 1 932,561 s écoulées worker,
7 611,828 s CPU cumulées**, 33 propositions, 15 refus, 18 paragraphes et 25
alertes. Les 5 contextes ont tous été traités. Reprise séparée : **0 appel neuf,
9 réponses réutilisées**, résultat identique hors durée mesurée. Le rejeu du
worker compilé sur ces caches réussit également ; ce n'est pas une mesure à froid.

Le plan global était cependant **invalide** : IDs présents dans plusieurs sujets,
répétés dans un sujet, ou à la fois retenus et écartés. Le contrôle a bien refusé
ce plan, puis conservé les groupes locaux. Les 18 paragraphes d'une seule phrase
ne satisfont donc pas l'objectif de regroupement global. Cet échec fonctionnel
est conservé dans `output/direct-summary/comparaison-v5-plan-listes.md`, avec les
prompts, sorties, profils, code source et ancien bundle. Aucun gain de vitesse
significatif ni de qualité annoncé : le temps reste proche des 1 985,427 s de
rédaction seule 0.2.4 et le CPU est légèrement supérieur ; les périmètres diffèrent.

Audit réel : **22 421 caractères non blancs** retrouvés dans les cinq prompts
effectivement envoyés à Qwen ; tous les libellés de voix sauvegardés sont conservés.
Chaque ancienne ligne de toutes les tables SQLite est identique, y compris les
17 révisions de registre et les 4 anciens brouillons ; un seul nouveau brouillon
est ajouté. Réouverture identique. Les contrôles de provenance et de citations
du nouveau brouillon passent. Les deux exports réels tentés sont refusés pour
absence de relecture humaine ; aucun PDF/DOCX de séance non relue n'est créé.
Preuves conservées : `evidence/direct-summary-v5-array-plan-preservation.json`
et `evidence/direct-summary-v5-array-plan-frozen-replay.json`.

Correction en qualification : une clé obligatoire par ID de candidat dans la
réponse de regroupement. Chaque clé affecte un sujet, un ordre et, en cas
d'exclusion, un motif. Le plan est ensuite reconstruit et le contrôle d'inventaire
existant reste exécuté. Aucun affaiblissement des vérifications sémantiques,
des sources ou de la relecture. **266 tests réussis en 12,49 s**, dont reproduction
du plan doublonné et refus d'une clé absente. Le sous-contrat est enregistré comme
`required-candidate-assignments-v1` ; la forme publique des artefacts v5 reste
compatible. L'empreinte du prompt et du schéma empêche de réutiliser l'ancien plan.

La préparation neuve 0.2.4 est mesurée séparément dans
`output/direct-summary/legacy-prepare-cold-01`, avec le worker conservé, tous les
670 passages et sans approbation simulée. Elle a terminé : **3 750,575 s écoulées,
14 123,141 s CPU cumulées, 45 appels neufs**, 184 unités inspectées. Elle produit
270 informations à vérifier et **aucune information encore admissible à la
rédaction**, avec la politique conservée `on_request`. Des contrôles ou une
intervention humaine supplémentaires restent nécessaires ; ils ne sont ni
simulés ni inclus dans ce temps. Ce registre neuf diffère du registre déjà
travaillé utilisé pour la mesure de rédaction seule : ne pas additionner ces
durées en les présentant comme un parcours complet mesuré. Preuve :
`evidence/direct-summary-legacy-preparation.json`.

Bundle de développement avec le plan corrigé :
`dist/direct-summary-assignment/NoteTaker`, **266 tests réussis en 9,49 s** au
gate de compilation. Deux exécutables et schéma conformes aux sources testées,
modèles locaux vérifiés, démarrage/fermeture compilés réussis. Les lots précédents
restent conservés. Le rejeu intégral `direct-cold-04` est séquencé après la fin
du worker 0.2.4 ; le temps d'attente n'entre pas dans la mesure d'inférence.
Le lanceur d'enchaînement a rencontré un `PermissionError` transitoire à la
lecture du rapport Windows et s'est arrêté avant toute inférence directe.
L'incident reste dans `direct-cold-04-queue.json` ; la lecture réessaie désormais
brièvement cette seule erreur. Après fin confirmée du worker conservé
(aucun processus actif), `direct-cold-04` a été lancé séparément, avec cache vide.
Les douze extraits de référence ont été comparés octet par octet au PCM original :
**12 × 40 s**, soit 480 s, empreinte audio et empreinte des 670 entrées vérifiées.
Le formulaire humain est inchangé et aucun extrait n'est encore marqué relu.
Preuve : `evidence/direct-summary-human-reference.json`.

La création des workers Windows les assigne désormais au Job avant reprise
du processus suspendu. Cela corrige la course observée avec le lanceur venv
qui pouvait créer un enfant avant son rattachement et fausser le CPU cumulé.
Le test réel avec enfant terminé vérifie la comptabilité ; aucun changement
dans les algorithmes de transcription ou diarisation.

### Regroupement par catalogue — qualification supplémentaire

Le second rejeu intégral `direct-cold-04` termine : **2 036,763 s écoulées worker,
7 807,906 s CPU cumulées, 9 appels neufs**, 33 candidats, 15 refus, 17 paragraphes,
24 alertes, 469 passages non cités. Les cinq contextes ont les mêmes réponses que
`direct-cold-03`, après de nouvelles inférences. Le plan ne présente plus de
doublons mais morcelle vingt candidats en dix-neuf sujets avant contrôles :
objectif de regroupement encore insuffisant, aucun gain de qualité ou de vitesse.
Comparaison conservée : `output/direct-summary/comparaison-plan-affectations-v1.md`.
Audit réel des tables, prompts, citations, provenance et réouverture réussi ;
exports PDF/DOCX sans relecture réellement tentés et refusés. Rejeu compilé :
zéro inférence neuve, neuf réponses en cache, résultat identique hors durée.
Preuves : `evidence/direct-summary-required-v1-field-preservation.json`,
`evidence/direct-summary-required-v1-frozen-replay.json`. Code, tests et anciennes
preuves conservés sous `output/direct-summary/direct-required-assignments-v1-code`.

L'ajustement annoncé dans le document technique est implémenté : catalogue
commun avant affectation des IDs, indices contrôlés puis contrôles d'inventaire
existants ; alerte explicite si le plan reste majoritairement fragmenté, sans
fusion forcée. **268 tests réussis en 9,09 s** au gate du bundle distinct
`dist/direct-summary-catalogue/NoteTaker`. Sources embarquées et modèles vérifiés,
démarrage/fermeture compilés réussis ; aucun téléchargement. Audit natif de
292 PE : réserve commerciale sur `cudnn64_9.dll` toujours ouverte.
L'essai natif ciblé `group-catalogue-probe-01` est en cours ; il utilise tous les
vingt candidats admissibles du rejeu précédent mais ne représente pas une nouvelle
mesure complète à froid. Aucun gain sémantique déduit des tests de fixtures.

Cet essai a ensuite terminé avec refus d'intégrité : douze sujets mais indices
jusqu'à quatorze, **163,944 s, un appel neuf** ; brut/profil et `probe.json` conservés.
Le contrôle n'est pas contourné. Contrat corrigé `catalogue-then-required-assignments-v3` :
catalogue dans un premier appel, affectations dans un second avec enum des indices
réels. Les intitulés locaux restent dans le journal et les contrôles ; le
planificateur reçoit le contenu de tous les candidats sans ces catégories initiales.
Le probe suivant termine : **deux appels neufs, 162,528 s**, vingt candidats affectés
à deux sujets, aucun indice invalide. Cela ne mesure pas la pertinence des groupes
ni la fidélité et ne crée aucun brouillon. Aucun score humain disponible.
**268 tests réussis en 8,79 s** au gate du nouveau bundle distinct
`dist/direct-summary-catalogue-final/NoteTaker`, sources et modèles vérifiés,
démarrage/fermeture compilés réussis, même réserve native commerciale.
Le rejeu intégral `direct-cold-05` a été exécuté séparément après ce probe, avec
réponses absentes et tous les contrôles actifs. Résultat complet et limites dans
le bilan actuel en tête de ce document.

Le premier bundle compilé 0.2.5 reste conservé comme lot intermédiaire v1.
Le bundle de travail actuel est celui du plan corrigé, indiqué ci-dessus ;
sa qualification fonctionnelle sur le débat est encore en cours.
Douze extraits WAV de 40 s et un formulaire vierge sont préparés dans
`output/direct-summary/reference-humaine`. L'utilisateur a accepté de les
annoter ; **aucune annotation humaine reçue**, scores de fidélité, regroupement
et omissions importantes **non mesurés**. Aucun bundle commercial qualifié à ce stade.

## État conservé du lot précédent

Dernier lot sources précédent : **0.2.4.dev0, registre intermédiaire en qualification**.
Plan préalable : `information-registry-plan.md` ; architecture et procédure :
`information-registry-0.2.4.md`. La migration SQLite v5 est additive et sauvegardée ; ne pas
ouvrir une base v5 avec un ancien exécutable ni diminuer son numéro de schéma.

Dernier lot compilé : **0.2.4.dev0, registre intermédiaire en qualification**,
18 octobre 2026. Dossier : `dist/information-registry/NoteTaker`.
Bilan : `information-registry-0.2.4.md`. Ce bundle de développement contient
les modèles locaux ; ce n'est pas un installateur commercial qualifié.
Le lot 0.2.3 reste inchangé dans `dist/topic-summary/NoteTaker`.

Lot précédent : **0.2.2.dev0, corrections humaines et références de brouillon**,
18 octobre 2026. Dossier compilé : `dist/validation-fixes/NoteTaker`.
Bilan et procédure de réparation : `validation-fixes-0.2.2.md`.
Le lot 0.2.1 reste dans `dist/directory-01/NoteTaker`.
Les étapes biométriques 2–6 ne sont pas commencées.

## Lot 0.2.4.dev0 — registre intermédiaire (18 octobre 2026)

Plan présenté avant modification : `information-registry-plan.md`. Diagnostic :
six notes au maximum par fenêtre en 0.2.3, regroupement depuis les seules
notes acceptées et refus surtout accessibles dans les fichiers techniques.

Implémenté : migration additive SQLite v5 avec sauvegarde, révisions immuables,
inventaire intégral des segments (blancs compris), informations et variantes
avec identifiants stables, sources exactes/horaires, états auteur/vérification,
relations sourcées, refus et omissions conservés. Une correction humaine ne
supprime ni la proposition précédente ni les sources. Les conflits refusent
d'écraser la révision opérateur. Les informations refusées et résidus sont
accessibles dans « À vérifier ».

L'interface sépare préparation du registre, vérification, rédaction et relecture
finale. Recherche/filtres, correction, déplacement de sujet, approbation,
exclusion motivée, relations et historique sont disponibles. La lecture du
registre suit son instantané original, même si la transcription actuelle a
changé. L'ancien brouillon et sa relecture historique restent conservés ; une
ancienne révision de registre ne peut pas autoriser l'export comme révision
courante. L'approbation d'une information n'approuve jamais le document.

**226 tests réussis** (rejeu final : 8,98 s) : tests de services et widgets, migration/sauvegarde et
retour arrière, identifiants, citations/relations invalides, sources intégrales,
refus/variantes, concurrence, récupération après erreur, transaction registre–
brouillon, obsolescence et provenance, exports PDF/DOCX de fixtures après
relecture explicite et réouverture. Les réponses IA des tests unitaires sont
construites et déclarées. Trois captures Windows Qt sur données fictives ont
été inspectées. Preuves : `evidence/pytest-information-registry.xml` et
`evidence/information-registry-ui.json`.
Une relance préalable sans `--basetemp` a rencontré 151 erreurs de préparation
de fixtures, car le dossier temporaire système était inaccessible (73 tests
passés, aucun échec d'assertion). Sa preuve est conservée dans
`evidence/pytest-information-registry-temp-access-failed.xml`. La relance dans
un dossier neuf du dépôt est la preuve JUnit finale ci-dessus.

Le rejeu réel conserve les mêmes 670 passages sur une copie isolée, sans
nouveau calcul Whisper/sherpa. Les premiers calculs ont montré des erreurs
de type et d'origine du propos. Classement et reformulation sont séparés ;
une variante corrigée est revérifiée et ne remplace pas silencieusement la
proposition rejetée. Le plan thématique part des sources originales.
Trois arrêts volontaires de cet essai sont conservés dans les preuves, avant
normalisation séparée, répartition en trois processus CPU, puis vérification
approfondie sur demande après constat du coût trop élevé de la passe exhaustive.
Ce ne sont pas des plantages spontanés. Les contrôles de sources, de sens et
d'export ne sont pas désactivés.

L'extraction native a examiné **184 unités, 31 lots, les 670 passages**. Le
registre préparé contient 354 informations/variantes ; 508 segments portent
une citation candidate, 162 n'en portent pas. Les 670 textes intégraux restent
disponibles. Ces comptes ne mesurent pas les idées couvertes ni perdues.
Preuve : `evidence/information-registry-parallel.json`. Les lots
d'extraction gardent chacun l'instantané complet dans la requête worker et
sont réunis avant un seul
plan global ; cette répartition est un harnais de test, pas une option de
parallélisme activée dans le produit. Les réponses natives identiques peuvent
être reprises en cache strict ; les durées ne valent pas benchmark à froid.
Les prompts natifs d'extraction ne voient pas simultanément les 670 passages :
ils reçoivent six unités bornées par lot. Le plan lit des blocs de sources
originales, puis consolide leurs intitulés. Cela limite encore le contexte.
Les six dimensions qualitatives restent non mesurées sans annotation humaine.
Le harnais a pris 2 809,266 s avec reprises strictes de réponses antérieures ;
le code a évolué pendant le développement. Ce n'est ni un rejeu intégral à
froid des sources finales ni un benchmark de production.
L'initialisation sans IA rend immédiatement disponibles tous les passages.
La préparation Qwen conserve désormais des propositions en attente ; celles-ci
ne deviennent pas admissibles par la seule présence d'une citation. Le contrôle
approfondi se demande par fiche. Une fiche verrouillée conserve son choix
opérateur et reçoit seulement un avis consultatif. Deux observations de lecture
du développement (généralisation d'un récit personnel, métatexte sur un fragment)
restent dans `evidence/information-registry-agent-observations.json` ; ce ne sont
ni des annotations humaines de référence ni une mesure de gain de fidélité.
Le premier worker 0.2.4 compilé a réellement vérifié une fiche sur cette copie :
3 appels Qwen CPU, 53,732 s, sources et anciennes relectures inchangées,
proposition initiale conservée, aucune approbation créée. Preuve :
`evidence/information-registry-native-request-before-time-label.json`. Une variante a passé les
quatre contrôles machine ; cela reste un avis provisoire à contrôler humainement.

La dernière inspection Qt sur les 670 passages a révélé un horaire fictif
`00:00:00` pour les fiches sans citation retrouvée. L'affichage est corrigé en
**À rattacher**, avec test de non-régression et recompilation. La dernière suite
ci-dessus contient ce cas et un second contrôle du contexte d'une citation
rejetée : même sans correspondance exacte, l'interface conserve le texte de
l'instantané historique, pas celui d'une transcription corrigée depuis.
Les deux captures de la copie réelle ont été
inspectées (`evidence/information-registry-field-ui.json`), sans changer les
sources, le brouillon ou les relectures.

Après ces corrections d'interface, le worker final a rejoué le contrôle
antérieur : trois réponses natives en cache strict, **zéro nouvel appel natif**,
réponse identique. Les algorithmes gelés ont été comparés à ceux du premier
worker testé avec inférence fraîche. L'ancienne réponse n'est jamais réinjectée
dans le registre courant. Preuve : `evidence/information-registry-native-request.json`.

Le bundle 0.2.4 a passé son démarrage et sa fermeture Windows sur un dossier
isolé. Les modules du registre dans **les deux exécutables** ont été comparés
aux sources finales. Les modèles sont joints sans téléchargement, par liens
NTFS immuables pour cette copie de travail. Inventaire : 292 fichiers PE ;
aucune option ASIO/VirtualKeyboard interdite, mais `cudnn64_9.dll` reste présent.
Preuves : `evidence/information-registry-release.json`,
`desktop-information-registry.json`, `native-payload-information-registry.json`.
Les moteurs audio sont inchangés, contrôlés par comparaison au worker 0.2.3
(`information-registry-audio-engines-unchanged.json`), sans nouvelle inférence
audio. Cette vérification ne qualifie ni leur précision ni un PC vierge.

La rédaction native est terminée techniquement : **46 nouveaux appels CPU,
1 996,973 s (33 min 17 s), 14 parties sur 13 sujets examinés**. Cinq paragraphes,
neuf fiches reprises, 30 segments cités, 1 126 caractères, contre six paragraphes,
34 segments et 1 730 caractères dans le brouillon 0.2.3 archivé. **Ce résultat
est encore très partiel et ne démontre aucune amélioration de qualité.**
346 informations/variantes non rédigées restent dans l'instantané de comparaison,
avec 32 omissions explicites des fiches sélectionnées. La vérification était
partielle : les avis favorables provenaient des premiers essais natifs et du
contrôle supplémentaire. Une séance neuve prépare des propositions en attente,
à vérifier ou à approuver explicitement avant rédaction.

Le nouveau brouillon a passé les contrôles de références et son export sans
relecture a été refusé. Les 670 lignes, l'instantané original et l'ancien
brouillon sont conservés (`information-registry-real-comparison.json`).
Mais la lecture du développement a encore relevé des rapprochements douteux :
emploi étudiant/salaire sous un sujet de sélection universitaire, question
vague sous un sujet de chiffres du mouvement, lien entre révolution et emploi.
Une faute « durerant » subsiste également. Ces cas avaient passé les contrôles
Qwen ; un avis favorable ne certifie donc ni le contexte ni la qualité du texte.

**Huit fiches ont été remises à vérifier après rédaction**, sans exclusion,
effacement, modification des sources ou approbation humaine. Le registre
courant contient **355 fiches/variantes, 322 à vérifier, 33 admissibles** avant
rédaction. Le brouillon de comparaison est conservé mais lié à l'ancienne
révision : il faut corriger/reclasser les fiches puis régénérer avant une nouvelle
relecture et un export. Preuve :
`evidence/information-registry-post-writing-observations.json`.
Ces observations sont celles du développement, pas une référence humaine
annotée. Les six dimensions demandées restent non mesurées.

Comparaison lisible :
`output/information-registry/field-670/Comparaison-registre-0.2.4.md`.
Lanceur de copie isolée : `output/information-registry/field-670/Ouvrir-NoteTaker.cmd`.
Les liens audio de la copie pointent vers le fichier original ; elle n'est pas
portable. Les 670 bornes temporelles restent dans le fichier et son SHA-256
est inchangé (`evidence/information-registry-audio-links.json`).

Restent à développer/qualifier : meilleur classement contextuel, traitement
des rejets techniques (dont les alias de voix internes), coût CPU, fidélité et
complétude avec référence humaine. La redistribution native, la recette sur
Windows vierge déconnecté et le Setup commercial restent ouverts. **Le produit
n'est pas déclaré terminé ni qualifié pour un procès-verbal municipal.**

## Lot 0.2.3.dev0 — synthèse thématique en qualification (18 octobre 2026)

Le moteur précédent regroupait des notes mais les imprimait individuellement.
La nouvelle chaîne sélectionne et classe les propos, vérifie leur soutien,
établit un catalogue global puis affecte les notes aux sujets, rédige un
paragraphe et contrôle ses phrases ainsi que son titre. Les passages éloignés
peuvent être réunis. Les questions, avis cités et récits personnels restent
distincts ; les noms viennent des attributions opérateur. Aucun profil vocal
n’est créé. Les sources, révisions, votes manuels et approbations restent protégés.

Ajouts : transcription intégrale distincte de la synthèse, longueurs courte /
standard / détaillée, lexique local par séance, consultation phrase → citations
→ audio, liste des passages écartés/incertains. Les paragraphes modifiés à la
main conservent leurs liens et nécessitent une nouvelle relecture. SQLite reste
v4 ; les anciens documents restent lisibles dans cette nouvelle version.

**175 tests automatisés réussis** (services et widgets Qt), dont refus d’une
reformulation non soutenue malgré sa citation, contrôle des questions et
citations d’autrui, liens de voix/anaphores, renommage annuaire, scission/fusion,
réouverture et exports PDF/DOCX après relecture explicite de fixtures.
Sept contrôles textuels connus ont réellement été soumis à Qwen CPU : cinq
reformulations non étayées refusées et deux contrôles positifs acceptés. Aucun
taux de fidélité sur le débat n’en est déduit.

Le test réel utilise les **670 mêmes passages**, jusqu’à 20:37,580, sur l’audio
de **20 min 40,017 s** du PDF 0.2.2 de trois pages. Les corrections et les
horodatages sont identiques à son instantané exporté. Aucun nouveau calcul de
transcription ou de diarisation, aucune modification/approbation de séance réelle.
Les longueurs courte/détaillée sont testées par contrats unitaires ; la
comparaison de terrain porte sur le niveau standard uniquement.

Les essais réels ont exposé des erreurs de classement du discours, des sujets
trop fins, des répétitions, des alias mal respectés et des contrats de
vérification inadéquats pour les titres. Les sorties refusées et reprises
volontaires sont conservées, avec les calculs sources identiques en cache
strict. Les titres possèdent désormais leurs propres contrôles de soutien,
d’allégation et d’identité/décision ; les phrases gardent les quatre axes sens,
modalité, attribution, relation. Aucun critère de relecture/export n’est désactivé. Les essais natifs ont
révélé des faux positifs malgré les citations : budget attribué à une partie
des travaux, absence d’évaluation inventée, question suivie d’une assertion,
affiliation de parti nouvelle. Des refus déterministes supplémentaires couvrent
ces formes, avec perte possible d’information. Ils ne prouvent pas l’absence
d’autres erreurs sémantiques. La lecture réelle a aussi repéré une fausse
liaison entre deux passages éloignés : la vérification de paragraphe reçoit
maintenant les horaires et l’ordre des phrases. Une contestation anaphorique
exige les deux positions sourcées, et les référents courts non résolus sont
écartés plutôt que complétés par supposition. L’absence d’opposition ne peut
pas être transformée en soutien explicite.

La synthèse peut omettre des notes ou des sujets refusés. Elle n’est pas
exhaustive et le même modèle peut se tromper dans ses différents contrôles.
**Fidélité, couverture et gain qualitatif restent non mesurés**, faute de
référence humaine annotée. Les réserves Windows vierge déconnecté, redistribution
native et installateur commercial demeurent ouvertes. Voir
`topic-summary-0.2.3.md` et les preuves `evidence/topic-*.json`.

### Résultat livré et limites restantes

La comparaison finale produit **6 paragraphes, 12 phrases sourcées et 1 730
caractères**, contre 7 points et 2 830 caractères auparavant. Ce sont des
mesures de structure, pas de fidélité. Sur les candidats examinés, 21 notes
ont été refusées ; 3 notes acceptées ne sont pas reprises, dont 2 dans un
sujet finalement refusé. **Un sujet n'a pas été rédigé**, et cette omission
est affichée. Le dernier passage de calcul a exécuté 5 appels Qwen CPU en
212,362 s, avec réutilisation des autres réponses après contrôle strict de
leur identité. Cette durée n'est pas celle d'un traitement complet à froid.

Une inversion de rôles (« les ministres ne nous écoutent pas » devenant
« les ministres ne sont pas entendus ») et une fausse citation littérale ont
été repérées pendant l'inspection, puis corrigées avec de nouveaux contrôles.
La réparation de rôle a été recalculée sur les citations originales et
revérifiée. Malgré cela, des formulations maladroites, des sujets trop isolés
et des termes de transcription incertains, comme « prélèvement », restent
visibles. **La qualité rédactionnelle et la couverture restent en qualification.**

Le PDF technique de comparaison comporte **8 pages rendues et toutes inspectées**,
avec les sources et horodatages. Il porte la mention non validé sur chaque
page. La copie isolée de relecture conserve les 670 interventions, les noms
et l'historique antérieur ; son nouveau brouillon n'est pas approuvé et son
export normal est effectivement bloqué. L'instantané et l'audio source restent
inchangés. Aucune approbation humaine n'a été fabriquée sur ce débat.

Le bundle Windows a été recompilé dans `dist/topic-summary/NoteTaker`.
Interface démarrée et fermée normalement ; workers Whisper et sherpa exécutés
à nouveau sur la fixture CPU. Le contrôle final du worker Qwen compilé utilise
9 réponses natives en cache strict et **0 nouvel appel natif**, ce que la preuve
compte explicitement. Un précédent essai compilé avec calcul Qwen frais a
réussi en 352,302 s ; il précède les derniers contrôles conservateurs. Les
modules gelés sont comparés aux sources finales dans la preuve de livraison.
La suite finale compte **175 tests réussis**. Le PC Windows vierge déconnecté,
la redistribution native et l'installateur commercial restent non validés.

Preuves finales : `evidence/topic-summary-release.json`,
`evidence/topic-summary-standard.json`, `evidence/topic-review-copy.json`,
`evidence/topic-comparison-pdf.json`, `evidence/bundle-topic-summary.json`.
PDF et copie de relecture restent dans `output`, hors bundle de distribution.

## Corrections 0.2.2 réellement vérifiées

- Sur une copie SQLite cohérente de la séance en échec : **42 liens incohérents
  dans 11 des 18 affirmations**, tous dus à l'ancien identifiant d'intervenant
  conservé dans les affirmations après attribution manuelle. Les passages et
  citations existaient. Aucun remappage de source manquante n'était nécessaire
  pour ce cas. Le contrôle bloquait légitimement ; le message et l'absence
  d'outil de réparation empêchaient de comprendre et résoudre le problème.
- Diagnostic par point/affirmation/source, accès au passage audio et éditeur
  de citations, voix et texte. La mise à jour explicite des attributions résout
  les 42 liens sur cette copie sans changer textes, citations ou IDs sources.
  **Aucune séance réelle modifiée ou approuvée automatiquement.**
- Enregistrement d'une révision de travail incohérente possible, avec sources
  conservées ; relecture et export continuent de refuser toute incohérence.
  Modifier le texte d'un point ne supprime plus silencieusement ses affirmations.
- Scission/regroupement : remappage précis des citations et historique complet,
  mutation SQLite atomique, ancienne révision conservée. Un échec injecté après
  remappage annule à la fois les segments et le nouveau brouillon.
- Réanalyse : IDs, texte, noms, références audio et horaires des corrections
  manuelles préservés. Changement de montage audio ou alignement ambigu : arrêt
  sans remplacer la transcription corrigée. Les anciennes corrections restent
  restaurables. Les noms confirmés ne sont pas propagés par supposition.
- Sur les mêmes résultats acoustiques du débat déjà calculés : **1 822 → 903
  passages**, **491 → 237** passages de moins d'une seconde, mêmes mots lexicaux
  et mêmes neuf groupes. Aucun nombre de voix imposé. Cette mesure de
  segmentation ne démontre aucun gain de justesse des voix.
- **125 tests réussis**, dont 21 nouveaux tests de services/interface pour ce
  lot : attribution puis changement, diagnostic, citations absentes/modifiées,
  scission/fusion, transaction interrompue, migration v3→v4 avec sources/relecture,
  sauvegarde/réouverture, refus avant relecture et exports après contrôle valide.
- Chaîne avec les vrais moteurs CPU sur une fixture française synthétique de
  32 s : import, Whisper/sherpa, Qwen, deux attributions manuelles fictives,
  scission/fusion, deuxième analyse, régénération, refus d'export sans relecture,
  relecture **simulée et marquée comme telle**, PDF/DOCX et réouverture : réussie
  en **362,143 s**. Les deux exports ont été rendus et leurs quatre pages
  inspectées. Les essais initiaux refusés restent documentés dans le bilan.
- Bundle PyInstaller 0.2.2 compilé : interface ouverte/fermée normalement et
  trois workers CPU terminés avec succès, PATH limité à System32 et sans
  chemins Python. Unicode français conservé. Volume brut : 3 560 131 698 octets
  avant mise à jour du guide. Inventaire natif : 292 fichiers PE ; les réserves
  de redistribution existantes, dont la DLL cuDNN de CT2, restent ouvertes.

Preuves : `evidence/pytest-validation-fixes.xml`,
`evidence/validation-fix-real-audit.json`,
`evidence/segmentation-fix-real-replay.json`,
`evidence/corrections-real-workers-chain.json`,
`evidence/validation-fixes-ui.json`.
Contrôles du binaire : `evidence/bundle-validation-fixes.json`,
`evidence/desktop-validation-fixes.json`,
`evidence/native-payload-validation-fixes.json`.

La précision nominative, les chevauchements et la fidélité sémantique sur le
débat restent **non mesurés**, faute de référence humaine annotée. Aucun nouveau
test micro naturel de 10–20 min ni test sur Windows vierge déconnecté n'a été
effectué pour ce lot. Le bundle est de développement ; le Setup commercial
reste bloqué par les qualifications et droits de redistribution déjà recensés.

Mise à jour du 18 octobre 2026 (comparaison naturelle exécutée le 16 octobre).
**Le test réel 0.1 a échoué ; le problème global n'est pas
déclaré résolu.** L'audit a précédé les modifications des moteurs. Référence :
`audit-0.2.md`. L'ancien état est conservé dans `history/progress-0.1.md`.

## Référence réelle

Débat télévisé français de 50 min 54,733 s, environ six voix annoncées. Une
prise micro cochée de 9,899 s précède le MP3 dans la séance ; comparaison sur
la même dérivation de 51 min 4,632 s, sans la retirer artificiellement.

| Mesure 0.1 observée | Valeur |
|---|---|
| Identifiants / tours sherpa | 195 / 576 |
| Passages Whisper / incertains | 1 485 / 506 |
| Identifiants avec moins de 5 s attribuées | 61 |
| Caractères U+FFFD déjà perdus avant PDF | 1 734 |
| Brouillon / PDF | 88 404 caractères / 54 pages |
| Alertes de vérification | 29 |

L'instantané de la base et les sorties privées sont dans
`output/quality-02/baseline`. Statistiques : `evidence/quality-02-baseline.json`.
Le MP3 importé est identique à l'original selon SHA-256 ; aucune séance initiale
n'a été remplacée pour la recette.

## Corrections développées

- IPC JSON ASCII sans perte et décodage strict ; nouvelle transcription requise
  pour les textes historiques corrompus, sans substitution heuristique.
- Embeddings propres suffisamment longs, regroupement global sans nombre imposé,
  diagnostic de durée/segments courts/incertains et comparaison WeSpeaker/ERes2Net.
- Conservation des mots Whisper et alignement lors des changements de voix.
- Synthèse Qwen hiérarchique : blocs avec contexte partagé, informations sourcées,
  contrôle des citations/intervenants, seconde vérification et regroupement des
  sujets réellement abordés. Les décisions/actions rapportées restent à confirmer.
- Trois cadres explicites : transcription intégrale, compte rendu synthétique,
  projet de PV municipal avec relecture par le secrétaire.
- Noto Sans OFL embarqué et incorporé, couverture, pagination, sections espacées,
  références accessibles dans l'éditeur plutôt qu'imprimées intégralement.
- Signal de scrutin fondé sur des formulations procédurales ; les mots « voix »,
  « contre » ou « vote » seuls ne créent pas d'alerte ni d'objet vote.
- Fusion, scission et noms conservés ; restauration des transcriptions/corrections
  antérieures depuis l'interface. Un nouveau traitement ne supprime pas l'historique.

## Validations réelles à ce stade

La suite de **86 tests** a réussi, y compris restauration des corrections de
brouillons, refus des textes corrompus, protocole Unicode et polices incorporées.
Le rapport final est `evidence/pytest-quality02.xml`.

La nouvelle transcription complète produit **1 485 segments, 12 216 mots** et
**zéro U+FFFD**. Temps mural du rapport : 1 369,168 s. Les mots ne constituent pas
une référence humaine ; WER non mesuré.

L'alignement corrige aussi les élisions françaises et les mots de durée nulle :
2 350 passages deviennent 1 822, avec 644 unités de citation au lieu de 1 172.
Les caractères hors espaces et les neuf groupes sont conservés. Les 148
passages avec timing déduit restent incertains ; il reste 894 passages incertains.
Ces compteurs sur des passages redécoupés ne prouvent pas une amélioration de
précision. Preuve : `evidence/quality-02-word-alignment.json`.

Les mêmes 619 fenêtres propres longues ont été regroupées avec plusieurs seuils
et les deux embeddings. La liaison complète WeSpeaker à 0,4 produit **neuf
groupes sans nombre imposé** ; d'autres réglages descendent jusqu'à un groupe,
ce qui illustre le risque de sur-fusion. Le profil reste expérimental.
La chaîne native complète a aussi été exécutée (573,678 s), puis la géométrie
de confiance a été étudiée sur ses mêmes observations, sans réextraire des
vecteurs différents. Rapports : `evidence/quality-02-speakers*.json`.

Des fenêtres courtes, chevauchées ou ambiguës restent non attribuées et de
nombreuses attributions sont incertaines. La diminution des groupes ne suffit
pas à prouver une meilleure précision. Les durées par groupe peuvent compter
des plages simultanées ; ce ne sont pas des temps de parole de référence.

Le dernier bundle a été reconstruit avec le modèle Instruct sélectionné et
les corrections d'alignement. La recette compilée du 18 octobre a révélé des
références répétées : la validation JSON arrêtait le traitement avant la passe
de réparation. Cette sortie échouée est conservée dans
`evidence/bundle-quality02-before-schema-fix.json`. Le contrôle d'unicité reste
obligatoire à l'issue de la réparation par un véritable appel Qwen ; le schéma
intermédiaire laisse désormais les doublons atteindre cette passe. Un test de
régression couvre ce chemin. La recette finale et ses empreintes sont dans
`bundle-quality02.json` et `desktop-quality02.json`.

La nouvelle recette compilée réussit ensuite les **trois moteurs CPU réels**
(ASR, sherpa, Qwen), avec protocole français sans perte et environnement Python
retiré du PATH. Le cas Qwen exerce effectivement la réparation des doublons,
puis conserve ses deux informations une seule fois. L'interface compilée
démarre, répond et se ferme normalement avec une base isolée. Le lot mesure
3 559 987 654 octets avant compression. Le poste possède des runtimes installés
et reste connecté : ces contrôles ne valent pas recette Windows vierge hors ligne.
Le résultat naturel complet du 16 octobre précède cette correction ciblée de
schéma du 18 ; sa fidélité n'est pas déclarée revalidée par la fixture compilée.

Ces réussites attestent l'exécution, pas l'exactitude sémantique. Sur la fixture
compilée, Qwen a rattaché un budget global de travaux à la seule toiture, sans
appui suffisant ; son vérificateur l'a accepté. Un contrôle plus strict a rejeté
ce glissement mais aussi une paraphrase fidèle, donc n'a pas été intégré sur
la base de ce seul essai (`evidence/quality-02-verifier.json`). Cette erreur
connue confirme la nécessité de relire les sources et la limite du même modèle
employé pour générer et vérifier.

Les PDF Unicode de contrôle ont été rendus avec Poppler et inspectés ; le DOCX
avec ses TTF a été ouvert/rendu en lecture seule par Word, source inchangée.
Accents, œ, apostrophes et euro lisibles, sans carrés noirs sur ces contrôles.
Word reste un outil de QA et n'est pas requis sur le poste utilisateur.
Les deux formats refusent les glyphes absents de la police embarquée avant de
remplacer le fichier de destination ; ce refus a été testé sur chaque format.

La première synthèse complète 0.2 est **rejetée** malgré une chaîne exécutée
jusqu'aux aperçus PDF/DOCX. Elle donne huit sujets, 1 006 caractères et deux pages,
mais ne retient que les huit premières informations sur 31 : ses sources
s'arrêtent à 708,060 s dans un fichier de 3 064,632 s. Le vérificateur a aussi
accepté une causalité ajoutée et une question créée. La réduction de 54 à deux
pages ne constitue donc pas une réussite. Rapport `evidence/quality-02-comparison.json`.
Les deux pages PDF et les deux pages rendues par Word ont été inspectées :
glyphes et mise en page lisibles, fidélité et couverture insuffisantes.

Un contrôle refuse désormais le regroupement global s'il omet ou répète une
information vérifiée. Il ne mesure pas la couverture humaine des sujets.
La comparaison complète de Qwen3-4B-Instruct-2507 est **exécutée**, séparée dans
`output/quality-02/instruct-2507`. Il est sélectionné pour le développement,
avec sa quantification Unsloth et sa provenance figées au manifeste. Le bundle
embarque seulement ces nouveaux poids LLM ; les anciens restent conservés hors
de ce lot. Aucun téléchargement au lancement n'est ajouté.

| Mesure sur le même audio | 0.1 | Recette 0.2 Instruct |
|---|---:|---:|
| Groupes vocaux, sans nombre imposé | 195 | 9 |
| Caractères de remplacement U+FFFD dans le texte | 1 734 | 0 |
| Caractères du brouillon synthétique | 88 404 | 6 844 |
| Pages PDF | 54 | 4 |
| Thèmes | 11 points initiaux | 8 |

Les 18 blocs/644 unités sources ont donné 46 informations reformulées, dont
36 retenues par le vérificateur. Les 36 sont affectées exactement une fois aux
huit thèmes, sans omission interne au regroupement. Le premier regroupement
du candidat omettait onze informations et en répétait une : il a été refusé,
puis réparé par un appel Qwen d'affectation à clés obligatoires. Aucune synthèse
de secours fabriquée n'est substituée au modèle.

Le contrôle automatique trouve zéro information retenue sans citation exacte.
**Ce résultat ne mesure ni la fidélité sémantique ni la couverture des sujets.**
Les sources retenues s'étendent de 78,460 à 2 968,180 s ; cette étendue ne prouve
pas que les sujets intermédiaires soient tous traités. Le vérificateur voit le
contexte proche : il refuse notamment l'unité « établissements » après une
rectification portant sur des personnes et des blocages.

Temps cumulés des appels natifs de synthèse : **3 056,834 s**, soit environ
51 minutes. La dernière reprise de 90,011 s réutilisait les étapes précédentes ;
elle n'est pas le coût d'une synthèse complète. Les calculs étaient concurrents,
donc ces durées ne constituent pas une comparaison de performances isolée.

Rapport complet : `evidence/quality-02-comparison-instruct.json`. Les quatre
pages PDF et les quatre pages du DOCX rendu par Word ont été inspectées :
accents et symboles français lisibles, police incorporée, mise en page lisible.
Le DOCX source est inchangé après QA. Les onglets réels transcription,
brouillon et votes de cette séance isolée ont aussi été rendus et inspectés.

**La qualité professionnelle du compte rendu reste non validée.** Des phrases
restent maladroites, certaines catégories et attributions d'opinions doivent
être corrigées. Les marqueurs de discours rapporté ne couvrent pas tous les
cas. Une citation exacte et l'accord du même LLM ne prouvent pas qu'une
reformulation est fidèle. Aucun résultat de scrutin n'est créé (zéro objet vote).
L'export normal de cette séance est réellement refusé avec
`HUMAN_REVIEW_REQUIRED_FOR_CURRENT_SESSION`. Les fichiers PDF/DOCX sont des
**aperçus techniques non validés** ; aucune relecture humaine n'a été créée.

La séance de recette distincte peut être ouverte avec le lanceur
`scripts/run-quality-review.ps1`. Le MP3 et la séance utilisateur initiale
restent préservés. Les anciennes sorties échouées restent consultables.

## Redistribution native et chantier CPU

L'inventaire final contient 292 fichiers PE ; les deux fichiers Qt Virtual
Keyboard GPL/commerciaux seulement sont exclus et ASIO reste exclu. Le
démarrage réel du bundle réussit. L'audit confirme toutefois que la roue
CTranslate2 active importe directement le frontal NVIDIA `cudnn64_9.dll`,
même pour CPU. Les conditions cuDNN 9.1 empêchent d'approuver en l'état ce lot
pour une cible commerciale générale sans GPU NVIDIA. Les réserves FFmpeg,
Qt/LGPL et Visual C++ restent ouvertes : voir `licenses.md`.

Une DLL CTranslate2 4.6.0 CPU seule a été réellement compilée depuis la révision
amont figée, avec Ruy, sans MKL/OpenMP/CUDA/cuDNN. Ses imports PE ne contiennent
pas de DLL NVIDIA. Sa taille est 7 082 496 octets ; preuve
`evidence/ctranslate2-cpu-build.json`. Elle reste isolée, sans remplacement du
moteur actif ni du bundle. Son import Python réussit (zéro périphérique CUDA,
types CPU float32/int8/int8_float32), mais la transcription de l'extrait naturel
de 30 secondes dépasse **600 secondes** et termine en `TimeoutExpired`.
**Cet essai d'inférence est un échec**, pas une réussite CPU produit. Preuve
`evidence/ctranslate2-cpu-smoke.json`. La variante reste non intégrée ; le
moteur actif est inchangé. Le lanceur d'essai gère désormais les délais et
l'arrêt de son propre arbre de processus, y compris le lanceur de venv Windows.

Aucun compte rendu réel n'a été approuvé automatiquement ; aucune réussite
globale de résumé n'est annoncée.
Les calculs de développement ont été concurrents : leurs durées observées ne
forment pas une comparaison de performances CPU isolée avec l'ancien test.

## Non validé

Référence humaine des voix, WER/DER, couverture thématique et taux d'invention
sémantique : **NON MESURÉS**. Les références/citations et le second passage du
LLM ne remplacent pas une relecture humaine. La réunion municipale naturelle,
capture longue, bruit/chevauchements avec vérité terrain, GPU, minima matériels,
Windows vierge déconnecté et installateur commercial signé restent non validés.
Les réserves de redistribution native restent dans `licenses.md`.

Procédure et conventions : `benchmark-0.2.md`. Le produit reste en développement.

L'utilisateur a confirmé ne pas disposer d'extraits annotés de référence.
Les scores d'exactitude ne sont donc pas calculés et aucun nombre n'est
substitué à cette absence de vérité terrain.

## Annuaire et références vocales — audit préalable du 18 octobre 2026

La nouvelle demande est cadrée dans `speaker-directory-plan.md`, avant modification
du code applicatif. L'annuaire nominatif interséances n'est pas encore développé.
La collecte d'empreintes nominatives et l'identification restent désactivées/non
implémentées ; aucune personne du débat n'est enrôlée dans cet audit.

Les API sherpa-onnx 1.13.8 installées ont été inspectées et leurs opérations
réellement exécutées sur CPU. WeSpeaker charge en 256 dimensions, ERes2Net en
512 ; les extractions sur tonalité artificielle donnent des vecteurs finis.
Le manager accepte plusieurs embeddings mais les agrège ; son binding expose
`score`, pas `GetBestMatches`. L'ajout, le refus d'un UUID dupliqué, le rejet
d'un vecteur inconnu et le retrait réussissent sur vecteurs artificiels.
Une égalité de scores renvoie quand même un identifiant via `search` : NoteTaker
devra ajouter une garde d'ambiguïté. `is_ready` ne prouve pas la présence de parole.
Rapport : `evidence/speaker-directory-api-audit.json`.

Le plan propose annuaire sans biométrie, coffre/contrôles Windows, enrôlement
CPU puis suggestions après diarisation libre, sans nombre imposé ni apprentissage
à partir des corrections. Le code de capture/SQLite en clair n'est pas adapté
tel quel aux références biométriques. La validation juridique doit précéder
l'enrôlement lui-même, avec évaluation des articles 6/9 et de l'AIPD par la
collectivité/DPO ; aucune approbation juridique n'est déduite de cette demande.

**Non exécutés/non validés pour cette fonctionnalité :** enrôlement naturel,
coffre et habilitations, purge/restauration, correspondances réelles et benchmark
annoté libre/profils. Les contrôles API artificiels ne mesurent aucune précision.
Les 86 tests de l'application précédente n'ont pas été relancés dans cet audit
sans changement applicatif et ne valident pas la future fonctionnalité.

## Étape 1 de l'annuaire implémentée — 18 octobre 2026

Après validation du plan : annuaire civil, recherche/filtres, fiches modifiables,
archive/réactivation, sélection par séance, présences/procurations et rôles
distincts des fonctions permanentes. Attribution manuelle de la transcription,
instantanés/historique conservés, nouvelle relecture requise après modification.
Assistant vocal grisé sans action ; aucun profil vocal ou traitement nominatif
biométrique ajouté. Les étapes suivantes ne sont pas commencées.

**104 tests réussis**, dont 18 nouveaux contrôles de service et d'interface.
Migration v3 → v4 sur copie isolée de l'instantané réel : valeurs des neuf
tables historiques identiques, 1 485 interventions conservées, sauvegarde et
clés étrangères vérifiées, source inchangée. La base utilisateur active n'a pas
été ouverte en écriture pour cette recette. Les rendus réels de l'annuaire,
des présences et de l'attribution ont été inspectés ; un défaut de synchronisation
de l'éditeur a été corrigé et couvert. Les deux pages de chaque export de test
PDF/DOCX sont également inspectées, DOCX rendu par Word en lecture seule.

Le nouveau lot **`dist/directory-01/NoteTaker`** démarre/se ferme normalement ;
les trois workers compilés passent leurs contrôles CPU. Le lot antérieur est
conservé. Rapports : `pytest-directory.xml`, `directory-ui.json`,
`directory-legacy-migration.json`, `desktop-directory.json`,
`bundle-directory.json` et `native-payload-directory.json` dans `evidence`.

Recette sur le poste de développement connecté, pas sur Windows vierge hors
ligne. Ergonomie à valider par les agents ; aucun Setup commercial produit.
La base civile reste sous les permissions Windows, sans coffre chiffré ni
habilitations avancées ; le lot 2 n'est pas commencé. Les limites précédentes
des moteurs et de redistribution restent ouvertes. Voir `directory-stage1.md`.
