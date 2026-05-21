"""Batch pre-generate detailed answers for 2026 exam questions.

Run once to populate detailed standard_answer fields in all 2026 JSON files.
After this, users get instant detailed answers without waiting for AI.
"""
import json, os, sys, glob, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_client import create_client
from choice_explainer import generate_detailed_answer
from latex_utils import from_legacy_text
from config import LLM_BASE_URL, LLM_MODEL


def main():
    # Read API key from config
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        # Try to read from credential manager
        try:
            from credential_manager import get_credential
            api_key = get_credential("deepseek") or get_credential("default") or ""
        except Exception:
            pass
    if not api_key:
        print("ERROR: No API key found. Set LLM_API_KEY env var or configure credentials.")
        sys.exit(1)

    client = create_client(api_key=api_key, base_url=LLM_BASE_URL, protocol="openai")
    model = os.environ.get("LLM_MODEL", LLM_MODEL)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pattern = os.path.join(base_dir, "storage", "questions", "exams", "2026-*.json")
    files = sorted(glob.glob(pattern))
    print(f"Found {len(files)} question files\n")

    success = 0
    skipped = 0
    failed = 0

    for fp in files:
        fname = os.path.basename(fp)
        with open(fp, "r", encoding="utf-8") as f:
            q = json.load(f)

        qid = q.get("question_id", fname)
        cached = q.get("standard_answer", "")
        qtype = q.get("question_type", "")

        # Skip if already detailed (has step markers or is long enough)
        import re
        already_detailed = (
            len(cached.strip()) >= 200
            or re.search(r'步骤\s*\d+\s*[：:]', cached)
            or q.get("_ai_expanded_at")
        )
        if already_detailed:
            print(f"  SKIP {fname}: already detailed ({len(cached)} chars)")
            skipped += 1
            continue

        # Build question dict for generation
        question_dict = dict(q)
        question_dict.setdefault("question", q.get("question", ""))
        if q.get("options"):
            question_dict["question"] += "\n" + "\n".join(
                f"({k}) {v}" for k, v in sorted(q["options"].items())
            )

        # Build known_answer
        known = cached or ""
        if qtype == "选择题" and q.get("correct_option"):
            co = q["correct_option"]
            opts = q.get("options", {})
            if co in opts:
                known = f"正确选项: {co}. {opts[co]}"
            else:
                known = f"正确选项: {co}"

        print(f"  GEN {fname}: type={qtype}, known_len={len(known)}...", end=" ", flush=True)

        try:
            expanded = generate_detailed_answer(
                question=question_dict,
                known_answer=known,
                question_type=qtype or "解答题",
                client=client,
                model=model,
            )
            if expanded and len(expanded.strip()) >= 80 and expanded != known:
                # Update JSON file
                q["standard_answer"] = expanded
                if not q.get("_original_answer") and len(cached) < 200:
                    q["_original_answer"] = cached
                q["_ai_expanded_at"] = time.strftime("%Y-%m-%d %H:%M")
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(q, f, ensure_ascii=False, indent=2)
                print(f"OK ({len(expanded)} chars)")
                success += 1
            else:
                print(f"FAIL: generated content too short or same as known")
                failed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        time.sleep(0.5)  # Rate limit protection

    print(f"\nDone: {success} generated, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
