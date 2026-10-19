# Packaging Windows — version de travail 0.2.3

Nouveau dossier : **`dist/topic-summary/NoteTaker`**, rédaction par sujet,
longueurs et lexique local. Bilan : `docs/topic-summary-0.2.3.md`. Les rapports
réels sont `bundle-topic-summary.json`, `desktop-topic-summary.json` et
`native-payload-topic-summary.json` dans `docs/evidence` ; consulter leur état,
les refus initiaux sont conservés séparément. Aucun nouveau modèle ou paquet.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build.ps1 -Development -SkipModels -DistributionDirectory dist/topic-summary
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\attach-dev-assets.ps1 -BundleDirectory dist/topic-summary/NoteTaker
.venv\Scripts\python.exe scripts\validate_bundle.py --bundle dist/topic-summary/NoteTaker --report docs/evidence/bundle-topic-summary.json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_desktop.ps1 -BundleDirectory dist/topic-summary/NoteTaker -ReportFile docs/evidence/desktop-topic-summary.json
```

Pour reconstruire ce dossier existant, `rebuild-dev.ps1 -DistributionDirectory
dist/topic-summary` archive ses binaires et préserve les modèles. Les modèles
et dépendances de build partagés par liens physiques doivent rester immuables.
Les schémas SQLite restent v4 ; les nouveaux points JSON ajoutent des liaisons
de phrases facultatives. Utiliser 0.2.3 pour ouvrir/valider ces nouveaux documents.
Les anciens brouillons restent lisibles et soumis aux mêmes contrôles humains.

L'environnement de validation reste ce PC de développement, avec runtimes
système préexistants. Le Setup commercial et Windows vierge déconnecté ne sont
pas validés ; les réserves de redistribution du payload natif restent ouvertes.

## Lot précédent 0.2.2

Lot conservé : **`dist/validation-fixes/NoteTaker`**, corrections humaines
et références de brouillon. Les contrôles sont `bundle-validation-fixes.json`,
`desktop-validation-fixes.json` et `native-payload-validation-fixes.json` dans
`docs/evidence`. Le lot précédent `dist/directory-01/NoteTaker` est conservé.
Build de cette étape (dossier cible inexistant) :

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\build.ps1 -Development -SkipModels -DistributionDirectory dist/validation-fixes
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\attach-dev-assets.ps1 -BundleDirectory dist/validation-fixes/NoteTaker
.venv\Scripts\python.exe scripts\validate_bundle.py --bundle dist/validation-fixes/NoteTaker --report docs/evidence/bundle-validation-fixes.json
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate_desktop.ps1 -BundleDirectory dist/validation-fixes/NoteTaker -ReportFile docs/evidence/desktop-validation-fixes.json
```

La migration v4 est compatible avec les séances existantes après sauvegarde ;
les anciens exécutables refusent une base v4. Bilan : `docs/directory-stage1.md`.
Ce lot n'ajoute ni modèle ni dépendance. Le schéma reste v4. Bilan des correctifs :
`docs/validation-fixes-0.2.2.md`. Le dossier complet reste nécessaire.
`attach-dev-assets.ps1` vérifie hashes/tailles avant et après création de liens
physiques NTFS vers les assets locaux immuables. C'est une économie de disque
pour le build de développement uniquement. Les fichiers du dossier complet sont
autonomes et copiables ; aucun téléchargement ni chemin de modèle externe n'est
nécessaire à son exécution. Le build habituel sans `-SkipModels` copie les poids.

Objectif de livraison : **un seul `NoteTaker-Setup.exe`**, incluant modèles,
dépendances et runtimes redistribuables, sans Python préinstallé ni acquisition
pendant l'installation ou le premier lancement. Ce livrable n'est pas encore validé.

## Réalisé

