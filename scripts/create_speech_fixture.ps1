# Development-only synthetic speech fixture, never used as evidence of field quality.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$notetakerSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$notetakerVoice = $notetakerSynth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'fr-FR' } | Select-Object -First 1
if (-not $notetakerVoice) { throw 'NO_LOCAL_FRENCH_SAPI_VOICE' }
$notetakerSynth.SelectVoice($notetakerVoice.VoiceInfo.Name)
$notetakerDir = Join-Path $PSScriptRoot '..\output\phase0'
New-Item -ItemType Directory -Force -Path $notetakerDir | Out-Null
$notetakerFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo -ArgumentList 16000, ([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen), ([System.Speech.AudioFormat.AudioChannel]::Mono)
$notetakerSynth.SetOutputToWaveFile((Join-Path $notetakerDir 'fr-synthetic.wav'), $notetakerFormat)
$notetakerText = 'La séance du conseil municipal est ouverte. Nous examinons les travaux de la bibliothèque. Le montant annoncé est de douze mille euros. Le résultat du vote reste à compléter.'
$notetakerSynth.Speak($notetakerText)
$notetakerSynth.Dispose()
@{ kind = 'synthetic-speech'; voice = $notetakerVoice.VoiceInfo.Name; text = $notetakerText; purpose = 'ASR smoke test only, not WER or meeting quality validation' } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $notetakerDir 'fixture.json')
Write-Output "Fixture created with $($notetakerVoice.VoiceInfo.Name)"

