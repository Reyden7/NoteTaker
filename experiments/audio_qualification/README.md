# Qualification humaine de la transcription et des voix

Outil **séparé** de NoteTaker, conservant les résultats figés BFMTV et permettant
des essais municipaux distincts. Aucun modèle n'est chargé par l'interface ou le calcul des
scores, aucun fichier de séance n'est modifié, aucun téléchargement n'est prévu.
Les dépendances PySide6 de `.venv` et pyannote.metrics de `.venv-lab-b` sont
réutilisées sans nouvelle installation. Les modèles acquis restent en place.

## Reprise BFMTV et nouveau conseil municipal

Voir le protocole complet `docs/protocole-qualification-municipale.md`.

- **Corrections ciblées…** prépare les six contrôles BFMTV prioritaires :
  E11-P01, deux ensembles de frontières E12 et trois plages sans voix attribuée.
  La sélection élargie des 39 mots est une proposition explicitement déclenchée,
  jamais une modification ou approbation au simple affichage. Les mots restent
  ceux du verbatim en lecture seule.
- Les tours manquants peuvent être ajoutés sans retaper le texte. La validation
  locale conserve la provenance de la relecture antérieure et crée une nouvelle
  révision. La case permettant de conserver les accords WER inchangés est
  décochée par défaut ; les accords devenus incompatibles restent à revoir.
- **Nouveau test municipal / ouvrir un test…** copie un WAV/MP3/M4A dans un
  projet neuf, puis exécute les trois chaînes avec les modèles existants.
  Source, WAV commun, paliers, essais, référence, plans et journal sont séparés
  de BFMTV dans `output/audio-qualification/municipal/<id>/`.
- Le parcours teste 60 s, 180 s puis le fichier complet. Chaque composant tourne
  dans un processus isolé annulable : 4 GiB pour Small/sherpa, 12 GiB pour les
  candidats, 900 s par pilote et 3600 s par composant complet. Les échecs ne
  deviennent pas des résultats simulés. A reste CPU ; la route B CPU/CUDA est
  choisie explicitement, sans prétendre qu'un repli CPU est une mesure GPU.
- **Choisir quelques extraits…** propose six plages temporelles de 25 s et
  quelques repères ASR/voix, non validés. Choisir au plus six plages non
  recouvrantes, par exemple deux contrôles temporels et des événements réellement
  présents. Une référence déjà annotée ne peut pas être remplacée par ce sélecteur.
- Le journal distingue les corrections de protocole, les annotations initiales
  et les attributions importantes signalées par chaîne. Ces comptes ne sont pas
  des taux exhaustifs. Les rapports changés par le seul journal sont marqués périmés.

Chaque essai complet possède `full/Ouvrir-ce-test.cmd`, ou :

```powershell
.venv\Scripts\python.exe -m experiments.audio_qualification.app --project chemin/essai/full/project.json
```

Le fichier municipal fourni le 21 octobre dure **336,039 s (5 min 36 s)**,
donc ne couvre pas encore la cible 10–15 min. Les trois chaînes ont réellement
réussi les trois paliers ; aucune référence humaine municipale n'a été approuvée.
Les WER/DER municipaux restent non mesurés. Les mots « voter » dans une hypothèse
ne prouvent ni un vote effectif ni un résultat ; confirmer ou déclarer absent.

Tests complémentaires : `test_workflow.py` (services) et `test_workflow_ui.py`
(PySide6). Placer les dossiers temporaires numériques dans le workspace Windows
pour éviter les restrictions du répertoire temporaire du bac à sable.

## Ouvrir

Double-cliquer `Ouvrir-le-comparateur.cmd` dans ce dossier, ou depuis la racine :

```powershell
.venv\Scripts\python.exe -m experiments.audio_qualification.app
```

La référence se sauvegarde dans
`output/audio-qualification/2026-10-20-01/reference-humaine.sqlite`, jamais dans
la base NoteTaker. Le programme refuse de réutiliser une base d'une autre
application. Les copies de recette sous `qa` et les cas unitaires sont distincts
de cette référence utilisateur.

## Annoter un extrait

1. Choisir une des douze zones. Le lecteur utilise **toujours le même WAV complet**,
   SHA `95da1f0787fd22ad313acfd367fda3012b47587660cb9b1a2d6e6001bf0e708a`.
   Tous les horaires sont absolus dans le débat. Ajuster les limites si seule
   une portion est réellement annotée ; placer les limites WER sur des pauses.
   Les zones ne peuvent pas se recouvrir, afin de ne pas compter deux fois l'audio.
