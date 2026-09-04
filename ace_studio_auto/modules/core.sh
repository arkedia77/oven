#!/bin/bash
# ACE Studio GUI 자동화 — 공통 유틸리티
# 사용법: source modules/core.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKING_DOC="$HOME/ACE_Studio/project/temp_workspace/working_document"
ACE_APP="ACE Studio"
ACE_PROCESS="ACE Studio"

# --- 앱 제어 ---

ace_launch() {
    open -a "$ACE_APP"
    sleep 3
    ace_activate
}

ace_activate() {
    osascript -e "tell application \"$ACE_APP\" to activate"
    sleep 0.5
}

ace_is_running() {
    pgrep -f "$ACE_APP" > /dev/null 2>&1
}

ace_ensure_running() {
    if ! ace_is_running; then
        echo "[core] ACE Studio가 실행 중이 아닙니다. 실행합니다..."
        ace_launch
        ace_wait_for_window 30
    else
        ace_activate
    fi
}

# --- 윈도우 정보 ---

ace_get_window_info() {
    osascript <<'EOF'
tell application "System Events"
    tell process "ACE Studio"
        set winPos to position of window 1
        set winSize to size of window 1
        return (item 1 of winPos as text) & "," & (item 2 of winPos as text) & "," & (item 1 of winSize as text) & "," & (item 2 of winSize as text)
    end tell
end tell
EOF
}

ace_get_window_pos() {
    local info
    info=$(ace_get_window_info)
    echo "$info" | cut -d',' -f1-2
}

ace_get_window_size() {
    local info
    info=$(ace_get_window_info)
    echo "$info" | cut -d',' -f3-4
}

ace_window_x() { ace_get_window_info | cut -d',' -f1; }
ace_window_y() { ace_get_window_info | cut -d',' -f2; }
ace_window_w() { ace_get_window_info | cut -d',' -f3; }
ace_window_h() { ace_get_window_info | cut -d',' -f4; }

ace_wait_for_window() {
    local timeout=${1:-20}
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if ace_get_window_info > /dev/null 2>&1; then
            echo "[core] 윈도우 감지됨"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    echo "[core] 타임아웃: 윈도우를 찾지 못했습니다" >&2
    return 1
}

# --- 좌표 계산 ---
# 윈도우 내 상대 좌표를 절대 좌표로 변환

ace_abs_xy() {
    local rel_x=$1 rel_y=$2
    local info
    info=$(ace_get_window_info)
    local wx=$(echo "$info" | cut -d',' -f1)
    local wy=$(echo "$info" | cut -d',' -f2)
    echo "$((wx + rel_x)),$((wy + rel_y))"
}

# 윈도우 크기 대비 비율로 좌표 계산 (해상도 독립)
ace_ratio_xy() {
    local ratio_x=$1 ratio_y=$2
    local info
    info=$(ace_get_window_info)
    local wx=$(echo "$info" | cut -d',' -f1)
    local wy=$(echo "$info" | cut -d',' -f2)
    local ww=$(echo "$info" | cut -d',' -f3)
    local wh=$(echo "$info" | cut -d',' -f4)
    local ax=$(echo "$wx + $ww * $ratio_x" | bc | cut -d'.' -f1)
    local ay=$(echo "$wy + $wh * $ratio_y" | bc | cut -d'.' -f1)
    echo "${ax},${ay}"
}

# --- cliclick 래퍼 ---

ace_click() {
    local x=$1 y=$2
    cliclick "c:${x},${y}"
    sleep 0.3
}

ace_double_click() {
    local x=$1 y=$2
    cliclick "dc:${x},${y}"
    sleep 0.3
}

ace_right_click() {
    local x=$1 y=$2
    cliclick "rc:${x},${y}"
    sleep 0.3
}

ace_click_abs() {
    local rel_x=$1 rel_y=$2
    local coords
    coords=$(ace_abs_xy "$rel_x" "$rel_y")
    local x=$(echo "$coords" | cut -d',' -f1)
    local y=$(echo "$coords" | cut -d',' -f2)
    ace_click "$x" "$y"
}

ace_click_ratio() {
    local ratio_x=$1 ratio_y=$2
    local coords
    coords=$(ace_ratio_xy "$ratio_x" "$ratio_y")
    local x=$(echo "$coords" | cut -d',' -f1)
    local y=$(echo "$coords" | cut -d',' -f2)
    ace_click "$x" "$y"
}

# --- 키보드 ---

ace_keystroke() {
    local key="$1"
    osascript -e "tell application \"System Events\" to keystroke \"$key\""
    sleep 0.2
}

ace_keystroke_cmd() {
    local key="$1"
    osascript -e "tell application \"System Events\" to keystroke \"$key\" using command down"
    sleep 0.3
}

ace_keystroke_cmd_shift() {
    local key="$1"
    osascript -e "tell application \"System Events\" to keystroke \"$key\" using {command down, shift down}"
    sleep 0.3
}

ace_key_code() {
    local code="$1"
    osascript -e "tell application \"System Events\" to key code $code"
    sleep 0.2
}

ace_key_return() { ace_key_code 36; }
ace_key_escape() { ace_key_code 53; }
ace_key_tab() { ace_key_code 48; }
ace_key_space() { ace_key_code 49; }
ace_key_delete() { ace_key_code 51; }

