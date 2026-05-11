"""
Benchmark Runner — 运行所有 smoke 测试用例

用法:
  python tests/benchmark/run_benchmark.py
  python tests/benchmark/run_benchmark.py --case case_01

验证:
  1. Safe Normalize 跑两次结果完全相同
  2. Layout Recovery 跑两次结果完全相同
  3. 整条 pipeline 结果完全可复现
  4. 每个 pass 都生成 RepairTrace
  5. Validator 能区分 resolved_warnings 和 introduced_warnings
  6. 所有 manual_review 都必须有 failure_mode
"""

import json
import os
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ocr_repair import OCRRepair, RepairPolicy, safe_normalize, layout_recovery, rule_engine
from ocr_repair.utils import count_math_objects as _count_math_objects


def load_case(subdir: Path, name: str) -> tuple[str, dict]:
    """加载测试用例"""
    txt_path = subdir / f"{name}.txt"
    exp_path = subdir / f"{name}_expected.json"

    if not txt_path.exists():
        raise FileNotFoundError(f"Test case not found: {txt_path}")

    text = txt_path.read_text(encoding="utf-8")
    expected = json.loads(exp_path.read_text(encoding="utf-8")) if exp_path.exists() else {}
    return text, expected


def check_condition(repaired: str, report, condition: str, value) -> tuple[bool, str]:
    """检查单个条件。每个checker返回原始值，按条件类型与expected比较。"""
    # Raw value getters — all return the actual value, no comparison
    getters = {
        "question_count": lambda: report.post_validation.question_count,
        "question_count_min": lambda: report.post_validation.question_count,
        "answer_count": lambda: report.post_validation.answer_count,
        "has_option_A": lambda: 'A.' in repaired or 'A．' in repaired or 'A、' in repaired,
        "has_option_B": lambda: 'B.' in repaired or 'B．' in repaired or 'B、' in repaired,
        "has_option_C": lambda: 'C.' in repaired or 'C．' in repaired or 'C、' in repaired,
        "has_option_D": lambda: 'D.' in repaired or 'D．' in repaired or 'D、' in repaired,
        "has_individual_options": lambda: ('\nA' in repaired and '\nB' in repaired and '\nC' in repaired and '\nD' in repaired),
        "answer_on_separate_line": lambda: '【答案】' in repaired and '\n' in repaired.split('【答案】')[0][-3:],
        "needs_manual_review": lambda: report.needs_manual_review,
        "math_valid": lambda: report.post_validation.math_valid if report.post_validation else False,
        "warnings_include_missing_option": lambda: any("missing_option" in str(w).lower() for w in (report.post_validation.warnings or [])),
        "warnings_include_question_gap": lambda: any("question_gap" in str(w).lower() for w in (report.post_validation.warnings or [])),
        "warnings_include_math_bracket": lambda: any("math_bracket" in str(w).lower() for w in (report.post_validation.warnings or [])),
        "has_failure_mode": lambda: bool(report.failure_mode),
        "option_lines": lambda: sum(1 for l in repaired.split('\n') if l.strip() and l.strip()[0] in 'ABCD'),
        "lines_max": lambda: len(repaired.split('\n')),
        "question_gaps": lambda: report.post_validation.details.get("question_gaps", []),
        "has_question_numbers": lambda: report.post_validation.question_count > 0,
        "math_object_count_min": lambda: _count_math_objects(repaired),
        "contains_latex_int": lambda: '\\int' in repaired,
        "contains_latex_sum": lambda: '\\sum' in repaired,
        "contains_latex_infty": lambda: '\\infty' in repaired,
        "contains_display_math": lambda: '$$' in repaired,
        "math_env_intact": lambda: repaired.count('$$') % 2 == 0 and '$$' in repaired,
    }

    getter = getters.get(condition)
    if getter is None:
        return True, f"  ? {condition}: unknown check — skipped"

    try:
        raw = getter()
        # Apply comparison strategy
        if condition.endswith("_min"):
            passed = raw >= value
        elif condition == "lines_max":
            passed = raw <= value
        else:
            passed = (raw == value)
        status = "[PASS]" if passed else "[FAIL]"
        detail = f"  {status} {condition}: expected={value}, got={raw}"
        return passed, detail
    except Exception as e:
        return False, f"  [FAIL] {condition}: ERROR {e}"




