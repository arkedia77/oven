# 음악 AI 엔진 아키텍처 종합 연구보고서

작성일: 2026-03-16
연구 주체: reklcli (Claude Code Agent)

본 보고서는 주요 음악 AI 엔진들의 아키텍처를 기술적으로 분석합니다. 로컬 파일 및 웹 검색을 통해 Leo의 Liszt 엔진 개발 맥락에 맞춰 정보를 정리했습니다.

---

## 1. SUNO

### 생성 방식
- **멀티모달 트랜스포머 기반**: 텍스트와 오디오 패턴 모두 처리
- **단계식 처리**: 텍스트 인코더 → 뮤지컬 특성 디코더 → 신경 보코더
- **두 개의 핵심 모델**:
  - **Bark**: 보컬 멜로디와 가사 생성
  - **Chirp**: 악기 음향 및 음성 효과 생성
- **오디오 기반 출력**: Raw audio를 통째로 생성 (MIDI 사용 안함)

### v5 (2025년 9월) 주요 개선
- **Intelligent Composition Architecture**: 절과 절 사이 자연스러운 진행
- **Latent diffusion**: 압축된 오디오 표현 사용 → 빠른 생성
- **구조 제어**: Verse, Chorus 같은 섹션 자동 생성
- **보컬 표현력**: 음색, 호흡 제어, 비브라토, 프레이징 다이나믹
- **최대 8분** 곡 생성 가능

### 아키텍처 특징
- MIDI 사용 안함 → 오디오에서 직접 생성
- 음색이 모델 내장 (변경 불가)
- 분리 불가능한 완성된 오디오 출력

### Leo와의 차이점 (ENGINE_PLAN.md 기준)
| 항목 | Suno | Liszt |
|------|------|-------|
| 출력 형식 | 오디오 | **MIDI** |
| 음색 수정 | 불가 | **VST 교체 가능** |
| 편집성 | 불가 | **파트별 수정 가능** |
| 표현력 | 평균 | **연주자 스타일** |

---

## 2. META MUSICGEN / MUSICLM

### MusicGen 아키텍처

**핵심 차이점**: MusicLM과 달리 self-supervised semantic representation이 필요 없음

#### 구성 요소
1. **EnCodec 토크나이저**
   - 32kHz 오디오 → 4개의 코드북으로 토큰화
   - 50Hz 샘플링 레이트 (초당 50 토큰)
   - Residual Vector Quantization (RVQ) 사용

2. **Transformer 디코더 (한 단계)**
   - Single-stage, causal decoder-only 아키텍처
   - **모든 4개 코드북을 한 번에 생성** (병렬 처리)
   - 작은 지연으로 코드북 간 종속성 활용
   - MusicLM의 계층식 seq2seq와 다름

3. **텍스트 인코더**
   - 텍스트 설명 → 임베딩 변환
   - CLAP 모델 기반 (음악-텍스트 대조 학습)

4. **Melody 조건화**
   - Raw MIDI 사용 안함
   - **Chromagram 표현** 사용 (음악 이론적 접근)
   - 하모니와 멜로디 가이드

### MIDI vs. Audio 토큰 선택
- **MusicGen**: Audio latent tokens (EnCodec) 사용
- 이유: MIDI는 표현력 제한, 음향 세부사항 부족
- 트레이드오프: 연산 비용 증가하지만 음질 우수

### 조건화 메커니즘
- **텍스트**: CLAP 임베딩을 통해 "upbeat jazz", "calm classical" 같은 스타일 인식
- **멜로디**: Chromagram → 멜로디적 제약 적용
- **장르 제어**: 텍스트 설명으로 간접 제어

---

## 3. STABLE AUDIO (Stability AI)

### 생성 방식
- **Latent Diffusion 모델**: 텍스트 및 시간(duration) 조건화
- **확산(diffusion)** 접근 → 노이즈에서 점진적 정제

### 아키텍처 구성 (3부)

1. **Variational Autoencoder (VAE)**
   - 스테레오 오디오 → 압축된 잠재 인코딩
   - Descript Audio Codec 기반 convolutional 구조
   - 임의 길이 오디오 처리 가능

2. **Text Encoder**
   - CLAP 모델 (음악-텍스트 대조 학습)
   - 단어-사운드 관계 정보 포함

3. **Diffusion 모델**
   - 버전 1: 907M 파라미터 U-Net
   - 버전 2.0: **Diffusion Transformer (DiT)** → 긴 시퀀스 처리 개선
   - 음악의 대규모 구조 인식 및 재현 능력

### Stable Audio 2.0 진화
- **최대 3분 곡** 생성 (44.1kHz 스테레오)
- **Audio-to-audio**: 사용자 샘플 업로드 후 텍스트로 변환/확장
- **Coherent Musical Structure**: 장기간 구조 유지

