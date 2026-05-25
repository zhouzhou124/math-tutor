#!/usr/bin/env python3
"""P21: Evaluate solution prompting quality — dry-run by default.

Usage:
  python scripts/eval_solution_prompting.py           # dry-run: load dataset, check contracts
  python scripts/eval_solution_prompting.py --live    # actually call SolutionService (needs API key)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EVAL_DATASET = ROOT / "storage" / "eval_dataset.json"


def load_dataset():
    with open(EVAL_DATASET, encoding="utf-8") as f:
        return json.load(f)["entries"]


def check_contract(entry: dict) -> dict:
    """Dry-run: check question exists and has required fields."""
    from database.question_db import get_question_path
    from services.solution_quality import solution_is_complete, solution_is_renderable

    qid = entry["question_id"]
    path = get_question_path(qid)
    if not path or not path.exists():
        return {"eval_id": entry["eval_id"], "status": "missing_question"}

    with open(path, encoding="utf-8") as f:
        q = json.load(f)

    # Build a solution-like dict from the question's cached answer
    sol = {
        "standard_answer": q.get("standard_answer") or q.get("raw_answer_text") or "",
        "_structured": q.get("_structured"),
    }

    return {
        "eval_id": entry["eval_id"],
        "question_id": qid,
        "question_type": q.get("question_type", "?"),
        "standard_answer_len": len(sol["standard_answer"]),
        "solution_is_renderable": solution_is_renderable(sol),
        "solution_is_complete": solution_is_complete(sol, q),
        "broken_latex_count": _count_broken(sol["standard_answer"]),
        "has_canonical_pool": bool(q.get("canonical_solutions")),
    }


def _count_broken(text: str) -> int:
    from services.solution_quality import count_broken_latex_fragments
    return count_broken_latex_fragments(text)


def run_dry(entries: list[dict]):
    results = [check_contract(e) for e in entries]
    renderable = sum(1 for r in results if r.get("solution_is_renderable"))
    complete = sum(1 for r in results if r.get("solution_is_complete"))
    broken = sum(r.get("broken_latex_count", 0) for r in results)
    print(f"Total: {len(results)}")
    print(f"  Renderable: {renderable}")
    print(f"  Complete:   {complete}")
    print(f"  Broken frags: {broken}")
    print("Dry-run complete. Use --live for real solution generation.")


def run_live(entries: list[dict]):
    from services.solution_service import SolutionService
    from services.grading_adapter import normalize_solution_for_render
    from services.solution_quality import solution_is_renderable, solution_is_complete
    from database.question_db import get_question_path
    import os

    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        print("Set LLM_API_KEY to run --live")
        sys.exit(1)

    from config import LLM_MODEL
    from llm_client import create_client
    client = create_client(api_key=api_key, base_url=os.getenv("LLM_BASE_URL", ""), protocol="openai")
    svc = SolutionService(client=client, model=LLM_MODEL)

    renderable = complete = 0
    for entry in entries:
        path = get_question_path(entry["question_id"])
        if not path or not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            q = json.load(f)
        sol = svc.build(question=q.get("question", ""), selected_q=q)
        sol = normalize_solution_for_render(sol)
        r = solution_is_renderable(sol)
        c = solution_is_complete(sol, q)
        if r:
            renderable += 1
        if c:
            complete += 1
        status = "OK" if (r and c) else ("R" if r else ("C" if c else "FAIL"))
        print(f"  {entry['eval_id']:12s} {status:4s}  renderable={r} complete={c}")
    print(f"Renderable: {renderable}/{len(entries)}  Complete: {complete}/{len(entries)}")


def main():
    args = set(sys.argv[1:])
    entries = load_dataset()
    print(f"Loaded {len(entries)} eval entries")
    if "--live" in args:
        run_live(entries)
    else:
        run_dry(entries)


if __name__ == "__main__":
    main()
