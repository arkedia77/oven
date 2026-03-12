"""
Liszt: Aria 피아노 파인튜닝 스크립트
- 베이스: aria-medium-base (LLaMA 3.2, 1B params)
- 데이터: curate된 피아노 MIDI (143만곡 중 tier1+tier2)
- GPU: RTX 5090 (32GB VRAM)
- 실행: python finetune_liszt.py [--resume checkpoint_path]
- 모니터: tail logs/finetune.log
"""

import os
import sys
import json
import time
import glob
import random
import argparse
import gc
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.cuda.amp import GradScaler, autocast

# aria 패키지
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "aria"))

from aria.model import TransformerLM
from aria.config import load_model_config
from ariautils.tokenizer import AbsTokenizer
from safetensors.torch import load_file, save_file

# ========== 설정 ==========
class Config:
    # 경로
    base_dir = r"C:\Users\leo\liszt"
    data_dir = r"C:\Users\leo\liszt\data\training_midi"  # 학습 MIDI 폴더
    checkpoint_dir = r"C:\Users\leo\liszt\checkpoints"
    base_checkpoint = r"C:\Users\leo\liszt\checkpoints\aria-medium-base\model.safetensors"
    output_dir = r"C:\Users\leo\liszt\output"
    log_file = r"C:\Users\leo\liszt\logs\finetune.log"

    # 모델
    model_size = "medium"  # aria-medium (1B params)
    seq_len = 4096  # 8192는 VRAM 초과 가능 → 4096으로 시작

    # 학습
    batch_size = 2  # RTX 5090 32GB 기준
    gradient_accumulation_steps = 16  # effective batch = 32
    learning_rate = 1e-5  # 파인튜닝이라 낮게
    warmup_steps = 500
    max_steps = 50000  # ~2 epochs on 143K files
    weight_decay = 0.01
    max_grad_norm = 1.0

    # 체크포인트
    save_every = 2000  # steps
    eval_every = 1000
    log_every = 50

    # 데이터
    max_files = None  # None = 전체, 숫자 = 제한 (테스트용)
    train_split = 0.98

    # AMP
    use_amp = True  # mixed precision


def make_logger(log_file):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line)
        with open(log_file, "a") as f:
            f.write(line + "\n")
    return log


# ========== 데이터셋 ==========
class MidiTokenDataset(Dataset):
    """MIDI 파일을 토크나이즈해서 고정 길이 시퀀스로 반환"""

    def __init__(self, midi_files, tokenizer, seq_len, log_fn=None):
        self.midi_files = midi_files
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.log = log_fn or print

        # 미리 토크나이즈하지 않고 on-the-fly로 처리 (메모리 절약)
        self.log(f"  데이터셋 초기화: {len(midi_files):,}개 MIDI")

    def __len__(self):
        return len(self.midi_files)

    def __getitem__(self, idx):
        midi_path = self.midi_files[idx]
        try:
            # MIDI → 토큰 시퀀스
            mid = self.tokenizer.midi_to_tokens(midi_path)
            token_ids = self.tokenizer.encode(mid)

            # seq_len+1 길이로 자르기 (input + target)
            if len(token_ids) > self.seq_len + 1:
                # 랜덤 위치에서 시작
                start = random.randint(0, len(token_ids) - self.seq_len - 1)
                token_ids = token_ids[start:start + self.seq_len + 1]
            elif len(token_ids) < self.seq_len + 1:
                # 패딩 (pad token = 0)
                token_ids = token_ids + [0] * (self.seq_len + 1 - len(token_ids))

            tokens = torch.tensor(token_ids, dtype=torch.long)
            input_ids = tokens[:-1]  # [0:seq_len]
            labels = tokens[1:]      # [1:seq_len+1]

            return input_ids, labels

        except Exception:
            # 실패 시 랜덤 다른 파일
            return self.__getitem__(random.randint(0, len(self) - 1))


def collate_fn(batch):
    input_ids = torch.stack([b[0] for b in batch])
    labels = torch.stack([b[1] for b in batch])
    return input_ids, labels


