# 하모니시티 시뮬레이션 watchdog v2 (A-089, 2026-08-04)
#
# ★ v1의 결함 — 판정이 아니라 "조치"가 무통지로 실패했다.
#   2026-08-03 23:55 킬스위치 정지 후 13h40m 미복구 사고의 실측:
#     · v1의 탐지는 정상이었다(python.exe + 명령줄 `*run_village*` 매칭). procs=0을 매번 맞게 봤다.
#     · v1은 00:00:02 ~ 13:40:02 사이 `schtasks /Run`을 165회 발신하고 165회 전부 실패했는데
#       한 번도 실패를 알지 못했다. → `schtasks /Run`은 실행이 거부돼도 exit code 0(SUCCESS)를
#       반환하며(실측: "INFO: ... is currently running." + errorlevel 0, Last Result 0x800710E0),
#       v1은 그 출력을 `| Out-Null`로 버렸다.
#   ⇒ 판정 축이 「존재」인 것(kee A-089)에 더해, 조치 축이 「명령을 보냈다」이지 「복구됐다」가 아니었다.
#
# v2의 두 축:
#   ① 진행 판정 — sim.log의 Tick 번호 증가(주) + 파일 길이 증가(보조)로 「진행」을 잰다.
#      프로세스 존재(명령줄 매칭)는 보조 축으로 병행(kee: 배타 아님). halt로 멈춘 프로세스는
#      존재 판정을 통과하므로 진행 판정이 주(主)여야 한다.
#   ② 조치 검증 — 조치 후 다음 사이클에 복구를 확인한다. 미복구면 에스컬레이션(/End → /Run)하고
#      schtasks의 표준출력을 로그에 남긴다(exit code는 신뢰 불가). 연속 실패는 ALERT로 격상.
#
# 임계 STALL_THRESHOLD_SEC는 손으로 고르지 않는다 — tick 간격 실측 p95의 배수. 산출 근거는
# WATCHDOG_THRESHOLD.md 참조.
#
# 로그 문자열은 전부 ASCII (PowerShell 5.1 + 콘솔 코드페이지에서 한글이 깨지므로).

$ErrorActionPreference = 'Continue'

$ROOT       = 'C:\projects\harmonicity'
$SIM_LOG    = "$ROOT\sim.log"
$LOG        = "$ROOT\healthcheck.log"
$BEAT       = "$ROOT\healthcheck_heartbeat.txt"
$STATE      = "$ROOT\healthcheck_state.json"
$ALERT      = "$ROOT\healthcheck_ALERT.txt"
$TASK       = 'HarmonicityP11'
$LLAMA_URL  = 'http://localhost:8080/health'

# --- 임계: tick 간격 실측 p95 x k (WATCHDOG_THRESHOLD.md) ---
$STALL_THRESHOLD_SEC = 900

# ★ /End 에스컬레이션 — kee 조건부 승인(2026-08-04, A-089 ⒝). 조건 3:
#   ⑴ /End는 STALLED 판정에만 → ★2026-08-04 16:29 kee 개정 승인으로 「DEAD_PROC ∧ 태스크 Running」 추가(아래)
#   ⑵ 상태 저장 확인 후 실행(무손실 확인)  ⑶ 실증 1회는 kee 통지 후·감독 하에
$ENABLE_END_ESCALATION = $true

# ★★ 조건⑴ 개정 — kee 승인(2026-08-04 16:29, A-089).
#   kee 원 사유 「DEAD_PROC엔 불요(이미 프로세스가 없음)」는 python 기준으로는 맞으나,
#   `/End`가 끝내는 것은 python이 아니라 **태스크**다. 2026-08-03 사고의 기제는
#   「python은 죽었는데(procs=0) 태스크가 Running에 묶여 `/Run`이 165회 거부」였고 이는
#   **DEAD_PROC 판정**이다 — 조건⑴을 그대로 두면 에스컬레이션이 정작 그 사고를 못 덮는다.
#   ⇒ **DEAD_PROC이면서 태스크 상태가 Running일 때만** /End 허용. 그 조건에선 죽일 python이
#   없으므로 손실 0이고, /End의 목적이 「묶인 태스크 해제」 하나로 좁혀진다.
$END_ON_STUCK_TASK = $true

