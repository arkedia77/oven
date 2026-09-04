#!/usr/bin/env python3
"""
Phrase Embedding Pipeline for Liszt RAG System
================================================
Tier1 MIDI → Phrase Segmentation → Aria Embedding (512-dim) → FAISS Index

Usage (on 5090):
    python embed_phrases.py --midi-dir C:/Users/leo/liszt/tier1_premium --output C:/Users/leo/liszt/embeddings
    python embed_phrases.py --file-list tier1_files.txt --output embeddings/

Steps:
    1. Load Aria embedding model (aria-medium-embedding, 512-dim)
    2. For each MIDI: segment into phrases → tokenize → embed → collect
    3. Build FAISS IndexFlatIP (cosine similarity via L2-normalized vectors)
    4. Save: index.faiss + metadata.jsonl
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch

# ── Aria imports (adjust paths as needed) ──
# On 5090: C:\Users\leo\liszt\aria\ should be in sys.path
ARIA_DIR = os.environ.get("ARIA_DIR", "C:/Users/leo/liszt/aria")
if ARIA_DIR not in sys.path:
    sys.path.insert(0, ARIA_DIR)

try:
    from ariautils.tokenizer import AbsTokenizer
    from ariautils.midi import MidiDict
except ImportError:
    print("ERROR: ariautils not found. Set ARIA_DIR or install ariautils.")
    sys.exit(1)

try:
    import faiss
except ImportError:
    print("WARNING: faiss not installed. Will save raw vectors only.")
    faiss = None

# ── Phrase segmenter (simplified inline version for 5090) ──
import pretty_midi

DEFAULT_REST_GAP = 0.3
VELOCITY_JUMP = 30
PITCH_JUMP = 12
MIN_PHRASE_NOTES = 4
MIN_PHRASE_DURATION = 0.4
MAX_PHRASE_DURATION = 15.0
MAX_PHRASE_NOTES = 200
BOUNDARY_THRESHOLD = 2.2


def segment_midi(midi_path, rest_gap=DEFAULT_REST_GAP):
    """Segment a MIDI file into phrases. Returns list of (start_time, end_time, notes)."""
    try:
        pm = pretty_midi.PrettyMIDI(str(midi_path))
    except Exception:
        return []

    notes = []
    for inst in pm.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            notes.append((n.pitch, n.velocity, n.start, n.end))
    notes.sort(key=lambda x: (x[2], x[0]))

    if len(notes) < MIN_PHRASE_NOTES:
        return []

    # Compute boundary scores
    boundaries = [0]
    for i in range(len(notes) - 1):
        score = 0.0
        curr_end = notes[i][3]
        nxt_start = notes[i + 1][2]
        gap = nxt_start - curr_end

        if gap >= rest_gap:
            score += min(1.0 + (gap - rest_gap) / rest_gap, 2.0)

        vel_diff = abs(notes[i + 1][1] - notes[i][1])
        if vel_diff >= VELOCITY_JUMP:
            score += min(vel_diff / VELOCITY_JUMP, 1.5)

        pitch_diff = abs(notes[i + 1][0] - notes[i][0])
        if pitch_diff >= PITCH_JUMP:
            score += min(pitch_diff / PITCH_JUMP, 1.5)

        if score >= BOUNDARY_THRESHOLD:
            boundaries.append(i + 1)

    # Build phrases
    phrases = []
    for pi in range(len(boundaries)):
        start_idx = boundaries[pi]
        end_idx = boundaries[pi + 1] if pi + 1 < len(boundaries) else len(notes)
        phrase_notes = notes[start_idx:end_idx]

        if len(phrase_notes) < MIN_PHRASE_NOTES:
            if phrases:
                phrases[-1] = (phrases[-1][0], phrase_notes[-1][3], phrases[-1][2] + phrase_notes)
            continue

        start_t = phrase_notes[0][2]
        end_t = phrase_notes[-1][3]
        dur = end_t - start_t

        if dur < MIN_PHRASE_DURATION:
            if phrases:
                phrases[-1] = (phrases[-1][0], end_t, phrases[-1][2] + phrase_notes)
            continue

        phrases.append((start_t, end_t, phrase_notes))

    # Force-split oversized phrases
    final = []
    for start_t, end_t, pnotes in phrases:
        while len(pnotes) > MAX_PHRASE_NOTES or (pnotes[-1][3] - pnotes[0][2]) > MAX_PHRASE_DURATION:
            take = min(MAX_PHRASE_NOTES, len(pnotes))
            for j in range(1, take + 1):
                if pnotes[j - 1][2] - pnotes[0][2] > MAX_PHRASE_DURATION:
                    take = max(MIN_PHRASE_NOTES, j - 1)
                    break
            chunk = pnotes[:take]
            pnotes = pnotes[take:]
            if not pnotes:
                break
            final.append((chunk[0][2], chunk[-1][3], chunk))
            if len(pnotes) < MIN_PHRASE_NOTES:
                if final:
                    final[-1] = (final[-1][0], pnotes[-1][3], final[-1][2] + pnotes)
                pnotes = []
        if pnotes:
            final.append((pnotes[0][2], pnotes[-1][3], pnotes))

    return final


def phrase_to_midi_dict(phrase_notes, original_midi_path):
    """Convert phrase notes back to a minimal MidiDict for tokenization."""
    # Create a temporary MIDI with only the phrase notes
    pm = pretty_midi.PrettyMIDI()
    piano = pretty_midi.Instrument(program=0)
    base_time = phrase_notes[0][2]  # normalize to start at 0
    for pitch, vel, start, end in phrase_notes:
        note = pretty_midi.Note(
            velocity=vel,
            pitch=pitch,
            start=start - base_time,
            end=end - base_time,
        )
        piano.notes.append(note)
    pm.instruments.append(piano)

    # Save to temp and load as MidiDict
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
        tmp_path = f.name
        pm.write(tmp_path)

    try:
        midi_dict = MidiDict.from_midi(tmp_path)
    finally:
        os.unlink(tmp_path)

    return midi_dict


# ── Embedding Model ──

class AriaEmbedder:
    """Wrapper for aria-medium-embedding model."""

    def __init__(self, model_dir, device="cuda"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.tokenizer = AbsTokenizer()

        # Load using transformers AutoModel (handles relative imports in model code)
        from transformers import AutoModelForCausalLM
        self.model = AutoModelForCausalLM.from_pretrained(
            model_dir, trust_remote_code=True
        )
        self.model = self.model.to(self.device)
        self.model.eval()
        print(f"Loaded aria-medium-embedding on {self.device}")

    @torch.no_grad()
    def embed(self, midi_dict, max_tokens=2048):
        """Get 512-dim embedding from a MidiDict."""
        tokens = self.tokenizer.tokenize(midi_dict)

        # Add EOS token
        eos_tok = self.tokenizer.eos_tok
        tokens.append(eos_tok)

        # Truncate if needed (keep last max_tokens to preserve EOS)
        if len(tokens) > max_tokens:
            tokens = tokens[-(max_tokens):]

        token_ids = self.tokenizer.encode(tokens)
        input_ids = torch.tensor([token_ids], device=self.device)

        # forward() returns (pooled_embedding, ...) or object with pooler_output
        outputs = self.model(input_ids)
        if hasattr(outputs, 'pooler_output') and outputs.pooler_output is not None:
            emb = outputs.pooler_output[0]
        elif isinstance(outputs, tuple):
            emb = outputs[0].squeeze(0)  # [1, 512] → [512]
        else:
            emb = outputs[0]

        # L2 normalize for cosine similarity
        emb = emb.float() / emb.float().norm()
        return emb.cpu().numpy()

    @torch.no_grad()
    def embed_batch(self, midi_dicts, max_tokens=2048, batch_size=16):
        """Batch embedding for efficiency."""
        all_embeddings = []
        for i in range(0, len(midi_dicts), batch_size):
            batch = midi_dicts[i:i + batch_size]
            batch_ids = []
            for md in batch:
                tokens = self.tokenizer.tokenize(md)
                tokens.append(self.tokenizer.eos_tok)
                if len(tokens) > max_tokens:
                    tokens = tokens[-max_tokens:]
                batch_ids.append(self.tokenizer.encode(tokens))

            # Pad to same length
            max_len = max(len(ids) for ids in batch_ids)
            pad_id = self.tokenizer.pad_tok if hasattr(self.tokenizer, 'pad_tok') else 2
            padded = [ids + [pad_id] * (max_len - len(ids)) for ids in batch_ids]

            input_ids = torch.tensor(padded, device=self.device)
            outputs = self.model(input_ids)

            if hasattr(outputs, "last_hidden_state"):
                hidden = outputs.last_hidden_state
            else:
                hidden = outputs

            # Get last non-pad token for each
            for j, ids in enumerate(batch_ids):
                emb = hidden[j, len(ids) - 1, :]
                emb = emb / emb.norm()
                all_embeddings.append(emb.cpu().numpy())

        return np.stack(all_embeddings)


# ── Main Pipeline ──

def collect_midi_files(args):
    """Collect MIDI file paths from directory or file list."""
    files = []
    if args.file_list:
        with open(args.file_list, encoding='utf-8') as f:
            for line in f:
                p = line.strip()
                if p and os.path.exists(p):
                    files.append(p)
    elif args.midi_dir:
        midi_dir = Path(args.midi_dir)
        for ext in ("*.mid", "*.midi", "*.MID"):
            files.extend(str(p) for p in midi_dir.rglob(ext))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="Phrase Embedding Pipeline")
    parser.add_argument("--midi-dir", help="Directory with MIDI files")
    parser.add_argument("--file-list", help="Text file with MIDI paths (one per line)")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--model-dir", default="C:/Users/leo/liszt/aria-medium-embedding",
                        help="Path to aria-medium-embedding checkpoint")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-files", type=int, default=0, help="Limit files (0=all)")
    parser.add_argument("--resume", action="store_true", help="Skip already processed files")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Collect files
    print("Collecting MIDI files...")
    midi_files = collect_midi_files(args)
    if args.max_files > 0:
        midi_files = midi_files[:args.max_files]
    print(f"Found {len(midi_files)} MIDI files", flush=True)
    if not midi_files:
        print("No MIDI files found! Check paths.", flush=True)
        return

    # Resume support
    metadata_path = os.path.join(args.output, "metadata.jsonl")
    processed = set()
    if args.resume and os.path.exists(metadata_path):
        with open(metadata_path) as f:
            for line in f:
                m = json.loads(line)
                processed.add(m["source_file"])
        print(f"Resuming: {len(processed)} already processed")

    # Load model
    print("Loading embedding model...")
    embedder = AriaEmbedder(args.model_dir, device=args.device)

    # Process
    all_embeddings = []
    all_metadata = []
    total_phrases = 0
    errors = 0
    t0 = time.time()

    meta_f = open(metadata_path, "a" if args.resume else "w", encoding="utf-8")

    for fi, midi_path in enumerate(midi_files):
        if midi_path in processed:
            continue

        try:
            phrases = segment_midi(midi_path)
            if not phrases:
                continue

            for pi, (start_t, end_t, pnotes) in enumerate(phrases):
                try:
                    midi_dict = phrase_to_midi_dict(pnotes, midi_path)
                    emb = embedder.embed(midi_dict)
                    all_embeddings.append(emb)

                    meta = {
                        "idx": total_phrases,
                        "source_file": midi_path,
                        "phrase_idx": pi,
                        "start_time": round(start_t, 3),
                        "end_time": round(end_t, 3),
                        "duration": round(end_t - start_t, 3),
                        "num_notes": len(pnotes),
                        "avg_pitch": round(np.mean([n[0] for n in pnotes]), 1),
                        "avg_velocity": round(np.mean([n[1] for n in pnotes]), 1),
                        "pitch_range": [min(n[0] for n in pnotes), max(n[0] for n in pnotes)],
                    }
                    all_metadata.append(meta)
                    meta_f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                    total_phrases += 1

                except Exception:
                    errors += 1
                    continue

        except Exception as e:
            errors += 1
            if errors <= 5:
                traceback.print_exc()
            continue

        if (fi + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (fi + 1) / elapsed
            print(f"[{fi+1}/{len(midi_files)}] {total_phrases} phrases, "
                  f"{rate:.1f} files/s, {errors} errors", flush=True)

    meta_f.close()
    elapsed = time.time() - t0
    print(f"\nDone: {total_phrases} phrases from {len(midi_files)} files "
          f"in {elapsed:.0f}s ({errors} errors)")

    if not all_embeddings:
        print("No embeddings generated!")
        return

    # Stack and save
    embeddings = np.stack(all_embeddings).astype(np.float32)
    np.save(os.path.join(args.output, "embeddings.npy"), embeddings)
    print(f"Saved embeddings: {embeddings.shape}")

    # Build FAISS index
    if faiss is not None:
        dim = embeddings.shape[1]  # 512
        # L2 normalize already done, use IndexFlatIP for cosine similarity
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        faiss.write_index(index, os.path.join(args.output, "index.faiss"))
        print(f"FAISS index built: {index.ntotal} vectors, dim={dim}")
    else:
        print("FAISS not available — saved raw .npy only")


if __name__ == "__main__":
    main()
