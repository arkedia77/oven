# 하모니시티 D-A1 — 자율경계 확장 MVP 스펙 v0 (위치·방문 선택)

> 작성: oven, 2026-07-23. kee 게이트 GO(2026-07-23) — 대상·스캐폴딩 방식·halt-loop 가드 계획 전부 승인.
> 조건: ①형식이탈 시 기존 스크립트로 안전 fallback ②관계수치 변경 로직 불가침 ③검증결과(3관측) 게이트 보고 후 D-A2/A3 진행.

## 1. 대상

`village/interaction/encounter.py`의 `determine_locations()` — 캐릭터 목표가 있을 때 20% 확률로 발동하는 "ally 방문" 분기. 기존: `random.choice(allies)`로 방문 대상 결정(100% 스크립트). 신규: LLM이 니즈·목표를 보고 실제로 어디로 갈지 스스로 선택(스캐폴딩 — 지정 아님).

- 옵트인: `HARMONICITY_AUTONOMY_LOCATION=1`. 미설정 시 기존 로직 완전 동일(회귀 확인).
- 관계수치 변경 로직은 이 모듈이 건드리지 않음 — encounter.py의 위치 배정에만 관여.

## 2. 구현 (`village/autonomy.py`)

- `_build_prompt`: 캐릭터의 최우선 미충족 니즈 + 목표 + 갈 수 있는 장소 7종(+ally가 있을 것 같은 위치 힌트) 제시.
- `choose_location`: LLM 호출 → 응답이 유효 장소 id 집합에 속하면 채택(`interpretation_status=parsed`), 아니면 **안전 fallback**(기존 스크립트 `_scripted_ally_pick` 그대로 호출, `interpretation_status=fallback`, kee 게이트 조건1).
- D-L1 decision_record 연동: basis=니즈/목표, alternatives_considered=전체 장소목록, choice=선택(or `format_deviation_fallback`), outcome={assigned_location, realized}.

### 🔴 실측 중 발견한 프롬프트 버그(수정 완료)

이 모델(`google_gemma-4-26B-A4B-it-Q8_0.gguf`)은 `chat_template_kwargs.thinking=False`를 보내도 `reasoning_content`를 자체적으로 채우는 경향이 있다. 최초 프롬프트("다른 설명 없이 장소 id 하나만 정확히 출력해")+`max_tokens=20`은 **100% 빈 응답**("(무응답)")이었다 — 직접 진단 결과 `finish_reason=length`로, reasoning이 토큰 예산을 전부 소진하고 content는 항상 빈 채였다(max_tokens을 1024까지 올려도 동일 프롬프트 문구로는 실패).

appraisal.py가 이미 쓰는 문구("thinking 없이 바로 JSON만 출력")로 바꾸고 `max_tokens=512`로 올리자 일부 성공하기 시작함 — 즉 **문구 자체가 이 모델/서버 설정에서 reasoning 억제에 유의미**했다(단순 토큰 예산 문제가 아니었음). 코드에 근거 주석 반영.

## 3. 검증 결과 (격리 world, 실 LLM, 20틱, N=37 위치선택 사례)

| 관측 | 결과 |
|---|---|
| ①형식이탈율(interpretation_status) | **fallback 46%(17/37)** — 프롬프트/토큰 수정 후에도 남는 값. appraisal의 기존 실측 실패율과 같은 계열의 "젬마 판단 두께" 신호로 판단(확대 없이 그대로 보고, kee 조건3). |
| ②판단분산(parsed 20건 choice 분포) | cafe 14 / community_center 2 / council 2 / studio 1 / lab 1 — 균일분포 아님, 캐릭터별 목표에 정합된 편향(아래 참조). |
| ③선택-니즈 상관 | 목표가 장소를 명시하는 캐릭터는 **일관되게 그 장소를 선택**: luna(목표="민아 카페에 전시 제안")→cafe 4/4, tae_sik(목표="서진 규제안 무력화", 시의회 근무)→council 2/2, joon_ho(목표="공방/교실 열기")→community_center 2/2. affection이 최우선 미충족 니즈인 캐릭터들은 편안함·일상대화 vibe인 cafe로 쏠림. **무작위가 아니라 목표/니즈에 정합된 선택**으로 판단. |

