"""
批量标准答案生成与校验系统

核心思路：每道题的标准答案必须是 LLM 生成的带详细步骤的 CanonicalSolutionTrace，
而不是预先手工输入的简略答案。逐步骤批改时直接参考该标准答案。

用法:
    python validate_answers.py                          # dry-run：报告缺失/不完整的答案
    python validate_answers.py --generate               # 生成 text 标准答案（轻量）
    python validate_answers.py --generate --trace        # 生成 CanonicalSolutionTrace（推荐，支持图批改）
    python validate_answers.py --generate --force        # 强制重新生成
    python validate_answers.py --generate --trace --force # 强制重新生成 trace
    python validate_answers.py --validate                # 校验已有答案的完整性
    python validate_answers.py --validate --fix          # 校验并删除不完整的答案
"""

import sys
import os
import json
import argparse
import time

# ── 路径修复 ──
_ROOT = os.path.dirname(os.path.realpath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
    SOLVER_MODEL,
)


# ═══════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════

def load_all_questions(data_dir: str) -> list:
    """加载所有题目 JSON 文件，返回 (data, filepath) 元组列表。"""
    results = []
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(data_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append((data, path))
        except Exception as e:
            print(f"  [跳过] {fname}: 读取失败 ({e})")
    return results


def save_question(path: str, data: dict):
    """写回题目 JSON。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_llm_client():
    """构建 LLM 客户端（支持 OpenAI / Anthropic 协议）。"""
    if not LLM_API_KEY:
        return None
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location("llm_client", os.path.join(_ROOT, "llm_client.py"))
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        # 尝试从 credential_store 读取协议
        protocol = "openai"
        try:
            _cs_spec = _ilu.spec_from_file_location("credential_store", os.path.join(_ROOT, "credential_store.py"))
            _cs = _ilu.module_from_spec(_cs_spec)
            _cs_spec.loader.exec_module(_cs)
            active = _cs.get_active_profile()
            if active:
                protocol = active.get("protocol", "openai")
        except Exception:
            pass
        return _mod.create_client(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, protocol=protocol)
    except Exception as e:
        # 回退到 OpenAI
        try:
            from openai import OpenAI
            return OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        except Exception:
            print(f"[错误] LLM 客户端初始化失败: {e}")
            return None


def get_solver(client):
    """获取 SolverAgent 实例。"""
    from agents.solver_agent import SolverAgent
    model = SOLVER_MODEL or LLM_MODEL or "deepseek-chat"
    return SolverAgent(client, model=model)


# ═══════════════════════════════════════════
#  答案完整性校验
# ═══════════════════════════════════════════

MIN_STEPS = 2


def check_answer_completeness(question: dict) -> dict:
    """检查一道题的答案是否完整。"""
    qtype = question.get("question_type", "")
    std_answer = (question.get("standard_answer") or "").strip()
    steps = question.get("solution_steps") or []
    step_count = len(steps) if isinstance(steps, list) else 0
    has_cs = bool(question.get("canonical_solution"))

    has_standard = bool(std_answer)
    has_steps = step_count >= MIN_STEPS

    # 有已验证的 canonical_solution → 直接通过
    if has_cs:
        cs = question["canonical_solution"]
        if cs.get("verified"):
            return {"complete": True, "reason": "canonical_solution 已验证", "action": "keep",
                    "has_standard": True, "has_steps": True, "step_count": step_count, "has_trace": True}
        return {"complete": True, "reason": "canonical_solution 存在（未验证）", "action": "keep",
                "has_standard": True, "has_steps": True, "step_count": step_count, "has_trace": True}

    # 选择题
    if qtype == "选择题":
        correct = question.get("correct_option", "")
        if not correct:
            return {"complete": False, "reason": "选择题缺少 correct_option", "action": "regenerate",
                    "has_standard": False, "has_steps": False, "step_count": 0, "has_trace": False}
        if not has_standard or not has_steps:
            return {"complete": False, "reason": f"选择题缺少详细解题过程（{step_count} 步）", "action": "regenerate",
                    "has_standard": has_standard, "has_steps": has_steps, "step_count": step_count, "has_trace": False}
        return {"complete": True, "reason": "选择题答案和解题过程完整", "action": "keep",
                "has_standard": True, "has_steps": True, "step_count": step_count, "has_trace": False}

    # 填空题 / 解答题 / 证明题
    if not has_standard:
        return {"complete": False, "reason": f"{qtype}缺少 standard_answer", "action": "regenerate",
                "has_standard": False, "has_steps": has_steps, "step_count": step_count, "has_trace": False}
    if not has_steps:
        return {"complete": False, "reason": f"{qtype}缺少详细解题过程（{step_count} 步）", "action": "regenerate",
                "has_standard": True, "has_steps": False, "step_count": step_count, "has_trace": False}

    return {"complete": True, "reason": f"{qtype}答案和解题过程完整（{step_count} 步）", "action": "keep",
            "has_standard": True, "has_steps": True, "step_count": step_count, "has_trace": False}


# ═══════════════════════════════════════════
#  LLM 答案生成（text 模式）
# ═══════════════════════════════════════════

def generate_standard_answer(solver, question: dict) -> dict | None:
    """调用 SolverAgent.solve() 生成文本标准解答。"""
    qtext = question.get("raw_question_text") or question.get("question", "")
    qtype = question.get("question_type", "解答题")
    category = question.get("category", "数学一")
    kps = question.get("knowledge_points") or []
    kp = kps[0] if kps else "未指定"

    result = solver.solve(
        question=qtext, math_type=category,
        question_type=qtype, knowledge_point=kp,
    )
    if not result.get("success"):
        return None

    steps_raw = result.get("steps", [])
    solution_steps = [s.get("content", "").strip() for s in steps_raw if s.get("content", "").strip()]

    if len(solution_steps) < MIN_STEPS:
        import re
        full_text = result.get("standard_answer", "")
        parts = re.split(r"###\s*步骤[一二三四五六七八九十\d]+", full_text)
        solution_steps = [p.strip() for p in parts if p.strip()]

    return {
        "standard_answer": result.get("standard_answer", ""),
        "solution_steps": solution_steps,
        "knowledge_points": result.get("knowledge_points", []),
        "common_mistakes": result.get("common_mistakes", []),
    }


def apply_generated_answer(question: dict, generated: dict) -> dict:
    """将文本答案写入 question dict。"""
    question["standard_answer"] = generated["standard_answer"]
    question["solution_steps"] = generated["solution_steps"]
    if generated.get("knowledge_points"):
        question["knowledge_points"] = generated["knowledge_points"]
    if generated.get("common_mistakes"):
        question["common_mistakes"] = generated["common_mistakes"]
    return question


# ═══════════════════════════════════════════
#  CanonicalSolutionTrace 生成（trace 模式）
# ═══════════════════════════════════════════

def generate_canonical_trace(solver, question: dict, verbose: bool = False) -> dict | None:
    """
    调用 SolverAgent.solve_trace() 生成 CanonicalSolutionTrace，
    验证后缓存到 question JSON。

    Returns:
        成功返回 {"trace_dict": dict, "verified": bool, "confidence": float, "method_count": int}，
        失败返回 None。
    """
    qtext = question.get("raw_question_text") or question.get("question", "")
    qtype = question.get("question_type", "解答题")
    category = question.get("category", "数学一")
    kps = question.get("knowledge_points") or []
    kp = ", ".join(kps) if kps else "未指定"
    qid = question.get("question_id", "unknown")
    score = float(question.get("score", 10))

    # 1. 生成 trace
    trace = solver.solve_trace(
        question=qtext, math_type=category,
        question_type=qtype, knowledge_point=kp,
        total_score=score,
    )
    if not trace or not trace.methods:
        return None

    # 设置 question_id
    trace.question_id = qid
    for m in trace.methods:
        m.graph.question_id = qid

    # 2. SymPy 验证
    verified = False
    confidence = 0.0
    try:
        from solution_verifier import verify_trace
        vresult = verify_trace(trace)
        trace.verified = vresult.all_verified
        trace.verification_log = vresult.log
        verified = vresult.all_verified
        confidence = vresult.confidence
        if verbose:
            print(f"    验证: {'通过' if verified else '未通过'} (置信度 {confidence:.0%})")
            if vresult.failed_steps:
                print(f"    失败步骤: {vresult.failed_steps[:3]}")
    except Exception as e:
        if verbose:
            print(f"    验证跳过: {e}")

    # 3. 生成评分标准
    try:
        from rubric_builder import build_rubric
        rubric = build_rubric(trace, int(score))
        trace.rubric = [
            {"step_id": r.step_id, "label": r.label,
             "score": r.score, "is_critical": r.is_critical,
             "error_type_hint": r.error_type_hint}
            for r in rubric
        ]
    except Exception:
        pass

    # 4. 同时生成文本答案（兼容旧流程）
    best = trace.best_method()
    if best:
        question["standard_answer"] = best.final_answer or ""
        # 从 graph nodes 构建 solution_steps
        steps = []
        for node in best.graph.nodes:
            if node.type != "final_answer":
                label = node.label or node.type
                out = node.output or ""
                steps.append(f"{label}: {out}" if out else label)
        question["solution_steps"] = steps
        if best.knowledge_points:
            question["knowledge_points"] = best.knowledge_points
        if best.common_mistakes:
            question["common_mistakes"] = best.common_mistakes

    return {
        "trace_dict": trace.to_dict(),
        "verified": verified,
        "confidence": confidence,
        "method_count": len(trace.methods),
    }


# ═══════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════

def cmd_validate(questions: list, fix: bool, verbose: bool):
    """校验所有题目的答案完整性。"""
    stats = {"total": len(questions), "complete": 0, "incomplete": 0, "has_trace": 0, "deleted": 0}
    incomplete_list = []

    for data, path in questions:
        qid = data.get("question_id", os.path.basename(path))
        qtype = data.get("question_type", "")
        result = check_answer_completeness(data)

        if result.get("has_trace"):
            stats["has_trace"] += 1

        if result["complete"]:
            stats["complete"] += 1
            if verbose:
                trace_tag = " [trace]" if result.get("has_trace") else ""
                print(f"  [OK] {qid} ({qtype}): {result['reason']}{trace_tag}")
        else:
            stats["incomplete"] += 1
            incomplete_list.append((qid, qtype, result))
            print(f"  [缺失] {qid} ({qtype}): {result['reason']}")

            if fix and result["action"] == "delete":
                data.pop("standard_answer", None)
                data.pop("solution_steps", None)
                data.pop("canonical_solution", None)
                save_question(path, data)
                stats["deleted"] += 1
                print(f"    → 已清除不完整答案")

    print(f"\n{'=' * 50}")
    print(f"校验完成:")
    print(f"  总题数:       {stats['total']}")
    print(f"  完整:         {stats['complete']}")
    print(f"  有 Trace:     {stats['has_trace']}")
    print(f"  不完整:       {stats['incomplete']}")
    if fix:
        print(f"  已清除:       {stats['deleted']}")

    if incomplete_list and not fix:
        print(f"\n不完整的题目 ({len(incomplete_list)} 道):")
        for qid, qtype, r in incomplete_list[:20]:
            print(f"  {qid} ({qtype}): {r['reason']}")
        if len(incomplete_list) > 20:
            print(f"  ... 还有 {len(incomplete_list) - 20} 道")
        print(f"\n提示: 使用 --generate 生成文本答案，--generate --trace 生成结构化轨迹（推荐）")


def cmd_generate(questions: list, force: bool, verbose: bool, trace: bool):
    """为缺失（或全部）题目生成标准解答。"""
    client = build_llm_client()
    if not client:
        print("[错误] 未配置 LLM API Key，请在 .env 中设置 LLM_API_KEY")
        sys.exit(1)

    solver = get_solver(client)
    model_name = SOLVER_MODEL or LLM_MODEL or "deepseek-chat"
    mode = "CanonicalSolutionTrace" if trace else "文本答案"
    print(f"生成模式: {mode}\n")

    stats = {
        "total": len(questions), "skipped": 0,
        "generated": 0, "trace_verified": 0, "trace_unverified": 0, "failed": 0,
    }
    failed_list = []

    for i, (data, path) in enumerate(questions):
        qid = data.get("question_id", os.path.basename(path))
        qtype = data.get("question_type", "")

        # 非强制模式下，跳过已有完整答案的题目
        if not force:
            check = check_answer_completeness(data)
            if check["complete"]:
                # trace 模式下，有 text 但没 trace 的也需要补生成
                if trace and not check.get("has_trace") and qtype in ("解答题", "证明题"):
                    pass  # 继续生成 trace
                else:
                    stats["skipped"] += 1
                    if verbose:
                        print(f"  [跳过] {qid}: {check['reason']}")
                    continue

        print(f"  [{i + 1}/{len(questions)}] {qid} ({qtype}) ...", end=" ", flush=True)

        if trace and qtype in ("解答题", "证明题"):
            # ── CanonicalSolutionTrace 模式 ──
            result = generate_canonical_trace(solver, data, verbose=verbose)
            if result:
                data["canonical_solution"] = result["trace_dict"]
                save_question(path, data)
                v_tag = "✓验证" if result["verified"] else "△未验证"
                print(f"{v_tag} ({result['method_count']}方法, 置信度 {result['confidence']:.0%})")
                stats["generated"] += 1
                if result["verified"]:
                    stats["trace_verified"] += 1
                else:
                    stats["trace_unverified"] += 1
            else:
                # trace 失败，回退到 text 模式
                print("trace失败，回退text...", end=" ", flush=True)
                generated = generate_standard_answer(solver, data)
                if generated and generated.get("standard_answer"):
                    apply_generated_answer(data, generated)
                    save_question(path, data)
                    step_count = len(generated.get("solution_steps", []))
                    print(f"✓ text ({step_count} 步)")
                    stats["generated"] += 1
                else:
                    print("✗ 全部失败")
                    stats["failed"] += 1
                    failed_list.append(qid)
        else:
            # ── 文本答案模式 ──
            generated = generate_standard_answer(solver, data)
            if generated and generated.get("standard_answer"):
                apply_generated_answer(data, generated)
                save_question(path, data)
                step_count = len(generated.get("solution_steps", []))
                print(f"✓ ({step_count} 步)")
                stats["generated"] += 1
            else:
                print("✗ 生成失败")
                stats["failed"] += 1
                failed_list.append(qid)

        time.sleep(1.0)

    print(f"\n{'=' * 50}")
    print(f"生成完成 ({mode}):")
    print(f"  总题数:     {stats['total']}")
    print(f"  已跳过:     {stats['skipped']}")
    print(f"  已生成:     {stats['generated']}")
    if trace:
        print(f"  Trace验证:  {stats['trace_verified']} 通过 / {stats['trace_unverified']} 未通过")
    print(f"  失败:       {stats['failed']}")

    if failed_list:
        print(f"\n生成失败的题目:")
        for qid in failed_list[:20]:
            print(f"  {qid}")
        if len(failed_list) > 20:
            print(f"  ... 还有 {len(failed_list) - 20} 道")


# ═══════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════

def cmd_review():
    """人工审核待审批的候选方法。"""
    from trace_evolver import list_pending, approve_candidate, reject_candidate, get_pending_stats

    stats = get_pending_stats()
    print(f"待审核队列: {stats['total_pending']} 个候选方法\n")

    candidates = list_pending()
    if not candidates:
        print("暂无待审核方法。")
        return

    for i, c in enumerate(candidates):
        qid = c.get("question_id", "?")
        fp = c.get("fingerprint", "?")
        score = c.get("score", 0)
        total = c.get("total_score", 10)
        method = c.get("method", {})
        method_name = method.get("method_name", "?")

        print(f"[{i+1}/{len(candidates)}] {c.get('candidate_id', '?')[:60]}")
        print(f"  题目: {qid} | 方法: {method_name} | 分数: {score}/{total}")
        print(f"  指纹: {fp[:60]}")
        steps = method.get("graph", {}).get("nodes", [])
        for step in steps:
            label = step.get("label", "")
            op = step.get("operation", "")
            out = step.get("output", "")[:60]
            if label or out:
                print(f"    - ({op}) {label}: {out}")
        print()
        action = input("  [A]pprove / [R]eject / [S]kip? ").strip().lower()
        if action == "a":
            if approve_candidate(c.get("candidate_id", "")):
                print("  ✓ 已批准并加入 canonical_solutions")
            else:
                print("  ✗ 批准失败")
        elif action == "r":
            reason = input("  拒绝原因: ").strip()
            reject_candidate(c.get("candidate_id", ""), reason)
            print(f"  ✓ 已拒绝: {reason or '无'}")
        else:
            print("  跳过")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="考研数学 — 批量标准答案生成与校验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python validate_answers.py                        # 查看答案缺失情况
  python validate_answers.py --generate             # 生成文本标准答案
  python validate_answers.py --generate --trace     # 生成 CanonicalSolutionTrace（推荐）
  python validate_answers.py --generate --trace --force  # 强制重新生成所有 trace
  python validate_answers.py --validate --fix        # 校验并清除不完整答案
  python validate_answers.py --review               # 人工审核待审批方法
        """,
    )
    parser.add_argument("--generate", action="store_true",
                        help="为缺失答案的题目调用 LLM 生成解答")
    parser.add_argument("--trace", action="store_true",
                        help="配合 --generate：生成 CanonicalSolutionTrace")
    parser.add_argument("--validate", action="store_true",
                        help="校验已有答案的完整性（默认行为）")
    parser.add_argument("--review", action="store_true",
                        help="人工审核待审批的候选方法（pending_methods/）")
    parser.add_argument("--force", action="store_true",
                        help="强制重新生成所有题目的解答")
    parser.add_argument("--fix", action="store_true",
                        help="配合 --validate：清除不完整的答案")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="详细输出")
    args = parser.parse_args()

    if args.review:
        cmd_review()
        return

    data_dir = os.path.join(_ROOT, "storage", "questions", "data")
    if not os.path.isdir(data_dir):
        print(f"题目目录不存在: {data_dir}")
        sys.exit(1)

    print(f"加载题目: {data_dir}")
    questions = load_all_questions(data_dir)
    print(f"共加载 {len(questions)} 道题\n")

    if args.generate:
        cmd_generate(questions, force=args.force, verbose=args.verbose, trace=args.trace)
    else:
        cmd_validate(questions, fix=args.fix, verbose=args.verbose)


if __name__ == "__main__":
    main()