`notetaker.spec` produit un dossier PyInstaller avec deux exécutables partageant
les bibliothèques : interface `NoteTaker.exe` et `NoteTaker-worker.exe`. Les
modèles et llama CPU sont des ressources locales distinctes dans ce dossier.
Les DLL Qt restent remplaçables ; cela ne suffit pas à prouver la conformité LGPL.
PyTorch, les modules Python Qt WebEngine/QML/Quick, Qt Virtual Keyboard et la
DLL PortAudio ASIO sont exclus. Des DLL natives Qt QML/Quick restent collectées
par les hooks ; l'inventaire réel, plutôt que les seuls imports Python, fait foi.

Les trois workers compilés ont exécuté Whisper, sherpa et Qwen sur ce PC avec
PATH limité à System32 et sans PYTHONPATH. Volume brut mesuré : environ **3,53 Go**.
Rapport : `docs/evidence/bundle-validation.json`. Ce PC possède déjà des runtimes
système et n'était pas déconnecté. Aucun résultat de VM propre n'est revendiqué.

## Construire le dossier de développement

Avec l'environnement verrouillé et les modèles vérifiés :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging\build.ps1 -Development
.venv\Scripts\python.exe scripts\validate_bundle.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\validate_desktop.ps1
```

Le script exige que `dist\NoteTaker` n'existe pas. Pour reconstruire un dossier
de travail déjà présent, `packaging\rebuild-dev.ps1` préserve les anciens binaires
dans `dist\dev-previous-<identifiant>`, reconstruit puis transfère les modèles
existants sans les télécharger à nouveau. Il vérifie les chemins et marque
le résultat `development_only` dans `BUILD-STATUS.json`.

Le build exécute les tests avant PyInstaller. Les logs sont dans
`build-pyinstaller.log` et `build-pyinstaller-stderr.log`. Ne distribuer aucun
dossier `output` ni archive de séances avec le programme.

Le dossier de recette 0.2 est séparé du bundle 0.1 conservé :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging\rebuild-dev.ps1 -DistributionDirectory dist\quality-02
.venv\Scripts\python.exe scripts\validate_bundle.py --bundle dist/quality-02/NoteTaker --report docs/evidence/bundle-quality02.json
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\validate_desktop.ps1 -BundleDirectory dist\quality-02\NoteTaker -ReportFile docs\evidence\desktop-quality02.json
```

Il contient les poids WeSpeaker adaptés par métadonnées et les polices Noto
Sans, Whisper small et Qwen3-4B-Instruct-2507 Q4_K_M. Les anciens poids Qwen
restent hors de ce nouveau payload. Ces contrôles CPU et de démarrage sur le
poste de développement ne constituent pas une acceptation de qualité du débat
ni une validation de redistribution commerciale.

## Bundle de travail du registre 0.2.4

Le lot compilé est `dist/information-registry/NoteTaker`. Il comprend le nouvel
onglet, la migration SQLite v5, les modèles vérifiés et le runtime CPU local.
Pour cet essai, les poids joints utilisent des liens NTFS immuables vers les
poids locaux ; ne jamais les modifier en place. Ce dossier n'est pas un Setup.
Le lanceur privé `output/information-registry/field-670/Ouvrir-NoteTaker.cmd`
ouvre uniquement la copie de recette, avec `--data-dir`, et garde les séances
originales séparées. Les fichiers de recette ne font pas partie du logiciel
à redistribuer.

