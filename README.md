# NoteTaker

Application Windows locale de transcription et de préparation des procès-verbaux
municipaux. **Version de développement 0.1 : chaîne CPU implémentée, qualification
commerciale non terminée.** Aucun `NoteTaker-Setup.exe` approuvé n'est disponible.

## Utiliser la version de travail

Sur cette machine, lancer `dist\NoteTaker\NoteTaker.exe`. Conserver tout le
dossier `dist\NoteTaker` : exécutables, `_internal`, modèles et runtimes.
Aucun téléchargement n'est prévu au lancement. Ce dossier est généré et exclu de Git.

Le [guide opérateur](docs/operator-guide.md) décrit la création d'une séance,
le microphone, les imports **WAV/MP3/M4A**, les corrections et les exports.
Les données sont conservées dans `%LOCALAPPDATA%\NoteTaker` par défaut.

Le parcours comprend l'enregistrement avec journal et récupération, Whisper,
sherpa-onnx, les noms corrigés manuellement, un brouillon Qwen3 sourcé, l'édition,
la saisie des décisions/votes et l'export PDF/DOCX après confirmation humaine.
Le brouillon actuel reprend des extraits : Qwen classe les références des
passages ; les résultats de vote sont exclusivement saisis par l'opérateur.

## Développer et vérifier

Python 3.11 x64 et uv sont nécessaires sur la machine de build. L'installation
des dépendances et l'acquisition explicite des modèles nécessitent Internet
uniquement pendant la préparation du build.

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.tools\python'
uv python install 3.11.16
uv venv --python 3.11.16 .venv
uv pip sync --python .venv\Scripts\python.exe --require-hashes requirements.lock
$env:PYTHONPATH = Join-Path $PWD 'src'
.venv\Scripts\python.exe -m pytest --basetemp=.cache/pytest-local --junitxml=docs/evidence/pytest-workflow.xml
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\run.ps1
```

Modèles et moteur CPU présents sur ce poste, vérifiables par :

```powershell
.venv\Scripts\python.exe -m notetaker.main verify-models
```

Les acquisitions explicites restent dans `scripts/acquire_phase0.py` et
`scripts/acquire_diarization_alternative.py`. Elles ne sont jamais appelées par
l'application. Les révisions et hashes sont dans les deux manifestes de modèles.
L'ancien environnement PyTorch n'est pas nécessaire au produit sherpa CPU.

## État des validations

**50 tests automatisés réussis.** Chaîne réelle des trois moteurs sur fixture
synthétique, capture microphone courte et imports des trois formats exécutés.
Les workers du bundle PyInstaller ont également exécuté les trois moteurs.
Les rapports et limites sont dans [docs/progress.md](docs/progress.md).

**Non validés :** réunion naturelle française de 10–20 minutes à au moins trois
voix, chevauchements réels, capture longue, GPU et Windows vierge déconnecté.
La [procédure terrain](docs/field-test.md) permet d'enregistrer ou d'importer
la réunion dès qu'elle est disponible. Ces absences ne sont pas assimilées à
des tests réussis.

## Architecture et livraison

- [Architecture actuelle](docs/architecture.md)
- [Versions et compatibilité](docs/compatibility.md)
- [Licences et réserves de redistribution](docs/licenses.md)
- [Diarisation sherpa et limites](docs/diarization-alternative.md)
- [Reproduction des validations](docs/testing.md)
- [Build PyInstaller et stratégie Inno Setup](packaging/README.md)

Le lot de développement représente environ 3,53 Go avant compression. Les
notices natives, runtimes, signature et recette propre hors ligne restent à
qualifier avant le livrable commercial unique `NoteTaker-Setup.exe`.
L'état de phase 0 antérieur est conservé dans `docs/history`.
