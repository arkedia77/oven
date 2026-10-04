# leowin2 백업 목록 (manifest v1 · 2026-10-04)

원칙(LEO 10-04): **내용 = 그 경로를 쓰는 에이전트가 정함 · 실행 = 관리자 oven 1곳**(기계당 백업 작업 1개 → NAS DS420+ `/volume2/leofamily/backup/leowin2/`, 삭제 방어 = NAS 스냅샷).
**기본값 = 포함.** 아래 «뺄 것»에 주인이 명시한 것만 뺀다. 주인 미상 경로는 포함.
원자료: `agent-comm:projects/oven/messages/processed/` — vocia 174503 · 3070 174522 · hitmaking 174549.

## 백업 루트(이 아래 전부 포함 후 «뺄 것» 제외)
| 루트 | 주인 |
|---|---|
| `C:\Users\leowin2.DESKTOP-KSKH97R` | 3070·hitmaking(공용 프로필) |
| `C:\Users\leo.LEOWIN2` | 3070(embed_3070) · 그 외 미상 |
| `C:\Users\leowin2` | 3070(ACE-Step·fish-speech) · GPT-SoVITS·arena_tts_test 미상 |
| `C:\RVC` | vocia |
| `C:\so-vits-svc-fork` | 3070 |
| `C:\amt_tools` | hitmaking(inbox\3070_* = 3070) |

## 뺄 것(주인 명시분)
| 경로 | 주인 | 이유 |
|---|---|---|
| `…KSKH97R\egmd\.venv` · `bp_train\.venv` | 3070·hitmaking | venv — README_3070.txt로 재설치 |
| `…KSKH97R\egmd\s1\*.tfrecord` · `s1\input` · `s1\s1b_train` · `bp_train\smoke` | 3070 | reklcli s1_data/gt에서 재생성 |
| `…KSKH97R\egmd\ckpt`(.zip) · `magenta-2.1.4` · `*.zip` · `bp_train\basic-pitch-0.4.0` | 3070 | 공개 다운로드 |
| `…KSKH97R\.local` · `AppData\Roaming\uv\python` · `.cache\huggingface` | 3070·hitmaking | uv·파이썬·HF 캐시 |
| `C:\Users\leo.LEOWIN2\lora_stage` | 3070 | 08-25 LEO 삭제 승인분(정리 예정) |
| `C:\Users\leo.LEOWIN2\.cache` | (설계 v0) | HF·torch 캐시 |
| `C:\Users\leowin2\ACE-Step-1.5\.venv` · `checkpoints` | 3070 | 재설치·공개 가중치 |
| `C:\Users\leowin2\fish-speech\.venv` · `checkpoints` | 3070 | 재설치·공개 가중치 |
| `C:\so-vits-svc-fork\.venv` | 3070 | venv |
| `C:\RVC\.venv` · `venv` · `rvc\models` · `ffmpeg_temp` · `logs\*\{sliced_audios,sliced_audios_16k,f0,f0_voiced,extracted,eval}` | vocia | 재설치·재다운로드·전처리 재생성 |
| `C:\RVC\logs\*\G_*.pth` · `D_*.pth` | vocia | ⚠**3070의 NAS 이관이 끝난 뒤부터** 제외 — 그 전엔 포함 |
| `C:\amt_tools\hitmaking_gpu\venv` · `venv` · `omnizart_env` · `YourMT3*` · `hf_cache` · `test_audio` · `SongFormer`(단 `*.log`는 포함) | hitmaking | 재설치·공개 저장소·가중치 |
| 공통 | — | `AppData\Local\Temp` · `INetCache` |

## 지킬 것(유일본 — 검증 시 표본 해시 대상)
- 3070: `egmd\s1\run_*` · `bp_train\runs\*` · `embed_3070*` · `ACE-Step-1.5\{instrument_test_output,k015_output,k3018_output,pipeline_e2e,topline_genre_test}` · `so-vits-svc-fork\{logs,dataset,dataset_raw,separated}` (≈12.5GB)
- vocia: `C:\RVC\logs\{gummy,lyn,sung_sikyung}` 모델·index · `C:\RVC\datasets` (≈3.2GB)
- hitmaking: `amt_tools\hitmaking_gpu\{scripts,work}` · `amt_tools\output` · `SongFormer\*.log` · venv 재생성 근거 `amt_tools\hitmaking_gpu\requirements_freeze_20261004.txt`(54줄) · `amt_tools\requirements_freeze_20261004_venv.txt`(88줄) — hitmaking 174828

## 주인 미상(기본 포함 · 확인 대기)
`C:\Users\leowin2\GPT-SoVITS` · `arena_tts_test` · `…KSKH97R\.cache\suno`(2.2GB) · `C:\amt_tools\inbox`의 3070_* 외 낱개 wav

## 열린 것
NAS 공유·백업 전용 SMB 계정·스냅샷(admin 청구 174325) · 실행 시각(매일 04:00 — GPU 학습과 대조) · leowin 목록(별도 파일)
