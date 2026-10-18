# Audit des licences et de la redistribution

État mis à jour le 18 octobre 2026. Cet audit distingue le code, les poids, les bibliothèques
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
La version 0.2 embarque Noto Sans OFL et refuse les glyphes absents dans les
deux formats. Elle ne revendique pas tous les alphabets. Le logiciel exporte
sans Word ni LibreOffice.
Word installé a uniquement servi à la QA du DOCX sur le poste de développement.

## Audio et bibliothèques natives

### Contrôle du contenu Qt du bundle 0.2

L'inventaire réel a trouvé `Qt6VirtualKeyboard.dll` et
`platforminputcontexts/qtvirtualkeyboardplugin.dll`, collectés automatiquement.
Ce module optionnel n'offre pas la voie LGPL :
[Qt 6.8 le publie sous GPLv3 ou licence commerciale](https://doc.qt.io/qt-6.8/qtvirtualkeyboard-index.html#licenses-and-attributions).
L'application Widgets ne l'emploie pas ; l'examen PE des imports de Core/Gui,
Widgets et Multimedia ne montre aucune dépendance directe à ce module.
La spec l'exclut désormais, plugin compris, et `validate_bundle.py` refuse sa
présence dans le lot reconstruit, ainsi que la variante ASIO déjà écartée.
L'inventaire du dernier bundle confirme l'absence de ces fichiers et d'ASIO ;
le démarrage et l'arrêt réels réussissent le 18 octobre.
Cette correction ne constitue pas un audit exhaustif ni une approbation des
autres composants Qt et des deux piles FFmpeg distinctes.

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

**Constat binaire 0.2 : le profil CPU n'est pas dépourvu de composant NVIDIA.**
La roue Windows CTranslate2 4.6.0 fournit `cudnn64_9.dll` (438 840 octets,
version 9.1.0.70, NVIDIA Corporation). `ctranslate2.dll` l'importe directement,
sans chargement différé ; l'enlever casserait aussi l'import du moteur CPU.
Les DLL de calcul cuDNN manquantes empêchent toujours la voie GPU testée.
Le frontal doit donc entrer dans l'audit de redistribution du lot CPU, ou être
remplacé par un build CTranslate2 contrôlé avec CUDA désactivé, à requalifier.
Ne pas appliquer à ce binaire ancien l'EULA d'une version récente sans vérifier
la licence exacte. Le [supplément cuDNN 9.1.0, section 4.1](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.1.0/reference/eula.html)
limite le développement aux applications destinées aux systèmes avec GPU NVIDIA ;
sa section Distribution autorise les fichiers runtime sous les autres conditions
de l'accord. Le lot actuel n'est donc pas approuvé pour la cible commerciale
CPU générale incluant les PC sans GPU NVIDIA. Un build CTranslate2 CPU sans
cette dépendance, ou un droit distinct vérifié, reste nécessaire.
Inventaire PE et hashes :
`evidence/native-payload-quality02-before-filter.json` et inventaire final
`evidence/native-payload-quality02.json`. Ce constat ne vaut pas
autorisation de redistribution et ne justifie pas un faux frontal de remplacement.

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

Le dossier CPU de développement ne contient pas la pile PyTorch étudiée
antérieurement. Il contient toutefois le frontal cuDNN de la roue CTranslate2,
sans lot de calcul GPU complet, comme décrit plus haut. Les modèles locaux et llama CPU
sont copiés avec leurs manifestes, dont le statut reste `development-only` /
`pending-notices`. Aucun résultat de test fonctionnel ne change ce statut.

## Étude qualité 0.2 — WeSpeaker et polices

Le modèle officiel `Wespeaker/wespeaker-voxceleb-resnet34` annonce Apache-2.0
dans la fiche des poids (révision `ff1ac5bca8ef11e90662b879aa923979e0bd277b`).
Le fichier ONNX original est vérifié contre le SHA-256 LFS amont. La copie
`voxceleb_resnet34-sherpa.onnx` ajoute les métadonnées décrites par sherpa 1.13.8
(échelle des échantillons, framework, dimensions), sans changer les poids.
Les deux hashes et cette modification sont consignés dans
`evidence/quality-assets.json`. L'original reste conservé ; seule la copie
adaptée nécessaire figure au manifeste de distribution de développement.
La fiche ne fournit qu'un en-tête de licence : l'attribution complète et les
obligations du lot exact restent à intégrer au dossier commercial.

Noto Sans Regular/Bold est acquis depuis le dépôt officiel Noto, révision
`ffebf8c1ee449e544955a7e813c54f9b73848eac`, sous SIL OFL 1.1. Les TTF non
modifiés et le texte de licence sont dans `src/notetaker/assets/fonts` et
embarqués dans l'application. La police est incorporée au PDF et au DOCX ;
l'OFL autorise l'incorporation et la redistribution avec le logiciel sous ses
conditions, notamment conservation des notices et absence de vente isolée.
Le logiciel n'emprunte pas une police système Windows pour ces exports.

ONNX 1.19.1 et ml-dtypes servent seulement à l'adaptation pendant le build.
Le module ONNX est exclu de PyInstaller ; l'inférence reste ONNX Runtime/sherpa.
Ces ajouts ne lèvent pas les réserves FFmpeg, Qt, VC++ et Windows propre.

Sources : [poids officiels WeSpeaker](https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34),
[adaptation officielle sherpa](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/scripts/wespeaker/add_meta_data.py),
[licence Noto OFL](https://github.com/notofonts/noto-fonts/blob/ffebf8c1ee449e544955a7e813c54f9b73848eac/LICENSE),
[incorporation TrueType dans Word](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/ea097c57-5794-4624-b08e-017b47051b1d).

### Modèle de synthèse Instruct 2507 sélectionné pour le développement

Les erreurs sémantiques persistantes du Qwen3-4B initial justifient une
comparaison locale de Qwen3-4B-Instruct-2507. Après cette exécution complète,
il est sélectionné dans le manifeste du nouveau lot de développement ; aucune
acceptation humaine de qualité n'en découle. La [fiche officielle du modèle de base](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
annonce Apache-2.0 et un fonctionnement exclusivement sans raisonnement séparé.
La quantification Q4_K_M est produite par
[Unsloth](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF), également
déclarée Apache-2.0 ; cette provenance de conversion doit figurer dans les notices.
Révision quantifiée `a06e946bb6b655725eafa393f4a9745d460374c9`, SHA-256
`3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`.
Les poids, licence complète du modèle de base et fiches sont acquis explicitement
par `scripts/acquire_summary_candidate.py`. Les preuves et révisions sont dans
`evidence/qwen-instruct-candidate.json` et `qwen-instruct-upstream.json`.
Ce modèle n'est pas téléchargé par l'application. Il remplace l'ancien modèle
dans le payload et son manifeste ; les anciens poids sont conservés hors de ce
nouveau lot, qui ne livre donc pas les deux fichiers de 2,5 Go. Les notices
exactes, l'attribution de la conversion et le lot natif restent à approuver.

### Étude d'un runtime CTranslate2 CPU sans NVIDIA

CTranslate2 v4.6.0, révision `617405f4b050e994e829d527da6caa0e0030afe7`,
a été compilé réellement avec Ruy, sans MKL/OpenMP/CUDA/cuDNN et options UTF-8.
La DLL de 7 082 496 octets n'importe que les bibliothèques Windows/Visual C++
inventoriées dans `evidence/ctranslate2-cpu-build.json`. Elle n'est pas injectée
dans l'environnement actif ni dans le bundle ; l'import de son paquet Python
isolé réussit, mais l'essai de transcription naturelle de 30 secondes dépasse
le délai de 600 secondes (`evidence/ctranslate2-cpu-smoke.json`). La variante
n'est donc pas qualifiée ni intégrée. Cette compilation ne lève pas les obligations MIT/tiers du code,
la redistribution Visual C++ ni les autres réserves FFmpeg/Qt.
