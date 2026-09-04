"""Humanize flat MIDI files with realistic piano performance techniques.

Applies: velocity dynamics, micro-timing, articulation, sustain pedal.
Supports pianist style presets (--style).

Usage:
  python3 humanize_midi.py input.mid output.mid
  python3 humanize_midi.py input.mid output.mid --style einaudi
  python3 humanize_midi.py --list-styles
"""
import argparse, math, random
import mido

SEED = 42


# ──────────────────────────────────────────────
# Pianist style presets
# ──────────────────────────────────────────────

STYLE_DEFAULT = {
    "name": "default",
    "velocity_range": (40, 100),
    "melody_boost": 15,
    "lh_offset": -15,
    "inner_cut": -10,
    "downbeat_accent": 0.5,       # 0=flat, 1=heavy
    "weak_beat_factor": 0.87,
    "repeat_decay": 3,
    "jitter_sigma_slow": 15,
    "jitter_sigma_mid": 12,
    "jitter_sigma_fast": 8,
    "melody_lead_ms": -25,
    "bass_lag_ms": 12,
    "inner_lag_ms": 15,
    "timing_sigma_slow": 25,
    "timing_sigma_mid": 15,
    "timing_sigma_fast": 8,
    "chord_spread_ms": (8, 15),
    "rubato_strength": 0.25,      # max stretch at phrase end
    "phrase_end_rit": 0.15,       # duration stretch at phrase end
    "articulation_melody": 0.95,
    "articulation_bass": 0.90,
    "articulation_inner": 0.70,
    "melody_overlap_ms": 30,
    "pedal_density": 0.7,         # 0=skip most changes, 1=re-pedal every change
    "half_pedal_value": 35,
    "half_pedal_ratio": 0.5,      # fraction of non-bass changes that get half-pedal vs skip
    "description": "Balanced default — moderate everything",
}

