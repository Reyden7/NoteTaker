# Versions et compatibilité

Audit mis à jour le 18 octobre 2026. Les versions ci-dessous sont des choix d'étude,
pas une certification Windows 10/11 de l'ensemble du produit.

| Composant | Version ou révision | Windows x64 et état constaté |
|---|---|---|
| Python | 3.11.16, build Astral 20260901 | Environnement de test installé ; Python système 3.14 écarté |
| faster-whisper | 1.2.1 | Transcription française réelle CPU réussie |
| CTranslate2 | 4.6.0 | CPU int8 validé ; frontal cuDNN 9.1.0.70 importé même en CPU, backend GPU incomplet |
| setuptools | 80.9.0 | Fixe l'import `pkg_resources` requis par CTranslate2 4.6 |
| PyAV / FFmpeg | 16.0.1 / libavcodec 62.11.100 | Imports WAV, MP3 et M4A réellement décodés ; redistribution à auditer |
| numpy | 2.2.6 | Import et ASR validés |
| huggingface-hub / tokenizers | 0.36.0 / 0.22.1 | Compatibilité ASR testée avec modèles locaux |
| pyannote.audio | 4.0.2 | Import réussi, inférence bloquée par poids absents |
| torch / torchaudio | 2.8.0+cpu / 2.8.0+cpu | Imports et produit matriciel CPU exécutés |
| torchcodec | 0.7.0 | Roue cp311 win_amd64 publiée ; chargement natif échoue ici |
| Community-1 | 3533c8cf8e369892e6b79ff1bf80f7b0286a54ee | Métadonnées accessibles ; config HTTP 401 |
| llama.cpp | b11681, archive Windows CPU x64 | Qwen3 4B exécuté CPU, JSON valide |
| Qwen3 4B GGUF | bc640142c66e1fdd12af0bd68f40445458f3869b, Q4_K_M | 2 497 280 256 octets, CPU testé |
| Whisper small CT2 | 536b0662742c02347bc0e980a01041f333bce120 | model.bin 483 546 902 octets, CPU testé |
| sounddevice | 0.5.3 | Capture WASAPI réelle 2,944 s à 48 kHz ; longue réunion non validée |
| sherpa-onnx et sherpa-onnx-core | 1.13.8 / 1.13.8 | Deux voix synthétiques retrouvées en CPU ; GPU non qualifié |
| segmentation ONNX pyannote 3.0 | Archive GitHub asset 197666131, SHA-256 figé | LICENSE MIT inclus ; modèle float testé |
| embedding 3D-Speaker ERes2Net base | GitHub asset 198893098, SHA-256 figé | Fiche des poids Apache-2.0 ; modèle testé CPU |
| PySide6 | 6.8.3 | Interface installée, parcours widgets testés et rendu Windows inspecté |
| python-docx / ReportLab | 1.2.0 / 4.4.4 | Exports réels testés dans l'environnement verrouillé |
| jsonschema | 4.25.1 | Validation structurelle exécutée |
| PyInstaller | 6.16.0, hooks-contrib 2026.8 | Bundle produit ; trois workers autonomes exécutés avec modèles locaux |
| backports.tarfile | 1.2.0 | Collecté explicitement pour setuptools/pkg_resources dans le worker compilé |
| Inno Setup | 7.1.0 candidat | Non installé ; taille du Setup à qualifier |

`requirements.lock` contient les dépendances transitives du socle ASR,
audio, interface, sherpa, export, tests et build, avec hashes. L'environnement a été synchronisé dessus.
`requirements-diarization.snapshot.txt` est seulement un inventaire exact des
versions essayées, sans hashes : ce n'est pas un verrou de distribution approuvé.
Les inventaires JSON de `evidence` ne sont pas encore un SBOM complet des DLL.
La candidate sherpa est verrouillée dans `requirements.lock` et ses modèles
dans `diarization_models_manifest.json`. Le fichier de snapshot PyTorch décrit
la piste antérieure, conservée pour tracer l'audit et non pour livrer les deux piles.

## Complément de recette 0.2

