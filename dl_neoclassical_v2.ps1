$ErrorActionPreference = "Continue"
$ytdlp = "C:\Users\leo\ace-step-v15\venv\Scripts\yt-dlp.exe"
$ffmpeg = "C:\Users\leo\ffmpeg\bin"
$out = "D:\data\piano-v2\raw"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$queries = @(
  "olafur arnalds some kind of peace full album",
  "olafur arnalds re:member full album",
  "joep beving solipsism full album",
  "joep beving prehension full album",
  "chilly gonzales solo piano ii full album",
  "hania rani esja full album",
  "hania rani home full album",
  "nils frahm spaces full album",
  "max richter sleep piano",
  "yann tiersen amelie piano"
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
    --ignore-errors 2>&1 | Select-Object -Last 6
}

Write-Host "=== DONE ===" -ForegroundColor Green
Get-ChildItem $out -Filter *.wav | Measure-Object -Property Length -Sum | Select-Object Count, @{N="GB";E={[math]::Round($_.Sum/1GB,2)}}