2. Choisir la sortie audio du casque et le volume. F5 : lecture/pause ; boutons
   ±2 s ; vitesse 0,65× à 1,25× ; boucle au besoin. Cliquer/déplacer le curseur
   permet la recherche temporelle dans la zone. Un double-clic sur une intervention
   affichée la relit dans le même fichier, sans remettre son origine à zéro.
3. **Hypothèses masquées par défaut** : saisir le verbatim humain exhaustif, sans
   résumer. Ajouter les voix humaines avec un nom réellement identifié ou un
   pseudonyme stable. Aucune identité n'est déduite d'un groupe du moteur.
   Aucun texte, nom ou horaire d'un modèle ne préremplit la référence.
4. Onglet « Voix et chevauchements » : ajouter les tours de chaque voix, début
   et fin en secondes absolues. Les trous entre ces tours doivent être vérifiés :
   ils peuvent contenir une parole non annotée, pas seulement un silence.
   Les voix simultanées doivent avoir des plages simultanées, **deux lignes**.
   Les boutons début/fin au curseur (F6/F7 sur la ligne sélectionnée) aident à
   ajuster les frontières. Écouter avant de marquer les limites : l'action
   seule ne prouve pas leur précision.
5. Indiquer les cas difficiles dans « Écarts » : interruption, chevauchement,
   passage court, nom propre. Ajouter des observations séparées par chaîne et
   type d'erreur. Marquer l'inaudible : il est exclu des scores, jamais deviné.
   Une zone entièrement silencieuse peut être validée explicitement sans texte.
6. Renseigner son nom et confirmer séparément l'écoute exhaustive du texte et
   des tours de parole. Les validations sont des actes humains explicites ; le
   logiciel ne peut pas certifier qu'une personne a réellement écouté.
7. Afficher les trois hypothèses pour comparer. La lecture surligne simultanément
   les interventions des trois colonnes. L'affichage standard conserve les
   chevauchements ; l'exclusif facilite la lecture sans devenir la référence.
   Les hypothèses restent en lecture seule : **corriger dans les onglets humains**.
8. L'onglet des mots horodatés est facultatif pour WER/DER, nécessaire pour
   mesurer l'alignement et l'attribution des mots. « Recréer depuis le verbatim »
   crée la liste lexicale humaine, **sans horaires inventés** ; les anciennes
   listes restent dans l'historique. Compléter chaque début/fin et chaque voix,
   puis valider seulement après écoute. Chaque mot doit appartenir à un tour de
   sa voix ; pour le mot coupant deux tours artificiels, réunir ces tours humains.

L'exposition aux hypothèses est enregistrée. Une validation faite avant leur
affichage est distincte d'une annotation corrigée après comparaison. Masquer
ensuite ou restaurer une ancienne révision ne supprime pas l'exposition passée :
un registre SQLite distinct des instantanés la conserve. L'indépendance signifie que la
référence est créée et vérifiée humainement sur l'audio, sans choisir un moteur
comme vérité. Le mode masqué réduit le biais, sans garantir qu'un annotateur n'a
jamais vu auparavant des sorties sur le débat. Le récit et les corrections
existants restent conservés ; ils ne sont pas convertis automatiquement en vérité
horodatée exhaustive.

## Sauvegarde et conservation

- Sauvegarde progressive après 650 ms de saisie ; Ctrl+S pour enregistrer
  immédiatement. Un brouillon brut est conservé avant interprétation des
  horaires : une cellule numérique incomplète reste récupérable à la réouverture.
- Révisions SQLite transactionnelles, horodatées, avec auteur/événement, empreinte
  du contenu et parent. Les corrections ne réécrivent jamais les anciennes
  révisions. L'historique permet de restaurer une version sous une nouvelle révision.
- Modifier texte, horaires, auteurs ou portée retire les validations concernées.
  Les notes/catégories seules ne changent pas le verbatim. Un renommage conserve
  l'identifiant humain. Aucune empreinte vocale, aucun apprentissage.
- Éviter plusieurs fenêtres d'édition simultanées : un contrôle de concurrence
  refuse d'écraser une référence plus récente. Les brouillons restent dans la base.
