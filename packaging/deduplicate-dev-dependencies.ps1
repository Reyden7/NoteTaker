param([Parameter(Mandatory=$true)][string]$SourceBundle, [Parameter(Mandatory=$true)][string[]]$TargetBundles)
# Preserve bytes of generated archives, sharing identical immutable dependency files.
$ErrorActionPreference='Stop'
$notetakerRoot=Split-Path -Parent $PSScriptRoot
$notetakerDist=[IO.Path]::GetFullPath((Join-Path $notetakerRoot 'dist'))+'\'
$notetakerSource=[IO.Path]::GetFullPath((Join-Path $notetakerRoot $SourceBundle))
if(-not $notetakerSource.StartsWith($notetakerDist)){throw 'Source is outside dist'}
if(-not (Test-Path -LiteralPath (Join-Path $notetakerSource 'NoteTaker.exe'))){throw 'Source is not a generated bundle'}
$notetakerCount=0;$notetakerBytes=0
foreach($notetakerTargetName in $TargetBundles){
    $notetakerTarget=[IO.Path]::GetFullPath((Join-Path $notetakerRoot $notetakerTargetName))
    if(-not $notetakerTarget.StartsWith($notetakerDist) -or $notetakerTarget -eq $notetakerSource){throw 'Unsafe archive target'}
    if(-not (Test-Path -LiteralPath (Join-Path $notetakerTarget 'NoteTaker.exe'))){throw 'Target is not a generated bundle'}
    $notetakerInternal=Join-Path $notetakerTarget '_internal'
    foreach($notetakerFile in Get-ChildItem -LiteralPath $notetakerInternal -Recurse -File | Where-Object {$_.Length -ge 1MB -and $_.LinkType -ne 'HardLink'}){
        $notetakerRelative=$notetakerFile.FullName.Substring($notetakerTarget.Length+1)
        $notetakerOriginal=[IO.Path]::GetFullPath((Join-Path $notetakerSource $notetakerRelative))
        $notetakerBackup=$notetakerFile.FullName+'.dedup-backup'
        if(-not $notetakerOriginal.StartsWith($notetakerSource+'\') -or -not $notetakerBackup.StartsWith($notetakerTarget+'\')){throw 'Invalid dependency path'}
        if(-not (Test-Path -LiteralPath $notetakerOriginal) -or (Test-Path -LiteralPath $notetakerBackup)){continue}
        if((Get-Item -LiteralPath $notetakerOriginal).Length -ne $notetakerFile.Length){continue}
        $notetakerHash=(Get-FileHash -LiteralPath $notetakerFile.FullName -Algorithm SHA256).Hash
        if($notetakerHash -ne (Get-FileHash -LiteralPath $notetakerOriginal -Algorithm SHA256).Hash){continue}
        Move-Item -LiteralPath $notetakerFile.FullName -Destination $notetakerBackup
        try{
            New-Item -ItemType HardLink -Path $notetakerFile.FullName -Target $notetakerOriginal | Out-Null
            if((Get-FileHash -LiteralPath $notetakerFile.FullName -Algorithm SHA256).Hash -ne $notetakerHash){throw 'Linked dependency hash mismatch'}
        }catch{
            if(Test-Path -LiteralPath $notetakerFile.FullName){Remove-Item -LiteralPath $notetakerFile.FullName}
            Move-Item -LiteralPath $notetakerBackup -Destination $notetakerFile.FullName
            throw
        }
        Remove-Item -LiteralPath $notetakerBackup
        $notetakerCount++;$notetakerBytes+=$notetakerFile.Length
    }
}
@{identical_files_linked=$notetakerCount;duplicate_allocations_replaced_bytes=$notetakerBytes;content_hashes_preserved=$true;scope='generated archived dependencies only; no model or user data deletion'} | ConvertTo-Json
