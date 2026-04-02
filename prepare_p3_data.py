"""
Quincy P3 Data Preparation — Lyrical Piano Focus
=================================================
P2 Issues:
  - Tempo prefix ignored (est_bpm random 101-200)
  - Jazz harmony dominance

P3 Strategy:
  - Focus on lyrical/emotional piano (upsample MAESTRO, ATEPP, ASAP)
  - Reduce jazz-heavy data ratio
  - Keep tempo prefix but with corrected BPM estimation
  - Add "mood" prefix: lyrical, energetic, dramatic
  - Use tier1_premium as primary source

Usage (on 5090):
  python prepare_p3_data.py
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

# Tempo classification (same as P2 but stricter BPM estimation)
TEMPO_RANGES = [
    ('slow', 40, 89),
    ('medium', 90, 119),
    ('fast', 120, 159),
    ('very_fast', 160, 240),
]

# Sources to upsample for lyrical quality
LYRICAL_SOURCES = {'maestro', 'atepp', 'asap'}
LYRICAL_UPSAMPLE = 8  # 8x for lyrical performance sources

# Jazz-indicative patterns to downweight
JAZZ_KEYWORDS = {'jazz', 'swing', 'bebop', 'bossa', 'blues'}

# Lyrical composer keywords (for mood detection)
LYRICAL_COMPOSERS = {
    'chopin', 'debussy', 'satie', 'ravel', 'liszt',
    'rachmaninoff', 'schubert', 'schumann', 'grieg',
    'sakamoto', 'yiruma', 'einaudi', 'hisaishi', 'nils frahm',
    'ludovico', 'tiersen', 'olafur arnalds',
}

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
    """More accurate BPM estimation using weighted average of tempo changes."""
    try:
        midi_dict = MidiDict.from_midi(midi_path)
        if not midi_dict.tempo_msgs:
            return None

        tempos = midi_dict.tempo_msgs
        if len(tempos) == 1:
            return 60_000_000 / tempos[0]['data']

        # Use tick-weighted average
        total_ticks = 0
        weighted_bpm = 0
        for i, tm in enumerate(tempos):
            bpm = 60_000_000 / tm['data']
            if i + 1 < len(tempos):
                dur = tempos[i + 1]['tick'] - tm['tick']
            else:
                dur = max(1, midi_dict.note_msgs[-1]['data']['end'] - tm['tick']
                          if midi_dict.note_msgs else 1)
            # Clamp extreme tempos
            bpm = max(30, min(300, bpm))
            weighted_bpm += bpm * dur
            total_ticks += dur

        return weighted_bpm / total_ticks if total_ticks > 0 else None
    except Exception:
        return None


def is_jazz_like(filepath):
    """Check if filepath suggests jazz content."""
    name = (os.path.basename(filepath) + os.path.dirname(filepath)).lower()
    return any(kw in name for kw in JAZZ_KEYWORDS)


def detect_source(filepath):
    """Detect source from path."""
    path_lower = filepath.lower()
    for src in ['maestro', 'atepp', 'asap', 'pop909', 'gigamidi', 'aria-midi', 'lakh']:
        if src in path_lower:
            return src
    return 'unknown'


def detect_mood(filepath, bpm):
    """Simple mood classification for prefix."""
    name = os.path.basename(filepath).lower()
    parent = os.path.dirname(filepath).lower()

    # Check for lyrical composer
    for comp in LYRICAL_COMPOSERS:
        if comp in name or comp in parent:
            return 'lyrical'

    # Tempo-based heuristic
    if bpm and bpm < 90:
        return 'lyrical'
    if bpm and bpm > 150:
        return 'energetic'

    return None  # no mood prefix


def detect_genre(filepath, source):
    """Detect genre."""
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
    """Tokenize MIDI with prefix."""
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


def build_sequences(all_seqs, max_seq_len, tokenizer):
    """Concatenate short sequences into fixed-length chunks."""
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
    """Find all .mid files recursively."""
    result = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith(('.mid', '.midi')):
                result.append(os.path.join(root, f))
    return result


def main():
    global LOG_PATH
    os.makedirs(P3_OUTPUT, exist_ok=True)
    LOG_PATH = os.path.join(P3_OUTPUT, 'prepare_log.txt')

    log("=" * 60)
    log("Quincy P3 Data Preparation — Lyrical Piano Focus")
    log("=" * 60)

    tokenizer = AbsTokenizer()
    log(f"Vocab size: {tokenizer.vocab_size}")

    # === Phase 1: Process tier1_premium MIDI files ===
    log("\n=== Phase 1: tier1_premium MIDI ===")
    midis = find_midis(TIER1_DIR)
    log(f"Found {len(midis)} MIDI files in tier1_premium")

    lyrical_seqs = []
    standard_seqs = []
    skipped_jazz = 0
    tempo_stats = {'slow': 0, 'medium': 0, 'fast': 0, 'very_fast': 0, 'unknown': 0}
    source_stats = {}

    for i, midi_path in enumerate(midis):
        if i % 5000 == 0:
            log(f"  Processing {i}/{len(midis)}...")

        # Skip jazz-like files
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

        # Categorize as lyrical or standard
        if source in LYRICAL_SOURCES:
            lyrical_seqs.append(seq)
        else:
            standard_seqs.append(seq)

    log(f"\nPhase 1 results:")
    log(f"  Lyrical (MAESTRO/ATEPP/ASAP): {len(lyrical_seqs)}")
    log(f"  Standard: {len(standard_seqs)}")
    log(f"  Jazz skipped: {skipped_jazz}")
    log(f"  Tempo: {tempo_stats}")
    log(f"  Sources: {source_stats}")

    # === Phase 2: Upsample lyrical sources ===
    log(f"\n=== Phase 2: Upsample lyrical {LYRICAL_UPSAMPLE}x ===")
    lyrical_upsampled = lyrical_seqs * LYRICAL_UPSAMPLE
    log(f"  Lyrical after upsample: {len(lyrical_upsampled)}")

    # === Phase 3: Load P2 existing data (for continuity) ===
    log("\n=== Phase 3: Reuse P2 data ===")
    p2_train_path = os.path.join(P2_OUTPUT, 'data', 'train_data', 'epoch0.jsonl')
    p2_seqs = []
    if os.path.exists(p2_train_path):
        with open(p2_train_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue  # header
                obj = json.loads(line)
                if 'seq' in obj:
                    seq = [tuple(t) if isinstance(t, list) else t for t in obj['seq']]
                    p2_seqs.append(seq)
        log(f"  P2 train sequences loaded: {len(p2_seqs)}")
    else:
        log(f"  P2 data not found at {p2_train_path}, skipping")

    # === Phase 4: Build final dataset ===
    log("\n=== Phase 4: Build final dataset ===")

    # Build chunks
    lyrical_chunks = build_sequences(lyrical_upsampled, MAX_SEQ_LEN, tokenizer)
    standard_chunks = build_sequences(standard_seqs, MAX_SEQ_LEN, tokenizer)
    log(f"  Lyrical chunks: {len(lyrical_chunks)}")
    log(f"  Standard chunks: {len(standard_chunks)}")

    # Combine: P2 data + new lyrical-enriched data
    # Ratio target: ~40% lyrical, ~40% P2 continuity, ~20% new standard
    all_train = lyrical_chunks + p2_seqs + standard_chunks
    random.shuffle(all_train)
    log(f"  Total train: {len(all_train)}")

    # Val set: 5% of lyrical + 5% of standard
    val_lyrical = build_sequences(lyrical_seqs[:max(1, len(lyrical_seqs)//20)], MAX_SEQ_LEN, tokenizer)
    val_standard = build_sequences(standard_seqs[:max(1, len(standard_seqs)//20)], MAX_SEQ_LEN, tokenizer)
    all_val = val_lyrical + val_standard
    random.shuffle(all_val)
    log(f"  Total val: {len(all_val)}")

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

    log("\n=== Summary ===")
    log(f"  Lyrical: {len(lyrical_chunks)} chunks ({LYRICAL_UPSAMPLE}x upsampled from {len(lyrical_seqs)} seqs)")
    log(f"  Standard: {len(standard_chunks)} chunks")
    log(f"  P2 continuity: {len(p2_seqs)} seqs")
    log(f"  Jazz skipped: {skipped_jazz}")
    log(f"  Total: {len(all_train)} train, {len(all_val)} val")
    log(f"  Output: {P3_OUTPUT}")
    log("=== DONE ===")


if __name__ == '__main__':
    main()
