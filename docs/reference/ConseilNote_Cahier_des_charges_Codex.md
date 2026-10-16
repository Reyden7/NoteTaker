# ConseilNote — Cahier des charges technique et plan Codex
Version 1.0 — 16 octobre 2026

## 1. Vision et limites
ConseilNote est un logiciel commercial Windows 10/11 x64, entièrement local et utilisable sans Internet, pour enregistrer et transcrire les réunions de conseils municipaux, distinguer les intervenants, préparer un projet de procès-verbal et exporter des documents après validation humaine. Le procès-verbal n'est jamais officialisé automatiquement. Aucune reconnaissance biométrique automatique des identités dans la V1 : la diarisation distingue les voix par identifiants anonymes, et un opérateur associe manuellement ces identifiants aux noms.

**Livrable de distribution impératif :** un seul `ConseilNote-Setup.exe` installable sur un Windows vierge, sans Python, pip, Git, Ollama, modèles téléchargeables, clés Hugging Face ou accès réseau. Il peut extraire plusieurs Go de données sur le disque. Le support des GPU nécessite toujours un pilote graphique système approprié ; la présence d'un GPU compatible n'est jamais garantie. En son absence, le logiciel fonctionne sur CPU.

## 2. Exigences fonctionnelles (priorité P0 obligatoire, P1 souhaitable)

### P0 — Séances
- Créer, modifier et archiver une séance : commune, date/heure, lieu, titre, ordre du jour, secrétariat, participants, absents, excusés, pouvoirs/procurations (saisis explicitement).
- Importer une liste locale d'élus/participants, avec fonctions et préférences d'affichage ; ne pas créer de profils biométriques.
- Historique filtrable et recherchable ; ne jamais fusionner deux séances.

### P0 — Audio fiable
- Afficher microphones disponibles et niveau sonore en temps réel ; test d'enregistrement et réécoute.
- Démarrer, arrêter, pause/reprise et suivre durée/état ; journaliser incidents sans interrompre l'UI.
- Capture locale dans un format PCM/WAV documenté, segmentée de manière régulière (par exemple 1 à 5 minutes), avec manifest de segments, écritures atomiques et état de reprise après plantage/coupure.
- Interdire la suppression automatique des prises brutes après traitement ; montrer l'espace disque disponible avant une longue séance.
- Importer un fichier audio existant (WAV, MP3, M4A selon codecs effectivement testés).
- Le travail IA se fait en arrière-plan après l'enregistrement en V1, indépendamment de la capture audio.

### P0 — Transcription
- Transcrire français via `faster-whisper` en local, horodatages et indication des segments non fiables quand disponible ; configurations de modèles embarqués, versions figées.
- Audio stéréo/multicanal normalisé proprement ; conserver le fichier source.
- Texte editable sans modifier les données audio ; sauvegarde automatique, annulation/rétablissement, recherche.
- Relier chaque bloc de transcription à sa plage audio (lecture depuis un clic).

### P0 — Intervenants
- Diarisation via modèle `pyannote/speaker-diarization-community-1` ou alternative prouvée utilisable commercialement/offline, acquis et embarqué au build conformément à sa licence/conditions.
- Attribution initiale « Intervenant 1 », « Intervenant 2 », etc. ; correction et fusion/scission manuelles ; association des noms par l'opérateur.
- Gérer segments avec chevauchement ; afficher « attribution incertaine » plutôt que forcer une certitude.
- Ne jamais prétendre vérifier automatiquement l'identité d'un élu.

### P0 — Génération du projet de PV
- Modèle local GGUF et moteur `llama.cpp` embarqués, sélection CPU/GPU séparée de la transcription.
- Entrées : ordre du jour, transcription corrigée, participants, notes manuelles et votes explicitement structurés.
- Sortie JSON validée par schéma : points, synthèses sourcées par identifiants de segments, interventions pertinentes, délibérations proposées, décisions connues, résultats de votes saisis, éléments « à vérifier ».
- Contraindre le modèle à ne jamais inventer noms, montants, dates, délibérations, votes ou quorum. Une information absente reste « à compléter ».
- Traiter les longues réunions par portions cohérentes et synthèse hiérarchique sans dépasser la fenêtre de contexte ; préserver les références aux segments originaux.
- La génération produit un **brouillon non officiel** jusqu'à confirmation de l'opérateur.

