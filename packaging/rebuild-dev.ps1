# Preserve the generated model payload while rebuilding the code bundle.
$ErrorActionPreference = 'Stop'
$notetakerRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $notetakerRoot
$notetakerCurrent = (Resolve-Path -LiteralPath 'dist\NoteTaker').Path
$notetakerArchive = [IO.Path]::GetFullPath((Join-Path $notetakerRoot ('dist\dev-previous-' + [guid]::NewGuid().ToString('N'))))
foreach ($notetakerPath in @($notetakerCurrent,$notetakerArchive)) { if (-not $notetakerPath.StartsWith($notetakerRoot + '\dist\')) { throw 'Unsafe build path' } }
$notetakerStatus = Get-Content -LiteralPath (Join-Path $notetakerCurrent 'BUILD-STATUS.json') -Raw | ConvertFrom-Json
if (-not $notetakerStatus.development_only -or -not $notetakerStatus.models_included) { throw 'A complete generated development bundle is required' }
Move-Item -LiteralPath $notetakerCurrent -Destination $notetakerArchive
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging\build.ps1 -Development -SkipModels
if ($LASTEXITCODE -ne 0) { throw "Build failed. Previous generated bundle preserved at $notetakerArchive" }
foreach ($notetakerName in @('models','runtimes','models_manifest.json','diarization_models_manifest.json')) {
    $notetakerFrom = [IO.Path]::GetFullPath((Join-Path $notetakerArchive $notetakerName))
    $notetakerTo = [IO.Path]::GetFullPath((Join-Path $notetakerCurrent $notetakerName))
    if (-not $notetakerFrom.StartsWith($notetakerArchive + '\') -or -not $notetakerTo.StartsWith($notetakerCurrent + '\')) { throw 'Unsafe asset move' }
    if (Test-Path -LiteralPath $notetakerTo) { throw 'Asset destination already exists' }
    Move-Item -LiteralPath $notetakerFrom -Destination $notetakerTo
}
@{development_only=$true;models_included=$true;qualification='NOT VALIDATED ON CLEAN OFFLINE WINDOWS';version='0.1.0'} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $notetakerCurrent 'BUILD-STATUS.json')
Write-Output "Code bundle rebuilt; original model files preserved. Previous binaries: $notetakerArchive"
