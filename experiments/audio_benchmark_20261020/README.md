# Laboratoire ASR et diarisation — 20 octobre 2026

## Périmètre fixé avant les essais

Ce laboratoire n’écrit ni séance, ni attribution, ni base de données NoteTaker.
Il conserve l’application, ses moteurs, ses modèles et les corrections humaines.
Les anciens essais Qwen restent distincts ; aucun moteur de synthèse n’est évalué ici.

- **A** : faster-whisper 1.2.1 / CTranslate2 4.6.0 Small, sherpa-onnx 1.13.8,
  mêmes fichiers et paramètres de la référence actuelle, y compris son raffinement
  WeSpeaker et son indicateur de chevauchement. Aucun nombre de voix imposé.
- **B** : faster-whisper Large-v3, Community-1 standard ET sa diarisation exclusive
  conservées séparément. Une variante d’alignement WhisperX réemploie exactement le
  même texte reconnu : l’alignement ne constitue pas une deuxième reconnaissance.
  Acquisition Community-1 conditionnée à l’accès officiel accordé à l’utilisateur.
- **C** : MOSS-Transcribe-Diarize 0.9B officiel OpenMOSS, code et poids épinglés.
  Route Python/Transformers locale sous Windows ; pas de serveur cloud, SGLang ou
  vLLM. Revue du code distant avant exécution. SDPA ; pas de repli eager implicite.

## Données et progression

Source : le WAV normalisé historique des vingt premières minutes BFMTV, durée réelle
**20 min 40,017 s** ; SHA-256 figé. Le MP3 original n’est pas réencodé/écrasé.
60 s : 18:00–19:00. Trois minutes : 17:31.960–20:31.960. Puis le WAV complet.
Les clips sont des copies PCM exactes, communes aux moteurs, sans nettoyage sélectif.

Chaque chaîne doit réussir réellement 60 s, puis 180 s avant son essai long. Un
chargement seul ou un résultat tronqué n’ouvre pas le palier suivant. Les erreurs,
sorties partielles et raisons d’arrêt sont conservées. Les autres chaînes peuvent
progresser quand une candidate est indisponible ou échoue.

La référence narrative et la copie humaine Parcoursup sont conservées. Le formulaire
local des douze extraits indique pour l’instant zéro annotation terminée. Ces textes
ne sont pas assimilés à des RTTM/STM exhaustifs ni à des frontières de parole revues.
Les douze vues comparatives serviront à l’écoute humaine, avec changements de voix,
interruptions et chevauchements à contrôler. L’agent n’a pas d’entrée audio et ne
revendique pas cette écoute. Aucune réunion française supplémentaire n’est disponible
dans les fichiers déjà désignés par l’utilisateur.

## Mesures prévues

Environnements de dépendances séparés, processus séparés, exécution séquentielle visée,
quota mémoire et annulation ; aucune installation dans `.venv` ou `.venv-diar`.
CPU contrôlé (quatre threads). GPU RTX 5070 12 Go réellement présent, pas supposé
compatible par la seule présence du pilote : contrôle d’inférence requis.
CPU mural, CPU Windows cumulé, RSS maximale, mémoire engagée, VRAM lorsque mesurable,
durées de calcul CUDA par événements si le moteur le permet, tailles logiques des
environnements et modèles. Le partage physique éventuel du cache uv est indiqué.
Une durée murale GPU n’est pas étiquetée « temps GPU ».

Écart réel au protocole : A complet a tourné pendant certains pilotes GPU courts.
Les étapes GPU du fichier complet et les essais CPU B/C ultérieurs sont séquentiels.
Les durées sont des observations sur le PC de développement ; pas des rapports de
vitesse à matériel/charge identiques ni des mesures avec caches système purgés.

Conserver séparément segments ASR, tours diarisation, mots alignés et interventions
rapprochées, sans fusion destinée à embellir les statistiques. Compter les durées
négatives/nulles, les segments <0,5 / <1 / <2 secondes, le texte vide, les groupes
et l’incertitude. Les seuils sont descriptifs, pas des scores de précision.

WER : uniquement verbatim humain complet pour une portée audio identifiée.
DER : uniquement plages de parole/locuteurs et chevauchements annotés humainement,
avec UEM et convention de collerette explicités. cpWER/cpCER : transcription
exhaustive par locuteur et portée identique ; permutation optimale, pas nommage
automatique depuis les identités du débat. Références insuffisantes => **non mesuré**.
Aucun moteur, notamment MOSS, n’est employé comme vérité terrain des autres.

## Licences

Sources primaires à archiver : modèle OpenMOSS et code Apache-2.0 ; Whisper et
conversion Systran MIT ; Community-1 CC BY 4.0 et conditions distinctes d’acquisition ;
WhisperX BSD-2-Clause ; aligneur français et dépendances à vérifier individuellement.
Les restrictions déjà documentées des DLL NVIDIA/CTranslate2 et de FFmpeg restent
ouvertes pour le produit. Une réussite du benchmark n’approuve pas leur redistribution.

## Résultats et reproduction

Rapport principal : `output/audio-benchmark/2026-10-20-01/rapport-comparatif.md`.
Mesures JSON/CSV, sorties brutes, portes de progression et traces sont conservées.
Les douze vues dans `review` sont préparées pour écoute humaine ; elles ne certifient
pas une écoute faite par l’agent. WER/DER/cpWER/cpCER restent non mesurés.

Les commandes suivantes traitent uniquement le laboratoire. Les acquisitions
explicites sont distinctes des workers offline ; les dossiers déjà exécutés ne sont
jamais écrasés par les lanceurs. Pour une nouvelle répétition, choisir une autre
série et respecter à nouveau 60 s puis 180 s avant `full`.

```powershell
# Exemple d'une série neuve pour MOSS, après acquisition officielle.
.venv\Scripts\python.exe -m experiments.audio_benchmark_20261020.run_candidate moss 60s --device cuda --series repetition2
.venv\Scripts\python.exe -m experiments.audio_benchmark_20261020.run_candidate moss 180s --device cuda --series repetition2
.venv\Scripts\python.exe -m experiments.audio_benchmark_20261020.run_candidate moss full --device cuda --series repetition2
# Les rapports dérivés peuvent être régénérés ; les résultats bruts restent identiques.
.venv\Scripts\python.exe -m experiments.audio_benchmark_20261020.report
```

Pour annuler, créer `output/audio-benchmark/2026-10-20-01/CANCEL` ; tous les
lanceurs de ce laboratoire le vérifient. Le fermer/retirer avant un autre essai
doit être une décision explicite de l'opérateur. Le Job arrête uniquement ses
propres processus et conserve les fichiers de sortie déjà écrits.
