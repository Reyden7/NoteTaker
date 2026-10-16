# Audit des licences et de la redistribution

État au 16 octobre 2026. Cet audit distingue le code, les poids, les bibliothèques
natives et les conditions d'acquisition. Une licence permissive du moteur ne
vaut pas autorisation de redistribuer toutes ses dépendances. Aucun lot final
de distribution n'est approuvé aujourd'hui.

## Modèles et moteurs

| Élément | Licence et conclusion initiale | Obligations ou réserve |
|---|---|---|
| faster-whisper 1.2.1 | MIT, usage commercial et redistribution possibles | Conserver copyright et texte de licence |
| CTranslate2 4.6.0 | MIT | Auditer aussi DLL CPU, OpenMP/MKL/oneDNN et CUDA du binaire choisi |
| Whisper small et conversion Systran | MIT annoncée pour les poids et leur conversion | Conserver provenance, licence des poids originaux et conversion, révision et hashes |
| llama.cpp b11681 | MIT | Notices du moteur et dépendances réellement livrées |
| Qwen3 4B GGUF officiel | Apache-2.0 | Inclure LICENSE, NOTICE si fourni, provenance et modifications ; modèle Q4_K_M précisément identifié |
| pyannote.audio 4.0.2 | MIT | Télémétrie désactivée explicitement ; ne pas inclure la voie cloud |
| Community-1 | CC-BY-4.0, usage commercial et redistribution permis avec attribution | Accès HF conditionné aux coordonnées/conditions ; poids non acquis, pas de validation du lot complet |
| sherpa-onnx 1.13.8 et core | Apache-2.0 | Notices et audit du binaire Windows et ONNX Runtime inclus |
| pyannote segmentation 3.0 convertie ONNX | MIT ; archive contient LICENSE CNRS | Inclure licence, origine du modèle et conversion ; acquisition publique depuis la release sherpa documentée |
| 3D-Speaker ERes2Net base 3dspeaker 16k | Fiche des poids originaux : Apache License 2.0 | Conserver fiche originale, licence, conversion ONNX et hash exact ; ne pas confondre avec la licence du seul dépôt de code |

L'utilisateur a demandé l'étude d'une alternative à Community-1. La voie
sherpa-onnx + segmentation 3.0 + 3D-Speaker est désormais une **candidate testée**.
Elle évite la pile PyTorch dans le futur lot de diarisation CPU, ce qui réduit
le volume et les conflits de DLL. Son adéquation aux chevauchements, au français
naturel et aux longues séances reste à démontrer ; le choix de production est ouvert.

La segmentation originale sur Hugging Face demande elle aussi un accord d'accès.
La documentation sherpa publie une conversion redistribuée et son LICENSE MIT :
l'essai utilise cette distribution publique, sans requête authentifiée ni
contournement du portail d'origine. La fiche ModelScope des **poids** ERes2Net a
été lue et copiée dans `evidence/3dspeaker-model-card.md`, avec son en-tête Apache.
Les archives anciennes GitHub ne publient pas de digest : leurs empreintes ont
été calculées lors de l'acquisition, puis figées pour les acquisitions suivantes.
Elles ne sont pas présentées comme des hashes certifiés par l'auteur.

Les modèles `nvidia/diar_sortformer_4spk-v1` et Reverb ne sont pas des remplacements
commerciaux acceptés : les sources consultées indiquent une restriction
non commerciale. Aucun poids de ces modèles n'a été intégré.

## Interface et traitement documentaire

PySide6/Qt propose une voie LGPLv3/GPLv3 ou commerciale. Une application
propriétaire peut envisager les modules LGPL avec les obligations applicables :
notices, texte de licence, accès aux sources exactes et modifications de ces
bibliothèques, possibilité de remplacer/recombiner la bibliothèque et absence
de restriction empêchant le débogage de ces modifications. Un bundle onedir
avec DLL remplaçables est le choix initial ; il ne suffit pas à lui seul à
prouver la conformité. Éviter les modules uniquement GPL, auditer les composants
Qt tiers et vérifier les termes de l'EULA produit. Une licence Qt commerciale
est une autre voie, pas une autorisation supposée acquise.