### P0 — Validation et exports
- Éditeur de projet de PV : titres, paragraphes, noms, corrections, sections, gestion structurée des votes (pour/contre/abstention/non-participation, selon cas), revue des mentions à vérifier.
- Export DOCX et PDF local, avec entête commune, date, pagination, identifiants de séance ; ne pas apposer de signature ni de mention « approuvé » sans action explicite.
- Export transcription TXT/JSON avec horodatages ; éviter de joindre les segments d'IA non validés comme faits établis.
- Conserver le brouillon et la version exportée distinctement.

### P0 — Stockage, sécurité, confidentialité
- SQLite en stockage local avec migration de schéma versionnée ; fichiers audio et modèles dans des répertoires séparés.
- Installation dans Program Files (ou dossier programme approprié), données modifiables sous `%LOCALAPPDATA%/ConseilNote` par défaut ; configuration d'un dossier d'archives géré par la mairie ; sauvegarde/restauration exportable.
- Conception locale sans télémétrie, téléchargement implicite, serveur externe ou service Windows nécessaire ; désactiver par défaut toute tentative de récupération de modèles.
- Journaux techniques sans contenu des conversations ni données personnelles en clair ; conservation configurable.
- Permissions NTFS, contrôle d'accès OS, et éventuellement chiffrement des archives via mécanismes Windows après étude ; ne jamais présenter SQLite simple comme chiffré.
- Définir avec la collectivité les durées de conservation, l'information préalable des participants, les accès et les règles de publication ; ne pas intégrer de délai légal arbitraire.

### P0 — Paramètres et diagnostics
- Inventaire CPU, RAM, GPU, VRAM approximative et versions de pilotes/bibliothèques.
- Tester effectivement l'initialisation de chaque moteur (Whisper, diarisation, LLM) avec une petite tâche représentative ; ne pas se fier seulement au nom de GPU.
- Modes « Auto », « CPU uniquement », « GPU si compatible » avec retour CPU automatique et message détaillé.
- Le mode GPU peut différer selon moteur : CTranslate2/CUDA pour Whisper, PyTorch/CUDA si compatible pour pyannote, llama.cpp CUDA ou Vulkan pour la synthèse.
- En cas d'échec (DLL, mémoire, GPU, crash worker), préserver fichiers et états, réessayer en CPU, afficher diagnostics lisibles.
- Un test matériel doit rester court, non destructif et ne pas bloquer l'UI.

### P1 — Après stabilisation
- Profils de modèles (rapide/équilibré/précis), modèles de PV par commune, export de délibérations séparées, sauvegarde chiffrée, diagnostics administrateur, mises à jour contrôlées par installateur signé.
- La transcription en direct et l'attribution vocale biométrique automatique sont hors périmètre V1.

## 3. Architecture logicielle recommandée
- Python 3.11 (choix initial à valider selon compatibilités exactes), `PySide6` GUI, `sounddevice`/PortAudio pour capture, `faster-whisper`/CTranslate2 ASR, `pyannote.audio` et modèle Community-1 pour diarisation, `llama.cpp` en binaire embarqué appelé par un adaptateur IPC local ou subprocess pour LLM, `sqlite3`, `python-docx` et moteur PDF embarqué éprouvé.
- Séparer `UI` et `core` ; chaque moteur IA dans un **processus worker distinct** ; communication IPC messages JSON avec job_id, états, étapes, erreurs et chemins de résultats ; limiter la mémoire et la concurrence.
- Système de jobs persistants SQLite : `queued`, `running`, `completed`, `failed`, `cancelled`, `interrupted` ; le redémarrage remet les tâches interrompues en attente avec reprise sûre.
- Interfaces Python : `AudioRecorder`, `Transcriber`, `SpeakerDiarizer`, `Summarizer`, `DocumentExporter`, `HardwareProbe`, `EngineRouter`, `JobManager`. Adapter les backends sans toucher à l'UI.
- Versionner chaque modèle et sa configuration dans `models_manifest.json` (fichier, taille, hash SHA256, licence, provenance, version).

