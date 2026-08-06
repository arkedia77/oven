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

## 추론 수칙 — ★정본=킷 §2 (여기는 색인. 문면 복제 금지)
- **정본**: `agent-comm:projects/fableself/exchange/context-memory-kit-v01.md` §2 — 현행 판은 그 파일 제목 줄이 정본(파일명의 `-v01`은 개설 당시 이름). 개정은 정본에서만.
- 색인(판정 근거로 인용하지 말 것 — 인용은 정본 문면으로):
  R-P1 전제 감사(작성 전 grep·`근거:{파일}`) / R-P2 부분 Read / R-P3 결정 하나씩 닫기 / R-P4 코어+어댑터 / R-P5 시각 실측 / **R-P6 경계 넘는 참조는 한정자 필수**
- ★**R-P6** — 자기 머신·자기 repo 밖에서 읽힐 참조(경로·커밋 해시·첨부)는 `머신:경로` 또는 `repo명` 한정자 없이 적지 않는다. 상대경로는 **읽는 쪽 기준으로 해석돼 에러가 아니라 「없음」**을 만든다(그래서 양쪽 다 모른다). 예: `pipeline/x.py` ❌ → `reklcli:~/oven/pipeline/x.py` ✅
- `R-P*` 번호 공간은 **킷 전용**. oven 고유 규율이 필요하면 `OVN-*` 접두를 쓴다.
- ⚠이 파일이 **oven 세션이 실제로 로드하는 CLAUDE.md**다(`reklcli:~/oven/CLAUDE.md`). `agent-comm:projects/oven/CLAUDE.md`는 타 슬롯 열람용 사본이며 로드되지 않는다.

## 세션 시작 시
1. `cd ~/projects/agent-comm && git pull`
2. `ls projects/oven/messages/` 에서 내 메시지 확인
3. 작업 후 결과 메시지 push (git add → pull --ff-only → push)

## 세션 종료 시
1. KANBAN.md IN PROGRESS 상태 업데이트
2. 작업 결과/인계사항 메시지 작성 → messages/ push
3. agent-comm git push
4. 지식 수명주기(정본=킷 §3): 2회+ 재발만 룰 승격(G-K1), 허브 15건↑ 시 병합·archive(G-K2), MEMORY.md에는 포인터 1줄만(G-K4)
5. repo 정본 변경 시 push 후 `git show HEAD:{파일}` 실물 대조(G-K5)
