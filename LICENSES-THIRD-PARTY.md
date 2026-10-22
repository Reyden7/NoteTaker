# Notices tierces de NoteTaker

**Registre initial de phase 0, incomplet pour une distribution commerciale.**
Le détail des conclusions et sources est dans [docs/licenses.md](docs/licenses.md).
Les métadonnées des dépendances réellement essayées sont dans `docs/evidence`.

Les poids actuels et moteurs sont exclus de Git. Aucune licence globale du
projet ne remplace les droits et obligations propres aux fichiers embarqués.
Avant livraison, ce fichier sera accompagné des textes de licences, copyrights,
NOTICE, sources/offres LGPL et mentions des composants natifs correspondant
exactement aux hashes du bundle. Le Setup doit permettre leur consultation hors ligne.

Attributions initiales à compléter : Whisper/OpenAI et conversion SYSTRAN ;
CTranslate2/OpenNMT ; llama.cpp/ggml-org ; Qwen/Qwen Team ; segmentation 3.0/CNRS ;
conversion sherpa-onnx et contributeurs ; 3D-Speaker et ses auteurs ; Qt/The Qt Company ;
python-docx, ReportLab, PortAudio, PyAV/FFmpeg, Python/PSF et leurs contributeurs.
Silero VAD est utilisé par faster-whisper ; ses poids ONNX embarqués et son
texte MIT doivent être couverts dans le lot exact. QtMultimedia et ses plugins
FFmpeg font également partie de l'audit natif restant.

La version de développement 0.1 collecte les notices disponibles des 52
distributions inventoriées, dont PySide6 6.8.3 et backports.tarfile 1.2.0, dans
`third_party/asr`. La présence de ces textes ne constitue pas un SBOM exhaustif,
une offre de sources LGPL complète ni une autorisation du lot commercial.

Situation initiale : Community-1 n'avait pas été acquis. Depuis le 20 octobre
2026, le modèle acquis avec l'accord du titulaire du compte HF et son runtime
PyTorch/pyannote font l'objet d'essais locaux. L'intégration GPU du 21 octobre
est décrite dans [docs/audio-gpu-licenses.md](docs/audio-gpu-licenses.md), avec
attributions dans `third_party/audio-gpu/NOTICE.md`. La redistribution du lot
Windows complet reste non approuvée.

Étude qualité 0.2 : WeSpeaker VoxCeleb ResNet34 (fiche de poids officielle
Apache-2.0 ; adaptation des métadonnées tracée), Noto Sans Regular/Bold et
The Noto Project Authors (SIL OFL 1.1). La licence complète des polices est
livrée avec les TTF dans les ressources de l'application ; provenance et
empreintes dans `docs/evidence/quality-assets.json`. Le registre commercial
complet reste à finaliser, notamment l'attribution du modèle WeSpeaker.

Synthèse du lot 0.2 sélectionné : Qwen3-4B-Instruct-2507, Qwen Team /
Alibaba Cloud, sous Apache-2.0 ; quantification Q4_K_M par Unsloth, également
déclarée Apache-2.0. Révision de base `cdbee75f17c01a7cc42f958dc650907174af0554`,
révision GGUF `a06e946bb6b655725eafa393f4a9745d460374c9`. LICENSE et fiches
de provenance sont dans `models/llm/qwen3-4b-instruct-2507` et figurent au
manifeste avec leurs empreintes. L'ancien modèle Qwen est conservé hors du
nouveau payload. Cette sélection de développement n'approuve pas le lot commercial.

Le lot natif contient encore le frontal NVIDIA cuDNN 9.1.0.70 provenant de
CTranslate2. Sa redistribution pour la cible CPU générale reste bloquée dans
l'audit ; ne pas annoncer un lot CPU déjà dépourvu de composant NVIDIA.
Qt Virtual Keyboard et PortAudio ASIO sont exclus du nouveau bundle vérifié.
