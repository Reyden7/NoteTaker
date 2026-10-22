# Registre et rédaction — correctif du 21 octobre 2026

## Diagnostic

Le compteur d'informations et la table ne désignaient pas la même catégorie.
Après « Initialiser sans IA », le filtre restait sur les **sources intégrales**,
y compris après une préparation Qwen. Ces lignes restaient volontairement
« À classer » : ce sont des verbatims conservés, pas des informations approuvables.
La vue « À vérifier » mélangeait aussi les sources et les propositions.

Il existe également un défaut d'extraction réel. Dans la copie municipale locale
disponible pour la reproduction (36 passages, 24 informations), 23 propositions
étaient refusées : 6 codes de voix dans le contenu, 5 copies longues, 5 mauvais
rapports d'opinions, 4 citations introuvables, 2 descriptions devenues propositions
et 1 question transformée. Une seule restait en attente. Ce constat reproduit
le blocage ; il ne prétend pas être une inspection de la révision 8 de 23 fiches
signalée par l'utilisateur, dont la base exacte n'a pas été retrouvée.

Autres causes :

- L'extraction précédente n'expliquait pas assez les types et la nature du propos ;
  les alias `V1` fournis au modèle se retrouvaient dans le texte.
- Une préparation déjà marquée terminée n'était pas réextraite après un changement
  de consigne. La nouvelle version doit distinguer ses unités des anciennes.
- Le diagnostic « Aucune information extraite » signifiait parfois seulement
  « aucune citation rattachée », y compris lorsqu'une proposition rejetée existait.
  Il pouvait aussi apparaître sur des sources pas encore examinées.
- Les contrôles de rédaction restaient plus stricts que le bouton d'approbation.
  Une fiche pouvait donc sembler approuvable avant d'être refusée à la rédaction.
- Un contrôle Qwen réel a échoué sur Windows : les fichiers portant l'UUID complet
  dépassaient la longueur de chemin acceptée par llama.cpp (288 caractères pour
  un artefact). Les noms techniques de ces fichiers sont désormais courts ; les
  identifiants complets des informations restent dans les JSON et la base.

## Corrections

### Données et services

Contrat d'extraction **`typed-sourced-proposals-v4`**, modèle Qwen existant inchangé :
citation en premier dans le schéma, reformulation ensuite, définitions explicites
des types et natures. Critiques, questions, descriptions et opinions restent des
informations même sans action future. L'auteur vient uniquement des segments,
pas d'un nom proposé par Qwen. Une citation non retrouvée reste un refus visible.

Les 36 sources, références, horodatages et prises originales sont conservés.
Les fiches contiennent sujet, type, nature, auteur et état d'attribution, contenu,
citations exactes, horaires des segments, contrôles et historique. Les horaires
de citation ne prétendent pas être des horaires mot à mot.

Un changement de contrat réexamine les unités, sans supprimer les anciennes
propositions. Celles sans intervention humaine sont séparées dans **Propositions
antérieures conservées**, hors rédaction automatique. Les fiches corrigées,
approuvées ou verrouillées humainement restent protégées. Une action explicite
sur une ancienne proposition permet de la reprendre. Aucun statut humain n'est
créé par le modèle. Aucun changement de schéma SQLite : champs JSON optionnels
dans de nouvelles révisions, historique antérieur conservé.

Une reprise du même contrat déjà terminé conserve les fiches sans refaire les
inférences. Une extraction partielle n'est plus annoncée terminée et n'efface
pas l'état « non examiné » des autres sources. Un échec pendant la mise à niveau
ne peut pas faire passer les anciennes unités pour nouvellement traitées.

`services/registry_workflow.py` partage les diagnostics entre service et interface.
Une approbation est refusée si les références manquent, si le texte cité ne
correspond pas, si l'occurrence est ambiguë, si l'intervalle est nul, si la voix
est inconnue ou si les contrôles statiques de rédaction refusent la formulation.
Ces contrôles restent actifs lors de la rédaction. Un soutien Qwen reste
provisoire ; il ne constitue ni une approbation humaine de fiche ni une relecture
du document. Les décisions potentielles ne deviennent pas des décisions métier.

### Interface

- Sources et informations sont dans des vues distinctes, y compris « À vérifier ».
- Après préparation, ouverture des propositions actuelles, même si l'ancien
  filtre était Sources. Vues dédiées : propositions, corrections, approuvées,
  admissibles, sources et propositions antérieures.
- Étiquettes et couleurs différentes ; explication du blocage visible en permanence.
  Les actions « approuver » / « contrôle Qwen » sont désactivées sur un verbatim.
- Accès direct à l'audio et aux informations liées ; création manuelle explicite
  d'une fiche séparée, sans réécriture du passage source.
- Parcours en six étapes, bouton de rédaction activé seulement avec des éléments
  admissibles, progression de l'extraction et phases de préparation.
- Bilan persistant : créations, unités examinées, propositions, blocages et motifs
  des passages sans citation. Les avis d'extraction du modèle restent consultables.
- Texte long défilable, identité de l'opérateur et actions d'approbation accessibles
  indépendamment du défilement des détails.

## Utilisation

1. Lancer la version source avec `scripts/run.ps1`, importer puis transcrire.
   Les anciens exécutables ne sont pas mis à jour automatiquement.
