"""
Quincy P2 Data Preparation — Tempo-labeled
Adds tempo prefix (slow/medium/fast/very_fast) based on MIDI BPM.
Re-tokenizes P1 data + adds tempo prefix.

Tempo ranges:
  slow:      60-89 BPM
  medium:    90-119 BPM
  fast:      120-159 BPM
  very_fast: 160+ BPM

Usage (on 5090):
  python prepare_p2_data.py
"""
import sys
import os
import json
import glob
import random
import time

sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, r'C:\Users\leo\liszt\aria')

from ariautils.tokenizer import AbsTokenizer
from ariautils.midi import MidiDict

TRAINING_DATA = r'C:\Users\leo\liszt\training_data'
P1_DATA_DIR = r'D:\liszt\output\liszt_v9_prefix\data'
OUTPUT_DIR = r'D:\liszt\output\quincy_p2\data'
MAX_SEQ_LEN = 8192

# Tempo classification
TEMPO_RANGES = [
    ('slow', 60, 89),
    ('medium', 90, 119),
    ('fast', 120, 159),
    ('very_fast', 160, 999),
]

# Composer mapping
COMPOSER_MAP = {
    'bach': 'bach', 'beethoven': 'beethoven', 'mozart': 'mozart',
    'chopin': 'chopin', 'rachmaninoff': 'rachmaninoff', 'liszt': 'liszt',
    'debussy': 'debussy', 'schubert': 'schubert', 'brahms': 'brahms',
    'ravel': 'ravel', 'satie': 'satie', 'scarlatti': 'scarlatti',
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
    """Classify BPM into tempo category."""
    if bpm < 60:
        return 'slow'  # treat very slow as slow
    for name, lo, hi in TEMPO_RANGES:
        if lo <= bpm <= hi:
            return name
    return 'medium'  # fallback


def get_midi_bpm(midi_path):
    """Extract average BPM from MIDI file."""
    try:
        midi_dict = MidiDict.from_midi(midi_path)
        if not midi_dict.tempo_msgs:
            return None
        # tempo_msgs are dicts: {'type': 'tempo', 'data': microsec_per_beat, 'tick': N}
        tempos = midi_dict.tempo_msgs
        if len(tempos) == 1:
            return 60_000_000 / tempos[0]['data']
        total_time = 0
        weighted_bpm = 0
        for i, tm in enumerate(tempos):
            bpm = 60_000_000 / tm['data']
            if i + 1 < len(tempos):
                dur = tempos[i + 1]['tick'] - tm['tick']
            else:
                dur = 1
            weighted_bpm += bpm * dur
            total_time += dur
        return weighted_bpm / total_time if total_time > 0 else None
    except Exception:
        return None


def detect_composer(filepath):
    """Try to detect composer from filepath."""
    name = os.path.basename(filepath).lower()
    parent = os.path.basename(os.path.dirname(filepath)).lower()
    for key, composer in COMPOSER_MAP.items():
        if key in name or key in parent:
            return composer
    return None


def tokenize_midi(midi_path, tokenizer, genre=None, composer=None, tempo=None):
    """Tokenize a single MIDI file with genre/composer/tempo prefix."""
    try:
        midi_dict = MidiDict.from_midi(midi_path)
        seq = tokenizer.tokenize(midi_dict)
        if not seq or len(seq) < 10:
            return None

        # Build prefix: genre -> composer -> tempo -> instrument
        prefix = []
        if genre:
            prefix.append(('prefix', 'genre', genre))
        if composer:
            prefix.append(('prefix', 'composer', composer))
        if tempo:
            prefix.append(('prefix', 'tempo', tempo))
        prefix.append(('prefix', 'instrument', 'piano'))

        # Find <S> position and replace prefix
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


def add_tempo_to_existing_seq(seq, tempo, tokenizer):
    """Add tempo prefix to an existing tokenized sequence."""
    tempo_tok = ('prefix', 'tempo', tempo)

    # Find where to insert: after last existing prefix, before <S>
    # Sequence format: [prefix_tokens...] <S> [music_tokens...]
    insert_idx = 0
    for i, tok in enumerate(seq):
        if isinstance(tok, tuple) and tok[0] == 'prefix':
            insert_idx = i + 1
        elif tok == tokenizer.bos_tok:
            insert_idx = i  # insert before <S>
            break

    return seq[:insert_idx] + [tempo_tok] + seq[insert_idx:]


def find_midis(base_dir, source):
    """Find all .mid files under base_dir/source/"""
    src_dir = os.path.join(base_dir, source)
    if not os.path.isdir(src_dir):
        return []
    result = []
    seen = set()
    for root, dirs, files in os.walk(src_dir):
        for f in files:
            if f.lower().endswith(('.mid', '.midi')):
                full = os.path.join(root, f)
                key = full.lower()
                if key not in seen:
                    seen.add(key)
                    result.append(full)
    return result


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


def main():
    global LOG_PATH
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    LOG_PATH = os.path.join(OUTPUT_DIR, 'prepare_log.txt')

    log("=== Quincy P2 Data Preparation ===")
    log(f"Tempo ranges: {TEMPO_RANGES}")

    tokenizer = AbsTokenizer()
    log(f"Vocab size: {tokenizer.vocab_size}")

    # Verify tempo tokens exist
    for t in ['slow', 'medium', 'fast', 'very_fast']:
        tok = ('prefix', 'tempo', t)
        assert tok in tokenizer.tok_to_id, f"Missing tempo token: {tok}"
    log("Tempo tokens verified in tokenizer")

    # === Strategy: Re-tokenize from MIDI with tempo prefix ===
    # Rather than patching existing JSONL, re-process from MIDI files
    # to get accurate BPM per file.

    sources = {
        'pop909': 'pop',
        'atepp': None,  # detect composer
        'asap': None,
        'maestro': None,
    }

    all_seqs = []
    tempo_stats = {'slow': 0, 'medium': 0, 'fast': 0, 'very_fast': 0, 'unknown': 0}

    for source, genre in sources.items():
        midis = find_midis(TRAINING_DATA, source)
        log(f"\n--- {source}: {len(midis)} MIDI files ---")

        for midi_path in midis:
            bpm = get_midi_bpm(midi_path)
            tempo = classify_tempo(bpm) if bpm else None
            composer = detect_composer(midi_path)

            # For pop909, always genre=pop
            if source == 'pop909':
                g = 'pop'
            elif composer:
                g = 'classical'
            else:
                g = genre

            seq = tokenize_midi(midi_path, tokenizer, genre=g, composer=composer, tempo=tempo)
            if seq:
                all_seqs.append(seq)
                if tempo:
                    tempo_stats[tempo] += 1
                else:
                    tempo_stats['unknown'] += 1

        log(f"  Tokenized: {len(all_seqs)} total so far")

    # Also process existing V5 Pop training data (large set without genre labels)
    v5_train = r'C:\Users\leo\liszt\output\liszt_v5_pop\train_data\epoch0.jsonl'
    v5_val = r'C:\Users\leo\liszt\output\liszt_v5_pop\val_data\epoch0.jsonl'

    def read_existing_jsonl(path):
        seqs = []
        with open(path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue
                obj = json.loads(line)
                if 'seq' in obj:
                    seq = [tuple(t) if isinstance(t, list) else t for t in obj['seq']]
                    seqs.append(seq)
        return seqs

    log(f"\n--- Existing V5 Pop data ---")
    existing_train = read_existing_jsonl(v5_train)
    existing_val = read_existing_jsonl(v5_val)
    log(f"  Train: {len(existing_train)}, Val: {len(existing_val)}")

    # For existing data, we can't easily get BPM (already tokenized).
    # Strategy: estimate tempo from onset tokens in the sequence.
    def estimate_tempo_from_seq(seq):
        """Rough BPM estimation from tokenized onset patterns."""
        onsets = []
        for tok in seq:
            if isinstance(tok, tuple) and tok[0] == 'onset':
                onsets.append(tok[1])
        if len(onsets) < 4:
            return None
        # Average inter-onset interval
        diffs = [onsets[i+1] - onsets[i] for i in range(min(len(onsets)-1, 50))
                 if onsets[i+1] > onsets[i]]
        if not diffs:
            return None
        avg_ioi_ms = sum(diffs) / len(diffs)
        if avg_ioi_ms <= 0:
            return None
        # Rough BPM: assume each onset ~= a beat (very rough)
        bpm = 60000 / avg_ioi_ms
        # Clamp to reasonable range
        while bpm > 200:
            bpm /= 2
        while bpm < 40:
            bpm *= 2
        return bpm

    log("Estimating tempo for existing sequences...")
    for seq in existing_train:
        bpm = estimate_tempo_from_seq(seq)
        tempo = classify_tempo(bpm) if bpm else None
        if tempo:
            seq_with_tempo = add_tempo_to_existing_seq(seq, tempo, tokenizer)
            all_seqs.append(seq_with_tempo)
            tempo_stats[tempo] += 1
        else:
            all_seqs.append(seq)  # keep without tempo prefix
            tempo_stats['unknown'] += 1

    # Val data
    val_seqs = []
    for seq in existing_val:
        bpm = estimate_tempo_from_seq(seq)
        tempo = classify_tempo(bpm) if bpm else None
        if tempo:
            val_seqs.append(add_tempo_to_existing_seq(seq, tempo, tokenizer))
        else:
            val_seqs.append(seq)

    log(f"\nTempo distribution: {tempo_stats}")
    log(f"Total sequences: {len(all_seqs)} train + {len(val_seqs)} val (from existing)")

    # === Build fixed-length chunks from newly tokenized MIDI ===
    # Separate new MIDI seqs from existing
    new_count = len(all_seqs) - len(existing_train)
    new_seqs = all_seqs[:new_count]
    existing_with_tempo = all_seqs[new_count:]

    new_chunks = build_sequences(new_seqs, MAX_SEQ_LEN, tokenizer)
    log(f"New MIDI chunks: {len(new_chunks)}")

    # Pop909 upsampling (10x like P1)
    pop_chunks = [c for c in new_chunks if any(
        isinstance(t, tuple) and len(t) == 3 and t[2] == 'pop'
        for t in c[:10]
    )]
    if pop_chunks:
        upsample = pop_chunks * 9  # already have 1x
        new_chunks.extend(upsample)
        log(f"Pop upsampled: {len(pop_chunks)} x 10 = {len(pop_chunks)*10}")

    # Merge
    all_train = existing_with_tempo + new_chunks
    all_val = val_seqs + build_sequences(new_seqs[:len(new_seqs)//20 + 1], MAX_SEQ_LEN, tokenizer)
    random.shuffle(all_train)
    random.shuffle(all_val)

    log(f"Final: {len(all_train)} train, {len(all_val)} val")

    # === Write JSONL ===
    train_dir = os.path.join(OUTPUT_DIR, 'train_data')
    val_dir = os.path.join(OUTPUT_DIR, 'val_data')
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)

    def write_jsonl(seqs, output_path, epoch_name="epoch0"):
        fpath = os.path.join(output_path, f'{epoch_name}.jsonl')
        with open(fpath, 'w', encoding='utf-8') as f:
            header = {
                "tokenizer_config": {"name": "abs", "version": "p2_tempo"},
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

    # Summary
    log("\n=== Summary ===")
    log(f"  Tempo distribution: {tempo_stats}")
    log(f"  Total: {len(all_train)} train, {len(all_val)} val")
    log(f"  Output: {OUTPUT_DIR}")
    log("=== DONE ===")


if __name__ == '__main__':
    main()
