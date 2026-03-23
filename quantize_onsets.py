"""
Onset Quantization Post-Processor for Liszt MIDI output.

Snaps note onsets to the nearest beat grid position (default: 16th note).
Preserves relative timing within chords (notes starting within a small window).
"""

import pretty_midi
import numpy as np
import argparse
import os


def estimate_tempo(pm):
    """Estimate tempo from MIDI tempo changes, fallback to note density."""
    tempos = pm.get_tempo_changes()
    if len(tempos[1]) > 0:
        return float(np.median(tempos[1]))
    # Fallback: estimate from note density
    notes = sorted(
        [n for inst in pm.instruments for n in inst.notes],
        key=lambda n: n.start
    )
    if len(notes) < 2:
        return 120.0
    intervals = [notes[i+1].start - notes[i].start for i in range(min(len(notes)-1, 200))]
    intervals = [iv for iv in intervals if iv > 0.01]
    if not intervals:
        return 120.0
    median_interval = np.median(intervals)
    # Assume median interval ≈ 16th note
    bpm = 60.0 / (median_interval * 4)
    return np.clip(bpm, 40, 240)


def quantize_midi(input_path, output_path, grid_resolution=16, chord_window=0.03):
    """
    Quantize note onsets to nearest grid position.

    Args:
        input_path: Input MIDI file
        output_path: Output MIDI file
        grid_resolution: Grid resolution (4=quarter, 8=eighth, 16=sixteenth, 32=thirty-second)
        chord_window: Notes within this window (seconds) are treated as a chord
    """
    pm = pretty_midi.PrettyMIDI(input_path)
    tempo = estimate_tempo(pm)
    beat_duration = 60.0 / tempo
    grid_duration = beat_duration / (grid_resolution / 4)

    total_notes = 0
    quantized_notes = 0
    total_shift = 0.0

    for inst in pm.instruments:
        # Sort notes by start time
        inst.notes.sort(key=lambda n: n.start)

        # Group into chords (notes starting within chord_window)
        i = 0
        while i < len(inst.notes):
            chord_start = inst.notes[i].start
            chord = [inst.notes[i]]
            j = i + 1
            while j < len(inst.notes) and inst.notes[j].start - chord_start < chord_window:
                chord.append(inst.notes[j])
                j += 1

            # Snap chord to nearest grid
            avg_start = np.mean([n.start for n in chord])
            snapped = round(avg_start / grid_duration) * grid_duration
            shift = snapped - avg_start

            for note in chord:
                original_duration = note.end - note.start
                note.start = max(0, note.start + shift)
                note.end = note.start + original_duration
                total_notes += 1
                total_shift += abs(shift)
                if abs(shift) > 0.001:
                    quantized_notes += 1

            i = j

    pm.write(output_path)

    avg_shift_ms = (total_shift / total_notes * 1000) if total_notes > 0 else 0
    return {
        'tempo_estimated': round(tempo, 1),
        'grid_resolution': grid_resolution,
        'grid_ms': round(grid_duration * 1000, 1),
        'total_notes': total_notes,
        'quantized_notes': quantized_notes,
        'avg_shift_ms': round(avg_shift_ms, 1),
    }


def main():
    parser = argparse.ArgumentParser(description='Quantize MIDI onsets to beat grid')
    parser.add_argument('input', help='Input MIDI file or directory')
    parser.add_argument('-o', '--output', help='Output path (file or directory)')
    parser.add_argument('-g', '--grid', type=int, default=16, help='Grid resolution (4/8/16/32)')
    parser.add_argument('-w', '--chord-window', type=float, default=0.03, help='Chord window in seconds')
    parser.add_argument('--suffix', default='_q', help='Suffix for output files when no -o given')
    args = parser.parse_args()

    if os.path.isfile(args.input):
        files = [args.input]
    elif os.path.isdir(args.input):
        files = sorted([
            os.path.join(args.input, f)
            for f in os.listdir(args.input)
            if f.endswith('.mid')
        ])
    else:
        print(f"Error: {args.input} not found")
        return

    for fpath in files:
        if args.output and os.path.isdir(args.output):
            out = os.path.join(args.output, os.path.basename(fpath))
        elif args.output and len(files) == 1:
            out = args.output
        else:
            base, ext = os.path.splitext(fpath)
            out = f"{base}{args.suffix}{ext}"

        result = quantize_midi(fpath, out, args.grid, args.chord_window)
        print(f"{os.path.basename(fpath)} → {os.path.basename(out)}")
        print(f"  tempo={result['tempo_estimated']}bpm grid={result['grid_ms']}ms "
              f"shifted={result['quantized_notes']}/{result['total_notes']} "
              f"avg_shift={result['avg_shift_ms']}ms")


if __name__ == '__main__':
    main()
