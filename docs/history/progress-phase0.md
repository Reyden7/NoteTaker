# Historique de phase 0 avant la version de travail 0.1

Date : 16 octobre 2026. **Phase 0 en cours ; sortie de phase non validée.**
Le cahier des charges a été lu intégralement et copié dans `reference` sans
modification (SHA-256 : `0e910b83ce8a724d1bef1f0cb00738be20885f1e54ddd3629d6c5fa5fce3ee40`).
La demande directe de l'utilisateur fixe le nom NoteTaker et demande de commencer
par la faisabilité ; les recommandations et prompts inclus dans le document
sont des exigences de référence, pas une autorisation de sauter les validations.

## Fonctionne et a été exécuté

- Environnement Python 3.11 x64 isolé et dépendances verrouillées avec hashes.
- Transcription française réelle par Whisper small int8 CPU sur audio synthétique
  local ; quatre segments horodatés et aucun téléchargement pendant la tâche.
- Génération réelle Qwen3 4B Q4_K_M dans llama.cpp CPU ; JSON conforme au schéma,
  source s0, vote absent laissé à vérifier dans cet exemple.
- À la demande de l'utilisateur, alternative Community-1 étudiée et exécutée :
  sherpa-onnx + segmentation MIT + ERes2Net Apache-2.0 retrouve deux voix
  synthétiques alternées sans nombre de locuteurs imposé.
- Tentative ASR GPU réelle : crash du worker faute de cuDNN 9 ; le routeur
  conserve son parent et réussit une nouvelle tentative CPU.
- Exports techniques DOCX/PDF locaux sur données fictives ; fichiers relus par
  python-docx/pypdf et pages contrôlées visuellement. PDF rendu par Poppler ;
  DOCX rendu par Word installé, en lecture seule, fichier source inchangé.
- SQLite WAL, première migration, rollback d'une migration échouée,
  réouverture, état des jobs interrompus et backup SQLite incluant le WAL validé.
- Écriture et contrôle d'intégrité de segments PCM, conservation d'orphelins et
  fichiers partiels après un véritable arrêt de processus et une erreur de manifeste.

## Tests réellement exécutés

**25 tests automatisés réussis**, aucun ignoré, rapport JUnit dans
`evidence/pytest.xml`. Commande de référence : `scripts/test.ps1`.
Les tests de routage injectent des fautes explicitement et ne sont pas des
preuves d'inférence ; les trois moteurs sont mesurés séparément par leurs sondes.

| Vérification | Preuve |
|---|---|
| ASR CPU et crash CUDA, puis repli | `evidence/phase0-probes.json` et sorties locales `output/phase0/asr-*` |
| GGUF CPU et schéma JSON | Même rapport, `llm_cpu.schema_valid=true`, sortie locale `llm-draft.json` |
| Deux voix distinctes, regroupement automatique | `evidence/diarization-alternative-probe.json` |
| Intégrité et provenance modèles | `models_manifest.json`, `diarization_models_manifest.json` |
| Versions et licences empaquetées initiales | `evidence/dependencies-*.json`, `third_party` |
| Rendu documentaire | `output/phase0/export-fixture-pdf.png` et `export-fixture-word.png` inspectés |
| Fichiers récupérables après arrêt du processus | Tests `test_segment_survives_a_real_child_process_crash` et `test_failure_between_wav_commit_and_manifest_preserves_orphan` |
| Aucun socket Python autorisé | Crochet d'audit des workers et test de blocage avant DNS |
| Texte français conservé par le lanceur | Encodage UTF-8 imposé et test du résultat accentué |

La machine possède environ 32 Go RAM, 20 processeurs logiques et une RTX 5070
de 12 Go (pilote 616.92). Le détail matériel et l'espace disponible sont dans
`evidence/hardware.json`. Les durées exactes et RSS agrégées échantillonnées sont
dans les rapports de sondes ; elles ne sont pas extrapolables à un PC de mairie.
Les RSS du premier essai ASR sont invalides car seul le trampoline était suivi ;
le dernier rapport mesure l'arbre de processus et remplace ces valeurs.

## Reste à valider en phase 0

- Corpus français naturel et annoté à deux puis trois voix, chevauchements,
  attribution incertaine, WER/DER et coût de correction humaine.
- Capture microphone réelle, normalisation multicanal, import MP3/M4A et durée longue.
- Constitution des DLL GPU compatibles, autorisées et isolées ; tâche accélérée
  réelle par moteur et tests mémoire/DLL. Sherpa est pour l'instant CPU uniquement.
- Pipeline continu ASR → attribution corrigée → LLM → validation humaine → export.
  Les sondes actuelles sont indépendantes et sur entrées courtes.
- Vérification système du fonctionnement sans réseau : les crochets Python et
  le mode offline llama ne capturent pas les sockets natives ni l'installation.
- Minima 8/16 Go RAM, Windows 10 x64 et véritables Windows vierges déconnectés.
- Notices finales, SBOM natif, droits exacts FFmpeg/Qt/runtimes et recette de build.
- Volume réel compressé du lot et faisabilité prouvée du Setup unique.

## Risques et incidents observés

Community-1 retourne HTTP 401. Ses conditions n'ont pas été acceptées ; il n'est
pas acquis. L'utilisateur préfère une alternative : la candidate sherpa est
documentée et testée, son adoption définitive attend les critères qualité.

CTranslate2 4.6 requiert `pkg_resources`, absent de setuptools 84 installé lors
du premier essai. La version 80.9.0 est figée pour l'environnement technique.
Un futur choix CT2 plus récent pourra supprimer cette dette après qualification.
CUDA ne trouve pas `cudnn_ops64_9.dll` et provoque un arrêt natif Windows : aucun
support GPU ne doit être annoncé à partir du seul inventaire matériel.

La piste pyannote/PyTorch s'importe en CPU mais TorchCodec ne charge pas ses
DLL FFmpeg ici. Elle reste un essai documenté séparé ; la candidate sherpa n'en
dépend pas. Les métadonnées FFmpeg de la roue PyAV demandent encore un audit
des codecs et de la compilation exacte avant redistribution.

Inno Setup exige plusieurs fichiers au-delà de 4 200 000 000 octets compressés.
Les modèles ASR/LLM occupent environ 2,98 Go avant runtimes. La réduction de la
pile de diarisation aide, mais ne garantit pas le volume avec CUDA/cuDNN.

Les échecs initiaux de tests dus au répertoire temporaire du bac à sable ont
été résolus par un répertoire de test sous `.cache`. Un appel fsync sur un
descripteur ouvert en lecture seule échouait sous Windows ; il a été corrigé
et les exports sont maintenant testés. Le rendu LibreOffice demandé par l'outil
DOCX était indisponible ; le contrôle réel a été effectué avec Word + Poppler.

## Phases suivantes

| Phase | État |
|---|---|
| 0 — Faisabilité | En cours, preuves CPU et audit initial disponibles |
| 1 — Séances, DB complète et UI | Non développée ; seule première migration technique existe |
| 2 — Capture robuste | Expérience de durabilité seulement, pas de recorder utilisateur |
| 3 — ASR, diarisation et correction | Sondes réelles ; pipeline produit non développé |
| 4 — PV et exports | Schéma et exports techniques ; éditeur, contrôles factuels et workflow humain à développer |
| 5 — Matériel et backends | Routage testé ; inventaire complet et GPU à qualifier |
| 6 — Installation hors ligne | Non réalisée, aucun `NoteTaker-Setup.exe` produit |
| 7 — Recette terrain et commercialisation | Non réalisée |
