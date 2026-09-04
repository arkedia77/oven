"""
EXAONE 4.0 32B vs Qwen3.6-27B 비교 평가
LeoFamily 실무 기준 테스트
"""
import json
import time
import requests
from datetime import datetime

API_URL = "http://100.107.229.5:8080/v1/chat/completions"

TESTS = [
    # 1. 한국어 자연스러움
    {
        "id": "kr_honorific",
        "category": "한국어",
        "name": "존댓말 비즈니스 메일",
        "prompt": "다음 상황에 맞는 비즈니스 이메일을 작성하세요: 협업 파트너에게 프로젝트 일정이 2주 지연됨을 알리면서, 대안 일정을 제안하는 메일. 200자 내외.",
        "criteria": ["존댓말 일관성", "비즈니스 톤", "구체적 대안 포함", "자연스러운 한국어"]
    },
    {
        "id": "kr_casual",
        "category": "한국어",
        "name": "반말 대화체",
        "prompt": "친구에게 카톡으로 보내는 메시지처럼 써줘. 내용: 오늘 저녁에 홍대에서 만나서 새로 생긴 라멘집 가자고 제안하는 거. 이모티콘 없이, 진짜 한국 20대가 쓰는 말투로.",
        "criteria": ["자연스러운 반말", "20대 말투", "카톡 스타일", "과하지 않음"]
    },
    {
        "id": "kr_creative",
        "category": "한국어",
        "name": "짧은 시 창작",
        "prompt": "비 오는 서울 지하철 창밖을 바라보는 장면을 4줄 시로 써주세요. 한국 현대시 스타일로.",
        "criteria": ["시적 표현", "이미지 선명도", "한국적 정서", "4줄 준수"]
    },
    {
        "id": "kr_summary",
        "category": "한국어",
        "name": "한국어 요약",
        "prompt": "다음 텍스트를 3줄로 요약하세요:\n\n인공지능 음악 생성 기술은 최근 몇 년간 눈부신 발전을 이루었다. 특히 Transformer 기반 모델들이 멜로디, 화성, 리듬을 동시에 학습할 수 있게 되면서, 과거의 단순한 패턴 반복에서 벗어나 인간 작곡가의 스타일을 모방할 수 있는 수준에 이르렀다. 그러나 여전히 장기적 구조(예: 소나타 형식의 발전부)를 일관성 있게 유지하는 것은 어려운 과제로 남아 있으며, 이를 해결하기 위해 계층적 생성 모델이나 강화학습 기반 접근법이 연구되고 있다. 또한 생성된 음악의 저작권 문제, 학습 데이터의 윤리적 사용, 그리고 AI 음악이 인간 음악가의 창작 활동에 미치는 영향에 대한 사회적 논의도 활발히 진행 중이다.",
        "criteria": ["핵심 포착", "3줄 준수", "정보 손실 최소", "자연스러운 문장"]
    },
    # 2. 가사/음악 관련
    {
        "id": "music_lyrics",
        "category": "음악/가사",
        "name": "한국어 가사 작성",
        "prompt": "테마: '새벽 산책'. 장르: 어쿠스틱 발라드. 1절 가사(verse + chorus)를 작성하세요. 조건: 7-8음절/행, 라임 포함, 한국어.",
        "criteria": ["음절 수 준수", "라임 존재", "테마 반영", "노래 가능성"]
    },
    {
        "id": "music_review",
        "category": "음악/가사",
        "name": "가사 비평",
        "prompt": "다음 가사를 비평하고 개선점을 제안하세요:\n\n밤하늘에 별이 빛나\n너를 생각하면 눈물이 나\n우리 함께한 시간들이\n모래처럼 흩어져 가\n\n평가 기준: 독창성, 이미지 구체성, 감정 전달력. 각 항목 10점 만점으로 점수를 매기고 이유를 설명하세요.",
        "criteria": ["점수 체계 준수", "구체적 근거", "개선 제안 실용성", "음악적 이해"]
    },
    {
        "id": "music_translate",
        "category": "음악/가사",
        "name": "가사 영한 번역",
        "prompt": "다음 영어 가사를 한국어로 번역하되, 노래로 부를 수 있게 음절 수를 맞추세요:\n\nWalking through the rain alone\nSearching for a place called home\nEvery step I take is slow\nBut I know where I need to go",
        "criteria": ["음절 수 유사", "의미 보존", "노래 가능성", "자연스러운 한국어"]
    },
    # 3. 코딩
    {
        "id": "code_python",
        "category": "코딩",
        "name": "Python 함수 작성",
        "prompt": "MIDI 파일에서 노트 이벤트를 읽어 BPM을 추정하는 Python 함수를 작성하세요. mido 라이브러리를 사용하고, onset 간격의 중앙값으로 BPM을 계산합니다.",
        "criteria": ["정확한 로직", "mido API 올바른 사용", "에지 케이스 처리", "코드 품질"]
    },
    {
        "id": "code_debug",
        "category": "코딩",
        "name": "버그 찾기",
        "prompt": "다음 코드의 버그를 찾고 수정하세요:\n\n```python\ndef moving_average(data, window=3):\n    result = []\n    for i in range(len(data)):\n        start = max(0, i - window)\n        end = i + 1\n        avg = sum(data[start:end]) / window\n        result.append(avg)\n    return result\n```",
        "criteria": ["버그 정확히 식별", "수정 올바름", "설명 명확", "추가 개선 제안"]
    },
    {
        "id": "code_explain",
        "category": "코딩",
        "name": "코드 설명 (한국어)",
        "prompt": "다음 PyTorch 코드가 무엇을 하는지 한국어로 설명하세요. 비전공자도 이해할 수 있게:\n\n```python\nclass LoRALayer(nn.Module):\n    def __init__(self, in_dim, out_dim, rank=4):\n        super().__init__()\n        self.lora_A = nn.Parameter(torch.randn(in_dim, rank) * 0.01)\n        self.lora_B = nn.Parameter(torch.zeros(rank, out_dim))\n    \n    def forward(self, x):\n        return x @ self.lora_A @ self.lora_B\n```",
        "criteria": ["정확한 설명", "비전공자 이해 가능", "비유 활용", "LoRA 개념 전달"]
    },
    # 4. 분석/비평
    {
        "id": "analysis_compare",
        "category": "분석",
        "name": "기술 비교 분석",
        "prompt": "AI 음악 생성에서 Transformer 기반 접근법(예: MusicGen)과 Diffusion 기반 접근법(예: Stable Audio)의 장단점을 표로 비교하세요. 항목: 음질, 생성 속도, 제어 가능성, 학습 데이터 효율성.",
        "criteria": ["정확한 기술 이해", "표 형식 준수", "균형잡힌 비교", "실무 관점"]
    },
    {
        "id": "analysis_scoring",
        "category": "분석",
        "name": "구조화된 평가",
        "prompt": "다음 프로젝트 제안서를 평가하세요:\n\n'AI 피아노 연주 엔진 개발. MIDI를 입력받아 인간처럼 자연스러운 연주(velocity, pedal, timing 변화)를 생성. 데이터: 15만 MIDI 청크. 모델: LoRA 파인튜닝. 목표: 블라인드 테스트에서 인간 연주와 구분 불가.'\n\n평가 항목: 실현 가능성(10), 혁신성(10), 비즈니스 가치(10), 기술적 완성도(10). JSON으로 출력.",
        "criteria": ["JSON 형식 정확", "점수 합리성", "근거 명확", "실무 이해도"]
    },
    # 5. 지시 따르기 (포맷 제약)
    {
        "id": "format_json",
        "category": "포맷",
        "name": "JSON 출력",
        "prompt": "다음 정보를 JSON으로 구조화하세요. 추가 설명 없이 JSON만 출력:\n\n프로젝트명: Quincy Piano Engine\n단계: Phase 3\n상태: 학습 대기\n모델: LoRA\n데이터: 154,594 chunks\nGPU: RTX 5090\n예상 소요: 8시간",
        "criteria": ["유효한 JSON", "모든 필드 포함", "추가 텍스트 없음", "적절한 키 네이밍"]
    },
    {
        "id": "format_markdown",
        "category": "포맷",
        "name": "마크다운 테이블",
        "prompt": "다음 데이터를 마크다운 테이블로 만드세요. 열: 모델명, 파라미터, 양자화, 파일크기, VRAM 필요량\n\n- EXAONE 4.0 32B, 32B params, Q5_K_M, 21.1GB, ~26GB\n- Qwen3.6 27B, 27B params, Q5_K_M, 19.5GB, ~24GB\n- Llama 3.1 70B, 70B params, Q4_K_M, 40.8GB, ~44GB",
        "criteria": ["올바른 마크다운 문법", "정렬", "데이터 정확성", "추가 설명 최소"]
    },
    {
        "id": "format_constraint",
        "category": "포맷",
        "name": "글자수 제약",
        "prompt": "AI 음악 생성의 미래를 정확히 50자(공백 포함)로 설명하세요. 50자를 넘거나 모자라면 안 됩니다.",
        "criteria": ["정확히 50자", "의미 전달", "완결된 문장"]
    },
    # 6. 일반 지식/추론
    {
        "id": "knowledge_music",
        "category": "지식",
        "name": "음악 이론 지식",
        "prompt": "쇼팽 발라드 1번의 형식 구조를 설명하고, 이 곡이 전통적인 소나타 형식과 어떻게 다른지 비교하세요.",
        "criteria": ["정확한 음악 지식", "구체적 마디/섹션 언급", "비교 논리", "한국어 품질"]
    },
    {
        "id": "knowledge_tech",
        "category": "지식",
        "name": "기술 지식",
        "prompt": "LoRA(Low-Rank Adaptation)와 QLoRA의 차이점을 설명하고, 각각 어떤 상황에서 선택해야 하는지 실무 관점에서 조언하세요.",
        "criteria": ["기술적 정확성", "차이점 명확", "실무 조언 실용성", "한국어 품질"]
    },
    {
        "id": "knowledge_reasoning",
        "category": "지식",
        "name": "논리 추론",
        "prompt": "A는 B보다 코딩을 잘하고, C는 A보다 음악을 잘합니다. B는 C보다 글을 잘 씁니다. D는 모든 영역에서 B보다 잘합니다. 음악을 가장 잘하는 사람은 누구인가요? 단계별로 추론하세요.",
        "criteria": ["정확한 답", "단계별 추론", "논리 일관성", "명확한 표현"]
    },
]


