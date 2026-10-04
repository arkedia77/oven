# leowin2 → NAS 백업 (oven 관리 · manifest = infra/leowin2_backup_manifest.md)
# ⚠배포 시 UTF-8 BOM 으로 저장(Windows PowerShell 5.1 은 BOM 없는 파일을 ANSI 로 읽음 — 주석 한글만 영향) · 10-04 ParseFile 0 errors(leowin2)
# 실행: 예약 작업(매일 04:00) 또는 수동 `powershell -NoProfile -File C:\scripts\leowin2_backup.ps1 [-DryRun]`
# 삭제 방어는 NAS 스냅샷이 맡는다 — robocopy /MIR 은 «최신 동기»만 (원본 삭제가 사본에도 번진다).
# 로그·결과는 C: 가 아니라 NAS 쪽에 쓴다(성공도 기록 — 성공 0 줄 = 「안 돌았다」).
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'

$Share   = '\\172.30.1.41\leowin_backup'   # admin 174649: 별도 공유(스냅샷이 공유 단위라 leofamily 하위 금지)
$Dest    = "$Share\leowin2"
$CredXml = 'C:\scripts\leowin_bk.cred.xml'   # Export-Clixml(PSCredential) — 그 계정 DPAPI 로만 풀림. 값은 vault 경로만 기록.
$Stamp   = Get-Date -Format 'yyyyMMdd_HHmmss'

# 루트별 제외 — manifest «뺄 것»과 1:1. 경로는 루트 기준 상대(/XD 는 이름 또는 전체 경로).
$Jobs = @(
  @{ Src='C:\Users\leowin2.DESKTOP-KSKH97R'; Name='home_leowin2.DESKTOP';
     XD=@('egmd\.venv','bp_train\.venv','egmd\s1\input','egmd\s1\s1b_train','bp_train\smoke','egmd\ckpt','egmd\magenta-2.1.4','bp_train\basic-pitch-0.4.0','.local','AppData\Roaming\uv\python','.cache\huggingface','AppData\Local\Temp','AppData\Local\Microsoft\Windows\INetCache');
     XF=@('*.tfrecord','C:\Users\leowin2.DESKTOP-KSKH97R\egmd\magenta.zip','C:\Users\leowin2.DESKTOP-KSKH97R\egmd\ckpt.zip','C:\Users\leowin2.DESKTOP-KSKH97R\bp_train\bp.zip') },  # zip 은 3070 이 명시한 3개만(전역 *.zip 금지)
  @{ Src='C:\Users\leo.LEOWIN2'; Name='home_leo.LEOWIN2';
     XD=@('lora_stage','.cache','AppData\Local\Temp','AppData\Local\Microsoft\Windows\INetCache'); XF=@() },
  @{ Src='C:\Users\leowin2'; Name='leowin2_projects';
     XD=@('ACE-Step-1.5\.venv','ACE-Step-1.5\checkpoints','fish-speech\.venv','fish-speech\checkpoints'); XF=@() },
  @{ Src='C:\RVC'; Name='RVC';
     # ⚠ G_*.pth·D_*.pth 는 3070 NAS 이관 완료 뒤에만 XF 에 추가(manifest)
     XD=@('.venv','venv','rvc\models','ffmpeg_temp','sliced_audios','sliced_audios_16k','f0','f0_voiced','extracted','eval'); XF=@() },
  @{ Src='C:\so-vits-svc-fork'; Name='so-vits-svc-fork'; XD=@('.venv'); XF=@() },
  @{ Src='C:\amt_tools'; Name='amt_tools';
     XD=@('hitmaking_gpu\venv','venv','omnizart_env','YourMT3','YourMT3_spaces','YourMT3_code','hf_cache','test_audio'); XF=@() }
  # SongFormer: 가중치 제외·*.log 만 포함 → 별도 잡(아래)
)

$cred = Import-Clixml $CredXml
$null = net use $Share /delete /y 2>$null
net use $Share $cred.GetNetworkCredential().Password /user:$($cred.UserName) /persistent:no | Out-Null
try {
  $LogDir = "$Dest\_logs"; New-Item -ItemType Directory -Force $LogDir | Out-Null
  $summary = @()
  foreach ($j in $Jobs) {
    $xd = $j.XD | ForEach-Object { Join-Path $j.Src $_ }
    $ra = @($j.Src, "$Dest\$($j.Name)", '/MIR', '/R:1', '/W:1', '/NP', '/FFT', '/XJ', "/LOG:$LogDir\$Stamp`_$($j.Name).log")
    if ($xd)      { $ra += '/XD'; $ra += $xd }
    if ($j.XF)    { $ra += '/XF'; $ra += $j.XF }
    if ($DryRun)  { $ra += '/L' }
    & robocopy @ra | Out-Null
    $rc = $LASTEXITCODE
    $summary += [pscustomobject]@{ job=$j.Name; rc=$rc; ok=($rc -lt 8) }
  }
  # SongFormer 는 *.log 만
  & robocopy 'C:\amt_tools\SongFormer' "$Dest\amt_tools_SongFormer_logs" '*.log' '/R:1' '/W:1' '/NP' "/LOG:$LogDir\$Stamp`_SongFormer_logs.log" $(if ($DryRun) { '/L' }) | Out-Null
  $summary += [pscustomobject]@{ job='SongFormer_logs'; rc=$LASTEXITCODE; ok=($LASTEXITCODE -lt 8) }

  $allOk = -not ($summary | Where-Object { -not $_.ok })
  $line = '{0} {1} {2} {3}' -f $Stamp, $(if ($DryRun) { 'DRYRUN' } else { 'RUN' }), $(if ($allOk) { 'OK' } else { 'FAIL' }), (($summary | ForEach-Object { "$($_.job)=$($_.rc)" }) -join ' ')
  Add-Content -Path "$LogDir\_results.txt" -Value $line   # 성공도 기록
  $line
  if (-not $allOk) { exit 8 }
} finally {
  net use $Share /delete /y | Out-Null
}
