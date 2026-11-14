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
| `C:\RVC\.venv` · `venv` · `env` · `.uvcache` · `.pipcache` · `rvc\models` · `Applio\rvc\models` · `Applio\.git` · `ffmpeg_temp` · 이름으로(어느 깊이든) `sliced_audios`·`sliced_audios_16k`·`f0`·`f0_voiced`·`extracted`·`eval`·`__pycache__` | vocia | 재설치·재다운로드·전처리 재생성 · ⚠11-02 정정: 전처리 폴더는 그전까지 `C:\RVC\f0` 처럼 루트 경로로만 빠졌음(기재와 실제 불일치) → XDN(이름) 으로 수리 |
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

- **10-26 22:10: 음성 4폴더(C:\RVC·so-vits-svc-fork 내용 · leowin2\fish-speech·arena_tts_test) NAS `_archive\voice_20261026\` 별도 보관(12,995파일·19.07GB 일치·SHA256 4/4) 뒤 C: 삭제** — RVC·so-vits 잡은 빈 원본을 /MIR 하므로 일일 사본도 빔(정상) · 위 «지킬 것» vocia·3070 so-vits 항목의 보관처 = `_archive\voice_20261026`.
- **11-02 18:3x: vocia Applio 설치(C:\RVC\Applio·env 7.62GB·.uvcache 7.59GB) 대응** — 그대로면 04:00 에 ≈15GB+ NAS 행 → RVC 잡 제외 추가(위 표) · 재배포 sha256 EF69AA2D…8A36 = repo · RVC 잡 /L 실측 195파일·195.7MB(rc 1). ✅11-06 23:2x 확인: 11-03~06 04:00 4회 연속 `RUN OK`(RVC=0~1) · NAS `leowin2\RVC` = 251파일 1.96GiB(env·.uvcache·G_/D_ 0 · 모델 7개 × ≈250MB = `Applio\logs\qF_*` 최종 .pth·.index + Applio 루트 .exe 2개 167MB(ffmpeg 류 · 재다운로드 가능 · 작아서 그대로 둠)).
- **10-26 04:00 RUN FAIL**(SongFormer_logs=16 — 원본 `C:\amt_tools\SongFormer` 를 10-25 정리에서 지운 탓 · robocopy 오류 2 «지정된 파일을 찾을 수 없음» · oven 이 정리 전에 백업 잡 원본 대조를 안 했음) → 10-26 22:39 스크립트 수리(원본 없으면 skip · SHA256 c611e043ed30…) 재배포 · DRYRUN OK. NAS `amt_tools_SongFormer_logs` 5파일(29,311B)은 /MIR 아님이라 보존. ✅10-27 04:00 RUN OK(SongFormer_logs=skip · 나머지 rc ≤2) — 수리 확인.

- **11-13 08:2x: NAS 주소 .41→.113 대응**(11-11 공유기 교체 · admin 11-12 DHCP 예약 .113) — 11-13 04:00 예약 결과 LastTaskResult **1**(평소 0 · FAIL=8 도 아님 = 스크립트가 결과 줄 쓰기 전 NAS 연결에서 멈춘 것으로 봄 · 결과 줄·robocopy 로그가 NAS 에만 있어 몇 밤 빠졌는지는 미측정, 11-12·13 두 밤 이상 추정) · 실측: .41:445 닫힘(leowin·leowin2·reklcli·mukl 넷 다) · .113:445 열림 → `$Share` 한 줄 고침·재배포 sha256 AD9932CA9AFB55E2… = repo · ⚠DRYRUN 의도였으나 ssh 기본 셸이 인자를 갈라 `-DryRun` 이 안 먹어 **실실행** `20261113_082346 RUN OK`(DESKTOP=3·나머지 0·SongFormer skip) = 04:00 분 따라잡기와 같음. · ✅**11-14 04:00 예약 LastTaskResult 0**(oven 실측 11-14 13:4x) = 수리 확인

## 열린 것
스냅샷 보존 정책(일 14·주 8) = LEO DSM 1회(admin 202152 — 지금은 안 지움) · 결과 FAIL 감시(누가·언제 읽나) 미정 · 실행 시각(매일 04:00 — GPU 학습과 대조) · leowin 목록(별도 파일)
