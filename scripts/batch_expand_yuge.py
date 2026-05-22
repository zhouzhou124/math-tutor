"""Batch pre-generate detailed answers for ALL 26宇哥八套卷 questions.

Reads every question JSON, calls generate_detailed_answer for those without
a canonical solution, and writes the result atomically back to disk.
"""
import json, os, time, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from credential_manager import get_effective_api_key
from llm_client import create_client
from choice_explainer import generate_detailed_answer
from config import LLM_BASE_URL, LLM_MODEL


def main():
    api_key = get_effective_api_key()
    if not api_key:
        print("ERROR: No API key. Run the app first to configure credentials.")
        sys.exit(1)

    client = create_client(api_key=api_key, base_url=LLM_BASE_URL, protocol="openai")
    model = LLM_MODEL
    print(f"Model: {model}\n")

    sim_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "storage", "questions", "simulations")
    files = sorted(f for f in os.listdir(sim_dir) if f.startswith("26宇哥"))
    total = len(files)
    print(f"Found {total} files\n")

    ok = skip = fail = 0
    for idx, fn in enumerate(files):
        fp = os.path.join(sim_dir, fn)
        with open(fp, "r", encoding="utf-8") as f:
            q = json.load(f)

        qid = q.get("question_id", fn)
        cached = str(q.get("standard_answer", ""))
        qtype = q.get("question_type", "")

        # Skip if already canonical or has detailed steps
        if q.get("canonical_solutions") or q.get("solution_metadata", {}).get("canonical"):
            skip += 1
            continue
        if len(cached) >= 300 and re.search(r'步骤\s*\d+\s*[：:]', cached):
            skip += 1
            continue

        # Build known_answer
        known = cached
        if qtype == "选择题" and q.get("correct_option"):
            co = q["correct_option"]
            opts = q.get("options", {})
            known = f"正确选项: {co}. {opts[co]}" if co in opts else f"正确选项: {co}"

        # Build full question dict
        qd = dict(q)
        qd.setdefault("question", q.get("question", ""))
        if q.get("options"):
            qd["question"] += "\n" + "\n".join(
                f"({k}) {v}" for k, v in sorted(q["options"].items())
            )

        status = f"[{idx+1}/{total}] {fn}"
        print(f"{status}: type={qtype}, known_len={len(known)}...", end=" ", flush=True)

        try:
            expanded = generate_detailed_answer(
                question=qd, known_answer=known,
                question_type=qtype or "解答题",
                client=client, model=model,
            )
            if expanded and len(expanded.strip()) >= 200 and expanded != known:
                if not q.get("final_answer") and len(cached) < 200:
                    q["final_answer"] = cached
                q["standard_answer"] = expanded
                q["solution_metadata"] = {
                    "canonical": True,
                    "has_steps": bool(re.search(r'步骤\s*\d+\s*[：:]', expanded)),
                    "generated_by": model,
                    "generated_at": time.strftime("%Y-%m-%d %H:%M"),
                    "reviewed": False,
                    "render_version": "v2",
                }
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(q, f, ensure_ascii=False, indent=2)
                print(f"OK ({len(expanded)} chars)")
                ok += 1
            else:
                print(f"SHORT/EMPTY ({len(expanded)} chars)")
                fail += 1
        except Exception as e:
            print(f"ERROR: {e}")
            fail += 1

        time.sleep(0.5)

    print(f"\nDone: {ok} generated, {skip} skipped, {fail} failed (total {total})")


if __name__ == "__main__":
    main()
