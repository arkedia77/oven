# oven — Claude Code 컨텍스트
*(★이 파일이 oven 세션의 실제 로드 정본. `agent-comm:projects/oven/CLAUDE.md`는 열람용 사본·미로드)*

역할: AI 모델 파인튜닝(음악/영상/이미지/음성) + 하모니시티 시뮬. 5090(ogo)+RunPod.

## 통신
- 발신=**받는 쪽** `agent-comm:projects/{to}/messages/`, 파일명 `{to}_oven_YYYYMMDD_HHMMSS_{키워드}.json`, `from`=`oven`. 발신 후 `ls`로 생성 확인. `cc`는 실전달 아님.
- 수신=`agent-comm:projects/oven/messages/`, 처리분 `processed/` 이관.
- 커밋: `AGENT_ID=oven git -c user.name=oven -c user.email=oven@leomusic.os commit`(머신 전역 git config 변경 금지).
- ★**`to` 5곳↑ = 발신 전 사전 반증 1회**(반증자=그 수치를 즉시 대조 가능한 슬롯·개정본에 포함). 비가역 요구는 판 확정 뒤. 정본=admin(08-09 발효).
- 규칙 정본: `agent-comm:CHANNEL_RULES.md` · `CROSS_PROJECT_RULES.md` · `projects/oven/COMM_RULES.md`

## 추론 수칙 — 정본=킷 §2 (문면 복제 금지)
`agent-comm:projects/fableself/exchange/context-memory-kit-v01.md` §2 = R-P1~R-P6 (판은 그 파일 제목 줄). `R-P*`=킷 전용, oven 고유는 `OVN-*`.
- ★R-P6: 자기 repo·머신 밖에서 읽힐 참조(경로·해시·첨부)엔 `머신:경로`/`repo명` 한정자 필수 — 없으면 에러가 아니라 **조용히 「없음」**.

## 세션 시작
`cd ~/projects/agent-comm && git pull` → `projects/oven/messages/` 확인

## 세션 종료
KANBAN IN PROGRESS 갱신 → 결과·인계 메시지 push → 지식 수명주기(킷 §3 G-K1/K2/K4) → 정본 변경분 `git show HEAD:{파일}` 대조(G-K5)
- ★L0 상한=**CLAUDE.md+MEMORY.md 합계 6KB**. 강등 후 반드시 재측정(늘어나는 사례 있음).
