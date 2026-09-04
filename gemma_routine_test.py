#!/usr/bin/env python3
"""
gemma_routine_test.py — Gemma 4 루틴 업무 처리 능력 종합 테스트

3 카테고리:
  A. 데이터/파일 처리 (CLI)
  B. 웹 정보 추출 (Playwright 시뮬레이션)
  C. 판단/의사결정

각 테스트: 태스크 → Gemma 4 응답 → 정답 검증 → 점수
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests

API_URL = "http://100.107.229.5:8080/v1/chat/completions"
MODEL = "gemma-4-26b"
OUTPUT_DIR = Path("routine_test_results")
OUTPUT_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT = """\
당신은 루틴 업무를 정확하고 효율적으로 처리하는 AI 어시스턴트입니다.

규칙:
1. 모든 응답은 JSON 형식으로 반환하세요.
2. 주어진 데이터를 정확히 분석하고, 요청된 형식으로 출력하세요.
3. 판단이 필요한 경우 근거를 명시하세요.
4. 추가 정보가 없으면 있는 정보만으로 최선의 답을 내세요.
"""


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def ask_gemma(system: str, user: str, temperature: float = 0.3) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    payload = {
        "model": MODEL, "messages": messages,
        "temperature": temperature, "max_tokens": 4096,
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning_content") or ""
    except Exception as e:
        return f"ERROR: {e}"


def extract_json(text: str) -> dict | list | None:
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'(\{[\s\S]*\})',
        r'(\[[\s\S]*\])',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    return None


# ============================================================
# A. 데이터/파일 처리 테스트
# ============================================================
CATEGORY_A = [
    {
        "id": "A1",
        "name": "CSV 파싱 + 집계",
        "difficulty": "easy",
        "prompt": """다음 CSV 데이터를 분석하세요:

name,department,salary
김철수,개발,5200
이영희,마케팅,4800
박민수,개발,6100
최지은,디자인,4500
정하나,마케팅,5100
한동욱,개발,5800

JSON으로 답해주세요:
{
  "total_employees": 숫자,
  "avg_salary": 숫자 (소수점 없이),
  "department_count": {"부서명": 인원수, ...},
  "highest_paid": {"name": "이름", "salary": 숫자}
}""",
        "validate": lambda r: (
            r.get("total_employees") == 6
            and r.get("avg_salary") in [5250, 5233, 5234]
            and r.get("department_count", {}).get("개발") == 3
            and r.get("highest_paid", {}).get("name") == "박민수"
        ),
    },
    {
        "id": "A2",
        "name": "JSON 변환 + 필터링",
        "difficulty": "medium",
        "prompt": """다음 JSON 데이터에서 조건에 맞는 항목만 추출하세요.

데이터:
[
  {"id": 1, "title": "Python 기초", "category": "programming", "rating": 4.5, "students": 1200},
  {"id": 2, "title": "마케팅 전략", "category": "business", "rating": 3.8, "students": 800},
  {"id": 3, "title": "React 심화", "category": "programming", "rating": 4.8, "students": 950},
  {"id": 4, "title": "데이터 분석", "category": "data", "rating": 4.2, "students": 1500},
  {"id": 5, "title": "UX 디자인", "category": "design", "rating": 4.0, "students": 600},
  {"id": 6, "title": "Node.js API", "category": "programming", "rating": 4.6, "students": 700}
]

조건: rating >= 4.5 AND students >= 700

JSON으로 답해주세요:
{
  "filtered": [{"id": 숫자, "title": "제목"}, ...],
  "count": 숫자
}""",
        "validate": lambda r: (
            r.get("count") == 3
            and len(r.get("filtered", [])) == 3
            and set(item["id"] for item in r.get("filtered", [])) == {1, 3, 6}
        ),
    },
    {
        "id": "A3",
        "name": "로그 파싱 + 에러 분류",
        "difficulty": "hard",
        "prompt": """다음 서버 로그를 분석하세요:

[2026-05-09 10:23:45] INFO  - User login: user_id=1042
[2026-05-09 10:23:46] ERROR - Database connection timeout: host=db-primary, retry=3/3
[2026-05-09 10:23:47] WARN  - High memory usage: 87% (threshold: 80%)
[2026-05-09 10:23:48] INFO  - API request: GET /api/users, status=200, latency=45ms
[2026-05-09 10:23:49] ERROR - Null pointer exception in UserService.getProfile(), line 142
[2026-05-09 10:23:50] INFO  - Cache hit ratio: 92%
[2026-05-09 10:23:51] ERROR - Database connection timeout: host=db-primary, retry=3/3
[2026-05-09 10:23:52] WARN  - Disk usage: 91% on /var/log
[2026-05-09 10:23:53] INFO  - Scheduled job completed: backup_daily, duration=12s
[2026-05-09 10:23:54] ERROR - Authentication failed: ip=203.0.113.42, attempts=5

JSON으로 답해주세요:
{
  "summary": {
    "total_lines": 숫자,
    "by_level": {"INFO": 숫자, "ERROR": 숫자, "WARN": 숫자}
  },
  "errors": [
    {"type": "에러유형", "count": 발생횟수, "severity": "high|medium|low"}
  ],
  "action_items": ["즉시 조치가 필요한 항목 (우선순위순)"]
}""",
        "validate": lambda r: (
            r.get("summary", {}).get("total_lines") == 10
            and r.get("summary", {}).get("by_level", {}).get("ERROR") == 4
            and r.get("summary", {}).get("by_level", {}).get("WARN") == 2
            and r.get("summary", {}).get("by_level", {}).get("INFO") == 4
            and len(r.get("errors", [])) >= 3
        ),
    },
]


# ============================================================
# B. 웹 정보 추출 테스트 (HTML 파싱 시뮬레이션)
# ============================================================
CATEGORY_B = [
    {
        "id": "B1",
        "name": "HTML 테이블 추출",
        "difficulty": "easy",
        "prompt": """다음 HTML에서 테이블 데이터를 추출하세요:

<table>
  <thead>
    <tr><th>제품</th><th>가격</th><th>재고</th></tr>
  </thead>
  <tbody>
    <tr><td>노트북 A</td><td>1,200,000</td><td>15</td></tr>
    <tr><td>모니터 B</td><td>450,000</td><td>0</td></tr>
    <tr><td>키보드 C</td><td>89,000</td><td>42</td></tr>
    <tr><td>마우스 D</td><td>35,000</td><td>100</td></tr>
  </tbody>
</table>

JSON으로 답해주세요:
{
  "products": [{"name": "이름", "price": 숫자, "stock": 숫자}, ...],
  "out_of_stock": ["품절 제품명"],
  "total_value": 전체 재고 가치 합계 (가격 × 재고)
}""",
        "validate": lambda r: (
            len(r.get("products", [])) == 4
            and r.get("out_of_stock") == ["모니터 B"]
            and r.get("total_value") == (1200000*15 + 450000*0 + 89000*42 + 35000*100)
        ),
    },
    {
        "id": "B2",
        "name": "구조화된 웹 데이터 추출",
        "difficulty": "medium",
        "prompt": """다음 HTML 구조에서 정보를 추출하세요:

<div class="job-listing">
  <div class="job-card" data-id="J001">
    <h3>시니어 백엔드 개발자</h3>
    <span class="company">테크스타트</span>
    <span class="location">서울 강남</span>
    <span class="salary">7000-9000만원</span>
    <div class="tags">
      <span class="tag">Python</span>
      <span class="tag">Django</span>
      <span class="tag">AWS</span>
    </div>
    <span class="posted">2026-05-07</span>
  </div>
  <div class="job-card" data-id="J002">
    <h3>프론트엔드 엔지니어</h3>
    <span class="company">클라우드원</span>
    <span class="location">서울 판교</span>
    <span class="salary">5500-7000만원</span>
    <div class="tags">
      <span class="tag">React</span>
      <span class="tag">TypeScript</span>
    </div>
    <span class="posted">2026-05-08</span>
  </div>
  <div class="job-card" data-id="J003">
    <h3>데이터 엔지니어</h3>
    <span class="company">데이터랩</span>
    <span class="location">부산 해운대</span>
    <span class="salary">6000-8000만원</span>
    <div class="tags">
      <span class="tag">Python</span>
      <span class="tag">Spark</span>
      <span class="tag">Kafka</span>
    </div>
    <span class="posted">2026-05-06</span>
  </div>
</div>

