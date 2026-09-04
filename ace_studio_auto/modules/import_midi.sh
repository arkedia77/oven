#!/bin/bash
# ACE Studio GUI 자동화 — MIDI/오디오 가져오기 모듈 (검증됨 2026-04-26)
# 사용법: source modules/core.sh && source modules/import_midi.sh
#
# 검증된 워크플로우:
#   1. 캔버스 우클릭 → 컨텍스트 메뉴
#   2. "가져오기" hover → 서브메뉴 열림
#   3. "MIDI" 클릭 → macOS 파일 다이얼로그
#   4. 파일 더블클릭 → MIDI 트랙 생성

ace_import_midi() {
    local midi_path="$1"
    local filename=$(basename "$midi_path")

    if [ ! -f "$midi_path" ]; then
        ace_log "ERROR: MIDI 파일을 찾을 수 없습니다: $midi_path"
        return 1
    fi

    ace_log "MIDI 가져오기 시작: $filename"

    cp "$midi_path" "$WORKING_DOC/" 2>/dev/null
    ace_log "파일 복사 완료 → $WORKING_DOC/$filename"

    ace_ensure_running

    # 메뉴바 → 파일 → 가져오기 → MIDI 파일 (우선)
    # 실패 시 컨텍스트 메뉴 방식 fallback
    if ace_import_midi_via_menu; then
        ace_wait 1.5
        ace_import_select_file_via_clipboard "$WORKING_DOC/$filename"
    else
        ace_import_midi_via_context_menu
        ace_wait 1.5
        ace_import_select_file_in_dialog "$filename"
    fi

    ace_log "MIDI 가져오기 완료: $filename"
}

ace_import_midi_via_menu() {
    ace_log "메뉴: 파일 → 가져오기 → MIDI 파일"
    osascript -e '
tell application "System Events"
    tell process "ACE Studio"
        click menu item "MIDI 파일" of menu 1 of menu item "가져오기" of menu 1 of menu bar item "파일" of menu bar 1
    end tell
end tell
' 2>/dev/null
    local rc=$?
    ace_wait 2
    return $rc
}

ace_import_select_file_via_clipboard() {
    local filepath="$1"
    local dirpath=$(dirname "$filepath")

    ace_log "파일 선택 (클립보드 방식): $filepath"

    echo -n "$dirpath" | pbcopy
    osascript <<'ENDSCRIPT'
tell application "System Events"
    keystroke "g" using {command down, shift down}
    delay 1.5
    keystroke "a" using command down
    delay 0.2
    key code 51
    delay 0.3
    keystroke "v" using command down
    delay 1
    key code 36
    delay 3
end tell
ENDSCRIPT

    # 파일 선택 → 열기
    local filename=$(basename "$filepath")
    ace_wait 1

    osascript -e "
tell application \"System Events\"
    tell process \"ACE Studio\"
        tell window 1
            set elems to entire contents
            repeat with e in elems
                try
                    if class of e is text field then
                        if value of e is \"$filename\" then
                            click e
                            exit repeat
                        end if
                    end if
                end try
            end repeat
        end tell
    end tell
end tell
" 2>/dev/null
    ace_wait 0.5

    # 열기 버튼 클릭
    osascript -e '
tell application "System Events"
    tell process "ACE Studio"
        tell window 1
            set elems to entire contents
            repeat with e in elems
                try
                    if class of e is button and name of e is "열기" then
                        click e
                        exit repeat
                    end if
                end try
            end repeat
        end tell
    end tell
end tell
' 2>/dev/null
    ace_wait 3
    ace_log "파일 선택 완료: $filename"
}

ace_import_midi_via_context_menu() {
    ace_log "메뉴: 우클릭 → 가져오기 → MIDI"

    local info
    info=$(ace_get_window_info)
    local wx=$(echo "$info" | cut -d',' -f1)
    local wy=$(echo "$info" | cut -d',' -f2)
    local ww=$(echo "$info" | cut -d',' -f3)
    local wh=$(echo "$info" | cut -d',' -f4)

    # 캔버스 중앙에서 우클릭
    local cx=$((wx + ww / 4))
    local cy=$((wy + wh / 3))

    ace_ctx_open "$cx" "$cy"

    # "가져오기" hover (dy=117) → 서브메뉴 → "MIDI" 클릭
    # MIDI는 서브메뉴 두 번째 항목 (오디오=1st, MIDI=2nd)
    # 서브메뉴 아이템 간격 ≈ 30px
    local import_dy=$CTX_DY_IMPORT
    local midi_dy=$((import_dy + 30))
    ace_ctx_click_submenu_item "$import_dy" "$midi_dy"

    ace_wait 1.5
    ace_log "MIDI 가져오기 다이얼로그 열림"
}

ace_import_select_file_in_dialog() {
    local filename="$1"

    # Cmd+Shift+G → 경로 직접 입력 → 파일 열기
    ace_dialog_goto_folder "$WORKING_DOC/$filename"
    ace_wait 0.5
    ace_key_return
    ace_wait 2

    ace_log "파일 선택 완료: $filename"
}

ace_import_musicxml() {
    local xml_path="$1"
    local filename=$(basename "$xml_path")

    if [ ! -f "$xml_path" ]; then
        ace_log "ERROR: MusicXML 파일을 찾을 수 없습니다: $xml_path"
        return 1
    fi

    ace_log "MusicXML 가져오기 시작: $filename"
    cp "$xml_path" "$WORKING_DOC/"
    ace_ensure_running

    local info
    info=$(ace_get_window_info)
    local cx=$(( $(echo "$info" | cut -d',' -f1) + $(echo "$info" | cut -d',' -f3) / 4 ))
    local cy=$(( $(echo "$info" | cut -d',' -f2) + $(echo "$info" | cut -d',' -f4) / 3 ))

    ace_ctx_open "$cx" "$cy"

    # MusicXML은 서브메뉴 세 번째 항목
    local import_dy=$CTX_DY_IMPORT
    local musicxml_dy=$((import_dy + 60))
    ace_ctx_click_submenu_item "$import_dy" "$musicxml_dy"

    ace_wait 1.5
    ace_import_select_file_in_dialog "$filename"
    ace_log "MusicXML 가져오기 완료: $filename"
}

ace_import_audio() {
    local audio_path="$1"
    local filename=$(basename "$audio_path")

    if [ ! -f "$audio_path" ]; then
        ace_log "ERROR: 오디오 파일을 찾을 수 없습니다: $audio_path"
        return 1
    fi

    ace_log "오디오 가져오기 시작: $filename"
    cp "$audio_path" "$WORKING_DOC/"
    ace_ensure_running

    local info
    info=$(ace_get_window_info)
    local cx=$(( $(echo "$info" | cut -d',' -f1) + $(echo "$info" | cut -d',' -f3) / 4 ))
    local cy=$(( $(echo "$info" | cut -d',' -f2) + $(echo "$info" | cut -d',' -f4) / 3 ))

    ace_ctx_open "$cx" "$cy"

    # 오디오는 서브메뉴 첫 번째 항목
    local import_dy=$CTX_DY_IMPORT
    ace_ctx_click_submenu_item "$import_dy" "$import_dy"

    ace_wait 1.5
    ace_import_select_file_in_dialog "$filename"
    ace_log "오디오 가져오기 완료: $filename"
}

ace_import_cleanup() {
    ace_log "working_document 정리 중..."
    rm -f "$WORKING_DOC"/*.mid "$WORKING_DOC"/*.midi "$WORKING_DOC"/*.musicxml "$WORKING_DOC"/*.mxl
    ace_log "정리 완료"
}
