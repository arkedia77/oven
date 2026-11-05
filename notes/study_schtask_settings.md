# 스터디 — 작업 스케줄러 ExecutionTimeLimit·LastTaskResult (A-177 learning · 11-05 마감 · 제때)

출처: Microsoft Learn «Task Scheduler Error and Success Constants»·`TaskSettings` 문서(기억 기반 정리 · 원문 재열람 안 함) + 11-05 10:4x leowin·leowin2 실측(아래 표). 실측과 맞춘 범위는 «검증» 줄.

## LastTaskResult 읽는 법
| 값 | 16진 | 뜻 | 우리 쪽 실례 |
|---|---|---|---|
| 0 | 0x0 | 마지막 실행이 0 으로 끝남 | 두 OvenBackupDaily 11-05 |
| 8 등 작은 정수 | — | **스크립트의 exit 값이 그대로** 올라옴 | 백업 스크립트 FAIL = `exit 8` → 8 |
| 267009 | 0x41301 | 지금 **실행 중**(오류 아님) | leowin OvenComfyUIMoss 11-05(Running) |
| 267011 | 0x41303 | 한 번도 안 돎 | 새로 등록한 직후 |
| 267014 | 0x41306 | 사용자 또는 **시간 제한**으로 종료됨 | 10-31 ComfyUI 72h 정지 |
| 2147750687 | 0x8004131F | 이미 실행 중이라 새 실행을 **건너뜀**(MultipleInstances=IgnoreNew) | 아직 관측 없음 |

⇒ 판정: «0 = OK» 만으로 보지 말 것. 상주 작업은 267009 가 정상이고, 백업 작업은 0 이 정상·8 이 FAIL.

## ExecutionTimeLimit
- 기본값 **PT72H** — 등록 때 안 바꾸면 72시간 뒤 강제 종료(267014). 상주 서버는 반드시 **PT0S**(무제한).
- 백업처럼 끝나는 작업은 제한이 «멈춘 robocopy 를 끊는 안전장치»라 짧게 두는 편이 낫다(leowin2 = PT4H).

## 실측 11-05 (Get-ScheduledTask)
| 머신·작업 | limit | StartWhenAvailable | 계정 | 마지막 |
|---|---|---|---|---|
| leowin OvenComfyUIMoss (부팅 트리거) | PT0S ✅ | False(부팅 트리거라 무관) | SYSTEM·Highest | 267009 실행 중 |
| leowin OvenBackupDaily (05:00) | **PT72H(기본값)** | **False** | SYSTEM·Highest | 0 |
| leowin2 OvenBackupDaily (04:00) | PT4H | True | SYSTEM·Highest | 0 |

## 판단
- leowin 백업 작업은 leowin2 판과 설정이 어긋남: 05:00 에 꺼져/재부팅 중이면 **그날 백업이 조용히 빠진다**(StartWhenAvailable=False → 놓친 실행을 다시 안 함, 결과 줄도 안 생김). leowin 은 상시 켜 두는 기계라 위험은 낮지만, «결과 줄 0 = 안 돌았다» 규칙으로만 잡힌다.
- 고칠 값: StartWhenAvailable=True · ExecutionTimeLimit=PT12H(첫 ≈230GB 무선 복사 여유). 예약 작업 설정 변경 = 지속성 변경이라 **LEO 손 실행 몫**(분류기 막힘) — 다음 LEO 요청 묶음에 넣을 것.

## 검증
- 267014 ↔ 10-31 ComfyUI 72h 정지·PT0S 적용(11-02) 뒤 재발 없음 — 실측 일치.
- 267009 ↔ 11-05 State=Running — 실측 일치.
- 0x8004131F 는 관측 없음(문서 기억만).
