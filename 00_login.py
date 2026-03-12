"""
MuseScore 전용 Chrome 프로필로 로그인
- 최초 1회만 실행 필요
- 로그인 후 세션이 ~/musicscore/chrome_profile에 영구 저장
- 이후 01, 02 스크립트가 같은 프로필 재사용 → 자동 로그인
"""
import time
import undetected_chromedriver as uc

PROFILE_DIR = "/Users/leo/musicscore/chrome_profile"

def main():
    driver = uc.Chrome(
        headless=False,
        version_main=145,
        user_data_dir=PROFILE_DIR,
    )

    driver.get("https://musescore.com/user/login")
    print("\n>>> musescore.com에서 로그인 해주세요.")
    print(">>> 로그인 완료 후 Enter 키 누르세요.")
    input()

    logged_in = driver.execute_script("""
        return document.querySelector('[href*="logout"]') !== null
            || document.querySelector('[class*="avatar"]') !== null
            || document.querySelector('[class*="userMenu"]') !== null
            || document.querySelector('[class*="user-menu"]') !== null
            || !document.querySelector('[href*="/user/login"]');
    """)
    print(f"로그인 상태: {'✅ 성공' if logged_in else '❌ 실패 — 다시 시도'}")

    driver.quit()
    print(f"세션 저장 완료: {PROFILE_DIR}")
    print("이제 01_collect_urls.py, 02_download.py 자동 실행됩니다.")

main()
