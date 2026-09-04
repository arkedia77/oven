"""v6 full pipeline: aria-midi → MusicXML → VirtuosoNet → tempo fix → Piano V3 render → segment.

Usage:
  /tmp/dawdreamer_venv/bin/python3.12 build_v6_full.py
  /tmp/dawdreamer_venv/bin/python3.12 build_v6_full.py --step select     # just pick MIDIs
  /tmp/dawdreamer_venv/bin/python3.12 build_v6_full.py --step virtuoso   # MusicXML + VirtuosoNet
  /tmp/dawdreamer_venv/bin/python3.12 build_v6_full.py --step render     # Piano V3 render
  /tmp/dawdreamer_venv/bin/python3.12 build_v6_full.py --step segment    # 30s segmentation
"""
import argparse, json, os, random, subprocess, sys, time
import numpy as np
import soundfile as sf_mod

ARIA = "/Volumes/project backup/score/aria-midi/aria-midi-v1-ext"
OUT_ROOT = "/Users/leo/oven/v6_data"
VIRTUOSO_DIR = "/Users/leo/oven/virtuosoNet"
PYTHON312 = "/tmp/dawdreamer_venv/bin/python3.12"
PLUGIN_PATH = "/Library/Audio/Plug-Ins/VST3/Piano V3.vst3"

PICKS = {
    "hisaishi": 10,
    "einaudi": 10,
    "yiruma": 8,
    "sakamoto": 8,
}

SCORE_MIN = 0.95
SEED = 42
SR_TARGET = 48000
SEG_LEN = 30.0
STRIDE = 15.0
MAX_PER_SONG = 20
RMS_MIN = 0.005
PEAK_MAX = 0.99
FADE_MS = 50

random.seed(SEED)

DIR_SELECT = os.path.join(OUT_ROOT, "selected")
DIR_MUSICXML = os.path.join(OUT_ROOT, "musicxml")
DIR_VIRTUOSO = os.path.join(OUT_ROOT, "virtuoso_midi")
DIR_TEMPO_FIXED = os.path.join(OUT_ROOT, "tempo_fixed_midi")
DIR_RENDER = os.path.join(OUT_ROOT, "render")
DIR_SEG = os.path.join(OUT_ROOT, "segments")
MANIFEST_PATH = os.path.join(OUT_ROOT, "manifest.json")


def step_select():
    """Select best MIDIs per composer from aria-midi."""
    print("\n[1/5] Selecting MIDIs...", flush=True)
    meta = json.load(open(f"{ARIA}/metadata.json"))

    # Build file index
    idx = {}
    for root, _, files in os.walk(f"{ARIA}/data"):
        for fn in files:
            if fn.endswith(".mid"):
                idx[fn[:-4]] = os.path.join(root, fn)
    print(f"  Index: {len(idx)} MIDI files", flush=True)

    selections = []
    for comp, n in PICKS.items():
        candidates = []
        for k, v in meta.items():
            if v.get("metadata", {}).get("composer", "") != comp:
                continue
            scores = v.get("audio_scores", {})
            if not scores:
                continue
            best_take = max(scores, key=scores.get)
            best_s = scores[best_take]
            if best_s >= SCORE_MIN:
                key = f"{k}_{best_take}"
                if key in idx:
                    candidates.append((best_s, k, best_take, idx[key]))

        candidates.sort(reverse=True)
        random.shuffle(candidates)
        picked = candidates[:n]
        for score, mid_id, take, path in picked:
            selections.append({
                "composer": comp, "mid_id": mid_id, "take": take,
                "score": score, "midi_path": path,
                "stem": f"{comp}_{mid_id}_{take}",
            })
        print(f"  {comp}: {len(picked)}/{len(candidates)} picked", flush=True)

    os.makedirs(DIR_SELECT, exist_ok=True)
    manifest = os.path.join(DIR_SELECT, "selections.json")
    with open(manifest, "w") as f:
        json.dump(selections, f, indent=2, ensure_ascii=False)
    print(f"  Total: {len(selections)} tracks → {manifest}", flush=True)
    return selections


