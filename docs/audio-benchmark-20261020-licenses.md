# Laboratoire audio — licences et redistribution, 20 octobre 2026

## Périmètre et conclusion

Audit des actifs **effectivement acquis pour l'expérience**, hors production.
Les preuves figent les révisions, tailles et SHA-256 sous
`output/audio-benchmark/2026-10-20-01/assets`. Les paquets réellement installés,
leurs versions, métadonnées de licence et chemins de notices figurent dans
`environments/A.json`, `B.json`, `C.json` ; les textes fournis par les paquets
sont copiés avec empreintes dans `licenses/index.json` du même dossier.
Ces inventaires ne remplacent pas une nomenclature exhaustive des DLL natives.

Les licences des modèles examinés autorisent un usage commercial sous leurs
conditions. **Le lot Windows n'est pas approuvé pour redistribution commerciale.**
L'expérience ne constitue ni un installateur, ni une recette sur Windows vierge,
ni une décision de remplacer le moteur NoteTaker.

## Actifs des modèles épinglés

| Actif | Provenance et révision | Licence | Obligations et conclusion |
|---|---|---|---|
| Large-v3, conversion faster-whisper | `Systran/faster-whisper-large-v3`, `edaa852ec7e145841d8ffdb056a99866b5f0a478` | MIT annoncée pour la conversion ; Whisper original MIT | Usage commercial et redistribution possibles avec copyrights et licences d'origine/conversion. Poids vérifiés contre SHA LFS. |
| Community-1 | `pyannote/speaker-diarization-community-1`, `3533c8cf8e369892e6b79ff1bf80f7b0286a54ee` | CC BY 4.0 | Usage commercial/redistribution permis avec attribution, lien de licence, indication des modifications, sans restrictions supplémentaires incompatibles. Conserver les crédits des composants et auteurs, pas seulement le nom du pipeline. |
| Aligneur français WhisperX | `jonatasgrosman/wav2vec2-large-xlsr-53-french`, `7c79e105a6525d38e1e69f640b974b4a679723cc` | Apache-2.0 dans la fiche des poids | Conserver la licence, les notices présentes, provenance et changements. Vérifier aussi les obligations des composants d'origine avant distribution. |
| MOSS-Transcribe-Diarize 0.9B | `OpenMOSS-Team/MOSS-Transcribe-Diarize`, `704aa4a9c304e8520be88901e0d1960158ef5b15` | Apache-2.0 dans la fiche des poids | Usage commercial/redistribution possibles sous conditions Apache ; conserver crédits et notices des bases/dérivations. Pas de quantification tierce utilisée. |
| Code officiel MOSS | `OpenMOSS/MOSS-Transcribe-Diarize`, `e3bdd93f8ad58418e04659818efd5fd87a0bc486` | Apache-2.0, texte complet acquis | Installation locale de cette révision ; code Python des poids exécuté via `trust_remote_code=True` après inspection. Aucune autorisation générale pour exécuter un autre dépôt non vérifié. |

