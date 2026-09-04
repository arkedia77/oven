#!/usr/bin/env python3
"""
gemma_researcher_search.py — Search-augmented research orchestrator.
Enhances gemma_researcher.py with web search (Wikipedia + Semantic Scholar + DuckDuckGo)
to inject factual context before each sub-question.

Usage:
    python3 gemma_researcher_search.py --topic "연구 주제" [--max-sessions 5] [--output-dir research_search]
"""

import argparse
import json
import re
import signal
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests as req

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL = "http://100.107.229.5:8080/v1/chat/completions"
MODEL = "gemma-4-26b"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2

SYSTEM_PROMPT = """\
당신은 심층 연구를 수행하는 전문 연구원입니다.

핵심 규칙:
1. 한 번의 응답에서 하나의 측면만 깊이 파고드세요. 절대 전체를 요약하려 하지 마세요.
2. 모든 주장에는 구체적 근거(사례, 데이터, 학술 문헌)를 제시하세요.
3. 제공된 참고자료를 적극적으로 인용하고 분석하세요. 참고자료에 있는 구체적 명칭, 분류, 수치를 반드시 포함하세요.
4. 최소 2000자 이상 상세하게 서술하세요.
5. 결론이나 요약을 내지 마세요. 공간이 부족하면 "CONTINUE"라고 쓰세요.
6. "[[RESEARCH_COMPLETE]]" 태그는 절대 사용하지 마세요.
7. 한국어로 응답하세요.
8. 참고자료의 출처(저자명, 논문명, 연도)를 인용 표기하세요.
"""

PLANNING_PROMPT = """\
다음 연구 주제를 분석하기 위한 연구 계획을 세워주세요.

주제: {topic}

아래 형식으로 출력하세요:
## 연구 하위 질문
(이 주제를 깊이 탐구하기 위한 구체적 하위 질문 8~12개를 번호 목록으로)

## 조사 순서
(어떤 순서로 탐구할지, 이유와 함께)

각 하위 질문은 독립적으로 깊이 있는 분석이 가능할 만큼 구체적이어야 합니다.
"""

HANDOFF_PROMPT = """\
지금까지의 연구 내용을 아래 형식으로 정리해주세요. 최소 2000자 이상으로 상세히 작성하세요.
인용한 출처를 모두 포함해주세요.

## 핵심 발견사항
(주요 발견을 번호 목록으로, 각각 2-3문장 이상, 출처 포함)

## 분석된 측면
(이미 다룬 각도/관점, 각각의 깊이 평가)

## 미탐구 영역
(아직 조사하지 않은 부분)

## 잠정적 결론
(현재까지의 종합 판단)

## 다음 세션에서 탐구할 질문
(구체적 후속 질문 5-8개)

## 참고문헌
(인용한 모든 출처 목록)
"""

CONTINUATION_TEMPLATE = """\
이전 세션의 연구 요약을 바탕으로 연구를 이어가세요.

--- 이전 연구 요약 ---
{summary}
--- 요약 끝 ---

위 요약에서 "미탐구 영역"과 "다음 세션에서 탐구할 질문"을 중심으로 연구를 계속하세요.
첫 번째 미탐구 질문부터 시작하세요.
"""

