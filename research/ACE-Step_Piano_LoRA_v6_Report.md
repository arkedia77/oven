# ACE-Step Piano LoRA v6 — 연구 보고서

작성일: 2026-05-08 | 프로젝트: oven (Quincy Piano Engine)

---

## 1. 개요

ACE-Step(Audio Creation Engine)의 피아노 음색/스타일을 개선하기 위해 LoRA(Low-Rank Adaptation) 파인튜닝을 v1부터 v6까지 반복 실험했다. 최종 v6에서는 Aria MIDI → VirtuosoNet 휴머나이제이션 → Piano V3 VST 렌더링 파이프라인으로 고품질 학습 데이터를 구축하고, AudioSR 초해상도 후처리까지 검토했다.

---

## 2. 학습 파이프라인 진화

### 2.1 버전별 데이터 & 학습 설정

| 버전 | 데이터 소스 | 세그먼트 수 | Rank/Alpha | Epochs | LR | Scheduler |
|------|-----------|-----------|-----------|--------|------|-----------|
| v2 | piano-v2/segments (사운드폰트) | 240 | 32/32 | 50 | 1.5e-4 | cosine |
| v3 | v2 동일 | 240 | 64/64 | 80 | 1.5e-4 | cosine |
| v4 | v2 동일 | 240 | 64/64 | 120 | 1.5e-4 | cosine |
| v5 | IdO Grand Piano 합성 | ~300 | 64/64 | 300 | 1.5e-4 | cosine |
| v6 | Aria MIDI + VirtuosoNet + Piano V3 | 487 | 64/64 | 300 | 1.5e-4 | cosine |

### 2.2 v6 데이터 파이프라인 (`build_v6_full.py`)

5단계 모듈형 파이프라인:

1. **MIDI 선별** — Aria MIDI v1-ext에서 audio quality score ≥ 0.95 기준, 4명의 작곡가(Hisaishi 10 / Einaudi 10 / Yiruma 8 / Sakamoto 8) 36트랙 선별
2. **VirtuosoNet 처리** — MIDI → MusicXML → VirtuosoNet(ISGN, z=0)으로 velocity/pedal 다이나믹스 추출, 템포 왜곡 보정
3. **Piano V3 렌더링** — DawDreamer + Piano V3 VST3 (48kHz), gain 0.8x 정규화, peak 0.99 리미팅
4. **세그먼테이션** — 30s 길이, 15s 스트라이드, 곡당 최대 20세그먼트, RMS ≥ 0.005 / peak ≤ 0.99 필터, 50ms 페이드
5. **텐서 전처리** — ACE-Step 전처리 포맷으로 변환 → 487개 세그먼트

### 2.3 핵심 개선 포인트 (v2 → v6)

- **데이터 품질**: 사운드폰트 → IdO Grand Piano → VirtuosoNet 휴머나이즈드 Piano V3
- **데이터 규모**: 240 → 487 세그먼트 (2배)
- **LoRA Rank**: 32 → 64 (표현력 증가)
- **학습 길이**: 50 → 300 에폭 (충분한 수렴)
- **최종 v6 loss**: 0.2737

---

## 3. 생성 평가

### 3.1 표준 프롬프트 세트 (전 버전 공통)

| ID | 프롬프트 | 용도 |
|----|---------|------|
| 01_lyrical | lyrical solo piano, emotional, slow tempo, reverb, cinematic | 서정적 피아노 |
| 02_jazz | jazz piano trio, swing, walking bass, brushed drums | 재즈 피아노 |
| 03_classical | classical piano sonata, romantic era, expressive dynamics | 클래식 소나타 |
| 04_darkcine | dark cinematic piano, suspenseful, minor key, sparse notes | 시네마틱 |
| 05_ragtime | ragtime piano, upbeat, syncopated, early 1900s | 래그타임 |
| 06_lofi | lo-fi piano, mellow, rainy mood, soft felt piano | 로파이 |

### 3.2 오디오 품질 평가 결과 (`eval_audio_quality.py`)

v5 기준 6개 샘플 정량 평가:

| 샘플 | 등급 | Centroid (Hz) | Flatness | Onsets | SNR (dB) | 비고 |
|------|------|--------------|----------|--------|----------|------|
| 01_lyrical | GREEN | 1,534 | 0.0003 | 34 | - | 정상 |
| 02_jazz | GREEN | 1,604 | 0.0007 | 103 | 29.4 | 정상 |
| 03_classical | GREEN | 1,666 | 0.0004 | 42 | 33.1 | 정상 |
| 04_darkcine | GREEN | 1,990 | 0.0005 | 12 | 36.7 | 정상 |
| 05_ragtime | GREEN | 2,607 | 0.0013 | 86 | 41.5 | 정상 |
| 06_lofi | YELLOW | 1,761 | - | 39 | - | 무음 31.3% |

### 3.3 청취 평가 요약

