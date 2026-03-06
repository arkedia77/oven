#!/bin/bash
# MusicXML 벌크 다운로드
# urls.jsonl에서 URL 읽어 dl-librescore로 다운로드

URLS_FILE=~/projects/musescore-dl/data/urls.jsonl
OUT_DIR=~/projects/musescore-dl/musicxml
LOG=~/projects/musescore-dl/logs/download.log
DONE_FILE=~/projects/musescore-dl/data/done_ids.txt

mkdir -p "$OUT_DIR" "$(dirname $LOG)"
touch "$DONE_FILE"

total=$(wc -l < "$URLS_FILE")
done_count=$(wc -l < "$DONE_FILE")
echo "[$(date '+%H:%M:%S')] 다운로드 시작: 총 $total개 (완료 $done_count개)" | tee -a "$LOG"

count=0
while IFS= read -r line; do
    id=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))")
    url=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('url',''))")
    title=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('title','unknown')[:50])")

    # 이미 완료된 것 스킵
    if grep -qF "$id" "$DONE_FILE" 2>/dev/null; then
        continue
    fi

    count=$((count + 1))
    echo "[$(date '+%H:%M:%S')] [$count/$total] $title" | tee -a "$LOG"

    # dl-librescore로 MusicXML 다운로드
    npx dl-librescore -i "$url" -t musicxml -o "$OUT_DIR" 2>>"$LOG"

    if [ $? -eq 0 ]; then
        echo "$id" >> "$DONE_FILE"
    else
        echo "FAIL: $id $url" >> "$LOG"
    fi

    # 메타데이터 JSON도 저장
    safe_title=$(echo "$title" | tr '/' '_' | tr ' ' '_')
    echo "$line" > "$OUT_DIR/${id}_meta.json"

    # 딜레이 (1.5~3초 랜덤)
    sleep $(python3 -c "import random; print(round(random.uniform(1.5, 3.0), 1))")

done < "$URLS_FILE"

echo "[$(date '+%H:%M:%S')] 다운로드 완료!" | tee -a "$LOG"
