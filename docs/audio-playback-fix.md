# Lecture des citations — correctif du 21 octobre 2026

## Cause et chemin d’exécution

**Écouter la citation sélectionnée** → `RegistryPage.listen()` dans
`ui/information_registry.py` → recherche du passage dans **l’instantané du
registre** → `MainWindow.play_registry_snapshot()` dans `ui/window.py` →
`source_json.normalized_audio`, `start_ms`, `end_ms` → lecteur Qt.
L’écoute reste attachée à la source historique après correction de la
transcription courante. **Transcription et voix** passe par `play_selected()`
ou `play_utterance()`, puis par la même fonction de lecture.

Fichier réellement chargé :

```
output/gpu-integration-20261021/e1434b50c08946f78e574f9056b6d11b/municipal-app/application-data/sessions/6516fdd4-2d60-4189-b7be-b4e9cd4bba6d/jobs/b56feefe-dfa9-45ed-bd49-eeba7eac607e/normalized.wav
```

WAV valide : RIFF/WAVE PCM signé 16 bits little endian, **1 canal / mono,
16 000 Hz**, 5 376 627 échantillons, **336,0391875 s**. Son en-tête PCM
classique déclare un canal, sans masque surround WAVEFORMATEXTENSIBLE.
SHA-256 : `9ca9933350c0b0e57f50347d49b58b7f7f9ae33b3e174cc6f99e593cebb59da2`.

Sortie Windows par défaut : **Haut-parleurs (Logitech PRO X Gaming Headset)**,
format préféré Qt **48 000 Hz, 8 canaux, Surround7Dot1, Float**.
Le backend **FFmpeg de Qt 6.8.3** produit **48 lignes SWR en trois secondes**,
dont l’erreur de disposition **de sortie** vide. Sa position avance pourtant
sans signal `errorOccurred` : le compteur seul ne prouvait pas la production
de son. L’échec est localisé à la conversion de sortie Qt/FFmpeg sur ce
périphérique 7.1, sans corruption du fichier source. Le détail interne du
défaut de correspondance des canaux Qt n’a pas été établi par débogage natif.

