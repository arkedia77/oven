"""
장르 자동 분류 스크립트
- 파일명/경로 기반 키워드 매칭
- 템포+난이도+스타일 조합 보조 분류
- DB files 테이블에 genre 컬럼 추가/업데이트
"""

import os, re, sqlite3
from datetime import datetime

BASE_DIR = os.path.expanduser("~/musicscore")
DB_PATH = f"{BASE_DIR}/data/musicscore.db"
LOG_FILE = f"{BASE_DIR}/logs/classify_genre.log"

# 장르 키워드 매핑 (파일명/경로에서 매칭)
GENRE_KEYWORDS = {
    "classical": [
        "bach", "mozart", "beethoven", "chopin", "liszt", "debussy", "ravel",
        "schubert", "schumann", "brahms", "tchaikovsky", "rachmaninoff", "prokofiev",
        "haydn", "handel", "vivaldi", "mendelssohn", "dvorak", "grieg", "satie",
        "scriabin", "shostakovich", "stravinsky", "bartok", "mussorgsky",
        "sonata", "sonatina", "prelude", "fugue", "etude", "waltz", "mazurka",
        "polonaise", "ballade", "scherzo", "impromptu", "nocturne", "rhapsody",
        "concerto", "symphony", "opus", "bwv", "k\\.", "op\\.", "woo",
        "minuet", "rondo", "aria ", "gavotte", "sarabande", "allemande",
        "fantaisie", "bagatelle", "variation", "invention", "toccata",
    ],
    "jazz": [
        "jazz", "swing", "bebop", "bossa nova", "blues scale", "jazz standard",
        "ragtime", "stride", "boogie", "woogie", "duke ellington", "thelonious",
        "coltrane", "miles davis", "bill evans", "oscar peterson", "art tatum",
        "maple leaf rag", "joplin", "take five", "autumn leaves",
    ],
    "pop": [
        "taylor swift", "ed sheeran", "billie eilish", "adele", "bruno mars",
        "coldplay", "maroon 5", "imagine dragons", "onerepublic", "ariana grande",
        "the weeknd", "dua lipa", "olivia rodrigo", "harry styles", "shawn mendes",
        "charlie puth", "sam smith", "john legend", "alicia keys",
        "someone like you", "perfect", "all of me", "hello", "shallow",
        "bohemian rhapsody", "let it be", "yesterday", "imagine",
    ],
    "kpop": [
        "bts", "blackpink", "twice", "exo", "red velvet", "itzy", "aespa",
        "newjeans", "ive", "le sserafim", "stray kids", "txt", "seventeen",
        "nct", "ateez", "g-idle", "gidle", "nmixx", "illit", "babymonster",
        "iu ", "zico", "bigbang", "2ne1", "shinee", "got7", "mamamoo",
        "kpop", "k-pop", "korean pop",
    ],
    "anime": [
        "anime", "ghibli", "miyazaki", "one piece", "naruto", "demon slayer",
        "kimetsu", "attack on titan", "shingeki", "my hero academia",
        "your name", "spirited away", "howl", "totoro", "merry-go-round",
        "unravel", "gurenge", "zankyou", "eva ", "evangelion",
        "joe hisaishi", "yoko kanno",
    ],
    "game": [
        "minecraft", "undertale", "zelda", "mario", "final fantasy",
        "kingdom hearts", "pokemon", "kirby", "megalovania", "deltarune",
        "genshin", "animal crossing", "hollow knight", "cuphead",
        "tetris", "chrono trigger", "nier", "halo",
    ],
    "film_ost": [
        "interstellar", "inception", "pirates of the caribbean", "star wars",
        "harry potter", "lord of the rings", "hans zimmer", "john williams",
        "ennio morricone", "disney", "pixar", "frozen", "la la land",
        "titanic", "schindler", "amelie", "pride and prejudice",
        "the godfather", "cinema paradiso", "forrest gump",
    ],
    "blues": [
        "blues", "12-bar", "twelve bar", "muddy waters", "bb king",
        "robert johnson", "howlin wolf",
    ],
    "folk": [
        "folk", "traditional", "irish", "celtic", "scottish",
        "appalachian", "bluegrass", "danny boy", "greensleeves",
        "scarborough fair", "amazing grace",
    ],
    "religious": [
        "hymn", "gospel", "praise", "worship", "church", "psalm",
        "ave maria", "hallelujah", "christmas carol", "silent night",
        "jingle bells", "o holy night",
    ],
    "new_age": [
        "new age", "yiruma", "ludovico einaudi", "george winston",
        "brian crain", "kevin kern", "river flows in you",
        "kiss the rain", "mariage d'amour", "comptine",
    ],
    "trot": [
        "트로트", "trot", "송가인", "임영웅", "나훈아", "태진아",
        "설운도", "주현미", "남진", "이미자",
    ],
    "korean_ballad": [
        "발라드", "김광석", "이문세", "조용필", "이승철", "박효신",
        "김범수", "나얼", "성시경", "이적", "윤종신",
        "드라마 ost", "drama ost", "korean ballad",
    ],
}

