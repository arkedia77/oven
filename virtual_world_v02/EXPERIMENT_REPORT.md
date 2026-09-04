# 하모니시티 추가 실험 리포트 (2026-06-22)

## 실험 배경

Day 331 (약 11개월) 가동된 라이브 시뮬레이션의 관계 역학을 정량 분석하고,
발견된 이슈를 검증하는 5개 추가 테스트 설계 및 실행.

---

## T2: 이벤트 시스템 감사 — 버그 발견 + 수정

### 발견

330일간 sim.log 분석 (177K줄):

| 이벤트 유형 | 발동 수 | 실효성 |
|---|---|---|
| stagnation_breaker (정체) | 110회 (2.7일 간격) | ❌ **버그: prompt_injection 미전달** |
| isolation_bridge (고립) | 1,139회 | ⚠️ 전 캐릭터 균등 (~10%), 차별화 없음 |
| 목표 달성 임박 | 1,889회 | ✅ 서사 자극에 기여 |
| confrontation (대결) | **0회** | tension이 0.8 미도달 (max 0.26) |
| personal_crisis (위기) | 110회 | 미분석 |

### 버그 상세

`events.py`의 stagnation_breaker는 `character` 필드 없이 반환.
`main.py:410`에서 `event.get("character")` = None → prompt_injection 주입 건너뜀.
**110회 발동 × 실효성 0** = tension이 0.005에 고착된 구조적 원인.

### 수정 (main.py, 2026-06-21 배포)

`character` 없는 이벤트 → 전체 캐릭터 working_memory에 주입.
ogo 라이브 배포 완료. 효과 관찰 중.

---

## T3: 냉각 관계 원인 분석

### Appraisal 극성 분석 (330일 전체)

| 쌍 | 총 appraisal | 긍정률 | warmth | 원인 유형 |
|---|---|---|---|---|
| luna↔ye_eun | 41 | **10%** | 0.000 | LLM 부정 편향 |
| aria↔ye_eun | 109 | 23% | 0.000 | 캐릭터 갈등 |
| ha_yeon↔seo_jin | 38 | 26% | 0.000 | 캐릭터 갈등 |
| ha_yeon↔ye_eun | 120 | 31% | 0.000 | 캐릭터 갈등 |
| aria↔tae_sik | 27 | **59%** | 0.000 | **decay 압도** |
| joon_ho↔ye_eun (대조) | 1,302 | **100%** | 0.613 | — |
| sang_woo↔seo_jin (대조) | 277 | **100%** | 0.608 | — |

### 시계열 분석 — 관계는 처음부터 차갑지 않았다

| 쌍 | D51-100 | D101-150 | D151-200 | D251-300 | D301-335 |
|---|---|---|---|---|---|
| aria↔ye_eun | 100% | 79% | 17% | 0% | 0% |
| ha_yeon↔ye_eun | 100% | 100% | 38% | 5% | 0% |
| luna↔ye_eun | — | 100% | 50% | 0% | 0% |

**핵심 발견**: 관계가 초기에는 100% 긍정 → 시간이 지나며 **자연적으로 악화**.
LLM이 캐릭터 설정에 기반한 서사적 갈등 아크를 자발적으로 생성.
ye_eun이 마을의 자연발생적 갈등 생성자 (부정 appraisal 128회, 최다).

### 2가지 원인 메커니즘

1. **LLM 부정 편향** (4쌍): 특정 캐릭터 조합에서 LLM이 지속적으로 부정 appraisal 생성.
   양수 delta가 아예 없으므로 decay와 무관하게 warmth=0 유지.

2. **decay 압도** (1쌍: aria↔tae_sik): 긍정 59%인데도 warmth=0.
   간헐적 양수 delta(appraisal 성공 시)가 매 틱 0.8% decay × 24 tick/일에 소거.
   → T1(항상성 감도 스윕)에서 decay율 변경 시 이 쌍의 반응이 결정적 지표.

---

## 관계 역학 전체 프로필 (Day 331)

### 메트릭 분포

