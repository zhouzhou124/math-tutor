"""
Question Locker — 题目锁定

给定 question_id 或 question dict，解析完整的解题上下文：
    - 题目元数据（知识点、难度、分值）
    - 标准答案
    - CanonicalSolutionTrace（规范解题轨迹，含验证）
    - SolutionGraph（从规范轨迹 / 缓存步骤 / auto_generate_from_db / 模板生成）

锁定后的数据在整个学习会话中复用，避免重复生成。
"""

import json
import os
import logging
from datetime import datetime, timezone

_log = logging.getLogger(__name__)

from database.question_db import QuestionDB


def lock_question(
    question_id_or_dict: str | dict,
    question_db: QuestionDB,
    client=None,
    model: str = "deepseek-chat",
) -> dict:
    """
    锁定题目，返回完整的学习会话上下文。

    Args:
        question_id_or_dict: question_id 字符串 或 完整的 question dict
        question_db: QuestionDB 实例
        client: OpenAI-compatible LLM client（用于生成规范解题轨迹）
        model: LLM 模型名

    Returns:
        {
            "question": dict,
            "solution_graph": SolutionGraph,
            "graph_source": str,
            "standard_answer": str,
            "total_score": float,
            "knowledge_points": [str],
            "question_type": str,
            "question_id": str,
            "locked_at": str,
            "canonical_trace": CanonicalSolutionTrace | None,
        }
    """
    # 解析输入
    if isinstance(question_id_or_dict, str):
        question = question_db.get(question_id_or_dict)
        if question is None:
            raise ValueError(f"题目不存在: {question_id_or_dict}")
    else:
        question = question_id_or_dict

    question_type = question.get("question_type", "解答题")
    standard_answer = question.get("standard_answer", "")
    total_score = question.get("score", 10)
    knowledge_points = question.get("knowledge_points", [])
    question_id = question.get("question_id", "unknown")

    # 尝试加载缓存的规范解题轨迹
    canonical_trace = _load_canonical_solution(question)

    # 生成 SolutionGraph
    graph, graph_source = _resolve_solution_graph(
        question, canonical_trace, client, model,
    )

    result = {
        "question": question,
        "solution_graph": graph,
        "graph_source": graph_source,
        "standard_answer": standard_answer,
        "total_score": float(total_score),
        "knowledge_points": knowledge_points,
        "question_type": question_type,
        "question_id": question_id,
        "locked_at": datetime.now(timezone.utc).isoformat(),
        "canonical_trace": canonical_trace,
    }
    return result


def _resolve_solution_graph(
    question: dict,
    canonical_trace=None,
    client=None,
    model: str = "deepseek-chat",
) -> tuple:
    """
    为题目生成 SolutionGraph。

    优先级:
    0. 缓存的 CanonicalSolutionTrace → 直接用其 best_method 的 graph
    1. 选择题 → make_choice_graph
    2. 填空题 → make_fill_blank_graph
    3. 解答题/证明题 → 生成 CanonicalSolutionTrace → verify → cache → 用其 graph
    4. graph_compiler.auto_generate_from_db
    5. solution_generator 模板兜底
    """
    from solution_graph import SolutionGraph, make_choice_graph, make_fill_blank_graph

    qtype = question.get("question_type", "")
    qid = question.get("question_id", "unknown")
    score = question.get("score", 10)
    answer = question.get("standard_answer", "")

    # 选择题：单节点图
    if qtype == "选择题":
        correct = question.get("correct_option", "")
        graph = make_choice_graph(qid, correct, score)
        return graph, "single_node_choice"

    # 填空题：单节点图
    if qtype == "填空题":
        graph = make_fill_blank_graph(qid, answer, score)
        return graph, "single_node_fill"

    # 解答题/证明题 — 优先用缓存的规范轨迹
    if canonical_trace and canonical_trace.methods:
        best = canonical_trace.best_method()
        if best and best.graph and len(best.graph.nodes) >= 1:
            # 更新 question_id
            best.graph.question_id = qid
            return best.graph, "canonical_cached"

    # 尝试生成规范解题轨迹
    return _resolve_solution_graph_for_solution(question, client, model)


