#!/bin/bash
# ACE Studio MIDI 가져오기 테스트
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/modules/core.sh"
source "$SCRIPT_DIR/modules/import_midi.sh"
source "$SCRIPT_DIR/modules/project.sh"

echo "=== Phase 2: MIDI 가져오기 테스트 ==="
echo ""

MIDI_TEST="$HOME/ACE_Studio/project/temp_workspace/working_document/test_piano.mid"

if [ ! -f "$MIDI_TEST" ]; then
    echo "테스트 MIDI 파일이 없습니다: $MIDI_TEST"
    echo "test_piano.mid를 working_document에 넣어주세요"
    exit 1
fi

# ACE Studio 준비
ace_ensure_running
sleep 2

# 2.1 MIDI 가져오기 다이얼로그 열기
echo "[2.1] MIDI 가져오기 다이얼로그"
ace_import_midi_open_dialog
echo "  → 다이얼로그가 열렸는지 확인해주세요"
sleep 3

# ESC로 닫기
ace_key_escape
sleep 1

# 2.2 전체 흐름: MIDI import
echo "[2.2] 전체 MIDI 가져오기 흐름"
ace_import_midi "$MIDI_TEST"
echo "  → 트랙이 생성되었는지 확인해주세요"
sleep 2

# 스크린샷으로 결과 확인
ace_screenshot "/tmp/ace_test_import.png"
echo "  스크린샷: /tmp/ace_test_import.png"

echo ""
echo "=== Phase 2 완료 — 스크린샷을 확인해주세요 ==="
