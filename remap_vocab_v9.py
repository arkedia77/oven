"""
Liszt V9 Vocab Remapping Script
- Remaps V5 checkpoint weights from old tokenizer vocab to new V9 vocab
- Old: 17727 tokens (genre: jazz/classical, form: sonata/prelude/nocturne/...)
- New: 17728 tokens (genre: +pop, form: ballad/groove/anthem/...)
- Form tokens replaced 1:1 (same positions), genre +1 shifts all downstream IDs
"""
import sys
import os
import json
import shutil
import argparse
import importlib

import torch

def build_tokenizer(config_path):
    """Build AbsTokenizer with a specific config file."""
    # Temporarily swap config
    pkg_config = os.path.join(
        os.path.dirname(__file__),
        'venv/lib/python3.14/site-packages/ariautils/config/config.json'
    )
    # Read target config
    with open(config_path) as f:
        cfg = json.load(f)
    # Write to package location
    with open(pkg_config, 'w') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

    # Force reimport
    import ariautils.config
    import ariautils.tokenizer.absolute
    import ariautils.tokenizer._base
    importlib.reload(ariautils.config)
    importlib.reload(ariautils.tokenizer._base)
    importlib.reload(ariautils.tokenizer.absolute)
    from ariautils.tokenizer import AbsTokenizer
    return AbsTokenizer()


