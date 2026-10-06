# leowin → NAS 백업 (oven 관리 · manifest = infra/leowin_backup_manifest.md)
# ⛔이 파일은 UTF-8 **BOM 포함**으로 유지 — PS 5.1 은 BOM 없으면 CP949 로 읽어 한글 주석·한글 경로가 깨진다(leowin2 10-04 실측).
# 실행: 예약 작업 또는 수동 `powershell -NoProfile -File C:\scripts\leowin_backup.ps1 [-DryRun] [-Ipg <ms>]`
# 삭제 방어는 NAS 스냅샷이 맡는다 — robocopy /MIR 은 «최신 동기»만 (원본 삭제가 사본에도 번진다).
# 로그·결과는 C: 가 아니라 NAS 쪽에 쓴다(성공도 기록 — 성공 0 줄 = 「안 돌았다」).
# leowin2 판과 다른 점: «확실히 지킬 것만»(LEO 10-04) → 루트 전체가 아니라 manifest «포함» 경로만 · RVC 는 파일 패턴 지정(Files).
param([switch]$DryRun, [int]$Ipg = 0)   # -Ipg = robocopy /IPG(패킷 간 ms). leowin 은 USB 무선(10-06 실측 Realtek 8812BU) — 첫 ≈230GB 가 다른 사용을 막으면 지정
$ErrorActionPreference = 'Stop'

$Share   = '\\172.30.1.41\leowin_backup'
$Dest    = "$Share\leowin"
$CredBin = 'C:\ProgramData\oven_backup\leowin_bk.bin'   # DPAPI LocalMachine 암호화 · ACL = SYSTEM·Administrators 만 · 원본 = mukl ~/vault/nas_leowin_bk.txt(값은 어디에도 안 적음)
$BkUser  = 'leowin_bk'
$Stamp   = Get-Date -Format 'yyyyMMdd_HHmmss'

# manifest «포함»과 1:1. Files 가 있으면 그 패턴만 복사(없으면 전체).
$RvcFiles = @('*e_*s.pth','*.index','config.json','model_info.json','training_data.json')   # 실제 이름 = gummy_100e_4500s.pth 꼴(10-06 실측)
$RvcXD    = @('eval','extracted','f0','f0_voiced','sliced_audios','sliced_audios_16k')
$Jobs = @(
  @{ Src='E:\work';              Name='E_work';            XD=@(); XF=@() },
  @{ Src='E:\사진';              Name='E_사진';            XD=@(); XF=@() },
  @{ Src='E:\어머니 사진 백업';  Name='E_어머니_사진_백업'; XD=@(); XF=@() },
  @{ Src='E:\leo1_backup';       Name='E_leo1_backup';     XD=@(); XF=@() },
  @{ Src='E:\backup_c';          Name='E_backup_c';        XD=@(); XF=@() },
  @{ Src='E:\temp_keygen';       Name='E_temp_keygen';     XD=@(); XF=@() },
  @{ Src='C:\RVC\logs\gummy';        Name='RVC_logs_gummy';        Files=$RvcFiles; XD=$RvcXD; XF=@('G_*.pth','D_*.pth') },   # G/D 제외 = vocia 224705 동의
  @{ Src='C:\RVC\logs\sung_sikyung'; Name='RVC_logs_sung_sikyung'; Files=$RvcFiles; XD=$RvcXD; XF=@('G_*.pth','D_*.pth') }
)

Add-Type -AssemblyName System.Security
$pw = [Text.Encoding]::UTF8.GetString([Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($CredBin), $null, 'LocalMachine'))
# New-PSDrive -Credential: 비밀번호가 명령줄에 안 남음. ⛔New-SmbMapping 은 ssh·서비스 세션에서 오류 1312(로그온 세션 없음) — 10-04 실측
$cred = New-Object System.Management.Automation.PSCredential($BkUser, (ConvertTo-SecureString $pw -AsPlainText -Force)); Remove-Variable pw
Get-PSDrive OVBK -ErrorAction SilentlyContinue | Remove-PSDrive -Force
New-PSDrive -Name OVBK -PSProvider FileSystem -Root $Share -Credential $cred | Out-Null
try {
  $LogDir = "$Dest\_logs"; New-Item -ItemType Directory -Force $LogDir | Out-Null
  $summary = @()
  foreach ($j in $Jobs) {
    if (-not (Test-Path -LiteralPath $j.Src)) { $summary += [pscustomobject]@{ job=$j.Name; rc=16; ok=$false }; continue }   # 원본 없음 = FAIL(빈 원본을 /MIR 하면 사본이 지워진다)
    $xd = $j.XD | ForEach-Object { Join-Path $j.Src $_ }
    $ra = @($j.Src, "$Dest\$($j.Name)")
    if ($j.Files) { $ra += $j.Files }
    $ra += @('/MIR', '/R:1', '/W:1', '/NP', '/FFT', '/XJ', "/LOG:$LogDir\$Stamp`_$($j.Name).log")
    if ($xd)      { $ra += '/XD'; $ra += $xd }
    if ($j.XF)    { $ra += '/XF'; $ra += $j.XF }
    if ($Ipg -gt 0) { $ra += "/IPG:$Ipg" }
    if ($DryRun)  { $ra += '/L' }
    & robocopy @ra | Out-Null
    $rc = $LASTEXITCODE
    $summary += [pscustomobject]@{ job=$j.Name; rc=$rc; ok=($rc -lt 8) }
  }

  $allOk = -not ($summary | Where-Object { -not $_.ok })
  $line = '{0} {1} {2} {3}' -f $Stamp, $(if ($DryRun) { 'DRYRUN' } else { 'RUN' }), $(if ($allOk) { 'OK' } else { 'FAIL' }), (($summary | ForEach-Object { "$($_.job)=$($_.rc)" }) -join ' ')
  Add-Content -Path "$LogDir\_results.txt" -Value $line   # 성공도 기록
  $line
  if (-not $allOk) { exit 8 }
} finally {
  Remove-PSDrive OVBK -Force -ErrorAction SilentlyContinue
}
