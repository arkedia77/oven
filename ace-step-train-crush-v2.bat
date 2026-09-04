@echo off
chcp 65001 >nul
set PATH=C:\Users\leo\ffmpeg\bin;%PATH%
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

echo ============================================
echo  ACE-Step 1.5 LoKR Crush v2 Training
echo  20 curated tracks (FANG + FMTS albums)
echo  500 epochs, LR 1e-4, dim 128
echo ============================================

if not exist C:\Users\leo\ace-step-v15\crush_v2_output mkdir C:\Users\leo\ace-step-v15\crush_v2_output

echo [%date% %time%] Crush v2 LoKR training start >> C:\Users\leo\ace-step-v15\crush_v2_output\train.log

cd /d C:\Users\leo\ace-step-v15

echo y | C:\Users\leo\ace-step-v15\venv\Scripts\python.exe -u C:\Users\leo\ace-step-v15\train.py --plain fixed --checkpoint-dir D:\models\ACE-Step-v1.5 --base-model turbo --dataset-dir C:\Users\leo\ace-step-v15\crush_v2_tensors --output-dir C:\Users\leo\ace-step-v15\crush_v2_output --adapter-type lokr --lokr-linear-dim 128 --lokr-linear-alpha 256 --lokr-weight-decompose --lr 1e-4 --batch-size 2 --gradient-accumulation 2 --epochs 500 --save-every 100 --gradient-checkpointing --optimizer-type adamw --scheduler-type cosine --warmup-steps 100 --weight-decay 0.01 --shift 3.0 --cfg-ratio 0.15 --dropout 0.05 --log-every 10 >> C:\Users\leo\ace-step-v15\crush_v2_output\train.log 2>&1

echo [%date% %time%] Training done (exit: %errorlevel%) >> C:\Users\leo\ace-step-v15\crush_v2_output\train.log
