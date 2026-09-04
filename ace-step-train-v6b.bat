@echo off
chcp 65001 >nul
set PATH=C:\Users\leo\ffmpeg\bin;%PATH%
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

if not exist D:\output\piano-lora-v6 mkdir D:\output\piano-lora-v6

echo [%date% %time%] ACE-Step v6 LoRA training start >> D:\output\piano-lora-v6\train.log

cd /d D:\
C:\Users\leo\ace-step-v15\venv\Scripts\python.exe -u C:\Users\leo\ace-step-v15\train.py --yes fixed --checkpoint-dir D:\models\ACE-Step-v1.5 --base-model turbo --dataset-dir D:\data\piano-v6\tensors --output-dir D:\output\piano-lora-v6 --adapter-type lora --rank 64 --alpha 64 --dropout 0.1 --lr 1.5e-4 --batch-size 1 --gradient-accumulation 2 --epochs 300 --save-every 50 --gradient-checkpointing --offload-encoder --optimizer-type adamw --scheduler-type cosine --warmup-steps 100 --log-every 10 >> D:\output\piano-lora-v6\train.log 2>&1

echo [%date% %time%] Training done (exit: %errorlevel%) >> D:\output\piano-lora-v6\train.log
