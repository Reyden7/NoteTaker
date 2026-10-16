$ErrorActionPreference = 'Stop'
$notetakerRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $notetakerRoot
$notetakerTemp = Join-Path $notetakerRoot ('.cache\pytest-' + [guid]::NewGuid().ToString('N'))
& .venv\Scripts\python.exe -m pytest "--basetemp=$notetakerTemp" --junitxml=docs/evidence/pytest.xml @args
exit $LASTEXITCODE