def _resolve_solution_graph_for_solution(
    question: dict,
    client=None,
    model: str = "deepseek-chat",
) -> tuple:
    """
    解答题/证明题的 SolutionGraph 生成。
    优先生成 CanonicalSolutionTrace，兜底用 graph_compiler / 模板。
    """
    from solution_graph import SolutionGraph

    qid = question.get("question_id", "unknown")
    score = question.get("score", 10)

    # 校验现有答案，无效则清除
    if client and question.get("standard_answer"):
        vresult = validate_cached_answer(question, client, model)
        if not vresult["valid"]:
            cleanup_invalid_answer(qid)
            question["standard_answer"] = ""
        elif vresult["canonical_trace"]:
            # 校验通过且有 trace，直接使用
            trace = vresult["canonical_trace"]
            _cache_canonical_solution(qid, trace)
            best = trace.best_method()
            if best and best.graph and len(best.graph.nodes) >= 1:
                best.graph.question_id = qid
                return best.graph, "canonical_validated"

    # 步骤1：尝试生成规范解题轨迹
    if client:
        try:
            from agents.solver_agent import SolverAgent
            solver = SolverAgent(client, model)
            trace = solver.solve_trace(
                question=question.get("question", ""),
                math_type=question.get("category", "数学一"),
                question_type=question.get("question_type", "解答题"),
                knowledge_point=", ".join(question.get("knowledge_points", [])),
                total_score=float(score),
                n_methods=3,  # 请求3种不同解法
            )
            if trace and trace.methods:
                # 设置 question_id
                trace.question_id = qid
                for m in trace.methods:
                    m.graph.question_id = qid

                # 验证
                try:
                    from solution_verifier import verify_trace
                    vresult = verify_trace(trace)
                    trace.verified = vresult.all_verified
                    trace.verification_log = vresult.log
                except Exception as e:
                    _log.warning("trace 验证失败 (%s): %s", qid, e)

                # 生成评分标准
                try:
                    from rubric_builder import build_rubric
                    rubric = build_rubric(trace, int(score))
                    trace.rubric = [
                        {"step_id": r.step_id, "label": r.label,
                         "score": r.score, "is_critical": r.is_critical,
                         "error_type_hint": r.error_type_hint}
                        for r in rubric
                    ]
                except Exception as e:
                    _log.warning("rubric 生成失败 (%s): %s", qid, e)

                # 缓存到题目文件
                _cache_canonical_solution(qid, trace)

                best = trace.best_method()
                if best and best.graph and len(best.graph.nodes) >= 1:
                    return best.graph, "canonical_generated"
        except Exception as e:
            _log.error("trace 生成失败 (%s): %s", qid, e)

    # 步骤2：尝试 graph_compiler
    try:
        from graph_compiler import auto_generate_from_db
        graph = auto_generate_from_db(question)
        if graph and len(graph.nodes) > 1:
            return graph, "generated"
    except Exception as e:
        _log.debug("graph_compiler 失败 (%s): %s", qid, e)

    # 步骤3：模板兜底
    try:
        from solution_generator import build_solution_graph
        graph = build_solution_graph(
            question.get("question", ""),
            question.get("standard_answer", ""),
            question.get("question_type", "解答题"),
            qid,
        )
        if graph and len(graph.nodes) >= 1:
            return graph, "template"
    except Exception as e:
        _log.debug("solution_generator 失败 (%s): %s", qid, e)

    # 步骤4：绝对兜底 — 单节点空图
    from solution_graph import make_solution_graph, GraphNode
    node = GraphNode(
        id="n1",
        type="compute",
        label="解题",
        output=question.get("standard_answer", ""),
    )
    graph = make_solution_graph(qid, question.get("standard_answer", ""), [node], [], score)
    return graph, "single_node_fallback"


# ═══════════════════════════════════════════════
# Canonical Solution 缓存
# ═══════════════════════════════════════════════

def _get_question_data_path(question_id: str) -> str:
    """获取题目 JSON 文件路径"""
    storage_dir = os.path.join(os.path.dirname(__file__), "storage", "questions", "data")
    return os.path.join(storage_dir, f"{question_id}.json")


def _load_canonical_solution(question: dict):
    """从题目 JSON 中加载缓存的 CanonicalSolutionTrace（兼容新旧格式）。"""
    from solution_graph import CanonicalSolutionTrace
    return CanonicalSolutionTrace.from_question_json(question)


