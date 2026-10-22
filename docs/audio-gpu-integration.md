# Traitement audio CPU / GPU — intégration du 21 octobre 2026

## Utilisation

L'application principale lancée par `scripts/run.ps1` propose **Paramètres audio
— CPU / GPU**, à gauche. Ce réglage est local à son dossier de données, dans
`audio-settings.json`, écrit atomiquement ; aucune migration des séances.

- **Automatique (recommandé)** : vérifier l'intégrité SHA-256 de tous les modèles
  GPU, les versions du runtime isolé, CUDA dans PyTorch et CTranslate2, le support
  float16, exécuter une multiplication matricielle sur CUDA et vérifier au moins
  **8 Gio libres**. Ce seuil prudent est une admission, pas une garantie pour
  toutes les durées ou toutes les cartes. Small + sherpa si cette admission échoue.
- **CPU** : Whisper Small int8 + sherpa-onnx et affinement actuels, sans importer
  PyTorch dans l'interface ou dans le worker CPU.
- **GPU NVIDIA** : Large-v3 float16 + Community-1 CUDA. Si l'admission échoue,
  diagnostic et proposition explicite de relance CPU.

Après une panne pendant une inférence GPU (y compris mémoire épuisée), la
transcription courante et les corrections humaines restent actives. Le bouton
**Relancer explicitement avec Small + sherpa sur CPU** propose une nouvelle analyse.
Il ne change pas le réglage permanent. Les résultats intermédiaires restent dans
le dossier de travail ; aucune relance CPU n'est automatique après cette panne.

L'import, les microphones, la lecture, l'annuaire, les corrections, le registre,
la rédaction et l'export gardent leur parcours habituel. Les voix automatiques
restent anonymes. **Annuler le traitement** arrête l'arbre de processus Windows.
Les prises originales ne sont jamais effacées ; une annulation avant l'écriture
transactionnelle conserve la transcription active. Une transaction déjà validée
ne peut pas être annulée rétroactivement ; l'historique reste disponible.

## Architecture

`services/audio_engine.py` porte la politique et l'adaptation Community-1.
`workers/gpu_audio.py` s'exécute avec un autre Python, une opération par processus :
admission, transcription puis diarisation. La sortie du processus libère ses
ressources natives, même après annulation. `Pipeline.analyse` partage la préparation
audio, l'alignement, les contrôles de montage, la préservation des corrections,
la sauvegarde transactionnelle et l'historique des deux chaînes.

Le mode CPU existant et les fonctions pures `lexical_words` / `align_transcript`
sont conservés. Les moteurs Qwen, prompts, registre et protections de rédaction /
relecture / export ne sont pas modifiés. Aucun enrôlement vocal nominatif.

Le runtime GPU réutilisé en développement est `.venv-lab-b`. La cible transportable
est `runtimes/audio-gpu/python.exe`, avec les sources minimales du worker dans
`runtimes/audio-gpu/app`. Le processus ne reçoit pas les variables de jeton HF,
ni `PYTHONHOME` ou les paquets de l'utilisateur. Chaque travail GPU utilise son
propre `offline-cache`, initialement vide. Les indicateurs hors ligne et le garde
réseau Python sont appliqués avant les imports des moteurs. Ce garde **n'est pas
un pare-feu natif** : la recette physique déconnectée reste nécessaire.

Modèles épinglés par `gpu_audio_manifest.json` :

- `models/audio-lab/large` : SYSTRAN Large-v3, révision
  `edaa852ec7e145841d8ffdb056a99866b5f0a478`.
- `models/audio-lab/community` : Community-1, révision
  `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee`.

Versions vérifiées : faster-whisper 1.2.1, CTranslate2 4.8.3, PyTorch 2.8.0+cu128,
pyannote.audio 4.0.7, PyAV 18.1.0. Les versions CPU restent distinctes.

Transcription : français, beam 5, VAD, horodatages de mots, un worker, quatre
threads CPU, modèles locaux uniquement. Diarisation : configuration locale du
laboratoire, tenseur PCM16 mono 16 kHz en entrée pour éviter le décodeur TorchCodec
non fonctionnel sur ce poste ; aucun nombre d'intervenants imposé.

## Tours simultanés et limites