$ts  = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

function Write-Log([string]$msg) { Add-Content -Path $LOG -Value "[$ts] $msg" -Encoding ASCII }

# --- 1. 진행 신호 수집: sim.log 꼬리에서 Tick 번호 + 파일 길이 ---
$tick = -1
$flen = -1
try {
    $fi   = Get-Item $SIM_LOG -ErrorAction Stop
    $flen = $fi.Length
    $from = [Math]::Max(0, $flen - 40960)
    $fs   = New-Object IO.FileStream($SIM_LOG, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    $null = $fs.Seek($from, [IO.SeekOrigin]::Begin)
    $buf  = New-Object byte[] ($flen - $from)
    $null = $fs.Read($buf, 0, $buf.Length)
    $fs.Close()
    $m = [regex]::Matches([Text.Encoding]::UTF8.GetString($buf), 'Tick (\d+)')
    if ($m.Count -gt 0) { $tick = [int]$m[$m.Count - 1].Groups[1].Value }
} catch {
    Write-Log "WARN sim.log read failed: $($_.Exception.Message)"
}

# --- 2. 보조 축: run_village 프로세스 존재(명령줄 매칭) ---
$procs = (Get-WmiObject Win32_Process -ErrorAction SilentlyContinue |
          Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*run_village*' } |
          Measure-Object).Count

# --- 3. 상태 로드 ---
$st = $null
if (Test-Path $STATE) { try { $st = Get-Content $STATE -Raw | ConvertFrom-Json } catch { $st = $null } }
if ($null -eq $st) {
    $st = [pscustomobject]@{ last_tick = $tick; last_flen = $flen; last_progress_epoch = $now
                             down_streak = 0; last_action = 'none'; last_action_epoch = 0 }
}

$progressed = ($tick -gt $st.last_tick) -or ($flen -gt $st.last_flen)
$stall      = $now - [int64]$st.last_progress_epoch

# 진행이 있었으면 진행 기록은 판정과 무관하게 항상 갱신한다(정체 시간이 부풀지 않게).
if ($progressed) { $st.last_tick = $tick; $st.last_flen = $flen; $st.last_progress_epoch = $now }

# --- 4. 판정 ---
# ★ 존재 축이 진행 축에 가려지면 안 된다. 2026-08-04 FAIL 표본에서 실제로 가려졌다:
#   프로세스를 죽인 직후 사이클에서, 죽기 직전 기록된 틱이 「직전 폴 대비 증가」로 잡혀
#   procs=0인데 verdict=OK가 나왔다(탐지 1주기 5분 지연). ⇒ 존재 판정을 먼저 본다.
#   ★이 결함은 FAIL 표본을 돌렸기 때문에 잡혔다 — 표본 없이 켰으면 매 사이클 PASS로 보였을 것.
if     ($procs -eq 0)                      { $verdict = 'DEAD_PROC' }
elseif ($progressed)                       { $verdict = 'OK' }
elseif ($stall -ge $STALL_THRESHOLD_SEC)   { $verdict = 'STALLED' }
else                                       { $verdict = 'OK_TOLERANCE' }

# 복구 선언은 「진행」이 관측될 때만 한다 — 프로세스가 떠 있는 것만으로는 복구가 아니다.
# (재기동 직후 모델 로드 등으로 아직 틱이 없으면 OK_TOLERANCE로 두고 streak을 유지 → 재발신 없음)
if ($verdict -eq 'OK') {
    if ([int]$st.down_streak -gt 0) {
        Write-Log ("RECOVERED tick={0} after attempts={1} stall={2}s (last_action={3})" -f $tick, $st.down_streak, $stall, $st.last_action)
        if (Test-Path $ALERT) { Remove-Item $ALERT -Force -ErrorAction SilentlyContinue }
    }
    $st.down_streak = 0; $st.last_action = 'none'
}

# --- 5. 조치 + 조치 검증 ---
if ($verdict -eq 'DEAD_PROC' -or $verdict -eq 'STALLED') {
    $st.down_streak = [int]$st.down_streak + 1
    $streak = [int]$st.down_streak

    # llama가 죽어 있으면 launch_p11.bat의 WAITLLM 대기가 정상 동작이다 -> End 금지(2026-07-22 사고 계열).
    $llamaOk = $false
    try { $llamaOk = ((Invoke-WebRequest -Uri $LLAMA_URL -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200) } catch { $llamaOk = $false }

    $sLine  = schtasks /Query /TN $TASK /FO LIST 2>&1 | Select-String 'Status:' | Select-Object -First 1
    $before = if ($sLine) { ($sLine.ToString() -replace '\s+', ' ').Trim() } else { 'Status:UNKNOWN' }

    # 조건⑵ 상태 저장 확인 — run_tick이 매 틱 save_all()을 부르므로(village/main.py:266)
    # world_state.json의 갱신 경과가 곧 「마지막 저장 이후 경과」다. /End 전에 반드시 로그에 남긴다.
    $saveAge = -1
    try { $saveAge = [int]((Get-Date) - (Get-Item "$ROOT\data\world_state.json").LastWriteTime).TotalSeconds } catch {}

    $stuckTask = ($before -like '*Running*')
    $mayEnd = $ENABLE_END_ESCALATION -and $llamaOk -and ($streak -ge 2) -and ($saveAge -ge 0) -and (
                ($verdict -eq 'STALLED') -or ($verdict -eq 'DEAD_PROC' -and $stuckTask -and $END_ON_STUCK_TASK))

    if ($mayEnd) {
        $act = 'END_THEN_RUN'
        $o1  = (schtasks /End /TN $TASK 2>&1) -join ' | '
        Start-Sleep -Seconds 5
        $o2  = (schtasks /Run /TN $TASK 2>&1) -join ' | '
        $out = "END[$o1] RUN[$o2]"
    } else {
        # ★라벨은 실제로 보류된 경우에만 «HELD»를 붙인다. 태스크가 Ready면 /End는 보류가 아니라
        #   «해당 없음»이고(묶인 태스크가 없으므로), 거기에 HELD를 붙이면 이름이 사실을 왜곡한다.
        $act = if ($streak -ge 2 -and $llamaOk -and $stuckTask -and -not $END_ON_STUCK_TASK) { 'RUN(END_HELD_STUCKTASK)' }
               elseif ($streak -ge 2 -and $llamaOk -and -not $ENABLE_END_ESCALATION)         { 'RUN(END_DISABLED)' }
               else                                                                          { 'RUN' }
        $out = "RUN[" + (((schtasks /Run /TN $TASK 2>&1) -join ' | ')) + "]"
    }

    $st.last_action = $act; $st.last_action_epoch = $now
    Write-Log ("{0} tick={1} procs={2} stall={3}s streak={4} llama_ok={5} save_age={6}s before=[{7}] action={8} out={9}" -f `
               $verdict, $tick, $procs, $stall, $streak, $llamaOk, $saveAge, $before, $act, $out)

    if ($streak -ge 4) {
        $msg = "ALERT: $streak consecutive failed remediations. verdict=$verdict stall=${stall}s tick=$tick procs=$procs llama_ok=$llamaOk last_action=$act"
        Write-Log $msg
        Set-Content -Path $ALERT -Value "[$ts] $msg" -Encoding ASCII
    }
}

# --- 6. 상태/하트비트 ---
$st | ConvertTo-Json -Compress | Set-Content -Path $STATE -Encoding ASCII
Set-Content -Path $BEAT -Value "[$ts] v2 verdict=$verdict tick=$tick procs=$procs stall=${stall}s streak=$($st.down_streak)" -Encoding ASCII
