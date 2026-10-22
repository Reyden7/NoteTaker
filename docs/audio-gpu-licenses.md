# Audit du lot GPU — 21 octobre 2026

**Utilisation locale de développement éprouvée ; redistribution commerciale du
lot Windows non approuvée.** Complète l'[audit du laboratoire](audio-benchmark-20261020-licenses.md).

## Modèles

| Élément exact | Preuve | Obligations et limites |
|---|---|---|
| Large-v3 SYSTRAN, révision `edaa852ec7e145841d8ffdb056a99866b5f0a478` | [Fiche épinglée MIT](https://huggingface.co/Systran/faster-whisper-large-v3/blob/edaa852ec7e145841d8ffdb056a99866b5f0a478/README.md), [Whisper OpenAI MIT](https://github.com/openai/whisper/blob/main/LICENSE) | Conserver copyrights et texte MIT des poids d'origine et de la conversion. Commerce permis sous conditions MIT ; aucune approbation des DLL n'en découle. |
| Community-1, révision `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee` | Fiche locale épinglée, [fiche officielle CC BY 4.0](https://huggingface.co/pyannote/speaker-diarization-community-1), [texte juridique](https://creativecommons.org/licenses/by/4.0/legalcode.en) | Attribution, lien licence, conservation des mentions fournies, indication des modifications, absence de restrictions additionnelles incompatibles sur les éléments concernés ; aucun endossement implicite. |
| Embedding WeSpeaker VoxCeleb ResNet34-LM inclus | `embedding/README.md` du snapshot : poids CC BY 4.0 et publication Wang et al., ICASSP 2023 | Conserver cette notice propre aux poids inclus ; distincts du modèle ONNX d'affinement CPU. |
| PLDA / VBx inclus | `plda/README.md` du snapshot | Crédits BUT Speech@FIT, Jiangyu Han et Petr Pálka, références fournies et notices associées à conserver. |

L'acquisition initiale Community-1 exige l'accord HF et le partage des coordonnées
du compte de build, acceptés par l'utilisateur. Cette acquisition ne vaut pas
approbation du futur lot redistribué. Les fichiers complets chargent localement
avec un cache HF neuf, sans variables de jeton et sous garde réseau Python ;
aucun compte HF client n'est techniquement requis. Ne jamais copier le cache
d'authentification de build. Aucun poids modifié durant l'intégration ; le
snapshot et la configuration locale `$model` du laboratoire sont réutilisés.

## Code et binaires natifs

| Élément essayé | Preuve / licence principale | Travail restant pour la redistribution |
|---|---|---|
| faster-whisper 1.2.1 / CTranslate2 4.8.3 | Notices et métadonnées locales MIT | Inclure textes MIT, Silero VAD embarqué ; contrôler les dépendances natives exactes. |
| pyannote.audio 4.0.7 | [MIT officielle versionnée](https://github.com/pyannote/pyannote-audio/blob/4.0.7/LICENSE) | Notices pyannote et transitives distinctes. `pyannoteai-sdk` peut être exigé à l'import : aucun service cloud utilisé ; télémétrie désactivée et garde réseau Python. |
| PyTorch 2.8.0+cu128 et torchaudio | [Licence versionnée PyTorch](https://github.com/pytorch/pytorch/blob/v2.8.0/LICENSE), LICENSE/NOTICE des wheels | La licence principale ne couvre pas automatiquement NVIDIA ni tous les composants tiers. Inventaire fichier par fichier nécessaire. |
| cuDNN **9.10.2.21**, version réellement lue de `torch/lib/cudnn64_9.dll` | [EULA cuDNN 9.10.2 et supplément](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html) | Les runtimes DLL sont listés comme distribuables sous conditions ; le supplément vise des applications sur systèmes NVIDIA. Examiner l'articulation avec l'installateur unique distribué aussi aux postes CPU. Point ouvert. |
| CUDA 12.8, cuBLAS / autres DLL du wheel | [EULA CUDA 12.8.1, conditions et liste des composants](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html) | Rapprocher chaque DLL/version de la liste distribuable et des conditions. Ne pas copier le Toolkit complet ou le pilote sous prétexte que PyTorch est BSD. |
| PyAV 18.1.0 | [BSD-3 du binding](https://github.com/PyAV-Org/PyAV/blob/v18.1.0/LICENSE.txt) et interrogation native du wheel | FFmpeg et codecs distincts : voir constat ci-dessous. L'audit CPU PyAV 16 ne couvre pas ce wheel. |
| Python 3.11.16 / bibliothèque standard | `LICENSE.txt` du Python local et notices du distributeur | PSF, OpenSSL et autres éléments livrés, redistribuables Microsoft à inventorier. |
| Fermeture transitive GPU | `portable-runtime/inventory.json` et `requirements-installed.txt` dans la recette | **95 distributions, 27 055 fichiers, 8 000 543 762 octets** dans le staging essayé. Métadonnées de licence déclaratives, pas une autorisation générale. WhisperX n'est pas inclus. |

### Constat natif FFmpeg

`ffmpeg-inventory.json` conserve `av.library_versions`, `avcodec_configuration()`
et `avcodec_license()` réellement interrogés. La DLL avcodec 62 annonce
**LGPL version 3 or later**, avec `--enable-version3`, mais aussi
`--enable-libx264` et `--enable-libx265` dans ses options de construction.
Obtenir la provenance/licence exacte des codecs et les sources correspondant
aux binaires. La chaîne « LGPL » seule ne valide pas ce lot.
[Conditions officielles FFmpeg](https://ffmpeg.org/legal.html).

TorchCodec peut rester nécessaire à l'import ; son décodeur n'est pas appelé.
Les DLL présentes dans le runtime doivent néanmoins être auditées. Les notices
des RECORD sont conservées par l'outil de staging, jamais les médias, résultats
du comparateur ou identifiants HF. Voir `third_party/audio-gpu/NOTICE.md`.

## Conditions de sortie

Le manifeste reste `development-only` / `pending-native-and-notice-audit`.
Avant un Setup : notices consultables hors ligne, provenance modèle/runtime et
Python, obligations FFmpeg (sources/offres et remplacement selon le lot),
conditions NVIDIA documentées pour la cible CPU/GPU, contrats cohérents et
recette sur PC Windows vierge physiquement déconnecté. Les blocages commerciaux
existants du build et d'Inno Setup restent actifs. Ce document est un audit
technique des preuves disponibles, pas un avis juridique.