FINAL_REPORT_PROMPT = """\
아래는 여러 세션에 걸쳐 수행한 연구의 요약들입니다.
이를 종합하여 하나의 체계적인 최종 보고서를 작성해주세요.
최소 4000자 이상으로 상세히 작성하세요.
인용한 모든 출처를 참고문헌 섹션에 포함하세요.

구조:
1. 서론 (연구 주제 및 범위)
2. 핵심 발견사항
3. 상세 분석 (각 세션의 발견을 통합, 구체적 분류/수치 포함)
4. 반론 및 한계
5. 실무 시사점
6. 결론
7. 참고문헌

--- 세션별 요약 ---
{all_summaries}
--- 요약 끝 ---
"""


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Search engines
# ---------------------------------------------------------------------------
class SearchEngine:
    """Multi-source search: Wikipedia (ko+en) + Semantic Scholar + DuckDuckGo."""

    HEADERS = {
        "User-Agent": "GemmaResearcher/1.0 (music research project; contact: beomjun.lee@gmail.com)"
    }

    @staticmethod
    def _shorten_query(query: str, max_words: int = 6) -> str:
        """Shorten and clean query for API search."""
        clean = re.sub(r'\*\*|[()（）「」\[\]{}:·—,，]', ' ', query)
        words = [w for w in clean.split() if len(w) > 1]
        return " ".join(words[:max_words])

    @staticmethod
    def search_wikipedia(query: str, lang: str = "en", max_results: int = 3) -> list[dict]:
        """Search Wikipedia and return article summaries."""
        query = SearchEngine._shorten_query(query)
        results = []
        try:
            search_url = f"https://{lang}.wikipedia.org/w/api.php"
            params = {
                "action": "query", "list": "search",
                "srsearch": query, "format": "json",
                "srlimit": max_results
            }
            resp = req.get(search_url, params=params, headers=SearchEngine.HEADERS, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get("query", {}).get("search", [])

            for hit in hits:
                title = hit["title"]
                content_url = f"https://{lang}.wikipedia.org/w/api.php"
                content_params = {
                    "action": "query", "titles": title,
                    "prop": "extracts", "explaintext": "1",
                    "format": "json", "exlimit": "1"
                }
                cresp = req.get(content_url, params=content_params, headers=SearchEngine.HEADERS, timeout=10)
                cresp.raise_for_status()
                pages = cresp.json().get("query", {}).get("pages", {})
                for _, page in pages.items():
                    extract = page.get("extract", "")
                    if extract and len(extract) > 100:
                        results.append({
                            "source": f"Wikipedia ({lang})",
                            "title": title,
                            "content": extract[:3000],
                            "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                        })
        except Exception as e:
            log(f"    Wikipedia ({lang}) 검색 실패: {e}")
        return results

    @staticmethod
    def search_semantic_scholar(query: str, max_results: int = 5) -> list[dict]:
        """Search Semantic Scholar for academic papers."""
        query = SearchEngine._shorten_query(query)
        results = []
        try:
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": query,
                "limit": max_results,
                "fields": "title,abstract,year,authors,citationCount"
            }
            for attempt in range(3):
                resp = req.get(url, params=params, timeout=10)
                if resp.status_code == 429:
                    wait = 3 * (attempt + 1)
                    log(f"    Semantic Scholar rate limited, {wait}초 대기...")
                    time.sleep(wait)
                    continue
                break
            else:
                log("    Semantic Scholar rate limit 초과, skip")
                return []
            resp.raise_for_status()
            data = resp.json()
            for paper in data.get("data", []):
                abstract = paper.get("abstract") or ""
                if abstract:
                    authors = ", ".join(a.get("name", "") for a in (paper.get("authors") or [])[:3])
                    results.append({
                        "source": "Semantic Scholar",
                        "title": paper.get("title", ""),
                        "content": abstract,
                        "year": paper.get("year"),
                        "authors": authors,
                        "citations": paper.get("citationCount", 0)
                    })
        except Exception as e:
            log(f"    Semantic Scholar 검색 실패: {e}")
        return results

    @staticmethod
    def search_ddg(query: str, max_results: int = 5) -> list[dict]:
        """Search DuckDuckGo for web results."""
        results = []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=max_results))
                for hit in hits:
                    body = hit.get("body", "")
                    if body and len(body) > 50:
                        results.append({
                            "source": "DuckDuckGo",
                            "title": hit.get("title", ""),
                            "content": body[:1000],
                            "url": hit.get("href", "")
                        })
        except Exception as e:
            log(f"    DuckDuckGo 검색 실패: {e}")
        return results

    @classmethod
    def search(cls, question: str, topic: str = "") -> str:
        """Run multi-source search and compile context string."""
        log(f"    검색 중: {question[:60]}...")
        all_results = []

        # Wikipedia (English + Korean)
        en_results = cls.search_wikipedia(question, "en", 2)
        all_results.extend(en_results)
        ko_query = question if any(ord(c) > 0xAC00 for c in question) else topic
        if ko_query:
            ko_results = cls.search_wikipedia(ko_query, "ko", 2)
            all_results.extend(ko_results)

        # Semantic Scholar (with delay to avoid rate limit)
        time.sleep(2)
        scholar_results = cls.search_semantic_scholar(question, 3)
        all_results.extend(scholar_results)

        # DuckDuckGo
        ddg_results = cls.search_ddg(question, 3)
        all_results.extend(ddg_results)

        if not all_results:
            log("    검색 결과 없음")
            return ""

        log(f"    검색 완료: {len(all_results)}건")

        # Compile context
        context_parts = []
        for i, r in enumerate(all_results, 1):
            parts = [f"[참고자료 {i}]"]
            parts.append(f"출처: {r['source']}")
            parts.append(f"제목: {r['title']}")
            if r.get("authors"):
                parts.append(f"저자: {r['authors']}")
            if r.get("year"):
                parts.append(f"연도: {r['year']}")
            if r.get("citations"):
                parts.append(f"인용 수: {r['citations']}")
            if r.get("url"):
                parts.append(f"URL: {r['url']}")
            parts.append(f"내용: {r['content']}")
            context_parts.append("\n".join(parts))

        return "\n\n---\n\n".join(context_parts)


