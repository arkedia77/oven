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

## 운영 상태(10-06 23:0x) — 첫 실행 진행 중 · ⛔예약 없음 · ⚠무선이 느려 완주 미정
- 스크립트 `infra/leowin_backup.ps1` → leowin `C:\scripts\leowin_backup.ps1`(SHA256 9a4f13e8…·파싱 오류 0).
- 자격 파일 설치(22:2x, LEO 승인·권한 규칙 추가 뒤): `C:\ProgramData\oven_backup\leowin_bk.bin` 246B · NAS 공유 접근 확인 · ACL = SYSTEM·Administrators.
- 드라이런 `20261006_222444 DRYRUN OK`(전 잡 rc 1 · 실패 열 0 · 약 30분 소요): E_work 205.7GB/58,979파일 · 사진 7.16GB · 어머니 사진 0.67GB · gummy 0.66GB(13) · sung_sikyung 0.56GB(5) · 기타 <0.1GB ⇒ 합 ≈215GB. ※E_work 로그에 ERROR/오류 문자열 72줄 — 실패 열 0 이라 파일명 일치로 추정(미확인).
- 첫 실행: 22:56 SSH 전경으로 시작(reklcli 백그라운드 작업 — SSH 끊기면 중단·재실행하면 이어감). **실측 속도 ≈0.3MB/s**(robocopy 읽기 0.23·쓰기 0.37MB/s, 23:00) · 디스크 사용률 0% ⇒ 병목 = 무선(Realtek 8812BU USB · 5GHz 신호 55% · NAS ping 평균 67ms·최대 410ms). 이 속도면 215GB ≈ 8일 — 유선 연결 또는 무선 개선 없이는 완주 비현실적. 소파일 다수 구간이라 과소일 수 있음(대용량 구간 속도 미측정).
- ⛔예약 작업 `OvenBackupDaily` 미등록 — 등록 명령이 Claude Code 자동 모드 분류기에 거부(Unauthorized Persistence, 22:56). LEO 손 또는 권한 규칙 필요.
- 해결: leowin PowerShell 기동 불가(`System32\mscoree.dll` 없음·0xC0000135) → `sfc /verifyonly` 위반 1건 → LEO 승인 `sfc /scannow` 복구(21:4x). 없어진 원인 미규명.
- SSH = `-p 2222 leo@100.110.30.103` · 콘솔 로그온 = beomj(17:51~).