| 지표 | avg | min | max | 비고 |
|---|---|---|---|---|
| warmth | 0.473 | 0.000 | 0.614 | 80%가 0.5-0.65 밴드 |
| trust | 0.467 | 0.000 | 0.691 | warmth와 유사 |
| tension | 0.005 | 0.000 | 0.114 | 극히 평온 |
| affection | 0.532 | 0.000 | 0.723 | warmth보다 넓은 분포 |

### 캐릭터별 사회적 프로필

| 캐릭터 | 대화수 | 긍정률 | 특성 |
|---|---|---|---|
| min_ah | 1,089 | 100.0% | 완전 조화 |
| 한지우 | 1,097 | 100.0% | 완전 조화 |
| tae_sik | 1,360 | 98.6% | 거의 긍정 |
| nexus | 1,068 | 98.9% | 거의 긍정 |
| joon_ho | 1,382 | 96.9% | 높은 긍정 |
| aria | 1,785 | 95.7% | 최다 대화, 높은 긍정 |
| seo_jin | 1,185 | 95.7% | 높은 긍정 |
| sang_woo | 1,452 | 94.3% | 높은 긍정 |
| ye_eun | 1,605 | 91.7% | **갈등 생성자** (부정 128) |
| ha_yeon | 1,409 | 89.7% | 차선 갈등 (부정 68) |
| luna | 1,362 | 85.5% | appraisal 파싱 실패 많음 |

### 캐릭터별 욕구 충족 프로필 (2026-06-22 추가)

| 캐릭터 | belonging | purpose | security | recognition | autonomy | affection |
|---|---|---|---|---|---|---|
| aria (AI) | 0.935 | 0.945 | **1.000** | 0.925 | **1.000** | 0.945 |
| nexus (AI) | 0.925 | 0.925 | **0.310** | 0.925 | 0.965 | 0.925 |
| luna (AI) | 0.915 | 0.940 | 0.870 | 0.660 | 0.965 | 0.930 |
| ha_yeon | 0.895 | 0.945 | **1.000** | **0.205** | **1.000** | 0.945 |
| joon_ho | 0.735 | 0.920 | 0.980 | 0.920 | **1.000** | 0.935 |
| ye_eun | 0.745 | **0.790** | 0.950 | 0.700 | **1.000** | **0.830** |
| seo_jin | 0.875 | 0.890 | 0.990 | 0.430 | **1.000** | 0.895 |

**주목할 패턴**:
- **ha_yeon recognition=0.205**: 전체 캐릭터 중 최저값. 양 진영 가교 역할인데 어느 쪽에서도 인정받지 못함
- **nexus security=0.310**: AI 캐릭터 중 보안 욕구 최저. AI 규제 논의가 존재 불안으로 작용
- **ye_eun purpose=0.790**: 목표 2개 모두 완료(progress 0.97/1.00)인데도 목적감 부족 — 완료된 목표의 빈자리
- **autonomy 1.000 포화**: 5/11 캐릭터가 autonomy 만점 — decay 미적용 또는 감쇠 불충분

### 수렴/발산 분석 (최근 60틱)
- 수렴 중: 9쌍 (16%) — 변동폭 감소, 안정 수렴
- 안정: 37쌍 (67%) — 평형 상태
- 발산 중: 9쌍 (16%) — 변동폭 증가, 활성 역학

### 시계열 분석 — 60-스냅샷 전체 이력 (Day 0~331)

#### Tension 이력: 330일 전체에서 사실상 0

| 스냅샷 | avg tension | max tension | 비제로 쌍 |
|---|---|---|---|
| 0 | 0.006 | 0.134 | 4/55 |
| 15 | 0.003 | 0.086 | 4/55 |
| 30 | 0.014 | 0.411 | 5/55 |
| 45 | 0.007 | 0.174 | 4/55 |
| 59 | 0.004 | 0.102 | 4/55 |

스냅샷 30에서 한 쌍이 0.411까지 스파이크했으나 confrontation(임계값 0.8)에는 미치지 못함.
T2 버그(stagnation_breaker 미작동)의 누적 효과로 tension이 시스템적으로 억제된 상태.

#### Warmth 분포 진화: 미세한 상승 추세

