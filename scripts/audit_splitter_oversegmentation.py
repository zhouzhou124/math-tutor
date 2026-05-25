#!/usr/bin/env python3
"""P26: Audit StateMachineSplitter for over-segmentation.

Checks if 2024/2025 question counts exceed expected ranges per exam.
Read-only — never modifies data.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_EXPECTED_RANGES = {
    # year: (min, max) questions per exam
    2024: (20, 24),
    2025: (20, 24),
    2026: (20, 50),  # 2026 may have more due to simulations mixed in
}


def main():
    from database.question_db import QuestionDB
    db = QuestionDB()
    index = db._load_index()
    cats = index.get("categories", {})

    print("P26: Splitter Over-Segmentation Audit\n")

    issues = 0
    for math_type, mt_data in cats.items():
        for year_key in sorted(mt_data.keys()):
            # Count total questions for this year+type
            total = sum(len(ids) for ids in mt_data[year_key].values())
            try:
                year_int = int(year_key)
            except ValueError:
                year_int = 0

            expected = _EXPECTED_RANGES.get(year_int)
            status = ""
            if expected:
                lo, hi = expected
                if total > hi:
                    status = f"SUSPICIOUS: {total} > {hi} expected max"
                    issues += 1
                elif total < lo:
                    status = f"LOW: {total} < {lo} expected min"

            print(f"  {math_type:20s} {year_key:8s}  total={total:3d}  {status}")

    print(f"\n{issues} suspicious entries found.")
    if issues == 0:
        print("No over-segmentation detected.")
    else:
        print("Review the flagged years — may need splitter rule adjustment.")

    # Summary
    all_counts = {}
    for mt_data in cats.values():
        for year_key, types in mt_data.items():
            for qtype, ids in types.items():
                for qid in ids:
                    all_counts[qid] = all_counts.get(qid, 0) + 1

    dupes = {k: v for k, v in all_counts.items() if v > 1}
    if dupes:
        print(f"\n{len(dupes)} duplicate question IDs found (appear in multiple categories):")
        for qid, count in sorted(dupes.items())[:10]:
            print(f"  {qid}: {count}x")
    else:
        print("\nNo duplicate question IDs found.")


if __name__ == "__main__":
    main()
