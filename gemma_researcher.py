#!/usr/bin/env python3
"""
gemma_researcher.py — Autonomous research orchestrator using local Gemma 4 LLM.

Usage:
    python3 gemma_researcher.py --topic "연구 주제" [--max-sessions 10] [--output-dir research_output]
    python3 gemma_researcher.py --topic "연구 주제" [--handoff-threshold 50000]
"""

import argparse
import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

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
3. 최소 2000자 이상 상세하게 서술하세요.
4. 결론이나 요약을 내지 마세요. 공간이 부족하면 "CONTINUE"라고 쓰세요.
5. "[[RESEARCH_COMPLETE]]" 태그는 절대 사용하지 마세요. 연구 완료는 시스템이 판단합니다.
6. 한국어로 응답하세요.
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

## 핵심 발견사항
(주요 발견을 번호 목록으로, 각각 2-3문장 이상)

## 분석된 측면
(이미 다룬 각도/관점, 각각의 깊이 평가)

## 미탐구 영역
(아직 조사하지 않은 부분)

## 잠정적 결론
(현재까지의 종합 판단)

## 다음 세션에서 탐구할 질문
(구체적 후속 질문 5-8개)
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

구조:
1. 서론 (연구 주제 및 범위)
2. 핵심 발견사항
3. 상세 분석 (각 세션의 발견을 통합)
4. 반론 및 한계
5. 실무 시사점
6. 결론

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
# API call with retries
# ---------------------------------------------------------------------------
def chat_completion(messages: list[dict], temperature: float = 0.7,
                    max_tokens: int = 8192) -> dict:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "repeat_penalty": 1.1,
        "presence_penalty": 0.3,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, json=payload, timeout=300)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout) as e:
            delay = RETRY_BASE_DELAY ** attempt
            log(f"  API 오류 (시도 {attempt}/{MAX_RETRIES}): {e}. {delay}초 후 재시도...")
            time.sleep(delay)
        except Exception as e:
            delay = RETRY_BASE_DELAY ** attempt
            log(f"  예상치 못한 오류: {e} (시도 {attempt}/{MAX_RETRIES}). {delay}초 후 재시도...")
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
# Research plan: decompose topic into sub-questions
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

    # Extract numbered questions from the plan
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
# Session management
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
            f"({total_tokens*100//self.handoff_threshold}%)")

        return reply

    def needs_handoff(self) -> bool:
        return self.cumulative_tokens >= self.handoff_threshold

    def build_recap(self) -> str:
        """Snowball recap: short summary of findings so far for context grounding."""
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
# Main orchestrator
# ---------------------------------------------------------------------------
class Researcher:
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
            "topic": topic,
            "max_sessions": max_sessions,
            "handoff_threshold": handoff_threshold,
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
            log("현재 세션 로그 저장 완료.")
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

    def build_directed_prompt(self, question: str, recap: str) -> str:
        """Build a prompt that directs the model to a specific sub-question with recap."""
        parts = []
        if recap:
            parts.append(recap)
        parts.append(f"\n다음 질문에 대해 깊이 있게 분석해주세요. 최소 2000자 이상 상세히 서술하세요.\n\n질문: {question}")
        return "\n".join(parts)

    def run(self):
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        log(f"연구 시작: \"{self.topic}\"")
        log(f"최대 세션: {self.max_sessions}, 핸드오프 임계값: {self.handoff_threshold} tokens")
        log(f"출력 디렉토리: {self.output_dir.resolve()}")

        # Phase 1: Generate research plan
        self.sub_questions = generate_plan(self.topic)
        plan_path = self.output_dir / "research_plan.md"
        plan_text = f"# 연구 계획: {self.topic}\n\n"
        for i, q in enumerate(self.sub_questions, 1):
            plan_text += f"{i}. {q}\n"
        plan_path.write_text(plan_text, encoding="utf-8")
        log(f"연구 계획 저장: {len(self.sub_questions)}개 하위 질문")

        # Phase 2: Execute research sessions
        previous_summary = None

        for session_num in range(1, self.max_sessions + 1):
            if self._shutdown_requested:
                break

            log(f"\n{'='*60}")
            log(f"세션 {session_num}/{self.max_sessions} 시작")
            log(f"{'='*60}")

            session = ResearchSession(session_num, self.output_dir, self.handoff_threshold)
            self.current_session = session

            session.add_message("system", SYSTEM_PROMPT)

            # First message
            if previous_summary:
                first_msg = CONTINUATION_TEMPLATE.format(summary=previous_summary)
            else:
                first_msg = f"다음 주제에 대해 심층 연구를 시작해주세요. 개요가 아닌 첫 번째 측면부터 깊이 파고들어주세요.\n\n주제: {self.topic}"

            reply = session.send(first_msg)

            # Follow-up loop: directed sub-questions
            while not session.needs_handoff():
                if self._shutdown_requested:
                    break

                question = self.next_question()
                if question is None:
                    # All planned questions exhausted — ask for what's missing
                    recap = session.build_recap()
                    prompt = f"{recap}\n\n위에서 다루지 않은 중요한 측면이 있다면 깊이 분석해주세요. 더 이상 새로운 측면이 없다면 기존 분석의 약점이나 반론을 탐구해주세요."
                else:
                    recap = session.build_recap()
                    prompt = self.build_directed_prompt(question, recap)
                    log(f"  하위 질문 {self.question_index}/{len(self.sub_questions)}: {question[:60]}...")

                reply = session.send(prompt)

            # Session ending — get summary for handoff
            if not self._shutdown_requested:
                log("  핸드오프 임계값 도달. 요약 요청 중...")
                summary = session.send(HANDOFF_PROMPT)
            else:
                summary = reply

            self.summaries.append(summary)
            session.save_log()
            session.save_summary(summary)
            previous_summary = summary

            # Check if all questions are done
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
            log("요약이 없어 최종 보고서를 생성하지 않습니다.")
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

        header = f"# 연구 보고서: {self.topic}\n\n"
        header += f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"세션 수: {len(self.summaries)}\n"
        header += f"탐구한 하위 질문: {self.question_index}/{len(self.sub_questions)}\n\n---\n\n"

        report_path.write_text(header + report, encoding="utf-8")
        log(f"최종 보고서 저장: {report_path.resolve()}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Gemma 4 자율 연구 오케스트레이터"
    )
    parser.add_argument("--topic", required=True, help="연구 주제")
    parser.add_argument("--max-sessions", type=int, default=10, help="최대 세션 수 (기본: 10)")
    parser.add_argument("--output-dir", default="research_output", help="출력 디렉토리 (기본: research_output)")
    parser.add_argument("--handoff-threshold", type=int, default=50000, help="핸드오프 토큰 임계값 (기본: 50000)")

    args = parser.parse_args()

    researcher = Researcher(
        topic=args.topic,
        max_sessions=args.max_sessions,
        output_dir=args.output_dir,
        handoff_threshold=args.handoff_threshold,
    )
    researcher.run()


if __name__ == "__main__":
    main()
