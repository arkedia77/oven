#!/usr/bin/env python3
"""
Phrase Segmenter for Piano MIDI Files
======================================
Detects musical phrase boundaries using multiple heuristic signals:
  - Rest gaps (silence > threshold between notes)
  - Dynamic shifts (sudden velocity changes)
  - Register jumps (large pitch gaps)
  - Onset density changes
  - Cadence-like patterns

Designed as a chunking preprocessor for a music generation RAG system.

Usage:
    python3 phrase_segmenter.py <midi_file> [--output json_path] [--gap 0.3] [--min-notes 4]
    python3 phrase_segmenter.py --batch <directory> [--recursive]
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np
import pretty_midi


# ── Configuration ──────────────────────────────────────────────────────────

DEFAULT_REST_GAP = 0.3        # seconds of silence to mark a phrase boundary
VELOCITY_JUMP = 30            # velocity units for a "dynamic shift"
PITCH_JUMP = 12               # semitones (1 octave) for a "register jump"
DENSITY_WINDOW = 0.5          # seconds – sliding window for onset density
DENSITY_RATIO = 2.5           # ratio threshold for density change
MIN_PHRASE_NOTES = 4          # minimum notes to keep a phrase
BOUNDARY_SCORE_THRESHOLD = 2.2  # how many signals must agree to split
MIN_PHRASE_DURATION = 0.4     # minimum phrase duration in seconds
MAX_PHRASE_DURATION = 15.0    # maximum phrase duration — force split if exceeded
MAX_PHRASE_NOTES = 200        # maximum notes per phrase — force split if exceeded


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class Note:
    pitch: int
    velocity: int
    start: float
    end: float

    @property
    def duration(self):
        return self.end - self.start


@dataclass
class Phrase:
    index: int
    start_time: float
    end_time: float
    notes: list = field(default_factory=list, repr=False)
    num_notes: int = 0
    avg_pitch: float = 0.0
    avg_velocity: float = 0.0
    pitch_range: tuple = (0, 0)
    duration: float = 0.0
    density: float = 0.0  # notes per second
    summary: str = ""

    def compute_stats(self):
        if not self.notes:
            return
        pitches = [n.pitch for n in self.notes]
        velocities = [n.velocity for n in self.notes]
        self.num_notes = len(self.notes)
        self.avg_pitch = round(np.mean(pitches), 1)
        self.avg_velocity = round(np.mean(velocities), 1)
        self.pitch_range = (min(pitches), max(pitches))
        self.duration = round(self.end_time - self.start_time, 3)
        self.density = round(self.num_notes / max(self.duration, 0.01), 2)
        self.summary = self._make_summary()

    def _make_summary(self):
        pitches = [n.pitch for n in self.notes]
        vels = [n.velocity for n in self.notes]

        # Register description
        avg_p = np.mean(pitches)
        if avg_p < 48:
            register = "low"
        elif avg_p < 60:
            register = "low-mid"
        elif avg_p < 72:
            register = "mid"
        elif avg_p < 84:
            register = "mid-high"
        else:
            register = "high"

        # Dynamic description
        avg_v = np.mean(vels)
        if avg_v < 40:
            dynamic = "pp"
        elif avg_v < 60:
            dynamic = "p"
        elif avg_v < 80:
            dynamic = "mf"
        elif avg_v < 100:
            dynamic = "f"
        else:
            dynamic = "ff"

        # Contour
        if len(pitches) >= 3:
            mid = len(pitches) // 2
            first_half = np.mean(pitches[:mid])
            second_half = np.mean(pitches[mid:])
            diff = second_half - first_half
            if diff > 3:
                contour = "ascending"
            elif diff < -3:
                contour = "descending"
            else:
                contour = "static"
        else:
            contour = "brief"

        span = max(pitches) - min(pitches)
        texture = "wide" if span > 24 else ("moderate" if span > 12 else "narrow")

        return (
            f"{register} register, {dynamic}, {contour} contour, "
            f"{texture} range ({span} st), {self.density:.1f} notes/s"
        )

    def to_dict(self):
        return {
            "index": self.index,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "duration": self.duration,
            "num_notes": self.num_notes,
            "avg_pitch": self.avg_pitch,
            "avg_velocity": self.avg_velocity,
            "pitch_range": list(self.pitch_range),
            "density_nps": self.density,
            "summary": self.summary,
        }


# ── Core segmentation ─────────────────────────────────────────────────────

def load_notes(midi_path: str) -> list[Note]:
    """Load all notes from a MIDI file, sorted by onset time."""
    pm = pretty_midi.PrettyMIDI(midi_path)
    notes = []
    for inst in pm.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            notes.append(Note(pitch=n.pitch, velocity=n.velocity,
                              start=n.start, end=n.end))
    notes.sort(key=lambda n: (n.start, n.pitch))
    return notes


def compute_boundary_scores(notes: list[Note],
                            rest_gap: float = DEFAULT_REST_GAP) -> list[float]:
    """
    For each consecutive note pair, compute a boundary score (0-5).
    Higher score = more likely phrase boundary.
    Returns list of length len(notes)-1.
    """
    if len(notes) < 2:
        return []

    scores = []
    # Precompute onset density using sliding window
    onsets = np.array([n.start for n in notes])

    for i in range(len(notes) - 1):
        score = 0.0
        curr = notes[i]
        nxt = notes[i + 1]

        # 1. Rest gap: time from end of current to start of next
        gap = nxt.start - curr.end
        if gap >= rest_gap:
            # Scale: longer gaps get stronger score
            score += min(1.0 + (gap - rest_gap) / rest_gap, 2.0)

        # Also check onset gap (time between note starts)
        onset_gap = nxt.start - curr.start
        if onset_gap >= rest_gap * 2:
            score += 0.5

        # 2. Dynamic shift
        vel_diff = abs(nxt.velocity - curr.velocity)
        if vel_diff >= VELOCITY_JUMP:
            score += min(vel_diff / VELOCITY_JUMP, 1.5)

        # 3. Register jump
        pitch_diff = abs(nxt.pitch - curr.pitch)
        if pitch_diff >= PITCH_JUMP:
            score += min(pitch_diff / PITCH_JUMP, 1.5)

        # 4. Onset density change
        t = curr.start
        window_before = np.sum((onsets >= t - DENSITY_WINDOW) & (onsets <= t))
        window_after = np.sum((onsets >= nxt.start) &
                              (onsets <= nxt.start + DENSITY_WINDOW))
        if window_before > 0 and window_after > 0:
            ratio = max(window_before, window_after) / min(window_before, window_after)
            if ratio >= DENSITY_RATIO:
                score += 0.8

        # 5. Cadence-like pattern: descending motion ending on a "stable" pitch
        # Check if current note resolves downward by step
        if i >= 2:
            prev2 = notes[i - 1]
            if (prev2.pitch > curr.pitch and
                    curr.pitch - nxt.pitch > 0 and
                    curr.pitch % 12 in (0, 4, 5, 7)):  # C, E, F, G – stable scale degrees
                score += 0.7

        scores.append(score)

    return scores


def segment_phrases(notes: list[Note],
                    rest_gap: float = DEFAULT_REST_GAP,
                    threshold: float = BOUNDARY_SCORE_THRESHOLD,
                    min_notes: int = MIN_PHRASE_NOTES) -> list[Phrase]:
    """Segment notes into phrases based on boundary scores."""
    if not notes:
        return []

    scores = compute_boundary_scores(notes, rest_gap)

    # Find boundary indices where score exceeds threshold
    boundaries = [0]  # start of first phrase
    for i, s in enumerate(scores):
        if s >= threshold:
            boundaries.append(i + 1)  # next note starts new phrase

    # Build phrases
    phrases = []
    for pi in range(len(boundaries)):
        start_idx = boundaries[pi]
        end_idx = boundaries[pi + 1] if pi + 1 < len(boundaries) else len(notes)
        phrase_notes = notes[start_idx:end_idx]

        p = Phrase(
            index=len(phrases),
            start_time=phrase_notes[0].start,
            end_time=phrase_notes[-1].end,
            notes=phrase_notes,
        )
        p.compute_stats()
        phrases.append(p)

    # Merge short/tiny phrases into neighbors
    for _pass in range(3):  # multiple passes to catch cascading merges
        new_phrases = []
        for p in phrases:
            too_short = (p.num_notes < min_notes or
                         p.duration < MIN_PHRASE_DURATION)
            if too_short and new_phrases:
                # Merge into previous
                new_phrases[-1].notes.extend(p.notes)
                new_phrases[-1].end_time = max(new_phrases[-1].end_time, p.end_time)
                new_phrases[-1].compute_stats()
            else:
                new_phrases.append(p)
        # Also merge leading fragment forward if it's still too short
        if (len(new_phrases) >= 2 and
                (new_phrases[0].num_notes < min_notes or
                 new_phrases[0].duration < MIN_PHRASE_DURATION)):
            new_phrases[1].notes = new_phrases[0].notes + new_phrases[1].notes
            new_phrases[1].start_time = min(new_phrases[0].start_time,
                                            new_phrases[1].start_time)
            new_phrases[1].compute_stats()
            new_phrases.pop(0)
        if len(new_phrases) == len(phrases):
            break
        phrases = new_phrases

    # Force-split phrases that exceed max duration or max notes
    split_phrases = []
    for p in phrases:
        if p.duration <= MAX_PHRASE_DURATION and p.num_notes <= MAX_PHRASE_NOTES:
            split_phrases.append(p)
            continue
        # Split into chunks of MAX_PHRASE_NOTES
        chunk_notes = p.notes
        while chunk_notes:
            take = min(MAX_PHRASE_NOTES, len(chunk_notes))
            # Also check duration: find how many notes fit within MAX_PHRASE_DURATION
            for j in range(1, take + 1):
                if chunk_notes[j - 1].start - chunk_notes[0].start > MAX_PHRASE_DURATION:
                    take = max(min_notes, j - 1)
                    break
            chunk = chunk_notes[:take]
            chunk_notes = chunk_notes[take:]
            sp = Phrase(
                index=0,
                start_time=chunk[0].start,
                end_time=chunk[-1].end,
                notes=chunk,
            )
            sp.compute_stats()
            split_phrases.append(sp)
    phrases = split_phrases

    # Re-index after merges and splits
    for i, p in enumerate(phrases):
        p.index = i

    return phrases


# ── Visualization ──────────────────────────────────────────────────────────

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def pitch_name(midi_pitch: int) -> str:
    return f"{NOTE_NAMES[midi_pitch % 12]}{midi_pitch // 12 - 1}"


def print_timeline(phrases: list[Phrase], total_duration: float):
    """Print a visual ASCII timeline of phrases."""
    if not phrases:
        print("  (no phrases detected)")
        return

    width = 70
    print(f"\n  Timeline ({total_duration:.1f}s total, {len(phrases)} phrases)")
    print(f"  {'─' * width}")

    for p in phrases:
        start_frac = p.start_time / max(total_duration, 0.01)
        end_frac = p.end_time / max(total_duration, 0.01)
        bar_start = int(start_frac * width)
        bar_end = max(bar_start + 1, int(end_frac * width))

        bar = ' ' * bar_start + '█' * (bar_end - bar_start) + ' ' * (width - bar_end)
        label = f"P{p.index:<2} {p.num_notes:>3}n"
        print(f"  |{bar}| {label}")

    print(f"  {'─' * width}")
    print(f"  0s{' ' * (width - 7)}{total_duration:.1f}s\n")


def print_phrase_details(phrases: list[Phrase]):
    """Print detailed info for each phrase."""
    for p in phrases:
        lo, hi = p.pitch_range
        print(
            f"  Phrase {p.index:>2}: "
            f"{p.start_time:6.2f}s – {p.end_time:6.2f}s  "
            f"({p.duration:5.2f}s)  "
            f"{p.num_notes:>3} notes  "
            f"pitch {pitch_name(lo)}–{pitch_name(hi)}  "
            f"vel {p.avg_velocity:.0f}  "
            f"dens {p.density:.1f}n/s"
        )
    print()


# ── Entry points ───────────────────────────────────────────────────────────

def process_file(midi_path: str,
                 rest_gap: float = DEFAULT_REST_GAP,
                 threshold: float = BOUNDARY_SCORE_THRESHOLD,
                 min_notes: int = MIN_PHRASE_NOTES,
                 verbose: bool = True) -> dict:
    """Process a single MIDI file and return results dict."""
    notes = load_notes(midi_path)
    if not notes:
        if verbose:
            print(f"  ⚠ No notes found in {midi_path}")
        return {"file": midi_path, "error": "no notes", "phrases": []}

    total_dur = max(n.end for n in notes) - min(n.start for n in notes)

    phrases = segment_phrases(notes, rest_gap, threshold, min_notes)

    if verbose:
        fname = os.path.basename(midi_path)
        print(f"\n{'=' * 78}")
        print(f"  FILE: {fname}")
        print(f"  Total notes: {len(notes)}  |  Duration: {total_dur:.2f}s  |  Phrases: {len(phrases)}")
        print_timeline(phrases, total_dur)
        print_phrase_details(phrases)

    return {
        "file": midi_path,
        "filename": os.path.basename(midi_path),
        "total_notes": len(notes),
        "total_duration": round(total_dur, 3),
        "num_phrases": len(phrases),
        "avg_phrase_duration": round(
            np.mean([p.duration for p in phrases]), 3
        ) if phrases else 0,
        "avg_phrase_notes": round(
            np.mean([p.num_notes for p in phrases]), 1
        ) if phrases else 0,
        "phrases": [p.to_dict() for p in phrases],
    }


def process_batch(directory: str, recursive: bool = False, **kwargs) -> list[dict]:
    """Process all MIDI files in a directory."""
    pattern = "**/*.mid" if recursive else "*.mid"
    midi_files = sorted(Path(directory).glob(pattern))
    if not midi_files:
        # Also try .midi extension
        pattern2 = "**/*.midi" if recursive else "*.midi"
        midi_files = sorted(Path(directory).glob(pattern2))

    results = []
    for mf in midi_files:
        try:
            result = process_file(str(mf), **kwargs)
            results.append(result)
        except Exception as e:
            print(f"  ERROR processing {mf}: {e}")
            results.append({"file": str(mf), "error": str(e), "phrases": []})
    return results


def print_summary_table(results: list[dict]):
    """Print a compact summary table of all results."""
    print(f"\n{'=' * 90}")
    print(f"  BATCH SUMMARY  ({len(results)} files)")
    print(f"{'=' * 90}")
    print(f"  {'File':<40} {'Notes':>6} {'Dur(s)':>7} {'Phrases':>8} {'Avg Dur':>8} {'Avg Notes':>9}")
    print(f"  {'─' * 40} {'─' * 6} {'─' * 7} {'─' * 8} {'─' * 8} {'─' * 9}")
    for r in results:
        if "error" in r and r.get("error"):
            print(f"  {r.get('filename', r['file']):<40} {'ERROR':>6}")
            continue
        print(
            f"  {r.get('filename', os.path.basename(r['file'])):<40} "
            f"{r['total_notes']:>6} "
            f"{r['total_duration']:>7.1f} "
            f"{r['num_phrases']:>8} "
            f"{r['avg_phrase_duration']:>8.2f} "
            f"{r['avg_phrase_notes']:>9.1f}"
        )
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Detect musical phrase boundaries in piano MIDI files."
    )
    parser.add_argument("input", help="MIDI file or directory (with --batch)")
    parser.add_argument("--batch", action="store_true",
                        help="Process all MIDI files in directory")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="Search recursively in batch mode")
    parser.add_argument("--output", "-o", help="Save results as JSON")
    parser.add_argument("--gap", type=float, default=DEFAULT_REST_GAP,
                        help=f"Rest gap threshold in seconds (default: {DEFAULT_REST_GAP})")
    parser.add_argument("--threshold", "-t", type=float,
                        default=BOUNDARY_SCORE_THRESHOLD,
                        help=f"Boundary score threshold (default: {BOUNDARY_SCORE_THRESHOLD})")
    parser.add_argument("--min-notes", type=int, default=MIN_PHRASE_NOTES,
                        help=f"Minimum notes per phrase (default: {MIN_PHRASE_NOTES})")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress per-file details, show summary only")

    args = parser.parse_args()
    verbose = not args.quiet

    if args.batch:
        results = process_batch(
            args.input, recursive=args.recursive,
            rest_gap=args.gap, threshold=args.threshold,
            min_notes=args.min_notes, verbose=verbose,
        )
        print_summary_table(results)
    else:
        results = process_file(
            args.input, rest_gap=args.gap, threshold=args.threshold,
            min_notes=args.min_notes, verbose=verbose,
        )
        results = [results]

    if args.output:
        out_path = args.output
        with open(out_path, "w") as f:
            json.dump(results if len(results) > 1 else results[0],
                      f, indent=2, ensure_ascii=False)
        print(f"  Results saved to {out_path}")


if __name__ == "__main__":
    main()
