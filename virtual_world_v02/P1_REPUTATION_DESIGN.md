# P1: 평판 & 정보 비대칭 시스템 설계

## 목표
현재 엔진의 양자 관계(warmth/trust/tension)에 **삼자 사회 역학**을 추가:
- 캐릭터 A가 B에 대해 갖는 **평판**(reputation)은 직접 경험 + 타인으로부터 들은 이야기로 형성
- **정보 비대칭**: 비밀, 관찰, 소문이 불균등하게 퍼지면서 갈등/동맹의 연료가 됨

## 1. 평판 시스템 (`village/systems/reputation.py`)

### 데이터 구조
```python
# reputation[observer_id][target_id] → ReputationEntry
@dataclass
class ReputationEntry:
    competence: float = 0.5    # 능력/신뢰성
    integrity: float = 0.5     # 도덕성/정직함
    warmth: float = 0.5        # 사교성/친절함
    influence: float = 0.5     # 사회적 영향력
    confidence: float = 0.3    # 평판 확신도 (정보량에 비례)
    last_updated_day: int = 0
```

### 평판 vs 관계 구분
| 속성 | 관계 (relationship) | 평판 (reputation) |
|------|-------|------|
| 범위 | 양자간 (A↔B) | 삼자 (A가 B에 대해 생각) |
| 원천 | 직접 대화 경험 | 직접 + 간접(소문) |
| 용도 | 대화 톤/delta 계산 | 동맹 선택, 정보 공유 결정 |
| 대칭성 | 비대칭 가능 | 항상 비대칭 (A→B ≠ B→A) |

### 평판 업데이트 트리거
1. **직접 상호작용 후** (appraisal 결과에서 파생):
   - 긍정 appraisal → competence/warmth 소폭 상승
   - 갈등 → integrity/warmth 소폭 하락
   - confidence 0.05 상승 (최대 1.0)

2. **간접 정보 (소문) 수신 시**:
   - 전달자의 integrity 평판이 높을수록 영향력↑
   - 기존 평판과 불일치할수록 변화량↓ (확증편향)
   - confidence 0.02 상승 (직접보다 약함)

3. **관찰 (목격)**:
   - 비밀 행위 목격 → integrity 급락 가능
   - confidence 0.08 상승 (직접 증거)

### 평판 감쇠
- 매일 confidence *= 0.99 (기억 희미해짐)
- 장기 미접촉 시 평판이 default(0.5)로 회귀

## 2. 정보 비대칭 시스템 (`village/systems/information.py`)

### 데이터 구조
```python
@dataclass
class InfoItem:
    id: str                    # 고유 식별자
    category: str              # "secret" | "observation" | "rumor" | "fact"
    subject: str               # 정보 대상 캐릭터 ID
    content: str               # 정보 내용 (1문장)
    truth_value: float         # 0.0 (거짓) ~ 1.0 (사실)
    sensitivity: float         # 0.0 (무해) ~ 1.0 (치명적)
    origin_day: int            # 생성일
    source: str                # 최초 출처 ("system" | char_id)

# knowledge[char_id] → set[info_id]
# 각 캐릭터가 알고 있는 정보 목록
```

### 초기 정보 시딩
definitions.py의 `secret` 필드를 InfoItem으로 변환:
- 본인만 알고 있는 정보로 시작
- 일부는 "관찰 가능" (schedule 이탈 등)

예시:
```python
InfoItem(
    id="secret_tae_sik_bribe",
    category="secret",
    subject="tae_sik",
    content="하이퍼테크에서 월 500만원 컨설팅비를 받고 있다",
    truth_value=1.0,
    sensitivity=0.9,
    origin_day=0,
    source="system",
)
```

### 정보 전파 메커니즘

#### A. 소문 전파 (대화 중)
appraisal 엔진에 새 필드 추가:
```json
{
  ...existing fields...,
  "gossip": {
    "shared": true/false,
    "about": "char_id or null",
    "content_hint": "무엇에 대한 이야기인지 1문장",
    "valence": "긍정/부정/중립"
  }
}
```

전파 조건:
- trust(A→B) > 0.6 일 때만 민감 정보 공유 가능
- sensitivity > 0.7 정보는 trust > 0.8 필요
- 전파 시 truth_value *= 0.9 (전화기 효과)
- 전달자 integrity 평판이 낮으면 수신자가 할인 적용

#### B. 관찰 (encounter.py 확장)
- 같은 장소에 있으면 서로의 행동을 "관찰"
- 특정 조건에서 비밀 노출:
  - 비밀 관련 장소에 있을 때 (태식이 council이 아닌 곳에 있으면)
  - 비밀 관련 인물과 대화할 때 목격
  - 확률적 노출: sensitivity * 0.02 per tick (같은 장소일 때)

#### C. 직접 고백 (대화 중)
- trust > 0.8 + affection > 0.6 → 비밀 공유 확률 상승
- goal 관련 비밀은 progress가 높을수록 공유 경향
  (예: 하연의 "아빠에게 AI 친구 고백" goal progress 올라가면 고백 가능)

## 3. 기존 시스템 수정 사항

### conversation.py
- `build_conversation_prompt`에 상대방 평판 정보 추가
- "당신이 알고 있는 제3자 이야기" 컨텍스트 추가

### appraisal.py
- 출력 스키마에 `gossip` 필드 추가
- `reputation_update` 필드 추가 (관찰자 시점의 평판 변화)

### encounter.py
- 평판이 낮은 인물은 회피 경향 (priority 감소)
- 소문 대상 인물은 호기심으로 priority 약간 증가

### main.py (_end_of_day 확장)
- 일일 평판 감쇠
- 정보 확산 요약 로그

## 4. 구현 순서

| 단계 | 작업 | 의존성 |
|------|------|--------|
| 4.1 | `reputation.py` — 데이터 + 업데이트 로직 | 없음 |
| 4.2 | `information.py` — 데이터 + 초기 시딩 | 없음 |
| 4.3 | `persistence/` — reputation/info 저장/로드 | 4.1, 4.2 |
| 4.4 | `appraisal.py` 스키마 확장 (gossip + rep_update) | 4.1, 4.2 |
| 4.5 | `conversation.py` 프롬프트 확장 | 4.1, 4.2 |
| 4.6 | `encounter.py` 우선순위 수정 | 4.1 |
| 4.7 | `main.py` 루프 통합 | 전부 |
| 4.8 | 테스트 + 5090 배포 | 4.7 |

## 5. 포화 방지 효과 기대

현재 문제: 관계가 양자간이라 "A-B가 좋으면 계속 좋음"
P1 효과:
- C에 대한 소문이 A-B 관계에 영향: "B가 C에게 비밀을 발설했다" → A→B trust 하락
- 평판이 낮은 인물과의 교류가 자기 평판에 영향 (연좌 효과)
- 정보 불일치로 인한 갈등: A가 모르는 걸 B가 알 때 오해 발생

## 6. LLM 토큰 비용 추정

- appraisal 스키마 확장: +50 tokens/call (gossip 필드)
- conversation prompt 확장: +100 tokens (평판/정보 컨텍스트)
- 총 증가: 대화당 ~150 tokens → 하루(24틱) 기존 대비 +10~15%
- 별도 LLM 호출 없음 (기존 appraisal에 통합)
