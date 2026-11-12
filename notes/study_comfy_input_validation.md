# 스터디 — ComfyUI API 그래프 입력 검증 규칙 (A-177 learning · 시한 11-12 → 11-13 종결, 1일 늦음)

대상: leowin `C:\comfyui_moss\ComfyUI` v0.44.2 `execution.py` `validate_inputs()`(852행~)·`get_input_data()`(164행~), `comfy_api/latest/_io.py`.
⚠ docs.comfy.org «server routes» 문서는 이번에 안 봄 — 근거는 소스 + 실측뿐.

## 규칙 (소스 근거)
| 경우 | 결과 | 근거 |
|---|---|---|
| required 칸 빠짐 | **400 `required_input_missing`** — object_info `default` 로 안 채움 | `if x not in inputs: if input_category == "required": errors.append` |
| optional 칸 빠짐 | 통과 · 노드 함수에 kwarg 안 감 → **파이썬 함수 기본값**(object_info default 아님) | 같은 줄 `continue` |
| `advanced: true` 칸 | 검증에서 따로 안 다룸 = 화면 표시용 표지. required 면 그대로 required(0.44.2 object_info 에 advanced+required 415칸) | execution.py 에 `advanced` 0회 · `_io.py` as_dict 에만 |
| 모르는 칸(사라진 칸) | 검사 안 함 · 실행 입력에서 **조용히 버림**(V3 `ACCEPT_ALL_INPUTS` 노드만 예외) | `valid_inputs` 만 순회 · get_input_data `elif input_category is not None` |
| 콤보 값이 선택지 밖 | **400 `value_not_in_list`** | 옛 표기 `[[선택지…], {..}]` · V3 `["COMBO", {"options": [...]}]` 둘 다 검사 |
| INT/FLOAT/STRING/BOOLEAN | 먼저 형변환(`int()` 등) → 실패하면 400 `invalid_input_type` | |
| min 미만 / max 초과 | **400** `value_smaller_than_min` / `value_bigger_than_max` | 노드가 VALIDATE_INPUTS 로 그 칸을 직접 받으면 건너뜀 |
| 연결 타입 불일치 | 400 `return_type_mismatch` | 출력 순서 바뀜 = 연결 번호 어긋남 |
| V3 동적 입력(점 표기 `a.b`) | `get_finalized_class_inputs` 가 보낸 입력 보고 칸 목록을 펼친 뒤 같은 규칙 · 오류 표시는 마지막 조각 | ⚠ 펼침 규칙 자체는 안 읽음(미측정) |

## 실측 (11-13 08:3x · leowin /prompt, 실행 0 — 검증 단계에서 400)
- `EmptyLatentImage{width:1, bogus_key:5}` → width `value_smaller_than_min`(min 16) · **bogus_key 오류 없음**(조용히 버림 확인)
- `EmptyLatentImage` width 빠짐(default 1024 있음) → `required_input_missing` (기본값 안 채움 확인)
- 11-09: `TextEncodeMOSSImageEdit` image_strength 빠짐 → 400 (같은 규칙)

## 대조 스크립트 ⑥ 에 반영 (oven `tools/comfy_upgrade_diff.py`)
- ✚ V3 콤보(`"COMBO"`+options, 0.44.2 에 550칸 · 옛 표기 114칸) 선택지 사라짐 검사 — **전엔 옛 표기만 봐서 V3 콤보 놓침**
- ✚ min 올라감 / max 내려감 = 위험 · 기본값 변화 = 참고
- ✎ «required 칸 사라짐» 위험 → **참고**로 내림(400 아님, 조용히 버려짐 — 동작 변화는 실생성으로)
- 재실행(11-09 스냅숏): 21종 위험 1(image_strength, 변화 없음) · 전 노드 위험 1 → **3**(새로 OpenAIChatNode·OpenAIGPTImage1 model 선택지 사라짐 — API 노드, LEOstudio 밖) · 자기대조 rc 0
