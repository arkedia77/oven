"""
Quincy P2 Vocab Remapping
Extends P1 base (17728) -> P2 (17732) by adding 4 tempo prefix tokens.
Also extends the P1 LoRA adapter's modules_to_save (tok_embeddings, lm_head).

Steps:
  1. Load P1 base_remapped.safetensors (17728)
  2. Extend tok_embeddings and lm_head with 4 new rows (random init)
  3. Save as P2 base
  4. Load P1 LoRA adapter_model.safetensors
  5. Extend modules_to_save weights similarly
  6. Save as P2 LoRA base
"""
import sys
import os
import json
import shutil

sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import torch
from safetensors.torch import load_file, save_file

# Paths
P1_BASE = r'D:\liszt\output\liszt_v9_prefix\base_remapped.safetensors'
P1_LORA = r'D:\liszt\output\liszt_v9_prefix\lora_checkpoints\lora_best\adapter_model.safetensors'
P1_LORA_CONFIG = r'D:\liszt\output\liszt_v9_prefix\lora_checkpoints\lora_best\adapter_config.json'

P2_OUTPUT_DIR = r'D:\liszt\output\quincy_p2'
P2_BASE = os.path.join(P2_OUTPUT_DIR, 'base_remapped.safetensors')
P2_LORA_DIR = os.path.join(P2_OUTPUT_DIR, 'lora_p1_extended')
P2_LORA = os.path.join(P2_LORA_DIR, 'adapter_model.safetensors')
P2_LORA_CONFIG = os.path.join(P2_LORA_DIR, 'adapter_config.json')

OLD_VOCAB = 17728
NEW_VOCAB = 17732  # +4 tempo tokens
HIDDEN_DIM = 1536


def extend_weight(weight, old_size, new_size, dim=0):
    """Extend weight tensor along dim with small random init."""
    assert weight.shape[dim] == old_size, f"Expected {old_size}, got {weight.shape[dim]}"
    extra = new_size - old_size
    if dim == 0:
        new_rows = torch.randn(extra, weight.shape[1], dtype=weight.dtype) * 0.02
        return torch.cat([weight, new_rows], dim=0)
    else:
        new_cols = torch.randn(weight.shape[0], extra, dtype=weight.dtype) * 0.02
        return torch.cat([weight, new_cols], dim=1)


def main():
    os.makedirs(P2_OUTPUT_DIR, exist_ok=True)
    os.makedirs(P2_LORA_DIR, exist_ok=True)

    # === Step 1: Extend base model ===
    print(f'Loading P1 base: {P1_BASE}')
    base_state = load_file(P1_BASE)

    emb_key = 'model.tok_embeddings.weight'
    lm_key = 'lm_head.weight'

    print(f'  {emb_key}: {base_state[emb_key].shape} -> [{NEW_VOCAB}, {HIDDEN_DIM}]')
    base_state[emb_key] = extend_weight(base_state[emb_key], OLD_VOCAB, NEW_VOCAB)

    print(f'  {lm_key}: {base_state[lm_key].shape} -> [{NEW_VOCAB}, {HIDDEN_DIM}]')
    base_state[lm_key] = extend_weight(base_state[lm_key], OLD_VOCAB, NEW_VOCAB)

    save_file(base_state, P2_BASE)
    size_mb = os.path.getsize(P2_BASE) / 1024 / 1024
    print(f'  Saved: {P2_BASE} ({size_mb:.1f}MB)')

    # === Step 2: Extend P1 LoRA adapter ===
    print(f'\nLoading P1 LoRA: {P1_LORA}')
    lora_state = load_file(P1_LORA)

    lora_emb_key = 'base_model.model.model.tok_embeddings.weight'
    lora_lm_key = 'base_model.model.lm_head.weight'

    print(f'  {lora_emb_key}: {lora_state[lora_emb_key].shape} -> [{NEW_VOCAB}, {HIDDEN_DIM}]')
    lora_state[lora_emb_key] = extend_weight(lora_state[lora_emb_key], OLD_VOCAB, NEW_VOCAB)

    print(f'  {lora_lm_key}: {lora_state[lora_lm_key].shape} -> [{NEW_VOCAB}, {HIDDEN_DIM}]')
    lora_state[lora_lm_key] = extend_weight(lora_state[lora_lm_key], OLD_VOCAB, NEW_VOCAB)

    save_file(lora_state, P2_LORA)
    size_mb = os.path.getsize(P2_LORA) / 1024 / 1024
    print(f'  Saved: {P2_LORA} ({size_mb:.1f}MB)')

    # Copy adapter_config.json
    shutil.copy(P1_LORA_CONFIG, P2_LORA_CONFIG)
    print(f'  Copied: {P2_LORA_CONFIG}')

    print(f'\n=== DONE: Vocab {OLD_VOCAB} -> {NEW_VOCAB} ===')
    print(f'Base: {P2_BASE}')
    print(f'LoRA: {P2_LORA_DIR}/')


if __name__ == '__main__':
    main()