# 소스 기반 기본 장르
SOURCE_GENRE = {
    "maestro": "classical",
    "asap": "classical",
    "pop909": "pop",
    "pop-k-midi": "kpop",
}


def classify_by_path(path):
    """파일 경로/이름에서 장르 추정"""
    path_lower = path.lower()
    fname = os.path.basename(path_lower)

    matches = {}
    for genre, keywords in GENRE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) if len(kw) > 3 else re.escape(kw), path_lower):
                score += 1
        if score > 0:
            matches[genre] = score

    if matches:
        return max(matches, key=matches.get)
    return None


def classify_by_tempo(avg_tempo, difficulty_level):
    """템포+난이도 기반 보조 분류 (경로 매칭 실패 시)"""
    if avg_tempo and avg_tempo < 80 and difficulty_level and difficulty_level >= 6:
        return "classical"  # 느린 고급 곡 → 클래식 가능성
    return None


def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # genre 컬럼 추가 (없으면)
    existing_cols = [row[1] for row in c.execute("PRAGMA table_info(files)").fetchall()]
    if "genre" not in existing_cols:
        c.execute("ALTER TABLE files ADD COLUMN genre TEXT")
        conn.commit()
        print("genre 컬럼 추가됨")

    # 미분류 파일 가져오기
    c.execute("SELECT id, path, source, avg_tempo, difficulty_level FROM files WHERE genre IS NULL")
    rows = c.fetchall()
    print(f"미분류 파일: {len(rows):,}개")

    stats = {}
    batch = 0

    for file_id, path, source, avg_tempo, difficulty in rows:
        genre = None

        # 1. 소스 기반
        if source in SOURCE_GENRE:
            genre = SOURCE_GENRE[source]

        # 2. 경로/파일명 기반
        if not genre:
            genre = classify_by_path(path)

        # 3. 템포+난이도 보조
        if not genre:
            genre = classify_by_tempo(avg_tempo, difficulty)

        # 4. 미분류
        if not genre:
            genre = "unclassified"

        c.execute("UPDATE files SET genre = ? WHERE id = ?", (genre, file_id))
        stats[genre] = stats.get(genre, 0) + 1
        batch += 1

        if batch % 10000 == 0:
            conn.commit()
            print(f"  {batch:,}개 처리...")

    conn.commit()
    conn.close()

    print(f"\n=== 장르 분류 결과 ({len(rows):,}개) ===")
    for genre, count in sorted(stats.items(), key=lambda x: -x[1]):
        pct = count / len(rows) * 100
        print(f"  {genre}: {count:,} ({pct:.1f}%)")

    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {len(rows):,}개 분류 완료\n")
        for g, cnt in sorted(stats.items(), key=lambda x: -x[1]):
            f.write(f"  {g}: {cnt:,}\n")


main()
