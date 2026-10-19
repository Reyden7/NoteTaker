# Explicit synthetic control for regression gates, never a quality benchmark.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$notetakerDirectory=Join-Path $PSScriptRoot '..\output\corrections-fixture'
New-Item -ItemType Directory -Force -Path $notetakerDirectory | Out-Null
$notetakerSynth=New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $notetakerVoice=$notetakerSynth.GetInstalledVoices() | Where-Object {$_.VoiceInfo.Culture.Name -eq 'fr-FR'} | Select-Object -First 1
    if(-not $notetakerVoice){throw 'NO_LOCAL_FRENCH_SAPI_VOICE'}
    $notetakerSynth.SelectVoice($notetakerVoice.VoiceInfo.Name)
    $notetakerFormat=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo -ArgumentList 16000,([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen),([System.Speech.AudioFormat.AudioChannel]::Mono)
    $notetakerAudio=Join-Path $notetakerDirectory 'substantive-synthetic.wav'
    if(Test-Path -LiteralPath $notetakerAudio){throw 'Preserve the existing fixture before repeating'}
    $notetakerSynth.SetOutputToWaveFile($notetakerAudio,$notetakerFormat)
    $notetakerText='Je propose de réparer la toiture de la bibliothèque municipale avant les pluies de novembre. Les infiltrations menacent les livres et les espaces de lecture. Je demande deux devis détaillés avant toute décision sur les travaux. Le budget global envisagé pour les travaux de la bibliothèque est de vingt mille euros. Je souhaite aussi maintenir un accueil temporaire des lecteurs dans une autre salle pendant le chantier.'
    $notetakerSynth.Speak($notetakerText)
    @{kind='synthetic-regression-fixture';voice=$notetakerVoice.VoiceInfo.Name;text=$notetakerText;purpose='Export and correction regression gates only; no field speaker accuracy or human meeting approval'} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $notetakerDirectory 'fixture.json')
} finally {$notetakerSynth.Dispose()}
