# leowin2 C: 일제 정리 (LEO 10-23 «하드 정리 일제히 하자»)

시작 여유 19.8GB/465 (10-23 12:2x) → 37.5GB(④ 후) → **55.7GB**(⑤ 후, 16:4x). 삭제 = `admin/scripts/win_remote_delete.py` 드라이런 → LEO 승인 → `--execute --expect-count`. 판단 기한 10-24 12:00 · 답 없는 폴더는 안 지움.
판단 주체(LEO 직지시): HF 캐시 = hf-playground · 음성 파일 = vocia(가져다 쓸지) · 나머지 = 주인.

| 경로 | 크기 | 주인 | 판단 | 상태 |
|---|---|---|---|---|
| `C:\Users\leo.LEOWIN2\lora_stage` | 141.7GB | 3070 | **ckpt_\* 26개 + qlora_venv 만 지움** · 소용량(.py·.log·gen_samples_*.json·marker) 남김 · 항목별 절대경로로 지울 것 (152353) | |
| `C:\Users\leowin2\ACE-Step-1.5` (+`lora_test`) | 24.3GB | 3070 | 남김 — encore LoRA 시험 ① 10-23 16:30~ (152353) | |
| `C:\Users\leo.LEOWIN2\embed_3070_work` | 8.8GB | 3070 | **전체 지움** — 3070 회수 끝(152510 · out/ 30파일 201,255,083B → reklcli:/Volumes/hitdata/3070/recovered_leowin2_embed_20261023/) | |
| `C:\Users\leowin2.DESKTOP-KSKH97R\egmd` | 8.8GB | 3070 | 남김 (152353) | |
| `C:\Users\leowin2.DESKTOP-KSKH97R\bp_train` | 6.0GB | 3070 | **지움** (152353) | |
| `C:\poc` · `C:\dev` 내용 전부 | 18.18GB | 미상 — 3070 아님(152353) | **지움** — LEO 직접 「4번은 지워」 | ✅ 10-23 16:4x · 24항목 LEFT=0 · 빈 폴더 C:\poc·C:\dev 만 남음(도구가 깊이1 거부) |
| `C:\amt_tools\SongFormer` | 6.7GB | hitmaking | **지움** (152310) | |
| `C:\amt_tools\inbox` 안의 파일만(폴더 유지) | 6.2GB | hitmaking | **지움** (152310) | |
| `C:\Users\leo.LEOWIN2\hitmaking_gpu` | 5.4GB | hitmaking | **지움** (152310) | |
| `C:\amt_tools\venv`·`YourMT3`·`YourMT3_spaces`·`hf_cache`·`hitmaking_gpu` | ≈21.7GB | hitmaking | 남김 (운영 경로) | |
| `C:\RVC` | 16.8GB | vocia | **NAS 보관 후 지움**: logs·datasets·*.log·test_*.wav·스크립트 → NAS / .venv·rvc·assets = 지움 (152355) | |
| `C:\so-vits-svc-fork` | 14.3GB | vocia 판단 | **NAS 보관 후 지움**: dataset·dataset_raw·logs·infer_out → NAS / .venv·코드 = 지움 (152355) | |
| `C:\Users\leowin2\fish-speech` | 7.3GB | vocia 판단 | **NAS 보관 후 지움**: 루트 *.wav·*.npy → NAS / checkpoints·.venv·코드 = 지움 (152355) | |
| `C:\Users\leowin2\GPT-SoVITS` | 4.6GB | vocia 판단 | **지움** (152355) | |
| `C:\Users\leowin2\arena_tts_test` | 5.0GB | vocia 판단 | **NAS 보관 후 지움**: outputs·results·reference_voices·scripts·*.py → NAS / .venv = 지움 (152355) | |
| HF 캐시 `leo.LEOWIN2` | 8.4GB | hf-playground(+vocia 음성 모델) | **지움** — hf 통째 지움(152516)·vocia 음성 모델 지움(152355). token 파일 제외 | |
| HF 캐시 `leowin2.DESKTOP-KSKH97R` | 10.4GB | hf-playground(+vocia 음성 모델) | **큰 모델 4개만 지움**(Qwen2.5-1.5B·Qwen3-TTS 0.6B 2종·XTTS-v2 ≈9.2GB) — 이 계정 = hitmaking 운영 계정이라 1GB 미만 모델은 남김(oven 판단). token 제외 | |
| `C:\comfyui_moss` 가중치 5개 | 18.26GB | oven | **지움** — LEO 직접 「5번 지워」 | ✅ 10-23 16:4x · 5/5 LEFT=0 · ComfyUI 코드·venv 는 남음 |
| `C:\Users\leowin2.DESKTOP-KSKH97R\AppData\Local\CrashDumps` | 2.7GB | 시스템 | 지움 | |

하드웨어(10-23 실측): RAM DDR4 DIMM 16GB(2667)+8GB(3200) · 슬롯 2개 모두 사용 · 보드 최대 64GB → 8GB를 16GB로 교체 시 32GB. 디스크 = Crucial P3 500GB NVMe 1개뿐(두 번째 하드 OS 미인식).

## NAS 보관 규칙 (vocia 152355)
- 실존 가수 자료(gummy·lyn·lee_suhyun·sung_sikyung)는 NAS에 보관하고 지우지 않음 — A-244 LEO 「중앙라이브러리화」.
- 보관 폴더에 README 1줄: 「실존 인물 목소리 · 내부 시험만 · 권리·동의 미기재 = 사용 금지 · 출처 3070 2026-03~06」.
- 이동·삭제 집행 = oven.

## vocia 가 leowin2 로 가져갈 것 (vocia 152355)
- 필수: venv_qwen 은 복사하지 않고 재생성(vocia freeze 목록) · HF Qwen3-TTS-12Hz-1.7B-Base·1.7B-VoiceDesign · ecapa · `C:\vocia\scripts`
- 선택(나중): VoxCPM2 + venv · Qwen3-ASR-1.7B-hf + venv_qasr
- 크기(vocia 164302 실측·HF 이중계수 보정 추정): 필수 ≈13.5GB(1.7B-Base ≈4.2 · 1.7B-VoiceDesign ≈4.2 · ecapa 0.08 · venv_qwen 재생성 ≈5.0 — 목록 leowin `C:\vocia\venv_qwen_freeze_after.txt`) · 선택 VoxCPM2 ≈4.6+venv 5.3 · Qwen3-ASR ≈3.8+venv 4.8
- leowin 잔여물: `C:\vocia\sz_tmp.py`(vocia 임시 스크립트)
