"""
MuseScore 다운로더 v4
- Download 버튼 → MusicXML 클릭 → 파일 저장
- 전용 Chrome 프로필로 자동 로그인 유지
- 하루 300개 한도
"""

import os, re, time, random, shutil, glob
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from utils import make_logger, load_done, mark_done, load_daily, save_daily, iter_pending_urls, UA, BASE_DIR

import json

PROFILE_DIR  = os.path.expanduser("~/musicscore/chrome_profile")
OUT_DIR      = "/Volumes/data/score/musescore"
DL_TEMP      = f"{BASE_DIR}/downloads"
MXL_DIR      = f"{OUT_DIR}/musicxml"
LOG_FILE     = f"{BASE_DIR}/logs/download.log"
DONE_FILE    = f"{BASE_DIR}/data/done_ids.txt"
DAILY_FILE   = f"{BASE_DIR}/data/daily_download.json"

DAILY_LIMIT  = 150
DELAY        = (5, 10)

log = make_logger(LOG_FILE)

def wait_for_download(timeout=20):
    """DL_TEMP에 완전히 다운로드된 파일 대기"""
    for _ in range(timeout):
        time.sleep(1)
        files = [f for f in glob.glob(f"{DL_TEMP}/*")
                 if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        if files:
            # 가장 최근 파일
            return max(files, key=os.path.getmtime)
    return None

def download_score(driver, score_url, score_id):
    try:
        # 다운로드 전 임시 폴더 비우기
        for f in glob.glob(f"{DL_TEMP}/*"):
            os.remove(f)

        driver.get(score_url)
        time.sleep(random.uniform(3, 5))

        # Download 버튼 클릭 (JS로)
        wait = WebDriverWait(driver, 10)
        dl_btn = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//button[contains(., 'Download')]")
        ))
        driver.execute_script("arguments[0].click();", dl_btn)
        time.sleep(3)

        # 포맷 버튼 찾기 (MusicXML 또는 MIDI)
        clicked = False
        for label in ["MusicXML", "MIDI", "musicxml", "midi"]:
            btns = driver.find_elements(By.XPATH,
                f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label.lower()}')]"
            )
            if btns:
                actions = ActionChains(driver)
                actions.move_to_element(btns[0]).pause(0.3).click().perform()
                log(f"  {label} 선택")
                clicked = True
                break
        if not clicked:
            log(f"  ⚠️ 포맷 버튼 못 찾음")

        # 다운로드 완료 대기
        filepath = wait_for_download(timeout=20)
        if not filepath:
            log(f"  ❌ 타임아웃")
            return False

        # 파일 이동
        ext = os.path.splitext(filepath)[1]
        dst = os.path.join(MXL_DIR, f"{score_id}{ext}")
        shutil.move(filepath, dst)
        log(f"  ✅ 저장: {score_id}{ext} ({os.path.getsize(dst)//1024}KB)")
        return True

    except Exception as e:
        log(f"  ❌ 오류: {e}")
        return False


def main():
    os.makedirs(DL_TEMP, exist_ok=True)
    os.makedirs(MXL_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    done_ids    = load_done(DONE_FILE)
    daily_count = load_daily(DAILY_FILE)

    if daily_count >= DAILY_LIMIT:
        log(f"오늘 한도 {DAILY_LIMIT}개 달성. 내일 재실행.")
        return

    log(f"오늘 {daily_count}/{DAILY_LIMIT} | 브라우저 시작 중...")

    # 다운로드 폴더를 DL_TEMP로 설정
    options = uc.ChromeOptions()
    options.add_experimental_option("prefs", {
        "download.default_directory": DL_TEMP,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    })

    driver = uc.Chrome(
        headless=False,
        version_main=145,
        user_data_dir=PROFILE_DIR,
        options=options,
    )

    driver.get("https://musescore.com")
    time.sleep(4)
    log("브라우저 준비 완료")

    try:
        for i, item in enumerate(iter_pending_urls(BASE_DIR + "/data/urls.jsonl", done_ids)):
            if daily_count >= DAILY_LIMIT:
                log(f"오늘 한도 도달. 중단.")
                break

            score_id  = item["id"]
            score_url = item["url"]
            title     = item.get("title", "")[:40]
            log(f"[{i+1}] {title}")

            ok = download_score(driver, score_url, score_id)

            if ok:
                with open(f"{OUT_DIR}/{score_id}_meta.json", "w") as f:
                    json.dump(item, f, ensure_ascii=False)
                mark_done(DONE_FILE, score_id)
                done_ids.add(score_id)
                daily_count += 1
                save_daily(DAILY_FILE, daily_count)

            time.sleep(random.uniform(*DELAY))

    finally:
        driver.quit()

    log(f"완료: 오늘 {daily_count}개 | 누적 {len(done_ids)}개")


main()
