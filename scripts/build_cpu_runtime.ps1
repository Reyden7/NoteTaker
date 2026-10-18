# Explicit build-only wrapper; no active application files are replaced.
param([int]$Parallel = 2)
$ErrorActionPreference = 'Stop'
$notetakerRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $notetakerRoot
& .venv\Scripts\python.exe scripts\build_cpu_runtime.py --parallel $Parallel
if ($LASTEXITCODE -ne 0) { throw 'CPU build failed; inspect isolated logs. Active application files are unchanged.' }
