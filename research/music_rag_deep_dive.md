# RAG for Symbolic Music / MIDI Generation: Deep Research Report
## For the Liszt Project (Aria-based Piano AI Engine)
## 2026-03-16

---

## 1. 핵심 숫자 요약

| 항목 | 값 |
|------|-----|
| Aria hidden dim | 1536 |
| Aria params | ~650M |
| Aria max seq length | 8192 tokens |
| **Embedding output dim** | **512** |
| Embedding max input | 2048 tokens |
| Contrastive training slice | 100-650 notes |
| 권장 청크 | 4-8마디 (~200-400 notes) |
| 권장 top-k | 5 검색, 3 주입 |
| Vector DB | FAISS (cosine similarity) |

### Embedding 분류 정확도 (linear probe)
| Task | Accuracy |
|------|----------|
| Genre | 92.40% |
| Musical Period | 84.70% |
| Composer | 90.50% |
| Pianist | 91.57% |

---

## 2. arXiv:2311.10384 — 심볼릭 음악 RAG 논문

- **도메인**: ABC notation, 아이리시 전통 음악
- **청킹**: 없음 (곡 단위)
- **임베딩**: 태그 기반 검색 (Jaccard similarity), 신경망 아님
- **LLM**: ChatGPT-4 (생성), ChatGPT-3 (검색)
- **top-k**: 3개, prepend 방식
- **정량 평가**: 없음 (개념 증명 수준)
- **평가**: 개념적 참고만, 기술적으로는 얕음

---

## 3. Aria Embedding Model (aria-medium-embedding) 상세

### 모델 스펙
| Parameter | Value |
|-----------|-------|
| Output embedding dim | 512 |
| Projection | Final hidden → 512-dim |
| Extraction point | EOS token |
| Max input | 2048 tokens |
| Training | NT-Xent loss (SimCLR-style) |
| Temperature τ | 0.1 |
| Epochs | 25 |
| LR | 1e-5, linear decay |

### 학습 방법
- 같은 MIDI의 두 랜덤 슬라이스(100-650 notes) → 가까운 벡터
- Augmentation: transposition ±5, tempo ±20%, velocity ±10%
- **Phrase-level 지원됨** — 4~30마디 프레이즈에 최적화

---

## 4. 관련 논문/프로젝트

### CLaMP 2 (NAACL 2025)
- text + ABC + MIDI 멀티모달 대조 모델, 768-dim
- text→MIDI 크로스모달 검색 가능

### VMB (arXiv:2412.09428) — Retrieval-Augmented Music Generation
- Latent diffusion + dual-track retrieval
- 주입: element-wise addition + cross-attention (오디오 도메인)
- KLpasst 75.29 vs 96.42 (without retrieval) — 유의미한 개선

### "From Generality to Mastery" (arXiv:2506.17497)
- Bottleneck adapter for composer style
- **161~307곡만으로 작곡가 스타일 학습 성공**
- 12-layer, 46M params

### MuLan / MusicLM (Google)
- Joint audio-text embedding (44M recordings)
- Cosine similarity retrieval → conditioned generation

---

## 5. LoRA for Music Models

### Aria에서 가능한가?
**거의 확실히 가능.** LLaMA 3.2 기반, standard MHA, PEFT 호환.

### LoRA vs RAG
| 차원 | LoRA | RAG |
|------|------|-----|
| 학습 필요 | Yes (스타일당) | No |
| 추론 비용 | base 동일 | +검색 |
| 스타일 깊이 | 깊음 | 얕음 |
| 조합 | 어려움 | 쉬움 |
| 데이터 | 50~300곡 | 많을수록 좋음 |
| 새 스타일 | 수시간 학습 | 즉시 |
| **권장** | 핵심 스타일 | 탐색/혼합 |

---

## 6. 실용 권장사항

### 청킹 전략
| 단위 | Notes | 음악 | 용도 |
|------|-------|------|------|
| Fine | 100-200 | 2-4마디 | 모티프 |
| **Medium** | **200-400** | **4-8마디** | **RAG 기본** |
| Coarse | 400-650 | 8-16마디 | 구조 |

50% overlap, max 15초/200노트 상한 필수

### FAISS 인덱스
| 규모 | 인덱스 | 메모리 |
|------|--------|--------|
| PoC (64K) | IndexFlatIP | ~125MB |
| 중간 (1M) | IVF1024,Flat | ~1GB |
| 풀 (69M) | IVF4096,PQ64 | ~8GB |

### 파이프라인
```
User → style/seed → tokenize → embed(512-dim)
  → FAISS top-5 → diversity rerank → top-3
  → prepend + prefix tokens → generate → MIDI
```

---

## Sources
- arXiv:2311.10384 (Music RAG), arXiv:2506.23869 (Aria ISMIR 2025)
- arXiv:2504.15071 (Aria-MIDI), arXiv:2410.13267 (CLaMP 2)
- arXiv:2412.09428 (VMB), arXiv:2506.17497 (Generality to Mastery)
- HuggingFace: loubb/aria-medium-embedding, loubb/aria-medium-base
- GitHub: EleutherAI/aria, ylacombe/musicgen-dreamboothing