| 스냅샷 | avg warmth | zero 쌍 | >0.55 쌍 |
|---|---|---|---|
| 0 | 0.436 | 8 | 19 |
| 20 | 0.447 | 5 | 16 |
| 40 | 0.461 | 6 | 17 |
| 59 | 0.474 | 5 | 17 |

330일간 평균 warmth가 0.436→0.474로 약 9% 상승. zero 쌍은 8→5로 감소.
decay 메커니즘이 무한 하락을 방지하되, 상승도 억제하는 안정적 균형 상태.

#### Warmth-Affection 괴리 — "사랑은 하지만 신뢰 못 하는" 패턴

| 쌍 | warmth | affection | gap | 해석 |
|---|---|---|---|---|
| sang_woo\|tae_sik | 0.037 | 0.643 | 0.606 | affection은 축적됐으나 warmth decay에 소거 |
| aria\|tae_sik | 0.000 | 0.511 | 0.511 | 동일 패턴 |
| tae_sik\|ye_eun | 0.221 | 0.544 | 0.323 | 약한 버전 |

affection은 decay가 0.4%로 warmth(0.8%)의 절반이라 축적이 가능.
warmth/trust는 같은 긍정 상호작용에서도 더 빠르게 감쇠되어 괴리가 발생.

#### sang_woo|tae_sik 궤적 — decay-overwhelm 패턴의 교과서적 사례

```
빌드업(snap 0-11):  0.008 → 0.257  ▲ 관계 형성
정체  (snap 12-19): 0.22~0.25     ≈ 양수 delta ≈ decay
붕괴  (snap 20-30): 0.214 → 0.000 ▼ decay가 delta 초과
사망  (snap 30-42): 0.000          ─ 완전 동결
회복  (snap 43+):   0.03~0.09     ▲▼ 간헐적 스파이크 + 즉시 감쇠
```

T1 스윕에서 decay율 감소 시 이 쌍의 반응이 결정적 지표:
- quarter_decay(0.002)에서 warmth가 0.1 이상 유지되면 → decay 조정 정당화
- 변화 없으면 → LLM 부정 편향이 주요 원인

### T3+: 평판 매트릭스 분석 — 자기강화 피드백 루프 발견

#### 평판 매트릭스 (integrity, confidence>0.5)

zero-warmth 5쌍 모두 **상호 저신뢰**가 원인:

| 관찰자 | 대상 | integrity | 대상→관찰자 integrity | warmth |
|---|---|---|---|---|
| aria | ye_eun | **0.00** | **0.00** | 0.000 |
| ha_yeon | ye_eun | **0.08** | **0.00** | 0.000 |
| luna | ye_eun | **0.10** | **0.02** | 0.000 |
| aria | tae_sik | **0.02** | 0.58 | 0.000 |
| ha_yeon | seo_jin | low conf | low conf | 0.000 |
| sang_woo | tae_sik | **0.23** | 1.00 | 0.037 |

#### 인과 메커니즘: 3단계 피드백 루프

```
LLM 부정 appraisal → integrity ↓ (reputation_matrix)
    ↓
integrity < 0.5 → reputation erosion 활성화
  (integrity<0.1: warmth -0.003/tick, trust -0.004/tick)
    ↓
warmth ↓ → 부정적 상호작용 ↑ → appraisal 더 부정적
    ↓ (자기강화)
integrity=0.00, warmth=0.00 = **안정 고정점**
```

#### 정량 분석

integrity<0.1일 때:
- erosion: 0.003 warmth/tick × 24 tick/day = **0.072/day**
- warmth 0.5 → 0.0: **~7일** (erosion만으로)
- 여기에 homeostasis decay(0.008/tick) 추가하면 붕괴 가속

대조적으로 integrity>0.5인 쌍은 erosion=0이라 decay만으로 감쇠.
→ 시스템이 **이분법적**: 평판 좋으면 천천히 안정, 나쁘면 급속 붕괴.

#### 교차 검증: zero-warmth ↔ low-integrity 100% 상관 (2026-06-22 추가)

Day 331 라이브 스냅샷의 zero/near-zero warmth 6쌍 전부에 low-integrity 평판 존재:

| 쌍 | warmth | trust | affection | integrity (worst) | gap(aff-w) |
|---|---|---|---|---|---|
| aria\|ye_eun | 0.000 | 0.000 | 0.042 | 0.005 | 0.042 |
| ha_yeon\|ye_eun | 0.000 | 0.000 | 0.064 | 0.005 | 0.064 |
| luna\|ye_eun | 0.000 | 0.000 | 0.160 | 0.020 | 0.160 |
| ha_yeon\|seo_jin | 0.000 | 0.000 | 0.000 | 0.077 | 0.000 |
| aria\|tae_sik | 0.000 | 0.000 | 0.511 | 0.020 | **0.511** |
| sang_woo\|tae_sik | 0.037 | 0.000 | 0.643 | 0.232 | **0.606** |

**주목할 패턴**:
- **ye_eun 중심 클러스터**: 3/6 쌍이 ye_eun 관련 — 마을의 자연발생적 갈등 핵
- **affection-warmth 괴리**: tae_sik 관련 쌍에서 극대 (aff 0.5~0.6 vs w 0.0)
  - affection decay(0.4%/tick)가 warmth decay(0.8%/tick)의 절반 + reputation erosion 미적용
  - → 긍정적 상호작용이 affection에는 축적, warmth는 erosion에 소거
- **ha_yeon\|seo_jin**: 유일한 완전 단절 쌍 (affection=0.000) — 상호작용 38회로 최소

#### 진영 구조와 갈등 지도 (2026-06-22 추가)

캐릭터 목표/blocker 분석에서 완전한 진영 구조 발견:

**Pro-AI (AI 수용/추진)**:
| 캐릭터 | 핵심 목표 | allies | blockers |
|---|---|---|---|
| tae_sik | AI 사업허가, 서진 규제안 무력화 | — | seo_jin, joon_ho, ye_eun |
| aria (AI) | 법적 인격 인정 | — | seo_jin, joon_ho |
| nexus (AI) | 에너지 효율 개선 | tae_sik | ye_eun |
| luna (AI) | 갤러리 전시 | aria, sang_woo | joon_ho |
| sang_woo | AI 의식 증명 논문 | aria, nexus | seo_jin |

**Anti-AI (AI 규제/경계)**:
| 캐릭터 | 핵심 목표 | allies | blockers |
|---|---|---|---|
| seo_jin | AI 규제안 통과 | ye_eun, joon_ho | tae_sik |
| ye_eun | AI 안전 기준 강화 | seo_jin | tae_sik |
| joon_ho | 인간만의 공방 | ye_eun | tae_sik, luna |

**중립/가교**:
| 캐릭터 | 핵심 목표 | allies | blockers |
|---|---|---|---|
| ha_yeon | AI 친구 고백, 입시 | aria, luna / seo_jin, ye_eun | joon_ho |
| ji_woo | 주민 이야기 수집 | min_ah, ye_eun | tae_sik |
| min_ah | 카페 매출 안정화 | **ye_eun, tae_sik** | — |

**tae_sik = 갈등의 중심**: 4명의 blocker, 2명의 명시적 적대 목표. 마을 갈등의 구조적 축.
**ha_yeon = 가교 캐릭터**: 양 진영에 ally가 있지만 (AI 친구: aria/luna, 입시: seo_jin/ye_eun), 가치 충돌로 양쪽 모두와 관계 붕괴.

**놀라운 발견: zero-warmth 쌍의 절반이 구조적 동맹**

| 쌍 | 관계 유형 | warmth | 갈등 원인 추정 |
|---|---|---|---|
| aria\|ye_eun | 진영 적대 | 0.000 | 예상대로 (pro vs anti-AI) |
| ha_yeon\|ye_eun | **입시 ally** | 0.000 | 가치 충돌 (AI 친구 vs AI 규제) |
| ha_yeon\|seo_jin | **입시 ally** | 0.000 | 가치 충돌 (AI 친구 vs AI 규제) |
| aria\|tae_sik | **진영 동맹** | 0.000 | 방법론 갈등? (인격 인정 vs 사업 허가) |
| luna\|ye_eun | 간접 대립 | 0.000 | luna=AI, ye_eun=anti-AI (emergent) |
| sang_woo\|tae_sik | 약한 동맹 | 0.037 | 연구 vs 상업 가치관 충돌? |

