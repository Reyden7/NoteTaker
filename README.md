# NoteTaker

Application Windows locale de transcription et de préparation des procès-verbaux
municipaux. **Version de développement 0.2.1 : annuaire municipal sans biométrie.** Le premier
test réel de 0.1 a échoué ; les corrections ne constituent pas une qualification
commerciale. Aucun `NoteTaker-Setup.exe` approuvé n'est disponible.

## Utiliser la version de travail

Le dernier dossier de travail est `dist\directory-01\NoteTaker` ; lancer son
`NoteTaker.exe`. Conserver tout ce dossier : exécutables, `_internal`, modèles et runtimes.
Aucun téléchargement n'est prévu au lancement. Ce dossier est généré et exclu de Git.

Le [guide opérateur](docs/operator-guide.md) décrit la création d'une séance,
le microphone, les imports **WAV/MP3/M4A**, les corrections et les exports.
Les données sont conservées dans `%LOCALAPPDATA%\NoteTaker` par défaut.

Le bouton **Annuaire des intervenants** est disponible même sans séance :
prénom, nom, fonction permanente, commune, recherche/filtres, archivage et
réactivation. L'onglet **Participants** conserve pour chaque séance les présences,
rôles et procurations. La transcription permet une attribution manuelle à ces
personnes. Le futur assistant vocal est grisé : aucune référence biométrique
n'est créée. Les étapes suivantes attendent la validation de cette interface.

La migration SQLite v3 → v4 sauvegarde automatiquement la base existante dans
`migration-backups` avant sa mise à niveau. Une ancienne version ne peut pas
ouvrir une base v4 ; pour un retour arrière, conserver une copie complète des
données et utiliser la sauvegarde compatible dans un dossier distinct.

Le parcours comprend l'enregistrement avec journal et récupération, Whisper,
sherpa-onnx/WeSpeaker, les noms corrigés manuellement, la synthèse Qwen3 sourcée,
l'édition, les décisions/votes et l'export PDF/DOCX après confirmation humaine.
Les modes transcription intégrale, synthèse et PV municipal sont distincts.
Les décisions et résultats de vote confirmés sont exclusivement saisis par
l'opérateur. Le mode municipal exige la confirmation du secrétaire.

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

**104 tests automatisés réussis**, dont 18 nouveaux contrôles de l'annuaire,
de la migration, des présences et de l'interface. Le [premier audit réel](docs/audit-0.2.md)
documente 195 groupes, 1 734 caractères perdus et un PDF de 54 pages. La nouvelle
transcription du même audio n'a plus ces caractères perdus et conserve les mots
horodatés. Les voix et synthèses sont comparées dans un benchmark local,
sans remplacer les corrections de la séance initiale. Les rapports et limites
sont dans [docs/progress.md](docs/progress.md). La comparaison complète donne
neuf groupes vocaux sans nombre imposé, 36 reformulations sourcées dans huit
thèmes et un aperçu PDF de quatre pages (6 844 caractères). Cela ne prouve pas
la justesse des voix ni la fidélité de la synthèse : des formulations et
attributions restent à corriger. Qwen3-4B-Instruct-2507 Q4_K_M est le modèle
sélectionné pour ce lot de développement, sans téléchargement au lancement.

Pour examiner cette séance réelle distincte, lancer
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\run-quality-review.ps1`.
Ce lanceur n'ouvre pas les données de la séance utilisateur initiale et ne crée
aucune approbation. Les aperçus privés sous `output/quality-02/instruct-2507`
portent explicitement la mention non validée.

**Non validés :** exactitude des voix sur référence humaine, WER/DER, couverture
des sujets et absence d'invention sémantique, capture longue, GPU et Windows
vierge déconnecté. Le débat est un premier cas réel, dont la réussite ne serait
pas une qualification des conseils municipaux. Voir le [benchmark](docs/benchmark-0.2.md)
et la [procédure terrain](docs/field-test.md).

## Architecture et livraison

- [Architecture actuelle](docs/architecture.md)
- [Versions et compatibilité](docs/compatibility.md)
- [Licences et réserves de redistribution](docs/licenses.md)
- [Diarisation sherpa et limites](docs/diarization-alternative.md)
- [Reproduction des validations](docs/testing.md)
- [Build PyInstaller et stratégie Inno Setup](packaging/README.md)

Le lot de développement représente environ 3,56 Go avant compression. Les
notices natives, runtimes, signature et recette propre hors ligne restent à
qualifier avant le livrable commercial unique `NoteTaker-Setup.exe`. La roue
CTranslate2 actuelle dépend de cuDNN même pour CPU ; une compilation CPU seule
est étudiée séparément avant toute intégration ou autorisation de distribution.
L'état de phase 0 antérieur est conservé dans `docs/history`.