2. Corriger et attribuer les voix dans **Transcription et voix**. Si les sources
   changent, le registre est signalé obsolète et doit être repris.
3. Dans **Registre des informations**, cliquer **Préparer / reprendre le registre**.
   Utiliser **Bilan de préparation** pour savoir ce qui a été produit ou refusé.
4. Dans **Propositions à vérifier**, lire la formulation, le type et la nature,
   puis **Écouter la citation sélectionnée** et examiner **Sources et contexte**.
   Les noms viennent de la transcription/annuaire ; aucune identité n'est déduite.
5. Corriger si nécessaire et enregistrer. Pour une citation manquante, utiliser
   **Ajouter une source** et sélectionner un extrait exact. Pour une attribution
   inconnue, revenir à la transcription. Une fiche signalée reste à corriger.
6. Après vérification réelle, renseigner **Opérateur** et **Motif**, puis approuver
   explicitement la fiche. Le contrôle Qwen facultatif fournit un avis provisoire,
   jamais une validation humaine. Lire aussi les réserves d'attribution.
7. **Rédiger depuis ce registre** produit un projet avec les seules informations
   admissibles. Les autres restent consultables ; leur omission n'est pas cachée.
8. Relire et corriger le document, saisir séparément décisions et votes vérifiés,
   puis confirmer sa relecture avant PDF/DOCX. Approuver une fiche ne valide pas le PV.

## Essais municipaux réels et limites

Preuves : `output/registry-workflow-20261021/4c9f7125b1934a5ab4c3939945cd8bfc/`.
Copie de la transcription GPU existante, sans nouvelle inférence audio ni
modification des références humaines du laboratoire.

| Essai | Résultat réel |
|---|---|
| Première consigne renforcée v3 | Trop restrictive : 1 proposition, refusée. 201,560 s. Réponses conservées ; échec non présenté comme amélioration. |
| Extraction v4 complète | 14 unités / 14, 36 sources ; **20 nouvelles fiches**, dont **13 avec citation retrouvée**, **9 sans blocage structurel**, **11 à corriger / rattacher** ; 385,658 s. Aucun gain de fidélité mesuré. |
| Réutilisation terminée | 2,491 s, **aucune nouvelle inférence** ; 20 fiches actuelles et 25 propositions antérieures conservées, aucune approbation humaine. |
| Contrôle de la fiche sur les véhicules amortis | Après correction du chemin Windows : 34,061 s, quatre axes soutenus selon Qwen ; attribution encore incertaine, donc fiche non admissible sans intervention humaine. |
| Contrôle d'une fiche sur les associations | 50,045 s, création d'une variante distincte, une information admissible provisoire ; aucune approbation humaine créée. |
| Rédaction sur cette seconde copie | **Un paragraphe partiel** produit en 57,365 s depuis l'information admissible ; PDF et DOCX sans relecture **refusés**. Ce n'est pas un PV complet ou validé. |

Les anciennes propositions restent conservées : la table compte au total 45
informations dans la copie de préparation (24 antérieures + 1 de l'essai v3 + 20
de v4). La copie de contrôle/rédaction contient en plus une variante. Les 12
passages sans citation rattachée restent accessibles ; cela ne mesure ni la
couverture sémantique ni l'importance des éléments manquants. Les erreurs de type,
citations et attributions restantes doivent être examinées, pas approuvées en masse.

Les neuf propositions sans blocage structurel ne sont **pas neuf informations
certifiées fidèles**. La fidélité de toute la séance n'a pas été validée humainement.
Le moteur 4B a encore produit des citations absentes et des reformulations douteuses.
Aucune correction des noms ou de l'audio n'a été faite automatiquement pour les
faire passer. Pas de comparaison de précision ni d'avis du modèle pris pour vérité
terrain. Les durées ne sont pas des mesures à froid ; la reprise est explicitement
distinguée de nouvelles inférences.

## Tests

La suite `tests/` couvre aussi les invariants audio, les migrations, corrections,
historique et exports existants. Nouveaux cas : filtre Sources restant actif,
actions sur une source, création liée, citations invalides, classification et
approbation, conservation des unités non analysées, changement de contrat,
reprise sans inférence, protection des fiches humaines, archivage explicite des
propositions et noms courts des artefacts natifs. Voir les XML et journaux de
recette dans le dossier de preuves ; le résultat final est consigné dans progress.md.

Les tests d'approbation utilisent des **fixtures identifiées comme artificielles**.
Aucune véritable information municipale ni document municipal n'a été approuvé
automatiquement. Aucun nouveau bundle ou installateur n'a été compilé dans cette
intervention ; recette sur Windows vierge déconnecté toujours à faire.

Résultat final : **330 tests réussis en 11,35 s**. Conservation vérifiée sur 1 746
fichiers suivis par empreinte : six fichiers du cœur modifiés dans le périmètre
registre/UI, aucun changement inattendu, moteurs audio et rédacteurs partagés
inchangés. Les trois révisions initiales du registre et les 36 interventions de
la base d'origine sont identiques à celles conservées dans la copie ; original
MP3 municipal intact. Preuve : `preservation.json`.

Pour ouvrir directement la copie municipale de recette :
`output/registry-workflow-20261021/4c9f7125b1934a5ab4c3939945cd8bfc/Ouvrir-la-recette.cmd`.
Cette copie contient les propositions à examiner ; l'original reste conservé.
