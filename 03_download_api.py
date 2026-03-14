"""
MuseScore API 다운로더 (브라우저 없이)
- curl_cffi로 Cloudflare 우회
- 페이지 소스에서 h값 추출 → 직접 S3 다운로드
- 서버 한도 감지 (download_limit=20/일, is_download_limited 체크)
- Downloadable 필드 체크로 불필요한 forbidden 방지
"""

import os, re, time, random, urllib.parse, json
from datetime import datetime
import browser_cookie3
from curl_cffi import requests as cf_requests
from utils import make_logger, load_done, mark_done, load_daily, save_daily, iter_pending_urls, UA, BASE_DIR

OUT_DIR    = "/Volumes/data/score/musescore"
MXL_DIR    = f"{OUT_DIR}/musicxml"
LOG_FILE   = f"{BASE_DIR}/logs/download_api.log"
DONE_FILE  = f"{BASE_DIR}/data/done_ids.txt"
DAILY_FILE = f"{BASE_DIR}/data/daily_download_api.json"
COOKIE_FILE = os.path.expanduser("~/musicscore/chrome_profile/Default/Cookies")

SERVER_LIMIT = 20     # MuseScore Pro 서버 한도 (20/일)
DAILY_LIMIT  = 20     # 로컬 한도 (서버 한도와 맞춤)
OFFICIAL_ONLY = False  # 모든 악보 다운로드 (official 극소수라 전환)
DELAY       = (3, 6)  # 서버 부담 줄이기 위해 간격 넓힘

log = make_logger(LOG_FILE)


def check_cf_cookie():
    """__cf_bm 쿠키 만료 여부 확인. 만료 시 None 반환."""
    cookies = browser_cookie3.chrome(cookie_file=COOKIE_FILE, domain_name='.musescore.com')
    for c in cookies:
        if c.name == '__cf_bm' and c.expires:
            exp = datetime.fromtimestamp(c.expires)
            if exp < datetime.now():
                return None, f"__cf_bm 만료됨 ({exp.strftime('%m/%d %H:%M')})"
            remaining = (exp - datetime.now()).total_seconds() / 60
            return c, f"__cf_bm 유효 (만료까지 {remaining:.0f}분)"
    return None, "__cf_bm 쿠키 없음"


def make_session():
    cookies = browser_cookie3.chrome(cookie_file=COOKIE_FILE, domain_name='.musescore.com')
    jar = {c.name: c.value for c in cookies}
    session = cf_requests.Session(impersonate="chrome110")
    for k, v in jar.items():
        session.cookies.set(k, v, domain='.musescore.com')
    return session


def check_server_limit(session):
    """서버 다운로드 한도 상태 확인. (remaining, reset_msg) 반환."""
    try:
        resp = session.get("https://musescore.com/sheetmusic", headers={"User-Agent": UA}, timeout=15)
        decoded = resp.text.replace('&quot;', '"').replace('&amp;', '&')

        limited = re.search(r'"is_download_limited":(true|false)', decoded)
        count = re.search(r'"download_count":(\d+)', decoded)
        limit = re.search(r'"download_limit":(\d+)', decoded)
        duration = re.search(r'"duration":"([^"]+)"', decoded)

        is_limited = limited.group(1) == "true" if limited else None
        dl_count = int(count.group(1)) if count else 0
        dl_limit = int(limit.group(1)) if limit else SERVER_LIMIT
        reset_msg = duration.group(1) if duration else "알 수 없음"

        remaining = dl_limit - dl_count
        return is_limited, remaining, dl_count, dl_limit, reset_msg
    except Exception as e:
        log(f"  서버 한도 확인 실패: {e}")
        return None, SERVER_LIMIT, 0, SERVER_LIMIT, "확인 불가"


def is_official_score(html_text):
    """페이지에서 official 배지 확인"""
    if 'class="official"' in html_text or '"isOfficial":true' in html_text:
        return True
    if '"official_score"' in html_text or 'Official Score' in html_text:
        return True
    return False


def check_downloadable(decoded):
    """isDownloadable 필드 확인 (false면 다운로드 불가 악보)"""
    m = re.search(r'"isDownloadable":(true|false)', decoded)
    if m:
        return m.group(1) == "true"
    return True  # 필드 없으면 다운로드 가능으로 간주


