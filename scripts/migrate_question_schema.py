"""
One-time migration: add raw_question_text + raw_answer_text to all question JSON files.

四层分离迁移:
  - raw_question_text ← 当前 question 字段值（原始文本）
  - raw_answer_text   ← 当前 standard_answer 字段值（原始答案）
  - question / standard_answer 旧字段保留作为向后兼容

用法:
  python scripts/migrate_question_schema.py --dry-run    # 仅报告
  python scripts/migrate_question_schema.py --backup     # 备份后迁移
  python scripts/migrate_question_schema.py --verify     # 验证迁移结果
"""

import json
import os
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Directories to migrate
DIRS = [
    ROOT / "storage" / "questions" / "exams",
    ROOT / "storage" / "questions" / "simulations1",
    ROOT / "storage" / "questions" / "simulations2",
    ROOT / "storage" / "questions" / "simulations3",
    ROOT / "storage" / "questions" / "simulations4",
]

BACKUP_BASE = ROOT / "storage" / "questions" / "_schema_backups"


def find_json_files():
    """Find all JSON question files."""
    files = []
    for d in DIRS:
        if d.exists():
            for f in sorted(d.glob("*.json")):
                files.append(f)
    return files


def backup(files: list[Path], timestamp: str):
    """Backup all files before migration."""
    backup_dir = BACKUP_BASE / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for fp in files:
        rel = fp.relative_to(ROOT)
        dest = backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fp, dest)
        count += 1
    print(f"Backup: {count} files → {backup_dir}")


def migrate_file(fp: Path, dry_run: bool) -> dict:
    """Migrate a single file. Returns stats dict."""
    stats = {"ok": 0, "skip": 0, "error": 0}
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ERROR reading {fp.name}: {e}")
        stats["error"] += 1
        return stats

    changed = False

    # Add raw_question_text if missing
    if not data.get("raw_question_text"):
        q_text = data.get("question", "")
        if q_text:
            data["raw_question_text"] = q_text
            changed = True

    # Add raw_answer_text if missing
    if not data.get("raw_answer_text"):
        a_text = data.get("standard_answer", "")
        if a_text:
            data["raw_answer_text"] = a_text
            changed = True

    if changed and not dry_run:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        stats["ok"] += 1
    elif changed:
        stats["ok"] += 1  # would migrate
    else:
        stats["skip"] += 1

    return stats


def verify(files: list[Path]):
    """Verify all files have the new fields."""
    missing_raw_q = []
    missing_raw_a = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not data.get("raw_question_text"):
            missing_raw_q.append(fp.name)
        if not data.get("raw_answer_text") and data.get("standard_answer"):
            missing_raw_a.append(fp.name)

    total = len(files)
    ok_q = total - len(missing_raw_q)
    ok_a = total - len(missing_raw_a)
    print(f"raw_question_text: {ok_q}/{total} OK")
    print(f"raw_answer_text:   {ok_a}/{total} OK")
    if missing_raw_q:
        print(f"  Missing raw_question_text ({len(missing_raw_q)}):")
        for name in missing_raw_q[:10]:
            print(f"    {name}")
        if len(missing_raw_q) > 10:
            print(f"    ... and {len(missing_raw_q) - 10} more")


def main():
    parser = argparse.ArgumentParser(description="Migrate question JSON schema")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    parser.add_argument("--backup", action="store_true", help="Backup before migration")
    parser.add_argument("--verify", action="store_true", help="Verify migration results")
    args = parser.parse_args()

    files = find_json_files()
    print(f"Found {len(files)} question files\n")

    if args.verify:
        verify(files)
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.backup:
        print("Creating backup...")
        backup(files, timestamp)
        print()

    if args.dry_run:
        print("DRY RUN — no files will be modified\n")

    stats = {"ok": 0, "skip": 0, "error": 0}
    for fp in files:
        s = migrate_file(fp, dry_run=args.dry_run)
        for k in stats:
            stats[k] += s[k]

    print(f"\nResults: {stats['ok']} migrated, {stats['skip']} skipped, {stats['error']} errors")

    if not args.dry_run and stats['ok'] > 0:
        print("\nVerifying...")
        verify(files)


if __name__ == "__main__":
    main()