- « Exporter la référence » crée un nouveau dossier : JSON intégral avec provenance,
  UEM/RTTM uniquement pour les zones diarisation revues, verbatim revu et mots TSV.
  L'export de référence d'étude ne constitue pas un procès-verbal validé.
- Les permissions locales Windows protègent ce dossier comme les autres fichiers
  du compte ; ce laboratoire n'ajoute pas un coffre chiffré ni des habilitations.

## Scores et comparaison

« Calculer la comparaison » fige une nouvelle copie de la référence et vérifie
les empreintes de l'audio et de toutes les hypothèses utilisées. Le calcul local
est isolé, limité à 2 GiB engagés et 120 s, annulable. Il n'importe aucun moteur
de reconnaissance ni modèle et interdit les connexions Python réseau.

### WER : seulement le verbatim revu

Normalisation documentée : Unicode NFC, casse et ponctuation ignorées,
apostrophes conservées, accents et chiffres conservés. Les nombres ne sont pas
magiquement réécrits : « 12 » et « douze » restent distincts. Afficher les
substitutions, omissions et ajouts, ainsi que leurs mots dans le JSON du rapport.
Les tokens coupant une frontière sont sélectionnés par leur milieu temporel.
Une frontière sans horaires de mots **moteur** exploitables bloque cette portion
pour **toutes** les chaînes ; ajuster la borne sur une pause puis la valider.
Aucun horaire humain de mot n'est requis pour le WER. Un texte sans référence ne reçoit
pas un zéro. En silence intégral, les insertions sont comptées, mais sans mots
humains le taux WER reste indéfini/non mesuré.

Seuls les intervalles réellement simultanés, d'après les tours humains de voix
distinctes, sont exclus du WER séquentiel. Une étiquette « chevauchement » ne
supprime plus tout un extrait dont les tours sont revus. La validation du texte
et des voix (2/3) suffit pour une zone séquentielle ; les mots horodatés restent
facultatifs. Pour séparer une zone contenant des chevauchements, l'opérateur
doit confirmer les bornes et les mots de chaque portion conservée.
Une future étude cpWER/cpCER pourra exploiter un verbatim exhaustif par voix ;
ces scores ne sont pas annoncés ici.

### Valider un découpage sans horodater chaque mot

Enregistrer puis fermer et relancer le comparateur si une ancienne version est
déjà ouverte. Cliquer **« WER sans horaires de mots… »** :

1. Sélectionner une portion, l'écouter dans le WAV commun et vérifier ses bornes.
2. Vérifier les mots surlignés dans le verbatim humain original en lecture seule.
   Si nécessaire, sélectionner les mots exacts puis « Utiliser les mots sélectionnés ».
   La présélection assistée par le moteur est une proposition, jamais une validation.
3. Ajuster les bornes sur des pauses ou scinder au curseur audio au besoin.
   Une plage non couverte doit être écoutée : parole séquentielle ou silence
   explicite, jamais silence supposé. Les vrais chevauchements restent exclus.
4. Renseigner son nom, confirmer l'écoute et cliquer **« Valider cette portion
   pour le WER »**. Toute modification de cette portion retire son approbation.
5. Cliquer **« Calculer les portions validées »**. Il est possible de mesurer
   un sous-ensemble ; les autres portions et les chevauchements restent visibles
   dans le rapport avec leur statut. Sans approbation, aucun WER n'est inventé.

Les bornes et sélections de texte sont enregistrées dans une base distincte
`decoupages-wer.sqlite`, avec historique, auteur et empreinte de la référence.
La référence humaine et ses révisions ne sont pas réécrites. Aucun mot n'est
corrigé automatiquement. Chaque rapport fige son propre découpage ; les rapports
précédents restent conservés. Le module `experiments.audio_qualification.wer_review`
permet aussi d'ouvrir uniquement cet assistant ; le calcul se lance depuis le
comparateur principal.

Sur la référence E11/E12 reçue le 20 octobre : sept portions séquentielles et
quatre trous de couverture sont proposés, sans approbation automatique. Le dernier
trou E12 est **20:25.251–20:37.580 (12,329 s)** : le verbatim continue, mais aucun
tour humain n'y est renseigné. Les détections des moteurs sont affichées comme
alertes et ne prouvent pas à elles seules la présence ou l'absence de parole.