def download_score(session, score_url, score_id):
    try:
        # 1. 페이지 로드 → h값 추출
        resp = session.get(score_url, headers={"User-Agent": UA}, timeout=15)

        # Cloudflare 차단 감지
        if resp.status_code == 403:
            return False, "CF차단 (403)", True

        decoded = urllib.parse.unquote(resp.text.replace('&amp;', '&').replace('&quot;', '"'))

        # official 필터
        if OFFICIAL_ONLY and not is_official_score(resp.text):
            return False, "non-official (스킵)", False

        # Downloadable 체크
        if not check_downloadable(decoded):
            return False, "not-downloadable (스킵)", False

        # 서버 한도 사전 체크 (페이지 데이터에서)
        limited = re.search(r'"is_download_limited":(true|false)', decoded)
        if limited and limited.group(1) == "true":
            duration = re.search(r'"duration":"([^"]+)"', decoded)
            reset = duration.group(1) if duration else "?"
            return False, f"서버한도 (리셋: {reset})", True

        m = re.search(rf'score_id={score_id}&type=mxl&h=(\d+)', decoded)
        if not m:
            return False, "h값 없음", False

        h = m.group(1)
        dl_url = f"https://musescore.com/score/download/index?score_id={score_id}&type=mxl&h={h}"

        # 2. 다운로드 요청 (redirect 따로 확인)
        r = session.get(dl_url, headers={
            "User-Agent": UA,
            "Referer": score_url,
        }, allow_redirects=False, timeout=30)

        # redirect → S3 URL이면 성공
        if r.status_code in (301, 302, 307):
            location = r.headers.get("location", "")
            if "forbidden" in location:
                return False, "한도초과 (forbidden redirect)", True
            # S3 URL로 실제 다운로드
            r2 = session.get(location, headers={"User-Agent": UA}, timeout=30)
            if r2.content[:2] == b'PK' or b'<?xml' in r2.content[:20]:
                dst = os.path.join(MXL_DIR, f"{score_id}.mxl")
                with open(dst, 'wb') as f:
                    f.write(r2.content)
                return True, f"{len(r2.content)//1024}KB", False
            return False, f"미확인응답({len(r2.content)}bytes)", False

        # 직접 응답
        if r.status_code == 200:
            if r.content[:2] == b'PK' or b'<?xml' in r.content[:20]:
                dst = os.path.join(MXL_DIR, f"{score_id}.mxl")
                with open(dst, 'wb') as f:
                    f.write(r.content)
                return True, f"{len(r.content)//1024}KB", False

        if r.status_code == 403:
            return False, "403 forbidden", True

        return False, f"HTTP {r.status_code}", False

    except Exception as e:
        return False, f"오류: {e}", False


def main():
    os.makedirs(MXL_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    done_ids    = load_done(DONE_FILE)
    daily_count = load_daily(DAILY_FILE)

    if daily_count >= DAILY_LIMIT:
        log(f"오늘 로컬 한도 {DAILY_LIMIT}개 달성. 내일 재실행.")
        return

    log(f"오늘 {daily_count}/{DAILY_LIMIT}")

    # __cf_bm 쿠키 만료 체크 (만료 시 자동 갱신 시도)
    cf_cookie, cf_msg = check_cf_cookie()
    if cf_cookie is None:
        log(f"⚠️ {cf_msg}")
        log("자동 갱신 시도 중...")
        import subprocess
        result = subprocess.run(
            [os.path.join(BASE_DIR, "venv/bin/python3"), os.path.join(BASE_DIR, "refresh_cookie.py")],
            capture_output=True, text=True, timeout=120
        )
        log(f"갱신 결과: {result.stdout.strip().split(chr(10))[-1]}")
        # 재확인
        cf_cookie, cf_msg = check_cf_cookie()
        if cf_cookie is None:
            log(f"⚠️ 갱신 실패: {cf_msg}")
            log("중단합니다.")
            return

    log(f"🍪 {cf_msg}")
    session = make_session()

    # 서버 한도 사전 체크
    is_limited, remaining, dl_count, dl_limit, reset_msg = check_server_limit(session)
    if is_limited:
        log(f"⚠️ 서버 한도 도달 ({dl_count}/{dl_limit}). 리셋: {reset_msg}")
        return
    log(f"📊 서버 한도: {dl_count}/{dl_limit} 사용 (남은: {remaining})")

    consecutive_fail = 0

    for i, item in enumerate(iter_pending_urls(BASE_DIR + "/data/urls.jsonl", done_ids)):
        if daily_count >= DAILY_LIMIT:
            log(f"오늘 한도 도달. 중단.")
            break

        score_id  = item["id"]
        score_url = item["url"]
        title     = item.get("title", "")[:40]
        log(f"[{i+1}] {title}")

        ok, msg, is_limit = download_score(session, score_url, score_id)

        if ok:
            log(f"  ✅ {score_id}.mxl ({msg})")
            consecutive_fail = 0
            with open(f"{OUT_DIR}/{score_id}_meta.json", "w") as f:
                json.dump(item, f, ensure_ascii=False)
            mark_done(DONE_FILE, score_id)
            done_ids.add(score_id)
            daily_count += 1
            save_daily(DAILY_FILE, daily_count)
        else:
            # 스킵 가능한 실패 (done 처리, 연속실패 카운트 안 함)
            skip_msgs = ("non-official (스킵)", "not-downloadable (스킵)", "h값 없음")
            is_404 = msg.startswith("HTTP 404")
            if msg in skip_msgs or is_404:
                if is_404:
                    log(f"  ⏭️ 삭제된 악보 (404)")
                mark_done(DONE_FILE, score_id)
                done_ids.add(score_id)
                time.sleep(random.uniform(1, 2))  # Cloudflare rate limit 방지
                continue
            log(f"  ❌ {msg}")
            if is_limit:
                log("서버 한도 도달. 오늘 중단.")
                break
            consecutive_fail += 1
            if consecutive_fail >= 10:
                log("연속 10회 실패. 중단.")
                break

        time.sleep(random.uniform(*DELAY))

    log(f"완료: 오늘 {daily_count}개 | 누적 {len(done_ids)}개")


main()
