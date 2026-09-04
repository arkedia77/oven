"""Render MIDI files through VST3 instrument plugins via DawDreamer.

Usage:
  python3 render_vsti.py scan                          # list installed plugins (pedalboard)
  python3 render_vsti.py render --plugin /path/to.vst3 --midi input.mid --out output.wav
  python3 render_vsti.py batch --plugin /path/to.vst3 --midi-dir ./midis --out-dir ./renders

Requires: dawdreamer, mido, soundfile, numpy
  DawDreamer needs Python 3.12 (not 3.14): /tmp/dawdreamer_venv/bin/python3.12
"""
import argparse, glob, os, sys, time
import numpy as np
import soundfile as sf


def scan_plugins():
    """List all installed VST3 and AU plugins (uses pedalboard for scanning)."""
    from pedalboard import VST3Plugin, AudioUnitPlugin
    print("=== VST3 Plugins ===")
    for p in sorted(VST3Plugin.installed_plugins):
        print(f"  {p}")
    if sys.platform == "darwin":
        print("\n=== Audio Unit Plugins ===")
        for p in sorted(AudioUnitPlugin.installed_plugins):
            print(f"  {p}")


def parse_midi_notes(midi_path):
    """Parse MIDI file into notes and CC events."""
    import mido
    mid = mido.MidiFile(midi_path)
    notes = []
    cc_events = []
    max_time = 0
    for track in mid.tracks:
        abs_time = 0.0
        active = {}
        for msg in track:
            abs_time += mido.tick2second(msg.time, mid.ticks_per_beat, 500000)
            if msg.type == "note_on" and msg.velocity > 0:
                active[msg.note] = (abs_time, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in active:
                    start, vel = active.pop(msg.note)
                    dur = abs_time - start
                    if dur > 0:
                        notes.append((msg.note, vel, start, dur))
            elif msg.type == "control_change":
                cc_events.append((abs_time, msg.control, msg.value))
        for note, (start, vel) in active.items():
            notes.append((note, vel, start, 2.0))
        if abs_time > max_time:
            max_time = abs_time
    return notes, cc_events, max_time + 3.0


def render_midi(plugin_path, midi_path, out_path, sr=48000, gain=0.8, **_):
    """Render a single MIDI file through a VSTi plugin using DawDreamer."""
    import dawdreamer as daw

    engine = daw.RenderEngine(sr, 512)
    synth = engine.make_plugin_processor("synth", plugin_path)
    print(f"  Plugin: {synth.get_name()} ({synth.get_plugin_parameter_size()} params)")

    notes, cc_events, duration = parse_midi_notes(midi_path)
    print(f"  Notes: {len(notes)}, CC events: {len(cc_events)}, duration: {duration:.1f}s")

    synth.load_midi(midi_path)

    engine.load_graph([(synth, [])])
    engine.render(duration)
    output = engine.get_audio()

    output = output * gain
    peak = np.max(np.abs(output))
    if peak > 0.99:
        output = output * (0.99 / peak)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    sf.write(out_path, output.T, sr, subtype="PCM_24")
    print(f"  → {out_path} ({duration:.1f}s, peak={peak:.4f})")
    return True


def batch_render(plugin_path, midi_dir, out_dir, sr=48000, **_):
    """Render all MIDI files in a directory."""
    midis = sorted(glob.glob(os.path.join(midi_dir, "**", "*.mid"), recursive=True))
    if not midis:
        print(f"No MIDI files in {midi_dir}")
        return

    print(f"Found {len(midis)} MIDI files")
    os.makedirs(out_dir, exist_ok=True)

    for i, mid in enumerate(midis, 1):
        rel = os.path.relpath(mid, midi_dir)
        out = os.path.join(out_dir, os.path.splitext(rel)[0] + ".wav")
        print(f"\n[{i}/{len(midis)}] {rel}")
        t0 = time.time()
        try:
            render_midi(plugin_path, mid, out, sr=sr)
        except Exception as e:
            print(f"  FAILED: {e}")
        print(f"  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Render MIDI through VSTi plugins")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("scan", help="List installed plugins")

    rp = sub.add_parser("render", help="Render single MIDI")
    rp.add_argument("--plugin", required=True, help="Path to VST3/AU plugin")
    rp.add_argument("--midi", required=True, help="Input MIDI file")
    rp.add_argument("--out", required=True, help="Output WAV file")
    rp.add_argument("--sr", type=int, default=48000)

    bp = sub.add_parser("batch", help="Batch render MIDI directory")
    bp.add_argument("--plugin", required=True, help="Path to VST3/AU plugin")
    bp.add_argument("--midi-dir", required=True, help="Input MIDI directory")
    bp.add_argument("--out-dir", required=True, help="Output WAV directory")
    bp.add_argument("--sr", type=int, default=48000)

    args = p.parse_args()

    if args.cmd == "scan":
        scan_plugins()
    elif args.cmd == "render":
        render_midi(args.plugin, args.midi, args.out, sr=args.sr)
    elif args.cmd == "batch":
        batch_render(args.plugin, args.midi_dir, args.out_dir, sr=args.sr)
    else:
        p.print_help()