### MusicGen과의 비교
| 항목 | MusicGen | Stable Audio 2.0 |
|------|----------|-----------------|
| 방식 | Autoregressive | Diffusion |
| 토큰 | 이산(discrete) | 연속(latent) |
| 구조 | Single-stage | VAE + DiT |
| 계산 | 빠름 | 느림 (확산 스텝) |

---

## 4. ARIA (EleutherAI) - 로컬 구현

### 아키텍처 (~/musicscore/aria/)

#### 핵심
- **LLaMA 3.2 (1B)** 기반 autoregressive Transformer
- **MIDI 토큰 기반** (Audio가 아님)
- 피아노 특화

#### 토큰화
- **Note-centric tokenizer**: 음악 이벤트의 미세 입도 양자화
- **17,727 vocab 크기** (medium.json 기준)
- 음표별(next-token) 예측으로 연속 생성

#### 모델 스펙 (medium.json)
```json
{
  "d_model": 1536,
  "n_heads": 24,
  "n_layers": 16,
  "max_seq_len": 8192,
  "vocab_size": 17727
}
```

#### 학습 데이터
- **Aria-MIDI**: ~60,000시간 피아노 MIDI (1,186,253곡)
- **수집 방식**: 웹 오디오 자동 크롤링 + LLM 메타데이터 기반 스코어링 + 다단계 프루닝

### 조건화 & 임베딩

#### 3가지 체크포인트
1. **aria-medium-base**: Base model (next-token prediction)
2. **aria-medium-gen**: 생성 품질 최적화 (finetuned)
3. **aria-medium-embedding**: **SimCSE-style 대조 학습** (MIDI 임베딩)

#### 임베딩 모델 (medium-emb.json, 클래스 크기 = 2)
- **Contrastive learning**: 곡의 컴포지션/퍼포먼스 특성 캡처
- 멘델스존 vs. 쇼팽 같은 스타일 구분 가능

#### 조건화된 분류 모델들
```
medium-genre.json      (class_size: 6)       → 장르 분류/조건화
medium-form.json       (class_size: 6)       → 음악 형식 (소나타 등)
medium-composer.json   (class_size: ?)       → 작곡가 스타일
medium-pianist.json    (class_size: ?)       → 연주자 스타일
medium-emotion.json    (class_size: ?)       → 감정 표현
medium-music_period.json                     → 시대별 특성
```

### 장점
- **MIDI 기반**: 음악 이론과 일치, 편집 가능, VST 렌더링 용이
- **Expressive 피아노**: ~60k 시간 고품질 피아노 음악 학습
- **미세한 표현력**: 루바토, 벨로시티, 페달 타이밍 학습 가능
- **구조 인식**: 멀티-트랙 지원 (제한적)

### 한계
- **피아노 특화**: 다른 악기는 충분하지 않음
- **컨티뉴에이션 최적화**: 기존 MIDI에서 시작할 때 최고 성능
- **메모리**: 인기 클래식곡 과다 표현 (Chopin 등)

### Leo의 Liszt 전략
- **기본**: Aria base 위에 구축
- **파인튜닝**: MAESTRO + ATEPP 데이터로 퍼포먼스 표현 강화
- **출력**: MIDI → Keystroke (키스케이프) VST 렌더링
- **조건화**: 연주자 스타일, 곡의 형식, 감정 임베딩 활용

---

## 5. 음악 생성 아키텍처 비교: 핵심 결정점들

### 5.1 MIDI vs. Audio Tokens

| MIDI 토큰 | Audio 토큰 (Latent) |
|-----------|-------------------|
| **구조**: 음악 이론 기반 | **구조**: 신경망 학습 기반 |
| **표현**: 이산, 명시적 | **표현**: 연속, 암묵적 |
| **편집성**: 높음 (DAW 호환) | **편집성**: 낮음 |
| **음향 충실도**: 제한적 | **음향 충실도**: 높음 |
| **계산**: 빠름 | **계산**: 느림 |
| **사용처**: Aria (피아노) | **사용처**: MusicGen, Stable Audio |

**선택 이유**:
- **Aria (MIDI)**: 피아노는 표기법이 풍부하고, 퍼포먼스 미묘함이 중요
- **MusicGen (Audio)**: 일반 음악(보컬, 악기 혼합)은 음향 세부사항이 중요

### 5.2 장르/스타일 조건화 메커니즘

#### A. 텍스트 임베딩 기반 (MusicGen, Stable Audio)
```
사용자 텍스트 → CLAP 인코더 → 텍스트 임베딩 → 조건 벡터
```
- 장점: 자유로운 자연어 표현
- 단점: 미세한 음악 특성 제어 어려움

