#!/bin/bash
# ACE Studio GUI 자동화 — 오디오/MIDI 내보내기 모듈 (검증됨 2026-04-26)
# 사용법: source modules/core.sh && source modules/export_audio.sh
#
# 검증된 워크플로우:
#   1. 상단 우측 "내보내기" 버튼 클릭 → 내보내기 옵션 다이얼로그 (Qt)
#   2. 옵션 확인/변경 (트랙, 범위, 포맷, 샘플레이트 등)
#   3. "내보내기" 확인 버튼 클릭 → macOS 저장 다이얼로그
#   4. 파일명 입력 → 저장 → WAV 파일 생성
#
# 기본 설정: 마스터 / 전체 프로젝트 / 스테레오 / .WAV / 44100Hz / 16bit

# --- 상수 ---
# "내보내기" 버튼 (상단 우측 바, 윈도우 상대좌표)
EXPORT_BTN_REL_X=2900
EXPORT_BTN_REL_Y=12

# 내보내기 옵션 다이얼로그 (윈도우 중앙에 열림, Qt 렌더링)
# 다이얼로그 상대좌표는 윈도우 크기에 따라 가변 → 비율 기반 사용

# --- 내보내기 흐름 ---

ace_export_open_dialog() {
    ace_log "내보내기 다이얼로그 열기 (상단 내보내기 버튼)"
    ace_ensure_running

    local info
    info=$(ace_get_window_info)
    local wy=$(echo "$info" | cut -d',' -f2)

    cliclick "c:${EXPORT_BTN_REL_X},$((wy + EXPORT_BTN_REL_Y))"
    ace_wait 1.5
    ace_log "내보내기 옵션 다이얼로그 열림"
}

ace_export_confirm() {
    ace_log "내보내기 확인 버튼 클릭"

    local info
    info=$(ace_get_window_info)
    local wx=$(echo "$info" | cut -d',' -f1)
    local wy=$(echo "$info" | cut -d',' -f2)
    local ww=$(echo "$info" | cut -d',' -f3)
    local wh=$(echo "$info" | cut -d',' -f4)

    # "내보내기" 확인 버튼: 다이얼로그 우하단
    # 검증된 좌표 (3008x1572 윈도우 기준): x≈1630, y≈1045 (절대)
    local btn_x=$((wx + ww * 54 / 100))
    local btn_y=$((wy + wh * 65 / 100))

    cliclick "c:${btn_x},${btn_y}"
    ace_wait 2
    ace_log "macOS 저장 다이얼로그로 이동"
}

ace_export_save_dialog() {
    local filename="${1:-export}"

    ace_log "저장 다이얼로그: 파일명 = $filename"

    # 파일명 필드가 자동 선택됨 → 바로 입력
    ace_keystroke_cmd "a"
    ace_wait 0.2
    ace_type_text "$filename"
    ace_wait 0.3

    # Return으로 저장
    ace_key_return
    ace_wait 3
    ace_log "저장 완료 대기 중..."
}

# 전체 파이프라인: 내보내기 → 저장
ace_export_audio() {
    local output_name="${1:-export}"
    local format="${2:-wav}"

    ace_log "=== 오디오 내보내기: $output_name.$format ==="

    ace_export_open_dialog

    # TODO: 포맷 변경이 필요한 경우 드롭다운 클릭
    if [ "$format" = "mp3" ]; then
        ace_export_set_format "mp3"
    fi

    ace_export_confirm
    ace_export_save_dialog "$output_name"

    # 파일 생성 확인
    ace_export_verify "$output_name" "$format"
    ace_log "=== 내보내기 완료 ==="
}

ace_export_verify() {
    local filename="$1"
    local format="${2:-wav}"
    local timeout=${3:-30}
    local filepath="$WORKING_DOC/${filename}.${format}"

    ace_log "파일 확인: $filepath"
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if [ -f "$filepath" ]; then
            local size=$(stat -f%z "$filepath" 2>/dev/null || echo 0)
            if [ "$size" -gt 1000 ]; then
                ace_log "내보내기 성공: $(du -h "$filepath" | cut -f1) ($size bytes)"
                return 0
            fi
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    ace_log "ERROR: 내보내기 파일을 찾을 수 없습니다: $filepath"
    return 1
}

# --- 옵션 변경 ---

