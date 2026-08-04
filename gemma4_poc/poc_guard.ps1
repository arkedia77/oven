# PoC 자동중단 가드 (kimsecretary 선결 ⑵, 2026-08-04)
#
# ★계기: 2026-08-04 18:00:52 사고 — PoC용 llama-server(8090)가 워킹셋 18.2GB까지 부푼 상태에서
#   하모니시티 LLM 서버(8080)가 크래시했고, 시뮬이 13분 30초 정지했다.
#   ★그때 PoC는 «자기가 남을 죽이고 있다»는 것을 몰랐다. 이 가드가 그 구멍을 막는다.
#
# 감시 3축 (하나라도 위반하면 PoC를 즉시 죽인다):
#   ①하모니시티 LLM(8080) health != 200            → 이진 판정, 임계 불요
#   ②하모니시티 시뮬(run_village) 프로세스 소멸      → 이진 판정, 임계 불요
#   ③PoC 서버(8090) 워킹셋 / 시스템 여유 메모리      → 임계 필요(아래 근거)
#
# ★임계 근거 — ★1차로 12GB를 잡았다가 즉시 틀린 것이 드러나 실측으로 고쳤다.
#   ⓐ오류: 「모델 약 7GB + 체크포인트 2×0.45GB ≈ 8GB」로 «추정»해 상한 12GB를 잡았다.
#     ★실측하니 ctxcp=2 서버의 **기동 직후 워킹셋이 이미 13.57GB**였다(KV 캐시를 안 셌다).
#     ⇒ 그대로 켰으면 **가드가 정상 운전을 즉시 오중단**했을 것이다.
#     ★임계를 실측 아닌 추정으로 잡으면 안 된다는 것을 같은 날 두 번째로 확인한 셈이다.
#   ⓑ정정(실측 기반):
#     · PoC 워킹셋 상한 **17GB** = 실측 기저 13.57GB + 체크포인트 여유 2×0.45GB(=14.5GB) 에
#       약 1.15배 여유 → 16.7 → 17GB. ★그리고 **사고 시 실측 18.2GB보다 아래**다.
#       ⇒ «정상 운전은 통과 / 사고 수준에 닿기 전에 정지»가 둘 다 성립하는 유일한 구간.
#     · ★시스템 여유 메모리는 **트립 축에서 뺐다(기록만)**. 1차로 40GB를 잡았다가 무장 13초 만에
#       오중단했다 — ★40GB를 «무부하 49.6~51GB와 사고 저점 31.7GB의 사이»로 잡았는데,
#       **PoC 서버를 올린 정상 상태의 여유가 이미 36.1GB**였다(서버가 13.5GB를 먹으므로).
#       ⇒ 정상 36.1 vs 사고 31.7 = **간격 4.4GB**밖에 안 되어 **판별력이 없다.**
#       ★대신 워킹셋 축이 판별한다(정상 13.57 vs 사고 18.2, 기저가 명확).
#       여유 메모리는 **20GB 백스톱**만 남긴다 — 사고 저점보다도 한참 아래라 «진짜 고갈»에만 발동.
#   ⓒ재산출 조건: 모델·ctx-size·ctx-checkpoints가 바뀌면 **기저 워킹셋부터 다시 재고**
#     이 절을 다시 쓴다. 임계만 고쳐 쓰지 않는다.
#
# 로그는 ASCII로 남긴다(PowerShell 5.1 콘솔 코드페이지).

param(
    [int]$PocWorkingSetLimitGB = 17,
    [int]$FreeMemFloorGB       = 20,   # 백스톱 전용(판별용 아님)
    [int]$IntervalSec          = 10,
    [int]$MaxMinutes           = 120
)

$LOG      = 'C:\projects\krea2_test\poc_guard.log'
$LLAMA_HC = 'http://localhost:8080/health'

function Write-Log([string]$m) {
    Add-Content -Path $LOG -Value ("[" + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + "] $m") -Encoding ASCII
}

function Stop-Poc([string]$reason) {
    Write-Log "TRIP: $reason -> killing PoC"
    Get-WmiObject Win32_Process |
        Where-Object { $_.CommandLine -like '*poc_logdiag*' -or ($_.Name -eq 'llama-server.exe' -and $_.CommandLine -like '*8090*') -or $_.CommandLine -like '*start8090.bat*' } |
        ForEach-Object {
            Write-Log ("  kill " + $_.Name + " pid=" + $_.ProcessId)
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    Write-Log "TRIP done."
}

Write-Log ("guard start: ws_limit=${PocWorkingSetLimitGB}GB free_floor=${FreeMemFloorGB}GB interval=${IntervalSec}s")

$peakWs   = 0.0
$minFree  = 999.0
$deadline = (Get-Date).AddMinutes($MaxMinutes)

while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds $IntervalSec

    $poc = @(Get-WmiObject Win32_Process -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like '*poc_logdiag*' -and $_.Name -eq 'python.exe' })
    $srv = @(Get-WmiObject Win32_Process -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -eq 'llama-server.exe' -and $_.CommandLine -like '*8090*' })

    # PoC가 이미 끝났으면 가드도 종료
    if ($poc.Count -eq 0 -and $srv.Count -eq 0) { Write-Log "PoC gone - guard exit"; break }

    # ① 하모니시티 LLM health
    $h = $false
    try { $h = ((Invoke-WebRequest -Uri $LLAMA_HC -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200) } catch { $h = $false }
    if (-not $h) { Stop-Poc "harmonicity llama(8080) health != 200"; break }

    # ② 하모니시티 시뮬 생존
    $sim = (Get-WmiObject Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*run_village*' } |
            Measure-Object).Count
    if ($sim -eq 0) { Stop-Poc "harmonicity run_village disappeared"; break }

    # ③ 메모리
    $ws = 0.0
    if ($srv.Count -gt 0) { $ws = [math]::Round(($srv | Measure-Object -Property WorkingSetSize -Sum).Sum / 1GB, 2) }
    $os   = Get-CimInstance Win32_OperatingSystem
    $free = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
    if ($ws   -gt $peakWs)  { $peakWs  = $ws }
    if ($free -lt $minFree) { $minFree = $free }

    Write-Log "sample: poc_ws=${ws}GB free=${free}GB sim=${sim} llama8080=ok"
    if ($ws -ge $PocWorkingSetLimitGB) { Stop-Poc "poc server working set ${ws}GB >= ${PocWorkingSetLimitGB}GB"; break }
    if ($free -le $FreeMemFloorGB)     { Stop-Poc "BACKSTOP: system free ${free}GB <= ${FreeMemFloorGB}GB"; break }
}

Write-Log ("guard end: peak_poc_ws=${peakWs}GB min_free=${minFree}GB")
