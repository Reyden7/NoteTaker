# Avancement NoteTaker 0.2 — qualité en évaluation

## Parcours simplifié et références vocales facultatives — 21 octobre 2026

Guide : [automatic-report-guide.md](automatic-report-guide.md).
Audit, architecture, licences, mesures et limites :
[automatic-report-architecture.md](automatic-report-architecture.md).
Preuves : `output/automatic-report-20261021/470f7221d5eb4cd0974963bf81f4e64d/`.

### Fonctionnel dans les sources de recette

- Page par défaut : import → **Générer le compte rendu** → brouillon modifiable,
  sources audio et export PDF/DOCX explicitement **BROUILLON NON RELU**.
  Aucun prérequis d’approbation des fiches. Le mode avancé conserve les outils
  antérieurs et le parcours distinct de validation humaine/export relu.
- Orchestration des moteurs CPU/GPU existants, sans modification des moteurs
  audio ni réentraînement. Réemploi de la transcription si l’audio sélectionné
  est identique ; garde contre les modifications concurrentes, annulation et
  erreurs sans effacement des sources ou des anciens brouillons.
- Format Qwen compact, citations exactes assemblées côté service, identifiants
  et noms liés aux sources. Une réécriture ciblée au maximum puis contrôle ;
  refus, variantes et omissions conservés dans un inventaire consultable.
  La preuve de citation ne vaut pas preuve du sens : contrôles déterministes
  des déformations effectivement observées, relecture toujours nécessaire.
- Composants de références vocales : microphone/import, réécoute, contrôles,
  embeddings WeSpeaker/sherpa CPU, plusieurs prises, seuil/marge/cohérence,
  rejet des inconnus, suggestions sans écrasement des identités humaines.
  Coffre séparé chiffré DPAPI du compte Windows, conservation et suppression,
  compatibilité par hash modèle. Aucun changement du schéma des séances.

**Cadre juridique non validé, aucun échantillon autorisé fourni** : collecte et
identification nominative sont restées désactivées. Le formulaire d’autorisation
consigne une décision externe ; il ne détermine pas la licéité. Aucune personne
réellement enrôlée ; précision nominative et calibration non mesurées. L’annuaire
civil, les noms déjà confirmés et la génération fonctionnent sans biométrie.

### Tests et recette réellement exécutés

**377 tests réussis en 12,25 s**, rapport `complete.xml`. Cela couvre notamment
le parcours simple, sauvegarde/réouverture, brouillon sans registre approuvé,
intégrité des sources/noms, export non relu et blocage de l’export officiel,
annulation, reprise de transcription/cache, contrôles des erreurs municipales,
chiffrement DPAPI réel de données fictives, capture simulée vers stockage
chiffré réel, expiration, suppression, modèle incompatible et rejet mathématique
des voix inconnues/proches. Les moteurs natifs dans les tests unitaires sont
remplacés par des fixtures explicitement fictives ; les inférences réelles sont
documentées séparément ci-dessous. `git diff --check` sans erreur de contenu.

Sur copie du municipal réel de **336,039 s / 36 passages** : Qwen CPU exécuté,
transcription déjà corrigée réutilisée, noms humains conservés, PDF/DOCX produits,
aucune relecture créée, export officiel refusé. Recette finale `delivery-final/` :
**4 reformulations et 3 citations de repli**, dont 2 reformulations avec source
faible. **23 passages non repris**, inventoriés. Pas de gain de fidélité annoncé.

Le format compact a nécessité **443,608 s** pour les deux appels initiaux neufs
(189,077 + 250,155 s). La réécriture depuis les sources a pris 50,331 s et son
premier contrôle 38,941 s. L’assemblage final de 43,795 s réutilise ces résultats
et ne recalcule qu’un contrôle modifié de 40,609 s : **ce n’est pas un temps de
génération à froid**. Pas de mesure finale du temps CPU cumulé de la chaîne.
Essais insuffisants conservés : première version 919,109 s / zéro reformulation,
chemin natif Windows trop long, puis JSON tronqué après 512,624 s. Ils ont conduit
au cache court vérifié et au contrat compact, sans masquer les échecs.

Contrôles de conservation SQL : transcription, annuaire, participants, décisions,
votes, registre, historique et anciens brouillons identiques. WAV municipal et
références BFMTV inchangés par SHA-256. L’ancienne empreinte physique de la base
du lot audio précédent diffère ; aucune identité binaire avec cet ancien relevé
n’est annoncée. Comparaison au premier instantané de ce lot et vérifications
avant/après les recettes consignées. Voir `delivery-preservation.json`.
Capture Qt de la page finale inspectée : `simple-page-final.png`.

Essai CPU d’embeddings sur deux groupes anonymes du même enregistrement :
1,336 s, cohérence interne uniquement, aucun vecteur stocké et aucune précision
d’identité mesurée. Pas de test réel de microphone nominatif, de voix proches
interséances ou de réunion longue avec référence humaine. Le test trois heures
est une couverture de blocs textuels, pas un essai audio terrain.

### Reste à qualifier

La synthèse **reste partielle**, avec des déformations que le même Qwen avait
initialement déclarées soutenues. Les protections ciblées ne constituent pas un
vérificateur sémantique général. Couverture et fidélité à améliorer/évaluer
humainement avant usage comme procès-verbal municipal. Authentification locale
par compte Windows, sauvegarde/migration du coffre et annulation native de
l’enrôlement à durcir ; voir limites techniques du rapport.
Licences amont vérifiées/documentées ; redistribution commerciale globale,
matériel supplémentaire et PC Windows vierge hors ligne toujours non validés.
**Pas de nouveau bundle compilé dans ce lot**, aucun téléchargement de modèle.
Lanceur fourni sur copie : `Ouvrir-la-recette-simple.cmd` dans les preuves.

## Lecture audio des citations — 21 octobre 2026

Rapport : [audio-playback-fix.md](audio-playback-fix.md).
WAV municipal PCM16 mono 16 kHz valide ; 48 erreurs SWR en trois secondes
avec Qt/FFmpeg et le casque Logitech 7.1, zéro avec Windows Media Foundation.
Choix du backend Windows avant initialisation Qt, lecteur partagé et copies
temporaires PCM limitées au début **et à la fin** des passages. Sources,
horaires et instantanés inchangés. Erreurs françaises, arrêt et nettoyage,
garde de cinq secondes et aucune nouvelle tentative automatique. Plugin natif
exigé au packaging ; aucun moteur IA modifié ni téléchargement.

**347 tests réussis en 11,41 s**, dont 17 nouveaux. Recette réelle Windows
sur sauvegarde de la séance municipale : boutons registre et transcription,
signal **Core Audio du processus non nul**, arrêt final et temporaire supprimé.
Intervalles 0–2 240 ms et **55 240–59 340 ms** ; lecture de celui-ci en
4,235 / 4,250 s avec chargement. Stéréo et quatre changements rapides vérifiés.
Journaux stderr des recettes réussies vides ; base de recette, références
humaines et WAV contrôlés identiques par empreintes.

Preuves : `output/playback-fix-20261021/758d8f8a825a450996c9b9eaed7f23e3/`
(`final.xml`, `real-windows-03/result.json`, journaux, captures, conservation).
Répétition finale `real-windows-04/result.json`, onglets visibles : 4,265 /
4,281 s, signal mesuré, arrêt et nettoyage confirmés, stderr vide.
L’essai initial refusé pour la mesure Core Audio par le bac à sable est conservé
comme échec ; recettes réussies ensuite autorisées hors bac à sable.
**Écoute acoustique humaine, autres matériels et PC vierge non validés**.
Pas de recompilation du bundle ; relancer la recette depuis ses sources.

Dernier lot sources : **0.2.5.dev0, laboratoire de synthèse directe en qualification**.
Plan préalable : `direct-summary-0.2.5-plan.md` ; utilisation et limites :
`direct-summary-0.2.5.md`. Le parcours 0.2.4 et le schéma SQLite v5 sont conservés.

