"""
Liszt Player — MIDI SoundFont Player for Mac
=============================================
Usage: python liszt_player.py [midi_file_or_folder]
"""
import sys
import os
import time
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QListWidget,
    QListWidgetItem, QComboBox, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent

import fluidsynth
import pretty_midi

DEFAULT_SF2_PATHS = [
    os.path.expanduser("~/musicscore/soundfonts/SalamanderGrandPiano-SF2-V3+20200602/SalamanderGrandPiano-V3+20200602.sf2"),
    os.path.expanduser("~/musicscore/soundfonts/Steinway_Model_C.sf2"),
    os.path.expanduser("~/ACE_Studio/Instrument preview samples/Piano_de_Cola_(Grand_Piano).sf2"),
    os.path.expanduser("~/musicscore/dashboard/piano.sf2"),
]


class MidiPlayer(QObject):
    """pretty_midi + fluidsynth noteon/noteoff 방식 재생"""
    playback_finished = pyqtSignal()
    status_changed = pyqtSignal(str)
    time_changed = pyqtSignal(float, float)  # current, total

    def __init__(self):
        super().__init__()
        self.fs = None
        self.sfid = None
        self.playing = False
        self.current_file = None
        self._play_thread = None
        self._stop_event = threading.Event()

    def init_synth(self, sf2_path):
        if self.fs:
            self.stop()
            try:
                self.fs.delete()
            except:
                pass

        self.fs = fluidsynth.Synth(samplerate=44100.0)
        self.fs.start(driver="coreaudio")

        if os.path.exists(sf2_path):
            self.sfid = self.fs.sfload(sf2_path)
            self.fs.program_select(0, self.sfid, 0, 0)
            self.status_changed.emit(f"SF2: {Path(sf2_path).name}")
            return True
        return False

    def play_file(self, midi_path):
        self.stop()
        self.current_file = midi_path
        self._stop_event.clear()
        self.playing = True

        self._play_thread = threading.Thread(target=self._play_worker, args=(midi_path,), daemon=True)
        self._play_thread.start()

    def _play_worker(self, midi_path):
        try:
            pm = pretty_midi.PrettyMIDI(midi_path)
        except Exception as e:
            self.status_changed.emit(f"Error: {e}")
            self.playing = False
            self.playback_finished.emit()
            return

        # 모든 노트를 시간순 이벤트로 변환
        events = []
        for inst in pm.instruments:
            if inst.is_drum:
                continue
            for note in inst.notes:
                events.append((note.start, 'on', note.pitch, note.velocity, 0))
                events.append((note.end, 'off', note.pitch, 0, 0))
            # 서스테인 페달 (CC 64)
            for cc in inst.control_changes:
                events.append((cc.time, 'cc', cc.number, cc.value, 0))

        events.sort(key=lambda x: x[0])

        if not events:
            self.playing = False
            self.playback_finished.emit()
            return

        total_dur = pm.get_end_time()
        self.status_changed.emit(f"Playing: {Path(midi_path).name} ({total_dur:.1f}s)")

        start_time = time.time()
        for evt_time, evt_type, p1, p2, ch in events:
            if self._stop_event.is_set():
                break

            # 이벤트 시간까지 대기
            elapsed = time.time() - start_time
            wait = evt_time - elapsed
            if wait > 0:
                # 작은 단위로 sleep해서 stop 반응성 확보
                while wait > 0 and not self._stop_event.is_set():
                    time.sleep(min(wait, 0.02))
                    elapsed = time.time() - start_time
                    wait = evt_time - elapsed

            if self._stop_event.is_set():
                break

            if evt_type == 'on':
                self.fs.noteon(ch, p1, p2)
            elif evt_type == 'off':
                self.fs.noteoff(ch, p1)
            elif evt_type == 'cc':
                self.fs.cc(ch, p1, p2)

            # 시간 업데이트 (0.5초마다)
            cur = time.time() - start_time
            if int(cur * 2) != int((cur - 0.02) * 2):
                self.time_changed.emit(cur, total_dur)

        # 모든 노트 끄기
        for ch in range(16):
            for note in range(128):
                self.fs.noteoff(ch, note)

        self.playing = False
        if not self._stop_event.is_set():
            self.playback_finished.emit()

    def stop(self):
        self._stop_event.set()
        self.playing = False
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=2)
        # 모든 노트 끄기
        if self.fs:
            for ch in range(16):
                for note in range(128):
                    self.fs.noteoff(ch, note)

    def render_wav(self, midi_path, wav_path, sf2_path):
        """MIDI → WAV 렌더링 (오프라인, 실시간 아님)"""
        fs = fluidsynth.Synth(samplerate=44100.0)
        sfid = fs.sfload(sf2_path)
        fs.program_select(0, sfid, 0, 0)

        pm = pretty_midi.PrettyMIDI(midi_path)
        events = []
        for inst in pm.instruments:
            if inst.is_drum:
                continue
            for note in inst.notes:
                events.append((note.start, 'on', note.pitch, note.velocity, 0))
                events.append((note.end, 'off', note.pitch, 0, 0))
            for cc in inst.control_changes:
                events.append((cc.time, 'cc', cc.number, cc.value, 0))
        events.sort(key=lambda x: x[0])

        if not events:
            fs.delete()
            return False

        total_dur = pm.get_end_time() + 2.0  # 2초 여유 (리버브 테일)
        sample_rate = 44100
        total_samples = int(total_dur * sample_rate)

        import numpy as np
        import wave

        audio = np.zeros((total_samples, 2), dtype=np.float32)
        current_sample = 0

        for evt_time, evt_type, p1, p2, ch in events:
            target_sample = int(evt_time * sample_rate)
            if target_sample > current_sample:
                chunk_len = target_sample - current_sample
                samples = fs.get_samples(chunk_len)
                chunk = np.frombuffer(samples, dtype=np.int16).reshape(-1, 2).astype(np.float32) / 32768.0
                end = min(current_sample + len(chunk), total_samples)
                audio[current_sample:end] = chunk[:end - current_sample]
                current_sample = end

            if evt_type == 'on':
                fs.noteon(ch, p1, p2)
            elif evt_type == 'off':
                fs.noteoff(ch, p1)
            elif evt_type == 'cc':
                fs.cc(ch, p1, p2)

        # 남은 오디오 (리버브 테일)
        remaining = total_samples - current_sample
        if remaining > 0:
            samples = fs.get_samples(remaining)
            chunk = np.frombuffer(samples, dtype=np.int16).reshape(-1, 2).astype(np.float32) / 32768.0
            end = min(current_sample + len(chunk), total_samples)
            audio[current_sample:end] = chunk[:end - current_sample]

        fs.delete()

        # WAV 저장 (16-bit)
        audio_int16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
        with wave.open(wav_path, 'w') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return True

    def cleanup(self):
        self.stop()
        if self.fs:
            try:
                self.fs.delete()
            except:
                pass


class LisztPlayerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.player = MidiPlayer()
        self.midi_files = []
        self.current_sf2 = None
        self.setup_ui()
        self.load_default_sf2()

    def setup_ui(self):
        self.setWindowTitle("Liszt Player")
        self.setMinimumSize(700, 500)
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # SoundFont
        sf2_group = QGroupBox("SoundFont")
        sf2_layout = QHBoxLayout(sf2_group)
        self.sf2_combo = QComboBox()
        self.sf2_combo.setMinimumWidth(300)
        for sf2 in DEFAULT_SF2_PATHS:
            if os.path.exists(sf2):
                self.sf2_combo.addItem(Path(sf2).name, sf2)
        self.sf2_combo.currentIndexChanged.connect(self.on_sf2_changed)
        sf2_layout.addWidget(self.sf2_combo)
        sf2_browse = QPushButton("Browse...")
        sf2_browse.clicked.connect(self.browse_sf2)
        sf2_layout.addWidget(sf2_browse)
        layout.addWidget(sf2_group)

        # 파일 리스트 + 컨트롤
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # MIDI 리스트
        list_group = QGroupBox("MIDI Files (drag & drop)")
        list_layout = QVBoxLayout(list_group)
        self.file_list = QListWidget()
        self.file_list.setFont(QFont("Menlo", 12))
        self.file_list.itemDoubleClicked.connect(self.on_file_double_click)
        list_layout.addWidget(self.file_list)

        list_buttons = QHBoxLayout()
        add_btn = QPushButton("Add Files...")
        add_btn.clicked.connect(self.browse_midi)
        list_buttons.addWidget(add_btn)
        add_dir_btn = QPushButton("Add Folder...")
        add_dir_btn.clicked.connect(self.browse_midi_dir)
        list_buttons.addWidget(add_dir_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_list)
        list_buttons.addWidget(clear_btn)
        list_layout.addLayout(list_buttons)
        splitter.addWidget(list_group)

        # 컨트롤
        ctrl_group = QGroupBox("Controls")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self.info_label = QLabel("No file loaded")
        self.info_label.setFont(QFont("Menlo", 11))
        self.info_label.setWordWrap(True)
        ctrl_layout.addWidget(self.info_label)

        self.time_label = QLabel("")
        self.time_label.setFont(QFont("Menlo", 13))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(self.time_label)

        ctrl_layout.addStretch()

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶  Play")
        self.play_btn.setFont(QFont("Menlo", 14))
        self.play_btn.setMinimumHeight(50)
        self.play_btn.clicked.connect(self.on_play)
        btn_layout.addWidget(self.play_btn)
        self.stop_btn = QPushButton("■  Stop")
        self.stop_btn.setFont(QFont("Menlo", 14))
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.clicked.connect(self.on_stop)
        btn_layout.addWidget(self.stop_btn)
        ctrl_layout.addLayout(btn_layout)

        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("⏮ Prev")
        prev_btn.clicked.connect(self.on_prev)
        nav_layout.addWidget(prev_btn)
        next_btn = QPushButton("Next ⏭")
        next_btn.clicked.connect(self.on_next)
        nav_layout.addWidget(next_btn)
        ctrl_layout.addLayout(nav_layout)

        # WAV 렌더링
        render_layout = QHBoxLayout()
        self.render_btn = QPushButton("Render WAV")
        self.render_btn.clicked.connect(self.on_render_wav)
        render_layout.addWidget(self.render_btn)
        self.render_all_btn = QPushButton("Render All WAV")
        self.render_all_btn.clicked.connect(self.on_render_all_wav)
        render_layout.addWidget(self.render_all_btn)
        ctrl_layout.addLayout(render_layout)

        ctrl_layout.addStretch()

        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("Volume:"))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 127)
        self.vol_slider.setValue(100)
        self.vol_slider.valueChanged.connect(self.on_volume_changed)
        vol_layout.addWidget(self.vol_slider)
        ctrl_layout.addLayout(vol_layout)

        splitter.addWidget(ctrl_group)
        splitter.setSizes([400, 300])
        layout.addWidget(splitter)

        self.statusBar().showMessage("Ready — Drop MIDI files to start")

        # 시그널
        self.player.status_changed.connect(self.statusBar().showMessage)
        self.player.playback_finished.connect(self.on_playback_finished)
        self.player.time_changed.connect(self.on_time_changed)

    def load_default_sf2(self):
        for sf2 in DEFAULT_SF2_PATHS:
            if os.path.exists(sf2):
                self.current_sf2 = sf2
                self.player.init_synth(sf2)
                return

    def on_sf2_changed(self, index):
        sf2_path = self.sf2_combo.itemData(index)
        if sf2_path:
            self.current_sf2 = sf2_path
            self.player.init_synth(sf2_path)

    def browse_sf2(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select SoundFont", "", "SoundFont (*.sf2)")
        if path:
            self.sf2_combo.addItem(Path(path).name, path)
            self.sf2_combo.setCurrentIndex(self.sf2_combo.count() - 1)

    def browse_midi(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select MIDI", "", "MIDI (*.mid *.midi)")
        for p in paths:
            self.add_midi_file(p)

    def browse_midi_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if dir_path:
            for f in sorted(Path(dir_path).rglob("*.mid")):
                self.add_midi_file(str(f))

    def add_midi_file(self, path):
        if path not in self.midi_files:
            self.midi_files.append(path)
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.file_list.addItem(item)

    def clear_list(self):
        self.on_stop()
        self.midi_files.clear()
        self.file_list.clear()
        self.info_label.setText("No file loaded")
        self.time_label.setText("")

    def on_file_double_click(self, item):
        self.play_selected(item)

    def play_selected(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.on_stop()

        # synth 재초기화 (이전 재생 잔여음 방지)
        if self.current_sf2:
            self.player.init_synth(self.current_sf2)

        # 파일 정보
        try:
            pm = pretty_midi.PrettyMIDI(path)
            dur = pm.get_end_time()
            notes = sum(len(i.notes) for i in pm.instruments)
            self.info_label.setText(
                f"File: {Path(path).name}\n"
                f"Duration: {dur:.1f}s | Notes: {notes}\n"
                f"SF2: {Path(self.current_sf2).name if self.current_sf2 else 'None'}"
            )
        except:
            self.info_label.setText(f"File: {Path(path).name}")

        self.player.play_file(path)
        self.play_btn.setText("▶  Playing...")

    def on_play(self):
        if self.player.playing:
            return
        item = self.file_list.currentItem()
        if not item and self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)
            item = self.file_list.currentItem()
        if item:
            self.play_selected(item)

    def on_stop(self):
        self.player.stop()
        self.play_btn.setText("▶  Play")
        self.time_label.setText("")

    def on_prev(self):
        row = self.file_list.currentRow()
        if row > 0:
            self.file_list.setCurrentRow(row - 1)
            self.on_play()

    def on_next(self):
        row = self.file_list.currentRow()
        if row < self.file_list.count() - 1:
            self.file_list.setCurrentRow(row + 1)
            self.on_play()

    def on_render_wav(self):
        """현재 선택된 MIDI → WAV 렌더링"""
        item = self.file_list.currentItem()
        if not item:
            self.statusBar().showMessage("No file selected")
            return
        if not self.current_sf2:
            self.statusBar().showMessage("No SoundFont loaded")
            return

        midi_path = item.data(Qt.ItemDataRole.UserRole)
        default_name = Path(midi_path).with_suffix('.wav').name
        wav_path, _ = QFileDialog.getSaveFileName(
            self, "Save WAV", str(Path(midi_path).parent / default_name), "WAV (*.wav)")
        if not wav_path:
            return

        self.render_btn.setEnabled(False)
        self.statusBar().showMessage(f"Rendering: {Path(midi_path).name}...")
        QApplication.processEvents()

        def _do_render():
            try:
                ok = self.player.render_wav(midi_path, wav_path, self.current_sf2)
                if ok:
                    self.player.status_changed.emit(f"WAV saved: {Path(wav_path).name}")
                else:
                    self.player.status_changed.emit("Render failed — no notes")
            except Exception as e:
                self.player.status_changed.emit(f"Render error: {e}")
            self.render_btn.setEnabled(True)

        threading.Thread(target=_do_render, daemon=True).start()

    def on_render_all_wav(self):
        """리스트 전체 MIDI → WAV 일괄 렌더링"""
        if self.file_list.count() == 0:
            self.statusBar().showMessage("No files in list")
            return
        if not self.current_sf2:
            self.statusBar().showMessage("No SoundFont loaded")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select output folder")
        if not out_dir:
            return

        self.render_all_btn.setEnabled(False)
        total = self.file_list.count()

        def _do_render_all():
            ok_count, fail_count = 0, 0
            for i in range(total):
                item = self.file_list.item(i)
                midi_path = item.data(Qt.ItemDataRole.UserRole)
                wav_name = Path(midi_path).with_suffix('.wav').name
                wav_path = str(Path(out_dir) / wav_name)
                self.player.status_changed.emit(f"Rendering {i+1}/{total}: {Path(midi_path).name}")
                try:
                    if self.player.render_wav(midi_path, wav_path, self.current_sf2):
                        ok_count += 1
                    else:
                        fail_count += 1
                except:
                    fail_count += 1
            self.player.status_changed.emit(f"Render complete: {ok_count} ok, {fail_count} fail / {total}")
            self.render_all_btn.setEnabled(True)

        threading.Thread(target=_do_render_all, daemon=True).start()

    def on_playback_finished(self):
        self.play_btn.setText("▶  Play")
        row = self.file_list.currentRow()
        if row < self.file_list.count() - 1:
            self.file_list.setCurrentRow(row + 1)
            self.on_play()

    def on_time_changed(self, current, total):
        self.time_label.setText(f"{current:.0f}s / {total:.0f}s")

    def on_volume_changed(self, value):
        if self.player.fs:
            for ch in range(16):
                self.player.fs.cc(ch, 7, value)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.mid', '.midi')):
                self.add_midi_file(path)
            elif os.path.isdir(path):
                for f in sorted(Path(path).rglob("*.mid")):
                    self.add_midi_file(str(f))

    def closeEvent(self, event):
        self.player.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = LisztPlayerApp()

    for arg in sys.argv[1:]:
        if os.path.isfile(arg) and arg.lower().endswith(('.mid', '.midi')):
            window.add_midi_file(arg)
        elif os.path.isdir(arg):
            for f in sorted(Path(arg).rglob("*.mid")):
                window.add_midi_file(str(f))

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