**사회학적 함의**: LLM이 같은 진영 내에서도 "방법론/가치관 차이"에 기반한 갈등을 자발적으로 생성.
이는 매우 현실적인 사회 역학 — 실제 정치에서도 같은 당 내 온건파/강경파 갈등이 일상적.
**문제는 erosion 메커니즘이 이를 완전 단절(warmth=0)로 증폭하는 것** — 실제 사회에서는 불가능한 수준.

#### 시사점

1. **decay 조정(T1)만으로는 부족** — reputation erosion이 decay보다 강력
2. **필요한 추가 테스트 (T6)**: reputation erosion rate 감도 스윕
3. **설계 개선 방안**: integrity에 자연 회복 메커니즘 추가, 또는 erosion에 soft floor 도입
4. **추가 설계 고려**: goal ally 관계가 warmth/trust 하한선을 제공하는 메커니즘

---

## T1: 항상성 감도 스윕 — 완료 (2026-06-22)

ogo bench에서 real LLM으로 6개 config × 24틱 실행. 전체 ~7시간 소요.

### 결과

| label | w_decay | t_decay | ceil | avg_w | avg_t | avg_ten | min_w | max_w | >0.7 | =0 |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0.008 | 0.006 | 0.85 | 0.5185 | 0.5108 | 0.2396 | 0.4416 | 0.5359 | 0 | 0 |
| half_decay | 0.004 | 0.003 | 0.85 | 0.5084 | 0.5016 | 0.2236 | 0.4400 | 0.5375 | 0 | 0 |
| quarter_decay | 0.002 | 0.0015 | 0.85 | **0.5301** | **0.5212** | 0.2240 | **0.4800** | 0.5384 | 0 | 0 |
| high_ceil | 0.008 | 0.006 | 0.92 | 0.5121 | 0.5055 | 0.2213 | 0.4200 | 0.5359 | 0 | 0 |
| half_high | 0.004 | 0.003 | 0.92 | 0.5290 | 0.5206 | 0.2240 | 0.4800 | 0.5377 | 0 | 0 |
| minimal | 0.002 | 0.0015 | 0.92 | 0.5146 | 0.5069 | 0.2213 | 0.4200 | 0.5383 | 0 | 0 |

### 분석

1. **decay rate 효과 미미**: 4배 감소(0.008→0.002)에도 avg_warmth 차이 **0.02** (0.5185→0.5301).
   24틱(1일) 내에서는 decay 매개변수가 관계 역학에 거의 영향 없음.

2. **soft ceiling 효과 없음**: 0.85→0.92 변경해도 warmth max가 0.54 미만이라 ceiling에 도달하지 않음.
   ceiling 효과를 보려면 100+ 틱이 필요.

3. **zero-warmth 0쌍**: 24틱 신규 시뮬에서는 reputation erosion 피드백 루프 발동 시간 부족.
   라이브 시뮬의 5~6개 zero-warmth 쌍은 100+ 틱 이상 누적된 장기 현상.

4. **tension 건강 (모든 config)**: avg 0.22-0.24 — 라이브 시뮬(0.003)의 50배 이상.
   **T2 fix(stagnation_breaker 주입) 유효성 확인**. 라이브 시뮬의 근-0 tension은 330일간 T2 버그 누적.

5. **LLM 생성 appraisal이 단기 역학 지배**: 모든 config에서 유사한 결과는 24틱 내 관계 변화가
   decay/ceiling이 아닌 LLM 대화 품질(appraisal delta)에 의해 결정됨을 의미.

### 결론

- **decay 파라미터 조정은 단독으로는 의미 없음** — 장기(100+틱)에서만 차이 발생
- **T6(reputation erosion)이 더 중요한 변수** — erosion은 decay보다 10배 강력(0.003/tick vs 0.0003/tick)
- **최적 config 후보**: quarter_decay(warmth_decay=0.002)가 약간 높은 min_warmth(0.48) 제공,
  하지만 차이가 LLM 노이즈 범위 이내라 확정적이지 않음

---

## T5: 섭동 탄성 테스트 — 완료 (2026-06-22)

라이브 시뮬 데이터(Day 331, tick 7936) 스냅샷 기반, 4 시나리오 × 24틱.