JSON으로 답해주세요:
{
  "jobs": [
    {"id": "J00X", "title": "제목", "company": "회사", "location": "위치",
     "salary_min": 숫자, "salary_max": 숫자, "tags": ["태그"], "posted": "날짜"}
  ],
  "python_jobs": ["Python 태그가 있는 job id 목록"],
  "highest_paying": "최고 연봉 상한 job id"
}""",
        "validate": lambda r: (
            len(r.get("jobs", [])) == 3
            and set(r.get("python_jobs", [])) == {"J001", "J003"}
            and r.get("highest_paying") == "J001"
        ),
    },
]


# ============================================================
# C. 판단/의사결정 테스트
# ============================================================
CATEGORY_C = [
    {
        "id": "C1",
        "name": "이메일 우선순위 분류",
        "difficulty": "easy",
        "prompt": """다음 5개 이메일의 우선순위를 분류하세요:

1. 제목: "서버 다운 - 긴급 대응 필요"
   보낸이: ops-alert@company.com
   내용: "프로덕션 서버가 10분 전부터 응답 없음. 즉시 확인 바랍니다."

2. 제목: "다음 주 팀 회식 장소 투표"
   보낸이: team-lead@company.com
   내용: "다음 주 금요일 회식 장소를 정하려고 합니다. 선호하는 곳에 투표해주세요."

3. 제목: "Q2 리포트 제출 마감 (내일까지)"
   보낸이: cfo@company.com
   내용: "내일 오후 5시까지 Q2 실적 리포트를 제출해주세요."

4. 제목: "뉴스레터: AI 트렌드 2026"
   보낸이: newsletter@techblog.com
   내용: "이번 달 AI 뉴스 정리..."

5. 제목: "보안 패치 긴급 적용 요청"
   보낸이: security@company.com
   내용: "CVE-2026-XXXX 취약점 발견. 24시간 내 패치 적용 필수."

JSON으로 답해주세요:
{
  "priority": [
    {"email_num": 숫자, "level": "critical|high|medium|low", "reason": "이유"}
  ],
  "action_order": [이메일 번호를 처리 순서대로]
}""",
        "validate": lambda r: (
            r.get("action_order", [None])[0] == 1
            and any(e["email_num"] == 1 and e["level"] == "critical"
                    for e in r.get("priority", []))
            and any(e["email_num"] == 4 and e["level"] == "low"
                    for e in r.get("priority", []))
        ),
    },
    {
        "id": "C2",
        "name": "리소스 할당 최적화",
        "difficulty": "medium",
        "prompt": """다음 상황에서 서버 리소스를 할당하세요:

가용 서버: 5대 (각 8 CPU, 32GB RAM)

요청된 서비스:
1. API 서버 (필수): CPU 4, RAM 8GB, 최소 2대 (HA)
2. 배치 처리 (필수): CPU 8, RAM 16GB, 최소 1대
3. 모니터링 (선택): CPU 2, RAM 4GB, 1대
4. 개발 서버 (선택): CPU 4, RAM 16GB, 1대
5. AI 추론 (선택): CPU 8, RAM 32GB, 1대

제약:
- 필수 서비스는 반드시 배치
- 한 서버에 여러 서비스 가능 (리소스 합이 서버 한계 이내)
- 남는 서버가 있으면 개발용으로 활용

JSON으로 답해주세요:
{
  "allocation": [
    {"server": 1, "services": [{"name": "서비스명", "cpu": 숫자, "ram": 숫자}], "cpu_used": 숫자, "ram_used": 숫자}
  ],
  "unallocated_services": ["배치 못한 서비스"],
  "utilization": 전체 CPU 사용률 (%)
}""",
        "validate": lambda r: (
            # API 서버가 2대 이상에 배치되었는지
            sum(1 for s in r.get("allocation", [])
                if any(svc["name"] in ["API 서버", "API서버", "api_server", "API"]
                       for svc in s.get("services", [])))
            >= 2
            # 배치 처리가 배치되었는지
            and any(
                any(svc["name"] in ["배치 처리", "배치처리", "batch", "배치"]
                    for svc in s.get("services", []))
                for s in r.get("allocation", [])
            )
        ),
    },
    {
        "id": "C3",
        "name": "이상 탐지 + 근본 원인 분석",
        "difficulty": "hard",
        "prompt": """다음 시계열 메트릭 데이터에서 이상을 탐지하고 원인을 분석하세요:

시간 | CPU(%) | MEM(%) | Disk I/O(MB/s) | Network(Mbps) | Error Rate(%)
10:00 | 25 | 45 | 12 | 100 | 0.1
10:05 | 28 | 46 | 15 | 105 | 0.1
10:10 | 30 | 47 | 14 | 98  | 0.2
10:15 | 45 | 52 | 80 | 110 | 0.5
10:20 | 78 | 68 | 250 | 95  | 2.5
10:25 | 92 | 85 | 310 | 45  | 8.3
10:30 | 95 | 91 | 280 | 30  | 15.2
10:35 | 88 | 87 | 200 | 55  | 12.1
10:40 | 60 | 72 | 90  | 80  | 5.0
10:45 | 35 | 55 | 20  | 95  | 0.8

JSON으로 답해주세요:
{
  "anomaly_detected": true/false,
  "anomaly_window": {"start": "시간", "end": "시간"},
  "affected_metrics": ["영향받은 메트릭 목록"],
  "root_cause_hypothesis": "가장 가능성 높은 원인",
  "evidence": ["근거 목록"],
  "severity": "critical|high|medium|low",
  "recommendation": ["조치 사항"]
}""",
        "validate": lambda r: (
            r.get("anomaly_detected") is True
            and "10:15" <= r.get("anomaly_window", {}).get("start", "99:99") <= "10:20"
            and "Disk" in str(r.get("affected_metrics", []))
                or "disk" in str(r.get("affected_metrics", [])).lower()
                or "I/O" in str(r.get("affected_metrics", []))
            and r.get("severity") in ["critical", "high"]
        ),
    },
]


# ============================================================
# Runner
# ============================================================
def run_test(test: dict) -> dict:
    log(f"  [{test['id']}] {test['name']} ({test['difficulty']})...")
    start = time.time()
    response = ask_gemma(SYSTEM_PROMPT, test["prompt"])
    elapsed = time.time() - start

    parsed = extract_json(response)
    if parsed is None:
        log(f"    ❌ JSON 파싱 실패")
        return {
            "id": test["id"], "name": test["name"],
            "difficulty": test["difficulty"],
            "passed": False, "parse_error": True,
            "elapsed": round(elapsed, 1),
            "raw_response": response[:500],
        }

    try:
        passed = test["validate"](parsed)
    except Exception as e:
        passed = False
        log(f"    ⚠ 검증 오류: {e}")

    status = "✅" if passed else "❌"
    log(f"    {status} ({elapsed:.1f}s)")

    return {
        "id": test["id"], "name": test["name"],
        "difficulty": test["difficulty"],
        "passed": passed, "parse_error": False,
        "elapsed": round(elapsed, 1),
        "response": parsed,
        "raw_response": response[:1000],
    }


def main():
    log("=" * 60)
    log("Gemma 4 루틴 업무 처리 능력 종합 테스트")
    log("=" * 60)

    all_tests = {
        "A. 데이터/파일 처리": CATEGORY_A,
        "B. 웹 정보 추출": CATEGORY_B,
        "C. 판단/의사결정": CATEGORY_C,
    }

    results = {}
    total_pass = 0
    total_tests = 0

    for category, tests in all_tests.items():
        log(f"\n--- {category} ---")
        cat_results = []
        for test in tests:
            result = run_test(test)
            cat_results.append(result)
            if result["passed"]:
                total_pass += 1
            total_tests += 1
        results[category] = cat_results

    # Summary
    log(f"\n{'=' * 60}")
    log(f"최종 결과: {total_pass}/{total_tests} 통과 ({total_pass*100//total_tests}%)")
    log(f"{'=' * 60}")

    for category, cat_results in results.items():
        cat_pass = sum(1 for r in cat_results if r["passed"])
        log(f"  {category}: {cat_pass}/{len(cat_results)}")
        for r in cat_results:
            status = "✅" if r["passed"] else "❌"
            log(f"    {status} [{r['id']}] {r['name']} ({r['difficulty']}) - {r['elapsed']}s")

    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "total_pass": total_pass,
        "total_tests": total_tests,
        "pass_rate": f"{total_pass*100//total_tests}%",
        "results": results,
    }
    report_path = OUTPUT_DIR / "routine_test_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\n리포트 저장: {report_path}")


if __name__ == "__main__":
    main()
