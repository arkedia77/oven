#!/bin/bash
# ACE Studio GUI 자동화 — AI 보컬 모듈 (검증됨 2026-04-26)
# 사용법: source modules/core.sh && source modules/vocal.sh
#
# 검증된 워크플로우:
#   1. MIDI 클립 더블클릭 → 팝업 메뉴
#   2. "MIDI에서 보컬 생성" 클릭 → Singer 선택 패널
#   3. Singer 옆 "+" 버튼 클릭 → 새 보컬 트랙 생성 (MIDI 복사됨)
#
# Singer 패널 구조:
#   - 타이틀: "보컬 신스 음성"
#   - V2 (Beta) / V1 탭
#   - 검색: "음성 검색"
#   - 카테고리: 사전 제작 / 복제됨 / 커뮤니티 / 혼합 / 합창
#   - 3열 그리드: 썸네일 + 이름 + 태그 + "+" 버튼

# MIDI 클립에서 AI 보컬 트랙 생성
ace_vocal_create_from_midi() {
    local clip_x=${1:-300}
    local clip_y=${2:-290}

    ace_log "MIDI에서 보컬 트랙 생성"

    # 1. 선택 해제 → MIDI 클립 더블클릭 → 팝업
    cliclick "c:800,600" "w:300" "dc:${clip_x},${clip_y}" "w:700"
    sleep 0.5

    # 2. "MIDI에서 보컬 생성" 클릭 (팝업 첫 번째 항목)
    # 팝업 위치: 더블클릭 좌표 기준 dx≈+70, dy≈-15
    local popup_x=$((clip_x + 70))
    local popup_y=$((clip_y - 15))
    cliclick "c:${popup_x},${popup_y}"
    ace_wait 3

    ace_log "Singer 선택 패널 열림"
}

# Singer 패널에서 검색으로 Singer 선택
ace_vocal_search_and_select() {
    local singer_name="$1"
    ace_log "Singer 검색: $singer_name"

    local info
    info=$(ace_get_window_info)
    local ww=$(echo "$info" | cut -d',' -f3)
    local wy=$(echo "$info" | cut -d',' -f2)

    # 검색창: 패널 중앙 상단 (윈도우 중앙 x, 패널 상단에서 ~100px)
    # 검증된 좌표 기준: 검색창 y ≈ wy + 415 (3008x1572 윈도우)
    local search_x=$((ww / 2 + 100))
    local search_y=$((wy + 630))

    cliclick "c:${search_x},${search_y}"
    ace_wait 0.3
    ace_keystroke_cmd "a"
    ace_type_text "$singer_name"
    ace_wait 1

    # 첫 번째 검색 결과의 "+" 버튼 클릭 (검색결과 우측)
    local plus_x=$((search_x + 150))
    local plus_y=$((search_y + 80))
    cliclick "c:${plus_x},${plus_y}"
    ace_wait 5

    ace_log "Singer 선택됨: $singer_name"
}

# Singer 패널에서 그리드 위치로 선택
# row=0-based (0=Elirah행), col=0-2 (3열)
ace_vocal_select_by_position() {
    local row=${1:-0}
    local col=${2:-0}

    ace_log "Singer 선택: row=$row, col=$col"

    local info
    info=$(ace_get_window_info)
    local wy=$(echo "$info" | cut -d',' -f2)
    local ww=$(echo "$info" | cut -d',' -f3)

    # 그리드 시작: 패널 상단에서 ~160px, 각 행 ~50px, 각 열 ~230px
    # "+" 버튼은 각 Singer 카드 우측 끝
    local grid_start_x=$((ww / 2 - 350))
    local grid_start_y=$((wy + 730))
    local col_width=230
    local row_height=50

    local target_x=$((grid_start_x + col * col_width + 200))
    local target_y=$((grid_start_y + row * row_height))

    ace_log "Singer + 클릭: ($target_x, $target_y)"
    cliclick "c:${target_x},${target_y}"
    ace_wait 5

    ace_log "Singer 선택 완료 (row=$row, col=$col)"
}

# 전체 파이프라인: MIDI 클립 → 보컬 트랙 생성
ace_vocal_assign() {
    local singer_name="${1:-Elirah}"
    local clip_x=${2:-300}
    local clip_y=${3:-290}

    ace_log "=== 보컬 할당: $singer_name ==="
    ace_vocal_create_from_midi "$clip_x" "$clip_y"
    ace_vocal_search_and_select "$singer_name"
    ace_log "=== 보컬 할당 완료 ==="
}

# 가사 입력: 피아노롤에서 노트를 선택하고 가사를 한 음절씩 배정
# ACE Studio 가사 입력 방식: 노트 클릭 → 더블클릭 → 텍스트 입력 → Tab으로 다음 노트
ace_vocal_input_lyrics() {
    local lyrics="$1"

    ace_log "가사 입력 시작: ${lyrics:0:20}..."

    # 피아노롤이 열려 있어야 함
    # 첫 번째 노트 선택: Home 키로 처음으로 이동
    ace_key_code 115
    ace_wait 0.5

    # 전체 선택 후 첫 노트부터 입력
    # 한국어/영어 가사를 공백 기준 음절 분리
    IFS=' ' read -ra syllables <<< "$lyrics"

    for syllable in "${syllables[@]}"; do
        # 현재 노트에 가사 입력 (더블클릭으로 편집 모드 진입)
        ace_type_text "$syllable"
        ace_wait 0.2
        # Tab으로 다음 노트 이동
        ace_key_tab
        ace_wait 0.1
    done

    ace_log "가사 입력 완료: ${#syllables[@]}개 음절"
}

# 가사 일괄 입력: 전체 가사를 한 번에 배정 (ACE Studio 가사 편집기 사용)
ace_vocal_bulk_lyrics() {
    local lyrics_text="$1"

    ace_log "가사 일괄 입력"

    # 피아노롤에서 전체 선택
    ace_keystroke_cmd "a"
    ace_wait 0.3

    # 가사를 클립보드에 복사 후 붙여넣기
    echo -n "$lyrics_text" | pbcopy
    ace_keystroke_cmd "v"
    ace_wait 1

    ace_log "가사 일괄 입력 완료"
}

# Singer 목록
ace_vocal_singer_list() {
    cat <<'SINGERS'
[V2 Beta - 사전 제작]
  Elirah    — 영어, r&b, pop, ballad
  Mangus    — 영어, country, raspy
  Ember Rose — 영어, pop, clear, ballad
  Anderson  — 영어, country, raspy
  Drex L    — 영어, pop, r&b, funk
  Golden G  — 영어, hiphop, rap, afr
  Jayden    — 영어, rap, hiphop, trap
  Zinny     — 영어, rap, hiphop, trap
  Rebecca   — 영어, r&b, pop, gospel
  Zalo      — 영어, pop, soul, gos
  Jessica   — 영어, pop, soul
  Emma      — 영어, ballad, pop
  Laolu     — 영어, pop, country
  Lexa      — 영어, jazz, soul
  Oma       — (미확인)

[지원 언어] English, Chinese, Japanese, Korean, Spanish, Italian, French, Portuguese
SINGERS
}