# ========== 학습 ==========
def train(config, resume_from=None):
    log = make_logger(config.log_file)

    log("=" * 60)
    log("Liszt 파인튜닝 시작")
    log("=" * 60)

    # GPU 확인
    assert torch.cuda.is_available(), "CUDA 필요"
    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_mem / 1e9
    log(f"GPU: {gpu_name} ({vram:.1f} GB)")
    log(f"PyTorch: {torch.__version__}")

    # 토크나이저
    tokenizer = AbsTokenizer()
    log(f"토크나이저 vocab: {tokenizer.vocab_size}")

    # 모델 로드
    log(f"\n모델 로드: {config.model_size}")
    model_config = load_model_config(config.model_size)
    model = TransformerLM(**model_config, vocab_size=tokenizer.vocab_size)

    if os.path.exists(config.base_checkpoint):
        log(f"베이스 체크포인트 로드: {config.base_checkpoint}")
        state_dict = load_file(config.base_checkpoint)
        model.load_state_dict(state_dict)
    else:
        log(f"WARNING: 베이스 체크포인트 없음 — 랜덤 초기화")

    model = model.to(device)
    params = sum(p.numel() for p in model.parameters())
    log(f"파라미터: {params/1e6:.0f}M ({params/1e9:.2f}B)")
    log(f"GPU 메모리 (모델 로드 후): {torch.cuda.memory_allocated()/1e9:.2f} GB")

    # 데이터 준비
    log(f"\n데이터 로드: {config.data_dir}")
    midi_files = []
    for ext in ("*.mid", "*.midi"):
        midi_files.extend(glob.glob(os.path.join(config.data_dir, "**", ext), recursive=True))

    if config.max_files:
        midi_files = midi_files[:config.max_files]

    random.shuffle(midi_files)
    split = int(len(midi_files) * config.train_split)
    train_files = midi_files[:split]
    eval_files = midi_files[split:]

    log(f"  전체: {len(midi_files):,} / 학습: {len(train_files):,} / 평가: {len(eval_files):,}")

    train_dataset = MidiTokenDataset(train_files, tokenizer, config.seq_len, log)
    eval_dataset = MidiTokenDataset(eval_files, tokenizer, config.seq_len, log)

    train_loader = DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True,
        num_workers=2, pin_memory=True, collate_fn=collate_fn,
        drop_last=True, persistent_workers=True
    )
    eval_loader = DataLoader(
        eval_dataset, batch_size=config.batch_size, shuffle=False,
        num_workers=1, pin_memory=True, collate_fn=collate_fn,
        drop_last=True
    )

    # 옵티마이저
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
        betas=(0.9, 0.95)
    )

    # LR 스케줄러 (cosine with warmup)
    def lr_lambda(step):
        if step < config.warmup_steps:
            return step / config.warmup_steps
        progress = (step - config.warmup_steps) / max(config.max_steps - config.warmup_steps, 1)
        return 0.1 + 0.9 * (1 + __import__('math').cos(__import__('math').pi * progress)) / 2

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    scaler = GradScaler(enabled=config.use_amp)

    # Resume
    global_step = 0
    best_eval_loss = float("inf")

    if resume_from and os.path.exists(resume_from):
        log(f"\n체크포인트 이어받기: {resume_from}")
        ckpt = torch.load(resume_from, map_location=device)
        model.load_state_dict(ckpt["model"])
        optimizer.load_state_dict(ckpt["optimizer"])
        scheduler.load_state_dict(ckpt["scheduler"])
        global_step = ckpt.get("global_step", 0)
        best_eval_loss = ckpt.get("best_eval_loss", float("inf"))
        log(f"  Step {global_step}부터 재개, best_loss={best_eval_loss:.4f}")

    # 학습 루프
    log(f"\n{'='*60}")
    log(f"학습 시작 (effective batch={config.batch_size * config.gradient_accumulation_steps})")
    log(f"  seq_len={config.seq_len}, lr={config.learning_rate}, max_steps={config.max_steps}")
    log(f"{'='*60}")

    model.train()
    criterion = nn.CrossEntropyLoss(ignore_index=0)  # pad=0 무시

    running_loss = 0.0
    step_count = 0
    t_start = time.time()

    train_iter = iter(train_loader)

    while global_step < config.max_steps:
        optimizer.zero_grad()
        accum_loss = 0.0

        for accum_step in range(config.gradient_accumulation_steps):
            try:
                input_ids, labels = next(train_iter)
            except StopIteration:
                train_iter = iter(train_loader)
                input_ids, labels = next(train_iter)

            input_ids = input_ids.to(device)
            labels = labels.to(device)

            with autocast(device_type="cuda", enabled=config.use_amp):
                logits = model(input_ids)
                loss = criterion(logits.view(-1, logits.size(-1)), labels.view(-1))
                loss = loss / config.gradient_accumulation_steps

            scaler.scale(loss).backward()
            accum_loss += loss.item()

        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()

        global_step += 1
        running_loss += accum_loss
        step_count += 1

        # 로깅
        if global_step % config.log_every == 0:
            avg_loss = running_loss / step_count
            lr = scheduler.get_last_lr()[0]
            elapsed = time.time() - t_start
            steps_per_sec = step_count / elapsed
            gpu_mem = torch.cuda.memory_allocated() / 1e9

            log(f"  step {global_step:>6d} | loss {avg_loss:.4f} | lr {lr:.2e} | "
                f"{steps_per_sec:.1f} step/s | GPU {gpu_mem:.1f}GB")

            running_loss = 0.0
            step_count = 0
            t_start = time.time()

        # 평가
        if global_step % config.eval_every == 0:
            eval_loss = evaluate(model, eval_loader, criterion, device, config)
            log(f"  ★ eval loss: {eval_loss:.4f} (best: {best_eval_loss:.4f})")

            if eval_loss < best_eval_loss:
                best_eval_loss = eval_loss
                save_checkpoint(
                    model, optimizer, scheduler, global_step, best_eval_loss,
                    os.path.join(config.checkpoint_dir, "liszt-best"),
                    log
                )
            model.train()

        # 체크포인트
        if global_step % config.save_every == 0:
            save_checkpoint(
                model, optimizer, scheduler, global_step, best_eval_loss,
                os.path.join(config.checkpoint_dir, f"liszt-step{global_step}"),
                log
            )

        gc.collect()

    # 최종 저장
    save_checkpoint(
        model, optimizer, scheduler, global_step, best_eval_loss,
        os.path.join(config.checkpoint_dir, "liszt-final"),
        log
    )

    log(f"\n{'='*60}")
    log(f"학습 완료! step={global_step}, best_eval_loss={best_eval_loss:.4f}")
    log(f"{'='*60}")


