#!/bin/bash
# ACE Studio GUI 자동화 — 배치 오케스트레이터 (업데이트 2026-04-26)
# 사용법: source modules/core.sh && source modules/*.sh && source modules/batch.sh
#
# 검증된 모듈 함수들을 조합하여 배치 렌더링 수행
# 주의: ACE Studio가 foreground 필수, 마우스/키보드 사용 불가

# 단일 MIDI → 여러 악기로 배치 렌더링
ace_batch_instruments() {
    local midi_path="$1"
    local output_dir="$2"
    shift 2
    local instruments=("$@")

    if [ ${#instruments[@]} -eq 0 ]; then
        ace_log "ERROR: 악기를 하나 이상 지정해주세요"
        return 1
    fi

    local midi_name=$(basename "$midi_path" .mid)
    mkdir -p "$output_dir"

    ace_log "=== 배치 시작: $midi_name → ${#instruments[@]}개 악기 ==="

    for instrument in "${instruments[@]}"; do
        ace_log "--- [$instrument] 렌더링 시작 ---"

        ace_project_new
        ace_wait 3
        ace_dismiss_record_dialog
        ace_wait 1
        ace_import_midi "$midi_path"
        ace_wait 3
        ace_instrument_assign "$instrument"
        ace_wait 3
        ace_export_audio "${midi_name}_$(echo "$instrument" | tr ' ' '_')"
        ace_wait 2

        ace_export_retrieve "${midi_name}_$(echo "$instrument" | tr ' ' '_').wav" "$output_dir"

        ace_log "--- [$instrument] 완료 ---"
    done

    ace_log "=== 배치 완료: ${#instruments[@]}개 파일 ==="
    ls -la "$output_dir"/${midi_name}_*.wav 2>/dev/null
}

# "무엇을 녹음하시겠습니까?" 다이얼로그 닫기
ace_dismiss_record_dialog() {
    osascript -e '
tell application "System Events"
    tell process "ACE Studio"
        try
            if exists window "녹음 옵션" then
                -- "없음" 선택하여 닫기
                set p to position of window "녹음 옵션"
                set s to size of window "녹음 옵션"
                -- "없음" 버튼: 왼쪽 1/3 영역, 하단 40%
                set bx to (item 1 of p) + ((item 1 of s) / 6)
                set by to (item 2 of p) + ((item 2 of s) * 3 / 4)
                click at {bx, by}
            end if
        end try
    end tell
end tell
' 2>/dev/null
    ace_wait 1
}

# 여러 MIDI → 단일 악기로 배치 렌더링
ace_batch_midis() {
    local output_dir="$1"
    local instrument="$2"
    shift 2
    local midi_files=("$@")

    if [ ${#midi_files[@]} -eq 0 ]; then
        ace_log "ERROR: MIDI 파일을 하나 이상 지정해주세요"
        return 1
    fi

    mkdir -p "$output_dir"

    ace_log "=== 배치 시작: ${#midi_files[@]}개 MIDI → $instrument ==="

    for midi_path in "${midi_files[@]}"; do
        local midi_name=$(basename "$midi_path" .mid)
        ace_log "--- [$midi_name] ---"

        ace_project_new
        ace_wait 2
        ace_import_midi "$midi_path"
        ace_wait 3
        ace_instrument_assign "$instrument"
        ace_wait 3
        local safe_inst=$(echo "$instrument" | tr ' ' '_')
        ace_export_audio "${midi_name}_${safe_inst}"
        ace_wait 2
        ace_export_retrieve "${midi_name}_${safe_inst}.wav" "$output_dir"
    done

    ace_log "=== 배치 완료 ==="
}

# 풀 매트릭스: N MIDI × M 악기
ace_batch_matrix() {
    local output_dir="$1"
    local midi_list="$2"
    local instrument_list="$3"

    IFS=',' read -ra midis <<< "$midi_list"
    IFS=',' read -ra instruments <<< "$instrument_list"

    local total=$((${#midis[@]} * ${#instruments[@]}))
    local count=0

    ace_log "=== 매트릭스: ${#midis[@]} MIDI × ${#instruments[@]} 악기 = ${total}개 ==="
    mkdir -p "$output_dir"

    for midi_path in "${midis[@]}"; do
        for instrument in "${instruments[@]}"; do
            count=$((count + 1))
            local midi_name=$(basename "$midi_path" .mid)
            local safe_inst=$(echo "$instrument" | tr ' ' '_')
            ace_log "[$count/$total] $midi_name + $instrument"

            ace_project_new
            ace_wait 2
            ace_import_midi "$midi_path"
            ace_wait 3
            ace_instrument_assign "$instrument"
            ace_wait 3
            ace_export_audio "${midi_name}_${safe_inst}"
            ace_wait 2
            ace_export_retrieve "${midi_name}_${safe_inst}.wav" "$output_dir"
        done
    done

    ace_log "=== 매트릭스 완료: $count/$total ==="
}

ace_batch_status() {
    local output_dir="$1"
    local wav_count=$(ls "$output_dir"/*.wav 2>/dev/null | wc -l)
    ace_log "생성된 WAV: ${wav_count}개 ($output_dir)"
}
