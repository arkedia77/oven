# leowin 백업 목록 (manifest v1 · 2026-10-04)

결정 = LEO 10-04 ≈20:3x 이전(oven 화면 · 시각 미실측 — 발신 커밋 20:33 이전): 판단 필요 항목 「백업할 정도는 없어, 그냥 이 내용은 백업하지 마」 ⇒ **확실히 지킬 것만**. 원칙·실행 방식은 leowin2 와 같음(실행 = oven 1곳 → NAS `\\172.30.1.41\leowin_backup\leowin`, 삭제 방어 = NAS 스냅샷).
실측: 10-04 robocopy /L 합(E: 5.324TB · 32줄 접근 오류 → 일부 과소 가능).

## 포함(≈230GB)
| 경로 | 크기 | 이유 |
|---|---|---|
| `E:\work` | 220.9GB | 사업 문서(유일본) |
| `E:\사진` | 7.7GB | 사진 |
| `E:\어머니 사진 백업` | 0.7GB | 가족 사진 |
| `E:\leo1_backup` · `E:\backup_c` · `E:\temp_keygen` | <0.1GB | 작음 — 포함 |
| `C:\RVC\logs\{gummy,sung_sikyung}`의 `*_e_*s.pth`·`*.index`·`config.json`·`model_info.json`·`training_data.json` | ≈1.3GB | 학습된 목소리 모델 유일본(재다운로드 불가) — 3070 224405 제보·oven 실측 22:4x. ★leowin gummy = 40k · leowin2 gummy = 48k 비교 쌍[vocia 추정·A-244 폴더명] — 둘 다 보관 |

## 제외(백업만 안 함 · leowin 에서 지우는 것 아님)
| 경로 | 크기 | 사유 |
|---|---|---|
| `C:\RVC\logs\gummy\G_*·D_*.pth` | ≈13GB | 학습 재개 전용 — vocia 224705 동의 |
| `E:\archive\switch` | 2,166GB | 게임 덤프 — 재획득 |
| `E:\archive\vsti` | 771GB | 가상악기 설치본 — 재다운로드 |
| `E:\exist\음악` · `기타 백업` · `동영상` | 598·416·154GB | LEO 「백업할 정도 아님」 |
| `E:\고음원` | 205GB | 〃 |
| `E:\cloud\OneDrive` | 174GB | 〃 |
| `E:\google backup\work` | 220.9GB | `E:\work` 중복(크기 동일·파일 수 1 차 — 해시 미대조) |
| `E:\archive\movies` · `E:\models` · `E:\hf_models` · `E:\seed-vc` · `E:\UTIL` · `E:\MV` | 140·138·4.8·5.1·9.2·1.7GB | 영화·공개 가중치·공개 코드·설치본 |
| `E:\exist\$Recycle.Bin` · `$RECYCLE.BIN` · `System Volume Information` · `Recovery` · `OneDriveTemp` | — | 시스템 |

## 열린 것
leowin C:(286GB 사용)의 사용자 홈 범위 — 미측정 · leowin 사용 슬롯 목록 미청구(Ternary-Bonsai `C:\tb2` = oven, 재다운로드 가능 → 제외 예정)

## 운영 상태(10-07 09:3x) — 첫 실행 완주·검증 OK · ⛔예약 없음(수동 실행뿐)
- **첫 실행 `20261006_225654 RUN OK`**: 10-06 22:56 → 10-07 09:19(≈10시간 22분 · 평균 ≈5.7MB/s, USB 무선). 전 잡 rc 1 · 로그 실패 열 0.
- **검증(10-07 09:2x)**: 원본↔NAS 파일 수·바이트 일치(숨김 포함) — `E:\work` 58,979개/220,881,432,496B · `E:\사진` 255/7,687,641,083B · `E:\어머니 사진 백업` 331/705,846,367B · 표본 SHA256 8개 일치(gummy_500e pth·gummy.index·work 2·사진 2·어머니 사진 2). 복원 시험은 안 함.
- ⛔**예약 작업 `OvenBackupDaily` 미등록** — 등록 명령이 Claude Code 자동 모드 분류기에 거부(Unauthorized Persistence, 10-06 22:56). 지금은 «한 번 돈 사본»일 뿐 매일 갱신 안 됨 — LEO 손 또는 권한 규칙 필요.
- 구성: 스크립트 `infra/leowin_backup.ps1` → leowin `C:\scripts\leowin_backup.ps1`(SHA256 9a4f13e8…) · 자격 `C:\ProgramData\oven_backup\leowin_bk.bin`(DPAPI LocalMachine · ACL SYSTEM·Administrators, 10-06 22:2x 설치) · 권한 규칙 = reklcli `~/oven/.claude/settings.local.json`(LEO 기입).
- 속도 이력: 소파일 구간 0.3MB/s·대용량 2~3MB/s 실측 → 「8일」·「27시간」 추정은 둘 다 과대였음(실제 10.4시간). 무선 = Realtek 8812BU USB · 5GHz 신호 55%.
- 드라이런 `20261006_222444 DRYRUN OK`(≈30분). ※E_work 로그 ERROR/오류 문자열 72줄 = 실패 열 0·수량 일치로 파일명 일치 판정.
- 해결 이력: leowin PowerShell 기동 불가(`System32\mscoree.dll` 없음·0xC0000135) → LEO 승인 `sfc /scannow` 복구(10-06 21:4x) · 없어진 원인 미규명.
- SSH = `-p 2222 leo@100.110.30.103`.
