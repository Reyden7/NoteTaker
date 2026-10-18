# Avancement de NoteTaker 0.1

16 octobre 2026 — **chaîne CPU utilisable en développement ; produit commercial non qualifié**.
Les quatre documents demandés ont été relus. À la demande de l’utilisateur,
l’interface et le parcours complet ont été développés sans attendre un fichier
terrain. Les essais naturels français à trois voix restent **non validés**.
L’état initial est conservé dans `history/progress-phase0.md`.

## Fonctionne et a été implémenté

| Fonction | État actuel |
|---|---|
| Séances | Création, titre, commune, date, lieu, participants/présences en texte, ordre du jour et notes |
| Historique | Recherche, archivage/réactivation et réouverture SQLite |
| Interface | PySide6 6.8.3, cinq onglets, traitements en arrière-plan, annulation et messages en français |
| Microphone | Sélection, préférence WASAPI, niveau, durée, pause/reprise et arrêt |
| Sauvegarde audio | PCM16 segmenté toutes les 60 s ; flush/fsync et journal atomique environ chaque seconde ; hashes des segments clos et du préfixe actif |
| Récupération | Prises interrompues détectées à la réouverture ; trames existantes récupérables sans réécrire les originaux |
| Import | Copies vérifiées SHA-256 de WAV, MP3 et M4A ; normalisation dérivée mono 16 kHz |
| Choix des prises | Inclusion/exclusion sans supprimer les prises brutes |
| ASR | faster-whisper CPU int8 réel, VAD Silero local, horodatages, recherche, corrections autosauvegardées et écoute du passage |
| Voix | sherpa-onnx CPU, attribution manuelle des noms, confirmation, scission de passages et fusion de voix |
| Incertitude | Faible couverture/plusieurs voix signalées ; masque de chevauchement possible implémenté mais qualité terrain non validée |
| Qwen3 | llama.cpp CPU réel ; sélection JSON d’identifiants de sources par ordre du jour sur portions bornées |
| Projet de PV | Extraits sourcés éditables, points, titres, références, décisions manuelles et votes structurés |
| Relecture | Nom et confirmation explicite ; empreinte du contenu et du contexte, invalidée après modification pertinente |
| Exports | DOCX/PDF réels, projet non officiel, copies et instantanés conservés distinctement des brouillons |
| Isolation | Workers distincts, délais, annulation et Job Objects Windows pour fermer l’arbre de processus ; capture indépendante |
| Distribution de travail | Dossier PyInstaller autonome avec modèles et moteur CPU ; stratégie Inno préparée |

Le brouillon est **extractif** : Qwen choisit les identifiants des passages ;
l’application reprend leurs textes et les noms corrigés. Le modèle ne peut
ajouter de texte libre ou de comptes de votes. Les passages relatifs aux votes
sont réservés à la vérification et à la saisie structurée. Une synthèse narrative
libre du débat reste à qualifier. Les votes exportés proviennent exclusivement
des quatre nombres et de la source saisis par l’opérateur.

## Tests réellement exécutés

**50 tests automatisés réussis, aucun ignoré sur ce Windows.** Rapport JUnit :
`docs/evidence/pytest-workflow.xml`.

- Migration de la base phase 0 vers le schéma 3, rollback, backup SQLite,
  réouverture, historique et archivage.
- Journal PCM, rotation, véritable arrêt forcé de processus, récupération du
  fichier actif, erreur de manifeste et détection de fichier altéré.
- Import préservant les originaux et normalisation stéréo 48 kHz → mono 16 kHz.
- Attribution incertaine, corrections, fusion et scission ; découpage des
  transcriptions longues sans perte de caractères/références.
- Rejet de votes incomplets et de votes inconnus chiffrés ; absence de résultat
  créé par le LLM ; export refusé avant relecture et après modification.
- Parcours Qt de création, sauvegarde, archivage, réouverture, confirmation
  refusée/acceptée et export depuis les widgets.
- Panne de diarisation injectée : ASR conservé, original inchangé, job en échec.
  Annulation et fermeture réelle de descendants via Job Object Windows.

Les tests de fautes injectées sont identifiés comme tels et ne remplacent pas
les inférences réelles ci-dessous.

### Chaîne réelle sur la fixture existante

`scripts/validate_chain.py` a exécuté import → Whisper → sherpa et masque
d’incertitude → Qwen → brouillon → refus d’export non relu → test de la barrière
d’export sur données fictives → DOCX/PDF → réouverture. Pour l’audio synthétique
existant de 13,59 s : dernière analyse 8,993 s, Qwen 11,315 s, quatre passages et
une voix. Original inchangé. Preuve : `docs/evidence/application-chain.json`.

