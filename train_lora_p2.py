"""
Quincy P2 LoRA Training — Tempo Prefix
=======================================
- Base: P2 remapped (vocab 17732, tempo prefix added)
- Loads P1 LoRA weights (extended to 17732) as starting point
- LoRA target_modules: mixed_qkv, att_proj_linear
- modules_to_save: tok_embeddings, lm_head
- Data: P2 tempo-labeled data

Usage (on 5090):
  python train_lora_p2.py
"""
import sys
import os
import json
import time

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
P1_LORA_EXTENDED = r"D:\liszt\output\quincy_p2\lora_p1_extended\adapter_model.safetensors"
TRAIN_DATA_DIR = r"D:\liszt\output\quincy_p2\data\train_data"
VAL_DATA_DIR = r"D:\liszt\output\quincy_p2\data\val_data"
OUTPUT_DIR = r"D:\liszt\output\quincy_p2"
SAVE_DIR = os.path.join(OUTPUT_DIR, "lora_checkpoints")
LOG_FILE = os.path.join(OUTPUT_DIR, "p2_training.log")

LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LR = 3e-5  # slightly lower than P1 (5e-5) since we're fine-tuning from P1
EPOCHS = 3
BATCH_SIZE = 1
GRAD_ACC = 8
MAX_SEQ_LEN = 8192

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


def main():
    log("=" * 60)
    log("Quincy P2 LoRA Training — Tempo Prefix")
    log(f"  Base: P2 remapped (vocab 17732)")
    log(f"  LoRA: r={LORA_R}, alpha={LORA_ALPHA}, dropout={LORA_DROPOUT}")
    log(f"  LR={LR}, epochs={EPOCHS}, bs={BATCH_SIZE}, grad_acc={GRAD_ACC}")
    log(f"  Loading P1 LoRA weights as starting point")
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

    # Load P1 LoRA weights (extended to 17732)
    log(f"Loading P1 LoRA weights: {P1_LORA_EXTENDED}")
    p1_lora_state = load_file(P1_LORA_EXTENDED)
    set_peft_model_state_dict(model, p1_lora_state)
    log("P1 LoRA weights loaded successfully")

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    model = model.to(DEVICE)

    # grad_checkpoint hook — use modules_to_save version (original_module is frozen)
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

    # === Training Loop ===
    best_val_loss = float("inf")
    global_step = 0

    for epoch in range(EPOCHS):
        log(f"\n--- Epoch {epoch} ---")

        # Load epoch-specific data
        train_dataset = AriaJsonlDataset(TRAIN_DATA_DIR, tokenizer, epoch_idx=epoch)
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)

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
                optimizer.step()
                optimizer.zero_grad()
                global_step += 1

                if global_step % 10 == 0:
                    avg_loss = epoch_loss / step_count
                    log(f"  Step {global_step}, batch {batch_idx+1}/{len(train_loader)}, loss={avg_loss:.4f}")

                if global_step % 100 == 0:
                    save_path = os.path.join(SAVE_DIR, f"lora_step{global_step}")
                    model.save_pretrained(save_path)
                    log(f"  Checkpoint saved: {save_path}")

        avg_train_loss = epoch_loss / step_count if step_count > 0 else 0
        log(f"Epoch {epoch} train_loss: {avg_train_loss:.4f}")

        # === Validation ===
        model.eval()
        val_dataset = AriaJsonlDataset(VAL_DATA_DIR, tokenizer, epoch_idx=0)
        val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

        val_loss = 0
        val_steps = 0
        with torch.no_grad():
            for input_ids in val_loader:
                input_ids = input_ids.to(DEVICE)
                targets = input_ids[:, 1:].contiguous()
                logits = model(input_ids[:, :-1])
                loss = torch.nn.functional.cross_entropy(
                    logits.reshape(-1, logits.size(-1)),
                    targets.reshape(-1),
                    ignore_index=tokenizer.tok_to_id[tokenizer.pad_tok],
                )
                val_loss += loss.item()
                val_steps += 1

        avg_val_loss = val_loss / val_steps if val_steps > 0 else 0
        log(f"Epoch {epoch} val_loss: {avg_val_loss:.4f}")

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            save_path = os.path.join(SAVE_DIR, "lora_best")
            model.save_pretrained(save_path)
            log(f"  New best! Saved: {save_path}")

    # Save final
    save_path = os.path.join(SAVE_DIR, "lora_final")
    model.save_pretrained(save_path)
    log(f"\nFinal checkpoint: {save_path}")
    log(f"Best val_loss: {best_val_loss:.4f}")
    log("=== TRAINING COMPLETE ===")


if __name__ == "__main__":
    main()
