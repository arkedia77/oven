#!/bin/bash
# ACE Studio GUI 자동화 — AI 악기 모듈 (검증됨 2026-04-26)
# 사용법: source modules/core.sh && source modules/instrument.sh
#
# 검증된 워크플로우:
#   1. MIDI 클립 더블클릭 → 팝업 메뉴
#   2. "MIDI에서 악기 생성" 클릭 → 악기 선택 패널
#   3. 악기 썸네일 클릭 → 새 악기 트랙 생성 (MIDI 복사됨)

# MIDI 클립에서 AI 악기 트랙 생성
# $1 = 클릭할 클립의 x좌표 (기본: 캔버스 중앙)
# $2 = 클릭할 클립의 y좌표 (기본: 첫 번째 트랙 위치)
ace_instrument_create_from_midi() {
    local clip_x=${1:-300}
    local clip_y=${2:-365}

    ace_log "MIDI에서 악기 트랙 생성"

    # 1. 다른 곳 클릭 (선택 해제) → MIDI 클립 더블클릭 → 팝업
    cliclick "c:800,600" "w:300" "dc:${clip_x},${clip_y}" "w:700"

    # 2. "MIDI에서 악기 생성" 클릭 (팝업에서 두 번째 항목, dy≈85)
    local popup_y=$((clip_y + 85))
    cliclick "c:${clip_x},${popup_y}"
    ace_wait 2

    ace_log "악기 선택 패널 열림"
}

# 악기 패널에서 악기 선택 (이름 검색 방식)
ace_instrument_search_and_select() {
    local instrument_name="$1"
    ace_log "악기 검색: $instrument_name"

    # 악기 패널의 검색창 클릭 → 이름 입력 → 첫 번째 결과 클릭
    # 패널 위치는 가변적 — 윈도우 중앙 근처에 나타남
    local info
    info=$(ace_get_window_info)
    local ww=$(echo "$info" | cut -d',' -f3)
    local wy=$(echo "$info" | cut -d',' -f2)

    # 검색창은 패널 상단 (대략 윈도우 중앙 x, 윈도우 상단에서 40% 정도)
    local search_x=$((ww / 2 + 100))
    local search_y=$((wy + 250))

    # 검색창 클릭 → 입력
    cliclick "c:${search_x},${search_y}"
    ace_wait 0.3
    ace_keystroke_cmd "a"
    ace_type_text "$instrument_name"
    ace_wait 1

    # 첫 번째 검색 결과 클릭 (검색창 아래 ~120px)
    cliclick "c:${search_x},$((search_y + 120))"
    ace_wait 3

    ace_log "악기 선택됨: $instrument_name"
}

# 악기 패널에서 인덱스로 선택 (검색 없이 직접 클릭)
# 카테고리 내에서의 행(row)과 열(col) 기반
ace_instrument_select_by_position() {
    local row=${1:-0}
    local col=${2:-0}

    ace_log "악기 선택: 위치 row=$row, col=$col"

    # 패널 그리드 레이아웃: 3열, 행 간격 ≈ 60px, 열 간격 ≈ 230px
    # 첫 번째 Strings 항목 기준 (검증된 좌표)
    local info
    info=$(ace_get_window_info)
    local base_x=$(($(echo "$info" | cut -d',' -f3) / 2 - 250))
    local base_y=$(($(echo "$info" | cut -d',' -f2) + 440))

    local target_x=$((base_x + col * 230))
    local target_y=$((base_y + row * 60))

    cliclick "c:${target_x},${target_y}"
    ace_wait 3

    ace_log "악기 선택 완료 (row=$row, col=$col)"
}

# 전체 파이프라인: MIDI 클립 → 특정 악기로 변환
ace_instrument_assign() {
    local instrument_name="${1:-Violin}"
    local clip_x=${2:-300}
    local clip_y=${3:-365}

    ace_log "=== 악기 할당: $instrument_name ==="
    ace_instrument_create_from_midi "$clip_x" "$clip_y"
    ace_instrument_search_and_select "$instrument_name"
    ace_log "=== 악기 할당 완료 ==="
}

ace_instrument_list() {
    cat <<'INSTRUMENTS'
[Strings] (13)
  Violin - Gabriele Boschi
  Vintage Violin 1~5
  Viola - Nico
  Modern Viola
  Cello - Angelo
  Vintage Cello 1+

[Brass]
  Trumpet - Xiaochuan Li

[Woodwinds]
  Saxophone - Bob Magnuson
  Saxophone - Carlo Alfonso
  Duduk

[NOT Available as AI Instrument]
  Piano (use SoundFont or ACE-Step)
  Guitar
  Drums
INSTRUMENTS
}
