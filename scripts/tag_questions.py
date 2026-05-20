"""Batch tag exam questions with knowledge points using AI.

Usage:  python scripts/tag_questions.py [--years 2009,2010,2011] [--dry-run]
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import KNOWLEDGE_POINTS

# Flatten all knowledge points into a reference list
ALL_KP = []
for subject, kps in KNOWLEDGE_POINTS.items():
    ALL_KP.extend(kps)

KP_LIST_STR = "\n".join(f"- {kp}" for kp in ALL_KP)

TAG_PROMPT = f"""你是一位考研数学命题专家。请为下面的题目标注知识点。

## 可选知识点（只能从下面选，最多选5个）
{KP_LIST_STR}

## 题目
{{question}}

## 题目类型
{{question_type}}  |  {{year}}年 考研数学一

请只输出一个 JSON 数组，不要输出其他内容。例如：["极限与连续", "导数与微分"]

知识点数组："""


def load_credential():
    """Load API key from credential store."""
    try:
        import credential_store
        active = credential_store.get_active_profile()
        if active:
            return active
    except Exception:
        pass
    # Fallback: check env
    api_key = os.getenv("LLM_API_KEY", "")
    if api_key:
        return {
            "api_key": api_key,
            "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            "model": os.getenv("LLM_MODEL", "deepseek-v4-pro"),
            "protocol": "openai",
        }
    return None


def create_client(profile):
    from llm_client import create_client
    return create_client(
        api_key=profile["api_key"],
        base_url=profile["base_url"],
        protocol=profile.get("protocol", "openai"),
    )


def tag_question(client, model, question_text, question_type, year):
    prompt = TAG_PROMPT.format(
        question=question_text[:3000],
        question_type=question_type,
        year=year,
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=256,
            timeout=30,
        )
        raw = resp.choices[0].message.content.strip()
        # Extract JSON array
        import re
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            tags = json.loads(match.group())
            # Filter to valid KPs only
            valid = [t for t in tags if t in ALL_KP]
            return valid if valid else tags[:5]
        return []
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def process_files(years, dry_run=False):
    profile = load_credential()
    if not profile:
        print("ERROR: No API key configured. Run the app and set up a provider first.")
        return

    client = create_client(profile)
    model = profile.get("model", "deepseek-v4-pro")

    exams_dir = ROOT / "storage" / "questions" / "exams"
    json_files = sorted(exams_dir.glob("*.json"))

    # Filter: only target years, only files missing knowledge_points
    targets = []
    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        year = data.get("year", 0)
        if year not in years:
            continue
        kps = data.get("knowledge_points", [])
        tags = data.get("tags") or []
        if kps or tags:
            continue  # already tagged
        targets.append((fp, data))

    if not targets:
        print(f"No untagged questions found for years {years}.")
        return

    print(f"Found {len(targets)} untagged questions for years {years}.")
    print(f"Using model: {model}")
    print()

    success = 0
    for i, (fp, data) in enumerate(targets):
        q_text = data.get("question", "")
        q_type = data.get("question_type", "解答题")
        year = data.get("year", "?")
        qid = data.get("question_id", fp.stem)

        print(f"[{i+1}/{len(targets)}] {qid} ({year} {q_type}) ...", end=" ", flush=True)

        if dry_run:
            print("DRY-RUN (would tag)")
            continue

        kps = tag_question(client, model, q_text, q_type, year)
        if kps is None:
            print("SKIPPED (API error)")
            time.sleep(2)
            continue

        if not kps:
            # Fallback: try auto_tag
            from database.question_db import QuestionDB
            db = QuestionDB()
            kps = db.auto_tag(q_text)
            if kps:
                print(f"FALLBACK: {kps}")
            else:
                print("NO TAGS FOUND")
                continue

        print(f"-> {kps}")

        # Update JSON
        data["knowledge_points"] = kps
        data["tags"] = kps
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            success += 1
        except Exception as e:
            print(f"  WRITE ERROR: {e}")
            continue

        # Rate limit: 0.5s between calls
        time.sleep(0.5)

    print()
    print(f"Done. Tagged {success}/{len(targets)} questions.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch tag exam questions")
    parser.add_argument("--years", type=str, default="2009,2010,2011",
                        help="Comma-separated years (default: 2009,2010,2011)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List files that would be tagged without making changes")
    args = parser.parse_args()

    years = [int(y.strip()) for y in args.years.split(",")]
    process_files(years, dry_run=args.dry_run)
