"""
Quincy P3 Data Preparation - Lyrical Piano Focus (v2 - Resume Support)
======================================================================
Changes from v1:
  - Disk-based: sequences written to temp JSONL during Phase 1 (no OOM)
  - Resume: checkpoint every 5000 files, restarts from last checkpoint
  - Phase 2-4 reads from disk

Usage (on 5090):
  python prepare_p3_data_v2.py
"""
import sys
import os
import json
import glob
import random
import time
import re

sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, r'C:\Users\leo\liszt\aria')

from ariautils.tokenizer import AbsTokenizer
from ariautils.midi import MidiDict

# === Paths (5090) ===
TRAINING_DATA = r'D:\liszt\training_data'
TIER1_DIR = r'D:\liszt\training_data\tier1_premium'
P2_OUTPUT = r'D:\liszt\output\quincy_p2'
P3_OUTPUT = r'D:\liszt\output\quincy_p3'
P2_LORA_BEST = os.path.join(P2_OUTPUT, 'lora_checkpoints', 'lora_best')
MAX_SEQ_LEN = 8192

TEMPO_RANGES = [
    ('slow', 40, 89),
    ('medium', 90, 119),
    ('fast', 120, 159),
    ('very_fast', 160, 240),
]

LYRICAL_SOURCES = {'maestro', 'atepp', 'asap'}
LYRICAL_UPSAMPLE = 8

JAZZ_KEYWORDS = {'jazz', 'swing', 'bebop', 'bossa', 'blues'}

LYRICAL_COMPOSERS = {
    'chopin', 'debussy', 'satie', 'ravel', 'liszt',
    'rachmaninoff', 'schubert', 'schumann', 'grieg',
    'sakamoto', 'yiruma', 'einaudi', 'hisaishi', 'nils frahm',
    'ludovico', 'tiersen', 'olafur arnalds',
}

# Checkpoint / temp files
CHECKPOINT_FILE = os.path.join(P3_OUTPUT, 'checkpoint.json')
LYRICAL_TEMP = os.path.join(P3_OUTPUT, 'temp_lyrical.jsonl')
STANDARD_TEMP = os.path.join(P3_OUTPUT, 'temp_standard.jsonl')

LOG_PATH = None


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if LOG_PATH:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')


def classify_tempo(bpm):
    if bpm is None:
        return None
    if bpm < 40:
        return 'slow'
    for name, lo, hi in TEMPO_RANGES:
        if lo <= bpm <= hi:
            return name
    return 'fast' if bpm > 240 else 'medium'


def get_midi_bpm_strict(midi_path):
    try:
        midi_dict = MidiDict.from_midi(midi_path)
        if not midi_dict.tempo_msgs:
            return None
        tempos = midi_dict.tempo_msgs
        if len(tempos) == 1:
            return 60_000_000 / tempos[0]['data']
        total_ticks = 0
        weighted_bpm = 0
        for i, tm in enumerate(tempos):
            bpm = 60_000_000 / tm['data']
            if i + 1 < len(tempos):
                dur = tempos[i + 1]['tick'] - tm['tick']
            else:
                dur = max(1, midi_dict.note_msgs[-1]['data']['end'] - tm['tick']
                          if midi_dict.note_msgs else 1)
            bpm = max(30, min(300, bpm))
            weighted_bpm += bpm * dur
            total_ticks += dur
        return weighted_bpm / total_ticks if total_ticks > 0 else None
    except Exception:
        return None


def is_jazz_like(filepath):
    name = (os.path.basename(filepath) + os.path.dirname(filepath)).lower()
    return any(kw in name for kw in JAZZ_KEYWORDS)


def detect_source(filepath):
    path_lower = filepath.lower()
    for src in ['maestro', 'atepp', 'asap', 'pop909', 'gigamidi', 'aria-midi', 'lakh']:
        if src in path_lower:
            return src
    return 'unknown'


def detect_mood(filepath, bpm):
    name = os.path.basename(filepath).lower()
    parent = os.path.dirname(filepath).lower()
    for comp in LYRICAL_COMPOSERS:
        if comp in name or comp in parent:
            return 'lyrical'
    if bpm and bpm < 90:
        return 'lyrical'
    if bpm and bpm > 150:
        return 'energetic'
    return None


def detect_genre(filepath, source):
    if source == 'pop909':
        return 'pop'
    name = os.path.basename(filepath).lower()
    parent = os.path.dirname(filepath).lower()
    for comp in LYRICAL_COMPOSERS:
        if comp in name or comp in parent:
            return 'classical'
    if source in ('maestro', 'atepp', 'asap'):
        return 'classical'
    return None


