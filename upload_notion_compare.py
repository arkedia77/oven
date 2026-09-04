"""
EXAONE vs Qwen3.6 비교 결과를 Notion에 업로드
"""
import json
import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PARENT_PAGE_ID = "33676e47-daa3-8109-9138-f66938e0c112"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

with open("eval_exaone_results.json", encoding="utf-8") as f:
    exaone = json.load(f)
with open("eval_qwen36_results.json", encoding="utf-8") as f:
    qwen = json.load(f)


def rich_text(text, bold=False):
    obj = {"type": "text", "text": {"content": text[:2000]}}
    if bold:
        obj["annotations"] = {"bold": True}
    return obj


def heading2(text):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [rich_text(text)]},
    }


def heading3(text):
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [rich_text(text)]},
    }


def paragraph(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [rich_text(text[:2000])]},
    }


def table_row(cells):
    return {
        "type": "table_row",
        "table_row": {
            "cells": [[rich_text(c)] for c in cells]
        },
    }


# Build comparison blocks
blocks = []

# Summary section
blocks.append(heading2("종합 요약"))

exaone_avg_speed = sum(r["tokens_per_sec"] for r in exaone["results"]) / 18
qwen_avg_speed = sum(r["tokens_per_sec"] for r in qwen["results"]) / 18
qwen_success = sum(1 for r in qwen["results"] if len(r["response"]) > 0)

blocks.append(paragraph(
    f"테스트 일시: 2026-05-02\n"
    f"테스트 항목: 6카테고리 18개 (한국어, 음악/가사, 코딩, 분석, 포맷, 지식)\n"
    f"서버: 5090 (RTX 5090 32GB VRAM) + llama.cpp, -ngl 99, -c 8192"
))

# Summary table
blocks.append({
    "object": "block",
    "type": "table",
    "table": {
        "table_width": 5,
        "has_column_header": True,
        "has_row_header": False,
        "children": [
            table_row(["항목", "EXAONE 4.0 32B", "Qwen3.6 27B", "비고", ""]),
            table_row(["모델 크기", "21.1GB (Q5_K_M)", "19.5GB (Q5_K_M)", "EXAONE +1.6GB", ""]),
            table_row(["응답 성공", "18/18 (100%)", f"{qwen_success}/18 ({qwen_success*100//18}%)", "Qwen thinking 오버플로", ""]),
            table_row(["평균 속도", f"{exaone_avg_speed:.1f} tok/s", f"{qwen_avg_speed:.1f} tok/s", "Qwen thinking 포함", ""]),
            table_row(["실 응답 속도", "즉시~15s", "13~71s", "Qwen thinking 시간 포함", ""]),
            table_row(["Thinking 모드", "없음", "기본 활성", "실무 시 토큰 낭비 주의", ""]),
        ],
    },
})

# Category comparison
blocks.append(heading2("카테��리별 상세 비교"))

categories = ["한국어", "음악/가사", "코딩", "분석", "포맷", "지식"]
for cat in categories:
    blocks.append(heading3(f"[{cat}]"))
    cat_exaone = [r for r in exaone["results"] if r["category"] == cat]
    cat_qwen = [r for r in qwen["results"] if r["category"] == cat]

    for e, q in zip(cat_exaone, cat_qwen):
        status = "✓" if len(q["response"]) > 0 else "✗ (thinking overflow)"
        blocks.append(paragraph(
            f"● {e['name']}\n"
            f"  EXAONE: {e['elapsed_sec']}s | Qwen: {q['elapsed_sec']}s [{status}]"
        ))

        # Show EXAONE response (truncated)
        exaone_preview = e["response"][:400].replace("\n", " ")
        blocks.append(paragraph(f"  [EXAONE] {exaone_preview}"))

        if len(q["response"]) > 0:
            qwen_preview = q["response"][:400].replace("\n", " ")
            blocks.append(paragraph(f"  [Qwen3.6] {qwen_preview}"))
        else:
            blocks.append(paragraph(f"  [Qwen3.6] (응답 없음 - thinking이 4096 토큰 전부 소모)"))

# Conclusion
blocks.append(heading2("결론 및 권장사항"))
blocks.append(paragraph(
    "1. 안정성: EXAONE 압승 (18/18 vs 13/18). Qwen3.6은 thinking 모드가 기본이라 짧은 max_tokens에서 응답 실패 빈발.\n\n"
    "2. 한국어 품질: EXAONE이 더 자연스러운 한국어 생성. 존댓말/반말 전환, 시적 표현 모두 안정적.\n\n"
    "3. 코딩/분석: 응답이 나온 경우 Qwen3.6도 우수하나, thinking 오버헤드로 실용성 저하.\n\n"
    "4. 속도: 순수 토큰 생성은 Qwen이 약간 빠르나(65 vs 57 tok/s), thinking으로 실제 대기시간은 2-5배 더 김.\n\n"
    "5. 실무 권장:\n"
    "   - 한국어 생성/비평: EXAONE 유지\n"
    "   - 코딩/기술분석: Qwen3.6 (thinking disable 설정 시)\n"
    "   - 가사 파이프라인: EXAONE (안정성 우선)"
))

# Upload to Notion
payload = {
    "parent": {"page_id": PARENT_PAGE_ID},
    "properties": {
        "title": [rich_text("EXAONE 4.0 32B vs Qwen3.6 27B — 로컬 LLM 비교 평가 (2026-05-02)")]
    },
    "children": blocks[:100],  # Notion API limit: 100 blocks per request
}

resp = requests.post(
    "https://api.notion.com/v1/pages",
    headers=HEADERS,
    json=payload,
    timeout=30,
)

if resp.status_code == 200:
    page_id = resp.json()["id"]
    url = resp.json().get("url", "")
    print(f"SUCCESS: Page created!")
    print(f"  ID: {page_id}")
    print(f"  URL: {url}")
else:
    print(f"ERROR {resp.status_code}: {resp.text[:500]}")
