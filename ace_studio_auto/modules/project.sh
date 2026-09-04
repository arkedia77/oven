#!/bin/bash
# ACE Studio GUI 자동화 — 프로젝트 관리 모듈
# 사용법: source modules/core.sh && source modules/project.sh

# 새 프로젝트 만들기
ace_project_new() {
    ace_log "새 프로젝트 생성"
    ace_ensure_running

    osascript -e '
tell application "System Events"
    tell process "ACE Studio"
        click menu item "새 프로젝트" of menu 1 of menu bar item "파일" of menu bar 1
    end tell
end tell
'
    ace_wait 2

    # "저장하시겠습니까?" 다이얼로그 자동 처리 → "저장하지 않음" 클릭
    osascript -e '
tell application "System Events"
    tell process "ACE Studio"
        try
            click button "저장하지 않음" of window "공지"
        end try
    end tell
end tell
' 2>/dev/null
    ace_wait 2

    ace_log "새 프로젝트 준비 완료"
}

# 프로젝트 저장
ace_project_save() {
    ace_log "프로젝트 저장"
    ace_keystroke_cmd "s"
    ace_wait 1
    ace_log "저장 완료"
}

# 다른 이름으로 저장
ace_project_save_as() {
    local name="$1"
    local dir="${2:-$WORKING_DOC}"

    ace_log "다른 이름으로 저장: $name"
    ace_keystroke_cmd_shift "s"
    ace_wait 1

    if [ -n "$dir" ]; then
        ace_dialog_goto_folder "$dir"
    fi

    ace_keystroke_cmd "a"
    ace_wait 0.2
    ace_type_text "$name"
    ace_key_return
    ace_wait 2

    ace_log "저장 완료: $dir/$name.acep"
}

# 프로젝트 열기
ace_project_open() {
    local project_path="$1"

    ace_log "프로젝트 열기: $project_path"
    ace_ensure_running
    ace_keystroke_cmd "o"
    ace_wait 1

    ace_dialog_goto_folder "$project_path"
    ace_key_return
    ace_wait 3

    ace_log "프로젝트 로드 완료"
}

# 모든 트랙 삭제 (초기화)
ace_project_clear_tracks() {
    ace_log "모든 트랙 삭제"

    # Cmd+A로 전체 선택 → Delete
    ace_keystroke_cmd "a"
    ace_wait 0.3
    ace_key_delete
    ace_wait 0.5

    ace_log "트랙 삭제 완료"
}

# BPM 설정
ace_project_set_bpm() {
    local bpm="$1"
    ace_log "BPM 설정: $bpm"

    # 상단 트랜스포트 바의 BPM 필드를 더블클릭 → 값 입력
    # TODO: BPM 필드 좌표 (테스트 후)
    ace_log "TODO: BPM 필드 좌표 캡처 필요"
}

# 박자 설정
ace_project_set_time_sig() {
    local time_sig="$1"
    ace_log "박자 설정: $time_sig"
    # TODO: 박자 필드 좌표
    ace_log "TODO: 박자 필드 좌표 캡처 필요"
}

# 재생/정지 토글
ace_project_play_stop() {
    ace_key_space
}

# 타임라인 처음으로
ace_project_goto_start() {
    ace_key_return
}

# Undo
ace_project_undo() {
    ace_keystroke_cmd "z"
    ace_wait 0.3
}

# Redo
ace_project_redo() {
    ace_keystroke_cmd_shift "z"
    ace_wait 0.3
}