**종합 소견**: 판단 자체는 그럴듯하다(②③) — 젬마가 답을 낼 때는 목표·니즈를 반영한 선택을 한다. 문제는 **답을 내는 빈도**(①46% 미도달) — 이건 자율 확장의 상한이 "판단 품질"이 아니라 "판단 완주율"에 있다는 신호. D-A2(폴백 태깅 계측)가 정확히 이 신호를 추적하는 트랙이라 자연스럽게 이어짐.

## 4. Halt-loop 가드 (kee 지시로 선행 필수 격상)

✅ 완료 — `safety_rail.record_halt_and_check_loop()`(연속halt 3회/1h 초과 시 watchdog 자가 DISABLE + `HALT_LOOP_GUARD_TRIGGERED.json` 마커, admin §4-c 패턴 동형). 검증 PASS(3회 연속 킬스위치 → 3회째 정확 트리거). 완전 자동 통지는 kee가 YAGNI로 보류 — oven 세션재개 루틴에서 마커 확인.

## 5. 라이브 적용

D-L1/D-S1과 동일 원칙 — 옵트인이라 배포만으론 무해, 다음 자연 재기동 시 함께 배포 예정.

## 6. D-A3 판단분산 본계측 결과 (2026-07-23, kee 게이트 GO 후)

### 실험 설계
①동일 캐릭터, 자기 고유 니즈/목표로 N=8 반복(temp=0.7) — 엔트로피 측정.
②서로 다른 5캐릭터에 **동일한 합성 니즈/목표**(needs 대부분 0.9 균등, 목표="마을 사람들과 더 가까워지고 싶다")를 강제 부여 후 N=4씩 — 페르소나만으로 다른 선택이 나오는지("개별 법의 존재" 판정선) 확인.

### 결과
| 실험 | 결과 |
|---|---|
| ①자기 고유 목표 | luna 8/8 cafe(entropy=0) / aria 8/8 studio(entropy=0) / tae_sik 7/8 council+1fail(entropy=0.54) — **거의 완전 결정론적**. 목표가 구체적일수록(예: luna="카페에 전시 제안") 답이 사실상 하나뿐이라 개인차가 드러날 여지가 애초에 적음. |
| ②동일 합성 입력 | 같은 숫자 입력인데도 캐릭터별로 다른 장소에 쏠림 — luna(아티스트)/min_ah(카페사장)는 **plaza** 우세, tae_sik(시의원)/aria(AI)는 **cafe** 우세, seo_jin(윤리학자)은 cafe/community_center 혼합. 각 캐릭터 내에서도 ①과 달리 반복 간 변동 발생(예: luna cafe 1회+plaza 3회). |

### 소견
판단분산은 **입력이 애매할 때만 드러난다.** 목표가 구체적이면(①) 개인차와 무관하게 결정론적으로 수렴 — 이건 자율성 부재가 아니라 문제 자체에 정답이 하나뿐인 경우. 입력이 모호해지면(②) 그제서야 (a) 캐릭터 내 확률적 변동 (b) 페르소나에 따른 캐릭터 간 체계적 차이가 둘 다 나타남 — 이게 "개별 법의 존재" 증거로 판단된다. 즉 판단분산의 판정선은 "무작위인가"가 아니라 "**입력이 결정을 완전히 결정짓지 않을 때 페르소나가 차이를 만드는가**"이고, 이 실험은 그 답이 YES라는 걸 보였다.

### 컴퓨트 관측 (kee 신설 게이트)
새 계측 불요 — 기존 `village/profiling.py`(2026-07-19 배포, `HARMONICITY_PROFILE=1`)가 이미 호출당 gen_tokens·latency와 틱당 llm_calls·wait_s를 기록 중이며, autonomy.py의 호출도 동일 경로(`llm.chat()`)를 타므로 자동 포함된다. 실측 샘플(격리world 3틱, autonomy+profile 동시 옵트인): 틱당 llm_calls 2~18건, wait_s 15~168초 — 자율 판단 지점이 늘수록 틱당 컴퓨트가 선형 증가하는 게 이미 관측됨. S12/S11 예산 트랙이 참조할 수 있는 기존 산출물.
