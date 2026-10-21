# Qualification municipale locale — protocole du 21 octobre 2026

## But et séparation des données

Préparer le choix d'une route CPU et d'une route GPU sans remplacer les moteurs
de NoteTaker. BFMTV E11/E12 reste un **stress test** distinct, avec toutes ses
annotations, révisions, sorties et comparaisons. Les taux ne sont pas mélangés
avec ceux d'un conseil municipal ni d'une simulation.

Le comparateur propose « Corrections ciblées… », « Nouveau test municipal /
ouvrir un test… » et, dans un projet municipal, « Choisir quelques extraits… ».
Les nouveaux fichiers sont dans `output/audio-qualification/municipal/<id>/`.
WAV, MP3 et M4A sont décodés localement, sans téléchargement, en PCM16 mono
16 kHz ; l'original est copié et son empreinte est conservée. L'horloge commune
des trois chaînes commence à zéro dans ce WAV. Chaque essai conserve ses paliers,
requêtes, sorties brutes, limites de ressources et erreurs.

## A. Terminer BFMTV sans réécrire les textes

La file de corrections prépare six vérifications prioritaires :

1. E11-P01 : les 39 mots [60,99) hors sélection. Ouvrir l'assistant directement
   sur P01, écouter, éventuellement préparer la sélection élargie, puis valider.
   Le bouton ne valide rien lui-même et ne change aucun mot du verbatim.
2. E12-P01/P03 : fin de question, début de réponse, répétitions et petite pause.
3. E12-P04/P05/P06 : frontières de la question, de l'exemple et de la réponse.
4. E11 18:33.697–18:34.839 : tours de voix manquants.
5. E11 18:45.791–18:48.709 : tours de voix manquants.
6. E12 20:25.251–20:37.580 : 12,329 secondes de voix non attribuées.

Pour les voix, ajouter seulement les tours manquants et choisir les personnes
humainement identifiées. Plusieurs lignes sont possibles si plusieurs voix
parlent simultanément. Nom et confirmation d'écoute sont obligatoires. Les
tours existants et le texte sont conservés ; la correction crée une nouvelle
révision avec la provenance de la relecture antérieure et du complément local.
Elle ne prétend pas qu'une nouvelle écoute intégrale a été effectuée.

Une case **désactivée au départ** permet de confirmer explicitement le maintien
des validations WER dont les mots et bornes sont inchangés. Le système vérifie
l'audio, le texte et les chevauchements ; une portion devenue incompatible
reste à revoir avec la raison. L'ancien plan et les approbations originales
restent dans l'historique. Aucun transfert n'a lieu sans cette action humaine.

Consigner « corrigé », « vérifié sans changement » ou « à revoir ». Les indices
textuels de l'audit ne constituent pas tous une correction obligatoire : conserver
la sélection si l'écoute la confirme. Le journal distingue les corrections du
protocole des erreurs d'attribution importantes signalées pour chaque chaîne.

## B. Conseil réel ou simulation jouée de 10–15 minutes

Préférer un conseil réel autorisé pour le traitement local. Une simulation
jouée par au moins trois francophones est utilisable pour explorer les cas
d'usage ; elle doit rester étiquetée **simulation**, sans prétendre valider la
qualité sur une réunion naturelle. Ne pas utiliser une voix synthétique comme
preuve de précision en situation réelle.

### Scénario proposé si une simulation est nécessaire

| Temps indicatif | Situation à jouer naturellement |
|---|---|
| 0–1 min | Ouverture et annonce du sujet par la présidence |
| 1–3 min | Présentation simple : objet, contexte, noms propres et nombres |
| 3–5 min | Questions et changements d'intervenant, réponse à une question |
| 5–7 min | Proposition concrète, objection et alternative ; une courte interruption si elle survient naturellement |
| 7–9 min | Délibération : préciser ce qui est proposé au vote, ce qui reste une opinion |
| 9–11 min | Vote joué : demander pour/contre/abstentions, compter réellement et annoncer explicitement le résultat obtenu |
| 11–15 min | Deuxième point bref ou questions, puis clôture |

Ne pas fixer à l'avance un résultat à faire retrouver au logiciel. Les personnes
choisissent leurs réponses ; seules les paroles effectivement prononcées servent
de référence. Si un résultat n'est pas annoncé, s'il manque le vote dans le
fichier ou si le comptage est ambigu, marquer **absent/non couvert/à vérifier**.
La transcription et la comparaison ne décident pas du résultat.

Conserver le même microphone, la même distance et les conditions normales
d'enregistrement. Noter les bruits, coupures et chevauchements réellement
survenus ; ne pas nettoyer un seul moteur au profit d'un autre. Garder l'audio
original et documenter toute conversion commune aux trois chaînes.

