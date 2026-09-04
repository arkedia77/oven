@echo off
chcp 65001 >nul
set PATH=C:\Users\leo\ffmpeg\bin;%PATH%
set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8
cd /d C:\Users\leo\ace-step-v15
C:\Users\leo\ace-step-v15\venv\Scripts\python.exe -u C:\Users\leo\ace-step-v15\gen_crush_v2_test.py > C:\Users\leo\ace-step-v15\crush_v2_samples\inference.log 2>&1
