#!/bin/bash
# MusicXML 벌크 다운로드
# 1단계: dl-librescore로 MIDI 다운로드
# 2단계: music21로 MIDI → MusicXML 변환

URLS_FILE=~/musicscore/data/urls.jsonl
OUT_DIR=/Volumes/data/score/musescore
MIDI_DIR="$OUT_DIR/midi"
MXL_DIR="$OUT_DIR/musicxml"
LOG=~/musicscore/logs/download.log
DONE_FILE=~/musicscore/data/done_ids.txt

# 하루 다운로드 한도
DAILY_LIMIT=300
DAILY_FILE=~/musicscore/data/daily_download.txt

mkdir -p "$MIDI_DIR" "$MXL_DIR" "$(dirname $LOG)"
touch "$DONE_FILE"

# 오늘 카운트 확인
TODAY=$(date +%Y-%m-%d)
if [ -f "$DAILY_FILE" ]; then
    DAILY_DATE=$(head -1 "$DAILY_FILE")
    DAILY_COUNT=$(tail -1 "$DAILY_FILE")
    if [ "$DAILY_DATE" != "$TODAY" ]; then
        echo "$TODAY" > "$DAILY_FILE"
        echo "0" >> "$DAILY_FILE"
        DAILY_COUNT=0
    fi
else
    echo "$TODAY" > "$DAILY_FILE"
    echo "0" >> "$DAILY_FILE"
    DAILY_COUNT=0
fi

if [ "$DAILY_COUNT" -ge "$DAILY_LIMIT" ]; then
    echo "[$(date '+%H:%M:%S')] 오늘 한도 ${DAILY_LIMIT}개 달성. 내일 재실행." | tee -a "$LOG"
    exit 0
fi

total=$(wc -l < "$URLS_FILE")
done_count=$(wc -l < "$DONE_FILE")
echo "[$(date '+%H:%M:%S')] 다운로드 시작: 총 ${total}개 (완료 ${done_count}개, 오늘 ${DAILY_COUNT}/${DAILY_LIMIT})" | tee -a "$LOG"

count=0
while IFS= read -r line; do
    if [ "$DAILY_COUNT" -ge "$DAILY_LIMIT" ]; then
        echo "[$(date '+%H:%M:%S')] 오늘 한도 도달. 중단." | tee -a "$LOG"
        break
    fi

    id=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    url=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('url',''))" 2>/dev/null)
    title=$(echo "$line" | python3 -c "import sys,json; print(json.load(sys.stdin).get('title','unknown')[:50])" 2>/dev/null)

    [ -z "$id" ] && continue
    grep -qF "$id" "$DONE_FILE" 2>/dev/null && continue

    count=$((count + 1))
    echo "[$(date '+%H:%M:%S')] [${count}/${total}] ${title}" | tee -a "$LOG"

    # MIDI 다운로드
    MIDI_OUT="$MIDI_DIR/${id}.mid"
    printf "%s\n" "$url" | npx dl-librescore -t midi -o "$MIDI_DIR" >> "$LOG" 2>&1

    if ls "$MIDI_DIR"/*.mid 2>/dev/null | grep -q .; then
        # 가장 최근 받은 MIDI 파일을 id로 rename
        LATEST=$(ls -t "$MIDI_DIR"/*.mid 2>/dev/null | head -1)
        [ -n "$LATEST" ] && [ "$LATEST" != "$MIDI_OUT" ] && mv "$LATEST" "$MIDI_OUT"

        # MIDI → MusicXML 변환
        python3 -c "
import music21, sys
try:
    s = music21.converter.parse('$MIDI_OUT')
    s.write('musicxml', '$MXL_DIR/${id}.xml')
    print('  변환 완료: ${id}.xml')
except Exception as e:
    print(f'  변환 실패: {e}')
" 2>/dev/null

        echo "$id" >> "$DONE_FILE"
        DAILY_COUNT=$((DAILY_COUNT + 1))
        # 오늘 카운트 업데이트
        echo "$TODAY" > "$DAILY_FILE"
        echo "$DAILY_COUNT" >> "$DAILY_FILE"
    else
        echo "  FAIL: $id $url" >> "$LOG"
    fi

    # 메타데이터 저장
    echo "$line" > "$OUT_DIR/${id}_meta.json"

    sleep $(python3 -c "import random; print(round(random.uniform(5.0, 10.0), 1))")

done < "$URLS_FILE"

echo "[$(date '+%H:%M:%S')] 완료: 오늘 ${DAILY_COUNT}개 다운로드" | tee -a "$LOG"