STYLES = {
    "default": STYLE_DEFAULT,

    "yiruma": {
        **STYLE_DEFAULT,
        "name": "yiruma",
        "velocity_range": (45, 105),
        "melody_boost": 12,
        "downbeat_accent": 0.3,
        "weak_beat_factor": 0.90,
        "melody_lead_ms": -20,
        "timing_sigma_slow": 12, "timing_sigma_mid": 8, "timing_sigma_fast": 5,
        "chord_spread_ms": (10, 25),
        "rubato_strength": 0.30,
        "phrase_end_rit": 0.20,
        "articulation_melody": 0.95,
        "articulation_inner": 0.75,
        "melody_overlap_ms": 35,
        "pedal_density": 0.7,
        "half_pedal_ratio": 0.3,
        "description": "Warm singing melody, gentle arpeggiated accompaniment",
    },

    "einaudi": {
        **STYLE_DEFAULT,
        "name": "einaudi",
        "velocity_range": (35, 110),
        "melody_boost": 10,
        "downbeat_accent": 0.5,
        "weak_beat_factor": 0.88,
        "jitter_sigma_slow": 8, "jitter_sigma_mid": 5, "jitter_sigma_fast": 3,
        "melody_lead_ms": -15,
        "timing_sigma_slow": 8, "timing_sigma_mid": 5, "timing_sigma_fast": 3,
        "chord_spread_ms": (5, 15),
        "rubato_strength": 0.12,
        "phrase_end_rit": 0.08,
        "articulation_melody": 0.85,
        "articulation_inner": 0.72,
        "melody_overlap_ms": 20,
        "pedal_density": 0.8,
        "half_pedal_value": 40,
        "half_pedal_ratio": 0.6,
        "description": "Hypnotic ostinato, metronomic pulse, tidal dynamics",
    },

    "nils_frahm": {
        **STYLE_DEFAULT,
        "name": "nils_frahm",
        "velocity_range": (20, 75),
        "melody_boost": 8,
        "lh_offset": -18,
        "inner_cut": -5,
        "downbeat_accent": 0.15,
        "weak_beat_factor": 0.95,
        "jitter_sigma_slow": 25, "jitter_sigma_mid": 18, "jitter_sigma_fast": 10,
        "melody_lead_ms": -10,
        "bass_lag_ms": 8,
        "inner_lag_ms": 10,
        "timing_sigma_slow": 25, "timing_sigma_mid": 18, "timing_sigma_fast": 10,
        "chord_spread_ms": (15, 40),
        "rubato_strength": 0.35,
        "phrase_end_rit": 0.25,
        "articulation_melody": 1.0,
        "articulation_bass": 0.95,
        "articulation_inner": 0.90,
        "melody_overlap_ms": 50,
        "pedal_density": 0.9,
        "half_pedal_value": 45,
        "half_pedal_ratio": 0.7,
        "description": "Felt-dampened whisper, notes dissolve into resonance",
    },

    "sakamoto": {
        **STYLE_DEFAULT,
        "name": "sakamoto",
        "velocity_range": (30, 90),
        "melody_boost": 18,
        "lh_offset": -18,
        "inner_cut": -12,
        "downbeat_accent": 0.2,
        "weak_beat_factor": 0.93,
        "jitter_sigma_slow": 18, "jitter_sigma_mid": 12, "jitter_sigma_fast": 8,
        "melody_lead_ms": -35,
        "bass_lag_ms": 15,
        "timing_sigma_slow": 18, "timing_sigma_mid": 12, "timing_sigma_fast": 8,
        "chord_spread_ms": (5, 15),
        "rubato_strength": 0.20,
        "phrase_end_rit": 0.30,
        "articulation_melody": 0.75,
        "articulation_bass": 0.80,
        "articulation_inner": 0.60,
        "melody_overlap_ms": 15,
        "pedal_density": 0.5,
        "half_pedal_value": 40,
        "half_pedal_ratio": 0.5,
        "description": "Sparse, surgical — silence is as composed as sound",
    },

    "gonzales": {
        **STYLE_DEFAULT,
        "name": "gonzales",
        "velocity_range": (40, 125),
        "melody_boost": 12,
        "lh_offset": -10,
        "inner_cut": -8,
        "downbeat_accent": 0.7,
        "weak_beat_factor": 0.82,
        "jitter_sigma_slow": 15, "jitter_sigma_mid": 10, "jitter_sigma_fast": 5,
        "melody_lead_ms": -10,
        "bass_lag_ms": 5,
        "inner_lag_ms": 8,
        "timing_sigma_slow": 15, "timing_sigma_mid": 10, "timing_sigma_fast": 5,
        "chord_spread_ms": (3, 10),
        "rubato_strength": 0.15,
        "phrase_end_rit": 0.08,
        "articulation_melody": 0.70,
        "articulation_bass": 0.55,
        "articulation_inner": 0.50,
        "melody_overlap_ms": 15,
        "pedal_density": 0.4,
        "half_pedal_ratio": 0.2,
        "description": "Theatrical showman — stride-jazz, percussive attack, pop hooks",
    },

    "hisaishi": {
        **STYLE_DEFAULT,
        "name": "hisaishi",
        "velocity_range": (40, 115),
        "melody_boost": 15,
        "lh_offset": -12,
        "inner_cut": -8,
        "downbeat_accent": 0.5,
        "weak_beat_factor": 0.88,
        "jitter_sigma_slow": 10, "jitter_sigma_mid": 7, "jitter_sigma_fast": 4,
        "melody_lead_ms": -22,
        "timing_sigma_slow": 10, "timing_sigma_mid": 7, "timing_sigma_fast": 4,
        "chord_spread_ms": (10, 20),
        "rubato_strength": 0.22,
        "phrase_end_rit": 0.18,
        "articulation_melody": 0.88,
        "articulation_bass": 0.82,
        "articulation_inner": 0.65,
        "melody_overlap_ms": 25,
        "pedal_density": 0.7,
        "half_pedal_ratio": 0.4,
        "description": "Cinematic swells, childlike melody, orchestral piano",
    },

    "tiersen": {
        **STYLE_DEFAULT,
        "name": "tiersen",
        "velocity_range": (50, 120),
        "melody_boost": 10,
        "lh_offset": -10,
        "inner_cut": -6,
        "downbeat_accent": 0.65,
        "weak_beat_factor": 0.83,
        "jitter_sigma_slow": 7, "jitter_sigma_mid": 5, "jitter_sigma_fast": 3,
        "melody_lead_ms": -8,
        "bass_lag_ms": 5,
        "inner_lag_ms": 5,
        "timing_sigma_slow": 7, "timing_sigma_mid": 5, "timing_sigma_fast": 3,
        "chord_spread_ms": (2, 8),
        "rubato_strength": 0.08,
        "phrase_end_rit": 0.05,
        "articulation_melody": 0.55,
        "articulation_bass": 0.50,
        "articulation_inner": 0.40,
        "melody_overlap_ms": 5,
        "pedal_density": 0.3,
        "half_pedal_ratio": 0.1,
        "description": "Toy-piano clockwork — bright staccato waltzes, perpetual motion",
    },
}


