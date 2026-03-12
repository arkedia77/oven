"""
BitMIDI 전체 다운로더 (113K MIDI)
- 페이지당 15개, 총 7,549페이지
- 직접 다운로드: https://bitmidi.com/uploads/{id}.mid
"""

import os, re, time, random, requests, json
from utils import make_logger, load_done, mark_done, UA, BASE_DIR

OUT_DIR   = "/Volumes/data/score/bitmidi"
LOG_FILE  = f"{BASE_DIR}/logs/bitmidi.log"
DONE_FILE = f"{BASE_DIR}/data/bitmidi_done.txt"
TOTAL_PAGES = 7549
DELAY = (0.5, 1.5)

log = make_logger(LOG_FILE)

def get_page_midis(session, page):
    url = f"https://bitmidi.com/?page={page}"
    try:
        resp = session.get(url, headers={"User-Agent": UA}, timeout=10)
        m = re.search(r'window\.initStore\s*=\s*(\{.*?\})\s*\n', resp.text, re.DOTALL)
        if not m:
            return []
        data = json.loads(m.group(1))
        midis = data.get("data", {}).get("midis", {})
        return [
            {"id": v["id"], "name": v["name"], "slug": k, "download_url": v["downloadUrl"]}
            for k, v in midis.items()
        ]
    except Exception as e:
        return []

def download_midi(session, midi_info, done_ids):
    mid_id = str(midi_info["id"])
    if mid_id in done_ids:
        return False, "skip"

    url = f"https://bitmidi.com{midi_info['download_url']}"
    try:
        r = session.get(url, headers={"User-Agent": UA, "Referer": "https://bitmidi.com/"}, timeout=15)
        if not r.content or len(r.content) < 20:
            return False, "빈파일"
        if not r.content[:4].startswith(b'MThd'):
            return False, "MIDI아님"

        out_path = os.path.join(OUT_DIR, f"{mid_id}.mid")
        with open(out_path, 'wb') as f:
            f.write(r.content)
        mark_done(DONE_FILE, mid_id)
        return True, f"{len(r.content)//1024}KB"
    except Exception as e:
        return False, str(e)[:40]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    done_ids = load_done(DONE_FILE)
    log(f"BitMIDI 다운로더 시작 | 기존 완료: {len(done_ids):,}개")

    session = requests.Session()
    ok_total = 0
    fail_total = 0

    for page in range(0, TOTAL_PAGES):
        midis = get_page_midis(session, page)
        if not midis:
            log(f"  p{page}: 파싱 실패, 건너뜀")
            time.sleep(2)
            continue

        for midi in midis:
            ok, msg = download_midi(session, midi, done_ids)
            if ok:
                done_ids.add(str(midi["id"]))
                ok_total += 1
            elif msg != "skip":
                fail_total += 1
            time.sleep(random.uniform(*DELAY))

        if page % 50 == 0:
            log(f"p{page}/{TOTAL_PAGES} | 오늘 +{ok_total} | 누적 {len(done_ids):,}개")

    log(f"완료: 성공 {ok_total:,} / 실패 {fail_total:,} / 누적 {len(done_ids):,}개")

main()
