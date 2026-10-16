# Two distinct installed synthetic voices; controlled smoke test, not field DER.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$notetakerDir = Join-Path $PSScriptRoot '..\output\phase0'
$notetakerSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$notetakerFrench = $notetakerSynth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'fr-FR' } | Select-Object -First 1
$notetakerOther = $notetakerSynth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -ne $notetakerFrench.VoiceInfo.Name } | Select-Object -First 1
if (-not $notetakerFrench -or -not $notetakerOther) { throw 'TWO_INSTALLED_SYNTHETIC_VOICES_REQUIRED' }
$notetakerFormat = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo -ArgumentList 16000, ([System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen), ([System.Speech.AudioFormat.AudioChannel]::Mono)
$notetakerIndex = 0
foreach ($notetakerVoice in @($notetakerFrench, $notetakerOther)) {
    $notetakerSynth.SelectVoice($notetakerVoice.VoiceInfo.Name)
    $notetakerSynth.SetOutputToWaveFile((Join-Path $notetakerDir "voice-$notetakerIndex.wav"), $notetakerFormat)
    $notetakerSynth.Speak('La discussion porte sur les travaux de la bibliotheque municipale. Nous devons examiner les propositions et completer les informations avant de prendre une decision.')
    $notetakerSynth.SetOutputToNull()
    $notetakerIndex++
}
$notetakerSynth.Dispose()
@{kind='synthetic-two-voices'; voices=@($notetakerFrench.VoiceInfo.Name,$notetakerOther.VoiceInfo.Name); limitation='The second voice may not be French. This is not a natural meeting corpus.'} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $notetakerDir 'diarization-fixture.json')
