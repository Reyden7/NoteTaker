# Developer disk-space operation: preserve identical bytes in the old bundle.
param([string]$BundleDirectory = 'dist\NoteTaker')
$ErrorActionPreference = 'Stop'
$notetakerRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$notetakerRelative = 'models\llm\qwen3-4b\Qwen3-4B-Q4_K_M.gguf'
$notetakerSource = (Resolve-Path -LiteralPath (Join-Path $notetakerRoot $notetakerRelative)).Path
$notetakerBundle = (Resolve-Path -LiteralPath (Join-Path $notetakerRoot $BundleDirectory)).Path
if (-not $notetakerBundle.StartsWith($notetakerRoot + '\dist\')) { throw 'Bundle must be generated inside dist' }
$notetakerStatus = Get-Content -LiteralPath (Join-Path $notetakerBundle 'BUILD-STATUS.json') -Raw | ConvertFrom-Json
if (-not $notetakerStatus.development_only) { throw 'Only development bundles may be deduplicated' }
$notetakerTarget = (Resolve-Path -LiteralPath (Join-Path $notetakerBundle $notetakerRelative)).Path
if (-not $notetakerSource.StartsWith($notetakerRoot + '\') -or -not $notetakerTarget.StartsWith($notetakerBundle + '\')) { throw 'Unsafe paths' }
$notetakerHash = (Get-FileHash -LiteralPath $notetakerSource -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $notetakerTarget -Algorithm SHA256).Hash -ne $notetakerHash) { throw 'Preserve differing models' }
$notetakerLink = $notetakerTarget + '.link-temp'
$notetakerBackup = $notetakerTarget + '.duplicate-temp'
if ((Test-Path -LiteralPath $notetakerLink) -or (Test-Path -LiteralPath $notetakerBackup)) { throw 'Existing temporary file; preserve and inspect' }
New-Item -ItemType HardLink -Path $notetakerLink -Value $notetakerSource | Out-Null
if ((Get-FileHash -LiteralPath $notetakerLink -Algorithm SHA256).Hash -ne $notetakerHash) { throw 'Link mismatch' }
Move-Item -LiteralPath $notetakerTarget -Destination $notetakerBackup
try {
    Move-Item -LiteralPath $notetakerLink -Destination $notetakerTarget
    if ((Get-FileHash -LiteralPath $notetakerTarget -Algorithm SHA256).Hash -ne $notetakerHash) { throw 'Final hash mismatch' }
} catch {
    if (-not (Test-Path -LiteralPath $notetakerTarget)) { Move-Item -LiteralPath $notetakerBackup -Destination $notetakerTarget }
    throw
}
Remove-Item -LiteralPath $notetakerBackup
Write-Output 'Old generated bundle model now shares an NTFS hardlink with its identical canonical model; bytes preserved.'