python-docx est MIT ; ReportLab est BSD. lxml et ses bibliothèques XML,
Pillow et les polices utilisées doivent aussi figurer dans le lot de notices.
Les PDF d'essai utilisent les polices de base ; la couverture Unicode complète
(noms propres, symboles, alphabets supplémentaires) devra employer une police
embarquée avec licence vérifiée. Le logiciel exporte sans Word ni LibreOffice.
Word installé a uniquement servi à la QA du DOCX sur le poste de développement.

## Audio et bibliothèques natives

sounddevice et PortAudio sont sous licences permissives (MIT pour sounddevice,
licence permissive PortAudio). La roue Windows contient aussi une variante ASIO :
elle sera exclue tant que son droit de redistribution n'a pas été vérifié.
Le chemin produit visé est WASAPI. Aucun besoin fonctionnel d'ASIO n'est retenu.

PyAV est BSD-3-Clause ; FFmpeg suit sa propre licence selon la compilation.
La roue 16.0.1 essayée expose « LGPL version 3 or later » dans ses bibliothèques,
mais sa configuration mentionne libx264/libx265. Cette combinaison exige un
examen de ses recettes et notices exactes ; on ne l'approuve pas sur la seule
chaîne de licence retournée. Les métadonnées natives sont conservées dans
`evidence/pyav-library-meta.json`. Une compilation contrôlée de FFmpeg avec les
seuls codecs audio nécessaires est l'alternative à qualifier. Respecter la
mise à disposition des sources et les obligations de remplacement/recombinaison
LGPL ; examiner les éventuels droits de codecs selon les territoires concernés.
Les imports MP3/M4A ont ensuite été réellement décodés dans la version 0.1 ;
cette réussite technique ne lève pas les réserves de redistribution.

PyTorch/TorchAudio sont sous licences de type BSD et TorchCodec BSD-3-Clause,
avec de nombreux composants tiers et FFmpeg séparé. Ces composants sont dans
un environnement d'étude distinct. Ils ne sont pas nécessaires à la candidate
sherpa CPU et ne doivent pas être livrés « par défaut » si ce choix est confirmé.

CUDA/cuBLAS et cuDNN sont sous EULA NVIDIA. Les portions autorisées ne sont
pas l'intégralité du Toolkit. L'annexe A CUDA liste notamment les DLL de runtime
et cuBLAS redistribuables ; le supplément cuDNN autorise ses fichiers runtime
DLL sous les conditions de distribution. Figer chaque nom, version, hash et
EULA, conserver les notices tierces et adapter les conditions produit.
Les pilotes restent un prérequis système ; NoteTaker ne les installe pas.
Aucune DLL NVIDIA n'a encore été constituée en lot redistribuable validé.

## Python et outils de livraison

Python est sous licence PSF et bibliothèques tierces associées. Le build de
développement est Astral python-build-standalone 3.11.16 : ses notices et son
origine doivent être traitées si ce runtime est retenu pour livraison.
Ne pas substituer sans étude un ancien runtime Windows 3.11.9 simplement
parce qu'il était le dernier installateur officiel de la série de correctifs.

PyInstaller est GPL avec une exception permettant les applications générées
sous d'autres licences, y compris commerciales ; cette exception ne change
pas les licences des bibliothèques collectées. Inno Setup permet l'utilisation
commerciale selon son texte de licence ; le site demande aux utilisateurs
commerciaux d'acheter une licence commerciale. Cette demande doit être distinguée
des conditions du texte effectivement livré avec la version retenue. Aucun
achat ni acceptation nominative n'a été effectué ici.

Les redistribuables Visual C++ ne sont pas simplement copiables parce qu'ils
sont installés sur ce poste. Microsoft réserve leur distribution aux utilisateurs
Visual Studio licenciés selon les termes applicables et la liste REDIST. Le
build final devra disposer de ce droit et embarquer le runtime requis hors ligne.

