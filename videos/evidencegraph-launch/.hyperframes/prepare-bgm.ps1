param(
    [string]$Ffmpeg = "ffmpeg"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $projectRoot "assets\A_Little_Story_Kei_Morimoto.mp3"
$audioDir = Join-Path $projectRoot ".media\audio\bgm"
$ingested = Join-Path $audioDir "bgm_001.mp3"
$edited = Join-Path $audioDir "bgm_001.edit.mp3"

if (-not (Test-Path -LiteralPath $source)) {
    throw "Download Track 1 from the official DOVA-SYNDROME page and place it at: $source"
}

New-Item -ItemType Directory -Path $audioDir -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $ingested -Force

& $Ffmpeg -hide_banner -loglevel error -y `
    -i $source `
    -t 130 `
    -af "afade=t=in:st=0:d=0.8,afade=t=out:st=128.8:d=1.2" `
    -c:a libmp3lame -b:a 256k `
    $edited

if ($LASTEXITCODE -ne 0) {
    throw "ffmpeg failed with exit code $LASTEXITCODE"
}

Write-Host "Prepared licensed local BGM: $edited"
