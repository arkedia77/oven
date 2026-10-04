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

## 제외(백업만 안 함 · leowin 에서 지우는 것 아님)
| 경로 | 크기 | 사유 |
|---|---|---|
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
