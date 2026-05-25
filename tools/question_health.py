"""Health check and repair tool for the active question dataset.

The app currently stores active questions under storage/questions/exams,
storage/questions/simulations1, and storage/questions/simulations2. A
legacy storage/questions/data directory is also supported when present.
Historical build artifacts and backups are intentionally ignored.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_ROOT = ROOT / "storage" / "questions"
DATA_DIRS = [
    QUESTIONS_ROOT / "data",
    QUESTIONS_ROOT / "exams",
    QUESTIONS_ROOT / "simulations1",
    QUESTIONS_ROOT / "simulations2",
]
SOURCE_OF_TRUTH = "storage/questions/{data,exams,simulations1,simulations2}"
INDEX_PATH = ROOT / "storage" / "questions" / "_index.json"
VERSION_PATH = ROOT / "VERSION.json"

MATH1 = "\u6570\u5b66\u4e00"
YUGE8 = "26\u5b87\u54e5\u516b\u5957\u5377"
VOLUME_NAMES = {
    1: "\u7b2c\u4e00\u5957",
    2: "\u7b2c\u4e8c\u5957",
    3: "\u7b2c\u4e09\u5957",
    4: "\u7b2c\u56db\u5957",
    5: "\u7b2c\u4e94\u5957",
    6: "\u7b2c\u516d\u5957",
    7: "\u7b2c\u4e03\u5957",
    8: "\u7b2c\u516b\u5957",
}

QUESTION_TYPES = [
    "\u9009\u62e9\u9898",
    "\u586b\u7a7a\u9898",
    "\u89e3\u7b54\u9898",
    "\u8bc1\u660e\u9898",
]

REQUIRED_FIELDS = ["question_id", "year", "category", "question_type", "question"]


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_questions() -> list[tuple[Path, dict[str, Any]]]:
    questions: list[tuple[Path, dict[str, Any]]] = []
    seen: set[Path] = set()
    for data_dir in DATA_DIRS:
        if not data_dir.exists():
            continue
        for path in sorted(data_dir.glob("*.json")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            questions.append((path, read_json(path)))
    return questions


def infer_volume(question: dict[str, Any]) -> str:
    volume = question.get("volume")
    if volume:
        return str(volume)

    if question.get("category") != YUGE8:
        return ""

    haystack = f"{question.get('question_id', '')} {question.get('source', '')}"
    match = re.search(r"(?:vol|卷)(\d+)", haystack, flags=re.IGNORECASE)
    if not match:
        return ""
    number = int(match.group(1))
    return VOLUME_NAMES.get(number, f"vol{number}")


def category_group(question: dict[str, Any]) -> str:
    volume = question.get("volume") or infer_volume(question)
    if volume:
        return str(volume)
    return str(question.get("year", ""))


def normalize_answer(answer: str) -> tuple[str, bool]:
    cleaned = re.sub(r"^\s*\$\s*\d+\s*\.\s*\$\s*", "", answer or "")
    cleaned = re.sub(r"^\s*\d+\s*[\.\uff0e]\s+", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned, cleaned != (answer or "").strip()


def answer_prefix_number(answer: str) -> int | None:
    match = re.match(r"^\s*\$\s*(\d+)\s*\.\s*\$", answer or "")
    if match:
        return int(match.group(1))
    match = re.match(r"^\s*(\d+)\s*[\.\uff0e]\s+", answer or "")
    if match:
        return int(match.group(1))
    return None


def rebuild_index(questions: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, dict[str, dict[str, list[str]]]] = {}
    knowledge_index: dict[str, list[str]] = defaultdict(list)
    difficulty_index: dict[str, list[str]] = defaultdict(list)

    for question in sorted(
        questions,
        key=lambda q: (
            str(q.get("category", "")),
            category_group(q),
            str(q.get("question_type", "")),
            int(q.get("question_no") or 0),
            str(q.get("question_id", "")),
        ),
    ):
        qid = question["question_id"]
        category = question["category"]
        group = category_group(question)
        qtype = question["question_type"]
        categories.setdefault(category, {}).setdefault(group, {}).setdefault(qtype, [])
        if qid not in categories[category][group][qtype]:
            categories[category][group][qtype].append(qid)

        for tag in sorted(set(question.get("knowledge_points", []) + question.get("tags", []))):
            if qid not in knowledge_index[tag]:
                knowledge_index[tag].append(qid)

        difficulty = question.get("difficulty") or "\u4e2d\u7b49"
        if qid not in difficulty_index[difficulty]:
            difficulty_index[difficulty].append(qid)

    years = sorted(
        {
            int(q["year"])
            for q in questions
            if q.get("category") == MATH1 and str(q.get("year", "")).isdigit()
        }
    )
    volumes: dict[str, list[str]] = {}
    for category, groups in categories.items():
        non_year_groups = [group for group in groups if not group.isdigit()]
        if non_year_groups:
            volumes[category] = sorted(non_year_groups)

    return {
        "categories": categories,
        "knowledge_index": dict(sorted(knowledge_index.items())),
        "difficulty_index": dict(sorted(difficulty_index.items())),
        "metadata": {
            "total_questions": len(questions),
            "years_covered": years,
            "volumes": volumes,
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "categories": sorted(categories.keys()),
            "source_of_truth": SOURCE_OF_TRUTH,
            "missing_data": [],
            "pending_review": [],
        },
    }


def flatten_index_ids(index: dict[str, Any]) -> dict[str, tuple[str, str, str]]:
    result: dict[str, tuple[str, str, str]] = {}
    for category, groups in index.get("categories", {}).items():
        for group, type_map in groups.items():
            if not isinstance(type_map, dict):
                continue
            for qtype, ids in type_map.items():
                for qid in ids:
                    result[qid] = (category, group, qtype)
    return result


def build_report(
    questions_with_paths: list[tuple[Path, dict[str, Any]]],
    index: dict[str, Any] | None,
) -> dict[str, Any]:
    questions = [q for _, q in questions_with_paths]
    file_ids = [q.get("question_id", "") for q in questions]
    id_counts = Counter(file_ids)
    duplicate_ids = sorted([qid for qid, count in id_counts.items() if qid and count > 1])

    missing_required: list[dict[str, Any]] = []
    answer_prefixes: list[dict[str, Any]] = []
    answer_number_mismatches: list[dict[str, Any]] = []
    missing_solution = []
    missing_answer = []
    missing_volume = []

    by_category = Counter()
    by_question_type = Counter()
    by_year = Counter()

    for path, question in questions_with_paths:
        qid = question.get("question_id", path.stem)
        by_category[question.get("category", "")] += 1
        by_question_type[question.get("question_type", "")] += 1
        by_year[question.get("year", "")] += 1

        fields = [field for field in REQUIRED_FIELDS if not question.get(field)]
        if fields:
            missing_required.append({"question_id": qid, "fields": fields})

        if not question.get("standard_answer"):
            missing_answer.append(qid)

        if not question.get("solution_steps"):
            missing_solution.append(qid)

        if question.get("category") == YUGE8 and not question.get("volume"):
            missing_volume.append(qid)

        prefix = answer_prefix_number(question.get("standard_answer", ""))
        if prefix is not None:
            answer_prefixes.append({"question_id": qid, "answer_no": prefix})
            question_no = question.get("question_no")
            if question_no and int(question_no) != prefix:
                answer_number_mismatches.append(
                    {
                        "question_id": qid,
                        "question_no": question_no,
                        "answer_no": prefix,
                    }
                )

    rebuilt_index = rebuild_index(questions)
    existing_map = flatten_index_ids(index or {})
    rebuilt_map = flatten_index_ids(rebuilt_index)
    missing_from_index = sorted(set(file_ids) - set(existing_map))
    stale_index_ids = sorted(set(existing_map) - set(file_ids))
    index_mismatches = [
        {"question_id": qid, "current": existing_map[qid], "expected": rebuilt_map[qid]}
        for qid in sorted(set(file_ids) & set(existing_map))
        if existing_map[qid] != rebuilt_map[qid]
    ]

    return {
        "total_files": len(questions_with_paths),
        "index_total": (index or {}).get("metadata", {}).get("total_questions"),
        "by_category": dict(sorted(by_category.items())),
        "by_question_type": dict(sorted(by_question_type.items())),
        "by_year": dict(sorted(by_year.items(), key=lambda item: str(item[0]))),
        "duplicate_ids": duplicate_ids,
        "missing_required": missing_required,
        "missing_answer_count": len(missing_answer),
        "missing_solution_count": len(missing_solution),
        "missing_volume_count": len(missing_volume),
        "answer_prefix_count": len(answer_prefixes),
        "answer_number_mismatch_count": len(answer_number_mismatches),
        "missing_from_index": missing_from_index,
        "stale_index_ids": stale_index_ids,
        "index_mismatch_count": len(index_mismatches),
        "index_mismatch_examples": index_mismatches[:20],
    }


def backup_current_dataset() -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = ROOT / "storage" / "questions" / f"current_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=False)
    for data_dir in DATA_DIRS:
        if data_dir.exists():
            shutil.copytree(data_dir, backup_dir / data_dir.name)
    if INDEX_PATH.exists():
        shutil.copy2(INDEX_PATH, backup_dir / "_index.json")
    return backup_dir


def update_version(questions: list[dict[str, Any]]) -> None:
    version = read_json(VERSION_PATH) if VERSION_PATH.exists() else {}
    total = len(questions)
    with_answers = sum(1 for q in questions if q.get("standard_answer"))
    with_solutions = sum(1 for q in questions if q.get("solution_steps"))
    math1_years = sorted(
        {
            int(q["year"])
            for q in questions
            if q.get("category") == MATH1 and str(q.get("year", "")).isdigit()
        }
    )
    volumes = sorted({category_group(q) for q in questions if q.get("category") != MATH1})
    version.update(
        {
            "parser_version": version.get("parser_version", "0.6.0-stable"),
            "frozen": False,
            "frozen_date": "",
            "dataset_policy": "current_active_questions_only",
            "dataset": {
                "source_of_truth": SOURCE_OF_TRUTH,
                "years": (
                    f"{math1_years[0]}-{math1_years[-1]}" if math1_years else ""
                ),
                "math1_years": math1_years,
                "extra_volumes": volumes,
                "total_questions": total,
                "answer_coverage": round(with_answers / total, 3) if total else 0,
                "solution_coverage": round(with_solutions / total, 3) if total else 0,
            },
            "last_updated": time.strftime("%Y-%m-%d"),
            "rule": f"{SOURCE_OF_TRUTH} is the active dataset",
        }
    )
    write_json(VERSION_PATH, version)


def apply_repairs() -> dict[str, Any]:
    questions_with_paths = load_questions()
    backup_dir = backup_current_dataset()
    repaired_questions = []

    for path, question in questions_with_paths:
        answer, changed = normalize_answer(question.get("standard_answer", ""))
        if changed:
            question["standard_answer"] = answer

        volume = infer_volume(question)
        if volume and not question.get("volume"):
            question["volume"] = volume

        repaired_questions.append(question)
        write_json(path, question)

    write_json(INDEX_PATH, rebuild_index(repaired_questions))
    update_version(repaired_questions)
    return {"backup_dir": str(backup_dir)}


def print_human_report(report: dict[str, Any], repair_info: dict[str, Any] | None) -> None:
    print("Question dataset health")
    print(f"- total files: {report['total_files']}")
    print(f"- index total: {report['index_total']}")
    print(f"- by category: {report['by_category']}")
    print(f"- by question type: {report['by_question_type']}")
    print(f"- duplicate ids: {len(report['duplicate_ids'])}")
    print(f"- missing required: {len(report['missing_required'])}")
    print(f"- missing answers: {report['missing_answer_count']}")
    print(f"- missing solutions: {report['missing_solution_count']}")
    print(f"- missing volumes: {report['missing_volume_count']}")
    print(f"- answer prefixes: {report['answer_prefix_count']}")
    print(f"- answer number mismatches: {report['answer_number_mismatch_count']}")
    print(f"- missing from index: {len(report['missing_from_index'])}")
    print(f"- stale index ids: {len(report['stale_index_ids'])}")
    print(f"- index mismatches: {report['index_mismatch_count']}")
    if report["index_mismatch_examples"]:
        print("- index mismatch examples:")
        for item in report["index_mismatch_examples"][:5]:
            print(f"  {item['question_id']}: {item['current']} -> {item['expected']}")
    if repair_info:
        print(f"- backup: {repair_info['backup_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="repair data and rebuild index")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args()

    if not any(path.exists() for path in DATA_DIRS):
        print(f"No data directories found under {QUESTIONS_ROOT}", file=sys.stderr)
        return 2

    index = read_json(INDEX_PATH) if INDEX_PATH.exists() else None
    before = build_report(load_questions(), index)
    repair_info = None

    if args.fix:
        repair_info = apply_repairs()
        index = read_json(INDEX_PATH)
        report = build_report(load_questions(), index)
    else:
        report = before

    output = {"before": before, "after": report, "repair": repair_info}
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if args.fix:
            print("Before repair:")
            print_human_report(before, None)
            print()
            print("After repair:")
        print_human_report(report, repair_info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