ace_type_text() {
    local text="$1"
    osascript -e "tell application \"System Events\" to keystroke \"$text\""
    sleep 0.3
}

# --- 컨텍스트 메뉴 (Qt 렌더링 — macOS 네이티브 메뉴 아님) ---
# ACE Studio는 파일/편집 메뉴가 앱 내부 Qt 위젯으로 렌더링됨
# 접근 방법: 캔버스에서 우클릭 → cliclick으로 hover/click

# 빈 캔버스 컨텍스트 메뉴 아이템 오프셋 (우클릭 지점 기준)
# 트랙 위에서 우클릭 시 다른 메뉴가 나옴 (클립 편집 메뉴)
CTX_DY_AI_TOOLS=25
CTX_DY_PASTE=55
CTX_DY_SELECT_ALL=85
CTX_DY_IMPORT=117
CTX_DY_LOOP=147
CTX_DY_GRID=177

ace_ctx_open() {
    local x=${1:-750} y=${2:-400}
    ace_log "컨텍스트 메뉴 열기 ($x, $y)"
    cliclick "rc:${x},${y}"
    sleep 0.8
    CTX_X=$x
    CTX_Y=$y
}

ace_ctx_hover_item() {
    local dy=$1
    local target_y=$((CTX_Y + dy))
    cliclick "m:${CTX_X},${target_y}"
    sleep 0.5
}

ace_ctx_click_item() {
    local dy=$1
    local target_y=$((CTX_Y + dy))
    cliclick "c:${CTX_X},${target_y}"
    sleep 0.5
}

ace_ctx_hover_submenu() {
    local dy=$1
    local submenu_x=$((CTX_X + 120))
    local target_y=$((CTX_Y + dy))
    cliclick "m:${CTX_X},${target_y}" "w:800" "m:${submenu_x},${target_y}"
    sleep 0.5
}

ace_ctx_click_submenu_item() {
    local parent_dy=$1
    local item_dy=$2
    local submenu_x=$((CTX_X + 120))
    local item_y=$((CTX_Y + item_dy))
    cliclick "m:${CTX_X},$((CTX_Y + parent_dy))" "w:800" "m:${submenu_x},${item_y}" "w:300" "c:${submenu_x},${item_y}"
    sleep 1
}

# --- 대기 / 타이밍 ---

ace_wait() {
    local seconds=${1:-1}
    sleep "$seconds"
}

ace_wait_for_render() {
    local timeout=${1:-120}
    local check_interval=${2:-3}
    echo "[core] 렌더링 완료 대기 중... (최대 ${timeout}초)"
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        sleep "$check_interval"
        elapsed=$((elapsed + check_interval))
        echo "[core]   ... ${elapsed}초 경과"
    done
    echo "[core] 렌더링 대기 타임아웃 (${timeout}초)"
}

# --- 스크린샷 ---

ace_screenshot() {
    local output=${1:-"/tmp/ace_screenshot.png"}
    local info
    info=$(ace_get_window_info)
    local x=$(echo "$info" | cut -d',' -f1)
    local y=$(echo "$info" | cut -d',' -f2)
    local w=$(echo "$info" | cut -d',' -f3)
    local h=$(echo "$info" | cut -d',' -f4)
    screencapture -R "${x},${y},${w},${h}" "$output"
    echo "[core] 스크린샷 저장: $output"
}

ace_screenshot_region() {
    local rx=$1 ry=$2 rw=$3 rh=$4
    local output=${5:-"/tmp/ace_region.png"}
    local info
    info=$(ace_get_window_info)
    local wx=$(echo "$info" | cut -d',' -f1)
    local wy=$(echo "$info" | cut -d',' -f2)
    screencapture -R "$((wx + rx)),$((wy + ry)),${rw},${rh}" "$output"
    echo "[core] 영역 스크린샷 저장: $output"
}

# --- 파일 다이얼로그 ---

ace_dialog_type_filename() {
    local filename="$1"
    osascript <<ENDSCRIPT
tell application "System Events"
    keystroke "g" using {command down, shift down}
    delay 0.5
    keystroke "$filename"
    delay 0.3
    key code 36
    delay 0.5
end tell
ENDSCRIPT
}

ace_dialog_goto_folder() {
    local folder_path="$1"
    osascript <<ENDSCRIPT
tell application "System Events"
    keystroke "g" using {command down, shift down}
    delay 0.8
    keystroke "$folder_path"
    delay 0.5
    key code 36
    delay 1
end tell
ENDSCRIPT
}

# --- 유틸리티 ---

ace_log() {
    echo "[$(date '+%H:%M:%S')] $*"
}

ace_check_deps() {
    local missing=0
    if ! command -v cliclick &>/dev/null; then
        echo "[core] ERROR: cliclick이 설치되어 있지 않습니다. brew install cliclick" >&2
        missing=1
    fi
    if ! command -v osascript &>/dev/null; then
        echo "[core] ERROR: osascript가 없습니다. macOS가 필요합니다." >&2
        missing=1
    fi
    if ! command -v bc &>/dev/null; then
        echo "[core] ERROR: bc가 없습니다." >&2
        missing=1
    fi
    return $missing
}

ace_mouse_pos() {
    cliclick p
}
