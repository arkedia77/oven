@echo off
chcp 65001 >nul
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

set VENV_PYTHON=C:\Users\leo\ace-step-v15\venv\Scripts\python.exe
set ACE_DIR=C:\Users\leo\ace-step-v15
set ARTIST_DIR=C:\Users\leo\ace-step-v15\lokr_artists\leehi
set CHECKPOINT=D:\models\ACE-Step-v1.5

if not exist "%ARTIST_DIR%\tensors" mkdir "%ARTIST_DIR%\tensors"
if not exist "%ARTIST_DIR%\output" mkdir "%ARTIST_DIR%\output"

echo [%date% %time%] === Lee Hi LoKR Pipeline Start === >> "%ARTIST_DIR%\train.log"

cd /d %ACE_DIR%

echo [%date% %time%] Step 1: Preprocess >> "%ARTIST_DIR%\train.log"
%VENV_PYTHON% -u train.py --plain fixed --checkpoint-dir %CHECKPOINT% --base-model turbo --preprocess --audio-dir "%ARTIST_DIR%\wav" --tensor-output "%ARTIST_DIR%\tensors" --dataset-dir "%ARTIST_DIR%\tensors" --dataset-json "%ARTIST_DIR%\dataset.json" --output-dir "%ARTIST_DIR%\output" --adapter-type lokr --lokr-linear-dim 128 --lokr-linear-alpha 256 --lokr-weight-decompose --lr 1e-4 --epochs 500 >> "%ARTIST_DIR%\train.log" 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] Preprocess FAILED >> "%ARTIST_DIR%\train.log"
    exit /b 1
)
echo [%date% %time%] Preprocess done >> "%ARTIST_DIR%\train.log"

echo [%date% %time%] Step 2: Train >> "%ARTIST_DIR%\train.log"
echo y | %VENV_PYTHON% -u train.py fixed --checkpoint-dir %CHECKPOINT% --base-model turbo --dataset-dir "%ARTIST_DIR%\tensors" --output-dir "%ARTIST_DIR%\output" --adapter-type lokr --lokr-linear-dim 128 --lokr-linear-alpha 256 --lokr-weight-decompose --lr 1e-4 --epochs 500 --batch-size 2 --gradient-accumulation 2 --scheduler-type cosine --warmup-steps 100 --cfg-ratio 0.15 --shift 3.0 --dropout 0.05 >> "%ARTIST_DIR%\train.log" 2>&1

echo [%date% %time%] Training done (exit: %errorlevel%) >> "%ARTIST_DIR%\train.log"