Les dépendances transitives Python (NumPy, ONNX Runtime, psutil, jsonschema,
requests, tokenizers, etc.) disposent d'un premier inventaire de métadonnées.
Un champ de métadonnée manquant n'est pas une preuve d'absence de licence.
Le contrôle final doit couvrir chaque fichier du bundle, les DLL transitives,
sources/offres nécessaires et polices, avec un SBOM et des notices accessibles.

## Sources primaires

- [Whisper, licence du code et des poids](https://github.com/openai/whisper)
- [Systran Whisper small](https://huggingface.co/Systran/faster-whisper-small)
- [Qwen3 4B GGUF et LICENSE](https://huggingface.co/Qwen/Qwen3-4B-GGUF)
- [Community-1, licence et conditions](https://huggingface.co/pyannote/speaker-diarization-community-1)
- [Texte CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en)
- [Segmentation 3.0, licence MIT](https://huggingface.co/pyannote/segmentation-3.0)
- [Distribution ONNX documentée](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/models.html)
- [Fiche des poids ERes2Net originaux](https://modelscope.cn/models/iic/speech_eres2net_base_sv_zh-cn_3dspeaker_16k)
- [Code 3D-Speaker et licence](https://github.com/modelscope/3D-Speaker)
- [Licence sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE)
- [Sortformer v1, restriction non commerciale](https://huggingface.co/nvidia/diar_sortformer_4spk-v1)
- [Licences Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html)
- [FFmpeg et obligations de distribution](https://ffmpeg.org/legal.html)
- [Construction des FFmpeg de PyAV](https://github.com/PyAV-Org/pyav-ffmpeg)
- [PortAudio et variantes ASIO](https://python-sounddevice.readthedocs.io/en/0.5.3/installation.html)
- [EULA CUDA et annexe A](https://docs.nvidia.com/cuda/eula/index.html)
- [EULA cuDNN 9.10.2](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html)
- [Exception PyInstaller](https://pyinstaller.org/en/stable/license.html)
- [Texte de licence Inno Setup](https://jrsoftware.org/files/is/license.txt)
- [Distribution Visual C++](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170)

## Condition de validation commerciale

Les possibilités de redistribution ci-dessus sont conditionnelles aux textes
et composants exacts. Les manifestes restent `development-only` / `pending-notices`.
L'audit technique initial n'est pas une approbation juridique de l'EULA finale.
Le lot sera bloqué si un fichier n'a pas une provenance, un hash, une licence
et les obligations de redistribution documentées.

## Delta du lot de développement 0.1

PySide6 6.8.3, ses paquets Essentials/Addons et shiboken6 sont maintenant
installés et collectés par PyInstaller. La lecture audio utilise QtMultimedia :
ses plugins et son backend FFmpeg doivent aussi figurer dans l'audit natif,
en plus de FFmpeg privé de PyAV. Le choix `onedir` permet l'accès aux DLL ;
les notices collectées ne constituent ni un dossier de sources complet ni
une validation du remplacement effectif des bibliothèques LGPL.

Whisper emploie désormais le VAD Silero ONNX déjà inclus dans la roue
faster-whisper. Le dépôt amont Silero annonce MIT ; inclure sa provenance,
la licence et l'empreinte du fichier effectivement embarqué dans le SBOM final.
Source : [licence Silero VAD](https://github.com/snakers4/silero-vad/blob/master/LICENSE).

Le build utilise PyInstaller 6.16.0, hooks-contrib 2026.8 et backports.tarfile
1.2.0. Ce dernier est nécessaire à la chaîne setuptools/pkg_resources du worker
compilé et fait partie du verrou. L'inventaire Python a été régénéré avec
52 distributions ; les textes fournis par les paquets sont copiés dans
`third_party/asr`. Cet inventaire ne recense pas encore toutes les DLL et leurs
composants tiers. La DLL PortAudio ASIO est filtrée du bundle.

Le dossier CPU de développement ne contient ni la pile PyTorch étudiée
antérieurement ni un lot CUDA/cuDNN. Les trois modèles locaux et llama CPU
sont copiés avec leurs manifestes, dont le statut reste `development-only` /
`pending-notices`. Aucun résultat de test fonctionnel ne change ce statut.
