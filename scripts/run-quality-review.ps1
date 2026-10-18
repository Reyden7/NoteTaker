# Open the separate, unapproved real-audio review session. No inference or approval.
$ErrorActionPreference = 'Stop'
$notetakerRoot = Split-Path -Parent $PSScriptRoot
$notetakerExecutable = Join-Path $notetakerRoot 'dist\quality-02\NoteTaker\NoteTaker.exe'
$notetakerReview = Join-Path $notetakerRoot 'output\quality-02\instruct-2507\review-session'
if (-not (Test-Path -LiteralPath $notetakerExecutable -PathType Leaf)) { throw 'Build the quality-02 development bundle first' }
if (-not (Test-Path -LiteralPath $notetakerReview -PathType Container)) { throw 'The private comparative review session is unavailable' }
# Visible window requested by the operator running this launcher.
Start-Process -FilePath $notetakerExecutable -ArgumentList @('--data-dir',('"' + $notetakerReview + '"')) -WorkingDirectory $notetakerRoot