def step_virtuoso(selections=None):
    """Convert to MusicXML, run VirtuosoNet, fix tempo."""
    if selections is None:
        selections = json.load(open(os.path.join(DIR_SELECT, "selections.json")))

    print(f"\n[2/5] VirtuosoNet pipeline ({len(selections)} tracks)...", flush=True)
    os.makedirs(DIR_MUSICXML, exist_ok=True)
    os.makedirs(DIR_VIRTUOSO, exist_ok=True)
    os.makedirs(DIR_TEMPO_FIXED, exist_ok=True)

    import music21
    import mido

    for i, sel in enumerate(selections, 1):
        stem = sel["stem"]
        midi_path = sel["midi_path"]

        # Check if already done
        final_mid = os.path.join(DIR_TEMPO_FIXED, f"{stem}.mid")
        if os.path.exists(final_mid):
            print(f"  [{i}/{len(selections)}] {stem} (cached)", flush=True)
            continue

        t0 = time.time()

        # 1) MIDI → MusicXML
        xml_dir = os.path.join(DIR_MUSICXML, stem)
        xml_path = os.path.join(xml_dir, "musicxml_cleaned.musicxml")
        if not os.path.exists(xml_path):
            os.makedirs(xml_dir, exist_ok=True)
            try:
                score = music21.converter.parse(midi_path)
                score.write("musicxml", fp=xml_path)
            except Exception as e:
                print(f"  [{i}/{len(selections)}] {stem} MusicXML FAIL: {e}", flush=True)
                continue

        # 2) VirtuosoNet
        vnet_test_dir = os.path.join(VIRTUOSO_DIR, "test_pieces", stem)
        if not os.path.exists(os.path.join(vnet_test_dir, "musicxml_cleaned.musicxml")):
            os.makedirs(vnet_test_dir, exist_ok=True)
            os.symlink(xml_path, os.path.join(vnet_test_dir, "musicxml_cleaned.musicxml"))

        vnet_out = os.path.join(VIRTUOSO_DIR, "test_result", f"{stem}_by_isgn_z0.mid")
        if not os.path.exists(vnet_out):
            r = subprocess.run(
                [PYTHON312, "model_run.py", "-mode=test", "-code=isgn",
                 f"-path=./test_pieces/{stem}/", "-comp=Chopin"],
                capture_output=True, text=True, cwd=VIRTUOSO_DIR,
            )
            if not os.path.exists(vnet_out):
                print(f"  [{i}/{len(selections)}] {stem} VirtuosoNet FAIL: {r.stderr[-200:]}", flush=True)
                continue

        # 3) Fix tempo: original timing + VirtuosoNet velocity/pedal
        try:
            orig = mido.MidiFile(midi_path)
            vnet = mido.MidiFile(vnet_out)

            vnet_vels = [m.velocity for t in vnet.tracks for m in t
                         if m.type == "note_on" and m.velocity > 0]

            vnet_dur = vnet.length
            orig_dur = orig.length
            ratio = orig_dur / vnet_dur if vnet_dur > 0 else 1.0

            # Get tempo
            tempo = 500000
            for t in orig.tracks:
                for m in t:
                    if m.type == "set_tempo":
                        tempo = m.tempo
                        break

            # Collect scaled CC events
            vnet_ccs = []
            for t in vnet.tracks:
                abs_time = 0.0
                for m in t:
                    abs_time += mido.tick2second(m.time, vnet.ticks_per_beat, 500000)
                    if m.type == "control_change":
                        vnet_ccs.append((abs_time * ratio, m.control, m.value))

            # Build new MIDI
            new_mid = mido.MidiFile(ticks_per_beat=orig.ticks_per_beat)
            track = mido.MidiTrack()
            new_mid.tracks.append(track)

            vel_idx = 0
            for t in orig.tracks:
                for m in t:
                    if m.type == "set_tempo":
                        track.append(m.copy())
                    elif m.type == "note_on" and m.velocity > 0:
                        new_msg = m.copy()
                        if vel_idx < len(vnet_vels):
                            new_msg.velocity = vnet_vels[vel_idx]
                            vel_idx += 1
                        track.append(new_msg)
                    elif m.type == "note_off" or (m.type == "note_on" and m.velocity == 0):
                        track.append(m.copy())
                    elif m.type in ("program_change", "time_signature", "key_signature"):
                        track.append(m.copy())

            cc_track = mido.MidiTrack()
            new_mid.tracks.append(cc_track)
            vnet_ccs.sort(key=lambda x: x[0])
            prev_tick = 0
            for time_sec, cc_num, cc_val in vnet_ccs:
                abs_tick = int(mido.second2tick(time_sec, orig.ticks_per_beat, tempo))
                delta = max(0, abs_tick - prev_tick)
                cc_track.append(mido.Message("control_change", control=cc_num, value=cc_val, time=delta))
                prev_tick = abs_tick

            new_mid.save(final_mid)
        except Exception as e:
            print(f"  [{i}/{len(selections)}] {stem} tempo fix FAIL: {e}", flush=True)
            continue

        elapsed = time.time() - t0
        print(f"  [{i}/{len(selections)}] {stem} ({elapsed:.1f}s)", flush=True)

    print(f"  Done: {len(os.listdir(DIR_TEMPO_FIXED))} tempo-fixed MIDIs", flush=True)