def remap_checkpoint(old_ckpt_path, old_config_path, new_config_path, output_path):
    print(f"Loading old tokenizer from {old_config_path}...")
    old_tok = build_tokenizer(old_config_path)
    old_vocab = old_tok.tok_to_id
    old_size = old_tok.vocab_size
    print(f"  Old vocab size: {old_size}")

    print(f"Loading new tokenizer from {new_config_path}...")
    new_tok = build_tokenizer(new_config_path)
    new_vocab = new_tok.tok_to_id
    new_size = new_tok.vocab_size
    print(f"  New vocab size: {new_size}")

    # Build remapping: new_id -> old_id (for tokens that exist in both)
    remap = {}
    new_only = []
    for tok, new_id in new_vocab.items():
        old_id = old_vocab.get(tok)
        if old_id is not None:
            remap[new_id] = old_id
        else:
            new_only.append((tok, new_id))

    print(f"\n  Tokens in both vocabs: {len(remap)}")
    print(f"  New tokens (no old weights): {len(new_only)}")
    for tok, nid in new_only:
        print(f"    {tok} -> new_id={nid}")

    # Identify removed tokens
    removed = []
    for tok, old_id in old_vocab.items():
        if tok not in new_vocab:
            removed.append((tok, old_id))
    print(f"  Removed tokens: {len(removed)}")
    for tok, oid in removed:
        print(f"    {tok} -> old_id={oid}")

    # Load checkpoint
    print(f"\nLoading checkpoint: {old_ckpt_path}")
    ckpt = torch.load(old_ckpt_path, map_location='cpu', weights_only=False)

    # Handle different checkpoint formats
    if 'model' in ckpt:
        state_dict = ckpt['model']
    elif 'state_dict' in ckpt:
        state_dict = ckpt['state_dict']
    else:
        state_dict = ckpt

    # Find embedding and lm_head keys
    emb_key = None
    lm_key = None
    for k in state_dict.keys():
        if 'tok_embeddings' in k:
            emb_key = k
        if 'lm_head' in k or ('output' in k and 'weight' in k):
            lm_key = k

    if emb_key is None:
        # Try common patterns
        for k in state_dict.keys():
            if 'embed' in k.lower() and 'weight' in k:
                emb_key = k
                break

    print(f"  Embedding key: {emb_key}")
    print(f"  LM head key: {lm_key}")

    if emb_key is None:
        print("ERROR: Could not find embedding layer in checkpoint")
        print("Available keys:")
        for k in sorted(state_dict.keys()):
            print(f"  {k}: {state_dict[k].shape}")
        return

    old_emb = state_dict[emb_key]  # [old_vocab, dim]
    print(f"  Old embedding shape: {old_emb.shape}")
    dim = old_emb.shape[1]

    # Create new embedding
    new_emb = torch.zeros(new_size, dim, dtype=old_emb.dtype)

    # Copy remapped weights
    for new_id, old_id in remap.items():
        new_emb[new_id] = old_emb[old_id]

    # Initialize new tokens with category mean
    for tok, new_id in new_only:
        category = tok[1] if isinstance(tok, tuple) and len(tok) >= 2 else None
        if category == 'genre':
            # Mean of existing genre embeddings (jazz, classical)
            genre_ids = [old_vocab[('prefix', 'genre', g)] for g in ['jazz', 'classical']]
            new_emb[new_id] = old_emb[genre_ids].mean(dim=0)
            print(f"  Init {tok}: mean of jazz+classical embeddings")
        elif category == 'form':
            # Mean of all old form embeddings
            old_forms = ['sonata', 'prelude', 'nocturne', 'étude', 'waltz', 'mazurka', 'impromptu', 'fugue']
            form_ids = [old_vocab[('prefix', 'form', f)] for f in old_forms]
            new_emb[new_id] = old_emb[form_ids].mean(dim=0)
            print(f"  Init {tok}: mean of old form embeddings")
        else:
            # Random init (shouldn't happen)
            torch.nn.init.normal_(new_emb[new_id:new_id+1], mean=0.0, std=0.02)
            print(f"  Init {tok}: random")

    state_dict[emb_key] = new_emb
    print(f"  New embedding shape: {new_emb.shape}")

    # Remap lm_head if exists
    if lm_key and lm_key in state_dict:
        old_lm = state_dict[lm_key]  # [old_vocab, dim]
        print(f"  Old lm_head shape: {old_lm.shape}")
        new_lm = torch.zeros(new_size, dim, dtype=old_lm.dtype)
        for new_id, old_id in remap.items():
            new_lm[new_id] = old_lm[old_id]
        # Init new tokens same way
        for tok, new_id in new_only:
            category = tok[1] if isinstance(tok, tuple) and len(tok) >= 2 else None
            if category == 'genre':
                genre_ids = [old_vocab[('prefix', 'genre', g)] for g in ['jazz', 'classical']]
                new_lm[new_id] = old_lm[genre_ids].mean(dim=0)
            elif category == 'form':
                old_forms = ['sonata', 'prelude', 'nocturne', 'étude', 'waltz', 'mazurka', 'impromptu', 'fugue']
                form_ids = [old_vocab[('prefix', 'form', f)] for f in old_forms]
                new_lm[new_id] = old_lm[form_ids].mean(dim=0)
            else:
                torch.nn.init.normal_(new_lm[new_id:new_id+1], mean=0.0, std=0.02)
        state_dict[lm_key] = new_lm
        print(f"  New lm_head shape: {new_lm.shape}")

    # Save
    if 'model' in ckpt:
        ckpt['model'] = state_dict
    elif 'state_dict' in ckpt:
        ckpt['state_dict'] = state_dict
    else:
        ckpt = state_dict

    print(f"\nSaving remapped checkpoint to {output_path}...")
    torch.save(ckpt, output_path)
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  Saved: {size_mb:.1f}MB")

    # Verification
    print("\n=== Verification ===")
    piano_tok = ('prefix', 'instrument', 'piano')
    old_piano_id = old_vocab[piano_tok]
    new_piano_id = new_vocab[piano_tok]
    print(f"  piano: old_id={old_piano_id}, new_id={new_piano_id}")
    print(f"  piano embedding match: {torch.allclose(old_emb[old_piano_id], new_emb[new_piano_id])}")

    # Check a note token (should be shifted by +1 due to pop addition)
    for tok in [('prefix', 'instrument', 'piano'), ('prefix', 'composer', 'chopin'), ('prefix', 'genre', 'jazz')]:
        old_id = old_vocab[tok]
        new_id = new_vocab[tok]
        match = torch.allclose(old_emb[old_id], new_emb[new_id])
        print(f"  {tok}: old={old_id} new={new_id} match={match}")

    print("\n=== DONE ===")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-ckpt', required=True, help='Path to V5 checkpoint')
    parser.add_argument('--old-config', required=True, help='Path to old config.json')
    parser.add_argument('--new-config', required=True, help='Path to new config.json')
    parser.add_argument('--output', required=True, help='Output remapped checkpoint path')
    args = parser.parse_args()

    remap_checkpoint(args.old_ckpt, args.old_config, args.new_config, args.output)
