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

## 운영 상태(10-06 21:4x) — ⛔미가동
- 스크립트 `infra/leowin_backup.ps1` 작성(leowin2 판 파생 · 포함 경로 8잡 · RVC 는 파일 패턴) — **leowin 에 미배포·미실행(드라이런도 안 함)**.
- 막힘 ⑴ leowin PowerShell 기동 불가: `C:\Windows\System32\mscoree.dll` 없음(SysWOW64·WinSxS 에는 있음) → powershell.exe 종료 코드 0xC0000135 · cscript 도 실패. cmd·robocopy 는 됨. 원인 미규명(10-06 17:51 재부팅 뒤 첫 관측, blocked_as_of 21:42 · CBS.log 에 설치 세션 없음 — 적용성 평가만).
- 막힘 ⑵ 자격 파일 `C:\ProgramData\oven_backup\leowin_bk.bin` 없음 · `C:\scripts` 없음 · 예약 작업 없음.
- 실측: SSH = `-p 2222 leo@100.110.30.103` · 네트워크 = USB 무선(Realtek 8812BU, 표시 866Mbps) 뿐 · C: 여유 700GB · gummy `*e_*s.pth` 10개+index · sung_sikyung 폴더 584MB.