def evaluate(model, eval_loader, criterion, device, config):
    model.eval()
    total_loss = 0
    count = 0

    with torch.no_grad():
        for input_ids, labels in eval_loader:
            input_ids = input_ids.to(device)
            labels = labels.to(device)

            with autocast(device_type="cuda", enabled=config.use_amp):
                logits = model(input_ids)
                loss = criterion(logits.view(-1, logits.size(-1)), labels.view(-1))

            total_loss += loss.item()
            count += 1

            if count >= 50:  # 평가 50배치로 제한
                break

    return total_loss / max(count, 1)


def save_checkpoint(model, optimizer, scheduler, step, best_loss, path, log):
    os.makedirs(path, exist_ok=True)

    # 모델 가중치 (safetensors)
    model_path = os.path.join(path, "model.safetensors")
    save_file(model.state_dict(), model_path)

    # 옵티마이저 등 (PyTorch)
    train_state = {
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict(),
        "global_step": step,
        "best_eval_loss": best_loss,
    }
    torch.save(train_state, os.path.join(path, "train_state.pt"))

    # 메타데이터
    meta = {
        "name": "liszt",
        "base_model": "aria-medium",
        "step": step,
        "best_eval_loss": best_loss,
        "timestamp": datetime.now().isoformat(),
    }
    with open(os.path.join(path, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    log(f"  💾 체크포인트 저장: {path} (step {step})")


# ========== 메인 ==========
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Liszt: Aria Piano Fine-tuning")
    parser.add_argument("--resume", type=str, default=None, help="체크포인트 경로 (이어받기)")
    parser.add_argument("--test", action="store_true", help="소량 테스트 모드 (100파일)")
    parser.add_argument("--seq_len", type=int, default=None, help="시퀀스 길이 오버라이드")
    parser.add_argument("--batch_size", type=int, default=None, help="배치 사이즈 오버라이드")
    parser.add_argument("--lr", type=float, default=None, help="학습률 오버라이드")
    args = parser.parse_args()

    config = Config()

    if args.test:
        config.max_files = 100
        config.max_steps = 100
        config.save_every = 50
        config.eval_every = 50
        config.log_every = 10

    if args.seq_len:
        config.seq_len = args.seq_len
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.lr:
        config.learning_rate = args.lr

    train(config, resume_from=args.resume)
