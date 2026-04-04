"""
Quincy P3 Phase 2+ Streaming Resume
====================================
Resumes from temp_lyrical.jsonl and temp_standard.jsonl written by v2 script.
Stream-based to avoid OOM on 17GB+ data.

Usage (on 5090):
  python prepare_p3_phase2_stream.py
"""
import sys
import os
import json
import random
import time

sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, r'C:\Users\leo\liszt\aria')

from ariautils.tokenizer import AbsTokenizer

# Paths
P2_OUTPUT = r'D:\liszt\output\quincy_p2'
P3_OUTPUT = r'D:\liszt\output\quincy_p3'
LYRICAL_TEMP = os.path.join(P3_OUTPUT, 'temp_lyrical.jsonl')
STANDARD_TEMP = os.path.join(P3_OUTPUT, 'temp_standard.jsonl')
ALL_CHUNKS_TEMP = os.path.join(P3_OUTPUT, 'temp_all_chunks.jsonl')
VAL_CHUNKS_TEMP = os.path.join(P3_OUTPUT, 'temp_val_chunks.jsonl')

MAX_SEQ_LEN = 8192
LYRICAL_UPSAMPLE = 8

LOG_PATH = os.path.join(P3_OUTPUT, 'phase2_stream_log.txt')


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def json_to_seq(json_seq):
    return [tuple(t) if isinstance(t, list) else t for t in json_seq]


def seq_to_json(seq):
    return [list(t) if isinstance(t, tuple) else t for t in seq]