def tokenize_midi(midi_path, tokenizer, genre=None, tempo=None):
    try:
        midi_dict = MidiDict.from_midi(midi_path)
        seq = tokenizer.tokenize(midi_dict)
        if not seq or len(seq) < 20:
            return None
        prefix = []
        if genre:
            prefix.append(('prefix', 'genre', genre))
        if tempo:
            prefix.append(('prefix', 'tempo', tempo))
        prefix.append(('prefix', 'instrument', 'piano'))
        s_idx = None
        for i, tok in enumerate(seq):
            if tok == tokenizer.bos_tok:
                s_idx = i
                break
        if s_idx is None:
            seq = prefix + [tokenizer.bos_tok] + seq
        else:
            seq = prefix + seq[s_idx:]
        return seq
    except Exception:
        return None


def seq_to_json(seq):
    return [list(t) if isinstance(t, tuple) else t for t in seq]


def json_to_seq(json_seq):
    return [tuple(t) if isinstance(t, list) else t for t in json_seq]


def append_seq_to_file(filepath, seq):
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(seq_to_json(seq), ensure_ascii=False) + '\n')


def count_lines(filepath):
    if not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for _ in f:
            count += 1
    return count


def read_seqs_from_file(filepath):
    seqs = []
    if not os.path.exists(filepath):
        return seqs
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                seqs.append(json_to_seq(json.loads(line)))
    return seqs


def save_checkpoint(idx, skipped_jazz, tempo_stats, source_stats):
    data = {
        'last_processed_idx': idx,
        'skipped_jazz': skipped_jazz,
        'tempo_stats': tempo_stats,
        'source_stats': source_stats,
    }
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def build_sequences(all_seqs, max_seq_len, tokenizer):
    output = []
    buffer = []
    for seq in all_seqs:
        buffer.extend(seq)
        buffer.append(tokenizer.eos_tok)
        while len(buffer) >= max_seq_len:
            output.append(buffer[:max_seq_len])
            buffer = buffer[max_seq_len:]
    if len(buffer) > 100:
        output.append(buffer[:max_seq_len])
    return output


def find_midis(base_dir):
    result = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(('.mid', '.midi')):
                result.append(os.path.join(root, f))
    return result


