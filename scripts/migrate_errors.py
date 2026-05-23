"""
Migrate errors.json → per-user files (errors/{user_id}.json).

Also strips redundant fields (question, standard_answer, solution_steps)
that can be looked up from QuestionDB.
"""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OLD_FILE = ROOT / "storage" / "data" / "errors.json"
ERRORS_DIR = ROOT / "storage" / "data" / "errors"


def main():
    if not OLD_FILE.exists():
        print(f"{OLD_FILE} not found — nothing to migrate")
        return

    raw = json.loads(OLD_FILE.read_text(encoding="utf-8"))
    # Unwrap schema_version wrapper
    if isinstance(raw, dict) and "data" in raw:
        data = raw["data"]
    else:
        data = raw
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)

    total_users = 0
    total_records = 0
    stripped_fields = 0
    fields_to_strip = {"question", "standard_answer", "solution_steps"}

    for user_id, user_data in data.items():
        if not isinstance(user_data, dict):
            continue
        records = user_data.get("records", [])
        if not records:
            continue

        # Strip redundant fields
        for r in records:
            for f in fields_to_strip:
                if f in r:
                    del r[f]
                    stripped_fields += 1

        # Cap at 200
        if len(records) > 200:
            records = records[-200:]
            user_data["records"] = records

        # Recalculate stats
        stats = {"total_errors": len(records), "by_chapter": {}, "by_type": {},
                 "by_difficulty": {}, "repeat_rate": 0.0}
        for r in records:
            ch = r.get("knowledge_point", "未知").split(" - ")[0]
            stats["by_chapter"][ch] = stats["by_chapter"].get(ch, 0) + 1
            et = r.get("error_type", "未分类")
            stats["by_type"][et] = stats["by_type"].get(et, 0) + 1
            df = r.get("difficulty", "中等")
            stats["by_difficulty"][df] = stats["by_difficulty"].get(df, 0) + 1
        repeats = sum(1 for r in records if r.get("is_repeat"))
        stats["repeat_rate"] = repeats / len(records) if records else 0.0

        # Write per-user file
        out = {"records": records, "stats": stats}
        out_path = ERRORS_DIR / f"{user_id}.json"
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

        total_users += 1
        total_records += len(records)
        print(f"  {user_id}: {len(records)} records → {out_path.name}")

    # Rename old file as backup
    backup = OLD_FILE.with_suffix(".json.bak")
    OLD_FILE.rename(backup)

    print(f"\nDone: {total_users} users, {total_records} records migrated")
    print(f"Stripped {stripped_fields} redundant fields")
    print(f"Old file backed up as {backup}")


if __name__ == "__main__":
    main()
