"""
Quincy P3 LoRA Training — Lyrical Piano Focus
==============================================
- Base: P2 remapped (vocab 17732)
- Init: P2 best LoRA weights (continuing from P2)
- Focus: lyrical/emotional piano quality improvement
- Changes from P2:
  - Lower LR (2e-5) for fine-grained refinement
  - 5 epochs (more passes since data is enriched)
  - Cosine LR schedule
  - Val every 50 steps (earlier feedback)

Usage (on 5090):
  python train_lora_p3.py
"""
import sys
import os
import json
import time
import math

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"

ARIA_DIR = r"C:\Users\leo\liszt\aria"
sys.path.insert(0, ARIA_DIR)

import torch
from peft import LoraConfig, get_peft_model, set_peft_model_state_dict
from torch.utils.data import Dataset, DataLoader
from ariautils.tokenizer import AbsTokenizer
from aria.config import load_model_config
from aria.model import ModelConfig, TransformerLM
from safetensors.torch import load_file

# === Config ===
P2_BASE = r"D:\liszt\output\quincy_p2\base_remapped.safetensors"
P2_LORA_BEST = r"D:\liszt\output\quincy_p2\lora_checkpoints\lora_best\adapter_model.safetensors"
TRAIN_DATA_DIR = r"D:\liszt\output\quincy_p3\data\train_data"
VAL_DATA_DIR = r"D:\liszt\output\quincy_p3\data\val_data"
OUTPUT_DIR = r"D:\liszt\output\quincy_p3"
SAVE_DIR = os.path.join(OUTPUT_DIR, "lora_checkpoints")
LOG_FILE = os.path.join(OUTPUT_DIR, "p3_training.log")

LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LR = 2e-5  # lower than P2 (3e-5) for refinement
MIN_LR = 2e-6  # cosine schedule floor
EPOCHS = 5
BATCH_SIZE = 1
GRAD_ACC = 8
MAX_SEQ_LEN = 8192
WARMUP_STEPS = 50
VAL_EVERY = 50  # validate more frequently

DTYPE = torch.bfloat16
DEVICE = "cuda"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAVE_DIR, exist_ok=True)


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class AriaJsonlDataset(Dataset):
    """Load pre-tokenized Aria JSONL data"""

    def __init__(self, data_dir, tokenizer, epoch_idx=0):
        self.tokenizer = tokenizer
        self.sequences = []
        jsonl_path = os.path.join(data_dir, f"epoch{epoch_idx}.jsonl")
        if not os.path.exists(jsonl_path):
            jsonl_path = os.path.join(data_dir, "epoch0.jsonl")

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                obj = json.loads(line)
                if i == 0 and "tokenizer_config" in obj:
                    continue
                if "seq" in obj:
                    seq = [tuple(t) if isinstance(t, list) else t for t in obj["seq"]]
                    ids = tokenizer.encode(seq)
                    self.sequences.append(ids)

        log(f"Loaded {len(self.sequences)} sequences from {jsonl_path}")

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        ids = self.sequences[idx]
        if len(ids) > MAX_SEQ_LEN:
            ids = ids[:MAX_SEQ_LEN]
        elif len(ids) < MAX_SEQ_LEN:
            pad_id = self.tokenizer.tok_to_id[self.tokenizer.pad_tok]
            ids = ids + [pad_id] * (MAX_SEQ_LEN - len(ids))
        return torch.tensor(ids, dtype=torch.long)


def get_cosine_lr(step, total_steps, warmup_steps, lr, min_lr):
    """Cosine schedule with warmup."""
    if step < warmup_steps:
        return lr * step / warmup_steps
    progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
    return min_lr + 0.5 * (lr - min_lr) * (1 + math.cos(math.pi * progress))


def validate(model, tokenizer, device):
    """Run validation and return avg loss."""
    model.eval()
    val_dataset = AriaJsonlDataset(VAL_DATA_DIR, tokenizer, epoch_idx=0)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    val_loss = 0
    val_steps = 0
    with torch.no_grad():
        for input_ids in val_loader:
            input_ids = input_ids.to(device)
            targets = input_ids[:, 1:].contiguous()
            logits = model(input_ids[:, :-1])
            loss = torch.nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
                ignore_index=tokenizer.tok_to_id[tokenizer.pad_tok],
            )
            val_loss += loss.item()
            val_steps += 1

    model.train()
    return val_loss / val_steps if val_steps > 0 else float("inf")