La compilation exécute la suite avant PyInstaller. Les preuves actuelles sont
`docs/evidence/information-registry-release.json` (égalité des modules des
deux exécutables et des sources), `desktop-information-registry.json`
(démarrage/fermeture) et `information-registry-native-request.json` (contrôle
Qwen CPU réel d'une fiche avec le worker compilé). La transcription et la
diarisation ne sont pas recalculées dans ce lot. Les limites de redistribution
native et la recette sur Windows vierge déconnecté restent ouvertes.

## Stratégie Inno Setup préparée

`installer.iss` est un **scaffold non compilé**, avec blocage explicite tant que
la release n'est pas approuvée. Il prévoit Windows x64, Program Files, raccourci,
désinstallation du programme et conservation des données dans LocalAppData.
Il ne contient aucune directive de téléchargement.

Inno impose plusieurs fichiers si les données compressées dépassent
4 200 000 000 octets. Avec la contrainte du fichier unique, conserver
`DiskSpanning=no`, mesurer le lot exact et refuser la release si cette limite
est dépassée. Le volume brut actuel n'est pas une mesure de Setup compressé.
Source : [documentation officielle DiskSpanning](https://jrsoftware.org/ishelp/topic_setup_diskspanning.htm).

Avant compilation de l'installateur :

1. Figer le lot CPU et les hashes de tous les fichiers, constituer le SBOM et
   les notices/sources requises pour Qt, FFmpeg, Python et les DLL transitives.
2. Résoudre les réserves de `docs/licenses.md`, notamment PyAV/FFmpeg,
   QtMultimedia/FFmpeg, le frontal cuDNN importé par CTranslate2 même sur CPU,
   et le droit de redistribution Visual C++.
3. Inclure le redistribuable Visual C++ autorisé et vérifier son installation
   silencieuse hors ligne. Qualifier les droits d'utilisation d'Inno retenu.
4. Ajouter et qualifier chaque backend GPU séparément, avec repli CPU après
   DLL absente, mémoire insuffisante, crash ou délai dépassé. Aucun lot NVIDIA
   complet n'est livré dans la version CPU actuelle, mais le frontal cuDNN
   de la roue est bien présent ; sa présence bloque l'approbation de ce lot
   pour la cible CPU générale. La variante CPU seule compilée à part doit
   réussir ses recettes avant de remplacer cette roue.
5. Signer exécutables, installateur et désinstallateur avec le certificat du
   titulaire ; mesurer taille, espace temporaire et espace final.

La compilation commerciale reste bloquée dans `build.ps1`. Ce blocage décrit
l'état réel du lot, pas une impossibilité technique de créer un installateur.

L'inventaire final `docs/evidence/native-payload-quality02.json` compte 292
fichiers PE, sans ASIO ni Virtual Keyboard ; le test compilé refuse ces deux
composants optionnels. La suppression de Virtual Keyboard est motivée par sa
licence GPL/commerciale seulement. Les DLL Qt restantes ont encore leurs
obligations propres à documenter. Le nouveau runtime CPU isolé n'est pas livré
par le simple fait que sa compilation ait réussi.

## Recette requise sur Windows propre déconnecté

Utiliser des snapshots Windows 10 22H2 et Windows 11 x64 sans Python, Word,
FFmpeg ni outils de développement. Copier le Setup et un corpus autorisé puis
couper le réseau de la VM avant l'installation. Vérifier :

- installation depuis le seul fichier, sans autre accès réseau ; chemins Unicode
  et compte utilisateur standard après installation ;
- premier lancement, microphone choisi, import WAV/MP3/M4A, chaîne complète CPU,
  écoute, corrections, noms, décisions et votes inconnus/connus ;
- refus d'export avant confirmation, nouvelle relecture après modification,
  ouverture des PDF/DOCX sur un poste de contrôle ;
- arrêt forcé pendant capture et pendant chaque moteur, reprise des séances,
  comparaison des hashes des originaux ; tests de manque d'espace ;
- mise à jour, migrations, sauvegarde/restauration et désinstallation conservant
  les séances ;
- observation des tentatives réseau système, y compris des bibliothèques natives ;
- mesure RAM/CPU sur 8 et 16 Go, longues réunions et GPU qualifiés séparément.

Conserver pour chaque recette : version Windows, matériel, état du réseau,
versions/hashes du lot et du Setup, étapes, résultats et incidents. Les essais
français naturels et chevauchements restent **non validés** jusqu'à la recette
documentée dans `docs/field-test.md`. Aucun test de PC vierge n'a encore été exécuté.
