#!/bin/bash
# ACE Studio 오디오 내보내기 테스트
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/modules/core.sh"
source "$SCRIPT_DIR/modules/export_audio.sh"

echo "=== Phase 5: 내보내기 테스트 ==="
echo ""

ace_ensure_running
sleep 1

# 5.1 오디오 내보내기 다이얼로그 열기
echo "[5.1] 오디오 내보내기 다이얼로그"
ace_export_audio_open_dialog
echo "  → 내보내기 다이얼로그가 열렸는지 확인해주세요"
ace_screenshot "/tmp/ace_test_export_dialog.png"
sleep 2
ace_key_escape
sleep 1

# 5.3 MIDI 내보내기 다이얼로그 열기
echo "[5.3] MIDI 내보내기 다이얼로그"
ace_export_midi_open_dialog
echo "  → MIDI 내보내기 다이얼로그가 열렸는지 확인해주세요"
ace_screenshot "/tmp/ace_test_export_midi_dialog.png"
sleep 2
ace_key_escape

echo ""
echo "=== Phase 5 완료 — 스크린샷을 확인해주세요 ==="
echo "  /tmp/ace_test_export_dialog.png"
echo "  /tmp/ace_test_export_midi_dialog.png"
