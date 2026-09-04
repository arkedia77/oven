@echo off
chcp 65001 >nul
set PATH=C:\Users\leo\ffmpeg\bin;%PATH%
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

echo ============================================
echo  ACE-Step 1.5 Crush v2 Preprocessing
echo  2-pass: VAE+TextEnc -> DiT Enc
echo ============================================

if not exist C:\Users\leo\ace-step-v15\crush_v2_tensors mkdir C:\Users\leo\ace-step-v15\crush_v2_tensors
if not exist C:\Users\leo\ace-step-v15\crush_v2_output mkdir C:\Users\leo\ace-step-v15\crush_v2_output

echo [%date% %time%] Preprocessing start >> C:\Users\leo\ace-step-v15\crush_v2_output\preprocess.log

cd /d C:\Users\leo\ace-step-v15

C:\Users\leo\ace-step-v15\venv\Scripts\python.exe -u C:\Users\leo\ace-step-v15\train.py --yes fixed --checkpoint-dir D:\models\ACE-Step-v1.5 --base-model turbo --preprocess --audio-dir C:\Users\leo\ace-step-v15\crush_v2_data --tensor-output C:\Users\leo\ace-step-v15\crush_v2_tensors --dataset-dir C:\Users\leo\ace-step-v15\crush_v2_tensors --dataset-json C:\Users\leo\ace-step-v15\crush_v2_data\dataset.json --output-dir C:\Users\leo\ace-step-v15\crush_v2_output --adapter-type lokr --lokr-linear-dim 128 --lokr-linear-alpha 256 --lokr-weight-decompose --lr 1e-4 --epochs 500 --yes >> C:\Users\leo\ace-step-v15\crush_v2_output\preprocess.log 2>&1

echo [%date% %time%] Preprocessing done (exit: %errorlevel%) >> C:\Users\leo\ace-step-v15\crush_v2_output\preprocess.log
echo Preprocessing complete! Check crush_v2_output\preprocess.log
pause
