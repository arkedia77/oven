"""
MuseScore API 다운로더 (브라우저 없이)
- curl_cffi로 Cloudflare 우회
- 페이지 소스에서 h값 추출 → 직접 S3 다운로드
- 브라우저 대비 3-5x 빠름
"""

import os, re, time, random, urllib.parse, json
import browser_cookie3
from curl_cffi import requests as cf_requests
from utils import make_logger, load_done, mark_done, load_daily, save_daily, iter_pending_urls, UA, BASE_DIR

OUT_DIR    = "/Volumes/data/score/musescore"
MXL_DIR    = f"{OUT_DIR}/musicxml"
LOG_FILE   = f"{BASE_DIR}/logs/download_api.log"
DONE_FILE  = f"{BASE_DIR}/data/done_ids.txt"
DAILY_FILE = f"{BASE_DIR}/data/daily_download_api.json"
COOKIE_FILE = os.path.expanduser("~/musicscore/chrome_profile/Default/Cookies")

DAILY_LIMIT = 200
OFFICIAL_ONLY = True  # official 악보만 다운로드
DELAY       = (2, 5)

log = make_logger(LOG_FILE)


def make_session():
    cookies = browser_cookie3.chrome(cookie_file=COOKIE_FILE, domain_name='.musescore.com')
    jar = {c.name: c.value for c in cookies}
    session = cf_requests.Session(impersonate="chrome110")
    for k, v in jar.items():
        session.cookies.set(k, v, domain='.musescore.com')
    return session


def is_official_score(html_text):
    """페이지에서 official 배지 확인"""
    # MuseScore official 악보: "Official" 배지, 공식 출판사 표시
    if 'class="official"' in html_text or '"isOfficial":true' in html_text:
        return True
    if '"official_score"' in html_text or 'Official Score' in html_text:
        return True
    return False


def download_score(session, score_url, score_id):
    try:
        # 1. 페이지 로드 → h값 추출
        resp = session.get(score_url, headers={"User-Agent": UA}, timeout=15)
        decoded = urllib.parse.unquote(resp.text.replace('&amp;', '&').replace('&quot;', '"'))

        # official 필터
        if OFFICIAL_ONLY and not is_official_score(resp.text):
            return False, "non-official (스킵)"

        m = re.search(rf'score_id={score_id}&type=mxl&h=(\d+)', decoded)
        if not m:
            return False, "h값 없음"

        h = m.group(1)
        dl_url = f"https://musescore.com/score/download/index?score_id={score_id}&type=mxl&h={h}"

        # 2. 다운로드 요청
        r = session.get(dl_url, headers={
            "User-Agent": UA,
            "Referer": score_url,
        }, allow_redirects=True, timeout=30)

        # 3. 실제 파일인지 확인
        if r.content[:2] == b'PK' or b'<?xml' in r.content[:20]:
            dst = os.path.join(MXL_DIR, f"{score_id}.mxl")
            with open(dst, 'wb') as f:
                f.write(r.content)
            return True, f"{len(r.content)//1024}KB"

        # forbidden 체크
        if 'forbidden' in r.url:
            return False, "한도초과"

        return False, f"미확인응답({len(r.content)}bytes)"

    except Exception as e:
        return False, f"오류: {e}"


def main():
    os.makedirs(MXL_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    done_ids    = load_done(DONE_FILE)
    daily_count = load_daily(DAILY_FILE)

    if daily_count >= DAILY_LIMIT:
        log(f"오늘 한도 {DAILY_LIMIT}개 달성. 내일 재실행.")
        return

    log(f"오늘 {daily_count}/{DAILY_LIMIT}")

    session = make_session()
    log("세션 준비 완료 (브라우저 없음)")

    consecutive_fail = 0

    for i, item in enumerate(iter_pending_urls(BASE_DIR + "/data/urls.jsonl", done_ids)):
        if daily_count >= DAILY_LIMIT:
            log(f"오늘 한도 도달. 중단.")
            break

        score_id  = item["id"]
        score_url = item["url"]
        title     = item.get("title", "")[:40]
        log(f"[{i+1}] {title}")

        ok, msg = download_score(session, score_url, score_id)

        if ok:
            log(f"  ✅ {score_id}.mxl ({msg})")
            consecutive_fail = 0
            # 메타데이터 저장
            with open(f"{OUT_DIR}/{score_id}_meta.json", "w") as f:
                json.dump(item, f, ensure_ascii=False)
            mark_done(DONE_FILE, score_id)
            done_ids.add(score_id)
            daily_count += 1
            save_daily(DAILY_FILE, daily_count)
        else:
            if msg == "non-official (스킵)":
                # official 아닌 건 스킵 (한도 소비 X, 실패 카운트 X)
                mark_done(DONE_FILE, score_id)
                done_ids.add(score_id)
                continue
            log(f"  ❌ {msg}")
            consecutive_fail += 1
            if msg == "한도초과":
                log("서버 한도 초과. 오늘 중단.")
                break
            if consecutive_fail >= 5:
                log("연속 5회 실패. 중단.")
                break

        time.sleep(random.uniform(*DELAY))

    log(f"완료: 오늘 {daily_count}개 | 누적 {len(done_ids)}개")


main()