#### B. 분류 모델 기반 (Aria 파인튜닝)
```
MIDI 파일 → 분류 헤드 (genre/form/emotion) → 임베딩 → 생성 조건
```
- 장점: 이산적 범주 제어, 연주자 스타일 명확
- 단점: 사전 정의된 범주만 지원

#### C. 대조 학습 기반 (Aria embedding)
```
MIDI1 + MIDI2 → SimCSE 손실 → 공유 임베딩 공간
```
- 용도: 스타일 유사도 검색, 데이터셋 큐레이션

### 5.3 구조 제어 (Verse/Chorus/Bridge)

#### 접근법 1: 명시적 태그 (HeartMuLa, YuE)
```
[Verse] 메인 멜로디...
[Chorus] 반복 섹션...
[Bridge] 전환 부분...
```

#### 접근법 2: 계층식 모델 (Hierarchical generation)
```
High-level: 전체 곡 형식 (verse-chorus-verse...)
Low-level: 음표, 코드 생성
```

#### 접근법 3: 확산 + 이산 토큰 (Stable Audio 2.0)
- DiT → 장기 음악 구조 학습 (암묵적)

#### 접근법 4: Long context + 상대 주의 (Transformer)
- **최대 시퀀스**: Aria = 8192 토큰
- 피아노 MIDI: ~2048 토큰/분 → **최대 4분** 컨텍스트

### 5.4 Retrieval-Augmented Generation (RAG) 음악에서

#### 아이디어
```
사용자 요청 → 태그 추출 → 데이터베이스 검색 → 유사 예제 검색
→ 프롬프트에 연결 → 생성 모델 → 음악 출력
```

#### 음악 AI에서의 RAG 적용
- **아직 주류 아님** (LLM RAG만큼 흔하지 않음)
- **논문**: "Retrieval-Augmented Generation of Symbolic Music with LLMs" — 심볼릭 음악에서 RAG 유효성 확인
- **가능성**: 특정 스타일/장르 데이터베이스 + 검색 기반 제약

#### Leo의 Liszt에 적용 가능성
- MAESTRO + ATEPP 데이터베이스
- 연주자 스타일 검색 후 조건화 → "Horowitz 스타일로 계속"

---

## 6. 표현적 퍼포먼스(Expressive Performance) MIDI 생성

### 핵심 구성요소
- **벨로시티(Velocity)**: 32개 빈 양자화 (MIDI 0-127), 멜로디 강조 vs. 반주 억제
- **타이밍(Timing)**: 절대 시간 10ms 간격, 루바토/템포 유연성 캡처
- **페달(Sustain Pedal)**: 온/오프 이벤트, 악보에 없는 음향적 표현
- **아티큘레이션**: 음표 간 오버랩(레가토/스타카토)

---

## 7. 기술 스택 총정리

| 엔진 | 토큰화 | 생성 아키텍처 | 조건화 |
|------|--------|-------------|--------|
| Aria/Liszt | MIDI → Note tokens (17,727) | Transformer (LLaMA 1B) AR | 분류 임베딩 + 대조 학습 |
| MusicGen | Audio → EnCodec RVQ (4 codebooks) | Transformer decoder AR | CLAP 텍스트 + Chromagram |
| Stable Audio | Audio → VAE latent (연속) | Diffusion Transformer (DiT) | CLAP 텍스트 + Duration |
| Suno | Audio (end-to-end) | Multimodal Transformer | 자유 텍스트 + 구조 태그 |

---

## 8. 결론: 아키텍처 선택 매트릭스

| 요구사항 | Aria (MIDI) | MusicGen | Stable Audio | Suno |
|---------|------------|----------|-------------|------|
| 편집 가능 | ** | X | X | X |
| 음색 변경 | ** | X | X | X |
| 표현적 성능 | ** | O | O | O |
| 일반 음악 | X | ** | ** | ** |
| 보컬 품질 | X | X | X | ** |
| 협업 가능성 | ** | X | X | X |
| 오픈소스 | ** | ** | O (제한적) | X |

---

## Sources
- [Suno v5 Technical Deep Dive](https://musicgeneratorai.io/posts/how-does-suno-ai-create-music)
- [Meta AudioCraft Blog](https://ai.meta.com/blog/audiocraft-musicgen-audiogen-encodec-generative-ai-audio/)
- [MusicGen Paper](https://ai.honu.io/papers/musicgen/)
- [Stable Audio Research Paper](https://stability.ai/research/stable-audio-efficient-timing-latent-diffusion)
- [Aria GitHub Repository](https://github.com/EleutherAI/aria)
- [Aria Architecture Paper](https://arxiv.org/html/2506.23869)
- [Retrieval-Augmented Generation of Symbolic Music with LLMs](https://arxiv.org/html/2311.10384v2)
- [Expressive MIDI-format Piano Performance Generation](https://arxiv.org/abs/2408.00900)
