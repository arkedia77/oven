#!/bin/bash
# WAN 2.2 다운로드 완료 후 Google Drive로 복사
# 다운로드 완료 감지 → .incomplete 없으면 복사 시작

SRC="/Volumes/project backup/ai_models/wan2.2-t2v-a14b"
GDRIVE="$HOME/Library/CloudStorage/GoogleDrive-beomjun.lee@gmail.com/내 드라이브/1. work/claude/musicscore/wan2.2-t2v-a14b"
LOG="$HOME/musicscore/wan_upload.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

log "=== WAN 2.2 → Google Drive 업로드 스크립트 시작 ==="

# 1. 다운로드 완료 대기 (.incomplete 파일이 없어질 때까지)
log "다운로드 완료 대기 중..."
while true; do
    INCOMPLETE=$(find "$SRC" -name "*.incomplete" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$INCOMPLETE" -eq 0 ]; then
        log "다운로드 완료 확인! (.incomplete 파일 0개)"
        break
    fi
    log "아직 다운로드 중... (.incomplete $INCOMPLETE개 남음)"
    sleep 300  # 5분마다 체크
done

# 2. Google Drive로 복사
log "Google Drive 복사 시작: $GDRIVE"
mkdir -p "$GDRIVE"

# rsync로 복사 (중간에 끊겨도 이어받기 가능, .cache 제외)
rsync -av --progress --exclude='.cache' --exclude='.DS_Store' "$SRC/" "$GDRIVE/" 2>&1 | tee -a "$LOG"

if [ $? -eq 0 ]; then
    TOTAL=$(du -sh "$GDRIVE" | cut -f1)
    log "=== 복사 완료! 총 $TOTAL ==="
else
    log "=== 복사 실패! 로그 확인: $LOG ==="
fi