def run_test(test, model_name="unknown", temperature=0.7, max_tokens=4096):
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": test["prompt"]}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    start = time.time()
    try:
        resp = requests.post(API_URL, json=payload, timeout=120)
        elapsed = time.time() - start
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {})
        return {
            "id": test["id"],
            "category": test["category"],
            "name": test["name"],
            "response": content,
            "elapsed_sec": round(elapsed, 2),
            "prompt_tokens": tokens.get("prompt_tokens", 0),
            "completion_tokens": tokens.get("completion_tokens", 0),
            "tokens_per_sec": round(tokens.get("completion_tokens", 0) / elapsed, 1) if elapsed > 0 else 0,
        }
    except Exception as e:
        return {
            "id": test["id"],
            "category": test["category"],
            "name": test["name"],
            "response": f"ERROR: {e}",
            "elapsed_sec": time.time() - start,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "tokens_per_sec": 0,
        }


def run_all(model_name, output_file):
    print(f"\n{'='*60}")
    print(f"  Testing: {model_name}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = []
    for i, test in enumerate(TESTS, 1):
        print(f"  [{i}/{len(TESTS)}] {test['category']} > {test['name']}...", end=" ", flush=True)
        result = run_test(test, model_name)
        results.append(result)
        print(f"✓ {result['elapsed_sec']}s ({result['tokens_per_sec']} tok/s)")
        time.sleep(0.5)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "model": model_name,
            "timestamp": datetime.now().isoformat(),
            "tests": TESTS,
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n  Results saved to {output_file}")
    return results


if __name__ == "__main__":
    import sys
    model_name = sys.argv[1] if len(sys.argv) > 1 else "exaone"
    output_file = sys.argv[2] if len(sys.argv) > 2 else f"eval_{model_name}_results.json"
    run_all(model_name, output_file)
