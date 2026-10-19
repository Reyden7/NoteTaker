param([Parameter(Mandatory=$true)][string]$BundleDirectory)
# Disk-saving developer build only. Each payload path is an ordinary NTFS file.
$ErrorActionPreference = 'Stop'
$notetakerRoot = Split-Path -Parent $PSScriptRoot
$notetakerBundle = [IO.Path]::GetFullPath((Join-Path $notetakerRoot $BundleDirectory))
if (-not $notetakerBundle.StartsWith($notetakerRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Target is outside the repository' }
$notetakerStatusPath = Join-Path $notetakerBundle 'BUILD-STATUS.json'
$notetakerStatus = Get-Content -LiteralPath $notetakerStatusPath -Raw | ConvertFrom-Json
if (-not $notetakerStatus.development_only -or $notetakerStatus.models_included) { throw 'Requires an incomplete development-only bundle built with -SkipModels' }
foreach ($notetakerManifest in @('models_manifest.json','diarization_models_manifest.json')) {
    $notetakerData = Get-Content -LiteralPath (Join-Path $notetakerRoot $notetakerManifest) -Raw | ConvertFrom-Json
    foreach ($notetakerAsset in $notetakerData.assets) {
        $notetakerSource = [IO.Path]::GetFullPath((Join-Path $notetakerRoot $notetakerAsset.path))
        $notetakerTarget = [IO.Path]::GetFullPath((Join-Path $notetakerBundle $notetakerAsset.path))
        if (-not $notetakerSource.StartsWith($notetakerRoot + '\') -or -not $notetakerTarget.StartsWith($notetakerBundle + '\')) { throw 'Invalid manifest path' }
        if ((Get-Item -LiteralPath $notetakerSource).Length -ne $notetakerAsset.size_bytes -or (Get-FileHash -LiteralPath $notetakerSource -Algorithm SHA256).Hash.ToLowerInvariant() -ne $notetakerAsset.sha256) { throw 'Local model integrity check failed' }
        if (Test-Path -LiteralPath $notetakerTarget) { throw 'Target asset already exists; preserve it and use a fresh bundle' }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $notetakerTarget) | Out-Null
        New-Item -ItemType HardLink -Path $notetakerTarget -Target $notetakerSource | Out-Null
        if ((Get-FileHash -LiteralPath $notetakerTarget -Algorithm SHA256).Hash.ToLowerInvariant() -ne $notetakerAsset.sha256) { throw 'Bundled model integrity check failed' }
    }
    Copy-Item -LiteralPath (Join-Path $notetakerRoot $notetakerManifest) -Destination $notetakerBundle
}
$notetakerRuntime = Join-Path $notetakerBundle 'runtimes\llama-cpu-b11681'
New-Item -ItemType Directory -Path $notetakerRuntime | Out-Null
Get-ChildItem -LiteralPath (Join-Path $notetakerRoot 'runtimes\llama-cpu-b11681') -File | Where-Object { $_.Extension -eq '.dll' -or $_.Name -eq 'llama-completion.exe' -or $_.Name -like '*LICENSE*' } | ForEach-Object {
    $notetakerNativeTarget = Join-Path $notetakerRuntime $_.Name
    New-Item -ItemType HardLink -Path $notetakerNativeTarget -Target $_.FullName | Out-Null
    if ((Get-FileHash -LiteralPath $notetakerNativeTarget -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash) { throw 'Native runtime integrity check failed' }
}
$notetakerStatus.models_included = $true
$notetakerStatus | Add-Member -NotePropertyName asset_storage -NotePropertyValue 'verified local NTFS hardlinks; development only; keep immutable' -Force
$notetakerStatus | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath $notetakerStatusPath
Write-Output 'Development payload attached and verified. No download performed.'
