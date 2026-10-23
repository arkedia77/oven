# leowin 이미지 전용 상시 ComfyUI 기동기(oven 10-23 · kee 133932 레이어 · LEO 「성공이구만」 판정)
# 예약 작업(부팅 시·SYSTEM)이 이 파일을 부름. 조건: tailscale IP 바인딩만 · 유휴 시 VRAM 반납(--disable-smart-memory) · 출력 E:
param([switch]$Once)
$R = "C:\comfyui_moss"; $IP = "100.110.30.103"; $PORT = 8188; $OUT = "E:\comfyui_out"
$log = "$R\service.log"
function L($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m" | Out-File -Append -Encoding utf8 $log }
New-Item -ItemType Directory -Force $OUT | Out-Null
# 부팅 직후엔 tailscale IP 가 아직 없음 — 최대 10분 기다림
for ($i = 0; $i -lt 120; $i++) {
  if (Get-NetIPAddress -IPAddress $IP -ErrorAction SilentlyContinue) { break }
  Start-Sleep 5
}
if (-not (Get-NetIPAddress -IPAddress $IP -ErrorAction SilentlyContinue)) { L "tailscale IP $IP 없음 — 중단"; exit 1 }
$backoff = 10
while ($true) {
  L "ComfyUI 기동 $IP`:$PORT"
  $t0 = Get-Date
  & "$R\venv\Scripts\python.exe" "$R\ComfyUI\main.py" --listen $IP --port $PORT --output-directory $OUT --disable-smart-memory *>> "$R\comfy_service_out.log"
  L "ComfyUI 종료 rc=$LASTEXITCODE"
  if ($Once) { break }
  # 5분 넘게 살아 있었으면 정상 재시작, 바로 죽으면 간격을 늘림(최대 10분)
  if (((Get-Date) - $t0).TotalMinutes -gt 5) { $backoff = 10 } else { $backoff = [math]::Min($backoff * 2, 600) }
  Start-Sleep $backoff
}