Seule la sortie standard `speaker_diarization` est utilisée ; la variante
exclusive et WhisperX ne le sont pas. Les tours exacts sont conservés dans
`community-turns.json` et les sources de chaque intervention (`diarization_turns`,
`simultaneous_turns`). Des intervalles concurrents sont dérivés sans limiter les
voix. Les horodatages restent ceux du même WAV normalisé et de son SHA-256.

Le texte Whisper est un flux unique : il ne sépare pas les deux paroles qui se
chevauchent. Un groupe de mots touchant un chevauchement reste **sans voix primaire,
incertain**, avec toutes les voix candidates consultables. Le texte n'est pas
dupliqué. Cette précaution peut laisser un groupe entier à attribuer, même si une
partie seulement se chevauche. Le panneau explique ce cas et permet l'écoute et
la scission manuelle. Aucun score de confiance de diarisation n'est inventé.
Les probabilités Whisper et log-probabilités restent des informations du moteur,
pas une certification de transcription ni de locuteur.

## Recette reproductible

Depuis la racine du dépôt :

```powershell
.venv\Scripts\python.exe scripts\validate_gpu_audio.py `
  --audio "C:\chemin\conseil.mp3" --output "output\nouvel-essai-gpu" --mode auto
```

Le dossier cible doit être nouveau. La vraie séance municipale reste **non relue**.
Le test prépare une transcription intégrale, vérifie les refus PDF/DOCX sans
relecture, puis utilise une **autre base de fixture** pour tester les exports avec
une confirmation explicitement artificielle. Ce n'est ni une relecture humaine,
ni une validation de la synthèse Qwen ou du PV municipal.

Preuves de cette intervention :
`output/gpu-integration-20261021/e1434b50c08946f78e574f9056b6d11b/`.

| Test municipal, 336,039 s | Chaîne GPU auto | Chaîne CPU explicite |
|---|---:|---:|
| Durée analyse totale, admission / préparation comprises | 99,491 s | 133,217 s |
| Interventions après regroupement prudent | 36 | 68 |
| Groupes anonymes | 2 | 3 |
| Interventions avec tours simultanés Community | 1 | Sans objet |

La RTX 5070 expose 12 792 037 376 octets, dont 11 499 732 992 libres à l'admission.
Pilote observé : **616.92** ; aucune version minimale générale n'est déduite
de cette seule recette. L'inventaire `native-imports.json` recense les imports
de **484 fichiers PE** du runtime transportable ; un inventaire n'est pas une
qualification de toutes les dépendances retardées sur Windows vierge.
Composants GPU, mesures internes hors démarrage de l'interpréteur :

| Étape | Temps écoulé | Temps CPU | Pic privé hôte échantillonné |
|---|---:|---:|---:|
| Admission | 10,637 s | 10,281 s | 1 497 378 816 octets |
| Large-v3 | 53,805 s | 51,953 s | 7 594 459 136 octets |
| Community-1 | 30,108 s | 28,563 s | 5 310 222 336 octets |

Le pic est une mémoire **hôte**, mesurée toutes les 100 ms, pas un pic VRAM.
Une exécution par mode, caches OS non purgés, activité du poste non neutralisée :
aucune garantie de performance générale ni mesure « à froid ». Les nombres de
groupes ne mesurent pas la précision. Aucun nouveau WER/DER ou gain qualitatif
n'est annoncé ; les références et rapports du laboratoire sont préservés.

Le même WAV est retrouvé par SHA-256. Les tours Community-1 sont identiques au
laboratoire. Les 55 segments bruts Large gardent leurs bornes, mais le texte du
segment `s27` et certaines probabilités / bornes de mots diffèrent de l'essai
antérieur (`lab-output-comparison.json`). Les paramètres explicites sont les
mêmes ; une exécution n'établit pas la reproductibilité numérique, et aucune
de ces variantes ne remplace la référence humaine ou les résultats du comparateur.

Les tests de panne/OOM et de politique incluent de l'injection contrôlée,
distincte de ces inférences réelles. Une annulation d'un véritable worker Large
après 12 secondes a également été exécutée et son processus attendu/récolté.
Une panne CUDA physique et un épuisement VRAM réel ne sont pas provoqués.

## Préparation de l'installateur

`packaging/prepare_audio_gpu.py`, exécuté avec le Python GPU qualifié, calcule la
fermeture des dépendances déclarées installées, sans installation réseau. Il
produit un inventaire de versions, licences déclarées, fichiers/hashes/taille et
un verrou des versions. `--stage-development` copie un Python de base complet,
la bibliothèque standard, les dépendances et le worker minimal dans un dossier
neuf. Il ne copie pas un virtualenv Windows non transportable. Les modèles
restent copiés séparément à partir du manifeste épinglé.

```powershell
.venv-lab-b\Scripts\python.exe packaging\prepare_audio_gpu.py `
  --output "output\nouveau-runtime-gpu" --stage-development
```