**Windows Media Foundation** lit le même fichier sans erreur SWR. Qt documente
ce changement en cas de problème avec FFmpeg :
[Qt 6.8, Changing backends](https://doc.qt.io/qt-6.8/qtmultimedia-index.html#changing-backends).
Ce choix cible **PySide6 6.8.3 épinglé** ; requalifier après mise à niveau Qt,
les backends natifs ayant un support limité.

Autre défaut établi : l’ancien lecteur cherchait le début dans le WAV entier
mais **n’appliquait jamais la fin du passage**.

## Correction

- `QT_MEDIA_BACKEND=windows` avant initialisation QtMultimedia, dans le seul
  processus GUI ; aucun changement persistant des paramètres Windows.
- Un `LocalPlayback`, un `QMediaPlayer` et un `QAudioOutput` pour tous les
  boutons. Sortie Windows par défaut explicitement sélectionnée à chaque écoute.
- Copie temporaire **PCM16 mono ou stéréo**, avec fréquence et nombre de canaux
  déclarés. Copie des octets, sans gain, rééchantillonnage ou silence ajouté.
- Intervalle `[début, fin)` : indices `ms × fréquence // 1000`. À 16 kHz,
  bornes exactes ; à 44,1 kHz, arrondi vers le bas inférieur à un échantillon.
  Aucun horaire enregistré ne change. Durées nulles, fichier tronqué et bornes
  hors audio sont refusés, sans ajustement silencieux.
- Le fichier lu finit à la fin du passage : aucune coupure dépendante d’un
  minuteur UI. Progression affichée dans le repère temporel de la séance.
- Arrêt, nouvelle lecture, changement de séance, début d’enregistrement,
  fermeture des dialogues de sources et de la fenêtre libèrent le lecteur.
  Un seul nom temporaire réutilisé et supprimé après lecture ; aucun lecteur
  ni sous-processus supplémentaire par clic.
- Erreurs françaises avec action corrective, arrêt et source vidée. Aucun
  nouvel essai automatique. Garde de cinq secondes pour chargement bloqué /
  absence de progression, suspendue pendant une pause volontaire.
- Plugin `windowsmediaplugin.dll` exigé explicitement par le spec PyInstaller.
  **Pas de recompilation du bundle pour ce correctif.**

L’écoute correspond au **passage source associé**, pas à un découpage lexical
inventé de la citation. Les données de transcription, registre, citations et
annotations ne sont jamais réécrites par le lecteur.

## Fichiers de ce lot

| Fichier | Rôle |
| --- | --- |
| `src/notetaker/infrastructure/media.py` | Choix du backend Windows |
| `src/notetaker/main.py` | Configuration avant imports Qt |
| `src/notetaker/services/playback_audio.py` | Copie PCM bornée |
| `src/notetaker/ui/playback.py` | Lecteur unique, nettoyage, erreurs et garde |
| `src/notetaker/ui/window.py` | Branchement commun des parcours |
| `packaging/notetaker.spec` | Plugin Windows obligatoire |
| `tests/test_playback.py` | 17 cas de non-régression |
| `scripts/probe_qt_playback.py` | Reproduction bornée FFmpeg / Windows |
| `scripts/validate_audio_playback.py` | Recette sur sauvegarde SQLite |
| `scripts/windows_audio_meter.py` | Mesure Core Audio du processus de recette |
| `docs/audio-playback-fix.md`, `docs/operator-guide.md`, `docs/progress.md` | Rapport et utilisation |

Les modifications antérieures du registre et des moteurs présentes dans le
répertoire de travail ont été conservées ; ce lot ne modifie pas ces moteurs.

## Tests réellement exécutés

Preuves : `output/playback-fix-20261021/758d8f8a825a450996c9b9eaed7f23e3/`.

- Reproduction isolée : `ffmpeg.json`, `ffmpeg.stderr.log`, `windows.json`,
  `windows.stderr.log`. **48 lignes SWR / zéro**. Aucun filtre de journaux.
- **347 tests réussis en 11,41 s**, dont **17 nouveaux**, `final.xml` et
  `final.log`. Mono 16 kHz, stéréo 48 kHz, PCM 44,1 kHz, correspondance des
  octets et en-têtes, originaux identiques, bornes invalides, corruption,
  formats refusés, absence de sortie, erreur synchrone d’initialisation,
  garde, pause/reprise, fin, suppression du temporaire, aperçu intégral après
  extrait, deux parcours UI et instantanés historiques.
  Les tests unitaires du transport emploient un faux lecteur explicitement ;
  les recettes ci-dessous utilisent le vrai lecteur Windows.
- `real-windows-02/result.json` : deux boutons Qt, passage `s0-0`,
  **00:00.000–00:02.240**, signal Core Audio du processus non nul, arrêt final
  et suppression du temporaire dans les deux parcours.
- `real-windows-03/result.json` : passage `s10-0`,
  **00:55.240–00:59.340**, PCM temporaire identique octet pour octet à l’extrait
  source, sur une **sauvegarde indépendante** de la base municipale.

| Parcours | Temps avec chargement | Mesures non nulles | Pic Core Audio du processus | Fin / temporaire supprimé |
| --- | ---: | ---: | ---: | --- |
| Citation du registre | 4,235 s | 77 | 0,08702685 | Oui / oui |
| Transcription et voix | 4,250 s | 78 | 0,08702523 | Oui / oui |

Positions finales : **59 340 ms** ; aucun échantillon du passage suivant n’est
dans le fichier lu. Quatre remplacements rapides puis arrêt : zéro WAV
temporaire restant. Copie stéréo PCM16 d’une seconde dérivée du municipal :
pic **0,08703017**, arrêt normal. Journaux stderr des recettes réussies **vides**.
Captures `registry.png` / `transcription.png` conservées et registre inspecté.

Répétition finale avec les deux onglets explicitement affichés :
`real-windows-04/result.json`, **4,265 / 4,281 s**, pics **0,08703585 /
0,08703442**, 77 mesures non nulles par parcours, mêmes horaires et arrêts.
Stéréo, remplacements, temporaires et conservation de nouveau vérifiés,
stderr vide. Capture de l’onglet Transcription inspectée. Le temporaire de
l’essai interrompu a été supprimé une fois libéré ; aucun dossier temporaire
de lecteur ne reste dans le répertoire de cette recette.

`preservation-before.json` / `preservation-after.json` : base de recette,
WAV source et bases humaines BFMTV contrôlées (`reference-humaine.sqlite`,
`decoupages-wer.sqlite`) identiques par SHA-256. Aucun modèle lancé ou téléchargé.
Aucun accès Python au réseau détecté ; le lecteur ne dépend d’aucun service.

Core Audio mesure **les sessions du PID NoteTaker**, pas le niveau général
d’une autre application. C’est une preuve de signal numérique vers la sortie
Windows, au-delà du compteur de lecture. **Audibilité physique / qualité au
casque non certifiées par une écoute humaine.** Autres périphériques et PC
Windows vierge non qualifiés ici.

Premier essai instrumenté conservé comme échec dans `real-windows-01.stderr.log` :
le bac à sable refusait l’accès de mesure Core Audio (`80070005`). L’essai
a interrompu la mesure et laissé un temporaire verrouillé jusqu’à la sortie
du processus. Les recettes suivantes ont été autorisées hors bac à sable,
avec lecture et nettoyage vérifiés. Cet échec n’est pas compté comme réussite.

## Utilisation

Fermer puis relancer la recette **depuis les sources**, par son
`Ouvrir-la-recette.cmd` habituel. Le backend est choisi au démarrage ; une
fenêtre déjà ouverte garde l’ancien. Un ancien EXE ne reçoit pas les sources.

Registre : sélectionner une information puis, au besoin, une ligne de citation
dans **Sources et contexte**, cliquer **Écouter la citation sélectionnée**.
**Transcription et voix** : sélectionner une ligne, **Écouter le passage**, ou
double-cliquer la ligne. Arrêt automatique à la fin du passage.
L’onglet Audio propose **Lecture / pause** et **Arrêter la lecture**.
En cas d’échec : vérifier sortie/volume Windows, puis sélectionner à nouveau
le passage. Une source absente ou des horaires invalides sont signalés ;
aucune réanalyse automatique ne remplace les corrections pour autoriser l’écoute.