### DER : seulement l'activité et les identités revues

`pyannote.metrics.DiarizationErrorRate`, collerette **0 s**, chevauchements inclus,
UEM explicite. Appariement hongrois optimal **global sur les zones revues du même
enregistrement**, jamais une permutation avantageuse distincte par extrait.
Présenter séparément confusion de voix, parole manquée, fausse alarme et total
en secondes de voix humaines. Les doubles voix contribuent deux fois au dénominateur.
Une zone sans voix humaine peut contribuer une fausse alarme sans fabriquer un taux.
Si des trous de couverture contiennent de la parole détectée par les moteurs,
le rapport signale **« DER indicatif, couverture incomplète »**. Le calcul DER
existant est conservé pour la comparaison historique ; il ne qualifie pas la
précision tant que ces trous ne sont pas vérifiés humainement.

La diarisation brute Community-1 est identique pour Large-v3 avec/sans WhisperX :
son DER doit être identique. Les groupes ne sont pas un score d'exactitude.

### Gains et surcoût de WhisperX

La reconnaissance Large-v3 est la même dans les deux variantes : même WER
brut, avec la même horloge lexicale de sélection des zones pour ne pas fabriquer
un « gain WER » par simple déplacement de frontières. Comparer séparément :

- Erreur absolue moyenne début/fin des mots corrects avec horaires disponibles.
- Proportion de **tous** les mots humains dont les deux bornes sont à ±100/250 ms,
  avec couverture et mots sans horaire visibles ; ne pas exclure les cas difficiles
  pour embellir la mesure.
- Mauvaise attribution des mots lexicalement corrects dans la transcription
  finale, après appariement vocal global du DER ; les non attribués comptent
  comme erreurs. Cette mesure conditionnelle ne remplace pas le WER ni le DER.

Ces mesures demandent des horaires de mots et auteurs revus par une personne ;
elles restent non mesurées sinon. Hors chevauchement pour ces diagnostics
lexicaux ; les chevauchements sont évalués au DER et qualitativement à l'écoute.
Les résultats de référence manuelle et la taille des portions évaluées sont exportés.

Le rapport est lisible dans l'onglet « Résultats de comparaison », avec les erreurs
de mots et de voix présentées séparément et les sous-ensembles par catégorie.
Les catégories peuvent se recouper et ne doivent pas être additionnées. Après une
nouvelle correction, un bandeau signale que le rapport provient d'une ancienne
référence ; l'ancien fichier reste conservé et un nouveau calcul crée un autre dossier.

Surcoût GPU déjà observé : **33,96 s**, soit environ **21,96 %** des étapes B sans
alignement sur le fichier complet, une seule exécution, caches non purgés. Les
durées des moteurs CPU/GPU sur matériels/routes différents ne prouvent pas un
rapport de vitesse à configuration égale. La décision dépendra du gain humain mesuré.

