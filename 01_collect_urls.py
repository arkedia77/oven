"""
MuseScore 메타데이터 수집기 v3
- 검색 페이지 ARTICLE 카드에서 메타데이터 직접 추출
- 개별 악보 페이지 방문 없음 (Cloudflare 차단 우회)
- 목표: 10,000곡 → data/urls.jsonl
"""

import json, time, random, os, asyncio, re
from datetime import datetime
from playwright.async_api import async_playwright

BASE_DIR  = os.path.expanduser("~/projects/musescore-dl")
OUT_FILE  = f"{BASE_DIR}/data/urls.jsonl"
LOG_FILE  = f"{BASE_DIR}/logs/collect.log"
TARGET    = 10000

QUERIES = [
    ("piano", "view_count"), ("guitar", "view_count"), ("violin", "view_count"),
    ("", "view_count"), ("", "date_added"), ("classical", "view_count"),
    ("jazz", "view_count"), ("pop", "view_count"), ("bach", "view_count"),
    ("beethoven", "view_count"), ("chopin", "view_count"), ("mozart", "view_count"),
    ("anime", "view_count"), ("kpop", "view_count"), ("film", "view_count"),
    ("string quartet", "view_count"), ("orchestra", "view_count"),
    ("blues", "view_count"), ("folk", "view_count"), ("rock", "view_count"),
    ("cello", "view_count"), ("flute", "view_count"), ("trumpet", "view_count"),
    ("harp", "view_count"), ("drums", "view_count"), ("bass", "view_count"),
]

STEALTH_JS = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = {runtime: {}};
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
"""

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def parse_views(raw):
    """'7.4M' -> 7400000, '254.3K' -> 254300"""
    if not raw:
        return 0
    raw = raw.strip()
    try:
        if raw.endswith('M'):
            return int(float(raw[:-1]) * 1_000_000)
        elif raw.endswith('K'):
            return int(float(raw[:-1]) * 1_000)
        elif raw.endswith('B'):
            return int(float(raw[:-1]) * 1_000_000_000)
        return int(raw.replace(',', ''))
    except:
        return 0

DIFF_MAP = {'beginner': 1, 'easy': 2, 'intermediate': 3, 'advanced': 4, 'professional': 5}

async def get_cards_from_search(page, query, sort, pg):
    """검색 페이지 ARTICLE 카드에서 메타데이터 직접 추출"""
    url = f"https://musescore.com/sheetmusic?text={query}&sort={sort}&page={pg}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(random.uniform(3, 5))
    except Exception as e:
        log(f"  페이지 로드 실패: {e}")
        return []

    try:
        cards = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('article').forEach(article => {
                const link = article.querySelector('a[href*="/scores/"]');
                if (!link || !/user\\/\\d+\\/scores\\/\\d+/.test(link.href)) return;

                const lines = article.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
                const meta_line = lines.find(l => l.includes('part') || l.includes('page')) || '';

                const viewText = article.innerText.match(/([\\d.]+[KMB]?) view/);
                const savesText = article.innerText.match(/([\\d.]+[KMB]?) save/);
                const pagesText = meta_line.match(/(\\d+) page/);
                const partsText = meta_line.match(/(\\d+) part/);
                const durText   = meta_line.match(/\\b(\\d{1,2}:\\d{2})\\b/);
                const dateText  = meta_line.match(/([A-Z][a-z]+ \\d+, \\d{4})/);

                results.push({
                    url:        link.href,
                    difficulty_label: lines[0] || 'unknown',
                    title:      lines[1] || '',
                    author:     lines[2] || '',
                    parts:      partsText ? parseInt(partsText[1]) : 0,
                    pages:      pagesText ? parseInt(pagesText[1]) : 0,
                    duration:   durText   ? durText[1] : '',
                    date_added: dateText  ? dateText[1] : '',
                    views_raw:  viewText  ? viewText[1] : '',
                    saves_raw:  savesText ? savesText[1] : '',
                });
            });
            return results;
        }""")
    except Exception as e:
        log(f"  평가 실패: {e}")
        return []

    enriched = []
    for c in cards:
        m = re.search(r'/scores/(\d+)', c['url'])
        if not m:
            continue
        c['id'] = m.group(1)
        diff_lower = c['difficulty_label'].lower()
        c['difficulty'] = next((v for k, v in DIFF_MAP.items() if k in diff_lower), 0)
        c['views'] = parse_views(c['views_raw'])
        c['saves'] = parse_views(c['saves_raw'])
        c['collected_at'] = datetime.now().isoformat()
        del c['views_raw'], c['saves_raw']
        enriched.append(c)

    return enriched


async def main():
    os.makedirs(f"{BASE_DIR}/data", exist_ok=True)
    os.makedirs(f"{BASE_DIR}/logs", exist_ok=True)

    seen_ids = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE) as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["id"])
                except:
                    pass
    log(f"기존 수집 {len(seen_ids)}개 로드")

    collected = len(seen_ids)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        await ctx.add_init_script(STEALTH_JS)
        page = await ctx.new_page()

        out = open(OUT_FILE, "a")

        try:
            for (query, sort) in QUERIES:
                if collected >= TARGET:
                    break
                log(f"=== 검색: '{query}' sort={sort} ===")

                consecutive_empty = 0
                for pg in range(1, 500):
                    if collected >= TARGET:
                        break

                    cards = await get_cards_from_search(page, query, sort, pg)
                    new_cards = [c for c in cards if c['id'] not in seen_ids]

                    if not new_cards:
                        consecutive_empty += 1
                        log(f"  p{pg}: 새 항목 없음 ({consecutive_empty}회 연속)")
                        if consecutive_empty >= 3:
                            break
                        continue

                    consecutive_empty = 0
                    for card in new_cards:
                        if collected >= TARGET:
                            break
                        seen_ids.add(card['id'])
                        out.write(json.dumps(card, ensure_ascii=False) + "\n")
                        out.flush()
                        collected += 1

                    log(f"  p{pg}: +{len(new_cards)}개 (총 {collected}/{TARGET})")
                    await asyncio.sleep(random.uniform(1.5, 3.0))

        finally:
            out.close()
            await browser.close()

    log(f"완료: {collected}개 → {OUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