La confirmation du test est étiquetée **AUTOMATED TEST — NOT A HUMAN REVIEW**
dans un dossier isolé. Elle ne constitue pas une relecture d’une vraie séance.
L’interface ne confirme jamais automatiquement une révision utilisateur.

Les PDF et DOCX issus de la chaîne ont été rendus avec Poppler et Word en
lecture seule, puis inspectés : une page chacun, sources, décisions et comptes
fictifs lisibles. Word n’est pas une dépendance du produit. Les widgets réels
ont été inspectés avec le moteur Windows de Qt ; le rendu offscreen ne chargeait
pas correctement les polices de ce poste.

### Microphone et formats

- Logitech PRO X Gaming Headset, WASAPI, mono 48 kHz : **141 312 trames, 2,944 s**,
  aucun incident signalé, conversion WAV réussie. Ce contrôle ne juge pas la parole.
  Preuve : `docs/evidence/microphone-validation.json`.
- WAV, MP3 et M4A réellement importés/décodés depuis un encodage de la fixture :
  13,590 / 13,590 / 13,632 s, sources inchangées. Preuve :
  `docs/evidence/codec-validation.json`. Tous les codecs possibles de ces conteneurs
  ne sont pas pour autant qualifiés.

### Exécutables autonomes

PyInstaller 6.16.0 produit `dist/NoteTaker` : `NoteTaker.exe`,
`NoteTaker-worker.exe`, `_internal`, modèles et llama CPU. Volume mesuré environ
**3,53 Go décimaux** avant compression d’installateur. Les trois workers compilés
ont réussi ASR, sherpa et Qwen avec PYTHONPATH retiré et PATH limité à System32.
Preuve : `docs/evidence/bundle-validation.json`. Le poste possède déjà des runtimes
système et n’était pas déconnecté : ce n’est pas la recette Windows vierge.

L’interface compilée a ouvert une fenêtre Windows réactive, initialisé une base
isolée et accepté une fermeture normale (WM_CLOSE), code de sortie 0. Preuve :
`docs/evidence/desktop-validation.json`, avec hash de l’exécutable testé. Ce
contrôle de démarrage ne remplace pas un parcours complet de réunion dans le
bundle ni les essais des widgets effectués séparément depuis les sources.

Le premier worker compilé échouait dans `pkg_resources` faute de
`backports.tarfile`. Dépendance ajoutée, verrouillée, collectée explicitement ;
les essais compilés suivants réussissent. Le dossier reste marqué development_only.
Le script Inno est un scaffold non compilé et la publication commerciale est bloquée.

## Non validé ou restant

| Point | État |
|---|---|
| Réunion naturelle française 10–20 min, ≥3 voix | **NON VALIDÉ** — aucun fichier disponible |
| Chevauchements réels, bruit, voix proches et interruptions | **NON VALIDÉ** — indicateur implémenté, qualité inconnue |
| WER/DER et coût de correction terrain | Non mesurés |
| Capture continue de 10–20 min et plusieurs heures | Procédure fournie, essai microphone court seulement |
| Coupure électrique et panne de stockage | Non qualifiées ; crash de processus et erreurs d’écriture testés |
| GPU | Non qualifié ; Whisper a échoué sans cuDNN en phase 0, UI 0.1 en CPU |
| Windows 10, 8/16 Go RAM et Windows vierge déconnecté | **NON VALIDÉ** — développement sur Windows 11, environ 32 Go RAM |
| Audit réseau système | Non effectué ; sockets Python gardées et chemins locaux, sockets natives non capturées |
| Synthèse narrative libre et délibérations complètes | À développer/qualifier ; brouillon actuel par extraits |
| Présences/procurations normalisées et votes avancés | Texte et votes de base disponibles ; métier détaillé à compléter |
| Sauvegarde/restauration produit et chiffrement | Backup SQLite initial et copie du dossier fermé ; assistant portable à développer |
| Limites mémoire matérielles | Traitements séquentiels, budgets imposés non qualifiés |
| Setup unique signé | Non produit ; script Inno non compilé, essais d’installation/mise à jour/désinstallation à réaliser |
| Redistribution finale | Qt, codecs, VC++, notices et signature du lot exact encore à approuver |

La phase 0 reste ouverte ; les phases UI/audio/pipeline/édition disposent d’une
première chaîne fonctionnelle, sans recette complète de toutes les exigences.
Le produit ne doit pas être déclaré terminé avant la qualification Windows
propre déconnecté. La prochaine recette est décrite dans `operator-guide.md`
et `field-test.md`.
