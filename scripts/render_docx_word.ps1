# Developer QA only: installed Microsoft Word is NOT a product dependency.
param([Parameter(Mandatory=$true)][string]$InputPath, [Parameter(Mandatory=$true)][string]$PdfPath)
$ErrorActionPreference = 'Stop'
$notetakerInput = (Resolve-Path -LiteralPath $InputPath).Path
$notetakerOutput = [IO.Path]::GetFullPath($PdfPath)
$notetakerHashBefore = (Get-FileHash -LiteralPath $notetakerInput -Algorithm SHA256).Hash
$notetakerWord = $null
$notetakerDocument = $null
try {
    $notetakerWord = New-Object -ComObject Word.Application
    $notetakerWord.Visible = $false
    $notetakerWord.DisplayAlerts = 0
    $notetakerWord.AutomationSecurity = 3
    $notetakerDocument = $notetakerWord.Documents.Open($notetakerInput, $false, $true)
    $notetakerDocument.ExportAsFixedFormat($notetakerOutput, 17)
    Write-Output "Rendered pages: $($notetakerDocument.ComputeStatistics(2))"
} finally {
    $notetakerSaveChanges = 0
    try {
        if ($notetakerDocument) { $notetakerDocument.Close([ref]$notetakerSaveChanges); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($notetakerDocument) }
    } finally {
        if ($notetakerWord) { $notetakerWord.Quit([ref]$notetakerSaveChanges); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($notetakerWord) }
    }
}
if ((Get-FileHash -LiteralPath $notetakerInput -Algorithm SHA256).Hash -ne $notetakerHashBefore) { throw 'Source DOCX changed during rendering' }
