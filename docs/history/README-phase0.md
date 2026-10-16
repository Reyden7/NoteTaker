# NoteTaker

Application Windows locale de préparation des procès-verbaux municipaux.
**État : phase 0 en cours, critère de sortie non atteint. Aucun installateur commercial disponible.**

Le cahier des charges ConseilNote a été lu intégralement. Le nom produit retenu
par la demande est NoteTaker et le livrable futur sera `NoteTaker-Setup.exe`.
Voir [le bilan réel](docs/progress.md), [la faisabilité](docs/feasibility.md),
[l'architecture](docs/architecture.md), [les versions](docs/compatibility.md)
et [l'audit des licences](docs/licenses.md).

## Reproduire les tests de développement

Les commandes d'acquisition et d'installation ci-dessous concernent uniquement
la machine de développement connectée. Elles ne font pas partie du logiciel livré.
Python 3.11 x64 et uv sont nécessaires pour développer, puis seront embarqués au packaging.

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.cache\uv'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $PWD '.tools\python'
uv python install 3.11.16
uv venv --python 3.11.16 .venv
uv pip sync --python .venv\Scripts\python.exe --require-hashes requirements.lock
.venv\Scripts\python.exe -m pytest --basetemp=.cache/pytest-local --junitxml=docs/evidence/pytest.xml
```

Les tests de fondation n'ont besoin ni de modèles ni de GPU, ni d'accès réseau.
Ils génèrent des données fictives explicites, provoquent un véritable arrêt de
processus et relisent des fichiers DOCX/PDF réels.

## Sondes IA réelles

```powershell
.venv\Scripts\python.exe scripts\acquire_phase0.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\create_speech_fixture.ps1
.venv\Scripts\python.exe scripts\run_phase0_probes.py
$env:PYTHONPATH = Join-Path $PWD 'src'
.venv\Scripts\python.exe -m notetaker.main verify-models
```

L'acquisition est explicite, limitée aux révisions publiques déjà auditées,
et vérifie les gros fichiers contre les SHA-256 amont. Elle consomme environ
3 Go pour les modèles. La voix française SAPI doit être installée pour la fixture.
Le script PowerShell possède un BOM UTF-8 pour PowerShell 5.1.

Les sondes mesurent Whisper small en CPU et une tentative CUDA, puis Qwen3 4B
Q4_K_M dans llama.cpp CPU. Community-1 est absent et renvoie une erreur explicite.
À la demande de l'utilisateur, la candidate sherpa-onnx a été étudiée et testée :

```powershell
.venv\Scripts\python.exe scripts\acquire_diarization_alternative.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\create_diarization_fixture.ps1
.venv\Scripts\python.exe scripts\run_diarization_alternative.py
```

Deux voix synthétiques sont correctement regroupées en CPU sans nombre imposé.
Voir [l'étude de cette alternative](docs/diarization-alternative.md) pour les
preuves de licence et les limites de cet essai.
Les résultats JSON versionnés sont dans `docs/evidence/phase0-probes.json` ; les
poids, environnements et artefacts temporaires restent exclus de Git.

Les échantillons d'export sont des fixtures techniques, sans séance réelle ni
validation par un opérateur. Word n'a servi qu'à contrôler visuellement le DOCX
sur la machine de développement ; il ne sera pas une dépendance client.
