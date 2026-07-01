#!/usr/bin/env python3
"""Backfill missing fill-question answers for exams/simulations.

For fill questions (填空题) that lack both `final_answer` and `standard_answer`,
use the LLM to solve and extract the answer value, then save to the question JSON.

Usage:
  python scripts/backfill_fill_answers.py --dry-run       # list candidates
  python scripts/backfill_fill_answers.py --live           # generate answers (needs API key)
  python scripts/backfill_fill_answers.py --live --limit 5 # limit to 5 questions
"""

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FILL_SOLVE_PROMPT = """你是一个考研数学解题专家。请解答以下填空题，只输出最终答案，不需要解题过程。

题目：
{question}

请直接输出答案（数学表达式用 LaTeX 格式，例如：2、e^x、\\frac{{1}}{{2}}）。
只输出答案值，不要输出任何其他文字。"""


def find_candidates():
    """Find fill questions missing both final_answer and standard_answer."""
    candidates = []
    for subdir in ["exams", "simulations1", "simulations2", "simulations3", "simulations4"]:
        d = ROOT / "storage" / "questions" / subdir
        if not d.exists():
            continue
        for fname in sorted(d.iterdir()):
            if not fname.name.endswith(".json"):
                continue
            with open(fname, encoding="utf-8") as f:
                q = json.load(f)
            if "填空" not in q.get("question_type", ""):
                continue
            has_final = bool(q.get("final_answer"))
            has_std = bool(q.get("standard_answer"))
            if not has_final and not has_std:
                candidates.append({
                    "path": str(fname),
                    "question_id": q.get("question_id", fname.stem),
                    "question": q.get("question", "")[:300],
                    "year": q.get("year", "?"),
                })
    return candidates


def solve_fill_question(client, model, question_text):
    """Use LLM to solve a fill question and return the answer value."""
    prompt = FILL_SOLVE_PROMPT.format(question=question_text)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
            timeout=30,
        )
        if not resp.choices:
            return None
        answer = resp.choices[0].message.content.strip()
        # Clean up: remove common prefixes/suffixes
        answer = re.sub(r"^(答案[：:]?\s*|答[：:]?\s*)", "", answer)
        answer = re.sub(r"\s*[。.。]$", "", answer)
        return answer.strip() if answer.strip() else None
    except Exception as e:
        print(f"    LLM error: {e}")
        return None


def save_answer(path, answer_value):
    """Save answer to question JSON file."""
    with open(path, encoding="utf-8") as f:
        q = json.load(f)
    q["final_answer"] = answer_value
    # Also set _original_answer for reference
    q["_original_answer"] = answer_value
    q["_answer_backfilled_at"] = time.strftime("%Y-%m-%d %H:%M")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)


def main():
    args = set(sys.argv[1:])
    dry_run = "--live" not in args
    limit = 100
    for i, a in enumerate(sys.argv[1:]):
        if a == "--limit" and i + 1 < len(sys.argv) - 1:
            limit = int(sys.argv[i + 2])

    candidates = find_candidates()
    print(f"Fill questions missing answers: {len(candidates)}")
    candidates = candidates[:limit]

    if dry_run:
        print(f"\nDry-run (showing first {len(candidates)}):")
        for c in candidates:
            print(f"  {c['question_id']:30s} year={c['year']}")
        print(f"\nUse --live to generate answers.")
        return

    # Live mode
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        print("Set LLM_API_KEY environment variable")
        sys.exit(1)

    from config import LLM_MODEL, LLM_BASE_URL
    from llm_client import create_client

    model = os.getenv("LLM_MODEL", LLM_MODEL)
    base_url = os.getenv("LLM_BASE_URL", LLM_BASE_URL)
    client = create_client(api_key=api_key, base_url=base_url, protocol="openai",
                           timeout=30)

    saved = 0
    failed = 0
    for i, c in enumerate(candidates):
        print(f"[{i+1}/{len(candidates)}] {c['question_id']}...", end=" ", flush=True)
        answer = solve_fill_question(client, model, c["question"])
        if answer:
            save_answer(c["path"], answer)
            saved += 1
            print(f"OK: {answer[:60]}")
        else:
            failed += 1
            print("FAILED")
        # Rate limit
        time.sleep(0.5)

    print(f"\nDone. Saved: {saved}, Failed: {failed}")


if __name__ == "__main__":
    main()