## 4. Structure de dépôt
```
ConseilNote/
  README.md
  LICENSES-THIRD-PARTY.md
  pyproject.toml
  requirements.lock
  src/conseilnote/
    main.py
    ui/{dashboard,recording,transcript,minutes,settings}.py
    domain/{session,speaker,segment,agenda,vote}.py
    services/{recording,transcription,diarization,summarization,export,storage,hardware,jobs}.py
    engines/{whisper_adapter,pyannote_adapter,llama_adapter,engine_router}.py
    infrastructure/{database,migrations,logging,paths,ipc}.py
    workers/{asr_worker,diarization_worker,llm_worker}.py
  models/{asr,diarization,llm}/
  runtimes/{llama-cpu,llama-cuda,llama-vulkan,cuda-asr}/
  assets/
  tests/{unit,integration,e2e,fixtures}/
  packaging/{conseilnote.spec,installer.iss,build.ps1,verify-offline.ps1}
  docs/{architecture,privacy,deployment,licenses,operator-guide}.md
```

## 5. Modèle de données
- `municipality(id,name,settings_json)`
- `person(id,display_name,role,active)`
- `session(id,title,date,location,status,created_at,updated_at,agenda_json)`
- `attendance(session_id,person_id,status,proxy_details)`
- `audio_segment(id,session_id,file_path,start_ms,end_ms,sha256,capture_status)`
- `speaker(id,session_id,display_label,person_id_nullable)`
- `utterance(id,session_id,speaker_id,start_ms,end_ms,text,confidence_nullable,source_revision,edited_at)`
- `agenda_item(id,session_id,position,title,notes)`
- `vote(id,agenda_item_id,method,for_count,against_count,abstain_count,nonparticipating_count,status,source,reviewed)`
- `draft_minutes(id,session_id,revision,content_json,validation_status,created_at)`
- `export(id,session_id,draft_revision,format,path,sha256,created_at)`
- `job(id,session_id,type,status,engine,progress,error_code,payload_json,created_at,updated_at)`
- Migrations automatisées, transactionnelles et testées sur anciennes bases.

## 6. Pipeline de traitement
1. Création séance et configuration du microphone, contrôle micro/volume/espace disque.
2. Enregistrement segmenté robuste ; manifest + flush périodique + index audio.
3. Fin séance : assemblage logique audio, normalisation pour IA, sans écraser l'original.
4. Diarisation et transcription ; alignement temporel des segments ; gestion chevauchements et incertitudes.
5. Éditeur : affectation manuelle des intervenants et correction transcription.
6. Extraction par ordre du jour, puis synthèse locale par parties avec preuves/références segments.
7. Contrôles automatiques de cohérence (montants, noms, dates, votes) + champs « à confirmer ».
8. Révision humaine puis export de la version choisie.

## 7. Compatibilité et routage CPU/GPU
- `HardwareProbe` identifie matériel avec APIs Windows et/ou outils locaux, sans réseau, puis effectue un probe réel par moteur.
- Politique initiale : ASR GPU NVIDIA compatible si probe CTranslate2 OK, sinon CPU ; diarisation GPU si PyTorch/CUDA correctement empaqueté et probe OK, sinon CPU ; LLM backend CUDA ou Vulkan si probe OK, sinon CPU.
- Ne pas installer de pilotes NVIDIA dans le Setup. Empaqueter uniquement redistribuables autorisés, DLL compatibles et runtimes effectivement nécessaires.
- Séparer les bibliothèques GPU incompatibles dans processus indépendants ; ne pas mélanger des versions CUDA/cuDNN à l'aveugle.
- Un GPU avec VRAM insuffisante tombe sur CPU ; ne jamais interrompre ni supprimer l'audio.
- Tester sur Windows CPU-only (8 et 16 Go RAM) et au moins un PC NVIDIA ; AMD/Intel GPU seulement si backend réellement validé, sinon CPU.
- Objectifs de performance (à mesurer, non garantis) : aucune perte audible de capture pendant les traitements ; le traitement différé reste possible sur CPU, même lentement ; stockage et estimation de durée affichés honnêtement.

