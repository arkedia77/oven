#!/bin/bash
# 크러쉬 LoKR 학습 — 5090에서 실행
# 1) 전처리: WAV → 2-pass → .pt
# 2) LoKR 학습: ~5분 예상

PYTHON="C:\Users\leo\ace-step-v15\venv\Scripts\python.exe"
TRAIN_PY="C:\Users\leo\ace-step-v15\train.py"
CKPT_DIR="C:\Users\leo\ace-step-v15\checkpoints"

AUDIO_DIR="D:\data\crush_clean"
TENSOR_DIR="D:\data\crush_tensors"
OUTPUT_DIR="D:\data\crush_lokr_output"

echo "=== Step 1: Preprocess ==="
ssh leo@100.107.229.5 "$PYTHON $TRAIN_PY fixed \
  --preprocess \
  --checkpoint-dir $CKPT_DIR \
  --model-variant turbo \
  --audio-dir $AUDIO_DIR \
  --tensor-output $TENSOR_DIR \
  --dataset-dir $TENSOR_DIR \
  --output-dir $OUTPUT_DIR"

echo ""
echo "=== Step 2: LoKR Training ==="
ssh leo@100.107.229.5 "$PYTHON $TRAIN_PY fixed \
  --checkpoint-dir $CKPT_DIR \
  --model-variant turbo \
  --dataset-dir $TENSOR_DIR \
  --output-dir $OUTPUT_DIR \
  --adapter-type lokr \
  --lokr-linear-dim 64 \
  --lokr-linear-alpha 128 \
  --lokr-weight-decompose \
  --lr 0.03 \
  --batch-size 1 \
  --gradient-accumulation 4 \
  --epochs 100 \
  --scheduler-type cosine \
  --warmup-steps 50 \
  --save-every 25 \
  --gradient-checkpointing"