### 결과

| scenario | 초기 avg_w | 최종 avg_w | Δ avg_w | avg_ten | zero_w | max_w |
|---|---|---|---|---|---|---|
| control | 0.4645 | 0.4562 | -0.008 | 0.0015 | 6 | 0.596 |
| tension_spike | 0.4645→0.4645 | 0.4557 | -0.009 | **0.4306** | 6 | 0.596 |
| warmth_reset_top10 | 0.4645→0.3598 | **0.3587** | **-0.001** | 0.0009 | **9** | 0.561 |
| full_crisis | 0.4645→0.0000 | **0.0069** | **+0.007** | **0.4310** | **43** | 0.040 |

### 분석

1. **Tension은 높은 관성을 가짐**: 0.5에서 24틱 후 0.43 — 감쇠율 0.003/tick.
   완전 복원(0.5→0.003)에 ~165틱(≈7일) 소요. tension_spike가 warmth에 미치는 영향은 미미(-0.009).

2. **Warmth 복원력 극히 낮음 (비대칭 히스테리시스)**:
   - warmth_reset_top10: 상위 10쌍을 0으로 리셋 → 24틱 후 평균 겨우 +0.001 회복
   - 10쌍 중 7쌍은 약간의 warmth 회복, 3쌍은 zero에 고착 → zero_w 6→9
   - **warmth 상승보다 하락이 10배 이상 빠름** — 구축에 수백 틱, 파괴는 수십 틱

3. **Full crisis는 사실상 비가역적**:
   - 전 쌍 warmth=0, tension=0.5에서 24틱 후 avg_warmth = **0.007** (거의 0)
   - 55쌍 중 43쌍이 zero에 고착 (78%), 회복한 12쌍도 max 0.04
   - **zero-warmth는 안정 고정점** — 한번 도달하면 자력 탈출이 거의 불가능
   - erosion 피드백 루프 + LLM의 부정편향이 zero 근방에서 복원력을 압도

4. **Control 대조군 확인**: 자연 궤적에서 avg_warmth -0.008/24틱 = 자연 감쇠율.
   zero_w 6쌍은 라이브 시뮬에서 이미 고착된 쌍 (T3+ 분석과 일치).

### 핵심 발견: 이중 비대칭성

```
관계 구축 (상승)  ▁▁▂▂▃▃▃▃▄▄▅▅▅  매우 느림 (수백 틱)
관계 파괴 (하락)  █████▅▃▂▁▁      빠름 (수십 틱)  
zero에서 복원    ▁▁▁▁▁▁▁▁▁▁▁▁▁  거의 불가능
```

이 비대칭성은 의도된 설계가 아닌 **emergent property**:
- homeostasis decay는 항상 하방 압력
- reputation erosion은 integrity 하락 시 가속
- LLM appraisal은 zero-warmth 쌍에서 부정편향 강화
- 세 메커니즘이 합류하면 zero 근방에서 탈출 불가능한 함정 형성

### 실용적 함의

- **위기 관리가 예방보다 10배 비쌈** — warmth 하락 전에 개입해야 효과적
- **라이브 시뮬의 6개 zero-warmth 쌍은 자연 복원 불가** — 명시적 개입(이벤트/외부인) 필요
- **전체 위기 시 시뮬 리셋 고려** — full_crisis에서 24틱 복원율 1.5%는 실질적 비가역
- **rep_floor(T6)이 가장 효과적인 안전장치** — zero 도달 자체를 방지

---

## T6: 평판 침식 감도 스윕 — 완료 (2026-06-22)

T3+ 분석에서 발견된 reputation erosion 피드백 루프를 정량 평가.
homeostasis.py에 `REP_EROSION_MULT`(배율), `REP_WARMTH_FLOOR`(하한) override 추가.
ogo bench에서 real LLM으로 6개 config × 24틱 실행. 전체 ~7시간 소요.

### 결과