### Exécution

1. Importer le fichier ; choisir « réel », « simulation jouée » ou « test technique ».
   Une durée hors 10–15 min est signalée, sans étirer ni inventer de contenu.
2. Choisir la route : A reste CPU ; B et WhisperX utilisent CUDA ou CPU selon le
   choix explicite. Une erreur CUDA n'est pas présentée comme un succès GPU.
3. Lancer 60 s → 180 s → fichier complet. Chaque palier doit produire des sorties
   non vides avec des horaires valides. Une panne bloque le palier suivant et
   conserve les sorties déjà calculées. L'annulation ferme le Job du moteur.
4. Cinq composants sont calculés par palier : Small, sherpa, Large-v3, Community-1,
   alignement WhisperX. Les deux dernières chaînes partagent Large et Community ;
   la reconnaissance n'est pas répétée pour WhisperX. Aucun nombre de voix n'est imposé.
5. Ouvrir la référence propre à cet essai. Les noms humains, mots et tours sont
   **vides**, aucune validation n'est préremplie depuis les hypothèses.

Les modèles et environnements existants sont utilisés localement. Les mesures
ne purgent pas les caches du système et ne sont pas des essais « à froid ».
La VRAM maximale n'est pas déduite du pic de mémoire engagée hôte.

## C. Peu d'extraits, mais une couverture utile

Commencer avec **quatre à six extraits de 20–30 s**, soit environ deux minutes
à trois minutes d'audio annoté, sans horodater individuellement les mots.

- Garder deux extraits de contrôle répartis dans le temps, choisis avant
  l'affichage des hypothèses.
- Ajouter quelques situations réellement présentes : parole simple, transition,
  proposition, délibération et vote effectif. Plusieurs situations peuvent se
  trouver dans le même extrait.
- Les mots clés ASR et changements de groupes proposent des repères, pas des
  événements certifiés. L'interface les indique comme assistés par un moteur.
  Un extrait choisi ainsi n'est pas présenté comme une sélection aveugle.
- Écouter les propositions avant de les retenir. Décocher les plages temporelles
  remplacées si elles se recouvrent avec un événement. Le système refuse le
  double comptage et limite cette sélection initiale à six extraits.
- Une référence déjà annotée n'est jamais remplacée par ce sélecteur. Utiliser
  « Ajouter une zone » si une vérification complémentaire est réellement nécessaire.

Saisir le verbatim exact, des noms confirmés ou des pseudonymes stables, puis
les tours de voix. Les deux validations texte/voix suffisent au WER séquentiel.
Seuls les vrais chevauchements sont isolés ; un découpage lexical supplémentaire
demande une confirmation humaine. Le DER qualifié exclut l'activité inconnue
et compte les silences uniquement lorsqu'ils sont explicitement confirmés.

## D. Comparaison et travail humain

Le rapport conserve séparément :

- WER strict et français normalisé, N et erreurs S/D/I, par zone et portion ;
- DER qualifié, confusion/omission/fausse alarme en secondes de voix, couverture
  et plages exclues ; DER historique conservé pour comparaison du protocole ;
- signalements humains d'attributions importantes, surtout proposition, opposition,
  délibération ou vote attribués à la mauvaise personne ;
- temps écoulé et CPU, pic de mémoire engagée hôte, route et composants partagés ;
- corrections du protocole effectuées, contrôles sans changement, différés,
  temps opérateur consigné et vérifications encore proposées.

Un signalement est une observation liée à un passage et une révision ; ce n'est
pas un taux exhaustif. Zéro signalement ne prouve pas zéro erreur. Les corrections
communes de la référence ou du découpage ne sont pas attribuées à un moteur.
Les opinions citées, les négations et les résultats de vote doivent être vérifiés
sur l'audio ; l'accord de deux moteurs ne remplace pas cette référence.

### Critère de décision

Présenter les résultats municipaux et BFMTV dans deux tableaux distincts.
Comparer les erreurs qui changent le sens, l'effort humain, les ressources et la
couverture avant de recommander une route CPU ou GPU. Les mêmes textes/tours
Large avec/sans WhisperX produisent les mêmes WER/DER bruts ; l'alignement se
juge séparément. Les horaires humains des mots ne sont nécessaires que si ce
gain temporel mérite une mesure dédiée sur quelques frontières litigieuses.

Aucun moteur n'est sélectionné automatiquement. Les réserves de redistribution
et la recette Windows vierge hors ligne du dossier de licences du benchmark
restent applicables ; cette qualification ne constitue pas une intégration produit.
