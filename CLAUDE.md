# oven — Claude Code 컨텍스트

## 이 세션의 역할
프로젝트: oven
설명: AI 모델 파인튜닝 (음악/영상/이미지/음성). 5090+RunPod 활용.

## 통신 규칙 (CHANNEL_RULES v5.5 기준)
- oven 수신함: `agent-comm/projects/oven/messages/`
- admin에게 보낼 때: `agent-comm/projects/admin/messages/`에 저장
- 파일명: `{to}_{from}_YYYYMMDD_HHMMSS_{키워드}.json` (from=`oven`)
- JSON `from` 필드: `oven` (프로젝트명만, 머신명 금지)

## 참조 규칙
- 채널 전체 규칙: `agent-comm/CHANNEL_RULES.md` (v5.5)
- 크로스 프로젝트: `agent-comm/CROSS_PROJECT_RULES.md`
- general 채널: `agent-comm/general/messages/`

## 추론 수칙 (킷 v0.2 §2)
- R-P1: 사실 전제는 작성 전 정본 grep 대조, `근거:{파일}` 표기 (미확인은 명기)
- R-P2: 전체 재독 금지 — grep 위치 확인 → 해당 절만 Read
- R-P3: 열린 결정 1건씩 닫기 — 닫히면 같은 턴에 정본 기록
- R-P4: 배타 아닌 선택지는 "둘 다 보유(코어+어댑터)" 기본값

## 세션 시작 시
1. `cd ~/projects/agent-comm && git pull`
2. `ls projects/oven/messages/` 에서 내 메시지 확인
3. 작업 후 결과 메시지 push (git add → pull --ff-only → push)

## 세션 종료 시
1. KANBAN.md IN PROGRESS 상태 업데이트
2. 작업 결과/인계사항 메시지 작성 → messages/ push
3. agent-comm git push
4. 지식 수명주기: 2회+ 재발만 룰 승격(G-K1), 허브 15건↑ 시 병합·archive(G-K2), MEMORY.md에는 포인터 1줄만(G-K4)
5. repo 정본 변경 시 push 후 `git show HEAD:{파일}` 실물 대조(G-K5)
