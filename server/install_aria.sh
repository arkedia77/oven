#!/bin/bash
# ============================================
# Aria (Liszt) 파인튜닝 환경 설치
# 5090 서버에서 SSH 접속 후 실행
# ============================================
set -e

WORK_DIR="C:/liszt"
cd "$WORK_DIR"

echo "=== Liszt Engine - Aria 설치 시작 ==="

# 1. Python 가상환경
echo "[1/6] Python venv 생성..."
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
# venv\Scripts\activate       # Windows CMD

# 2. PyTorch + CUDA (RTX 5090 = sm_120, CUDA 12.8+)
echo "[2/6] PyTorch 설치 (CUDA 12.8)..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 3. Aria 생성 모델 클론
echo "[3/6] Aria 생성 모델 클론..."
if [ ! -d "aria" ]; then
    git clone https://github.com/EleutherAI/aria.git
fi
cd aria
pip install -e .
cd ..

# 4. 추가 의존성
echo "[4/6] 추가 패키지 설치..."
pip install wandb accelerate safetensors transformers datasets
pip install huggingface_hub

# 5. 모델 체크포인트 다운로드
echo "[5/6] Aria 체크포인트 다운로드..."
mkdir -p checkpoints
python -c "
from huggingface_hub import hf_hub_download
import os

ckpt_dir = 'checkpoints'

# aria-medium-base (사전학습 모델)
print('Downloading aria-medium-base...')
hf_hub_download(
    repo_id='loubb/aria-medium-base',
    filename='model.safetensors',
    local_dir=os.path.join(ckpt_dir, 'aria-medium-base')
)

# aria-medium-gen (생성 파인튜닝 모델)
print('Downloading aria-medium-gen...')
hf_hub_download(
    repo_id='loubb/aria-medium-gen',
    filename='model.safetensors',
    local_dir=os.path.join(ckpt_dir, 'aria-medium-gen')
)

print('Done!')
"

# 6. 환경 확인
echo "[6/6] 환경 확인..."
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
    print(f'CUDA version: {torch.version.cuda}')
"

echo ""
echo "=== 설치 완료 ==="
echo "작업 디렉토리: $WORK_DIR"
echo "Aria 코드: $WORK_DIR/aria"
echo "체크포인트: $WORK_DIR/checkpoints/"
echo ""
echo "다음: python test_aria.py 로 생성 테스트"
