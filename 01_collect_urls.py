"""
MuseScore 메타데이터 수집기 v5
- 경로 기반 쿼리 (악기별, 장르별, 타입별)
- 하루 수집 한도 자동 중단
- article에서 악기/앙상블/투표수 추출
"""

import json, random, os, re, time, urllib.parse
from datetime import datetime, date
import undetected_chromedriver as uc

BASE_DIR     = os.path.expanduser("~/musicscore")
OUT_FILE     = f"{BASE_DIR}/data/urls.jsonl"
LOG_FILE     = f"{BASE_DIR}/logs/collect.log"
SESSION_FILE = f"{BASE_DIR}/data/session.json"
STATE_FILE   = f"{BASE_DIR}/data/state.json"   # 진행 상태 저장

DAILY_LIMIT  = 50000  # 리스트 수집은 덜 위험 → 한도 높게
PAGE_DELAY   = (2, 4)   # 페이지 간 딜레이 (초)
TARGET       = 500_000

QUERIES = [
    # ── K-POP 아티스트 텍스트 검색 (최신순) ──────────────────
    ("BTS",             "date_added", "search"),
    ("aespa",           "date_added", "search"),
    ("NewJeans",        "date_added", "search"),
    ("BLACKPINK",       "date_added", "search"),
    ("IVE",             "date_added", "search"),
    ("Stray Kids",      "date_added", "search"),
    ("TWICE",           "date_added", "search"),
    ("LE SSERAFIM",     "date_added", "search"),
    ("(G)I-DLE",        "date_added", "search"),
    ("SEVENTEEN",       "date_added", "search"),
    ("EXO",             "date_added", "search"),
    ("Red Velvet",      "date_added", "search"),
    ("ITZY",            "date_added", "search"),
    ("TXT",             "date_added", "search"),
    ("NCT",             "date_added", "search"),
    ("ATEEZ",           "date_added", "search"),
    ("IU",              "date_added", "search"),
    ("ZICO",            "date_added", "search"),
    ("Jay Park",        "date_added", "search"),
    ("BABYMONSTER",     "date_added", "search"),
    ("ILLIT",           "date_added", "search"),
    ("KISS OF LIFE",    "date_added", "search"),
    ("NMIXX",           "date_added", "search"),
    ("Stray Kids piano","date_added", "search"),
    ("BTS piano",       "date_added", "search"),
    ("kpop piano",      "date_added", "search"),
    # ── 최신순 우선 (장르) ─────────────────────────────────
    ("k-pop",           "date_added", "genre"),
    ("pop",             "date_added", "genre"),
    ("anime",           "date_added", "genre"),
    ("soundtrack",      "date_added", "genre"),
    ("rock",            "date_added", "genre"),
    ("jazz",            "date_added", "genre"),
    ("electronic",      "date_added", "genre"),
    ("hip-hop",         "date_added", "genre"),
    ("rb-funk-soul",    "date_added", "genre"),
    ("new-age",         "date_added", "genre"),
    ("folk",            "date_added", "genre"),
    ("world-music",     "date_added", "genre"),
    ("classical",       "date_added", "genre"),
    ("blues",           "date_added", "genre"),
    ("country",         "date_added", "genre"),
    ("reggae-ska",      "date_added", "genre"),
    ("religious-music", "date_added", "genre"),
    ("experimental",    "date_added", "genre"),
    # ── 최신순 우선 (악기) ─────────────────────────────────
    ("piano",           "date_added", "instrument"),
    ("guitar",          "date_added", "instrument"),
    ("violin",          "date_added", "instrument"),
    ("voice",           "date_added", "instrument"),
    ("drums",           "date_added", "instrument"),
    ("bass-guitar",     "date_added", "instrument"),
    ("ukulele",         "date_added", "instrument"),
    ("cello",           "date_added", "instrument"),
    ("flute",           "date_added", "instrument"),
    ("saxophone-alto",  "date_added", "instrument"),
    # ── 최신순 (타입/난이도) ───────────────────────────────
    ("non-official",    "date_added", "type"),
    ("official",        "date_added", "type"),
    ("beginner",        "date_added", "difficulty"),
    ("intermediate",    "date_added", "difficulty"),
    ("advanced",        "date_added", "difficulty"),
    # ── 인기순 (보완용) ────────────────────────────────────
    ("k-pop",           "view_count", "genre"),
    ("pop",             "view_count", "genre"),
    ("anime",           "view_count", "genre"),
    ("soundtrack",      "view_count", "genre"),
    ("piano",           "view_count", "instrument"),
    ("guitar",          "view_count", "instrument"),
    ("violin",          "view_count", "instrument"),
    ("classical",       "view_count", "genre"),
    ("rock",            "view_count", "genre"),
    ("jazz",            "view_count", "genre"),
    ("electronic",      "view_count", "genre"),
    ("hip-hop",         "view_count", "genre"),
    ("rb-funk-soul",    "view_count", "genre"),
    ("new-age",         "view_count", "genre"),
    ("folk",            "view_count", "genre"),
    ("world-music",     "view_count", "genre"),
    ("blues",           "view_count", "genre"),
    ("country",         "view_count", "genre"),
    ("reggae-ska",      "view_count", "genre"),
    ("religious-music", "view_count", "genre"),
    ("experimental",    "view_count", "genre"),
    ("cello",           "view_count", "instrument"),
    ("viola",           "view_count", "instrument"),
    ("flute",           "view_count", "instrument"),
    ("clarinet",        "view_count", "instrument"),
    ("saxophone-alto",  "view_count", "instrument"),
    ("saxophone-tenor", "view_count", "instrument"),
    ("trumpet",         "view_count", "instrument"),
    ("trombone",        "view_count", "instrument"),
    ("french-horn",     "view_count", "instrument"),
    ("drums",           "view_count", "instrument"),
    ("bass-guitar",     "view_count", "instrument"),
    ("ukulele",         "view_count", "instrument"),
    ("harp",            "view_count", "instrument"),
    ("organ",           "view_count", "instrument"),
    ("accordion",       "view_count", "instrument"),
    ("voice",           "view_count", "instrument"),
    ("official",        "view_count", "type"),
    ("non-official",    "view_count", "type"),
    ("beginner",        "view_count", "difficulty"),
    ("intermediate",    "view_count", "difficulty"),
    ("advanced",        "view_count", "difficulty"),
]

