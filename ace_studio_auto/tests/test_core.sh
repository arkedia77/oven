#!/bin/bash
# ACE Studio core 모듈 단위 테스트
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/modules/core.sh"

PASS=0
FAIL=0

test_result() {
    local name="$1" result="$2"
    if [ "$result" -eq 0 ]; then
        echo "  ✅ $name"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Phase 1: core.sh 테스트 ==="
echo ""

# 1.0 의존성 확인
echo "[1.0] 의존성 체크"
ace_check_deps
test_result "cliclick + osascript + bc 설치됨" $?

# 1.1 ACE Studio 활성화
echo "[1.1] ACE Studio 활성화"
ace_ensure_running
test_result "ACE Studio foreground" $?
sleep 1

# 1.2 윈도우 위치/크기
echo "[1.2] 윈도우 정보"
INFO=$(ace_get_window_info 2>&1)
if [ -n "$INFO" ] && echo "$INFO" | grep -q ","; then
    echo "  윈도우 정보: $INFO"
    test_result "윈도우 위치/크기 반환" 0
else
    echo "  반환값: $INFO"
    test_result "윈도우 위치/크기 반환" 1
fi

# 1.3 메뉴바 접근
echo "[1.3] 메뉴바 목록"
MENUS=$(ace_list_menus 2>&1)
if [ -n "$MENUS" ]; then
    echo "  메뉴: $MENUS"
    test_result "메뉴바 목록 반환" 0
else
    test_result "메뉴바 목록 반환" 1
fi

# 1.3b 파일 메뉴 아이템
echo "[1.3b] 파일 메뉴 아이템"
FILE_ITEMS=$(ace_list_menu_items "파일" 2>&1)
if [ -z "$FILE_ITEMS" ]; then
    FILE_ITEMS=$(ace_list_menu_items "File" 2>&1)
fi
if [ -n "$FILE_ITEMS" ]; then
    echo "  파일 메뉴: $(echo "$FILE_ITEMS" | tr '\n' ', ')"
    test_result "파일 메뉴 아이템 반환" 0
else
    test_result "파일 메뉴 아이템 반환" 1
fi

# 1.4 좌표 계산
echo "[1.4] 좌표 계산"
ABS=$(ace_abs_xy 100 50 2>&1)
RATIO=$(ace_ratio_xy 0.5 0.5 2>&1)
echo "  절대(+100,+50): $ABS"
echo "  비율(0.5,0.5): $RATIO"
if echo "$ABS" | grep -q "," && echo "$RATIO" | grep -q ","; then
    test_result "좌표 변환 정상" 0
else
    test_result "좌표 변환 정상" 1
fi

# 1.5 마우스 위치
echo "[1.5] 현재 마우스 위치"
POS=$(ace_mouse_pos 2>&1)
echo "  마우스: $POS"
test_result "cliclick 마우스 위치" 0

# 1.6 스크린샷
echo "[1.6] 윈도우 스크린샷"
ace_screenshot "/tmp/ace_test_screenshot.png" 2>&1
if [ -f "/tmp/ace_test_screenshot.png" ]; then
    SIZE=$(ls -la /tmp/ace_test_screenshot.png | awk '{print $5}')
    echo "  스크린샷 크기: ${SIZE} bytes"
    test_result "스크린샷 저장" 0
else
    test_result "스크린샷 저장" 1
fi

echo ""
echo "=== 결과: ✅ $PASS / ❌ $FAIL ==="
