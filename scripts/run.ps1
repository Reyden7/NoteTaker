param([string]$DataDirectory)
$ErrorActionPreference = 'Stop'
$notetakerRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $notetakerRoot
$env:PYTHONPATH = Join-Path $notetakerRoot 'src'
if ($DataDirectory) {
    & .venv\Scripts\python.exe -m notetaker.main gui --data-dir $DataDirectory
} else {
    & .venv\Scripts\python.exe -m notetaker.main gui
}
exit $LASTEXITCODE
