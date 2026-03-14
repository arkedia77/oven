"""
Cloudflare 쿠키 자동 갱신 스크립트
- undetected_chromedriver로 musescore.com 접속
- __cf_bm + cf_clearance 갱신
- 갱신 실패 시 최대 2회 재시도
- headless로 실행 (화면 없음)
"""
import time, sys
import browser_cookie3
from datetime import datetime
import undetected_chromedriver as uc

PROFILE_DIR = "/Users/leo/musicscore/chrome_profile"
COOKIE_FILE = f"{PROFILE_DIR}/Default/Cookies"
MAX_RETRIES = 2


def check_cookies():
    """__cf_bm과 cf_clearance 상태 반환"""
    cookies = browser_cookie3.chrome(cookie_file=COOKIE_FILE, domain_name='.musescore.com')
    result = {}
    for c in cookies:
        if c.name in ('__cf_bm', 'cf_clearance') and c.expires:
            exp = datetime.fromtimestamp(c.expires)
            remaining = (exp - datetime.now()).total_seconds() / 60
            result[c.name] = (exp, remaining)
    return result


def print_status(label, cookies):
    for name in ('__cf_bm', 'cf_clearance'):
        if name in cookies:
            exp, rem = cookies[name]
            status = "유효" if rem > 0 else "만료됨"
            print(f"  {label} {name}: {status} (만료: {exp.strftime('%m/%d %H:%M')}, {rem:.0f}분)")
        else:
            print(f"  {label} {name}: 없음")


def refresh_once():
    """Chrome으로 쿠키 갱신 1회 시도. 성공 여부 반환."""
    print("Chrome 시작 중...")
    driver = uc.Chrome(
        headless=True,
        version_main=145,
        user_data_dir=PROFILE_DIR,
    )

    try:
        driver.get("https://musescore.com/sheetmusic")
        print("  페이지 로드 대기 (5초)...")
        time.sleep(5)

        driver.get("https://musescore.com/official_scores")
        print("  official_scores 방문 (3초)...")
        time.sleep(3)

        # 악보 상세 페이지도 방문 (cf_clearance 갱신 확실히)
        driver.get("https://musescore.com/user/39593079/scores/6967147")
        print("  악보 상세 방문 (3초)...")
        time.sleep(3)
    finally:
        driver.quit()
        print("Chrome 종료 완료")

    time.sleep(1)
    after = check_cookies()
    cf_bm_ok = '__cf_bm' in after and after['__cf_bm'][1] > 0
    cf_clear_ok = 'cf_clearance' in after and after['cf_clearance'][1] > 0
    return cf_bm_ok and cf_clear_ok, after


def main():
    before = check_cookies()
    print("갱신 전:")
    print_status("  ", before)

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n시도 {attempt}/{MAX_RETRIES}")
        success, after = refresh_once()

        print(f"\n갱신 후:")
        print_status("  ", after)

        if success:
            print("\n✅ 쿠키 갱신 성공 (__cf_bm + cf_clearance)")
            return 0

        print(f"\n⚠️ 일부 쿠키 갱신 실패")
        if attempt < MAX_RETRIES:
            print("  5초 후 재시도...")
            time.sleep(5)

    print("\n❌ 최대 재시도 횟수 초과. 수동 갱신 필요.")
    return 1


sys.exit(main())