def main():
    global LOG_PATH
    os.makedirs(P3_OUTPUT, exist_ok=True)
    LOG_PATH = os.path.join(P3_OUTPUT, 'prepare_log_v2.txt')

    log("=" * 60)
    log("Quincy P3 Data Preparation v2 - Lyrical Piano Focus")
    log("=" * 60)

    tokenizer = AbsTokenizer()
    log(f"Vocab size: {tokenizer.vocab_size}")

    # === Phase 1: Process tier1_premium MIDI files (disk-based) ===
    log("\n=== Phase 1: tier1_premium MIDI ===")
    midis = find_midis(TIER1_DIR)
    midis.sort()  # deterministic order for resume
    log(f"Found {len(midis)} MIDI files in tier1_premium")

    # Check for resume
    ckpt = load_checkpoint()
    start_idx = 0
    skipped_jazz = 0
    tempo_stats = {'slow': 0, 'medium': 0, 'fast': 0, 'very_fast': 0, 'unknown': 0}
    source_stats = {}

    if ckpt:
        start_idx = ckpt['last_processed_idx'] + 1
        skipped_jazz = ckpt['skipped_jazz']
        tempo_stats = ckpt['tempo_stats']
        source_stats = ckpt['source_stats']
        log(f"  RESUMING from index {start_idx} (checkpoint found)")
        log(f"  Previous: jazz_skipped={skipped_jazz}, lyrical={count_lines(LYRICAL_TEMP)}, standard={count_lines(STANDARD_TEMP)}")
    else:
        # Fresh start — clear temp files
        for f in [LYRICAL_TEMP, STANDARD_TEMP]:
            if os.path.exists(f):
                os.remove(f)
        log("  Starting fresh")

    for i in range(start_idx, len(midis)):
        midi_path = midis[i]

        if i % 5000 == 0:
            log(f"  Processing {i}/{len(midis)}...")
            # Save checkpoint every 5000
            if i > start_idx:
                save_checkpoint(i - 1, skipped_jazz, tempo_stats, source_stats)

        if is_jazz_like(midi_path):
            skipped_jazz += 1
            continue

        source = detect_source(midi_path)
        source_stats[source] = source_stats.get(source, 0) + 1

        bpm = get_midi_bpm_strict(midi_path)
        tempo = classify_tempo(bpm)
        genre = detect_genre(midi_path, source)

        seq = tokenize_midi(midi_path, tokenizer, genre=genre, tempo=tempo)
        if not seq:
            continue

        if tempo:
            tempo_stats[tempo] += 1
        else:
            tempo_stats['unknown'] += 1

        # Write to disk immediately
        if source in LYRICAL_SOURCES:
            append_seq_to_file(LYRICAL_TEMP, seq)
        else:
            append_seq_to_file(STANDARD_TEMP, seq)

    # Final checkpoint
    save_checkpoint(len(midis) - 1, skipped_jazz, tempo_stats, source_stats)

    lyrical_count = count_lines(LYRICAL_TEMP)
    standard_count = count_lines(STANDARD_TEMP)
    log(f"\nPhase 1 results:")
    log(f"  Lyrical (MAESTRO/ATEPP/ASAP): {lyrical_count}")
    log(f"  Standard: {standard_count}")
    log(f"  Jazz skipped: {skipped_jazz}")
    log(f"  Tempo: {tempo_stats}")
    log(f"  Sources: {source_stats}")

    # === Phase 2: Load sequences and upsample lyrical ===
    log(f"\n=== Phase 2: Upsample lyrical {LYRICAL_UPSAMPLE}x ===")
    lyrical_seqs = read_seqs_from_file(LYRICAL_TEMP)
    standard_seqs = read_seqs_from_file(STANDARD_TEMP)
    log(f"  Loaded lyrical: {len(lyrical_seqs)}, standard: {len(standard_seqs)}")

    lyrical_upsampled = lyrical_seqs * LYRICAL_UPSAMPLE
    log(f"  Lyrical after upsample: {len(lyrical_upsampled)}")

    # === Phase 3: Load P2 existing data ===
    log("\n=== Phase 3: Reuse P2 data ===")
    p2_train_path = os.path.join(P2_OUTPUT, 'data', 'train_data', 'epoch0.jsonl')
    p2_seqs = []
    if os.path.exists(p2_train_path):
        with open(p2_train_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue
                obj = json.loads(line)
                if 'seq' in obj:
                    seq = [tuple(t) if isinstance(t, list) else t for t in obj['seq']]
                    p2_seqs.append(seq)
        log(f"  P2 train sequences loaded: {len(p2_seqs)}")
    else:
        log(f"  P2 data not found at {p2_train_path}, skipping")

    # === Phase 4: Build final dataset ===
    log("\n=== Phase 4: Build final dataset ===")

    lyrical_chunks = build_sequences(lyrical_upsampled, MAX_SEQ_LEN, tokenizer)
    standard_chunks = build_sequences(standard_seqs, MAX_SEQ_LEN, tokenizer)
    log(f"  Lyrical chunks: {len(lyrical_chunks)}")
    log(f"  Standard chunks: {len(standard_chunks)}")

    # Free memory
    del lyrical_seqs, lyrical_upsampled, standard_seqs

    all_train = lyrical_chunks + p2_seqs + standard_chunks
    random.shuffle(all_train)
    log(f"  Total train: {len(all_train)}")

    # Val set
    val_count_l = max(1, len(lyrical_chunks) // 20)
    val_count_s = max(1, len(standard_chunks) // 20)
    all_val = lyrical_chunks[:val_count_l] + standard_chunks[:val_count_s]
    random.shuffle(all_val)
    log(f"  Total val: {len(all_val)}")

    del lyrical_chunks, standard_chunks, p2_seqs

    # === Write ===
    train_dir = os.path.join(P3_OUTPUT, 'data', 'train_data')
    val_dir = os.path.join(P3_OUTPUT, 'data', 'val_data')
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)

    def write_jsonl(seqs, output_path, epoch_name="epoch0"):
        fpath = os.path.join(output_path, f'{epoch_name}.jsonl')
        with open(fpath, 'w', encoding='utf-8') as f:
            header = {
                "tokenizer_config": {"name": "abs", "version": "p3_lyrical"},
                "tokenizer_name": "abs",
                "max_seq_len": MAX_SEQ_LEN
            }
            f.write(json.dumps(header, ensure_ascii=False) + '\n')
            for seq in seqs:
                json_seq = [list(t) if isinstance(t, tuple) else t for t in seq]
                f.write(json.dumps({"seq": json_seq}, ensure_ascii=False) + '\n')
        size_mb = os.path.getsize(fpath) / 1024 / 1024
        log(f"  Written: {fpath} ({size_mb:.1f}MB, {len(seqs)} seqs)")

    for ep in range(3):
        random.shuffle(all_train)
        write_jsonl(all_train, train_dir, f'epoch{ep}')

    write_jsonl(all_val, val_dir, 'epoch0')

    # Cleanup temp files
    for f in [LYRICAL_TEMP, STANDARD_TEMP, CHECKPOINT_FILE]:
        if os.path.exists(f):
            os.remove(f)

    log("\n=== Summary ===")
    log(f"  Total: {len(all_train)} train, {len(all_val)} val")
    log(f"  Output: {P3_OUTPUT}")
    log("=== DONE ===")


if __name__ == '__main__':
    main()
