# 하모니 시티 #02 Ecosystem — 가상 마을 시뮬레이션

## 개요
Gemma 4 26B 기반 10인 사회 시뮬레이션. #01 Genesis의 구조적 결함(tension 단조증가, 양성피드백, 에스컬레이션)을 해결한 **생태계 자기조절** 설계.

## #01 → #02 주요 변경점

| 항목 | #01 Genesis | #02 Ecosystem |
|------|-------------|---------------|
| tension 비율 | +0.1/-0.02 (5:1) | +0.05/-0.03 (1.67:1) + 항상성 |
| 만남 우선순위 | tension × 2.0 | salience × 1.5 + 다양성 보너스 |
| 프롬프트 | "반박해, 거짓말도 가능" | "타협, 양보, 유머도 자연스러운 선택" |
| 신념 | 고정 | conviction 기반 점진적 변화 |
| autonomy | 복원 불가 (전원 0.0) | 독백+혼자시간+갈등 3경로 복원 |
| 에너지 | 없음 | 캐릭터별 일일 예산 (2.0-3.5) |
| 피로 | 없음 | 3회 연속 갈등 → 5틱 쿨다운 |
| 장소 | 수동적 배경 | warmth/friction 토큰 축적 |
| 이벤트 | 미작동 | 6가지 조건 기반 자동 발화 |
| 목표 | 고정 (progress 안 변함) | 키워드 기반 자동 진행/후퇴 |
| 틱 간격 | 150초 | 200초 (25% 연산 절감) |

## 실행

```bash
cd ~/oven/virtual_world_v02
python3 -u run_village.py

# 백그라운드
nohup python3 -u run_village.py > village_output.log 2>&1 &

# 이어서 실행 (자동 복구)
python3 -u run_village.py
```

## 핵심 시스템

### 1. 항상성 (Homeostasis)
마을 평균 tension 목표: 0.4
- 평균 > 0.5: tension 상승 ½감쇠, 하강 1.5배 촉진
- 평균 < 0.3: tension 상승 1.5배, 하강 ½감쇠
- warmth > 0.7이면 tension 상한 제한 (warmth=1.0 → max tension=0.3)

### 2. 사회적 에너지
캐릭터별 일일 에너지 예산 (내향적 2.0 ~ 외향적 3.5)
- 대화: -0.5 (고긴장 시 추가 -0.3)
- 독백: -0.1
- 에너지 < 0.5: 대화 불가 → residential 이동

### 3. 피로 모델
동일인과 3회 연속 고긴장(tension > 0.6) 대화 시:
- salience -0.3, 5틱 쿨다운 (회피)

### 4. 만남 선택 (encounter priority)
```
score = 0.5 (기본)
  + salience × 1.5
  + needs_alignment × 1.0
  + goal_relevance (1.0)
  + diversity_bonus (5일+ 미대화: days × 0.3, max 2.0)
  + novelty_bonus (3회 미만: +2.0)
  - fatigue (-10.0 if cooldown)
  - low_energy (-5.0)
  + random(0, 0.5)
```

### 5. 신념 침식
belief별 conviction (0.1-0.9) 보유
- 대화에서 입장 변화 감지 시: belief ±0.02 × (1-conviction)
- conviction 자체도 -0.005씩 서서히 감소

### 6. 자생 이벤트
| 조건 | 이벤트 |
|------|--------|
| 욕구 < 0.1 × 3일 | 개인 위기 |
| tension > 0.8 × 5일 | 대결 (tension -0.25) |
| 마을 tension < 0.2 × 3일 | 정체 타파 |
| 5일간 3명 미만 교류 | 고립 브릿지 |
| 목표 progress > 0.9 | 목표 달성 임박 |

### 7. 10일 회고
10일마다 LLM 회고 세션 → persona_addendum 업데이트