# ---------------------------------------------------------------------------
# Generate search queries from a research question
# ---------------------------------------------------------------------------
def make_search_queries(question: str) -> list[str]:
    """Generate multiple search queries for a research question."""
    queries = [question]
    # Add English translation keywords for Korean questions
    keyword_map = {
        "시김새": "sigimsae korean music ornamentation",
        "가마카": "gamaka Indian raga ornamentation",
        "멜리스마": "melisma vocal ornamentation",
        "타흐리르": "tahrir Persian vocal technique",
        "장식음": "musical ornamentation cross-cultural",
        "농현": "nonghyeon vibrato gayageum",
        "추성": "chuseong ascending pitch bend korean",
        "퇴성": "toeseong descending pitch bend korean",
        "전성": "jeonseong turn ornament korean",
        "요성": "yoseong vibrato korean music",
        "기보법": "music notation ornamentation",
        "음향학": "acoustic analysis ornamentation",
    }
    for ko, en in keyword_map.items():
        if ko in question:
            queries.append(en)

    return queries[:3]


# ---------------------------------------------------------------------------
# LLM API
# ---------------------------------------------------------------------------
def chat_completion(messages: list[dict], temperature: float = 0.7,
                    max_tokens: int = 8192) -> dict:
    payload = {
        "model": MODEL, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
        "repeat_penalty": 1.1, "presence_penalty": 0.3,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = req.post(API_URL, json=payload, timeout=300)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            delay = RETRY_BASE_DELAY ** attempt
            log(f"  API 오류 (시도 {attempt}/{MAX_RETRIES}): {e}. {delay}초 후 재시도...")
            time.sleep(delay)
    log("최대 재시도 횟수 초과. 종료합니다.")
    sys.exit(1)


def extract_reply(api_response: dict) -> tuple[str, dict]:
    msg = api_response["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    text = content if content.strip() else reasoning
    usage = api_response.get("usage", {})
    return text, usage


# ---------------------------------------------------------------------------
# Research plan
# ---------------------------------------------------------------------------
def generate_plan(topic: str) -> list[str]:
    log("연구 계획 수립 중...")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": PLANNING_PROMPT.format(topic=topic)},
    ]
    api_resp = chat_completion(messages, temperature=0.5)
    reply, _ = extract_reply(api_resp)
    log(f"  연구 계획 수립 완료 ({len(reply)} chars)")

    questions = []
    for line in reply.split("\n"):
        line = line.strip()
        if line and line[0].isdigit() and ("." in line[:4] or ")" in line[:4]):
            q = line.split(".", 1)[-1].strip() if "." in line[:4] else line.split(")", 1)[-1].strip()
            if len(q) > 10:
                questions.append(q)

    if len(questions) < 3:
        questions = [
            f"{topic}의 정의, 역사적 배경, 기원",
            f"{topic}의 하위 분류와 각각의 특성",
            f"{topic}의 음향학적/물리적 특성 분석",
            f"{topic}에 대한 학술적 연구와 주요 문헌",
            f"{topic}의 실무적 응용과 현대적 의의",
            f"{topic}에 대한 비교문화적 관점",
            f"{topic}의 한계점과 반론",
            f"{topic}의 미래 전망과 연구 과제",
        ]
    return questions


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
class ResearchSession:
    def __init__(self, session_num: int, output_dir: Path, handoff_threshold: int):
        self.session_num = session_num
        self.output_dir = output_dir
        self.handoff_threshold = handoff_threshold
        self.messages: list[dict] = []
        self.cumulative_tokens = 0
        self.turn_count = 0
        self.findings: list[str] = []
        self.search_log: list[dict] = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def send(self, content: str | None = None, role: str = "user") -> str:
        if content is not None:
            self.add_message(role, content)

        log(f"  턴 {self.turn_count + 1}: 요청 전송 중...")
        api_resp = chat_completion(self.messages)
        reply, usage = extract_reply(api_resp)

        self.add_message("assistant", reply)
        self.turn_count += 1
        self.findings.append(reply)

        total_tokens = usage.get("total_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        self.cumulative_tokens = total_tokens

        log(f"  턴 {self.turn_count} 완료: "
            f"prompt={prompt_tokens}, completion={completion_tokens}, "
            f"total={total_tokens}/{self.handoff_threshold} "
            f"({total_tokens * 100 // self.handoff_threshold}%)")
        return reply

    def needs_handoff(self) -> bool:
        return self.cumulative_tokens >= self.handoff_threshold

    def build_recap(self) -> str:
        if not self.findings:
            return ""
        topics_covered = []
        for f in self.findings:
            first_line = f.strip().split("\n")[0][:100]
            topics_covered.append(first_line)
        return "지금까지 다룬 내용: " + " / ".join(topics_covered[-5:])

    def save_log(self):
        path = self.output_dir / f"session_{self.session_num:03d}_log.json"
        data = {
            "session": self.session_num,
            "turn_count": self.turn_count,
            "cumulative_tokens": self.cumulative_tokens,
            "search_log": self.search_log,
            "messages": self.messages,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"  세션 로그 저장: {path}")

    def save_summary(self, summary: str):
        path = self.output_dir / f"session_{self.session_num:03d}_summary.md"
        header = f"# 세션 {self.session_num} 요약\n\n"
        path.write_text(header + summary, encoding="utf-8")
        log(f"  세션 요약 저장: {path}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class SearchResearcher:
    def __init__(self, topic: str, max_sessions: int, output_dir: str,
                 handoff_threshold: int):
        self.topic = topic
        self.max_sessions = max_sessions
        self.output_dir = Path(output_dir)
        self.handoff_threshold = handoff_threshold
        self.summaries: list[str] = []
        self.current_session: ResearchSession | None = None
        self._shutdown_requested = False
        self.sub_questions: list[str] = []
        self.question_index = 0

        self.output_dir.mkdir(parents=True, exist_ok=True)
        config = {
            "topic": topic, "max_sessions": max_sessions,
            "handoff_threshold": handoff_threshold,
            "mode": "search-augmented",
            "started_at": datetime.now().isoformat(),
        }
        (self.output_dir / "config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def handle_shutdown(self, signum, frame):
        log("\n중단 요청 감지. 현재 상태를 저장합니다...")
        self._shutdown_requested = True
        if self.current_session:
            self.current_session.save_log()
        if self.summaries:
            self._write_final_report(partial=True)
        log("안전하게 종료되었습니다.")
        sys.exit(0)

    def next_question(self) -> str | None:
        if self.question_index < len(self.sub_questions):
            q = self.sub_questions[self.question_index]
            self.question_index += 1
            return q
        return None

    def search_and_build_prompt(self, question: str, recap: str) -> str:
        """Search for context, then build a prompt with search results injected."""
        search_queries = make_search_queries(question)
        all_context = []
        for sq in search_queries:
            ctx = SearchEngine.search(sq, self.topic)
            if ctx:
                all_context.append(ctx)
            time.sleep(1)  # rate limit courtesy

        search_context = "\n\n".join(all_context) if all_context else "(검색 결과 없음)"

        if self.current_session:
            self.current_session.search_log.append({
                "question": question,
                "queries": search_queries,
                "results_count": search_context.count("[참고자료"),
                "context_length": len(search_context),
            })

        parts = []
        if recap:
            parts.append(recap)
        parts.append(f"\n다음 참고자료를 기반으로 깊이 있게 분석해주세요. 참고자료의 구체적 내용(명칭, 분류, 수치, 저자)을 반드시 인용하세요. 최소 2000자 이상 상세히 서술하세요.")
        parts.append(f"\n--- 참고자료 ---\n{search_context}\n--- 참고자료 끝 ---")
        parts.append(f"\n질문: {question}")
        return "\n".join(parts)

    def run(self):
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        log(f"[검색 보강 모드] 연구 시작: \"{self.topic}\"")
        log(f"최대 세션: {self.max_sessions}, 핸드오프 임계값: {self.handoff_threshold} tokens")
        log(f"출력 디렉토리: {self.output_dir.resolve()}")

        # Phase 1: Plan
        self.sub_questions = generate_plan(self.topic)
        plan_path = self.output_dir / "research_plan.md"
        plan_text = f"# 연구 계획: {self.topic}\n\n"
        for i, q in enumerate(self.sub_questions, 1):
            plan_text += f"{i}. {q}\n"
        plan_path.write_text(plan_text, encoding="utf-8")
        log(f"연구 계획 저장: {len(self.sub_questions)}개 하위 질문")

        # Phase 2: Execute
        previous_summary = None

        for session_num in range(1, self.max_sessions + 1):
            if self._shutdown_requested:
                break

            log(f"\n{'=' * 60}")
            log(f"세션 {session_num}/{self.max_sessions} 시작")
            log(f"{'=' * 60}")

            session = ResearchSession(session_num, self.output_dir, self.handoff_threshold)
            self.current_session = session
            session.add_message("system", SYSTEM_PROMPT)

            if previous_summary:
                first_msg = CONTINUATION_TEMPLATE.format(summary=previous_summary)
            else:
                # First turn: search for topic overview
                overview_ctx = SearchEngine.search(self.topic)
                first_msg = f"다음 참고자료를 바탕으로 심층 연구를 시작해주세요. 개요가 아닌 첫 번째 측면부터 깊이 파고들어주세요.\n\n--- 참고자료 ---\n{overview_ctx}\n--- 참고자료 끝 ---\n\n주제: {self.topic}"

            reply = session.send(first_msg)

            # Follow-up loop with search
            while not session.needs_handoff():
                if self._shutdown_requested:
                    break

                question = self.next_question()
                if question is None:
                    recap = session.build_recap()
                    prompt = f"{recap}\n\n위에서 다루지 않은 중요한 측면이 있다면 깊이 분석해주세요."
                else:
                    recap = session.build_recap()
                    log(f"  하위 질문 {self.question_index}/{len(self.sub_questions)}: {question[:60]}...")
                    prompt = self.search_and_build_prompt(question, recap)

                reply = session.send(prompt)

            # Handoff
            if not self._shutdown_requested:
                log("  핸드오프 임계값 도달. 요약 요청 중...")
                summary = session.send(HANDOFF_PROMPT)
            else:
                summary = reply

            self.summaries.append(summary)
            session.save_log()
            session.save_summary(summary)
            previous_summary = summary

            if self.question_index >= len(self.sub_questions) and session_num >= 2:
                log(f"\n모든 하위 질문 탐구 완료! 총 {session_num}개 세션 수행.")
                break
        else:
            log(f"\n최대 세션 수({self.max_sessions}) 도달.")

        # Phase 3: Final report
        self._write_final_report(partial=False)
        self.current_session = None

    def _write_final_report(self, partial: bool = False):
        if not self.summaries:
            return

        log("\n최종 보고서 생성 중...")
        all_summaries = ""
        for i, s in enumerate(self.summaries, 1):
            all_summaries += f"\n### 세션 {i}\n{s}\n"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": FINAL_REPORT_PROMPT.format(all_summaries=all_summaries)},
        ]
        api_resp = chat_completion(messages, temperature=0.5, max_tokens=8192)
        report, _ = extract_reply(api_resp)

        suffix = "_partial" if partial else ""
        report_path = self.output_dir / f"final_report{suffix}.md"
        header = f"# 연구 보고서 (검색 보강): {self.topic}\n\n"
        header += f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"세션 수: {len(self.summaries)}\n"
        header += f"탐구한 하위 질문: {self.question_index}/{len(self.sub_questions)}\n"
        header += f"모드: 검색 보강 (Wikipedia + Semantic Scholar + DuckDuckGo)\n\n---\n\n"
        report_path.write_text(header + report, encoding="utf-8")
        log(f"최종 보고서 저장: {report_path.resolve()}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Gemma 4 검색 보강 자율 연구 오케스트레이터")
    parser.add_argument("--topic", required=True, help="연구 주제")
    parser.add_argument("--max-sessions", type=int, default=5, help="최대 세션 수")
    parser.add_argument("--output-dir", default="research_search", help="출력 디렉토리")
    parser.add_argument("--handoff-threshold", type=int, default=50000, help="핸드오프 토큰 임계값")
    args = parser.parse_args()

    researcher = SearchResearcher(
        topic=args.topic, max_sessions=args.max_sessions,
        output_dir=args.output_dir, handoff_threshold=args.handoff_threshold,
    )
    researcher.run()


if __name__ == "__main__":
    main()