def main():
    log("=" * 60)
    log("Quincy P3 LoRA Training — Lyrical Piano Focus")
    log(f"  Base: P2 remapped (vocab 17732)")
    log(f"  Init: P2 best LoRA")
    log(f"  LoRA: r={LORA_R}, alpha={LORA_ALPHA}, dropout={LORA_DROPOUT}")
    log(f"  LR={LR} -> {MIN_LR} (cosine), warmup={WARMUP_STEPS}")
    log(f"  Epochs={EPOCHS}, bs={BATCH_SIZE}, grad_acc={GRAD_ACC}")
    log("=" * 60)

    # === Tokenizer ===
    tokenizer = AbsTokenizer()
    vocab_size = tokenizer.vocab_size
    log(f"Tokenizer vocab: {vocab_size}")
    assert vocab_size == 17732, f"Expected 17732, got {vocab_size}"

    # === Model ===
    log("Loading model config...")
    model_config_dict = load_model_config("medium")
    model_config = ModelConfig(**model_config_dict)
    model_config.vocab_size = vocab_size

    log("Building model...")
    model = TransformerLM(model_config).to(DTYPE)

    log(f"Loading base weights: {P2_BASE}")
    base_state = load_file(P2_BASE)
    model.load_state_dict(base_state, strict=False)

    # === LoRA ===
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=["mixed_qkv", "att_proj_linear"],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        modules_to_save=["model.tok_embeddings", "lm_head"],
    )

    model = get_peft_model(model, lora_config)

    # Load P2 best LoRA weights
    log(f"Loading P2 best LoRA: {P2_LORA_BEST}")
    p2_lora_state = load_file(P2_LORA_BEST)
    set_peft_model_state_dict(model, p2_lora_state)
    log("P2 LoRA weights loaded successfully")

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    model = model.to(DEVICE)

    # grad_checkpoint hook
    emb_module = model.base_model.model.model.tok_embeddings
    if hasattr(emb_module, 'modules_to_save'):
        for key, mod in emb_module.modules_to_save.items():
            if mod.weight.requires_grad:
                mod.weight.register_hook(lambda grad: grad)
                log(f"  Hook on modules_to_save[{key}].weight")
                break
    else:
        emb_module.weight.register_hook(lambda grad: grad)
        log("  Hook on tok_embeddings.weight")

    # === Optimizer ===
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=LR,
        weight_decay=0.01,
    )

    # Estimate total steps for cosine schedule
    # We'll update this after loading first epoch data
    est_steps_per_epoch = 500  # placeholder
    total_steps = est_steps_per_epoch * EPOCHS

    # === Training Loop ===
    best_val_loss = float("inf")
    global_step = 0

    # Initial validation
    init_val = validate(model, tokenizer, DEVICE)
    log(f"Initial val_loss (P2 checkpoint): {init_val:.4f}")
    best_val_loss = init_val

    for epoch in range(EPOCHS):
        log(f"\n--- Epoch {epoch} ---")

        train_dataset = AriaJsonlDataset(TRAIN_DATA_DIR, tokenizer, epoch_idx=epoch)
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)

        # Update total steps estimate
        if epoch == 0:
            steps_per_epoch = len(train_loader) // GRAD_ACC
            total_steps = steps_per_epoch * EPOCHS
            log(f"  Steps/epoch: {steps_per_epoch}, total: {total_steps}")

        model.train()
        optimizer.zero_grad()
        epoch_loss = 0
        step_count = 0

        for batch_idx, input_ids in enumerate(train_loader):
            input_ids = input_ids.to(DEVICE)
            targets = input_ids[:, 1:].contiguous()
            logits = model(input_ids[:, :-1])

            loss = torch.nn.functional.cross_entropy(
                logits.reshape(-1, logits.size(-1)),
                targets.reshape(-1),
                ignore_index=tokenizer.tok_to_id[tokenizer.pad_tok],
            )
            loss = loss / GRAD_ACC
            loss.backward()

            epoch_loss += loss.item() * GRAD_ACC
            step_count += 1

            if (batch_idx + 1) % GRAD_ACC == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

                # Cosine LR
                current_lr = get_cosine_lr(global_step, total_steps, WARMUP_STEPS, LR, MIN_LR)
                for pg in optimizer.param_groups:
                    pg['lr'] = current_lr

                optimizer.step()
                optimizer.zero_grad()
                global_step += 1

                if global_step % 10 == 0:
                    avg_loss = epoch_loss / step_count
                    log(f"  Step {global_step}, batch {batch_idx+1}/{len(train_loader)}, "
                        f"loss={avg_loss:.4f}, lr={current_lr:.2e}")

                # Validate & checkpoint
                if global_step % VAL_EVERY == 0:
                    val_loss = validate(model, tokenizer, DEVICE)
                    log(f"  [VAL] Step {global_step}, val_loss={val_loss:.4f} "
                        f"(best={best_val_loss:.4f})")

                    if val_loss < best_val_loss:
                        best_val_loss = val_loss
                        save_path = os.path.join(SAVE_DIR, "lora_best")
                        model.save_pretrained(save_path)
                        log(f"  New best! Saved: {save_path}")

                if global_step % 100 == 0:
                    save_path = os.path.join(SAVE_DIR, f"lora_step{global_step}")
                    model.save_pretrained(save_path)
                    log(f"  Checkpoint saved: {save_path}")

        avg_train_loss = epoch_loss / step_count if step_count > 0 else 0
        log(f"Epoch {epoch} train_loss: {avg_train_loss:.4f}")

        # End-of-epoch validation
        val_loss = validate(model, tokenizer, DEVICE)
        log(f"Epoch {epoch} val_loss: {val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            save_path = os.path.join(SAVE_DIR, "lora_best")
            model.save_pretrained(save_path)
            log(f"  New best! Saved: {save_path}")

        # Epoch checkpoint
        save_path = os.path.join(SAVE_DIR, f"lora_epoch{epoch}")
        model.save_pretrained(save_path)
        log(f"  Epoch checkpoint: {save_path}")

    # Final
    save_path = os.path.join(SAVE_DIR, "lora_final")
    model.save_pretrained(save_path)
    log(f"\nFinal checkpoint: {save_path}")
    log(f"Best val_loss: {best_val_loss:.4f}")
    log("=== P3 TRAINING COMPLETE ===")


if __name__ == "__main__":
    main()