def _cache_canonical_solution(question_id: str, trace) -> bool:
    """将规范解题轨迹缓存到题目 JSON 文件（使用 canonical_solutions 数组）。"""
    path = _get_question_data_path(question_id)
    if not os.path.exists(path):
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        trace.save_to_question_json(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        _log.error("trace 缓存失败 (%s): %s", question_id, e)
        return False


# ═══════════════════════════════════════════════
# 缓存答案校验与清理
# ═══════════════════════════════════════════════

def validate_cached_answer(question: dict, client=None, model: str = "deepseek-chat") -> dict:
    """
    校验题目的缓存答案是否正确。

    优先检查 canonical_solution（AI 生成，有验证记录）；
    若无，则校验 standard_answer（可能是手动录入，需要验证）。

    Returns:
        {"valid": bool, "reason": str, "canonical_trace": CanonicalSolutionTrace | None}
    """
    qtype = question.get("question_type", "")
    qid = question.get("question_id", "")
    std_answer = question.get("standard_answer", "")

    # ── 有 canonical_solution 且已验证 ──
    cached_cs = question.get("canonical_solution")
    if cached_cs:
        trace = _load_canonical_solution(question)
        if trace and trace.verified:
            return {"valid": True, "reason": "canonical_solution 已验证", "canonical_trace": trace}
        # 有但未验证，尝试验证
        if trace and trace.methods:
            try:
                from solution_verifier import verify_trace
                vresult = verify_trace(trace)
                trace.verified = vresult.all_verified
                trace.verification_log = vresult.log
                if vresult.all_verified:
                    _cache_canonical_solution(qid, trace)
                    return {"valid": True, "reason": "canonical_solution 验证通过", "canonical_trace": trace}
                else:
                    return {"valid": False, "reason": f"canonical_solution 验证失败: {vresult.failed_steps[:3]}", "canonical_trace": trace}
            except Exception as e:
                _log.warning("canonical_solution 验证异常 (%s): %s", qid, e)
        return {"valid": False, "reason": "canonical_solution 格式异常", "canonical_trace": None}

    # ── 无 canonical_solution，校验 standard_answer ──
    if not std_answer:
        return {"valid": False, "reason": "无任何答案", "canonical_trace": None}

    # 校验是否有详细解题过程
    solution_steps = question.get("solution_steps", [])
    has_steps = bool(solution_steps and len(solution_steps) >= 2)
    if not has_steps:
        return {"valid": False, "reason": "标准答案缺少详细解题过程（solution_steps）", "canonical_trace": None}

    # 选择题：对比 correct_option（去除尾部标点），已确认有解题过程
    if qtype == "选择题":
        correct = question.get("correct_option", "")
        std_clean = std_answer.strip().rstrip(".。、，,").upper()
        if correct and correct.strip().upper() == std_clean:
            return {"valid": True, "reason": "选择题答案匹配，有解题过程", "canonical_trace": None}
        return {"valid": False, "reason": f"选择题答案不匹配: 标准={correct}, 缓存={std_answer}", "canonical_trace": None}

    # 填空题：已确认有解题过程
    if qtype == "填空题":
        return {"valid": True, "reason": "填空题有标准答案和解题过程", "canonical_trace": None}

    # 解答题/证明题：生成 trace 并校验 final_answer
    if client:
        try:
            from agents.solver_agent import SolverAgent
            solver = SolverAgent(client, model)
            trace = solver.solve_trace(
                question=question.get("question", ""),
                math_type=question.get("category", "数学一"),
                question_type=qtype,
                knowledge_point=", ".join(question.get("knowledge_points", [])),
                total_score=float(question.get("score", 10)),
            )
            if trace and trace.methods:
                best = trace.best_method()
                if best and best.final_answer:
                    from solution_verifier import verify_step_transition
                    vresult = verify_step_transition(best.final_answer, std_answer)
                    if vresult["verified"]:
                        # 生成的 trace 与 standard_answer 一致，缓存 trace
                        trace.question_id = qid
                        for m in trace.methods:
                            m.graph.question_id = qid
                        _cache_canonical_solution(qid, trace)
                        return {"valid": True, "reason": "解答题答案与 AI 解法一致", "canonical_trace": trace}
                    else:
                        return {"valid": False, "reason": f"解答题答案与 AI 解法不一致: {vresult.get('error', '')}", "canonical_trace": trace}
        except Exception as e:
            _log.error("trace 校验失败 (%s): %s", qid, e)

    # 无法校验（无 LLM），标记为待验证
    return {"valid": True, "reason": "无法校验（无 LLM），暂时保留", "canonical_trace": None}


def cleanup_invalid_answer(question_id: str) -> bool:
    """从题目 JSON 中移除错误的 standard_answer，防止污染答案库。"""
    path = _get_question_data_path(question_id)
    if not os.path.exists(path):
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "standard_answer" in data:
            del data["standard_answer"]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
