# leowin2 백업 목록 (manifest v1 · 2026-10-04)

원칙(LEO 10-04): **내용 = 그 경로를 쓰는 에이전트가 정함 · 실행 = 관리자 oven 1곳**(기계당 백업 작업 1개 → NAS DS420+ 공유 `leowin_backup`(volume2) `\\172.30.1.41\leowin_backup\leowin2` — admin 174649: 스냅샷이 공유 단위라 leofamily 하위에서 분리, 삭제 방어 = NAS 스냅샷).
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
| `C:\Users\leowin2\arena_tts_test\.venv` · `C:\Users\leowin2\GPT-SoVITS`(전체) | 3070(수행)·vocia(가치 판단, LEO 10-04) | 재설치 — GPT-SoVITS 학습 가중치 0 · ⚠로컬 수정 여부 미확인(3070) |
| `C:\so-vits-svc-fork\.venv` | 3070 | venv |
| `C:\RVC\.venv` · `venv` · `rvc\models` · `ffmpeg_temp` · `logs\*\{sliced_audios,sliced_audios_16k,f0,f0_voiced,extracted,eval}` | vocia | 재설치·재다운로드·전처리 재생성 |
| `C:\RVC\logs\*\G_*.pth` · `D_*.pth` | vocia | ⚠NAS 이관(이제 oven 몫, vocia 224705)이 끝난 뒤부터 제외 — 그 전엔 포함. 첫 백업이 NAS에 사본을 만듦 → 대조 후 C: 삭제는 win_remote_delete 드라이런→kee→LEO |
| `C:\amt_tools\hitmaking_gpu\venv` · `venv` · `omnizart_env` · `YourMT3*` · `hf_cache` · `test_audio` · `SongFormer`(단 `*.log`는 포함) | hitmaking | 재설치·공개 저장소·가중치 |
| 공통 | — | `AppData\Local\Temp` · `INetCache` |

## 지킬 것(유일본 — 검증 시 표본 해시 대상)
- 3070: `egmd\s1\run_*` · `bp_train\runs\*` · `embed_3070*` · `ACE-Step-1.5\{instrument_test_output,k015_output,k3018_output,pipeline_e2e,topline_genre_test}` · `so-vits-svc-fork\{logs,dataset,dataset_raw,separated}` (≈12.5GB)
- vocia: `C:\RVC\logs\{gummy,lyn,sung_sikyung}` 모델·index · `C:\RVC\datasets` (≈3.2GB) · `C:\Users\leowin2\arena_tts_test\{results,outputs,reference_voices,scripts}`·*.py (3070 예전 TTS 비교 실험 유일본 — vocia 203553)
- hitmaking: `amt_tools\hitmaking_gpu\{scripts,work}` · `amt_tools\output` · `SongFormer\*.log` · venv 재생성 근거 `amt_tools\hitmaking_gpu\requirements_freeze_20261004.txt`(54줄) · `amt_tools\requirements_freeze_20261004_venv.txt`(88줄) — hitmaking 174828

## 주인 미상(기본 포함 · 확인 대기)
`…KSKH97R\.cache\suno`(2.2GB) · `C:\amt_tools\inbox`의 3070_* 외 낱개 wav

## 운영 상태(10-04 23:5x)
- 첫 실행 22:36~23:39(≈93GB·63분, 1Gbps 유선) → 레지스트리 하이브(오류 32)·WindowsApps 별칭(오류 1920) 실패로 FAIL → 제외 추가 → 2회차 23:40 OK(175초).
- 검증: 표본 3 SHA256 일치(gummy 모델·embed_3070 파일·so-vits D_ 체크포인트) · 복원 시험 1회 일치.
- 예약 `OvenBackupDaily`(SYSTEM·매일 04:00·최대 4시간) → NAS 스냅샷 06:00(admin). 결과 = `\\172.30.1.41\leowin_backup\leowin2\_logs\_results.txt`(성공도 1줄).
- 자격 = leowin2 `C:\ProgramData\oven_backup\leowin_bk.bin`(DPAPI LocalMachine·SYSTEM/Administrators) ← 원본 mukl ~/vault/nas_leowin_bk.txt.
- 10-06 21:4x 결과 줄 열람(NAS `_results.txt`): `20261005_040001 RUN OK` · `20261006_040001 RUN OK`(전 잡 rc 0~1) — 예약 2회 연속 정상.
- 10-10 15:3x: 결과 줄 10-07~10-10 전부 `RUN OK` · C: 여유 6.7GB · RVC G_/D_ 40개(26,188,736,760B) = 매일 사본 40/40 같은 크기·별도 보관 사본 `_archive\RVC_GD_20261010\`(40개 일치·표본 SHA256 3/3) 신설 · **C: 삭제는 kee→LEO 결재 대기(154215)** — GO 뒤 삭제 + XF 추가.
- **10-10 16:2x: C: 의 G_/D_ 40개 삭제 완료**(kee 전결 162118 · win_remote_delete.py 40/40) → 여유 6.7GB → 33.9GB · 스크립트 RVC 잡 XF = `G_*.pth`·`D_*.pth`(재배포 SHA256 ea376592…) · 되살리기 = `_archive\RVC_GD_20261010\`. ⏳10-11 04:00 실행 뒤 `_archive` 40개 잔존 실측 확인 남음.

## 열린 것
스냅샷 보존 정책(일 14·주 8) = LEO DSM 1회(admin 202152 — 지금은 안 지움) · 결과 FAIL 감시(누가·언제 읽나) 미정 · 실행 시각(매일 04:00 — GPU 학습과 대조) · leowin 목록(별도 파일)