- **음악적 품질**: 양호 — 선율/화성 구조가 자연스러움
- **오디오 품질**: ACE-Step 아키텍처 한계 — "축음기 느낌"(고역 감쇠, 저해상도 텍스처)
- **v6 LoRA vs 베이스 모델**: LoRA 적용 시 피아노 음색 집중도 향상, 그러나 근본적 오디오 해상도는 변화 없음

---

## 4. 후처리 파이프라인

### 4.1 스타일별 프리셋 (`postprocess_audio.py`)

| 프리셋 | IR (임펄스 응답) | Wet | 압축 | 용도 |
|--------|---------------|-----|------|------|
| concert | Musikvereinsaal | 20% | -20dB / 2.5:1 | 서정적/클래식 |
| intimate | French Salon 18C | 12% | -18dB / 2.0:1 | 재즈/로파이 |
| cinematic | Scala Milan Opera | 30% | -22dB / 2.0:1 | 시네마틱 |
| bright | Synthetic | 12% | -18dB / 2.5:1 | 래그타임 |
| studio | Salon + 테이프 새추레이션 | 22% | -20dB / 2.0:1 | 마스터링 |

모든 프리셋 공통: LUFS -14 라우드니스 정규화, peak 0.99 리미터

### 4.2 프롬프트 → 프리셋 자동 매핑

```
01_lyrical   → concert
02_jazz      → intimate
03_classical → concert
04_darkcine  → cinematic
05_ragtime   → bright
06_lofi      → intimate
```

---

## 5. AudioSR 초해상도 실험

### 5.1 테스트 설정 (`test_audiosr.py`)

- 모델: AudioSR "basic"
- Guidance scale: 3.5 / DDIM steps: 50 / Seed: 42
- 출력 샘플레이트: 48kHz
- 테스트 파일: Hisaishi, Yiruma 스타일 각 1곡

### 5.2 스펙트럼 분석 (`compare_audiosr.py`)

9개 주파수 대역(0-500Hz ~ 20-24kHz) 파워 스펙트럼 비교:
- **고주파 복원**: 8kHz 이상 대역에서 에너지 증가 확인
- **아티팩트**: 지지직 노이즈 + 인위적 룸 이펙팅 잔존
- **결론**: 고주파는 회복되지만 새로운 아티팩트가 추가되어 net gain이 불확실

### 5.3 그리드 서치 (guidance_scale × steps)

| guidance_scale | steps | 결과 |
|----------------|-------|------|
| 1.5 | 25 | 변화 미미 |
| 1.5 | 50 | 약간 개선 |
| 2.5 | 25 | 고역 복원, 아티팩트 소량 |
| 2.5 | 50 | 중간 수준 |
| 3.5 | 25 | 고역 복원 뚜렷, 아티팩트 증가 |
| 3.5 | 50 | 고역 최대 복원, 아티팩트도 최대 |

**최적 후보**: guidance 2.5 / steps 25~50 (복원-아티팩트 트레이드오프)

---

## 6. 결론 및 교훈

### 무엇이 잘 됐는가
- v6 데이터 파이프라인(Aria MIDI → VirtuosoNet → Piano V3)은 기존 사운드폰트 대비 확실한 품질 향상
- LoRA rank 64, 300 epochs가 수렴에 적절 (loss 0.2737)
- 후처리 프리셋 자동화로 일관된 마스터링 품질 확보

### 한계
- **ACE-Step 아키텍처 한계**: 48kHz VAE(AutoencoderOobleck) 디코더 자체의 해상도가 낮아 "축음기 느낌" 해소 불가
- **AudioSR**: 고주파 복원은 되지만 새 아티팩트 도입 — 디노이즈 추가 없이는 실용 곤란
- **LoRA의 역할**: 음색 방향(피아노다움)은 개선하지만, 근본적 오디오 해상도는 변경 불가

### 향후 방향 (참고용)
- ACE-Step 자체 개선 없이는 오디오 품질 천장이 존재
- ACE Studio MCP + GUI 자동화로 고품질 렌더링하는 것이 현실적 대안
- AudioSR은 디노이즈 후처리와 결합해야 실용 가능성 있음

---

## 부록: 주요 파일 경로

| 파일 | 용도 |
|------|------|
| `build_v6_full.py` | v6 전체 데이터 파이프라인 |
| `build_v6_data.py` | v6 데이터 빌드 (이전 버전) |
| `preprocess_piano_v[2,3,5].py` | 전처리 스크립트 |
| `ace-step-train-v[2-6].bat` | 학습 배치 스크립트 |
| `gen_piano_lora_samples_v[2-5].py` | 체크포인트별 샘플 생성 |
| `gen_v6_samples.py` | v6 최종 샘플 생성 |
| `postprocess_audio.py` | 스타일별 후처리 |
| `eval_audio_quality.py` | 오디오 품질 평가 |
| `test_audiosr.py` | AudioSR 초해상도 테스트 |
| `compare_audiosr.py` | 스펙트럼 비교 분석 |
| `v6_preview/` | v6 데모 WAV |
| `piano_lora_samples/` | HTML 비교 갤러리 |