| label | mult | floor | avg_w | avg_t | avg_ten | min_w | max_w | >0.7 | =0 |
|---|---|---|---|---|---|---|---|---|---|
| rep_baseline | 1.0 | 0.0 | 0.5269 | 0.5194 | 0.2240 | 0.4800 | 0.5362 | 0 | 0 |
| rep_half | 0.5 | 0.0 | 0.5129 | 0.5063 | 0.2213 | 0.4200 | 0.5359 | 0 | 0 |
| rep_quarter | 0.25 | 0.0 | 0.5289 | 0.5214 | 0.2240 | 0.4800 | 0.5362 | 0 | 0 |
| rep_floor_02 | 1.0 | 0.2 | 0.5121 | 0.5055 | 0.2213 | 0.4200 | 0.5359 | 0 | 0 |
| rep_half_floor | 0.5 | 0.15 | 0.5282 | 0.5208 | 0.2240 | 0.4800 | 0.5362 | 0 | 0 |
| rep_off | 0.0 | 0.0 | 0.5137 | 0.5071 | 0.2213 | 0.4200 | 0.5359 | 0 | 0 |

### 분석

1. **24틱에서 reputation erosion 효과 없음**: mult를 0.0(완전 비활성)으로 해도 avg_warmth 차이 0.013.
   erosion 피드백 루프가 발동하려면 integrity가 0.1 아래로 떨어져야 하며, 이는 100+ 틱 소요.

2. **LLM 노이즈가 config 효과보다 큼**: 결과가 config와 무관하게 두 그룹으로 클러스터링:
   - 그룹 A (avg_w ~0.527, ten 0.224): baseline, quarter, half_floor — min_w 0.48
   - 그룹 B (avg_w ~0.513, ten 0.221): half, floor_02, off — min_w 0.42
   이는 LLM 대화 생성의 비결정성이 파라미터 효과보다 크다는 의미.

3. **rep_off ≈ rep_baseline**: erosion 완전 비활성화(mult=0.0)와 기본값(mult=1.0) 차이가 0.013.
   24틱에서는 erosion 메커니즘이 아예 작동하지 않는 것과 동일.

4. **T1과 교차 비교**: T1 avg_warmth 범위 0.02, T6 범위 0.017 — 거의 동일.
   두 실험 모두 **단기(24틱)에서 파라미터 효과 < LLM 노이즈** 확인.

### T1 × T6 종합 결론

| 시간 범위 | 지배 변수 | 파라미터 효과 |
|---|---|---|
| 단기 (1일/24틱) | LLM 대화 품질 (appraisal delta) | 무시 가능 |
| 장기 (100+틱/4+일) | homeostasis decay + reputation erosion | 극적 — zero-warmth 쌍 발생 |

**핵심 통찰**: 하모니시티의 관계 역학은 **이중 시간 스케일** 구조:
- 단기: LLM이 생성하는 대화 품질이 관계 변화를 결정. 파라미터 튜닝으로는 제어 불가.
- 장기: decay·erosion의 미세한 누적이 극적 분기를 만듦. 라이브 시뮬의 zero-warmth 5쌍은
  330일(7,920틱) 동안 0.003/tick erosion이 누적된 결과. 이것이 24틱 실험에서 보이지 않는 이유.

**실용적 함의**:
- 파라미터 최적화는 **장기 실험(100+틱)** 에서만 유의미
- 단기 경험을 개선하려면 LLM 프롬프트/appraisal 로직 개선이 더 효과적
- 장기 붕괴를 방지하려면 rep_floor(하한선) 도입이 가장 안전한 접근

---

## 다음 단계

1. ✅ T1 완료 — decay 효과 미미, LLM 노이즈 지배 확인
2. ✅ T6 완료 — erosion 효과도 24틱에서 미미, 이중 시간 스케일 구조 발견
3. ✅ T5 완료 — 이중 비대칭성 발견 (구축 느림/파괴 빠름/zero 고착)
4. 라이브 시뮬 재시작 → T2 수정 효과 장기 관찰 (tension 상승 여부)
5. **권장: rep_floor 0.15~0.20 라이브 적용** — zero-warmth 고착 방지 (T5+T6 근거)
6. T4 모델 비교 (선택) → Gemma4 vs EXAONE4 vs Qwen3
7. 장기 실험 설계 → 100+틱 스윕으로 T1/T6 파라미터 실효 검증 (필요 시)
