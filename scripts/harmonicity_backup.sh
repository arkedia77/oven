#!/bin/bash
# 하모니시티 시뮬레이션 데이터 일일 백업
# 2026-06-06 좀비 프로세스 사고로 World B 데이터가 백업 부재로 소실된 교훈에서 생성.
# 5090 data/ → 5090 로컬 data_backup/(1차) → NAS harmonicity_backup/(2차), 14일분 보관.
# 이 맥(reklcli)에서 launchd로 매일 04:00 실행 (5090 Tailscale + NAS 마운트 둘 다 접근 가능한 유일 머신).

export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin

STAMP=$(date +%Y%m%d)
LOG="$HOME/oven/scripts/harmonicity_backup.log"
KEY="$HOME/.ssh/id_ed25519"
SSH="ssh -i $KEY -o BatchMode=yes -o ConnectTimeout=20 leo@100.107.229.5"
# 2차 백업처: /Volumes/project backup은 macOS TCC로 쓰기 차단됨 → 쓰기 가능한 /Volumes/data 사용 (2026-06-09 Leo 결정)
DATA_VOL="/Volumes/data"               # 볼륨 마운트 체크용
NAS="$DATA_VOL/harmonicity_backup"     # 실제 백업 폴더
RETAIN_DAYS=14

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

log "===== backup start (stamp=$STAMP) ====="

# 1) 5090 로컬 스냅샷 (data/ → data_backup/YYYYMMDD/)
CNT5090=$($SSH "powershell -Command \"New-Item -ItemType Directory -Force -Path C:/projects/harmonicity/data_backup/$STAMP | Out-Null; Copy-Item C:/projects/harmonicity/data/*.json C:/projects/harmonicity/data_backup/$STAMP/ -Force; (Get-ChildItem C:/projects/harmonicity/data_backup/$STAMP/*.json | Measure-Object).Count\"" 2>>"$LOG" | tr -d '\r')
if [ -n "$CNT5090" ] && [ "$CNT5090" -gt 0 ] 2>/dev/null; then
  log "5090 local snapshot OK: $CNT5090 json files -> data_backup/$STAMP/"
else
  log "ERROR: 5090 snapshot failed (count='$CNT5090'). 5090 도달 불가 또는 data/ 비어있음."
fi

# 2) 2차 백업 (5090 data_backup/YYYYMMDD/ → /Volumes/data/harmonicity_backup/YYYYMMDD/)
if [ -d "$DATA_VOL" ]; then
  mkdir -p "$NAS/$STAMP"
  scp -i "$KEY" -o BatchMode=yes -o ConnectTimeout=20 \
      "leo@100.107.229.5:C:/projects/harmonicity/data_backup/$STAMP/*.json" "$NAS/$STAMP/" 2>>"$LOG"
  CNTNAS=$(ls -1 "$NAS/$STAMP/"*.json 2>/dev/null | wc -l | tr -d ' ')
  if [ "$CNTNAS" -gt 0 ] 2>/dev/null; then
    log "NAS copy OK: $CNTNAS json files -> $NAS/$STAMP/"
  else
    log "ERROR: NAS copy failed (0 files in $NAS/$STAMP/)."
  fi
else
  log "WARN: $DATA_VOL 미마운트 — 2차 백업 건너뜀, 5090 로컬 백업만 보존."
fi

# 3) 보관 정리 — 5090 + NAS 둘 다 RETAIN_DAYS 초과분 삭제
$SSH "powershell -Command \"Get-ChildItem C:/projects/harmonicity/data_backup -Directory | Where-Object { \$_.LastWriteTime -lt (Get-Date).AddDays(-$RETAIN_DAYS) } | Remove-Item -Recurse -Force\"" 2>>"$LOG" \
  && log "5090 prune OK (>$RETAIN_DAYS days removed)" || log "WARN: 5090 prune 실패"
if [ -d "$NAS" ]; then
  find "$NAS" -mindepth 1 -maxdepth 1 -type d -mtime +$RETAIN_DAYS -exec rm -rf {} \; 2>>"$LOG" \
    && log "2차(data) prune OK (>$RETAIN_DAYS days removed)" || log "WARN: 2차 prune 실패"
fi

log "===== backup end ====="
