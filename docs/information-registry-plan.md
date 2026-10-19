# Registre intermédiaire — plan et contrat

## Diagnostic de 0.2.3

`topic_summary.extract` sélectionne six notes par fenêtre avant de vérifier
leur sens. Le catalogue thématique ne voit ensuite que les notes acceptées.
Les notes refusées et les omissions détaillées restent dans le dossier du job ;
l'interface expose surtout une liste de passages, sans information éditable.
Une référence exacte ne prouve ni le sens ni le lien entre deux opinions.

## Modifications prévues

1. Migration additive SQLite v4 → v5 : table de révisions immuables du registre,
   avec identifiant, séance, version, instantané JSON, empreinte des sources,
   auteur de la modification et motif. Sauvegarde cohérente avant migration.
   Aucun ancien brouillon ni aucune relecture ne sont réécrits par la migration.
2. Domaine : inventaire intégral des segments, informations à IDs déterministes,
   sujet/type/auteur et état de vérification, contenu, citations exactes et
   coordonnées, vérification machine distincte de l'approbation humaine,
   relations sourcées. Toute information non admissible reste « À vérifier ».
   Les blancs et résidus non analysés restent visibles ; une couverture de
   citations n'est jamais appelée couverture sémantique.
3. Service transactionnel avec contrôle de concurrence : initialiser,
   préparer, approuver/corriger/déplacer/exclure, consulter l'historique.
   Une correction ne change pas l'instantané source. Une source modifiée,
   fusionnée ou scindée rend le registre obsolète sans supprimer son historique.
   Une nouvelle révision invalide le contexte du document déjà rédigé.
4. Worker local Qwen CPU : préparation séparée de la rédaction, examen de
   toutes les unités sources par petits lots sans sélection globale de six
   notes ; limites explicites et résidus conservés. Extraction, contrôle du
   sens, regroupement et relations sont des tâches distinctes. Les relations
   machine restent provisoires et sont vérifiées sur les deux extraits.
5. Rédaction depuis le registre courant uniquement, avec provenance de révision,
   refus et omissions persistants. Aucun changement des moteurs audio/ASR/voix,
   des votes manuels ou de la relecture humaine obligatoire du document final.
6. Onglet PySide6 : liste recherchable, filtres Tout/À vérifier/Admissibles/
   Exclus/Sources, détail avec contexte et lecture audio, correction de contenu,
   sujet/type/citations, approbation explicite, exclusion motivée et historique.
   La préparation du registre ne lance pas automatiquement la rédaction.
7. Tests : migration et retour arrière en échec, conservation des anciens
   documents, stabilité des IDs, rejets visibles, sources et relations invalides,
   concurrence, correction sans perte, obsolescence, interface, chaîne rédaction/
   relecture/export. Rejeu réel des 670 passages sur copie isolée ; comparer
   séparément les comptes techniques et les dimensions non annotées.

## Limites de qualification

Un verdict Qwen reste une opinion machine. Une intervention peut contenir
plusieurs informations non extraites ; le registre conserve donc aussi les
sources et les résidus. La référence humaine du débat manque : thèmes réels,
informations sémantiquement perdues, attributions, inversions et qualité
rédactionnelle ne peuvent pas recevoir de score de précision. Les mesures
automatiques ne seront pas annoncées comme un gain de fiabilité.

## Ajustement après essais CPU réels

Les premières reprises partielles (720,085 s, 744,666 s, puis 1 886,454 s)
ont révélé un coût excessif lorsque classement, reformulation et vérification
sont exécutés sur chaque candidat avant de rendre le registre disponible.
Ce sont des essais interrompus volontairement, avec caches partiels et code
en évolution, pas des benchmarks complets comparables.

Le contrat évolue : initialisation immédiate sans IA ; extraction conservée
comme propositions provisoires ; contrôle approfondi explicite fiche par
fiche. Les sujets sont proposés depuis toutes les sources, puis les intitulés
provisoires sont rattachés au plan avec un extrait uniquement destiné au
classement. L'opérateur peut ensuite déplacer individuellement les fiches.
Le contrôle sur demande conserve proposition, variante et verdicts. Sur une
fiche verrouillée par l'opérateur, il donne seulement un avis consultatif.
Une proposition en attente n'est jamais rendue admissible par sa seule citation.
Les contrôles nécessaires à la rédaction et à l'export restent obligatoires.
