param([switch]$Development, [switch]$SkipModels, [string]$InnoCompiler, [string]$DistributionDirectory = 'dist')
$ErrorActionPreference = 'Stop'
$notetakerRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $notetakerRoot
$notetakerDistRoot = [IO.Path]::GetFullPath((Join-Path $notetakerRoot $DistributionDirectory))
$notetakerBundle = Join-Path $notetakerDistRoot 'NoteTaker'
if (-not $notetakerBundle.StartsWith($notetakerRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Build target is outside the repository' }
if (Test-Path -LiteralPath $notetakerBundle) { throw 'dist\NoteTaker already exists. Preserve or move that generated bundle before rebuilding.' }
if (-not $Development) {
    throw 'Commercial build blocked: exact license bundle, signed redistributables and clean offline Windows qualification are not approved. Use -Development for local qualification only.'
}
if ($InnoCompiler) { throw 'Installer compilation is gated until redistribution and clean Windows qualification are approved.' }
$env:PYTHONPATH = Join-Path $notetakerRoot 'src'
$notetakerTestDir = Join-Path $notetakerRoot ('.cache\build-tests-' + [guid]::NewGuid().ToString('N'))
& .venv\Scripts\python.exe -m pytest "--basetemp=$notetakerTestDir"
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
$notetakerBuild = Start-Process -FilePath (Join-Path $notetakerRoot '.venv\Scripts\python.exe') -WorkingDirectory $notetakerRoot -ArgumentList @('-m','PyInstaller','--noconfirm','--distpath',('"' + $notetakerDistRoot + '"'),'packaging/notetaker.spec') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $notetakerRoot 'build-pyinstaller.log') -RedirectStandardError (Join-Path $notetakerRoot 'build-pyinstaller-stderr.log')
if ($notetakerBuild.ExitCode -ne 0) { throw 'PyInstaller failed; inspect build-pyinstaller-stderr.log' }
if (-not $SkipModels) {
    & .venv\Scripts\python.exe -m notetaker.main verify-models
    if ($LASTEXITCODE -ne 0) { throw 'Model integrity verification failed' }
    foreach ($notetakerManifest in @('models_manifest.json','diarization_models_manifest.json')) {
        $notetakerData = Get-Content -LiteralPath $notetakerManifest -Raw | ConvertFrom-Json
        foreach ($notetakerAsset in $notetakerData.assets) {
            $notetakerTarget = Join-Path $notetakerBundle $notetakerAsset.path
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $notetakerTarget) | Out-Null
            Copy-Item -LiteralPath $notetakerAsset.path -Destination $notetakerTarget
        }
        Copy-Item -LiteralPath $notetakerManifest -Destination $notetakerBundle
    }
    $notetakerLlama = Join-Path $notetakerBundle 'runtimes\llama-cpu-b11681'
    New-Item -ItemType Directory -Force -Path $notetakerLlama | Out-Null
    Get-ChildItem -LiteralPath 'runtimes\llama-cpu-b11681' -File | Where-Object { $_.Extension -eq '.dll' -or $_.Name -eq 'llama-completion.exe' -or $_.Name -like '*LICENSE*' } | Copy-Item -Destination $notetakerLlama
}
Copy-Item -LiteralPath 'third_party' -Destination $notetakerBundle -Recurse
Copy-Item -LiteralPath 'LICENSES-THIRD-PARTY.md' -Destination $notetakerBundle
Copy-Item -LiteralPath 'docs\operator-guide.md' -Destination (Join-Path $notetakerBundle 'GUIDE-UTILISATEUR.md')
Copy-Item -LiteralPath 'docs\field-test.md' -Destination (Join-Path $notetakerBundle 'RECETTE-TERRAIN.md')
Copy-Item -LiteralPath 'docs\information-registry-0.2.4.md' -Destination (Join-Path $notetakerBundle 'REGISTRE-INFORMATIONS.md')
Copy-Item -LiteralPath 'docs\direct-summary-0.2.5.md' -Destination (Join-Path $notetakerBundle 'LABORATOIRE-SYNTHESE.md')
Copy-Item -LiteralPath 'docs\direct-summary-human-evaluation.md' -Destination $notetakerBundle
$notetakerVersion = & .venv\Scripts\python.exe -c 'from notetaker import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Cannot read application version' }
@{development_only=$true; models_included=(-not $SkipModels); qualification='QUALITY UNDER EVALUATION; NOT VALIDATED ON CLEAN OFFLINE WINDOWS'; version=$notetakerVersion} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $notetakerBundle 'BUILD-STATUS.json')
Write-Output "Development bundle created: $notetakerBundle. This is not an approved commercial installer."
