@echo off
setlocal enabledelayedexpansion
set BASE=D:\models\Wan2.1-T2V-1.3B-Diffusers
set URL=https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers/resolve/main
set LOG=C:\Users\leo\wan22_repo\dl_progress.txt

echo [%date% %time%] === Download Start === > %LOG%

:: File list: relative_path
set FILES=transformer\diffusion_pytorch_model-00002-of-00002.safetensors
set FILES=%FILES%;vae\diffusion_pytorch_model.safetensors
set FILES=%FILES%;text_encoder\model-00001-of-00005.safetensors
set FILES=%FILES%;text_encoder\model-00002-of-00005.safetensors
set FILES=%FILES%;text_encoder\model-00003-of-00005.safetensors
set FILES=%FILES%;text_encoder\model-00004-of-00005.safetensors
set FILES=%FILES%;text_encoder\model-00005-of-00005.safetensors

for %%F in (%FILES%) do (
    echo [%date% %time%] Downloading %%F ... >> %LOG%
    :retry_%%F
    curl -L -C - --retry 10 --retry-delay 5 --retry-max-time 3600 -o "%BASE%\%%F" "%URL%/%%F"
    if errorlevel 1 (
        echo [%date% %time%] RETRY %%F >> %LOG%
        timeout /t 10 /nobreak >nul
        curl -L -C - --retry 10 --retry-delay 5 --retry-max-time 3600 -o "%BASE%\%%F" "%URL%/%%F"
    )
    echo [%date% %time%] DONE %%F >> %LOG%
)

echo [%date% %time%] === All Downloads Complete === >> %LOG%

:: Run video generation
echo [%date% %time%] Starting video generation... >> %LOG%
C:\Users\leo\liszt\venv\Scripts\python.exe -u C:\Users\leo\wan22_repo\dl_wan_1_3b.py >> %LOG% 2>&1

echo [%date% %time%] === ALL DONE === >> %LOG%