## Parcours registre / rédaction — correctif du 21 octobre 2026

Rapport et mode d'emploi : [registry-workflow-fix.md](registry-workflow-fix.md).
Preuves neuves :
`output/registry-workflow-20261021/4c9f7125b1934a5ab4c3939945cd8bfc/`.

### Causes établies et corrections

La table pouvait rester filtrée sur les sources intégrales après une préparation,
alors que le compteur annonçait les propositions distinctes. « À vérifier »
mélangeait aussi ces catégories. Le registre n'était pas simplement vide : dans
la copie municipale disponible, **24 propositions dont 23 refusées** (alias V1,
copie longue, confusion de nature/type, citation non retrouvée). La révision 8
de 23 fiches signalée par l'utilisateur n'a pas été retrouvée comme base exacte ;
le test reproduit les défauts avec les mêmes 36 passages.

- Contrat d'extraction v4 : citation avant reformulation, types/natures expliqués,
  absence d'alias de voix dans les entrées du modèle, auteur fixé depuis les
  sources. Critiques et descriptions restent des informations sans décision ni
  action future. Refus et citations introuvables conservés, jamais approuvés.
- Mise à niveau et reprise fiables, sans confondre les unités d'un ancien contrat
  avec celles du nouveau. Préparation partielle signalée. Réutilisation sans
  nouvelle inférence lorsque le contrat courant est déjà terminé.
- Sources, propositions actuelles, corrections et propositions antérieures dans
  des vues séparées. Anciennes fiches machine conservées, hors rédaction automatique ;
  toute intervention humaine reste protégée. Aucun schéma SQL modifié.
- Guide en six étapes, progression par phases, bilan des créations et motifs de
  non-extraction, actions contextuelles, accès direct à l'audio et fiches liées.
  Approfondissement défilable et commandes d'approbation accessibles.
- Approbation refusée sur les incohérences de références, occurrences ambiguës,
  intervalles nuls, voix inconnues et formulations refusées par les contrôles
  statiques existants. Aucun contrôle de rédaction/export supprimé.
- Défaut Windows découvert en recette : les noms UUID longs des artefacts de
  contrôle Qwen produisaient des chemins natifs trop longs. Noms de fichiers
  raccourcis, identifiants de source/information conservés intégralement en base.

### Résultats réels sur copies isolées

- Premier essai v3 **non concluant** : une seule nouvelle proposition refusée,
  201,560 s ; les réponses sont conservées. La consigne trop restrictive rejetait
  à tort critiques et descriptions faute d'action future ; elle a été remplacée.
- Préparation v4 : **385,658 s**, 14 unités sur 14, **36 passages conservés**,
  **20 nouvelles fiches**, 13 avec citation retrouvée, **9 sans blocage structurel**,
  **11 à corriger / rattacher**. **25 propositions antérieures** conservées séparément.
  Aucun statut humain approuvé. Les neuf fiches ne sont pas neuf vérités certifiées.
- Reprise finale : **2,491 s**, réutilisation explicite, aucune nouvelle inférence,
  aucune nouvelle fiche. Ne pas comparer cette durée à une extraction à froid.
- Contrôle Qwen d'une fiche sur les véhicules amortis : **34,061 s**, soutien
  provisoire sur les quatre axes ; attribution incertaine, donc non admissible
  sans intervention humaine. L'échec antérieur de chemin Windows est conservé.
- Contrôle d'une autre fiche sur les associations : **50,045 s**, variante sourcée
  conservée séparément, une information admissible selon les règles existantes.
  Rédaction réelle : **un paragraphe partiel en 57,365 s**. Refus PDF **et** DOCX
  sans relecture confirmée. Aucune information ni document municipal approuvé
  automatiquement. Ceci ne vaut pas un PV complet ou une validation de fidélité.
- Suite complète : **330 tests réussis en 11,35 s**, `final.xml` / `final-tests.log`,
  dont 24 nouveaux cas. Tests des filtres/actions, données historiques, citations,
  absence d'approbation implicite, refus avant rédaction/export, reprise, contrôle
  des chemins natifs et progression. Les trois premières attentes UI adaptées
  concernent des actions maintenant désactivées avec motif visible. Premier rapport
  conservé ; les invariants de sécurité n'ont pas été relâchés.
- Vues PySide6 rendues et inspectées sur la copie municipale, sans approbation.
  Aucune réexécution Whisper/sherpa/Community, aucun nouveau modèle.
- Conservation contrôlée sur **1 746 fichiers** : six changements du cœur dans
  le périmètre autorisé registre/UI, aucun autre changement inattendu. Moteurs
  audio et rédacteurs partagés inchangés ; trois révisions initiales du registre
  et 36 interventions conservées identiquement dans la copie, MP3 original intact.
  `preservation.json` contient la preuve. Un lanceur `Ouvrir-la-recette.cmd` ouvre
  uniquement la copie municipale pour la vérification humaine.

### Limites et suite opérateur

Les 7 nouvelles fiches sans citation retrouvée restent bloquées ; les autres
blocages incluent des horaires nuls, des voix inconnues et des erreurs de nature.
Les 12 passages sans citation rattachée restent consultables. Ces comptes ne
mesurent ni couverture du débat ni fidélité sémantique. Qwen 4B conserve des
erreurs réelles : lire et écouter les propositions, corriger puis approuver
uniquement celles effectivement vérifiées. Les décisions et votes restent saisis
séparément, et la relecture du document est obligatoire.

Le correctif est dans les sources, à lancer avec `scripts/run.ps1`. Aucun nouveau
bundle ni installateur compilé ici. Les anciens exécutables restent inchangés.
Recette complète avec validation humaine du registre et du PV toujours à effectuer ;
Windows vierge déconnecté et commercialisation restent non validés.

## Intégration ciblée Large-v3 + Community-1 — 21 octobre 2026

### Fonctionnel dans l'application source

- Paramètres persistants **Automatique / CPU / GPU NVIDIA**, sans migration SQL.
  CPU : Small int8 + sherpa existants ; GPU : Large-v3 float16 + Community-1,
  français, modèles et paramètres locaux du laboratoire, sans WhisperX.
- Runtime GPU isolé du processus Qt et du worker CPU. Vérification des hashes
  des modèles, versions des dépendances, calcul CUDA réel, support CTranslate2
  float16 et mémoire libre (seuil prudent 8 Gio, pas une garantie de capacité).
  L'admission automatique refusée sélectionne CPU ; une panne GPU en cours
  propose une **relance CPU explicite**, sans remplacer la transcription active.
- Phases, moteur utilisé et temps affichés. Annulation de l'arbre de processus,
  originaux et résultats intermédiaires conservés. Même préparation audio,
  alignement, sauvegarde transactionnelle, contrôle de montage et historique.
- Tours Community standards simultanés conservés, sans nombre de voix imposé,
  noms humains ni confiance inventés. Texte touchant un chevauchement laissé
  incertain, sans imposer une voix ni dupliquer le texte. Voix candidates visibles.
  Regroupement corrigé pour conserver aussi les tours GPU après une courte pause ;
  identifiants de ces métadonnées remappés avec les identifiants stables existants.
- Moteurs, prompts, registre et fonctions de rédaction **inchangés**. Références
  humaines et résultats du comparateur **inchangés** : contrôle de 1 695 fichiers
  protégés, des moteurs existants et des fonctions AST de rédaction / alignement.

### Essais réellement exécutés

Dossier de preuves neuf :
`output/gpu-integration-20261021/e1434b50c08946f78e574f9056b6d11b/`.