La disposition finale à inclure dans le lot PyInstaller/Inno Setup est :

```text
NoteTaker.exe / NoteTaker-worker.exe / _internal/   (socle CPU)
gpu_audio_manifest.json
models/audio-lab/large/ et community/              (modèles complets)
runtimes/audio-gpu/python.exe, DLLs/, Lib/, app/   (runtime GPU isolé)
third_party/audio-gpu/                             (licences et notices)
```

Le staging effectué ici contient 95 distributions, 27 055 fichiers et
8 000 543 762 octets (modèles exclus), inventoriés par SHA-256. Son Python copié,
hors virtualenv, a passé l'admission CUDA puis ASR et Community sur 60 secondes
municipales, avec son propre `app` et un cache HF neuf, zéro tentative réseau
Python. C'est une recette sur ce poste de développement, pas un Windows vierge.
La commande préparée pour assembler ultérieurement un nouveau lot est :

```powershell
powershell -NoProfile -File packaging\build.ps1 -Development -IncludeGpu `
  -DistributionDirectory "dist\nouveau-lot-gpu"
```

Cette commande complète PyInstaller n'a pas été exécutée durant l'intervention ;
le staging GPU et ses inférences ont été réellement testés séparément. Les
anciens bundles sont conservés et ne reçoivent pas ce code automatiquement.

Le socle PyInstaller continue d'exclure torch/pyannote : les DLL GPU ne doivent
pas être chargées dans le processus CPU. Le runtime externe reçoit son `app`
en `PYTHONPATH`, y compris depuis un exécutable gelé. L'installateur unique
embarque les deux lots, sans appel à pip/HF ni téléchargement ; le pilote NVIDIA
compatible doit déjà être présent pour le mode GPU, sinon CPU. Ne pas installer
un pilote ni un Toolkit complet à la volée.

Le squelette Inno Setup existant inclut récursivement le lot assemblé et reste
bloqué commercialement. Il faudra vérifier les hashes du runtime assemblé, les
imports PE, le pilote minimum réellement qualifié, les notices natives, les
obligations LGPL et l'application sur Windows vierge physiquement déconnecté,
avec puis sans GPU. **Aucun nouveau Setup commercial n'est déclaré prêt.**

**Risque de taille du fichier unique** : le runtime GPU seul représente 8,0 Go
non compressés, avant Large-v3, Small, sherpa et Qwen. Inno Setup annonce une
[limite proche de 4 Go pour un seul Setup.exe](https://jrsoftware.org/files/is6.5-whatsnew.htm).
La taille compressée de l'ensemble n'a pas été mesurée. Si elle atteint cette
limite, le squelette Inno actuel ne satisfait pas l'exigence du fichier unique :
une solution de packaging devra être prouvée séparément. Des fichiers annexes
ou un téléchargement ne sont pas considérés comme une résolution de l'objectif.

## Raccord réel au registre et à la rédaction inchangés

Une autre copie isolée des 36 interventions GPU a été transmise à
`Pipeline.prepare_registry` puis `Pipeline.generate(..., 'summary')`, sans
changer ni nommer les voix automatiquement. Résultat réel : **411,515 s** pour
le registre, 14 unités inspectées sur 14, 24 informations et 36 passages sources
conservés, dont 12 sans citation candidate. Les 24 informations sont à vérifier,
aucune admissible ; la rédaction s'arrête après 2,558 s avec
`REGISTRY_NO_ELIGIBLE_INFORMATION`. `pv-compatibility/report.json` et les
checkpoints conservent cet essai. Ce n'est pas un compte rendu généré avec succès.

La validation humaine du registre est donc un point de recette restant avant
un PV municipal issu de cette séance. Aucune information n'a été approuvée
artificiellement pour franchir cette porte. Les exports réels de transcription
ont été testés séparément dans la fixture explicitement étiquetée ; les tests
automatisés existants couvrent les affirmations, révisions et exports de PV.

Voir [audit de redistribution GPU](audio-gpu-licenses.md).