def step_render():
    """Render tempo-fixed MIDIs through Piano V3."""
    midis = sorted([f for f in os.listdir(DIR_TEMPO_FIXED) if f.endswith(".mid")])
    print(f"\n[3/5] Rendering {len(midis)} MIDIs with Piano V3...", flush=True)
    os.makedirs(DIR_RENDER, exist_ok=True)

    import dawdreamer as daw

    engine = daw.RenderEngine(SR_TARGET, 512)
    synth = engine.make_plugin_processor("synth", PLUGIN_PATH)
    print(f"  Plugin: {synth.get_name()}", flush=True)

    manifest = []
    for i, fn in enumerate(midis, 1):
        stem = fn[:-4]
        midi_path = os.path.join(DIR_TEMPO_FIXED, fn)
        out_path = os.path.join(DIR_RENDER, f"{stem}.wav")

        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            manifest.append({"stem": stem, "wav": out_path})
            print(f"  [{i}/{len(midis)}] {stem} (cached)", flush=True)
            continue

        t0 = time.time()
        try:
            synth.clear_midi()
            synth.load_midi(midi_path)

            import mido
            mid = mido.MidiFile(midi_path)
            duration = mid.length + 3.0

            engine.load_graph([(synth, [])])
            engine.render(duration)
            output = engine.get_audio()

            output = output * 0.8
            peak = np.max(np.abs(output))
            if peak > 0.99:
                output = output * (0.99 / peak)

            sf_mod.write(out_path, output.T, SR_TARGET, subtype="PCM_16")
            manifest.append({"stem": stem, "wav": out_path})
            elapsed = time.time() - t0
            print(f"  [{i}/{len(midis)}] {stem} ({duration:.0f}s audio, {elapsed:.1f}s render)", flush=True)
        except Exception as e:
            print(f"  [{i}/{len(midis)}] {stem} FAIL: {e}", flush=True)

    with open(os.path.join(DIR_RENDER, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Rendered: {len(manifest)}/{len(midis)}", flush=True)
    return manifest


def step_segment(manifest=None):
    """Segment rendered WAVs into 30s clips."""
    if manifest is None:
        manifest = json.load(open(os.path.join(DIR_RENDER, "manifest.json")))

    print(f"\n[4/5] Segmenting {len(manifest)} renders...", flush=True)
    os.makedirs(DIR_SEG, exist_ok=True)

    seg_samples = int(SEG_LEN * SR_TARGET)
    stride_samples = int(STRIDE * SR_TARGET)
    fade_n = int(FADE_MS / 1000 * SR_TARGET)
    fade_in = np.linspace(0, 1, fade_n) ** 2
    fade_out = np.linspace(1, 0, fade_n) ** 2

    seg_manifest = []
    total_seg = 0

    for entry in manifest:
        wav_path = entry["wav"]
        if not os.path.exists(wav_path):
            continue
        data, sr = sf_mod.read(wav_path)
        if data.ndim > 1:
            data = np.mean(data, axis=1)

        stem = entry["stem"]
        composer = stem.split("_")[0]
        count = 0
        pos = 0
        while pos + seg_samples <= len(data) and count < MAX_PER_SONG:
            seg = data[pos:pos + seg_samples].copy()
            rms = np.sqrt(np.mean(seg ** 2))
            peak = np.max(np.abs(seg))
            if rms < RMS_MIN or peak > PEAK_MAX:
                pos += stride_samples
                continue

            seg[:fade_n] *= fade_in
            seg[-fade_n:] *= fade_out

            out_name = f"{stem}_seg{count:02d}.wav"
            sf_mod.write(os.path.join(DIR_SEG, out_name), seg, SR_TARGET, subtype="PCM_16")
            seg_manifest.append({
                "file": out_name, "source": stem, "composer": composer,
                "rms": round(float(rms), 5), "peak": round(float(peak), 4),
            })
            count += 1
            total_seg += 1
            pos += stride_samples

    with open(os.path.join(DIR_SEG, "manifest.json"), "w") as f:
        json.dump(seg_manifest, f, indent=2, ensure_ascii=False)
    print(f"  Total segments: {total_seg}", flush=True)
    print(f"  Manifest: {os.path.join(DIR_SEG, 'manifest.json')}", flush=True)
    return seg_manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--step", choices=["select", "virtuoso", "render", "segment"],
                   help="Run only one step")
    args = p.parse_args()

    os.makedirs(OUT_ROOT, exist_ok=True)

    if args.step:
        if args.step == "select":
            step_select()
        elif args.step == "virtuoso":
            step_virtuoso()
        elif args.step == "render":
            step_render()
        elif args.step == "segment":
            step_segment()
    else:
        sels = step_select()
        step_virtuoso(sels)
        manifest = step_render()
        seg_manifest = step_segment(manifest)
        print(f"\n[5/5] DONE — {len(seg_manifest)} segments in {DIR_SEG}", flush=True)
