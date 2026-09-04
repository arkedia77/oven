#!/bin/bash
# Qwen2.5-VL-7B → 5090 E:\models\ SCP 전송
# 파일별로 쪼개서 전송, 실패 시 재시도

SRC="/Volumes/project backup/ai_models/qwen2.5-vl-7b"
DST="leo@100.107.229.5:E:/models/Qwen2.5-VL-7B-Instruct/"
LOG="$HOME/musicscore/scp_qwen7b.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "=== Qwen2.5-VL-7B → 5090 SCP 전송 시작 ==="

# 큰 파일(safetensors) 먼저, 작은 파일 나중에
for f in "$SRC"/*; do
    fname=$(basename "$f")
    log "전송 시작: $fname ($(du -h "$f" | cut -f1))"

    # 최대 3번 재시도
    for attempt in 1 2 3; do
        scp -o ConnectTimeout=30 "$f" "$DST" 2>&1 | tee -a "$LOG"
        if [ $? -eq 0 ]; then
            log "  ✅ $fname 완료"
            break
        else
            log "  ❌ $fname 실패 (시도 $attempt/3), 30초 후 재시도..."
            sleep 30
        fi
    done
done

log "=== 전송 완료 ==="

# 검증: 5090에서 파일 수 확인
ssh leo@100.107.229.5 "dir /b E:\models\Qwen2.5-VL-7B-Instruct" 2>&1 | tee -a "$LOG"