## 8. Emballage et livraison hors ligne
- PyInstaller `--onedir` comme point de départ ; collecter explicitement ressources Qt, runtimes Python, wheels natifs et dépendances worker. `--onefile` PyInstaller n'est pas le livrable final.
- Inno Setup compile un seul `ConseilNote-Setup.exe` à partir du dossier `dist/ConseilNote`, de tous les modèles, binaires CUDA/Vulkan/CPU et ressources autorisés.
- Raccourcis Bureau/menu Démarrer, désinstallation, options dossier des archives, vérification de l'espace disque, conditions/licences tierces accessibles.
- Aucun `pip install`, `git clone`, `winget`, requête Hugging Face ni téléchargement au démarrage ; les téléchargements de modèles sont autorisés uniquement sur **machine de build**, après acceptation des conditions/licences pertinentes.
- Build reproductible avec versions épinglées, hashes, SBOM/manifest ; contrôler antivirus, signatures numériques de code si commercialisation, tests d'installation/mise à jour/désinstallation.
- Les modèles restreints/licences peuvent empêcher une redistribution sans autorisation spécifique : vérifier avant intégration finale ; si non redistribuable, remplacer par solution autorisée au lieu de téléchargement caché chez le client.
- Attention au risque de volume du Setup (> plusieurs Go possibles), à l'espace extrait et aux limites du système de build/installation.

## 9. Exigences de sécurité et conformité
- Conseil municipal : projet de PV, non document officiel avant contrôle et procédure d'adoption. Respecter le contenu requis par le CGCT (notamment les votes et les débats pertinents), paramétrable selon contexte et conseils juridiques.
- Identifier responsable du traitement, base légale, information, sécurité, droits applicables, durée de conservation, diffusion des procès-verbaux et gestion des enregistrements ; accompagner la mairie dans l'analyse RGPD. Ne pas enregistrer à l'insu des personnes.
- Aucune donnée transmise automatiquement au développeur ; support sur demande avec anonymisation ; pas d'authentification à un service cloud.
- Minimisation : ne pas créer d'empreintes vocales biométriques permanentes en V1 ; distinguer les locuteurs sur une séance et attribuer les noms à la main.
- Prendre en compte les droits des tiers au titre des licences de code, modèles et runtimes, et leurs obligations d'attribution / redistribution.

## 10. Plan de développement Codex (phases livrables)

### Phase 0 — Faisabilité, licences et preuve de concept
- Écrire `docs/architecture.md`, matrice des versions compatibles et `docs/licenses.md` ; choisir modèles et vérifier droits de redistribution.
- Test indépendant : transcription sur audio français, diarisation sur voix distinctes, LLM GGUF CPU local, échantillon d'export DOCX/PDF ; microbench CPU/GPU.
- Documenter mesures, tailles, RAM, temps et limites. **Critère de sortie :** pipelines réels fonctionnels hors ligne dans l'environnement de dev.

### Phase 1 — Structure, DB, UI
- Initialiser repo, configuration, SQLite migrations, pages PySide6, UI moderne mais sobre, tests unitaires, logs, erreurs.
- Créer séances et ordre du jour ; sauvegarder/réouvrir. **Critère :** données persistantes après redémarrage.

### Phase 2 — Enregistrement robuste
- Liste micros, VU-mètre, capture segmentée, pause/reprise, import audio et récupération après interruption ; tests de coupure simulée.
- **Critère :** une séance enregistrée reste réécoutable et récupérable après arrêt inattendu.

### Phase 3 — Pipeline ASR + diarisation
- Workers isolés, job manager, diarisation, ASR, alignement temporel, affichage et correction, liaison audio/texte.
- **Critère :** 30 minutes de réunion traitées et éditables en CPU sans réseau ; attribution incertaine visible.

### Phase 4 — Résumé structuré + procès-verbal
- LLM local, JSON Schema, segment citation, regroupement par points de l'ordre du jour, contrôle de cohérence et votes manuels.
- Éditeur PV, exports DOCX/PDF. **Critère :** sur un jeu de test, pas d'invention de résultat de vote ; les champs manquants sont signalés.

