@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1
set PATH=C:\Users\leo\ffmpeg\bin;%PATH%
cd /d C:\Users\leo\ace-step-v15

echo [%date% %time%] Waiting for AKMU training to finish... >> C:\Users\leo\ace-step-v15\lokr_artists\train_all.log 2>&1

:wait_loop
timeout /t 60 /nobreak >nul
REM Check if AKMU output has epoch_490+ checkpoint (near completion)
dir "C:\Users\leo\ace-step-v15\lokr_artists\악뮤\output\checkpoints\epoch_*" /b 2>nul | findstr "epoch_49 epoch_500" >nul 2>nul
if errorlevel 1 goto wait_loop

REM Extra wait for final save
timeout /t 30 /nobreak >nul

echo [%date% %time%] AKMU training done. Starting remaining artists... >> C:\Users\leo\ace-step-v15\lokr_artists\train_all.log 2>&1
C:\Users\leo\ace-step-v15\venv\Scripts\python.exe -u C:\Users\leo\ace-step-v15\lokr_train_all.py >> C:\Users\leo\ace-step-v15\lokr_artists\train_all.log 2>&1

echo [%date% %time%] All training complete! >> C:\Users\leo\ace-step-v15\lokr_artists\train_all.log 2>&1
