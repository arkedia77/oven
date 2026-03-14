"""
MuseScore forbidden 원인 진단 스크립트
- HTTP 상태코드, redirect chain, 응답 본문 확인
- Pro 세션 유효 여부
- h값 추출 정상 여부
- cf_clearance 만료 여부
"""
import os, re, urllib.parse
from datetime import datetime
import browser_cookie3
from curl_cffi import requests as cf_requests

COOKIE_FILE = os.path.expanduser("~/musicscore/chrome_profile/Default/Cookies")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"

# 테스트용 악보 URL (유명 곡)
TEST_URL = "https://musescore.com/official_scores/scores/5164076"
TEST_ID = "5164076"


def check_cookies():
    print("=" * 60)
    print("1. 쿠키 진단")
    print("=" * 60)

    cookies = browser_cookie3.chrome(cookie_file=COOKIE_FILE, domain_name='.musescore.com')
    jar = {}
    now = datetime.now()

    critical = ['__cf_bm', 'cf_clearance', '_identity', '_ms_auth_provider']
    for c in cookies:
        jar[c.name] = c.value
        if c.name in critical:
            if c.expires:
                exp = datetime.fromtimestamp(c.expires)
                remaining = (exp - now).total_seconds() / 60
                status = "✅ 유효" if exp > now else "❌ 만료됨"
                print(f"  {c.name}: {status} (만료: {exp.strftime('%m/%d %H:%M')}, {remaining:.0f}분)")
            else:
                print(f"  {c.name}: ⚠️ 만료시간 없음 (세션 쿠키)")

    for name in critical:
        if name not in jar:
            print(f"  {name}: ❌ 없음")

    return jar


def test_page_load(jar):
    print()
    print("=" * 60)
    print("2. 페이지 로드 테스트")
    print("=" * 60)

    session = cf_requests.Session(impersonate="chrome110")
    for k, v in jar.items():
        session.cookies.set(k, v, domain='.musescore.com')

    # 악보 페이지 접속
    resp = session.get(TEST_URL, headers={"User-Agent": UA}, timeout=15)
    print(f"  URL: {TEST_URL}")
    print(f"  Status: {resp.status_code}")
    print(f"  Final URL: {resp.url}")
    print(f"  Content-Type: {resp.headers.get('content-type', 'N/A')}")
    print(f"  Content Length: {len(resp.text)} chars")

    # Cloudflare 차단 확인
    if resp.status_code == 403:
        print("  ❌ Cloudflare 403 차단")
        print(f"  응답 일부: {resp.text[:500]}")
        return None, session

    if 'challenge' in resp.text.lower() or 'cf-browser-verification' in resp.text.lower():
        print("  ❌ Cloudflare challenge 페이지 감지")
        return None, session

    # 로그인 상태 확인
    if '"isLoggedIn":true' in resp.text or 'userProfile' in resp.text:
        print("  ✅ 로그인 상태 확인됨")
    elif '"isLoggedIn":false' in resp.text:
        print("  ❌ 로그인 안 됨 (Pro 세션 만료)")
    else:
        print("  ⚠️ 로그인 상태 불확인")

    # Pro 계정 확인
    if '"isPro":true' in resp.text or '"hasPro":true' in resp.text or 'pro-badge' in resp.text:
        print("  ✅ Pro 계정 활성")
    elif '"isPro":false' in resp.text:
        print("  ⚠️ Pro 계정 아님 또는 감지 안 됨")

    # h값 추출
    decoded = urllib.parse.unquote(resp.text.replace('&amp;', '&').replace('&quot;', '"'))
    m = re.search(rf'score_id={TEST_ID}&type=mxl&h=(\d+)', decoded)
    if m:
        h = m.group(1)
        print(f"  ✅ h값 추출 성공: {h}")
        return h, session
    else:
        print("  ❌ h값 추출 실패")
        # h값 패턴 주변 확인
        h_any = re.search(r'type=mxl&h=(\d+)', decoded)
        if h_any:
            print(f"  ⚠️ 다른 score_id의 h값 발견: {h_any.group(0)}")
        # 다운로드 링크 확인
        dl_match = re.search(r'download.*?mxl', decoded[:5000], re.IGNORECASE)
        if dl_match:
            print(f"  힌트: {dl_match.group(0)[:100]}")
        return None, session


