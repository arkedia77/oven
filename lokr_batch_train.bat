@echo off
REM LoKR 배치 학습 스크립트 - 벅스 TOP 100 아티스트별
REM 사용법: lokr_batch_train.bat <artist_folder_name>
REM 예: lokr_batch_train.bat akmu

setlocal enabledelayedexpansion

set VENV=C:\Users\leo\ace-step-v15\venv\Scripts\python.exe
set ACE_DIR=C:\Users\leo\ace-step-v15
set BASE_DIR=C:\Users\leo\ace-step-v15\lokr_artists
set MP3_DIR=C:\Users\leo\ace-step-v15\bugs_top100

set ARTIST=%1
if "%ARTIST%"=="" (
    echo Usage: lokr_batch_train.bat ^<artist_folder^>
    exit /b 1
)

set WORK_DIR=%BASE_DIR%\%ARTIST%
echo ============================================================
echo LoKR Training Pipeline: %ARTIST%
echo Work dir: %WORK_DIR%
echo ============================================================

REM Step 1: Create directories
mkdir "%WORK_DIR%\wav" 2>nul
mkdir "%WORK_DIR%\tensors" 2>nul
mkdir "%WORK_DIR%\output" 2>nul
mkdir "%WORK_DIR%\samples" 2>nul

REM Step 2: Convert MP3 to WAV (using ffmpeg)
echo.
echo [Step 2] Converting MP3 to WAV...
set PATH=C:\Users\leo\ffmpeg\bin;%PATH%
for %%f in ("%WORK_DIR%\mp3\*.mp3") do (
    set "BASENAME=%%~nf"
    if not exist "%WORK_DIR%\wav\!BASENAME!.wav" (
        echo   Converting: %%~nf
        ffmpeg -y -i "%%f" -ar 48000 -ac 1 -sample_fmt s16 "%WORK_DIR%\wav\!BASENAME!.wav" -loglevel error
    )
)
echo MP3 to WAV conversion done.

REM Step 3: Preprocess
echo.
echo [Step 3] Preprocessing...
cd /d "%ACE_DIR%"
%VENV% train.py --plain fixed --preprocess --dataset-json "%WORK_DIR%\dataset.json" --audio-dir "%WORK_DIR%\wav" --tensor-dir "%WORK_DIR%\tensors" --yes
echo Preprocessing done.

REM Step 4: Train LoKR
echo.
echo [Step 4] Training LoKR (500 epochs)...
%VENV% train.py --plain fixed --adapter-type lokr --lokr-linear-dim 128 --lokr-linear-alpha 256 --lokr-weight-decompose --lr 1e-4 --epochs 500 --batch-size 2 --gradient-accumulation 2 --scheduler-type cosine --warmup-steps 100 --cfg-ratio 0.15 --shift 3.0 --dropout 0.05 --tensor-dir "%WORK_DIR%\tensors" --output-dir "%WORK_DIR%\output" --yes
echo Training done.

echo.
echo ============================================================
echo Pipeline complete for %ARTIST%
echo Output: %WORK_DIR%\output
echo ============================================================
