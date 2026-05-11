"""
rebuild_db.py — 一键重建数据库

用法:
  python rebuild_db.py              # 完整重建
  python rebuild_db.py --dry-run    # 仅提取不导入
  python rebuild_db.py --verify     # 验证现有数据

流程:
  backup → extract → validate → import → verify → report
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# ── 配置 ──
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "storage" / "questions" / "data"
INDEX_PATH = PROJECT_ROOT / "storage" / "questions" / "_index.json"
BACKUP_DIR = PROJECT_ROOT / "storage" / "questions"
PAPERS_DIR = PROJECT_ROOT / "storage" / "math1_source" / "Kaoyan-Math1-Papers-main" / "papers"
BENCHMARK_SCRIPT = PROJECT_ROOT / "tests" / "benchmark" / "run_benchmark.py"
SOLUTIONS_DIR = PROJECT_ROOT / "storage" / "math1_source" / "Kaoyan-Math1-Papers-main" / "solutions"


def backup(timestamp: str) -> str:
    """备份现有数据"""
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    os.makedirs(backup_path, exist_ok=True)
    count = 0
    if DATA_DIR.exists():
        for f in os.listdir(DATA_DIR):
            if f.endswith('.json'):
                shutil.copy2(DATA_DIR / f, backup_path / f)
                count += 1
    print(f"[backup] {count} files → {backup_path}")
    return str(backup_path)


def clear():
    """清空现有数据"""
    if DATA_DIR.exists():
        for f in os.listdir(DATA_DIR):
            if f.endswith('.json'):
                os.remove(DATA_DIR / f)
    if INDEX_PATH.exists():
        os.remove(INDEX_PATH)
    print("[clear] data + index cleared")


def extract() -> tuple[list[dict], dict]:
    """用完整管道提取所有题目"""
    from exam_parser import ExamParserPipeline
    from database import QuestionDB

    db = QuestionDB()
    pipeline = ExamParserPipeline(db=db)
    results = pipeline.process_directory(str(PAPERS_DIR))

    all_qs = []
    year_stats = {}
    for r in results:
        all_qs.extend(r.questions)
        y = r.year
        if y not in year_stats:
            year_stats[y] = {"total": 0, "with_ans": 0, "with_sol": 0}
        year_stats[y]["total"] += r.total_questions
        year_stats[y]["with_ans"] += r.stats.get("answers_found", 0)
        year_stats[y]["with_sol"] += r.stats.get("solutions_found", 0)

    return all_qs, year_stats


def import_questions(all_qs: list[dict]) -> dict:
    """导入题目到数据库"""
    from database import QuestionDB, QuestionImporter
    db = QuestionDB()
    importer = QuestionImporter(db)
    return importer.import_dict(all_qs)


def verify() -> dict:
    """验证数据库完整性"""
    from database import QuestionDB
    db = QuestionDB()
    stats = db.stats()

    data_dir = DATA_DIR
    files = [f for f in os.listdir(data_dir) if f.endswith('.json')] if data_dir.exists() else []
    with_ans = sum(1 for f in files if json.load(
        open(data_dir / f, encoding='utf-8')).get('standard_answer', '').strip())
    with_sol = sum(1 for f in files if json.load(
        open(data_dir / f, encoding='utf-8')).get('solution_steps'))
    with_kp = sum(1 for f in files if json.load(
        open(data_dir / f, encoding='utf-8')).get('knowledge_points'))

    return {
        "total": len(files),
        "with_answers": with_ans,
        "with_solutions": with_sol,
        "with_knowledge": with_kp,
        "years": sorted(stats.get("years_covered", [])),
    }


def run_benchmark() -> bool:
    """运行benchmark"""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(BENCHMARK_SCRIPT)],
        capture_output=True, text=True, timeout=120,
    )
    success = "ALL TESTS PASSED" in result.stdout
    print(f"[benchmark] {'PASS' if success else 'FAIL'}")
    if not success:
        print(result.stdout[-500:])
    return success


def generate_report(timestamp: str, year_stats: dict, verify_data: dict,
                    import_report: dict = None) -> str:
    """生成构建报告"""
    lines = []
    lines.append(f"# Build Report — {timestamp}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Total: {verify_data['total']} questions")
    lines.append(f"- Answers: {verify_data['with_answers']} ({verify_data['with_answers']/max(verify_data['total'],1)*100:.1f}%)")
    lines.append(f"- Solutions: {verify_data['with_solutions']} ({verify_data['with_solutions']/max(verify_data['total'],1)*100:.1f}%)")
    lines.append(f"- Knowledge: {verify_data['with_knowledge']} ({verify_data['with_knowledge']/max(verify_data['total'],1)*100:.1f}%)")
    lines.append(f"- Years: {len(verify_data['years'])} ({min(verify_data['years'])}-{max(verify_data['years'])})")

    if import_report:
        lines.append(f"- Import: {import_report['success']} success, {import_report['skipped_duplicates']} skipped, {import_report['failed']} failed")

    lines.append("")
    lines.append("## Per Year")
    lines.append("| Year | Questions | With Answers | Coverage |")
    lines.append("|------|-----------|-------------|----------|")
    for y in sorted(year_stats.keys()):
        s = year_stats[y]
        pct = s['with_ans'] / max(s['total'], 1) * 100
        bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
        lines.append(f"| {y} | {s['total']} | {s['with_ans']} | {bar} {pct:.0f}% |")

    report_path = BACKUP_DIR / f"build_report_{timestamp}.md"
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    return str(report_path)


def main():
    parser = argparse.ArgumentParser(description="考研数学真题数据库重建")
    parser.add_argument("--dry-run", action="store_true", help="仅提取不导入")
    parser.add_argument("--verify", action="store_true", help="仅验证现有数据")
    parser.add_argument("--skip-benchmark", action="store_true", help="跳过benchmark")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.verify:
        v = verify()
        print(f"Total: {v['total']} | Answers: {v['with_answers']} ({v['with_answers']/max(v['total'],1)*100:.0f}%)")
        return

    print(f"=== rebuild_db — {timestamp} ===\n")

    # 1. Backup
    print("[1/5] Backup...")
    backup(timestamp)

    # 2. Extract
    print("[2/5] Extract...")
    all_qs, year_stats = extract()
    print(f"  {len(all_qs)} questions from {len(year_stats)} years")

    if args.dry_run:
        print("[dry-run] Skipping import. Questions extracted but not saved.")
        # Still generate report
        report_path = generate_report(timestamp, year_stats, {
            "total": len(all_qs),
            "with_answers": sum(1 for q in all_qs if q.get('standard_answer', '').strip()),
            "with_solutions": sum(1 for q in all_qs if q.get('solution_steps')),
            "with_knowledge": sum(1 for q in all_qs if q.get('knowledge_points')),
            "years": sorted(year_stats.keys()),
        })
        print(f"Report: {report_path}")
        return

    # 3. Clear & Import
    print("[3/5] Clear & Import...")
    clear()
    import_report = import_questions(all_qs)
    print(f"  {import_report['success']} success, {import_report['skipped_duplicates']} skipped, {import_report['failed']} failed")

    # 4. Verify
    print("[4/5] Verify...")
    v = verify()
    print(f"  {v['total']} questions, {v['with_answers']} with answers ({v['with_answers']/max(v['total'],1)*100:.0f}%)")

    # 5. Benchmark
    if not args.skip_benchmark:
        print("[5/5] Benchmark...")
        ok = run_benchmark()
        if not ok:
            print("WARNING: Benchmark failed! Check output above.")
    else:
        print("[5/5] Benchmark skipped.")

    # Report
    report_path = generate_report(timestamp, year_stats, v, import_report)
    print(f"\nReport: {report_path}")
    print("Done.")


if __name__ == "__main__":
    main()
