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

Community-1 n'a pas été acquis. PyTorch et pyannote.audio ont servi à une étude
de compatibilité ; leur présence dans un environnement de développement ne
signifie pas leur inclusion dans le produit retenu.