## 캐릭터 10인
(#01과 동일 — VIRTUAL_WORLD_GUIDE.md of v01 참조)

---

## 컨트롤 파라미터 레퍼런스

### A. 인구 규모

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| 캐릭터 수 | 10명 | definitions.py 전체 | 관계 쌍 O(n²), LLM 호출 비례 증가 |
| 관계 쌍 | 45 (10C2) | 자동 생성 | 메모리/저장 비례 |
| 장소 수 | 7개 | locations.py | 만남 확률 분산에 영향 |
| 장소 수용량 | 3~10 | locations.py 4-45 | 작으면 만남 집중, 크면 분산 |

장소별 수용량: 광장(10), 카페(4), 커뮤니티센터(8), 시의회(4), 연구실(3), 스튜디오(3), 주거(10)

### B. 시간 스케일

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| TICK_SECONDS | 200 | config.py:10 | 줄이면 빈번한 LLM 호출, 늘리면 느린 진행 |
| TICKS_PER_DAY | 24 | config.py:11 | 하루 = 24틱 = 실시간 80분 |
| VILLAGE_HOURS_PER_TICK | 1 | config.py:12 | 1틱 = 마을 1시간 |
| 활성 시간대 | 06:00~23:00 | time_system.py 4-10 | late_night엔 독백/만남 없음 |

시간대: early_morning(6-8), morning(8-12), lunch(12-14), afternoon(14-18), evening(18-21), night(21-23), late_night(23-6)

### C. 대화 깊이

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| EXCHANGES_PER_CONVERSATION | 3 | config.py:14 | 대화 왕복 수. 늘리면 더 깊지만 비용 증가 |
| MAX_TOKENS_CONVERSATION | 2048 | config.py:15 | LLM 응답 길이 |
| MAX_TOKENS_REFLECTION | 2048 | config.py:16 | 반성 응답 길이 |
| MAX_TOKENS_MONOLOGUE | 1024 | config.py:17 | 독백 응답 길이 |
| MAX_TOKENS_RETROSPECTIVE | 1024 | config.py:18 | 10일 회고 응답 길이 |
| TEMPERATURE | 0.85 | config.py:19 | 낮추면 예측 가능, 높이면 창의적 |
| MAX_CONVERSATIONS_PER_TICK | 2 | config.py:24 | 틱당 대화 쌍 수 |
| SOLO_MONOLOGUES_PER_TICK | 1 | config.py:25 | 틱당 독백 캐릭터 수 |

### D. 메모리 용량

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| MAX_EPISODES | 50 | config.py:21 | 캐릭터당 보존 에피소드 수 (초과 시 FIFO) |
| working_memory | 5 | state.py:164 | LLM에 전달되는 최근 기억 수 |
| get_recent_episodes | n=10 | episodic.py:26 | 최근 에피소드 검색 기본 깊이 |
| get_episodes_about | n=3 | episodic.py:38 | 상대방 관련 에피소드 검색 깊이 |
| 에피소드 검색 풀 | 50 | episodic.py:39 | 최근 50개 중에서 필터 |

### E. 시스템 튜닝 (욕구/신념/관계 변화율)

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| 욕구 감소율 | -0.005/tick | state.py:76 | 빠르면 위기 빈번, 느리면 안정 |
| 대화 소속감 회복 | +0.05 | state.py:82 | 긍정 대화 시 belonging 회복량 |
| 대화 인정 회복 | +0.04 | state.py:83 | 긍정 대화 시 recognition 회복량 |
| 독백 자율 회복 | +0.06 | state.py:101 | 독백 시 autonomy 회복량 |
| 혼자 시간 자율 | +0.02 | state.py:105 | residential 체류 시 autonomy |
| 신념 이동율 | ±0.02×(1-conviction) | state.py:116 | conviction 높으면 변화 둔감 |
| conviction 감소 | -0.005/shift | state.py:119 | conviction이 서서히 열림 |
| warmth 변화 | ±0.04×dampening | conversation.py:193-196 | 긍정/부정 대화 시 |
| trust 변화 | +0.03/-0.04×dampening | conversation.py:194-197 | 신뢰는 비대칭(깨지기 쉬움) |
| tension 변화 | +0.05×inc_mult/-0.03×dec_mult | conversation.py:200-202 | 항상성 곱수 적용 |
| affection 변화 | +0.08(애정어)/+0.02(긍정)/-0.02 | conversation.py:208-212 | 애정은 큰 폭 변동 |
| dampening | 0.5 (>20회 교류) | conversation.py:190 | 20회 이상 만나면 변화폭 반감 |
| 항상성 목표 tension | 0.4 | homeostasis.py:3 | 마을 전체 긴장 목표값 |
| tension 자연 감소 | -0.005/tick | homeostasis.py:37 | 매 틱 자연 하락 |
| salience 자연 감소 | -0.01/tick | homeostasis.py:38 | 관심도 자연 하락 |

### F. 에너지 예산

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| 일일 에너지 (내향) | 2.0 (서진, 넥서스) | social_energy.py:4-5 | 하루 대화 가능 횟수 결정 |
| 일일 에너지 (중간) | 2.5 (준호, 상우, 루나) | social_energy.py:6-9 | |
| 일일 에너지 (외향) | 3.0-3.5 (민아, 태식, 하연 등) | social_energy.py:8-13 | |
| CONVERSATION_COST | 0.5 | social_energy.py:17 | 대화 1회 소모 |
| MONOLOGUE_COST | 0.1 | social_energy.py:18 | 독백 1회 소모 |
| HIGH_TENSION_BONUS_COST | +0.3 (tension>0.6) | social_energy.py:19 | 고긴장 대화 추가 비용 |
| MIN_ENERGY_FOR_CONVERSATION | 0.5 | social_energy.py:21 | 이하면 대화 불가 |

### G. 이벤트 트리거

| 이벤트 | 조건 | 임계값 | 파일:라인 | 효과 |
|--------|------|--------|-----------|------|
| personal_crisis | need < 0.15 × 3일 연속 | 0.15, 3일 | events.py:36-39 | 위기 이벤트 발동 |
| confrontation | tension ≥ 0.8, 5일 미교류 | 0.8, 5일 | events.py:50-57 | 대결 후 tension -0.25 |
| stagnation_breaker | 마을 평균 tension < 0.2 × 3일 | 0.2, 3일 | events.py:72-78 | 정체 타파 이벤트 |
| isolation_bridge | 3일 이상, 고유 접촉 < 2명 | day>3, <2명 | events.py:98 | 고립 해소 |
| goal_culmination | goal progress ≥ 0.9 | 0.9 | events.py:111 | 목표 달성 임박 |

### H. 데이터 보존

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| 히스토리 윈도우 | 60일 | main.py:145-157 | 욕구/신념/관계 히스토리 보존 기간 |
| 대화 로그 | 무제한 (일별 폴더) | save_load.py | 저장용량에 직결 |
| 에피소드 수 | 50/캐릭터 | config.py:21 | 오래된 기억 자동 삭제 |
| 커뮤니티 이벤트 | 20개 | state.py | FIFO |
| working_memory | 최근 5개 | state.py:164 | to_dict 시 직렬화 |

### I. 회고 시스템

| 파라미터 | 현재값 | 파일:라인 | 변경 효과 |
|----------|--------|-----------|-----------|
| RETROSPECTIVE_INTERVAL_DAYS | 10 | config.py:27 | 회고 빈도 (줄이면 더 자주 자기성찰) |
| 욕구 중요도 적응 주기 | 10일 | main.py:184 | need_importance 가중치 재조정 주기 |
| persona_addendum 길이 | 200자 | main.py:210 | 회고 결과 페르소나 업데이트 길이 |
| 욕구 적응 고평균 임계 | >0.7 → ×0.9 | state.py:128-129 | 충분한 욕구는 중요도 감소 |
| 욕구 적응 저평균 임계 | <0.3 → ×1.1 | state.py:130-131 | 부족한 욕구는 중요도 증가 |

---

## 규모별 리소스 산정

### 현재 시스템 사용량 (10명 기준, 5090 RTX 5090)

| 리소스 | 사용량 | 설명 |
|--------|--------|------|
| VRAM | ~29GB / 48GB | Gemma 4 26B Q8_0 (26.9GB) + 컨텍스트 (~2GB) |
| RAM | ~34GB / 68GB | llama-server 프로세스 (~34GB) + 시뮬레이션 (<50MB) |
| LLM 호출/일 | ~165-195회 | ~11 calls/tick × ~15 활성 틱 + 종일 이벤트 |
| 틱당 LLM 시간 | ~18초 | 대화 2건(각 ~6s) + 독백 1건(~3s) + 반영 2건(~3s) |
| 틱 활용률 | 9% | 18s / 200s (91% 유휴) |
| 저장용량/일 | ~0.8-1MB | 대화 로그 + 캐릭터 상태 + 히스토리 |
| 저장용량/10일 | ~9MB | 히스토리 JSON 포함 |

### LLM 호출 내역 (틱당)

| 호출 유형 | 횟수 | 토큰 | 비용 시간 |
|-----------|------|------|-----------|
| 대화 (3왕복) | 2쌍 × 6회 = ~12 | 2048/회 | ~12s |
| 반성 | 2쌍 × 2회 = ~4 | 2048/회 | ~4s |
| 독백 | ~1회 | 1024/회 | ~1.5s |
| 이벤트 | 간헐적 | 가변 | ~0.5s avg |
| **합계** | **~11-17** | | **~18s** |

### 스케일링 테이블

| 규모 | 캐릭터 | 관계 쌍 | 대화/틱 | LLM 호출/일 | 틱당 LLM 시간 | 활용률 | 저장/일 | 아키텍처 변경 |
|------|--------|---------|---------|------------|--------------|--------|---------|-------------|
| **현재** | 10 | 45 | 2 | ~195 | ~18s | 9% | ~1MB | 없음 |
| **중형** | 25 | 300 | 5 | ~465 | ~51s | 25% | ~2MB | MAX_CONV 조정만 |
| **대형** | 50 | 1,225 | 8 | ~750 | ~83s | 41% | ~8MB | encounter 최적화, 관계 pruning |
| **초대형** | 100 | 4,950 | 12 | ~1,125 | ~124s | 62% | ~25MB | TICK_SECONDS 300+, DB 백엔드 |
| **대규모** | 500 | 124,750 | 20+ | ~3,000+ | >200s | 초과 | ~200MB | 병렬 추론, 소셜 그래프 분할, DB 필수 |

### 스케일링 병목 분석

- **25명**: 현재 아키텍처로 가능. MAX_CONVERSATIONS_PER_TICK을 5로, TICK_SECONDS 유지
- **50명**: encounter 선택 O(n²) → O(n log n) 최적화 필요. 관계 중 salience < 0.1은 비활성 처리
- **100명**: 틱 시간 내 LLM 처리 불가 → TICK_SECONDS 300+. 대화 로그 JSON → SQLite 전환 권장
- **500명**: 단일 GPU 한계 초과 → llama-server 2+ 인스턴스 병렬, 소셜 그래프를 커뮤니티별 분할 필수

### 하드웨어 요구사항

| 규모 | GPU | RAM | 저장/월 |
|------|-----|-----|---------|
| 10명 | RTX 5090 1장 (48GB) | 64GB | ~30MB |
| 25명 | RTX 5090 1장 | 64GB | ~60MB |
| 50명 | RTX 5090 1장 | 128GB | ~240MB |
| 100명 | RTX 5090 1장 (TICK 300s+) | 128GB | ~750MB |
| 500명 | RTX 5090 2장 또는 A100 80GB | 256GB | ~6GB |

### 도메인 응용 가능성

현재 아키텍처는 **needs/beliefs/relationships/events** 4축으로 설계. 4개 파일만 교체하면 도메인 전환 가능:
- `definitions.py` — 캐릭터/에이전트 정의
- `prompts.py` — LLM 프롬프트
- `state.py` — 상태 차원 (needs → 도메인 특화 차원)
- `events.py` — 이벤트 트리거 조건

| 도메인 | needs 대체 | beliefs 대체 | events 대체 | 특수 시스템 |
|--------|-----------|-------------|-------------|-----------|
| **기업 시뮬레이션** | 성장욕/워라밸/보상만족/지위 | 기업문화/혁신성/안정성 | 인사이동/분기실적/부서갈등 | 조직도 계층, 부서간 로직 |
| **역사 재현** | 권력/안전/명예/동맹 | 이념/종교/민족정체성 | 전쟁/조약/혁명/기근 | 사망/세대교체, 외부 이벤트 주입 |
| **그룹 치료** | 소속감/자기효능/안전/신뢰 | 인지왜곡 패턴 5가지 | 위기/돌파/퇴행/종결 | 치료사 특수 역할, 진도 추적 |
| **교육 시나리오** | 호기심/숙달감/소속/인정 | 학습관/협동관/공정관 | 시험/프로젝트/대회/갈등 | 지식 상태 추적, 교사 역할 |
| **정치 시뮬레이션** | 권력/정당성/안전/인기 | 이념 스펙트럼 5축 | 선거/스캔들/위기/동맹 | 여론조사, 미디어 시스템 |

---

## 파일 구조
```
virtual_world_v02/
├── run_village.py          # 실행 엔트리포인트
├── village/
│   ├── config.py           # API, 타이밍, 상수
│   ├── main.py             # 메인 시뮬레이션 루프
│   ├── characters/
│   │   ├── definitions.py  # 10인 정의
│   │   └── state.py        # 상태 (convictions, need_importance 추가)
│   ├── world/
│   │   ├── locations.py    # 7개 장소
│   │   ├── time_system.py  # 시간 압축
│   │   └── state.py        # 월드 상태
│   ├── interaction/
│   │   ├── encounter.py    # salience+다양성 기반 만남 선택
│   │   ├── conversation.py # 대화+반영 (항상성/에너지/피로 통합)
│   │   └── prompts.py      # 균형화된 프롬프트
│   ├── memory/
│   │   ├── episodic.py     # L2 삽화기억
│   │   └── core.py         # L3 핵심기억
│   ├── systems/            # 🆕 #02 신규 시스템
│   │   ├── homeostasis.py  # 항상성 컨트롤러
│   │   ├── social_energy.py # 사회적 에너지 예산
│   │   ├── location_atmosphere.py # 장소 분위기
│   │   └── events.py       # 자생 이벤트
│   ├── engine/
│   │   └── llm.py          # Gemma 4 API
│   └── persistence/
│       └── save_load.py    # 저장/복구 (need_history, atmosphere 추가)
└── data/
    ├── world_state.json
    ├── characters/
    ├── memories/
    ├── conversations/
    ├── relationships.json
    ├── need_history.json   # 🆕
    └── atmosphere.json     # 🆕
```
