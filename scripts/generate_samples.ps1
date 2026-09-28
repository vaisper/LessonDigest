# Regenerates synthetic lesson audio (WAV) from the texts in samples/generated.
# Windows only (uses the built-in Speech API). Voices: run
#   Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/generate_samples.ps1

Add-Type -AssemblyName System.Speech

$dir = Join-Path $PSScriptRoot "..\samples\generated"
if (-not (Test-Path $dir)) {
    Write-Error "Folder not found: $dir"
    exit 1
}

$voice = "Microsoft Irina Desktop"
Get-ChildItem $dir -Filter *.txt | ForEach-Object {
    $wav = [System.IO.Path]::ChangeExtension($_.FullName, ".wav")
    $text = Get-Content $_.FullName -Raw -Encoding UTF8
    $words = ($text -split '\s+' | Where-Object { $_ -ne '' }).Count
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $synth.SelectVoice($voice)
    } catch {
        Write-Warning "Voice '$voice' not found, using default"
    }
    $synth.SetOutputToWaveFile($wav)
    $synth.Speak($text)
    $synth.Dispose()
    Write-Host "OK  $($_.Name)  (words=$words) -> $wav"
}