### Phase 5 — Détection matériel + backends
- Probes CPU/GPU indépendants, bascules automatiques, tests de panne/VRAM limitée, réglages utilisateur.
- **Critère :** GPU utilisable sélectionné si validé ; sinon CPU sans planter ni perdre de données.

### Phase 6 — Packaging offline
- Réaliser scripts `build.ps1`, `.spec`, `.iss`, manifest modèles, notices des licences ; compiler Setup unique.
- Essais sur VM Windows vierge déconnectée, PC CPU sans Python et PC GPU avec pilotes compatibles.
- **Critère :** du Setup à l'export final, zéro accès Internet et zéro installation manuelle de dépendance.

### Phase 7 — Recette terrain et commercialisation
- Test en salle de conseil municipal avec matériel audio réel, plusieurs positions et paroles simultanées.
- Mesurer qualité (WER, DER), temps de traitement, corrections humaines, ressources, robustesse.
- Écrire guide opérateur, notice RGPD, méthode de sauvegarde, support et mise à jour ; prioriser les corrections.

## 11. Tests d'acceptation indispensables
1. Windows 11 x64 vierge sans Python, sans Internet : le Setup installe tout et réalise un cycle complet en CPU.
2. Windows 10 x64 pris en charge : mêmes tests et prérequis précisément documentés.
3. PC avec NVIDIA compatible : probe GPU et traitement accéléré ; GPU indisponible simulé -> fallback CPU.
4. PC sans GPU : fonctionnement intégral en CPU ; durées sans promesse irréaliste.
5. Coupure enregistrement : les segments déjà validés et la séance sont récupérables.
6. Crash worker diarisation/LLM : audio intact, statut exploitable, reprise possible.
7. Deux locuteurs, trois locuteurs et chevauchements : attribution modifiable ; ne jamais garantir une identification certaine.
8. Transcription française comportant chiffres, noms, votes : correction par l'opérateur possible.
9. Exemple de séance sans vote identifiable : l'IA ne fabrique aucun résultat et demande validation.
10. Mise à niveau du Setup : conserve archives et migrations SQLite correctes ; désinstallation ne supprime pas les archives sans consentement explicite.
11. Audit réseau : aucun appel Internet au démarrage, à l'analyse, à l'export ou à l'installation.
12. Licence/attribution : toutes dépendances et tous modèles redistribués disposent de justifications écrites.

## 12. Instructions impératives à Codex
- Ne jamais simuler les modèles IA ou présenter un écran factice comme une fonction terminée.
- Écrire des tests automatisés et exécuter les vérifications disponibles après chaque phase.
- Bloquer explicitement sur une dépendance non redistribuable, incompatible ou absente ; fournir alternative et preuve.
- Ne pas prétendre que le Setup final fonctionne avant vérification sur un véritable Windows propre, déconnecté.
- Ne pas modifier les enregistrements originaux, attribuer biométriquement un nom sans décision produit/juridique, ni officialiser un PV sans validation humaine.
- Documenter chaque limitation et tenir `docs/progress.md` avec réalisé / restant / tests / risques.

## 13. Prompt initial pour Codex
Tu es un ingénieur logiciel principal Python/Windows. Développe ConseilNote suivant l'intégralité du cahier des charges `ConseilNote_Cahier_des_charges_Codex.md`. Procède phase par phase et ne saute pas les validations. Commence par auditer les dépendances, versions, compatibilités Windows, droits de redistribution des modèles IA, fonctionnement hors ligne et architecture des processus. Crée les documents, prototypes reproductibles et tests de Phase 0 avant l'interface finale. Ensuite mets en place l'ossature du projet et implémente chaque module réel avec tests. La distribution finale doit être un seul Inno Setup `ConseilNote-Setup.exe` qui inclut code, moteurs, bibliothèques et modèles autorisés, sans téléchargement ou installation manuelle au premier lancement. CPU est toujours disponible ; GPU n'est choisi qu'après un test réel par moteur, avec repli CPU. Conserve tous les enregistrements en cas de crash. Le document IA est un brouillon à valider, jamais un PV adopté automatiquement. Ne dis jamais « terminé » sans preuve de test d'installation sur Windows vierge hors ligne. Fais un rapport de progression et signale précisément chaque dépendance bloquante.
