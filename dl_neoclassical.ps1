$ErrorActionPreference = "Continue"
$ytdlp = "C:\Users\leo\ace-step-v15\venv\Scripts\yt-dlp.exe"
$ffmpeg = "C:\Users\leo\ffmpeg\bin"
$out = "D:\data\piano-v2\raw"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$queries = @(
  "ludovico einaudi elements full album",
  "ludovico einaudi seven days walking day 1",
  "ludovico einaudi in a time lapse",
  "ludovico einaudi nightbook full album",
  "ludovico einaudi divenire",
  "ludovico einaudi islands essential",
  "yiruma first love full album",
  "olafur arnalds some kind of peace",
  "joep beving solipsism full album",
  "nils frahm solo"
)

foreach ($q in $queries) {
  Write-Host "=== $q ===" -ForegroundColor Cyan
  & $ytdlp "ytsearch2:$q" `
    --match-filter "duration >= 1200 & duration <= 7200" `
    -f "bestaudio/best" `
    -x --audio-format wav --audio-quality 0 `
    --no-playlist `
    --ffmpeg-location $ffmpeg `
    -o "$out\%(uploader)s - %(title)s [%(id)s].%(ext)s" `
    --no-overwrites --continue `
    --ignore-errors 2>&1 | Select-Object -Last 8
}

Write-Host "=== DONE ===" -ForegroundColor Green
Get-ChildItem $out -Filter *.wav | Select-Object Name, @{N="MB";E={[math]::Round($_.Length/1MB,1)}} | Format-Table -AutoSize