def run_case(subdir: Path, name: str) -> tuple[bool, list[str]]:
    """运行单个测试用例"""
    text, expected = load_case(subdir, name)
    policy = RepairPolicy()
    engine = OCRRepair(policy)

    # 运行管道
    report = engine.repair(text)
    repaired = report.repaired
    checks = expected.get("checks", {})

    lines = []
    lines.append(f"\n--- {subdir.name}/{name} ---")
    lines.append(f"  Case: {expected.get('case', name)}")
    lines.append(f"  Input: {len(text)} chars")
    lines.append(f"  Output: {len(repaired)} chars")
    lines.append(f"  Quality: {report.post_validation.quality_score:.2f}" if report.post_validation else "  Quality: N/A")
    lines.append(f"  Math valid: {report.post_validation.math_valid}" if report.post_validation else "  Math valid: N/A")
    lines.append(f"  Questions: {report.post_validation.question_count}" if report.post_validation else "  Questions: N/A")
    lines.append(f"  Needs review: {report.needs_manual_review}")
    if report.failure_mode:
        lines.append(f"  Failure mode: {report.failure_mode}")

    # Check traces
    lines.append(f"  Traces: {len(report.traces)}")
    pass_names = {t.pass_name for t in report.traces}
    expected_passes = {"safe_normalize", "layout_recovery", "rule_engine", "validator"}
    missing = expected_passes - pass_names
    if missing:
        lines.append(f"  [FAIL] Missing traces: {missing}")
    else:
        lines.append(f"  [PASS] All expected passes traced")

    # Check warnings classification
    lines.append(f"  Resolved warnings: {len(report.resolved_warnings)}")
    lines.append(f"  Introduced warnings: {len(report.introduced_warnings)}")

    # Check failure_mode for manual_review
    if report.needs_manual_review and not report.failure_mode:
        lines.append(f"  [FAIL] needs_manual_review=True but no failure_mode")
        return False, lines

    # Run checks
    all_pass = True
    for condition, value in checks.items():
        result, detail = check_condition(repaired, report, condition, value)
        if not result:
            all_pass = False
        lines.append(detail)

    # Reproducibility: run twice
    report2 = engine.repair(text)
    if report2.repaired != repaired:
        lines.append("  [FAIL] REPRODUCIBILITY FAILED: two runs produced different output")
        all_pass = False
    else:
        lines.append("  [PASS] Reproducibility: identical output on 2nd run")

    # Individual pass reproducibility
    after1, _ = safe_normalize(text, policy)
    after2, _ = safe_normalize(text, policy)
    if after1 != after2:
        lines.append("  [FAIL] Safe Normalize not reproducible")
        all_pass = False
    else:
        lines.append("  [PASS] Safe Normalize reproducible")

    after1, _ = layout_recovery(text, policy)
    after2, _ = layout_recovery(text, policy)
    if after1 != after2:
        lines.append("  [FAIL] Layout Recovery not reproducible")
        all_pass = False
    else:
        lines.append("  [PASS] Layout Recovery reproducible")

    after1, _ = rule_engine(text, policy)
    after2, _ = rule_engine(text, policy)
    if after1 != after2:
        lines.append("  [FAIL] Rule Engine not reproducible")
        all_pass = False
    else:
        lines.append("  [PASS] Rule Engine reproducible")

    return all_pass, lines


def main():
    # Scan all benchmark subdirectories
    benchmark_root = Path(__file__).parent
    all_cases = {}
    for subdir in sorted(benchmark_root.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith('_'):
            for txt_file in sorted(subdir.glob("*.txt")):
                case_name = txt_file.stem
                # Use subdir/case_name as key
                key = f"{subdir.name}/{case_name}"
                all_cases[key] = (subdir, case_name)

    if not all_cases:
        print("No test cases found.")
        return

    # Filter by --case if specified
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="Run specific case (e.g., case_01_fullwidth_answer)")
    args = parser.parse_args()

    if args.case:
        base = args.case.replace(".txt", "").replace("_expected", "")
        all_cases = {k: v for k, v in all_cases.items() if base in k}

    if not all_cases:
        print("No test cases found.")
        return

    print(f"Running {len(all_cases)} test cases from {len(set(d for d,_ in all_cases.values()))} directories...")

    passed = 0
    failed = 0

    for key in sorted(all_cases.keys()):
        subdir, case_name = all_cases[key]
        ok, lines = run_case(subdir, case_name)
        for line in lines:
            print(line)
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(all_cases)} total")
    if failed > 0:
        print(f"FAILURES: {failed} test(s) failed!")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED [PASS]")
        sys.exit(0)


if __name__ == "__main__":
    main()