# ──────────────────────────────────────────────
# Analysis helpers
# ──────────────────────────────────────────────

def estimate_tempo(notes):
    onsets = sorted(set(n["start"] for n in notes))
    if len(onsets) < 3:
        return 120.0
    iois = [onsets[i+1] - onsets[i] for i in range(len(onsets)-1) if onsets[i+1] - onsets[i] > 0.05]
    if not iois:
        return 120.0
    median_ioi = sorted(iois)[len(iois) // 2]
    bpm = 60.0 / median_ioi
    while bpm > 200: bpm /= 2
    while bpm < 50: bpm *= 2
    return bpm


def analyze_phrases(notes, gap_thresh=0.8):
    phrases = []
    current = [notes[0]]
    for i in range(1, len(notes)):
        gap = notes[i]["start"] - (notes[i-1]["start"] + notes[i-1]["dur"])
        if gap > gap_thresh:
            phrases.append(current)
            current = []
        current.append(notes[i])
    if current:
        phrases.append(current)
    return phrases


def classify_melody_accompaniment(notes, window=0.05):
    has_hand_info = any(n.get("hand") == "LH" for n in notes)

    clusters = []
    current = [notes[0]]
    for i in range(1, len(notes)):
        if notes[i]["start"] - current[0]["start"] <= window:
            current.append(notes[i])
        else:
            clusters.append(current)
            current = [notes[i]]
    if current:
        clusters.append(current)

    for cluster in clusters:
        if has_hand_info:
            # track-aware: RH top note = melody, rest of RH = inner, all LH = bass/accompaniment
            rh_notes = sorted([n for n in cluster if n.get("hand") == "RH"], key=lambda n: n["note"])
            lh_notes = [n for n in cluster if n.get("hand") == "LH"]
            if rh_notes:
                rh_notes[-1]["role"] = "melody"
                for n in rh_notes[:-1]:
                    n["role"] = "inner"
            for n in lh_notes:
                n["role"] = "bass"
        else:
            if len(cluster) == 1:
                cluster[0]["role"] = "melody"
                continue
            sorted_c = sorted(cluster, key=lambda n: n["note"])
            sorted_c[-1]["role"] = "melody"
            sorted_c[0]["role"] = "bass"
            for n in sorted_c[1:-1]:
                n["role"] = "inner"

    for n in notes:
        if "role" not in n:
            n["role"] = "melody" if n.get("hand") == "RH" else "bass"


def detect_repeated_notes(notes):
    for i, n in enumerate(notes):
        n["repeat_idx"] = 0
    for i in range(1, len(notes)):
        if notes[i]["note"] == notes[i-1]["note"] and notes[i]["start"] - notes[i-1]["start"] < 1.0:
            notes[i]["repeat_idx"] = notes[i-1]["repeat_idx"] + 1


def detect_chord_changes(notes, window=0.05):
    if not notes:
        return []

    clusters = []
    current_cluster = [notes[0]]
    for i in range(1, len(notes)):
        if notes[i]["start"] - current_cluster[0]["start"] <= window:
            current_cluster.append(notes[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [notes[i]]
    if current_cluster:
        clusters.append(current_cluster)

    change_times = []
    prev_pcs = None
    prev_bass = None
    for cluster in clusters:
        onset = cluster[0]["start"]
        sounding = []
        for n in notes:
            if n["start"] <= onset < n["start"] + n["dur"]:
                sounding.append(n["note"])
        for n in cluster:
            sounding.append(n["note"])

        pcs = frozenset(p % 12 for p in sounding)
        bass = min(sounding) % 12

        if prev_pcs is not None and pcs != prev_pcs:
            change_times.append((onset, prev_bass != bass))
        prev_pcs = pcs
        prev_bass = bass

    return change_times


def _tempo_select(bpm, slow, mid, fast):
    if bpm < 80: return slow
    elif bpm < 120: return mid
    else: return fast


# ──────────────────────────────────────────────
# 1. Velocity humanization
# ──────────────────────────────────────────────

def humanize_velocity(notes, style):
    rng = random.Random(SEED)
    bpm = estimate_tempo(notes)
    classify_melody_accompaniment(notes)
    detect_repeated_notes(notes)
    phrases = analyze_phrases(notes)

    jitter_sigma = _tempo_select(bpm,
        style["jitter_sigma_slow"], style["jitter_sigma_mid"], style["jitter_sigma_fast"])

    lo, hi = style["velocity_range"]
    accent_strength = style["downbeat_accent"]
    weak_factor = style["weak_beat_factor"]
    secondary_factor = 1.0 - (1.0 - weak_factor) * 0.5

    for phrase in phrases:
        n_notes = len(phrase)
        peak_pos = rng.uniform(0.4, 0.7)
        phrase_intensity = rng.uniform(0.6, 1.0)

        for i, note in enumerate(phrase):
            t = i / max(n_notes - 1, 1)

            if t <= peak_pos:
                curve = (t / peak_pos) ** 1.3
            else:
                curve = 1.0 - ((t - peak_pos) / (1.0 - peak_pos)) ** 0.7 * 0.4

            vel = lo + (hi - lo) * curve * phrase_intensity

            # register offset
            midi_note = note["note"]
            if midi_note < 36:   vel += 7
            elif midi_note < 60: vel += 3
            elif midi_note > 84: vel -= 6
            elif midi_note > 72: vel -= 3

            # voicing: RH melody up, LH accompaniment down
            role = note.get("role", "melody")
            if role == "melody":   vel += style["melody_boost"]
            elif role == "bass":   vel += style["lh_offset"]
            elif role == "inner":  vel += style["inner_cut"]

            # metric accent
            beat_dur = 60.0 / bpm
            beat_pos = (note["start"] % (beat_dur * 4)) / beat_dur
            beat_idx = int(beat_pos) % 4
            if beat_idx == 0:
                vel *= 1.0
            elif beat_idx == 2:
                vel *= secondary_factor
            else:
                vel *= weak_factor

            # repeated note decay
            rep = note.get("repeat_idx", 0)
            if rep > 0:
                vel -= min(rep * style["repeat_decay"], 15)

            vel += rng.gauss(0, jitter_sigma)
            note["velocity"] = int(max(22, min(122, vel)))


# ──────────────────────────────────────────────
# 2. Micro-timing humanization
# ──────────────────────────────────────────────

def humanize_timing(notes, style):
    rng = random.Random(SEED + 1)
    bpm = estimate_tempo(notes)
    phrases = analyze_phrases(notes)

    timing_sigma = _tempo_select(bpm,
        style["timing_sigma_slow"], style["timing_sigma_mid"], style["timing_sigma_fast"]) / 1000.0

    melody_lead = style["melody_lead_ms"] / 1000.0
    bass_lag = style["bass_lag_ms"] / 1000.0
    inner_lag = style["inner_lag_ms"] / 1000.0

    for n in notes:
        role = n.get("role", "melody")
        if role == "melody":
            n["start"] += melody_lead + rng.gauss(0, timing_sigma)
        elif role == "bass":
            n["start"] += bass_lag + rng.gauss(0, timing_sigma)
        elif role == "inner":
            n["start"] += inner_lag + rng.gauss(0, timing_sigma)

    # chord arpeggiation
    clusters = []
    current = [notes[0]]
    for i in range(1, len(notes)):
        if abs(notes[i]["start"] - current[0]["start"]) <= 0.06:
            current.append(notes[i])
        else:
            clusters.append(current)
            current = [notes[i]]
    if current:
        clusters.append(current)

    spread_lo, spread_hi = style["chord_spread_ms"]
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        sorted_c = sorted(cluster, key=lambda n: n["note"])
        base_time = sorted_c[0]["start"]
        spread = rng.uniform(spread_lo, spread_hi) / 1000.0
        for j, n in enumerate(sorted_c):
            n["start"] = base_time + j * spread

    # free tempo rubato: tempo breathes within each phrase
    #   - slight accelerando toward emotional peak (40-60% of phrase)
    #   - deceleration after peak
    #   - strong ritardando at phrase end
    #   - agogic accent on strong beats (slight stretch)
    rubato = style["rubato_strength"]
    dur_stretch = style["phrase_end_rit"]
    beat_dur = 60.0 / bpm

    for phrase in phrases:
        if len(phrase) < 4:
            continue
        p_start = phrase[0]["start"]
        p_end = phrase[-1]["start"]
        p_dur = p_end - p_start
        if p_dur < 1.0:
            continue

        peak_pos = 0.45  # emotional peak at ~45% of phrase
        cumulative_shift = 0.0

        for n in phrase:
            t = (n["start"] - p_start) / p_dur  # 0~1 position in phrase

            # tempo curve: negative = speed up, positive = slow down
            if t < peak_pos:
                # accelerando toward peak: compress time slightly
                tempo_factor = -rubato * 0.4 * math.sin(math.pi * t / peak_pos)
            elif t < 0.8:
                # gentle deceleration after peak
                post_t = (t - peak_pos) / (0.8 - peak_pos)
                tempo_factor = rubato * 0.3 * post_t
            else:
                # strong ritardando at phrase end
                end_t = (t - 0.8) / 0.2
                tempo_factor = rubato * (0.3 + 0.7 * (end_t ** 1.5))

            # agogic accent: stretch strong beats slightly
            beat_phase = ((n["start"] - p_start) % beat_dur) / beat_dur
            if beat_phase < 0.15:  # near downbeat
                tempo_factor += rubato * 0.08

            # apply: shift this note's time
            time_offset = tempo_factor * beat_dur * 0.5
            cumulative_shift += time_offset * 0.3  # gradual accumulation
            n["start"] += cumulative_shift + time_offset * 0.7
            n["dur"] *= (1.0 + tempo_factor * dur_stretch)

    # velocity-dependent timing
    for n in notes:
        vel_factor = (n["velocity"] - 70) / 50.0
        n["start"] += vel_factor * (-0.008)

    for n in notes:
        n["start"] = max(0.0, n["start"])
    notes.sort(key=lambda x: x["start"])


# ──────────────────────────────────────────────
# 3. Articulation
# ──────────────────────────────────────────────

def humanize_articulation(notes, style):
    rng = random.Random(SEED + 2)
    overlap_sec = style["melody_overlap_ms"] / 1000.0

    for i, n in enumerate(notes):
        role = n.get("role", "melody")

        if role == "melody":
            dur_ratio = style["articulation_melody"]
            for j in range(i + 1, min(i + 10, len(notes))):
                if notes[j].get("role") == "melody":
                    gap_to_next = notes[j]["start"] - n["start"]
                    if gap_to_next > 0:
                        target_dur = gap_to_next + overlap_sec
                        dur_ratio = min(target_dur / n["dur"], 1.2) if n["dur"] > 0 else dur_ratio
                    break
        elif role == "bass":
            dur_ratio = style["articulation_bass"]
        else:
            dur_ratio = style["articulation_inner"]

        dur_ratio += rng.gauss(0, 0.04)
        dur_ratio = max(0.2, min(1.3, dur_ratio))
        n["dur"] *= dur_ratio

    phrases = analyze_phrases(notes, gap_thresh=0.5)
    for pi in range(len(phrases) - 1):
        last_note = phrases[pi][-1]
        first_next = phrases[pi + 1][0]
        gap = first_next["start"] - (last_note["start"] + last_note["dur"])
        if gap < 0.08:
            last_note["dur"] = max(0.05, last_note["dur"] - 0.08)


# ──────────────────────────────────────────────
# 4. Sustain pedal (legato pedaling)
# ──────────────────────────────────────────────

def add_sustain_pedal(notes, total_dur, style, min_pedal=0.3):
    bpm = estimate_tempo(notes)
    rng = random.Random(SEED + 3)

    if bpm < 80:
        release_delay = 0.040
        reon_delay = 0.070
    elif bpm < 120:
        release_delay = 0.025
        reon_delay = 0.050
    else:
        release_delay = 0.015
        reon_delay = 0.035

    half_val = style["half_pedal_value"]
    density = style["pedal_density"]
    half_ratio = style["half_pedal_ratio"]

    events = []
    phrases = analyze_phrases(notes, gap_thresh=0.5)
    chord_changes = detect_chord_changes(notes)
    change_map = {t: bass for t, bass in chord_changes}

    for phrase in phrases:
        if not phrase:
            continue
        p_start = phrase[0]["start"]
        p_end = max(n["start"] + n["dur"] for n in phrase)
        if p_end - p_start < min_pedal:
            continue

        events.append(("cc", 127, p_start + 0.01))

        for n in phrase[1:]:
            if n["start"] not in change_map:
                continue

            # density filter: skip some changes for lighter pedal styles
            if rng.random() > density:
                continue

            bass_changed = change_map[n["start"]]
            if bass_changed:
                events.append(("cc", 0, n["start"] + release_delay))
                events.append(("cc", 127, n["start"] + release_delay + reon_delay))
            else:
                if rng.random() < half_ratio:
                    events.append(("cc", half_val, n["start"] + release_delay))
                    events.append(("cc", 127, n["start"] + release_delay + reon_delay * 0.7))

        events.append(("cc", 0, p_end + 0.1))

    events.sort(key=lambda x: x[2])
    cleaned = []
    for evt in events:
        if cleaned and abs(evt[2] - cleaned[-1][2]) < 0.008:
            cleaned[-1] = evt
        else:
            cleaned.append(evt)

    return cleaned


# ──────────────────────────────────────────────
# MIDI I/O
# ──────────────────────────────────────────────

def notes_from_midi(mid):
    notes = []
    note_tracks = []
    for ti, track in enumerate(mid.tracks):
        abs_time = 0.0
        active = {}
        has_notes = False
        for msg in track:
            abs_time += mido.tick2second(msg.time, mid.ticks_per_beat, 500000)
            if msg.type == "note_on" and msg.velocity > 0:
                active[msg.note] = (abs_time, msg.velocity)
                has_notes = True
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in active:
                    start, vel = active.pop(msg.note)
                    dur = abs_time - start
                    if dur > 0:
                        notes.append({"note": msg.note, "velocity": vel,
                                      "start": start, "dur": dur, "track": ti})
        for note, (start, vel) in active.items():
            notes.append({"note": note, "velocity": vel, "start": start, "dur": 2.0, "track": ti})
        if has_notes:
            note_tracks.append(ti)
    notes.sort(key=lambda x: x["start"])

    # if 2 tracks with notes, classify by track: higher avg pitch = RH (melody track)
    if len(note_tracks) >= 2:
        track_avg = {}
        for ti in note_tracks:
            pitches = [n["note"] for n in notes if n["track"] == ti]
            track_avg[ti] = sum(pitches) / len(pitches) if pitches else 0
        rh_track = max(track_avg, key=track_avg.get)
        for n in notes:
            n["hand"] = "RH" if n["track"] == rh_track else "LH"
    else:
        for n in notes:
            n["hand"] = "RH"

    return notes


def notes_to_midi(notes, pedal_events, ticks_per_beat=480):
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    tempo = mido.bpm2tempo(120)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo))

    events = []
    for n in notes:
        events.append((n["start"], "note_on", n["note"], n["velocity"]))
        events.append((n["start"] + n["dur"], "note_off", n["note"], 0))
    for evt in pedal_events:
        events.append((evt[2], "cc", 64, evt[1]))

    events.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))

    prev_time = 0.0
    for evt in events:
        abs_sec = max(evt[0], 0)
        delta = abs_sec - prev_time
        ticks = int(mido.second2tick(delta, ticks_per_beat, tempo))
        if evt[1] == "note_on":
            track.append(mido.Message("note_on", note=evt[2], velocity=evt[3], time=ticks))
        elif evt[1] == "note_off":
            track.append(mido.Message("note_off", note=evt[2], velocity=0, time=ticks))
        elif evt[1] == "cc":
            track.append(mido.Message("control_change", control=evt[2], value=evt[3], time=ticks))
        prev_time = abs_sec

    return mid


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def humanize(input_path, output_path, style_name="default"):
    style = STYLES.get(style_name, STYLE_DEFAULT)

    mid = mido.MidiFile(input_path)
    notes = notes_from_midi(mid)
    if not notes:
        print("No notes found!")
        return

    total_dur = max(n["start"] + n["dur"] for n in notes)
    bpm = estimate_tempo(notes)
    print(f"  Style: {style['name']} — {style['description']}")
    print(f"  Notes: {len(notes)}, duration: {total_dur:.1f}s, tempo: {bpm:.0f} BPM")

    orig_vels = [n["velocity"] for n in notes]
    print(f"  Original velocity: {min(orig_vels)}~{max(orig_vels)}, avg={sum(orig_vels)/len(orig_vels):.0f}")

    humanize_velocity(notes, style)
    new_vels = [n["velocity"] for n in notes]
    roles = {}
    for n in notes:
        roles[n.get("role", "?")] = roles.get(n.get("role", "?"), 0) + 1
    print(f"  Velocity: {min(new_vels)}~{max(new_vels)}, avg={sum(new_vels)/len(new_vels):.0f} | voicing: {roles}")

    humanize_timing(notes, style)
    humanize_articulation(notes, style)

    pedal_events = add_sustain_pedal(notes, total_dur, style)
    full_rp = sum(1 for e in pedal_events if e[1] == 0)
    half_p = sum(1 for e in pedal_events if 0 < e[1] < 127)
    print(f"  Pedal: {len(pedal_events)} events (full: {full_rp}, half: {half_p})")

    new_mid = notes_to_midi(notes, pedal_events, mid.ticks_per_beat)
    new_mid.save(output_path)
    print(f"  → {output_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Humanize MIDI with pianist style presets")
    p.add_argument("input", nargs="?", help="Input MIDI")
    p.add_argument("output", nargs="?", help="Output MIDI")
    p.add_argument("--style", default="default", choices=list(STYLES.keys()),
                   help="Pianist style preset")
    p.add_argument("--list-styles", action="store_true", help="Show available styles")
    args = p.parse_args()

    if args.list_styles:
        for name, s in STYLES.items():
            vel = s["velocity_range"]
            print(f"  {name:15s}  vel={vel[0]:3d}~{vel[1]:3d}  "
                  f"pedal={s['pedal_density']:.1f}  rubato={s['rubato_strength']:.2f}  "
                  f"artic={s['articulation_melody']:.2f}  — {s['description']}")
    elif args.input and args.output:
        humanize(args.input, args.output, style_name=args.style)
    else:
        p.print_help()