def test_download(h, session):
    if not h:
        print()
        print("=" * 60)
        print("3. 다운로드 테스트 - 스킵 (h값 없음)")
        print("=" * 60)
        return

    print()
    print("=" * 60)
    print("3. 다운로드 테스트")
    print("=" * 60)

    dl_url = f"https://musescore.com/score/download/index?score_id={TEST_ID}&type=mxl&h={h}"
    print(f"  URL: {dl_url}")

    r = session.get(dl_url, headers={
        "User-Agent": UA,
        "Referer": TEST_URL,
    }, allow_redirects=False, timeout=30)

    print(f"  Status: {r.status_code}")
    print(f"  Location: {r.headers.get('location', 'N/A')}")

    # redirect chain 추적
    if r.status_code in (301, 302, 303, 307):
        redirect_url = r.headers.get('location', '')
        print(f"  Redirect → {redirect_url[:100]}")

        if 'forbidden' in redirect_url.lower():
            print("  ❌ forbidden redirect 감지")
            # allow_redirects로 최종 응답 확인
            r2 = session.get(dl_url, headers={
                "User-Agent": UA,
                "Referer": TEST_URL,
            }, allow_redirects=True, timeout=30)
            print(f"  최종 URL: {r2.url}")
            print(f"  최종 Status: {r2.status_code}")
            print(f"  응답 일부: {r2.text[:300]}")
        else:
            # follow redirect
            r2 = session.get(redirect_url, headers={"User-Agent": UA}, timeout=30)
            print(f"  최종 Status: {r2.status_code}")
            content_start = r2.content[:20]
            if content_start[:2] == b'PK':
                print(f"  ✅ MXL 파일 (ZIP) 다운로드 성공! ({len(r2.content)//1024}KB)")
            elif b'<?xml' in content_start:
                print(f"  ✅ XML 파일 다운로드 성공! ({len(r2.content)//1024}KB)")
            else:
                print(f"  ⚠️ 미확인 응답: {content_start}")
    elif r.status_code == 200:
        content_start = r.content[:20]
        if content_start[:2] == b'PK' or b'<?xml' in content_start:
            print(f"  ✅ 직접 다운로드 성공! ({len(r.content)//1024}KB)")
        else:
            print(f"  ⚠️ 200이지만 비정상 콘텐츠: {content_start}")
            print(f"  응답 일부: {r.text[:300]}")
    else:
        print(f"  ❌ 비정상 응답: {r.status_code}")
        print(f"  응답 일부: {r.text[:300]}")


def diagnose():
    print("MuseScore 다운로드 진단")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    jar = check_cookies()
    h, session = test_page_load(jar)
    test_download(h, session)

    print()
    print("=" * 60)
    print("4. 종합 진단")
    print("=" * 60)

    # cf_clearance 체크
    cookies = browser_cookie3.chrome(cookie_file=COOKIE_FILE, domain_name='.musescore.com')
    cf_clear = None
    for c in cookies:
        if c.name == 'cf_clearance' and c.expires:
            exp = datetime.fromtimestamp(c.expires)
            if exp < datetime.now():
                cf_clear = "expired"
            else:
                cf_clear = "valid"

    if cf_clear == "expired":
        print("  🔴 cf_clearance 만료 → Cloudflare 차단 가능성 높음")
        print("  → 해결: refresh_cookie.py 실행 또는 Chrome으로 musescore.com 방문")
    elif cf_clear is None:
        print("  🔴 cf_clearance 없음 → Cloudflare 차단")
        print("  → 해결: Chrome으로 musescore.com 방문하여 challenge 통과")
    else:
        print("  ✅ cf_clearance 유효")

    if h:
        print("  ✅ 페이지 로드 + h값 추출 정상")
    else:
        print("  🔴 h값 추출 실패 → 페이지 접근 문제")


diagnose()