DIFF_MAP = {'beginner':1,'easy':2,'intermediate':3,'advanced':4,'professional':5}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def parse_num(raw):
    if not raw: return 0
    raw = str(raw).strip()
    try:
        if raw.endswith('M'): return int(float(raw[:-1]) * 1_000_000)
        elif raw.endswith('K'): return int(float(raw[:-1]) * 1_000)
        elif raw.endswith('B'): return int(float(raw[:-1]) * 1_000_000_000)
        return int(raw.replace(',', ''))
    except: return 0

def load_state():
    """진행 상태 로드 (어떤 쿼리, 몇 페이지까지 했는지)"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"query_index": 0, "page": 1, "today": str(date.today()), "today_count": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_cards(driver, path, sort, pg, tag=""):
    if tag == "search":
        url = f"https://musescore.com/sheetmusic?text={urllib.parse.quote(path)}&sort={sort}&page={pg}"
    else:
        url = f"https://musescore.com/sheetmusic/{path}?sort={sort}&page={pg}"
    try:
        driver.get(url)
        time.sleep(random.uniform(*PAGE_DELAY))
    except Exception as e:
        log(f"  페이지 로드 실패: {e}")
        return []

    try:
        cards = driver.execute_script("""
            const results = [];
            document.querySelectorAll('article').forEach(article => {
                const link = article.querySelector('a[href*="/scores/"]');
                if (!link || !/user\\/\\d+\\/scores\\/\\d+/.test(link.href)) return;

                const lines = article.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                const meta_line = lines.find(l => l.includes('part') || l.includes('page')) || '';

                const viewText  = article.innerText.match(/([\\d.]+[KMB]?) view/);
                const savesText = article.innerText.match(/([\\d.]+[KMB]?) save/);
                const votesText = article.innerText.match(/([\\d.]+[KMB]?) vote/);
                const pagesText = meta_line.match(/(\\d+) page/);
                const partsText = meta_line.match(/(\\d+) part/);
                const durText   = meta_line.match(/\\b(\\d{1,2}:\\d{2})\\b/);
                const dateText  = meta_line.match(/([A-Z][a-z]+ \\d+, \\d{4})/);

                let instrument = '', ensemble = '';
                article.querySelectorAll('a[href*="/sheetmusic/"]').forEach(a => {
                    const m  = a.href.match(/\\/sheetmusic\\/([a-z-]+)\\/([a-z-]+)/);
                    const m2 = a.href.match(/\\/sheetmusic\\/([a-z-]+)$/);
                    if (m) { ensemble = m[1]; instrument = m[2]; }
                    else if (m2 && !instrument) { instrument = m2[1]; }
                });

                const diffEl = article.querySelector('[class*="cI0jj"]');
                const diffLabel = diffEl ? diffEl.innerText.trim() : (lines[0] || 'unknown');

                results.push({
                    url: link.href,
                    title: lines.find((l,i) => i>0 && l.length>2 && !l.match(/^\\d/)) || lines[1] || '',
                    difficulty_label: diffLabel,
                    instrument, ensemble,
                    parts:      partsText ? parseInt(partsText[1]) : 0,
                    pages:      pagesText ? parseInt(pagesText[1]) : 0,
                    duration:   durText   ? durText[1] : '',
                    date_added: dateText  ? dateText[1] : '',
                    views_raw:  viewText  ? viewText[1] : '',
                    saves_raw:  savesText ? savesText[1] : '',
                    votes_raw:  votesText ? votesText[1] : '',
                });
            });
            return results;
        """)
    except Exception as e:
        log(f"  평가 실패: {e}")
        return []

    enriched = []
    for c in cards:
        m = re.search(r'/scores/(\d+)', c['url'])
        if not m: continue
        c['id'] = m.group(1)
        diff_lower = c['difficulty_label'].lower()
        c['difficulty'] = next((v for k,v in DIFF_MAP.items() if k in diff_lower), 0)
        c['views'] = parse_num(c.pop('views_raw',''))
        c['saves'] = parse_num(c.pop('saves_raw',''))
        c['votes'] = parse_num(c.pop('votes_raw',''))
        c['collected_at'] = datetime.now().isoformat()
        enriched.append(c)
    return enriched


def main():
    os.makedirs(f"{BASE_DIR}/data", exist_ok=True)
    os.makedirs(f"{BASE_DIR}/logs", exist_ok=True)

    # 기존 수집 ID 로드
    seen_ids = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            for line in f:
                try: seen_ids.add(json.loads(line)["id"])
                except: pass
    log(f"기존 수집 {len(seen_ids):,}개 로드")
    collected = len(seen_ids)

    # 상태 로드 (이전 실행 이어받기)
    state = load_state()
    today_str = str(date.today())
    if state["today"] != today_str:
        state["today"] = today_str
        state["today_count"] = 0
        log(f"새 날짜 시작: {today_str}")
    else:
        log(f"오늘 이미 수집: {state['today_count']:,}개")

    if state["today_count"] >= DAILY_LIMIT:
        log(f"오늘 한도 {DAILY_LIMIT:,}개 이미 달성. 내일 다시 실행하세요.")
        return

    PROFILE_DIR = os.path.expanduser("~/musicscore/chrome_profile")
    driver = uc.Chrome(headless=False, version_main=145, user_data_dir=PROFILE_DIR)

    driver.get("https://musescore.com")
    time.sleep(5)
    # 로그인 체크 - /user/login 페이지가 아니면 로그인된 것
    current = driver.current_url
    logged_in = "login" not in current and "musescore.com" in current
    log(f"{'✅ 로그인 확인' if logged_in else '⚠️ 로그인 불확실, 계속 진행'}")

    out = open(OUT_FILE, "a")

    try:
        query_idx = state.get("query_index", 0)
        start_pg  = state.get("page", 1)

        for qi in range(query_idx, len(QUERIES)):
            if collected >= TARGET or state["today_count"] >= DAILY_LIMIT:
                break

            path, sort, tag = QUERIES[qi]
            pg_start = start_pg if qi == query_idx else 1
            log(f"=== [{tag}] {path} sort={sort} (p{pg_start}~) ===")

            consecutive_empty = 0
            for pg in range(pg_start, 1001):
                if collected >= TARGET or state["today_count"] >= DAILY_LIMIT:
                    state["query_index"] = qi
                    state["page"] = pg
                    save_state(state)
                    log(f"오늘 한도 {DAILY_LIMIT:,}개 도달. 중단 (내일 {path} p{pg}부터 재개)")
                    break

                cards = get_cards(driver, path, sort, pg, tag)
                new_cards = [c for c in cards if c['id'] not in seen_ids]

                if not new_cards:
                    consecutive_empty += 1
                    log(f"  p{pg}: 새 항목 없음 ({consecutive_empty}회) [파싱 {len(cards)}개]")
                    if consecutive_empty >= 3:
                        log(f"  → '{path}' 완료, 다음 쿼리로")
                        state["query_index"] = qi + 1
                        state["page"] = 1
                        save_state(state)
                        break
                    continue

                consecutive_empty = 0
                for card in new_cards:
                    if collected >= TARGET or state["today_count"] >= DAILY_LIMIT:
                        break
                    card['query_path'] = path
                    card['query_sort'] = sort
                    card['query_tag']  = tag
                    seen_ids.add(card['id'])
                    out.write(json.dumps(card, ensure_ascii=False) + "\n")
                    out.flush()
                    collected += 1
                    state["today_count"] += 1

                log(f"  p{pg}: +{len(new_cards)}개 (오늘 {state['today_count']:,} / 총 {collected:,})")
                save_state(state)
                time.sleep(random.uniform(1.5, 3.0))

    finally:
        out.close()
        driver.quit()

    log(f"세션 종료: 오늘 {state['today_count']:,}개, 누적 {collected:,}개")


main()