Sources primaires : [conversion Large-v3](https://huggingface.co/Systran/faster-whisper-large-v3),
[Whisper original](https://github.com/openai/whisper/blob/main/LICENSE),
[Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1),
[texte CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode),
[aligneur français](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-french),
[poids MOSS](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize),
[code MOSS épinglé](https://github.com/OpenMOSS/MOSS-Transcribe-Diarize/tree/e3bdd93f8ad58418e04659818efd5fd87a0bc486).

Community-1 : l'utilisateur a accepté les conditions d'accès et le partage des
coordonnées sur son compte Hugging Face. Cette formalité d'acquisition est
distincte de la licence CC BY 4.0 ; l'agent n'a ni accepté à sa place, ni créé
de compte, ni recopié le jeton dans le dépôt. Le modèle local complet a ensuite
été acquis et vérifié. Il comprend segmentation, embedding WeSpeaker et PLDA ;
leurs README et crédits sont conservés. La fiche du modèle d'embedding fourni
avec ce pipeline annonce CC BY 4.0 : ne pas la confondre avec le modèle WeSpeaker
Apache de la chaîne A. Les crédits PLDA mentionnent BUT SpeechFIT, Jiangyu Han
et Petr Pálka.

## Code et bibliothèques

| Composant effectivement utilisé | Licence du code | Réserve de distribution |
|---|---|---|
| faster-whisper 1.2.1, CTranslate2 4.6.0 (A) / 4.8.3 (B) | MIT | Notices et composants natifs exacts. Le changement de CTranslate2 est isolé au laboratoire B. |
| sherpa-onnx/core 1.13.8 et modèles actuels A | Apache-2.0 ; segmentation MIT ; modèles selon fiches déjà auditées | Les réserves de `docs/licenses.md` continuent de s'appliquer. Aucun poids produit remplacé. |
| pyannote.audio 4.0.7 et ses bibliothèques pyannote | MIT selon textes fournis | Certaines métadonnées de paquet omettent le champ licence ; utiliser les textes archivés, pas une inférence « champ vide = libre ». `pyannoteai-sdk` est installé comme dépendance transitive ; aucun service cloud n'est appelé. À exclure/justifier lors d'un futur packaging. |
| WhisperX 3.8.6 | **BSD-2-Clause** du tag utilisé | Conserver copyright et licence ; ne pas reprendre une licence attribuée à une ancienne version sans vérifier le tag. |
| PyTorch 2.8.0+cu128, torchaudio/torchvision | BSD pour le code principal et nombreuses notices tierces | Les DLL CUDA/cuDNN/cuBLAS ne deviennent pas BSD parce qu'elles sont dans la roue Torch. Audit de leurs EULA/redistributables et versions exactes encore requis. |
| Transformers 4.57.6 (B) / 5.20.2 (C), NLTK 3.10.3 | Apache-2.0 pour le code | Les données entraînées et modèles ont leurs propres licences. |
| PyAV 16.0.1 (A), 18.1.0 (B), 19.0.1 (C) | BSD-3-Clause pour PyAV | FFmpeg et codecs intégrés : licences, configuration de compilation, sources correspondantes et obligations LGPL/GPL à vérifier pour **chaque** roue. La recette 16.0.1 précédente ne vaut pas preuve pour les autres versions. |
| TorchCodec 0.7.0 (B) | BSD du code selon notice fournie | Décodeur natif non fonctionnel sur ce poste. Pas d'approbation de ses DLL/FFmpeg ; Community-1 fonctionne avec l'entrée tenseur officielle. |

Sources : [WhisperX 3.8.6, licence exacte](https://raw.githubusercontent.com/m-bain/whisperX/v3.8.6/LICENSE),
[pyannote.audio 4.0.7](https://github.com/pyannote/pyannote-audio/blob/4.0.7/LICENSE),
[licence PyTorch 2.8](https://github.com/pytorch/pytorch/blob/v2.8.0/LICENSE),
[licence TorchCodec 0.7](https://github.com/pytorch/torchcodec/blob/v0.7.0/LICENSE),
[licences FFmpeg](https://ffmpeg.org/legal.html).

## Réserves spécifiques

1. **Données `punkt_tab`** : WhisperX nécessite cette ressource NLTK pour
   segmenter les phrases. Acquise explicitement avant inférence et conservée
   localement ; jamais téléchargée par les workers offline. Le README et
   l'[index NLTK](https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt_tab.xml)
   inspectés ne fournissent pas de concession explicite de redistribution des
   paramètres entraînés. Ne pas appliquer automatiquement Apache-2.0 du code
   NLTK aux données. Empreintes locales archivées ; révision amont immuable non
   consignée lors de cette acquisition. **Clarification nécessaire avant inclusion
   commerciale**, ou remplacement contrôlé sans cette donnée à évaluer.
2. **DLL NVIDIA** : ce benchmark sur carte NVIDIA n'autorise pas par lui-même un
   unique lot installable sur machines sans NVIDIA. La restriction cuDNN déjà
   étudiée pour A reste ouverte. Il faut déterminer les versions des DLL du lot
   Torch, leurs termes, les redistribuables permis et la stratégie CPU/GPU.
3. **Dépendances transitives** : inventaires des notices disponibles conservés,
   mais pas encore de revue binaire exhaustive avec sources/notices de tous les
   composants tiers. L'exécution CPU d'une roue CUDA ne la transforme pas en
   distribution CPU dépourvue de ces obligations.
4. **Données de test** : l'utilisation locale du débat fourni par l'utilisateur
   ne donne pas un droit de redistribution de ce média avec le logiciel.
5. **Hors ligne** : acquisitions faites explicitement sur le poste de build ;
   inférences avec chemins locaux, mode offline et blocage Python réseau.
   Une recette sur Windows vierge déconnecté reste indispensable pour qualifier
   un installateur. Aucun Setup construit pour cette expérience.

## Séparation et protection du jeton

La commande de connexion interactive Hugging Face utilise son cache utilisateur
global, hors dépôt. Le jeton n'est passé ni en argument, ni dans les requêtes JSON
des workers, ni dans leurs logs. Les variables `HF_TOKEN` et
`HUGGING_FACE_HUB_TOKEN` sont retirées de l'environnement des workers ; toutes les
charges de modèle utilisent les copies locales. Le cache d'authentification HF
n'est pas un coffre chiffré. Il n'est jamais copié dans les résultats ni le bundle.
Les données de séance et l'audio ne sont envoyés à aucun service.