- **306 tests réussis en 12,90 s**, suite complète `tests/`, dont 38 nouveaux cas
  CPU/GPU et UI : sélection, kernels et versions simulés, admission refusée,
  mémoire insuffisante, chevauchements / changements de voix, formats invalides,
  erreurs/OOM injectées, annulation, conservation des corrections humaines,
  réglages, relance CPU explicite, cache neuf et variables d'authentification.
  Preuves finales `delivery.xml` / `delivery-tests.log`. Les premiers échecs de
  fixture (SHA d'import absent et statut `cancelled` attendu à tort `failed`)
  sont conservés dans les rapports antérieurs, puis corrigés.
- Inférence réelle dans deux nouvelles séances sur le MP3 municipal fourni,
  **336,039 secondes**, original et WAV commun vérifiés par SHA-256. RTX 5070,
  pilote **616.92** : GPU automatiquement sélectionné, **99,491 s**, 36
  interventions, 2 groupes, 1 intervention avec tours simultanés. CPU explicite :
  **133,217 s**, 68 interventions, 3 groupes. Ces comptes ne sont pas des scores
  de précision ; une exécution, caches non purgés et activité du poste non neutralisée.
- GPU : admission 10,637 s / CPU 10,281 s ; Large 53,805 s / CPU 51,953 s ;
  Community 30,108 s / CPU 28,563 s. Pics privés hôte échantillonnés : respectivement
  1 497 378 816, 7 594 459 136 et 5 310 222 336 octets. **Pic VRAM non mesuré**.
  Tous les workers GPU terminés de cette recette indiquent zéro tentative réseau
  Python. Ce garde n'est pas un pare-feu natif ni un test de PC déconnecté.
- Transcription intégrale préparée, refus PDF/DOCX sans relecture, réouverture,
  absence de votes/décisions inférés et intégrité des originaux vérifiés. PDF/DOCX
  produits dans une **base de fixture distincte**, confirmation marquée « TEST
  AUTOMATISÉ » ; aucune véritable séance approuvée automatiquement.
- Annulation réelle d'un worker Large après 12 s ; processus arrêté/récolté,
  requête conservée, aucun résultat validé. OOM matériel non provoqué ; les cas
  d'échec/OOM sont aussi couverts par injection. UI rendue et inspectée, réglages
  et passage simultané visibles. Import de l'interface sans torch/pyannote vérifié.
- Runtime Windows transportable assemblé depuis le Python de base et la fermeture
  installée : **95 distributions / 27 055 fichiers / 8 000 543 762 octets**, modèles
  exclus, sans WhisperX. Hors virtualenv, admission CUDA puis ASR et Community sur
  60 s municipaux réussis avec son propre worker, cache HF neuf et zéro tentative
  réseau Python. **484 fichiers PE** inventoriés ; syntaxe PowerShell du build vérifiée.
- Tours Community identiques au laboratoire. Large : mêmes 55 bornes de segments,
  mais texte `s27` et certaines probabilités / bornes de mots différents de l'essai
  précédent, consigné sans réécrire les résultats ni conclure à un gain de qualité.
- Raccord réel vers le registre Qwen inchangé sur une autre copie : 14/14 unités,
  24 informations à vérifier, **411,515 s**. La rédaction est refusée après 2,558 s
  (`REGISTRY_NO_ELIGIBLE_INFORMATION`) : aucune information approuvée ou vérifiée
  admissible. Checkpoints et refus conservés. **PV de cette séance non produit** ;
  une intervention humaine sur le registre reste nécessaire, sans contourner la porte.

### Packaging, droits et limites

Guide : [audio-gpu-integration.md](audio-gpu-integration.md) ;
audit : [audio-gpu-licenses.md](audio-gpu-licenses.md). Commande de build préparée
avec `-Development -IncludeGpu`, mais **pas de nouveau bundle PyInstaller ni de
Setup compilé ici**. Les anciens bundles restent inchangés ; utiliser
`scripts/run.ps1` pour le code source actuel.

Manifeste GPU épinglé, notices initiales et inventaire de staging disponibles.
Commercialisation toujours non approuvée : obligations CC BY / MIT, DLL NVIDIA
(cuDNN 9.10.2.21 observé), articulation installateur CPU/GPU, provenance/codecs et
sources FFmpeg, Python et notices transitives à finaliser. FFmpeg du wheel GPU
annonce LGPL v3 mais inclut x264/x265 dans sa configuration : analyse du lot exact
indispensable. La limite Inno d'environ 4 Go pour un Setup.exe unique doit aussi
être confrontée à la taille compressée finale, non mesurée. Aucun téléchargement
ou fichier annexe n'est proposé comme satisfaction du fichier unique demandé.

**Windows vierge physiquement déconnecté, avec et sans GPU : non validé.**
Précision municipale et relecture du PV : non validées. Aucun nouveau choix de
qualité déduit des temps ni remplacement de la référence de qualification.

## Diagnostic Parcoursup isolé — 20 octobre 2026

Expérience **hors pipeline applicatif**, scripts dans
`experiments/parcoursup_20261020/`. Rapport détaillé, trois synthèses brutes,
tableau de comparaison/CSV/JSON, références audio et diagnostic des 24 refus :
`output/diagnostic-parcoursup/2026-10-20-01/comparaison-v2/rapport-comparatif.md`.
La référence narrative humaine du Desktop est conservée ; l’utilisateur a ensuite
fourni `correction.txt` après la demande de correction sur écoute. Copie exacte,
SHA-256, provenance et différences archivés. Aucune écoute revendiquée par l’agent.

Fenêtre 17:31.960–20:37.580 : A original sauvegardé = 109 passages ; B correction
humaine = 103 ; six fragments absents inventoriés, aucun original remplacé.
C = B strictement identique + 58 passages du contexte original avant l’extrait.
**Ce contexte supplémentaire n’est pas corrigé à l’écoute** ; aucun contexte
transcrit après 20:37.580 n’existe dans les 670 passages. Le contexte propre des
deux côtés n’a donc pas été testé. Les horodatages ASR sont conservés, sans
ré-alignement des mots corrigés. A garde ses anciennes attributions/corrections :
il n’est pas présenté comme une sortie Whisper brute jamais modifiée.

Trois inférences CPU réellement terminées, mêmes instruction/schéma/paramètres,
4 threads, GPU 0 couche, contexte 12288, budget 3000, graine 42, aucun cache de
réponses. Tours consécutifs regroupés sans perte de mots ni sélection d’entrées,
correspondance Txxx → segments/horaires conservée. Référence humaine non transmise
à Qwen ; pas de Qwen utilisé comme juge.

| Variante | Durée native écoulée | CPU user + kernel | Tokens entrée / génération |
|---|---:|---:|---:|
| A original | 397,251 s | 1542,422 s | 2586 / 2628 |
| B correction humaine | 322,237 s | 1250,016 s | 2350 / 2303 |
| C correction + contexte original | 513,590 s | 1986,531 s | 3569 / 2841 |

Une mesure par condition, cache disque Windows non purgé, poste non isolé.
Premier A à fragments séparés : **échec par délai à 900,409 s natives**,
3526,922 s CPU, sortie partielle conservée. Ce protocole antérieur n’est pas
mélangé à la comparaison commune v2.

**Constats, selon l’analyse des sources humaines par Codex :** ouverture de places
et sectorisation présentes dans les trois essais. Centralisation des vœux correcte
dans A, transformée en maintien obligatoire de Parcoursup dans B, perdue dans C.
B attribue à Manès la sélection faible affirmée par Louise. C transforme une
question de Louise en proposition d’abrogation et rattache abusivement un propos
politique du contexte à Parcoursup. Il restitue mieux l’exception des lettres de
motivation, mais les relations et les propositions restent peu fiables.
Audit mécanique : 0 / 5 / 8 signalements ; zéro erreur littérale ne démontre pas
le soutien sémantique. Tableau justifié sur onze points narratifs et deux points
de la copie humaine ; pas de score global de fidélité ni d’amélioration mesurée.
Ce codage analytique n’est pas une nouvelle notation humaine aveugle des sorties.

24 refus étudiés individuellement : **18 justifiés en l’état, six motifs
potentiellement excessifs/mixtes**, selon cette analyse, aucun réintroduit.
Pertes à l’extraction (centralisation, cours/ramassage +1 h), groupes hétérogènes
et erreurs sémantiques distinguées. Les six motifs ne sont pas six phrases
déclarées admissibles. Recommandation : conserver 4B comme référence expérimentale,
tester des règles générales de prompt et un autre modèle Instruct local en
contre-épreuve avant choix du moteur ; aucun autre modèle testé ici.

**10 tests de protocole réussis en 0,33 s** : copie exacte, inventaire, regroupement
sans perte, noyau B/C identique, parseur, PCM exact, résolution des citations et
conservation. Une erreur initiale d’import de test puis une erreur de répertoire
temporaire sandbox ont été corrigées/contournées avec traces conservées.
**61 contrôles finaux de conservation vrais**, dont sources applicatives, ancienne
base/résultat/bundle, audio et correction humaine. Suite applicative 268 tests
non relancée, aucun code de production modifié, aucune migration/base de séance
écrite, aucun nouveau bundle. Whisper/sherpa inchangés, biométrie non commencée,
relecture/export applicatifs non appelés. Aucun document approuvé ou vote créé.

La qualité d’un PV municipal et la recette Windows vierge hors ligne restent
non validées. Les sections suivantes conservent le bilan antérieur 0.2.5.

## Bilan antérieur — expérimentation livrée, résultat rédactionnel insuffisant

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

## Laboratoire transcription/diarisation — 20 octobre 2026

Expérience indépendante : `experiments/audio_benchmark_20261020`. Aucun moteur
applicatif modifié, aucune base/séance ouverte en écriture et aucune recompilation.
Les essais comparatifs de synthèse Qwen/Gemma restent distincts de ce laboratoire.

### Corpus et références conservés

- Même PCM BFMTV, durée réelle **20 min 40,017 s**, SHA-256
  `95da1f0787fd22ad313acfd367fda3012b47587660cb9b1a2d6e6001bf0e708a`.
  Copies exactes 60 s à 18:00, puis 180 s à 17:31,960, puis totalité ; aucune
  réduction arbitraire du fichier long. MP3 d'origine jamais remplacé.
- Référence narrative et correction humaine Parcoursup copiées sans modification.
  Douze formulaires initiaux encore non annotés avec frontières/verbatim exacts :
  **WER, DER, cpWER et cpCER non mesurés**, conformément à la clarification utilisateur.
- Comparaison **textuelle** aux documents humains effectuée ; douze vues avec audio,
  transcriptions A/B et sorties C disponibles préparées dans `review`. Aucune
  écoute par l'agent revendiquée. Interruptions et chevauchements non certifiés.
  Aucune autre réunion naturelle française fournie.

### Exécutions réelles

Poste : i5-14600KF, 14 cœurs / 20 threads, 31,79 GiB RAM ; RTX 5070 12 227 MiB,
pilote 616.92, Windows 10.0.26300. CUDA réellement exécuté avec Torch 2.8.0+cu128
compatible sm_120. Trois environnements A/B/C séparés, quatre threads demandés,
processus neufs dans un Job Windows limité à 12 GiB engagés avant démarrage,
annulation et préservation des résultats partiels.

| Chaîne | 60 s | 180 s | 20 min 40 s |
|---|---|---|---|
| A — Small + sherpa actuel, CPU | Réussite | Réussite | Réussite, **616,85 s** écoulées cumulées |
| B — Large-v3 + Community-1, CUDA | Réussite | Réussite | Réussite, **154,66 s** sans WhisperX |
| B — avec alignement WhisperX, CUDA | Réussite | Réussite | Réussite, **188,62 s** étapes cumulées |
| C — MOSS officiel 0.9B, CUDA/SDPA | Réussite | Réussite, **89,19 s** | **Échec CUDA OutOfMemoryError**, 25,96 s |
| B et C, contrôles CPU | Réussites réelles | Non exécuté CPU | Non qualifié CPU long |

CPU 60 s : Large-v3 68,61 s, Community-1 26,15 s, WhisperX 13,37 s ; MOSS FP32
83,00 s. Ce sont des tests d'inférence réels, pas des tests d'import uniquement.
Le fichier long MOSS réclame une allocation CUDA supplémentaire de 15,96 GiB
sur une carte de 11,91 GiB utilisables ; aucune transcription longue n'est annoncée.
Pas de découpage caché ni de troncature présentée comme une réussite.

Mesures conservées par étape : durée écoulée, CPU utilisateur/noyau du Job,
pic engagé noyau et RSS échantillonnée. Le temps actif des kernels GPU et le pic
VRAM global ne sont pas mesurés ; les intervalles CUDA et pics d'allocateur Torch
de MOSS sont conservés avec leur portée limitée. Tailles logiques des dépendances :
A 330 783 618 B, B 8 065 430 665 B, C 7 941 748 579 B, hors modèles/interpréteurs.
Les liens physiques uv peuvent partager les blocs disque. Détails dans les inventaires.

Les étapes longues GPU et contrôles CPU ultérieurs sont séquentiels, mais A long
a chevauché des pilotes GPU courts : contention possible. Aucun rapport de vitesse
CPU/GPU à matériel égal. Pas de répétitions statistiques ni de purge des caches
OS/CUDA/JIT ; « processus neuf » ne signifie pas mesure à froid complète.

### Observations et limites de qualité

- A complet : 583 segments ASR, 442 tours diarisation, cinq groupes ; rapprochement
  692 interventions, dont **47 de durée nulle**, 285 signalées incertaines. Le nombre
  diffère des 670 passages historiques édités ; les sources ne sont pas modifiées.
- B complet : 476 segments ASR, 206 tours standard/167 exclusifs, cinq groupes.
  Quatre variantes avec/sans WhisperX et standard/exclusif conservées. Avec WhisperX,
  zéro intervention de durée nulle, **dix segments à alignement incomplet conservés
  en entier et signalés** ; tout le texte reconnu préservé à espaces près.
- C trois minutes : 54 segments, six groupes ; fusion de Sonia et Louise sous S01,
  et fragmentation de réponses brèves. C n'est pas précis du seul fait de six groupes.
- Contre-exemples humains documentés : A fusionne Arthur/Manès ; B complet fusionne
  l'intervenante évoquant l'Outre-mer avec Louise et fragmente des réponses au mot près.
  B trois minutes écrit « noms » au lieu de « notes », mais le fichier complet écrit
  « notes ». C écrit « premier serviteur » et « on approche » face à « premier servi »
  et « on abroge » humains. Pas de score de gain, ni jugement d'un moteur utilisé
  comme vérité terrain. Les voix naturelles et chevauchements restent non validés
  acoustiquement tant que l'écoute humaine annotée n'est pas réalisée.

Recommandation **expérimentale** : approfondir B avec WhisperX sur ce matériel,
en conservant A en production ; priorité aux annotations de changements de voix
E01/E04/E09/E10/E12 et à une réunion municipale naturelle. La préférence technique
ne valide ni la qualité, ni le repli CPU long, ni un remplacement applicatif.

### Incidents conservés, tests et licences

TorchCodec ne charge pas ses DLL de décodage FFmpeg sur ce Windows. L'entrée
tenseur officielle Community-1 fonctionne réellement, comme le WAV en mémoire
de WhisperX ; le décodeur direct n'est pas qualifié. Community-1 acquis après
acceptation HF par l'utilisateur, sans jeton dans le dépôt, commandes ou résultats.
Acquisition explicite séparée des inférences locales avec blocage Python réseau.
PC connecté de développement : pas de recette Windows vierge physiquement déconnecté.

Tests ciblés finaux : **8 réussites en 1,93 s**, rapport
`output/audio-benchmark/2026-10-20-01/tests-lab-06.xml`. Quota mémoire natif avec
allocation effectivement refusée, annulation du processus détenu, copies PCM
exactes, hashes, préservation des textes sur les trois portées et des segments
sans mots alignés, absence de scores de précision injustifiés. Pas de suite
applicative/recompilation revendiquée pour cette expérience sans changement produit.

Les incidents du contrôleur et des tests restent archivés : constante Python
`CREATE_SUSPENDED` non exposée corrigée avant A-v2 ; répertoire temporaire partagé
Windows inaccessible contourné par un dossier neuf dans le laboratoire ; assertion
incorrecte sur le compteur de pic mémoire remplacée par la vérification du quota
configuré **et du refus réel d'allocation avant 128 MiB de charge utile**. Pas de
relèvement de la limite native pour obtenir des tests verts. Premier adaptateur
WhisperX avec mots accolés archivé en `*-spacing-pilot`, correction des séparateurs
couverte par les tests ; aucun texte brut d'inférence réécrit.

Révisions, SHA LFS et licences des modèles acquis vérifiés. Licences des paquets
archivées ; réserves NVIDIA/FFmpeg et données entraînées NLTK documentées dans
`audio-benchmark-20261020-licenses.md`. Aucun lot commercial approuvé.
Vérification finale des hashes de sources Python, manifestes produit, références,
audio et actifs acquis : tous identiques aux empreintes enregistrées.

Livrables dans `output/audio-benchmark/2026-10-20-01/` :
`rapport-comparatif.md`, `mesures.json`/`.csv`, `chain-totals.json`, `model-sizes.json`,
`transcriptions.md`, `uncertitudes.json`, `diagnostic.json`, `review/index.md`,
`preservation.json`, sorties brutes et traces dans `runs`, variantes B dans `combined`.

## Qualification humaine comparative — interface du 20 octobre 2026

Outil autonome dans `experiments/audio_qualification`, séparé du produit et des
résultats précédents. Lancement : `Ouvrir-le-comparateur.cmd` dans ce dossier ou
`.venv\Scripts\python.exe -m experiments.audio_qualification.app` depuis le dépôt.
Guide complet et conventions : `experiments/audio_qualification/README.md`.
Aucun modèle ni pipeline applicatif modifié ; aucun nouveau modèle téléchargé,
aucune base utilisateur ouverte, aucune recompilation ni installation de dépendances.

### Fonctionnel et réellement vérifié

- Trois colonnes : Small+sherpa, Large-v3+Community-1, Large-v3+WhisperX+Community-1.
  Même WAV PCM du benchmark, même SHA, horloge absolue commune. Douze zones
  proposées, limites ajustables ; création de zones supplémentaires sans double
  comptage. Les identifiants techniques restent propres à chaque chaîne.
- Lecture commune, recherche, retour/avance de 2 s, vitesse, boucle, suivi et
  surlignage des passages. Double-clic pour relire une intervention. Choix de la
  sortie audio et du volume. Les interventions longues s'affichent intégralement.
- Éditeur humain séparé : verbatim, voix avec noms confirmés ou pseudonymes,
  tours de parole pouvant se chevaucher, horaires des mots facultatifs,
  catégories interruption/chevauchement/passage court/nom propre et observations
  par chaîne et type d'erreur. Aucun texte ou horaire moteur ne préremplit la référence.
- Hypothèses masquées au départ pour réduire le biais d'annotation. L'exposition
  est conservée dans la provenance des validations ; masquer après coup ne
  l'efface pas et ne transforme pas une annotation assistée en annotation aveugle.
- Base SQLite **distincte**, identifiant d'application vérifié, transactions,
  révisions avec parent/hash/date/auteur ; contrôle de concurrence. Autosauvegarde
  et brouillon brut avant interprétation des cellules : saisie numérique incomplète
  récupérée réellement à la fermeture/réouverture. Refus d'ouvrir une base étrangère.
  Les révisions antérieures ne sont jamais réécrites. Les changements pertinents
  retirent les validations, et un rapport d'une ancienne référence porte un bandeau.
- Export de la référence figée : JSON avec provenance, UEM/RTTM des zones voix
  revues, verbatim revu et mots TSV. Les fichiers du benchmark restent en lecture seule.

### Mesures préparées, pas de précision annoncée

Calcul annulable dans `.venv-lab-b`, processus limité à 2 GiB engagés et 120 s,
sans chargement de modèle ; empreintes des hypothèses/audio vérifiées et réseau
Python interdit. Rapports par révision dans
`output/audio-qualification/2026-10-20-01/comparaisons/<id>/report/` :
`scores.json`, `rapport.md`, CSV par zone, référence exportée et traces séparées.
Le rapport est également affiché dans l'interface.

- **WER** : seulement verbatim exhaustif revu, normalisation française explicite,
  S/D/I et mots erronés consultables. Portée commune aux trois chaînes ; blocage
  d'une frontière sans horaires de mots exploitables. Pas de WER linéaire sur
  paroles simultanées. Une zone silencieuse contribue des insertions, sans
  fabriquer un taux lorsqu'il n'y a aucun mot humain au dénominateur.
- **DER brut** : pyannote.metrics, UEM des seules zones activité/voix revues,
  collerette 0 s, chevauchements inclus, permutation optimale globale sur le même
  enregistrement, pas par extrait. Confusion, parole manquée et fausses alarmes
  présentées séparément, avec secondes de voix humaines et couverture.
- **WhisperX** : même texte Large-v3 et mêmes tours Community-1 ; mêmes WER/DER
  bruts par construction. Gains éventuels mesurés séparément sur les mots humains
  horodatés : erreurs début/fin, bornes à ±100/250 ms avec couverture, erreur
  conditionnelle d'attribution des mots corrects. Horaires absents jamais devinés.
  Surcoût du benchmark conservé : **33,96 s / 21,96 %** des étapes B sans alignement,
  une seule exécution ; pas un gain de précision ni un ratio CPU/GPU égalitaire.
- Sous-ensembles des cas difficiles, erreurs de transcription et erreurs de voix
  séparés. Aucune extrapolation aux portions non annotées ou aux autres réunions.
  cpWER/cpCER restent non mesurés.

### Tests exécutés et limites

**23 tests ciblés réussis** : 13 éditeur/stockage/intégrité, 10 numériques.
Preuves dans `output/audio-qualification/2026-10-20-01/` :

- `editor-tests-04.xml` : 13 réussites, 2,26 s ; relecture et invalidation, versions,
  concurrence, base étrangère inchangée, brouillon récupéré, synchronisation,
  absence de préremplissage, sources modifiées bloquées, rapport périmé signalé,
  exposition aux hypothèses non effaçable par restauration et sélection conservée
  lorsqu'une révision antérieure ne contient pas la zone nouvellement créée.
- `scoring-tests-03/{stderr.txt,measurement.json}` : 10 tests unittest réussis,
  1,397 s pour la suite. Cas à vérité artificielle **uniquement pour vérifier
  les algorithmes** : permutation globale, chevauchement, silence, zones partielles,
  normalisation, mots manquants, catégories et dissociation WER/DER/alignement.
- `qa/2adfd57cb34a4f8d953e66551d464cef/result.json` et PNG : rendu Qt inspecté,
  décodage et recherche réels dans le WAV commun, progression 1 090 000 →
  1 090 866 ms, trois colonnes synchronisées, sortie Logitech réelle, lecture
  **son coupé**. Cela ne certifie pas une écoute humaine ni la fidélité acoustique.
- Rapport lancé depuis l'interface et affiché dans son onglet de résultats,
  référence vide : tous les WER/DER restent non mesurés ; zéro tentative réseau
  Python, hypothèses inchangées. Les rapports de recette ne sont pas des résultats
  d'annotation humaine du débat.

Incident conservé : l'import oublié de DOMAINS dans le premier test numérique
a été corrigé (rapport `scoring-tests-01`). La première recette de lecture avait
un curseur avançant mais des erreurs de conversion FFmpeg sur le casque 7.1 :
elle n'est pas une validation d'écoute. Le laboratoire utilise maintenant le
backend **Windows Media Foundation** dans son seul processus ; la recette
suivante sur le même casque donne BufferedMedia sans cette erreur. Aucun réglage
système ni lecteur de production n'a été modifié.

**Qualification de précision en cours** : aucune nouvelle référence exhaustive
horodatée n'a été remplie par l'agent. Il reste à annoter et écouter les extraits,
examiner les erreurs et la représentativité, puis recommander les routes CPU/GPU.
La voie CPU longue des nouveaux moteurs, les réserves de redistribution
(`audio-benchmark-20261020-licenses.md`) et la recette Windows vierge hors ligne
restent ouvertes. Le logiciel de production et tous les modèles acquis sont conservés.

## Correction du laboratoire WER sans horaires humains de mots — 20 octobre 2026

### Cause et périmètre

E11 et E12 ont bien un verbatim et des tours de voix validés humainement (2/3).
Le WER ne nécessitait pas de troisième validation des mots horodatés, mais
l'ancienne exclusion portait sur **tout l'extrait** dès qu'il contenait un
chevauchement. Les nouveaux rapports identiques résultaient d'entrées inchangées.
Le correctif porte exclusivement sur `experiments/audio_qualification` et sa
documentation : aucun moteur de production, aucune séance, aucune annotation
humaine ni ancien résultat n'est remplacé. Aucun modèle n'est téléchargé ou exécuté.

### Fonctionnement ajouté

- WER séquentiel sans horaires humains de mots : le texte et les voix revus
  suffisent pour les zones sans chevauchement réel. Les bornes lexicales des
  hypothèses utilisent les horaires déjà produits par les moteurs, communs pour
  Large-v3 avec/sans WhisperX. Leur disponibilité est vérifiée pour les trois chaînes.
- Les chevauchements sont isolés à partir des tours de **voix humaines distinctes**,
  sans écarter le reste de la zone : E11 1119.139–1124.499 ; E12
  1206.728–1211.158 et 1217.314–1217.490 secondes absolues.
- Assistant « WER sans horaires de mots… » : écoute du WAV commun, ajustement
  des bornes/scission, sélection de mots du verbatim original en lecture seule,
  auteur et confirmation humaine explicite. Les présélections assistées restent
  des propositions. Seules les portions approuvées entrent dans le score ; le
  rapport garde les portions en attente et les exclusions visibles.
- Découpages dans `decoupages-wer.sqlite`, base séparée avec versions, empreinte
  de la référence et contrôle de concurrence. Une modification invalide
  l'approbation concernée. Refus des chevauchements réels, doubles comptages et
  validations transférées d'une autre référence. Rapport avec copie figée du plan.
- Sept portions séquentielles et quatre trous de couverture proposés sur la
  référence actuelle. Aucun de ces découpages n'a été approuvé par l'agent.
  Le WER de cette référence reste donc **non mesuré avant validation du découpage**.
- Trous explicitement signalés : E11 1113.697–1114.839 et 1125.791–1128.709 ;
  E12 1201.380–1201.518 et **1225.251–1237.580 (12,329 s)**. Cette dernière
  plage correspond à **20:25.251–20:37.580** : du texte humain existe, mais les
  tours de voix s'arrêtent avant sa fin. Ces trous ne sont pas déclarés silencieux
  automatiquement. Les détections des moteurs sont des alertes à écouter.
- DER historique conservé avec avertissement **« indicatif, couverture incomplète »**
  lorsque de la parole moteur se trouve dans ces trous. Ne pas interpréter ce
  résultat comme une précision qualifiée tant que leur activité humaine manque.
  Les WER/DER bruts Large-v3 et WhisperX restent identiques par construction ;
  les diagnostics d'alignement restent séparés et facultatifs.

### Tests réellement exécutés

**39 tests réussis**, sans additionner les répétitions :

- 21 tests numériques unittest, 2,044 s : WER avec 2/3 et sans horaires humains,
  exclusion locale des chevauchements, approbation requise, portion partielle,
  rejet du double comptage et des approbations périmées, versions/concurrence,
  conservation du cas réel E12 avec trou de 12,329 s, non-régressions WER/DER.
  Processus isolé sous Job Windows 2 GiB / 120 s, 2,599 s écoulées.
  Preuves : `output/audio-qualification/2026-10-20-01/wer-correction/tests-numeriques-final/`.
- 18 tests PySide6 pytest, 3,42 s : 13 tests éditeur existants et cinq tests
  assistant (propositions non validées, sélection du texte humain, invalidation,
  scission avec historique, refus de calculer sans approbation).
  Preuve : `wer-correction/ui-tests-final.xml` dans le même dossier de qualification.
- Nouveau rapport sur une copie figée de la référence réelle : calcul terminé
  en 3,291 s, sans inférence ni approbation automatique. WER non mesuré et onze
  propositions en attente affichées ; avertissements DER et trous de couverture.
  Anciennes comparaisons conservées. Rapport :
  `wer-correction/61e6673431804c52b93c427101638356/rapport-corrige/report/rapport.md`.
- Recette Qt de l'assistant : rendu inspecté, recherche sur la fin E12 et
  progression réelles, sortie Windows, **son coupé** ; ce test ne certifie aucune
  écoute acoustique humaine. Images, JSON et base de test distincte dans
  `wer-correction/61e6673431804c52b93c427101638356/qa-decoupage/`.
- Conservation vérifiée par empreintes : référence humaine et toutes ses
  révisions inchangées, 91 fichiers de résultats antérieurs inchangés, 54 fichiers
  protégés du manifeste benchmark inchangés ; sources audio et hypothèses de la
  référence vérifiées. Preuve en lecture seule de la base d'origine :
  `wer-correction/61e6673431804c52b93c427101638356/preservation-after.json`.

Guide opérateur actualisé : `experiments/audio_qualification/README.md`.
Enregistrer puis relancer le comparateur pour charger le nouveau bouton.
L'étape humaine restante porte sur les bornes et le texte de chaque portion,
pas sur les horaires individuels de chaque mot. Aucun gain de précision annoncé.

## Audit et fiabilisation du benchmark E11/E12 — 21 octobre 2026

### Conservation et protocole

Travail limité à `experiments/audio_qualification` et à la documentation. Aucun
moteur de production modifié, aucun modèle téléchargé ou exécuté, aucune séance
ouverte pour modification. Les sorties Small, Large-v3, Community-1 et WhisperX
déjà calculées sont réutilisées. La référence utilisateur et le plan WER sont
lus en SQLite lecture seule, puis copiés dans un dossier d'audit neuf :

`output/audio-qualification/2026-10-20-01/audit-20261021/21f4bec280774828ab47468b8414a2af/`.

Le dossier conserve `reference.json`, `wer-plan.json`, le plan de l'ancien
rapport et `before.json`. Aucune approbation n'est donnée par l'agent.

### Défauts identifiés

- **E11-P01 : 60 mots sélectionnés, 91 mots Large-v3.** Le verbatim humain
  comporte ensuite **39 mots [60,99)** de « non non atendez… » à « mais avant »
  qui ne sont sélectionnés dans aucune portion. P01 couvre pourtant les deux
  premiers tours humains, jusqu'à 1113.697 s, sans chevauchement réel. Les
  alignements contextuels retrouvent 23 de ces mots dans les bornes avec Small
  et 32 avec Large. Cela soutient fortement une omission de sélection, mais ne
  certifie pas les paroles ou les frontières : écoute ciblée requise avant tout ajout.
- E12-P01 omet « c'est une vrai question » de sa sélection alors que les sorties
  en placent une partie dans ses bornes. E12-P04 et la frontière P05/P06 montrent
  aussi des mots sélectionnés hors bornes et des mots voisins non sélectionnés
  à l'intérieur. Le rapport détaille les onze portions, leurs mots sources et
  chaque mot moteur traversant une frontière ; ces indices ne sont pas une vérité audio.
- Toutes les portions WER validées excluent effectivement les chevauchements
  humains : **0 s** de chevauchement inclus dans chacune. On ne rejette pas les
  passages voisins. La sélection du milieu du mot moteur reste le protocole
  strict ; aucun horaire n'est déplacé pour améliorer les taux.
- Le plan courant n'est pas celui du rapport cité : **E12-P03 [21,43)** au lieu
  de **[21,42)**, donc « divers » est désormais inclus. Ce changement était
  enregistré avant l'audit ; il ne provient pas du nouveau normaliseur. L'interface
  signale maintenant un rapport périmé aussi lorsque seul le découpage change.

### Calculs ajoutés et résultats

WER strict conservé ; WER normalisé français version `fr-conservative-v1`,
symétrique, avec trace des transformations. Liste fermée d'accents/ligatures,
élisions préservant les négations, alias explicite parcours sup/Parcoursup,
entiers isolés 0–9999 et notation Nh. Pas de correction floue, d'accords ou de
typos humaines ; accents distinctifs conservés. Règles complètes dans le rapport
et `normalization.py`. Les dénominateurs distincts sont affichés.

| Chaîne | WER strict courant | WER normalisé courant | DER historique | DER qualifié partiel |
|---|---:|---:|---:|---:|
| Small + sherpa | 59,23 % | 56,38 % | 40,70 % | 30,45 % |
| Large-v3 + Community-1 | 58,54 % | 54,70 % | 59,53 % | 21,32 % |
| Large-v3 + WhisperX + Community-1 | 58,54 % | 54,70 % | 59,53 % | 21,32 % |

Courant : **287 mots stricts** (170 / 168 / 168 erreurs) et **298 tokens
normalisés** (168 / 163 / 163 erreurs). Les variations entre strict et normalisé
ne sont pas un gain de reconnaissance. Les deux variantes Large partagent
exactement les mêmes textes et tours ; leur égalité est attendue.

**Reproduction historique vérifiée séparément**, avec le plan du rapport cité :
286 mots, WER **59,79 % / 59,09 % / 59,09 %**, exactement identiques aux valeurs
antérieures. WER normalisés sur ce plan : **56,90 % / 55,22 % / 55,22 %**, N=297.
Ne pas mélanger les deux sélections dans une comparaison de moteur.

Le DER qualifié utilise seulement les tours humains revus et les silences
explicitement confirmés ; le silence de E12-P02 est inclus, la parole validée
pour le WER dans les autres trous n'apporte aucune identité. UEM identique
pour toutes les chaînes, permutation optimale globale sur ce masque, collerette
0, chevauchements conservés. **16,389 s inconnues exclues**, dont la fin E12
**20:25.251–20:37.580 (12,329 s)**. Le DER historique reste disponible, avec ses
fausses alarmes potentiellement artificielles dans ces trous.

- Couverture WER : **70,034 s / 1240,017 s = 5,65 %** du fichier, 87,54 %
  des 80 s E11/E12. Sélection lexicale : 287 / 383 mots humains = 74,93 %,
  avec anomalies de rattachement non corrigées et mots simultanés hors WER.
- Couverture DER qualifiée : **63,611 s = 5,13 %** du fichier, 79,51 % des
  zones E11/E12 ; 73,507 secondes de voix avec les doubles voix comptées.
- Small qualifié : confusion **10,642 s**, omission **11,350 s**, fausse alarme
  **0,391 s**. Large/WhisperX : **5,291 / 2,665 / 7,715 s** respectivement.
  Le meilleur taux partiel de Large coexiste avec davantage de fausses alarmes.
  Il ne mesure pas les erreurs dans les plages exclues, ni le reste du débat.

### Livrables et tests réellement exécutés

- `resultats-courants/report/{audit.md,rapport.md,scores.json,wer-strict-normalise.csv}` :
  tableaux par zone/portion, audit des bornes, corrections à confirmer, UEM
  qualifié et exclusions, provenance des normalisations et référence figée.
- `reproduction-historique/report/` : ancien plan reproduit, résultats d'origine
  conservés. Les premiers essais intermédiaires de cet audit sont aussi conservés.
- Onze WAV d'écoute ciblée avec contexte, copies PCM sans réencodage. Chaque
  échantillon a été comparé aux trames correspondantes de l'original : identiques.
  Horloge absolue et indices de trames documentés ; **aucune écoute acoustique
  humaine effectuée par l'agent** et aucune annotation automatiquement corrigée.
- **56 tests réussis** : 36 unittest numériques (1,831 s) dans le processus
  isolé 2 GiB / 120 s ; 20 pytest PySide6 (2,54 s). WER strict/normalisé séparés,
  négations, accents distinctifs, nombres signés, alias limités, provenance,
  cas 60 contre 91 mots, mots traversant une borne, silence explicite et trous
  exclus, DER avec chevauchements, historique/concurrence, rapport périmé après
  changement de découpage et liens audio locaux sans accès réseau/traversée.
  Preuves : `tests-numeriques-final/` et `tests-ui-verifies.xml` dans le dossier d'audit.
- Calcul courant : environ 3 s, zéro tentative réseau Python, sans inférence.
  Mesures précises CPU/mémoire dans `resultats-courants/process/measurement.json` ;
  les temps des moteurs restent ceux du benchmark initial, pas ces temps de score.
- Rendu PySide6 du nouveau tableau inspecté sur une base de test séparée,
  avec police chargée seulement pour la recette offscreen. Le premier rendu
  offscreen avait des glyphes manquants ; il est conservé, pas présenté comme
  une validation visuelle. Preuve lisible : `qa-rapport-police/rapport.png`.
- Premiers échecs de fixtures conservés : trois références artificielles avaient
  été modifiées sans invalider leurs validations ; les fixtures passent par
  `update_zone`. Un test de lien comparait des chaînes Windows avec séparateurs
  différents ; il compare maintenant les chemins résolus. Contrôles de production inchangés.

**Conclusion : indice mesuré favorable à Large sur le masque DER qualifié, mais
gain global de qualité non établi.** Priorités humaines : vérifier le passage
non sélectionné de E11-P01, les rattachements E12-P01/P04/P05/P06 et les voix de
la fin E12 ; recalculer ensuite sur une nouvelle révision validée. Pas de
correction automatique ni de remplacement du moteur opérationnel.

Contrôle final de conservation : référence, totalité des révisions et plan WER
inchangés ; **178 fichiers antérieurs** (dont les bases d'annotation) et **49
fichiers Python de production** inchangés par empreintes. Toutes les entrées de
la référence vérifiées ; reproduction exacte des trois couples WER/DER
historiques et aucun chevauchement humain dans les onze portions WER.
Preuve : `verification-integrite.json` dans le dossier d'audit.
Calcul courant final : **3,022 s écoulées, 2,469 s CPU**, pic mémoire engagée
Job Windows **1 450 684 416 octets**, zéro tentative réseau Python.

## Reprise ciblée BFMTV et premier cas municipal — 21 octobre 2026

### Fonctionnalités du laboratoire

Modifications limitées à `experiments/audio_qualification` et aux documents.
Les moteurs, les séances et les fichiers de production ne sont pas modifiés.
Les modèles déjà présents sont réutilisés ; aucun téléchargement ni installation.

- **Corrections ciblées…** : six vérifications préparées pour la référence BFMTV
  actuelle : E11-P01 et ses 39 mots hors sélection, deux ensembles de frontières
  E12, trois plages sans voix attribuée. Accès direct au passage audio et à la
  portion dans l'assistant. Une sélection élargie peut être préparée explicitement,
  mais l'ouverture ne change ni sélection ni approbation. Verbatim en lecture seule.
- Ajout local de tours manquants avec nom du relecteur et confirmation d'écoute.
  Les tours existants et la validation du texte restent inchangés ; la relecture
  complémentaire conserve la provenance de la relecture antérieure dans une
  nouvelle révision. Pas de prétention à une nouvelle écoute intégrale de la zone.
- Conservation des validations WER inchangées **uniquement après confirmation
  explicite** (case décochée au départ). Refus si texte, bornes ou audio changent ;
  une portion devenue chevauchante ou contradictoire reste à revoir avec la raison.
  Plans/révisions d'origine conservés. Aucun transfert ou nouvelle approbation
  réalisé par l'agent sur la référence utilisateur.
- Journal local séparé : contrôles corrigés, inchangés ou différés, temps écoulé
  déclaré et attributions importantes par chaîne. Les annotations initiales ne
  comptent pas comme corrections moteur. Les nombres restent déclaratifs, non
  exhaustifs ; un rapport périmé est signalé si référence, plan **ou journal** change.
- **Nouveau test municipal / ouvrir un test…** : import WAV/MP3/M4A via PyAV
  local, original copié et haché, WAV PCM commun 16 kHz mono. Projets, paliers,
  essais, références, plans et journaux isolés de BFMTV. Chaque essai est neuf.
- Exécution 60 s → 180 s → fichier complet, cinq composants par palier dans
  leurs environnements existants : Small, sherpa, Large-v3, Community-1, WhisperX.
  La reconnaissance Large et la diarisation Community sont partagées par B/B+X.
  Jobs Windows annulables : 4 GiB A, 12 GiB B, 900 s pilote, 3600 s complet.
  Sorties vides/horaires invalides/erreur moteur bloquent la suite et restent conservés.
- Route CPU obligatoire pour A, choix CPU/CUDA explicite pour B, aucun faux
  succès GPU après repli. Aucun nombre d'intervenants imposé.
- Six extraits temporels vierges de 25 s proposés, avec sélection humaine
  possible d'au plus six plages non recouvrantes. Indices ASR « proposition »,
  « délibération », « vote » et changements de voix clairement hypothétiques.
  Leur origine assistée est conservée ; aucune identité ni décision n'est déduite.
  Le sélecteur refuse de remplacer une référence déjà annotée.

Protocole réel/simulation jouée, situations simples, changements de voix,
propositions, délibération et vote : `docs/protocole-qualification-municipale.md`.
Il demande de constater ou marquer absent un vote, jamais d'en inventer un résultat.

### Enregistrement municipal fourni et traitements réellement exécutés

Fichier utilisateur : `Conseil municipal du 02 Octobre 2026 Maximi sur la  vente
de véhicules.mp3`, traité localement. Durée décodée **336,0391875 s (5 min 36 s)**,
donc **hors cible 10–15 min**. Pas d'étirement, de complétion ni d'annotation
inventée pour atteindre la cible. La présence d'un vote effectif et la couverture
des situations du protocole restent à vérifier humainement.

Dossier distinct :
`output/audio-qualification/municipal/e7f3eb95a94d49c48020b40cde29bddd/`.
Essai réel : `runs/e4edeb00b2d94601ad4b86b39eb7ec5a/`.

Les **15 invocations réelles isolées** ont terminé : cinq composants sur chacun
des trois paliers. Zéro tentative réseau Python dans les quinze sorties.
Les trois portes techniques sont passées ; aucune porte de qualité humaine
n'est considérée passée. Le texte reconnu Large est préservé après WhisperX.

| Chaîne complète | Route | Temps écoulé | Temps CPU cumulé | Pic mémoire engagée hôte |
|---|---|---:|---:|---:|
| Small + sherpa | CPU | 128,681 s | 373,016 s | 949 751 808 octets |
| Large-v3 + Community-1 | CUDA | 84,199 s | 79,250 s | 7 595 474 944 octets |
| Large-v3 + WhisperX + Community-1 | CUDA | 110,077 s | 103,688 s | 7 595 474 944 octets |

Temps des composants complets, distincts des paliers pilotes. Somme des durées
séquentielles, maximum des pics hôte, sans double inférence des composants
partagés. VRAM maximale non mesurée par ce compteur. Session de développement,
caches OS non purgés, pas une mesure « à froid » ni une comparaison à matériel
égal entre CPU et GPU. Aucun gain de précision déduit de ces durées.

`full/project.json` et `full/Ouvrir-ce-test.cmd` ouvrent la référence propre à
cet essai. Les six extraits sont vierges, sans voix nominative ni validation.
Les **WER strict/normalisé et DER qualifié municipaux restent non mesurés**.
Les quatre groupes Small et deux Community ne sont pas des scores de précision.

### Tests et recette

Preuves dans :
`output/audio-qualification/2026-10-20-01/qualification-municipale-20261021/589b0403cbce40a1bcafb52cb1589b7d/`.

- **73 tests réussis**, sans sommer les répétitions : 46 unittest numériques,
  2,130 s (`tests-numeriques-recette/`), 27 pytest PySide6, 4,03 s
  (`ui-tests-livraison.xml`). Non-régressions WER/DER, verbatim et tours antérieurs
  conservés, correction locale explicitement autorisée, transfert WER interdit
  sans accord, nouveau chevauchement invalidant la portion, projets/plans
  indépendants, historique/journal, échec bloquant les paliers, sélection sans
  annotation inventée et sans écrasement, rapport périmé après journal modifié.
- Import réellement exécuté depuis **QProcess/PySide6**, fixture technique WAV
  48 kHz stéréo → 16 kHz mono, sans lancer de modèle et sans modifier l'original.
  La fixture silencieuse ne mesure pas la qualité des moteurs.
- Défaut découvert puis corrigé : un gestionnaire `finished` dans `QDialog`
  entrait en collision avec son signal Qt natif. Le processus terminait, mais
  l'interface ne libérait pas son état occupé. Renommé `process_finished`, puis
  recette réelle réussie. Premier échec conservé dans `ui-tests-recette.xml`.
- Un test a révélé des connexions SQLite de journal non fermées à la sortie
  d'un bloc transactionnel ; fermeture explicite ajoutée et tests Windows passés.
  Les premiers essais utilisaient le temporaire restreint du bac à sable ; les
  temporaires finaux sont dans le workspace, preuves d'échec conservées.
- Rendus de la file de six corrections et des trois colonnes municipales
  inspectés sur des **copies de référence de test**. Décodage réel du WAV
  municipal, même source, transport 65 789 → 66 555 ms, son coupé, sans erreur.
  Cela ne constitue pas une écoute acoustique humaine ni une annotation.
  Preuves : `qa-interface/result.json` et PNG.
- Rapport municipal initial généré et contrôlé : tous les taux de qualité sont
  non mesurés et les six annotations restent à faire (`rapport-municipal-initial/`).
- Conservation vérifiée : référence BFMTV, tête, toutes les révisions et plan
  inchangés ; **301 fichiers antérieurs** et **49 fichiers Python de production**
  inchangés par empreintes. Audio/hypothèses BFMTV et municipales vérifiés,
  original MP3 utilisateur identique à la copie. Preuve : `preservation-et-benchmark.json`.

### Reste à faire humainement

Corriger ou confirmer les quelques points BFMTV proposés, puis annoter quelques
extraits municipaux en conservant la référence indépendante. Examiner surtout
les attributions qui changent le sens d'une proposition ou d'un vote. Compléter
la cible 10–15 min et les situations absentes si cet extrait ne les couvre pas.
Recalculer ensuite les taux et l'effort de correction sur une portée commune.
**Aucun choix automatique de moteur, aucune précision municipale déclarée validée,
aucune intégration produit ni recompilation.**
