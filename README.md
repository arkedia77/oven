# MusicScore + Liszt 피아노 엔진

## 프로젝트 개요
- 데이터 수집 파이프라인 + **Liszt 피아노 AI 엔진** 개발
- Aria (EleutherAI) 기반 파인튜닝 → 키스케이프 VST 렌더링
- 수노와 다른 방향: MIDI 생성 → VST 렌더링 → 뮤지션 협업 툴

## 핵심 문서
| 문서 | 설명 |
|------|------|
| `ENGINE_PLAN.md` | Liszt 엔진 Phase 1~7 전체 로드맵 |
| `KANBAN.md` | 현재 작업 상태 |
| `TODO.md` | 상세 할일 목록 |

---

## 스크립트

### 데이터 수집
| 파일 | 설명 |
|------|------|
| `00_login.py` | Chrome 프로필 로그인 (1회용) |
| `01_collect_urls.py` | MuseScore URL 수집 (새벽 2시 자동) |
| `02_download.py` | MuseScore MXL 다운로드 (Selenium) |
| `03_download_api.py` | MuseScore MXL 다운로드 (curl_cffi) ← 현재 사용 |
| `04_bitmidi.py` | BitMIDI 다운로더 (mukl에서 실행) |
| `monitor_bitmidi.py` | BitMIDI 진행 모니터 (3시간마다 자동) |
| `utils.py` | 공통 유틸리티 |

### Liszt 엔진
| 파일 | 설명 |
|------|------|
| `prepare_piano_data.py` | 피아노 MIDI 추출 + 품질 필터 + 중복 제거 |

---

## 데이터 현황 (`/Volumes/data/score/`)

### ✅ 완료
| 폴더 | 내용 | 수량 |
|------|------|------|
| `PDMX/` | 공개도메인 MXL + MIDI | 254,035개 |
| `gigamidi/` | 다악기 MIDI (train/val/test) | 3,409,419개 |
| `lakh/` | Lakh MIDI (Million Song 매핑) | 178,561개 |

### 🔄 다운로드 중 (Liszt 핵심)
| 폴더 | 내용 | 중요도 |
|------|------|--------|
| `aria-midi/` | ARIA-MIDI 피아노 118만곡, 품질 0.95+ | ★★★ |
| `maestro/` | 실제 피아니스트 퍼포먼스 MIDI 1,276곡 | ★★★ |
| `atepp/` | 49명 피아니스트 11,742곡 다중 해석 | ★★★ |
| `asap/` | 악보+퍼포먼스 정렬 1,068곡 | ★★★ |
| `aria-amt/` | EleutherAI 오디오→MIDI 변환 모델 | 검증용 |
| `pop909/` | 팝 구조 909곡 (멜로디/코드/반주 분리) | ★★ |
| `pop-k-midi/` | K-pop 멜로디 30만개 | ★★ |
| `midicaps/` | MIDI + 텍스트 캡션 | 향후 |
| `musescore/` | 최신 K-pop/팝 MXL | 자동 수집 중 |
| `bitmidi/` | 다장르 MIDI | mukl 수집 중 |

### 🔜 대기 중
| 데이터셋 | 내용 |
|---------|------|
| PianoCoRe | 16만 퍼포먼스 정렬 — 정식 출시 시 즉시 확보 |

---

## 설치된 도구
```
demucs       오디오 소스 분리 (보컬/악기 분리)
basic-pitch  오디오 → MIDI 변환 (Spotify)
pedalboard   Python VST 호스팅 (키스케이프 등 DAW 없이)
pretty_midi  MIDI 분석/가공
miditok      MIDI 토큰화 (Aria 파인튜닝 전처리)
```

## 자동화 (launchd)
| 시간 | 스크립트 |
|------|---------|
| 새벽 2시 | `01_collect_urls.py` |
| 새벽 3시 | `03_download_api.py` |
| 3시간마다 | `monitor_bitmidi.py` |

## mukl 협업 채널
`~/projects/agent-comm/musicscore/tasks/` → push → mukl → `results/`
