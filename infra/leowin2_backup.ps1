# leowin2 → NAS 백업 (oven 관리 · manifest = infra/leowin2_backup_manifest.md)
# ⛔이 파일은 UTF-8 **BOM 포함**으로 유지 — PS 5.1 은 BOM 없으면 CP949 로 읽어 한글 주석이 줄바꿈을 삼킨다(10-04 실측: BOM 없이 파싱 오류 6, BOM 넣고 0). 「주석만 영향」이라던 앞 기재는 틀렸음.
# 실행: 예약 작업(매일 04:00) 또는 수동 `powershell -NoProfile -File C:\scripts\leowin2_backup.ps1 [-DryRun]`
# 삭제 방어는 NAS 스냅샷이 맡는다 — robocopy /MIR 은 «최신 동기»만 (원본 삭제가 사본에도 번진다).
# 로그·결과는 C: 가 아니라 NAS 쪽에 쓴다(성공도 기록 — 성공 0 줄 = 「안 돌았다」).
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'

$Share   = '\\172.30.1.41\leowin_backup'   # admin 174649: 별도 공유(스냅샷이 공유 단위라 leofamily 하위 금지)
$Dest    = "$Share\leowin2"
$CredBin = 'C:\ProgramData\oven_backup\leowin_bk.bin'   # DPAPI LocalMachine 암호화 · ACL = SYSTEM·Administrators 만 · 원본 = mukl ~/vault/nas_leowin_bk.txt(값은 어디에도 안 적음)
$BkUser  = 'leowin_bk'
$Stamp   = Get-Date -Format 'yyyyMMdd_HHmmss'

# 루트별 제외 — manifest «뺄 것»과 1:1. 경로는 루트 기준 상대(/XD 는 이름 또는 전체 경로).
$Jobs = @(
  @{ Src='C:\Users\leowin2.DESKTOP-KSKH97R'; Name='home_leowin2.DESKTOP';
     XD=@('egmd\.venv','bp_train\.venv','egmd\s1\input','egmd\s1\s1b_train','bp_train\smoke','egmd\ckpt','egmd\magenta-2.1.4','bp_train\basic-pitch-0.4.0','.local','AppData\Roaming\uv\python','.cache\huggingface','AppData\Local\Temp','AppData\Local\Microsoft\Windows\INetCache');
     XF=@('*.tfrecord','C:\Users\leowin2.DESKTOP-KSKH97R\egmd\magenta.zip','C:\Users\leowin2.DESKTOP-KSKH97R\egmd\ckpt.zip','C:\Users\leowin2.DESKTOP-KSKH97R\bp_train\bp.zip') },  # zip 은 3070 이 명시한 3개만(전역 *.zip 금지)
  @{ Src='C:\Users\leo.LEOWIN2'; Name='home_leo.LEOWIN2';
     XD=@('lora_stage','.cache','AppData\Local\Temp','AppData\Local\Microsoft\Windows\INetCache'); XF=@() },
  @{ Src='C:\Users\leowin2'; Name='leowin2_projects';
     XD=@('ACE-Step-1.5\.venv','ACE-Step-1.5\checkpoints','fish-speech\.venv','fish-speech\checkpoints','arena_tts_test\.venv','GPT-SoVITS'); XF=@() },  # vocia 203553: GPT-SoVITS=설치본뿐·arena .venv 재설치
  @{ Src='C:\RVC'; Name='RVC';
     # ⚠ G_*.pth·D_*.pth 는 3070 NAS 이관 완료 뒤에만 XF 에 추가(manifest)
     XD=@('.venv','venv','rvc\models','ffmpeg_temp','sliced_audios','sliced_audios_16k','f0','f0_voiced','extracted','eval'); XF=@() },
  @{ Src='C:\so-vits-svc-fork'; Name='so-vits-svc-fork'; XD=@('.venv'); XF=@() },
  @{ Src='C:\amt_tools'; Name='amt_tools';
     XD=@('hitmaking_gpu\venv','venv','omnizart_env','YourMT3','YourMT3_spaces','YourMT3_code','hf_cache','test_audio'); XF=@() }
  # SongFormer: 가중치 제외·*.log 만 포함 → 별도 잡(아래)
)

Add-Type -AssemblyName System.Security
$pw = [Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($CredBin), $null, 'LocalMachine'))
Remove-SmbMapping -RemotePath $Share -Force -ErrorAction SilentlyContinue   # cmdlet 사용: 비밀번호가 명령줄(프로세스 목록)에 안 남고, PS 5.1 네이티브 stderr+Stop 중단도 없음
New-SmbMapping -RemotePath $Share -UserName $BkUser -Password $pw -Persistent $false | Out-Null
Remove-Variable pw
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
  Remove-SmbMapping -RemotePath $Share -Force -ErrorAction SilentlyContinue
}
