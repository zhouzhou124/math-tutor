#!/usr/bin/env python3
"""P25: Backfill detailed solutions for questions that lack them.

Usage:
  python scripts/backfill_solutions.py                  # dry-run: list candidates
  python scripts/backfill_solutions.py --live            # actually generate (needs API key)
  python scripts/backfill_solutions.py --limit 5 --type 解答题  # filter
  python scripts/backfill_solutions.py --year 2024       # filter by year

Safety: only saves solutions that pass P19/P21 quality gates.
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run_dry(candidates: list[dict]):
    print(f"\nCandidates for backfill ({len(candidates)}):")
    for c in candidates:
        qtype = c.get("question_type", "?")
        qid = c["question_id"]
        kps = ", ".join(c.get("knowledge_points", [])[:3])
        state = c["current_state"]
        print(f"  {qid:30s} {qtype:4s}  {state:15s}  {kps}")
    print(f"\n{c['current_state']} → target: has_detailed_solution")
    print("Dry-run complete. Use --live to generate solutions.")


def run_live(candidates: list[dict]):
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        print("Set LLM_API_KEY to run --live")
        sys.exit(1)

    from config import LLM_MODEL
    from llm_client import create_client
    from services.solution_service import SolutionService
    from services.grading_adapter import normalize_solution_for_render
    from services.solution_quality import solution_is_renderable, solution_is_complete
    from database.question_db import QuestionDB, get_question_path

    client = create_client(api_key=api_key, base_url=os.getenv("LLM_BASE_URL", ""), protocol="openai")
    svc = SolutionService(client=client, model=LLM_MODEL)
    db = QuestionDB()

    saved = 0
    failed = 0
    for c in candidates:
        path = get_question_path(c["question_id"])
        if not path or not path.exists():
            print(f"  {c['question_id']}: file missing, skip")
            failed += 1
            continue

        with open(path, encoding="utf-8") as f:
            q = json.load(f)

        try:
            sol = svc.build(question=q.get("question", ""), selected_q=q)
            sol = normalize_solution_for_render(sol)
            if solution_is_renderable(sol) and solution_is_complete(sol, q):
                from views.grading_page import save_as_canonical_solution
                ans = sol.get("standard_answer", "")
                if save_as_canonical_solution(q, ans, model=LLM_MODEL):
                    saved += 1
                    print(f"  {c['question_id']}: saved")
                else:
                    failed += 1
                    print(f"  {c['question_id']}: save failed")
            else:
                failed += 1
                print(f"  {c['question_id']}: quality gate failed (renderable={solution_is_renderable(sol)}, "
                      f"complete={solution_is_complete(sol, q)})")
        except Exception as exc:
            failed += 1
            print(f"  {c['question_id']}: error - {exc}")

    print(f"\nSaved: {saved}, Failed: {failed}")


def main():
    from services.solution_coverage_service import build_solution_backfill_candidates
    from database.question_db import QuestionDB

    args = set(sys.argv[1:])
    limit = 20
    qtype_filter = ""
    for i, a in enumerate(sys.argv[1:]):
        if a == "--limit" and i + 1 < len(sys.argv) - 1:
            limit = int(sys.argv[i + 2])
        if a == "--type" and i + 1 < len(sys.argv) - 1:
            qtype_filter = sys.argv[i + 2]

    filters = {}
    if qtype_filter:
        filters["question_type"] = qtype_filter

    db = QuestionDB()

    # Print coverage summary first
    from services.solution_coverage_service import compute_solution_coverage
    cov = compute_solution_coverage(db)
    print(f"Total: {cov['total']}")
    print(f"  Answer coverage:     {cov['answer_coverage_pct']}%")
    print(f"  Detailed coverage:   {cov['detailed_coverage_pct']}%")
    print(f"  no_answer:           {cov['no_answer']}")
    print(f"  answer_only:         {cov['answer_only']}")
    print(f"  has_detailed:        {cov['has_detailed_solution']}")
    print(f"  has_structured:      {cov['has_structured_solution']}")

    candidates = build_solution_backfill_candidates(db, limit=limit, filters=filters)

    if "--live" in args:
        run_live(candidates)
    else:
        run_dry(candidates)


if __name__ == "__main__":
    main()
