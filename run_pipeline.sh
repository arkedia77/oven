#!/bin/bash
# MusicScore 파이프라인 자동 실행
# 사용법: nohup bash run_pipeline.sh > /dev/null 2>&1 &
# 모니터: tail ~/musicscore/logs/pipeline.log

CD="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$CD/venv/bin/python3"
LOG="$CD/logs/pipeline.log"

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"; }

log "========== 파이프라인 시작 =========="

# 1단계: DB 2차 스캔 완료 대기
log "1단계: DB 2차 스캔 완료 대기 (PID 확인)..."
while pgrep -f "build_dataset_db.py" > /dev/null 2>&1; do
    sleep 60
done
log "1단계 완료: DB 스캔 종료 확인"

# 2단계: 피아노 분류
log "2단계: classify_piano.py 시작"
$PYTHON "$CD/classify_piano.py"
EXIT1=$?
log "2단계 완료: classify_piano.py (exit=$EXIT1)"

if [ $EXIT1 -ne 0 ]; then
    log "❌ classify_piano.py 실패, 파이프라인 중단"
    exit 1
fi

# 3단계: 큐레이션
log "3단계: curate_training_set.py 시작"
$PYTHON "$CD/curate_training_set.py"
EXIT2=$?
log "3단계 완료: curate_training_set.py (exit=$EXIT2)"

# Google Drive DB 동기화
log "DB → Google Drive 동기화"
GDRIVE="$HOME/Library/CloudStorage/GoogleDrive-beomjun.lee@gmail.com/내 드라이브/1. work/claude/musicscore"
if [ -d "$GDRIVE" ]; then
    cp "$CD/data/musicscore.db" "$GDRIVE/musicscore.db"
    cp "$CD/data/db_report.json" "$GDRIVE/db_report.json"
    cp "$CD/data/classify_report.json" "$GDRIVE/classify_report.json" 2>/dev/null
    cp "$CD/data/curate_report.json" "$GDRIVE/curate_report.json" 2>/dev/null
    log "동기화 완료"
else
    log "⚠️ Google Drive 경로 없음: $GDRIVE"
fi

log "========== 파이프라인 완료 =========="
