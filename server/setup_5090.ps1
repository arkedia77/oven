# ============================================
# 5090 서버 초기 셋업 (Windows PowerShell)
# Leo가 RDP 접속 후 PowerShell(관리자)에서 실행
# ============================================

Write-Host "=== 5090 Server Setup ===" -ForegroundColor Cyan

# 1. OpenSSH 서버 설치 & 시작
Write-Host "`n[1/5] OpenSSH 서버 설치..." -ForegroundColor Yellow
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# 방화벽 규칙 (이미 있으면 스킵)
$rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
if (-not $rule) {
    New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}
Write-Host "  SSH 서버 활성화 완료" -ForegroundColor Green

# 2. GPU 확인
Write-Host "`n[2/5] GPU 확인..." -ForegroundColor Yellow
nvidia-smi

# 3. Python 확인 / 설치 안내
Write-Host "`n[3/5] Python 확인..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if ($py) {
    python --version
    pip --version
} else {
    Write-Host "  Python 미설치 - winget으로 설치합니다..." -ForegroundColor Red
    winget install Python.Python.3.11
    Write-Host "  설치 후 터미널 재시작 필요" -ForegroundColor Yellow
}

# 4. CUDA 확인
Write-Host "`n[4/5] CUDA 확인..." -ForegroundColor Yellow
nvcc --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  CUDA toolkit 미설치 - PyTorch가 자체 CUDA 번들 사용 가능" -ForegroundColor Yellow
}

# 5. 작업 디렉토리 생성
Write-Host "`n[5/5] 작업 디렉토리 생성..." -ForegroundColor Yellow
$workDir = "C:\liszt"
if (-not (Test-Path $workDir)) {
    New-Item -ItemType Directory -Path $workDir
}
Write-Host "  작업 디렉토리: $workDir" -ForegroundColor Green

# 결과 요약
Write-Host "`n=== 셋업 완료 ===" -ForegroundColor Cyan
Write-Host "SSH 접속 테스트: ssh leo@op.nbase.io -p 33899" -ForegroundColor White
Write-Host "또는 포트포워딩 확인 후: ssh leo@op.nbase.io -p <ssh-port>" -ForegroundColor White
Write-Host "`n다음 단계: Claude가 SSH로 접속하여 Aria 환경 자동 설치" -ForegroundColor White
