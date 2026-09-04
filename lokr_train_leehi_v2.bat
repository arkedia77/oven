@echo off
chcp 65001 >nul
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

set VENV_PYTHON=C:\Users\leo\ace-step-v15\venv\Scripts\python.exe
set ACE_DIR=C:\Users\leo\ace-step-v15
set ARTIST_DIR=C:\Users\leo\ace-step-v15\lokr_artists\leehi
set CHECKPOINT=D:\models\ACE-Step-v1.5
set LOGFILE=%ARTIST_DIR%\train.log

echo [%date% %time%] === Lee Hi LoKR Training Start === > "%LOGFILE%"

cd /d %ACE_DIR%

%VENV_PYTHON% -u train.py --yes fixed --checkpoint-dir %CHECKPOINT% --base-model turbo --dataset-dir "%ARTIST_DIR%\tensors" --output-dir "%ARTIST_DIR%\output" --adapter-type lokr --lokr-linear-dim 128 --lokr-linear-alpha 256 --lokr-weight-decompose --lr 1e-4 --epochs 500 --batch-size 2 --gradient-accumulation 2 --scheduler-type cosine --warmup-steps 100 --cfg-ratio 0.15 --shift 3.0 --dropout 0.05 >> "%LOGFILE%" 2>&1

echo [%date% %time%] Training done (exit: %errorlevel%) >> "%LOGFILE%"
