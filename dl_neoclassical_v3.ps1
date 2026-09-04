$ErrorActionPreference = "Continue"
$ytdlp = "C:\Users\leo\ace-step-v15\venv\Scripts\yt-dlp.exe"
$ffmpeg = "C:\Users\leo\ffmpeg\bin"
$out = "D:\data\piano-v2\raw"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$queries = @(
  "philip glass etudes complete piano",
  "philip glass glassworks full album",
  "jean-michel blais il full album",
  "jean-michel blais dans ma main piano",
  "poppy ackroyd resolve full album",
  "poppy ackroyd feathers piano",
  "ryuichi sakamoto async full album",
  "ryuichi sakamoto playing the piano 2009",
  "helios eingya full album",
  "dustin o'halloran lumiere full album",
  "max richter 24 postcards in full colour",
  "sylvain chauveau nuage piano"
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
