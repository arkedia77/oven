"""
Liszt v5 LoRA Training (Fixed v2)
=================================
- Base: V5 Pop epoch6_step0 (val_loss 1.1929, best)
- LoRA target_modules: mixed_qkv, att_proj_linear (actual Aria layer names)
- Data: V5 Pop pre-tokenized data (POP909, already prepared)
- Output: D:\liszt\output\liszt_v5_lora

Usage (on 5090):
  python train_lora_v5_fixed.py
"""
import sys, os, json, time, torch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"

ARIA_DIR = r"C:\Users\leo\liszt\aria"
sys.path.insert(0, ARIA_DIR)

from peft import LoraConfig, get_peft_model
from torch.utils.data import Dataset, DataLoader
from ariautils.tokenizer import AbsTokenizer
from aria.config import load_model_config
from aria.model import ModelConfig, TransformerLM
from aria.utils import _load_weight

# === Config ===
V5_POP_CHECKPOINT = r"C:\Users\leo\liszt\output\liszt_v5_pop\training_run\checkpoints\epoch6_step0\model.safetensors"
TRAIN_DATA_DIR = r"C:\Users\leo\liszt\output\liszt_v5_pop\train_data"
VAL_DATA_DIR = r"C:\Users\leo\liszt\output\liszt_v5_pop\val_data"
OUTPUT_DIR = r"D:\liszt\output\liszt_v5_lora"
SAVE_DIR = os.path.join(OUTPUT_DIR, "lora_checkpoints")
LOG_FILE = os.path.join(OUTPUT_DIR, "lora_training.log")

LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LR = 5e-5
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
    """Load pre-tokenized Aria JSONL data (from `aria pretrain-dataset`)"""

    def __init__(self, data_dir, tokenizer, epoch_idx=0):
        self.tokenizer = tokenizer
        self.sequences = []
        jsonl_path = os.path.join(data_dir, f"epoch{epoch_idx}.jsonl")
        if not os.path.exists(jsonl_path):
            # val_data may have epoch0 only
            jsonl_path = os.path.join(data_dir, "epoch0.jsonl")

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                obj = json.loads(line)
                if i == 0 and "tokenizer_config" in obj:
                    continue  # skip header
                if "seq" in obj:
                    # JSON lists -> tuples for dict key lookup
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
    log("Liszt v5 LoRA Training (Fixed v2)")
    log(f"  Base: V5 Pop epoch6_step0")
    log(f"  LoRA: r={LORA_R}, alpha={LORA_ALPHA}, dropout={LORA_DROPOUT}")
    log(f"  target_modules: mixed_qkv, att_proj_linear")
    log(f"  LR={LR}, epochs={EPOCHS}, bs={BATCH_SIZE}, grad_acc={GRAD_ACC}")
    log(f"  Output: {OUTPUT_DIR}")
    log("=" * 60)

    # Tokenizer
    log("Loading tokenizer...")
    tokenizer = AbsTokenizer()
    pad_id = tokenizer.tok_to_id[tokenizer.pad_tok]

    # Model (training version, not inference)
    log("Loading V5 Pop best model (training TransformerLM)...")
    model_config = ModelConfig(**load_model_config("medium"))
    model = TransformerLM(model_config)
    state_dict = _load_weight(V5_POP_CHECKPOINT)
    model.load_state_dict(state_dict, strict=False)

    # Fix gradient checkpointing + LoRA: embeddings must produce requires_grad tensors
    def make_inputs_require_grad(module, input, output):
        output.requires_grad_(True)
    model.model.tok_embeddings.register_forward_hook(make_inputs_require_grad)

    model = model.to(DEVICE)
    log(f"Model loaded, GPU mem: {torch.cuda.memory_allocated()/1024**2:.0f}MB")

    # LoRA
    log("Applying LoRA...")
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=["mixed_qkv", "att_proj_linear"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Count trainable
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log(f"Trainable: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # Data
    log("Loading datasets...")
    val_ds = AriaJsonlDataset(VAL_DATA_DIR, tokenizer, epoch_idx=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # Optimizer
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=LR, weight_decay=0.01
    )
    scaler = torch.amp.GradScaler("cuda")

    best_val_loss = float("inf")
    global_step = 0

    for epoch in range(EPOCHS):
        # Load epoch-specific data (different shuffles from aria pretrain-dataset)
        epoch_idx = min(epoch, 2)  # epoch0/1/2.jsonl
        train_ds = AriaJsonlDataset(TRAIN_DATA_DIR, tokenizer, epoch_idx=epoch_idx)
        train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                                  num_workers=0, drop_last=True)

        log(f"Epoch {epoch}: {len(train_ds)} train, {len(val_ds)} val")

        model.train()
        epoch_loss = 0
        n_steps = 0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            batch = batch.to(DEVICE)
            input_ids = batch[:, :-1]
            labels = batch[:, 1:]

            with torch.amp.autocast("cuda", dtype=DTYPE):
                logits = model(src=input_ids)

                loss = torch.nn.functional.cross_entropy(
                    logits.reshape(-1, logits.size(-1)),
                    labels.reshape(-1),
                    ignore_index=pad_id
                )
                loss = loss / GRAD_ACC

            scaler.scale(loss).backward()
            epoch_loss += loss.item() * GRAD_ACC
            n_steps += 1

            if (step + 1) % GRAD_ACC == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
                global_step += 1

                if global_step % 10 == 0:
                    avg = epoch_loss / n_steps
                    log(f"E{epoch} step {global_step} loss {avg:.4f}")

                if global_step % 100 == 0:
                    cp_path = os.path.join(SAVE_DIR, f"lora_step{global_step}")
                    model.save_pretrained(cp_path)
                    log(f"Saved: lora_step{global_step}")

        avg_train = epoch_loss / max(n_steps, 1)
        log(f"Epoch {epoch} train_loss {avg_train:.4f}")

        # Validation
        model.eval()
        val_loss = 0
        val_steps = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(DEVICE)
                input_ids = batch[:, :-1]
                labels = batch[:, 1:]
                with torch.amp.autocast("cuda", dtype=DTYPE):
                    logits = model(src=input_ids)
                    loss = torch.nn.functional.cross_entropy(
                        logits.reshape(-1, logits.size(-1)),
                        labels.reshape(-1),
                        ignore_index=pad_id
                    )
                val_loss += loss.item()
                val_steps += 1

        avg_val = val_loss / max(val_steps, 1)
        log(f"Epoch {epoch} val_loss {avg_val:.4f}")

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            model.save_pretrained(os.path.join(SAVE_DIR, "lora_best"))
            log(f"New best! val_loss={avg_val:.4f}")

    # Final save
    model.save_pretrained(os.path.join(SAVE_DIR, "lora_final"))
    log("=" * 60)
    log(f"Training complete! Best val_loss: {best_val_loss:.4f}")
    log("=" * 60)


if __name__ == "__main__":
    main()