Sources méthodologiques : [pyannote.metrics, UEM et DER](https://pyannote.github.io/pyannote-metrics/reference.html),
[définition et opérations WER](https://jitsi.github.io/jiwer/usage/),
[backends Qt 6.8](https://doc.qt.io/qt-6.8/qtmultimedia-index.html).
Le WER est calculé par Levenshtein local, testé sur cas connus ; jiwer n'est
pas installé pour cet outil. Le DER utilise la bibliothèque pyannote déjà installée.

## Décision produit

### Audit du 21 octobre : strict, normalisé et DER qualifié

Les nouveaux rapports conservent le WER strict précédent et ajoutent un
**WER normalisé français** distinct. Les règles versionnées sont dans
`normalization.py` et intégralement reprises dans les rapports ; chaque
transformation conserve les indices de ses mots stricts dans `scores.json`.

- NFC et casse/ponctuation : protocole strict conservé.
- Élisions connues séparées sans effacer leurs composants ni les négations.
- Ligatures œ/oe et æ/ae ; accents corrigés seulement selon une liste fermée
  publiée (notamment selection/séléction/sélection). **a/à, ou/où, sur/sûr,
  du/dû et élevé/élève restent distincts.** Aucun correcteur orthographique.
- Alias explicite « parcours sup » / « Parcoursup ». « parcoursuc » n'est pas
  corrigé ; aucune identité ou ressemblance phonétique n'est extrapolée.
- Entiers isolés 0–9999 écrits en lettres, signes plus/moins conservés, notation
  Nh explicitée ; pluriels numériques conventionnels traités. Pas de nombres
  décimaux reconstitués depuis les tokens ; séquences numériques adjacentes
  conservées et signalées. Les fautes « uner », « acceuille », les accords et
  répétitions humaines ne sont pas réparés automatiquement.
- N strict et N normalisé affichés séparément : le changement de tokenisation
  interdit d'interpréter une simple baisse du WER normalisé comme un progrès moteur.

Le **DER historique** reste inchangé. Le **DER qualifié partiel** utilise un
masque commun aux chaînes : union des tours de voix humains revus et des silences
explicitement écoutés/validés. Les trous ne deviennent jamais du silence par
défaut. Une portion WER approuvée comme parole n'ajoute pas d'identité vocale.
Les confusions, omissions et fausses alarmes sont séparées en secondes de voix ;
la permutation optimale est globale sur ce seul masque, chevauchements inclus.
Les erreurs dans les plages inconnues exclues ne sont donc pas mesurées.

Les rapports ajoutent les WER par zone et portion, les couvertures, les mots
humains hors sélection et les frontières traversant un mot moteur. Ces derniers
indices viennent d'alignements textuels avec les sorties existantes : **écouter
avant de corriger**, sans prendre l'accord de Small et Large pour une vérité.
WhisperX n'est pas une troisième confirmation indépendante.

Chaque portion signalée dispose d'un WAV PCM de contrôle, copié sans réencodage
avec 1,5 s de contexte disponible de chaque côté. Le rapport donne son origine
absolue ; le lecteur du comparateur conserve le WAV complet d'origine. Les liens
audio de l'onglet résultats ouvrent uniquement des fichiers locaux du rapport.
Les écoutes et validations humaines restent à faire ; aucune annotation n'est
modifiée par le calcul.

Option CLI de comparaison historique (référence/plan JSON figés et sortie neuve) :

```powershell
.venv\Scripts\python.exe -m experiments.audio_qualification.controller chemin/reference.json chemin/nouveau-calcul --plan chemin/wer-plan.json --baseline-report chemin/ancien/scores.json
```

Une différence de sélection est signalée séparément. L'interface marque aussi
un rapport périmé lorsque le plan WER change sans changer le verbatim humain.
Tests supplémentaires : `.venv-lab-b\Scripts\python.exe -m unittest experiments.audio_qualification.test_audit -v`.

Les rapports de comparaison produisent les mesures disponibles et exposent les
domaines non mesurés. Ils ne sélectionnent aucun moteur. Une recommandation finale
CPU/GPU doit tenir compte de la couverture représentative, de la précision des
voix et des mots, des contraintes CPU longues, des dépendances et des droits de
redistribution (`docs/audio-benchmark-20261020-licenses.md`), puis du test Windows
vierge hors ligne. Tant que l'annotation et sa revue sont incomplètes, conserver
le moteur de production et le statut **qualification en cours**.

## Contrôles techniques

Tests de l'éditeur avec `.venv`, tests numériques avec `.venv-lab-b` :

```powershell
# Choisir à chaque exécution un dossier temporaire neuf pour préserver les preuves.
.venv\Scripts\python.exe -m pytest experiments/audio_qualification/test_editor.py experiments/audio_qualification/test_wer_review_ui.py -q --basetemp=output/audio-qualification/2026-10-20-01/nouveau-dossier-temporaire
.venv-lab-b\Scripts\python.exe -m unittest experiments.audio_qualification.test_scoring experiments.audio_qualification.test_wer_plan -v
```

La recette `qa_desktop.py` rend les vues, ouvre le WAV original, vérifie recherche
et progression sur la sortie Windows réelle, **son coupé**, puis calcule un rapport
avec toutes les zones non annotées (scores non mesurés). Elle ne prétend pas
vérifier la fidélité sonore à l'oreille ni constituer une annotation humaine.
Les fixtures unitaires sont artificielles et ne mesurent pas la qualité des moteurs.

Le lecteur de ce laboratoire utilise Windows Media Foundation dans son processus
pour le WAV PCM : le backend FFmpeg de Qt 6.8 a réellement échoué à configurer
la sortie 7.1 du casque Logitech. Aucune variable système ni lecteur de production
n'est modifié. Le choix du périphérique de sortie reste accessible à l'opérateur.
