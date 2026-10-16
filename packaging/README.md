# Packaging Windows — version de travail 0.1

Objectif de livraison : **un seul `NoteTaker-Setup.exe`**, incluant modèles,
dépendances et runtimes redistribuables, sans Python préinstallé ni acquisition
pendant l'installation ou le premier lancement. Ce livrable n'est pas encore validé.

## Réalisé

`notetaker.spec` produit un dossier PyInstaller avec deux exécutables partageant
les bibliothèques : interface `NoteTaker.exe` et `NoteTaker-worker.exe`. Les
modèles et llama CPU sont des ressources locales distinctes dans ce dossier.
Les DLL Qt restent remplaçables ; cela ne suffit pas à prouver la conformité LGPL.
PyTorch, les modules Qt WebEngine/QML/Quick et la DLL PortAudio ASIO sont exclus.

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
   QtMultimedia/FFmpeg et le droit de redistribution Visual C++.
3. Inclure le redistribuable Visual C++ autorisé et vérifier son installation
   silencieuse hors ligne. Qualifier les droits d'utilisation d'Inno retenu.
4. Ajouter et qualifier chaque backend GPU séparément, avec repli CPU après
   DLL absente, mémoire insuffisante, crash ou délai dépassé. Aucun lot NVIDIA
   n'est livré dans la version CPU actuelle.
5. Signer exécutables, installateur et désinstallateur avec le certificat du
   titulaire ; mesurer taille, espace temporaire et espace final.

La compilation commerciale reste bloquée dans `build.ps1`. Ce blocage décrit
l'état réel du lot, pas une impossibilité technique de créer un installateur.

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
