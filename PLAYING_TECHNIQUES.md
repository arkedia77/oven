# Piano Playing Techniques — MIDI Humanization Reference

구현: `humanize_midi.py` / 후처리: `postprocess_audio.py`

---

## 1. Sustain Pedal (CC64)

### Legato (Syncopated) Pedaling
새 코드를 **치고 나서** 떼었다가 다시 밟음. 이전 코드와 새 코드가 짧게 겹치며 레가토 형성.

- 순서: 새 노트 onset → 페달 OFF → 페달 ON
- OFF: onset 후 15~40ms / ON: OFF 후 35~70ms (템포 비례)

### Half Pedaling
- 트레블만 바뀔 때 CC64=35 (quarter pedal)로 부분 리프트
- 저음 잔향 유지, 고음 뭉침만 정리

### Bass-Driven Pedaling
- 베이스 pitch class 변화 → full re-pedal (0→127)
- 트레블만 변화 → half-pedal dip (35→127)

### Tempo-Adaptive Timing
| BPM | Release delay | Re-engage delay |
|-----|--------------|-----------------|
| <80 | 40ms | 70ms |
| 80~120 | 25ms | 50ms |
| >120 | 15ms | 35ms |

---

## 2. Velocity Dynamics

### Voicing (멜로디/반주 분리)
- 멜로디(최고음): **+15** velocity
- 베이스(최저음): **+5**
- 내성(inner voice): **-10**
- 동시 발음 노트에서 자동 분류 (onset window 50ms)

### Phrase Dynamics (power curve)
- Crescendo: `(t/peak)^1.3` (느린 시작, 가속)
- Diminuendo: `(1-progress)^0.7` (빠른 감소, 여운)
- 프레이즈별 peak position: 40~70% 랜덤

### Metric Accent
| Beat position | Multiplier |
|--------------|------------|
| Beat 1 (downbeat) | ×1.00 |
| Beat 3 (secondary) | ×0.93 |
| Beat 2, 4 (weak) | ×0.87 |

### Register Offset
| Range | Offset |
|-------|--------|
| <C2 (MIDI 36) | +7 (bass boost) |
| C2~C4 | +3 |
| C4~C6 | 0 (reference) |
| >C6 | -6 (treble soften) |

### Repeated Note Decay
- 연속 동음: -3 velocity/회 (최대 -15)
- 자연스러운 피로/이완 패턴

### Tempo-Adaptive Jitter
| BPM | σ (Gaussian) |
|-----|-------------|
| <80 | 15 |
| 80~120 | 12 |
| >120 | 8 |

### Dynamic Accents (TODO)
- sfz: 110~127 스파이크
- fp: 110~127 → 즉시 50~65
- fz: 100~120 (forte 맥락)

---

## 3. Micro-Timing

### Melody Lead
- 멜로디: **-25ms** (그리드보다 앞)
- 베이스: **+12ms** (살짝 뒤)
- 내성: **+15ms**
- 출처: Goebl (2001) median 30ms

### Chord Arpeggiation
- "동시" 코드도 bottom→top **8~15ms/note** 스프레드
- 2음 코드: ~15ms, 4음 코드: ~45ms 총 스프레드

### Phrase-End Ritardando
- 프레이즈 마지막 20%에서 지수적 감속
- 최대 **25% stretch** (progress^1.5)
- 마지막 구간 음표 duration도 15% 연장

### Velocity-Dependent Timing
- 강한 음(vel>70): **8ms 앞당김** (anticipation)
- 약한 음(vel<70): **8ms 늦춤**
- `offset = (vel - 70) / 50 × (-8ms)`

### Beat-Level Rubato (TODO)
- 강박: IOI +3~8% / 약박: IOI -2~5%
- 120 BPM 기준: 강박 +20~40ms, 약박 -10~25ms

---

## 4. Articulation

### Duration by Role
| Role | Duration ratio |
|------|---------------|
| Melody | 95% (legato, +30ms overlap) |
| Bass | 90% |
| Inner | 70% |
| Default | 80% |

### Phrase Gap
- 프레이즈 간 최소 80ms 간격 확보
- 마지막 노트 duration 줄여서 보장

### Staccato/Legato (TODO)
- Staccato: 25~50% duration
- Staccatissimo: 15~25%
- Tenuto: 90~100%

### Grace Notes (TODO)
- Acciaccatura: 65% of main velocity, 30~50ms 간격
- Appoggiatura: 80~90%, expressive weight

---

## 5. Audio Post-Processing

### Studio Preset Chain
1. **Tape saturation**: tanh soft clipping, drive=0.12 (even harmonics)
2. **HPF**: 35Hz rumble cut
3. **EQ**: 300Hz -2dB (mud), 150Hz +1.5dB (warmth), 3kHz +1.5dB (clarity), 10kHz +2dB (air)
4. **Convolution reverb**: French 18th Century Salon IR, wet=0.22, predelay 내장
5. **Compression**: threshold -20dB, ratio 2.0, attack 30ms, release 200ms
6. **Limiter**: -1dBFS
7. **Loudness normalize**: -14 LUFS

### Available Presets
| Preset | IR | Reverb wet | Character |
|--------|-----|-----------|-----------|
| concert | Musikvereinsaal | 0.20 | 대형 콘서트홀 |
| intimate | French Salon | 0.12 | 살롱, 가까운 느낌 |
| cinematic | Scala Milan | 0.30 | 영화음악, 넓은 공간 |
| bright | algorithmic | 0.12 | 밝고 선명 |
| **studio** | French Salon | 0.22 | **tape sat + full EQ** |
| studio_large | Musikvereinsaal | 0.18 | tape sat + 대형홀 |

---

## 참고 문헌
- Goebl (2001) — melody lead 측정 (median 30ms)
- Repp (1996) — 페달 타이밍 변동성 15~40ms, micro-timing SD
- Palmer (1989, 1996) — 표현적 타이밍 구조
- Bresin & Battel (2000) — 아티큘레이션 전략
- Bernays & Traube (2014) — 피아니스트 개별성
- MAESTRO dataset (Hawthorne et al., 2019) — 실제 CC64 연속값