def iter_seqs(filepath):
    """Yield sequences from a JSONL file one at a time."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json_to_seq(json.loads(line))


def stream_chunks_to_file(seq_iter, out_file, tokenizer, max_seq_len=MAX_SEQ_LEN):
    """Stream sequences, build max_seq_len chunks, append to out_file. Returns chunk count."""
    buffer = []
    chunks_written = 0
    for seq in seq_iter:
        buffer.extend(seq)
        buffer.append(tokenizer.eos_tok)
        while len(buffer) >= max_seq_len:
            chunk = buffer[:max_seq_len]
            out_file.write(json.dumps(seq_to_json(chunk), ensure_ascii=False) + '\n')
            chunks_written += 1
            buffer = buffer[max_seq_len:]
    if len(buffer) > 100:
        # pad remaining
        chunk = buffer[:max_seq_len]
        out_file.write(json.dumps(seq_to_json(chunk), ensure_ascii=False) + '\n')
        chunks_written += 1
    return chunks_written


def iter_lyrical_upsampled(lyrical_path, times):
    """Yield lyrical sequences repeated `times` times (no memory duplication)."""
    for _ in range(times):
        for seq in iter_seqs(lyrical_path):
            yield seq


def iter_p2_data(p2_path):
    """Yield sequences from P2 epoch0.jsonl (with header)."""
    if not os.path.exists(p2_path):
        return
    with open(p2_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i == 0:
                continue  # header
            obj = json.loads(line)
            if 'seq' in obj:
                yield json_to_seq(obj['seq'])


def build_line_offsets(filepath):
    """Build list of byte offsets for each line."""
    offsets = []
    with open(filepath, 'rb') as f:
        offset = f.tell()
        line = f.readline()
        while line:
            offsets.append(offset)
            offset = f.tell()
            line = f.readline()
    return offsets


def write_shuffled_epoch(src_path, offsets_order, dst_path, header):
    """Read lines from src in shuffled order, write to dst with header."""
    with open(src_path, 'rb') as src, open(dst_path, 'w', encoding='utf-8') as dst:
        dst.write(json.dumps(header, ensure_ascii=False) + '\n')
        for off in offsets_order:
            src.seek(off)
            line = src.readline().decode('utf-8').strip()
            obj = json.loads(line)
            dst.write(json.dumps({"seq": obj}, ensure_ascii=False) + '\n')


def main():
    log("=" * 60)
    log("Quincy P3 Phase 2+ Streaming Resume")
    log("=" * 60)

    tokenizer = AbsTokenizer()
    log(f"Vocab size: {tokenizer.vocab_size}")

    # Verify temp files exist
    if not os.path.exists(LYRICAL_TEMP) or not os.path.exists(STANDARD_TEMP):
        log(f"ERROR: temp files missing. lyrical={os.path.exists(LYRICAL_TEMP)}, standard={os.path.exists(STANDARD_TEMP)}")
        return
    log(f"  temp_lyrical: {os.path.getsize(LYRICAL_TEMP)/1e6:.1f}MB")
    log(f"  temp_standard: {os.path.getsize(STANDARD_TEMP)/1e6:.1f}MB")

    # === Phase 2+3+4 (streaming): build all chunks to single file ===
    log("\n=== Building all_chunks (streaming) ===")
    total_chunks = 0
    with open(ALL_CHUNKS_TEMP, 'w', encoding='utf-8') as out:
        log("  Processing lyrical (8x upsample)...")
        count = stream_chunks_to_file(
            iter_lyrical_upsampled(LYRICAL_TEMP, LYRICAL_UPSAMPLE),
            out, tokenizer
        )
        log(f"  Lyrical chunks: {count}")
        total_chunks += count

        log("  Processing standard...")
        count = stream_chunks_to_file(iter_seqs(STANDARD_TEMP), out, tokenizer)
        log(f"  Standard chunks: {count}")
        total_chunks += count

        log("  Processing P2 continuity data...")
        p2_train_path = os.path.join(P2_OUTPUT, 'data', 'train_data', 'epoch0.jsonl')
        p2_count = stream_chunks_to_file(iter_p2_data(p2_train_path), out, tokenizer)
        log(f"  P2 chunks: {p2_count}")
        total_chunks += p2_count

    log(f"\nTotal chunks: {total_chunks}")
    log(f"all_chunks file size: {os.path.getsize(ALL_CHUNKS_TEMP)/1e9:.2f}GB")

    # === Build val chunks (small sample) ===
    log("\n=== Building val chunks ===")
    val_chunks = 0
    with open(VAL_CHUNKS_TEMP, 'w', encoding='utf-8') as out:
        # 5% of lyrical + 5% of standard (limited sample for speed)
        log("  Val from lyrical...")
        # Take first 5% of raw lyrical seqs
        lyrical_for_val = []
        for i, seq in enumerate(iter_seqs(LYRICAL_TEMP)):
            if i >= max(1, 2719 // 20):
                break
            lyrical_for_val.append(seq)
        vc = stream_chunks_to_file(iter(lyrical_for_val), out, tokenizer)
        log(f"  Val lyrical chunks: {vc}")
        val_chunks += vc

        log("  Val from standard...")
        def iter_standard_sample(limit):
            with open(STANDARD_TEMP, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i >= limit:
                        break
                    yield json_to_seq(json.loads(line))
        vc = stream_chunks_to_file(iter_standard_sample(149941 // 20), out, tokenizer)
        log(f"  Val standard chunks: {vc}")
        val_chunks += vc

    log(f"Total val chunks: {val_chunks}")

    # === Build line offsets for shuffling (tiny memory) ===
    log("\n=== Building line offsets for shuffle ===")
    train_offsets = build_line_offsets(ALL_CHUNKS_TEMP)
    val_offsets = build_line_offsets(VAL_CHUNKS_TEMP)
    log(f"  Train offsets: {len(train_offsets)}")
    log(f"  Val offsets: {len(val_offsets)}")

    # === Write epoch files with shuffled order ===
    log("\n=== Writing epoch files ===")
    train_dir = os.path.join(P3_OUTPUT, 'data', 'train_data')
    val_dir = os.path.join(P3_OUTPUT, 'data', 'val_data')
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)

    header = {
        "tokenizer_config": {"name": "abs", "version": "p3_lyrical"},
        "tokenizer_name": "abs",
        "max_seq_len": MAX_SEQ_LEN
    }

    for ep in range(3):
        shuffled = list(train_offsets)
        random.shuffle(shuffled)
        fpath = os.path.join(train_dir, f'epoch{ep}.jsonl')
        write_shuffled_epoch(ALL_CHUNKS_TEMP, shuffled, fpath, header)
        size_mb = os.path.getsize(fpath) / 1024 / 1024
        log(f"  Written: {fpath} ({size_mb:.1f}MB, {len(shuffled)} chunks)")

    shuffled_val = list(val_offsets)
    random.shuffle(shuffled_val)
    val_path = os.path.join(val_dir, 'epoch0.jsonl')
    write_shuffled_epoch(VAL_CHUNKS_TEMP, shuffled_val, val_path, header)
    log(f"  Written: {val_path} ({len(shuffled_val)} chunks)")

    # Cleanup temp
    log("\n=== Cleanup ===")
    for f in [ALL_CHUNKS_TEMP, VAL_CHUNKS_TEMP, LYRICAL_TEMP, STANDARD_TEMP]:
        if os.path.exists(f):
            os.remove(f)
            log(f"  Removed: {f}")

    log("\n=== Summary ===")
    log(f"  Total train chunks: {total_chunks}")
    log(f"  Total val chunks: {val_chunks}")
    log(f"  Output: {P3_OUTPUT}")
    log("=== DONE ===")


if __name__ == '__main__':
    main()