ace_export_set_format() {
    local format="$1"
    ace_log "내보내기 포맷 변경: $format"

    local info
    info=$(ace_get_window_info)
    local wx=$(echo "$info" | cut -d',' -f1)
    local wy=$(echo "$info" | cut -d',' -f2)
    local ww=$(echo "$info" | cut -d',' -f3)
    local wh=$(echo "$info" | cut -d',' -f4)

    # 형식 드롭다운: 다이얼로그 중앙, 윈도우 상단에서 ~54% (검증: 3008x1572 → y≈875)
    local dd_x=$((wx + ww * 48 / 100))
    local dd_y=$((wy + wh * 54 / 100))

    cliclick "c:${dd_x},${dd_y}"
    ace_wait 1

    if [ "$format" = "mp3" ] || [ "$format" = "MP3" ] || [ "$format" = ".MP3" ]; then
        # .MP3 항목: 드롭다운 열린 뒤 .WAV 아래 ~30px
        cliclick "c:${dd_x},$((dd_y + 75))"
    else
        # .WAV 항목 (기본값): 드롭다운 첫 번째
        cliclick "c:${dd_x},$((dd_y + 45))"
    fi
    ace_wait 0.5
    ace_log "포맷 변경 완료: $format"
}

ace_export_set_track() {
    local track="$1"
    ace_log "렌더링 트랙 변경: $track"
    # "렌더링된 트랙" 드롭다운: 마스터 / 개별 트랙명
    # TODO: 드롭다운 좌표
    ace_log "TODO: 트랙 드롭다운 UI 구현 필요"
}

ace_export_set_sample_rate() {
    local rate="$1"
    ace_log "샘플레이트 변경: $rate Hz"
    # "샘플레이트" 드롭다운: 44100 / 48000 / 96000
    # TODO: 드롭다운 좌표
    ace_log "TODO: 샘플레이트 드롭다운 UI 구현 필요"
}

ace_export_set_bit_depth() {
    local bits="$1"
    ace_log "비트 깊이 변경: $bits bit"
    # "비트 길이" 드롭다운: 16 / 24 / 32
    # TODO: 드롭다운 좌표
    ace_log "TODO: 비트 깊이 드롭다운 UI 구현 필요"
}

# --- MIDI 내보내기 ---

ace_export_midi() {
    local output_name="${1:-export}"
    ace_log "MIDI 내보내기: $output_name.mid"
    ace_ensure_running

    # 파일 → MIDI 내보내기 (macOS 네이티브 메뉴)
    osascript -e '
tell application "System Events"
    tell process "ACE Studio"
        click menu item "MIDI 내보내기" of menu 1 of menu bar item "파일" of menu bar 1
    end tell
end tell
'
    ace_wait 2

    # MIDI 내보내기 다이얼로그 → "내보내기" 버튼 클릭
    local info
    info=$(ace_get_window_info)
    local wx=$(echo "$info" | cut -d',' -f1)
    local wy=$(echo "$info" | cut -d',' -f2)
    local ww=$(echo "$info" | cut -d',' -f3)
    local wh=$(echo "$info" | cut -d',' -f4)

    local btn_x=$((wx + ww * 54 / 100))
    local btn_y=$((wy + wh * 64 / 100))
    cliclick "c:${btn_x},${btn_y}"
    ace_wait 2

    # macOS 저장 다이얼로그
    ace_export_save_dialog "$output_name"

    # 파일 생성 확인
    local filepath="$WORKING_DOC/${output_name}.mid"
    local elapsed=0
    while [ $elapsed -lt 15 ]; do
        if [ -f "$filepath" ]; then
            ace_log "MIDI 내보내기 성공: $(du -h "$filepath" | cut -f1)"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    ace_log "ERROR: MIDI 파일을 찾을 수 없습니다: $filepath"
    return 1
}

# --- 결과 파일 회수 ---

ace_export_retrieve() {
    local source_name="$1"
    local dest_dir="$2"

    if [ -z "$source_name" ] || [ -z "$dest_dir" ]; then
        ace_log "ERROR: 사용법: ace_export_retrieve <파일명> <목적지>"
        return 1
    fi

    local source_path="$WORKING_DOC/$source_name"
    if [ ! -f "$source_path" ]; then
        ace_log "ERROR: 파일 없음: $source_path"
        return 1
    fi

    mkdir -p "$dest_dir"
    cp "$source_path" "$dest_dir/"
    ace_log "파일 회수: $dest_dir/$source_name"
}