Sur le même poste Windows x64, Whisper a retranscrit le débat complet sur CPU
avec timestamps de mots et zéro caractère U+FFFD. Le protocole JSON ASCII évite
la perte de caractères constatée avec la page de codes de stdout compilé.
La segmentation et les embeddings WeSpeaker ResNet34 adaptés par métadonnées
ont été exécutés avec sherpa 1.13.8. Noto Sans Regular/Bold est incorporé au PDF
et au DOCX ; Word a rendu un document de contrôle en lecture seule.
ONNX 1.19.1 sert seulement à préparer les métadonnées au build et reste exclu
des exécutables. La qualité humaine du débat et Windows vierge restent à valider.

La comparaison complète utilise Qwen3-4B-Instruct-2507 Q4_K_M (quantification
Unsloth, révision et hashes dans `models_manifest.json`). Ce modèle est désormais
celui du nouveau lot de développement, avec llama.cpp CPU b11681. Les 18 blocs
du débat sont réellement traités ; 36 informations sont retenues dans huit
thèmes. La fidélité humaine reste non validée. L'ancien Qwen3-4B reste archivé.

Une variante CTranslate2 4.6.0 CPU seule a été compilée avec MSVC 19.51/CMake
4.3.1 et Ruy. Son import via l'extension cp311 de la roue officielle réussit
dans un paquet isolé ; les imports PE ne contiennent ni cuDNN ni CUDA. L'essai
réel ASR sur 30 secondes naturelles dépasse le délai de 600 secondes : échec
documenté, sans qualification de transcription, de performance ni Windows propre.
L'environnement actif et le bundle conservent la roue initiale : ne pas
présenter l'application comme déjà libérée de cette dépendance NVIDIA.

## GPU (qualification distincte)

CTranslate2 4.6 et faster-whisper 1.2.1 nécessitent CUDA 12/cuBLAS et cuDNN 9
pour Whisper. La page d'installation générale CTranslate2 consultée mentionne
encore cuDNN 8, tandis que le README faster-whisper décrit cuDNN 9 : ne pas
composer le lot depuis ces indications génériques. Il faut figer le tag,
identifier chaque DLL et exécuter une transcription avec ce lot exact.

Sur la RTX 5070 détectée (pilote 616.92, environ 12 Go VRAM), CT2 voit un GPU
mais la transcription termine le worker avec le code Windows 3221226505,
après `Could not locate cudnn_ops64_9.dll`. Le routeur relance un worker CPU
qui réussit. Aucun gain GPU n'a été mesuré. La prise en charge des architectures
Blackwell et des GPU plus anciens doit être vérifiée avec le build choisi.

La diarisation du produit 0.1 utilise sherpa-onnx dans un worker CPU séparé,
sans PyTorch. La pile PyTorch du tableau est une étude antérieure conservée
dans un environnement distinct et exclue du bundle. Dans cette étude,
torchcodec 0.7 ne chargeait pas ses DLL FFmpeg 4–7 ; la voie Community-1
n'a pas été intégrée. Aucun test CUDA de diarisation n'est validé.

Le LLM a été testé en CPU uniquement. CUDA et Vulkan restent à qualifier
indépendamment. Pour AMD/Intel, aucun support accéléré n'est revendiqué.
Le CPU est une voie obligatoire, dont les minima RAM et CPU restent à mesurer
sur des machines de 8 et 16 Go. La machine de développement a environ 32 Go RAM
et ne valide donc pas ces minima.

## Sources officielles

- [Exigences faster-whisper](https://github.com/SYSTRAN/faster-whisper/tree/v1.2.1)
- [Installation CTranslate2](https://opennmt.net/CTranslate2/installation.html)
- [Dépendances pyannote.audio 4.0.2](https://raw.githubusercontent.com/pyannote/pyannote-audio/4.0.2/pyproject.toml)
- [TorchCodec et FFmpeg](https://github.com/meta-pytorch/torchcodec)
- [Qt 6.8 et versions Windows](https://doc.qt.io/qt-6.8/supported-platforms.html)
- [Métadonnées PySide6 6.8.3](https://pypi.org/pypi/PySide6/6.8.3/json)
- [Binaire llama.cpp testé](https://github.com/ggml-org/llama.cpp/releases/tag/b11681)

Qt 6.8 documente Windows 10 à partir de 1809 ; la recette produit visera
Windows 10 22H2 et Windows 11 x64 sur installations propres. La disponibilité
d'une roue ou la compatibilité Qt ne prouvent pas celle de toute la chaîne.
