"""
Trace Evolver — 人工审核队列

核心原则: 绝不自动将学生方法加入 canonical_solutions。
         所有候选方法必须经过人工审核才能 promote。

流程:
  学生高分 → 候选方法 → pending_methods/ → 人工审核 → approve → canonical
"""

import json
import os
from datetime import datetime, timezone

_QDATA_ROOT = os.path.join(os.path.dirname(__file__), "storage", "questions", "data")
_PENDING_ROOT = os.path.join(os.path.dirname(__file__), "storage", "pending_methods")


def submit_candidate(
    question_id: str,
    student_trace: dict,
    score: float,
    total_score: float,
    existing_trace=None,
    grading_summary: dict = None,
    min_score_ratio: float = 0.85,
    min_fingerprint_distance: int = 2,
) -> dict | None:
    """
    将高分但未匹配的学生方法提交到待审核队列。

    不再自动加入 canonical_solutions。所有新方法必须人工审核。

    Returns:
        成功 → {"submitted": True, "candidate_id": str}
        跳过 → None（分数不足或已有类似方法）
    """
    from solution_graph import SolutionMethod, SolutionGraph, GraphNode, GraphEdge

    # 1. 分数检查
    if score < total_score * min_score_ratio:
        return None

    # 2. 学生步骤检查
    steps = student_trace.get("steps", [])
    if len(steps) < 2:
        return None

    # 3. 构建 fingerprint
    student_fp = _build_fingerprint(steps)

    # 4. 与已有方法比对（去重）
    if existing_trace and existing_trace.methods:
        for m in existing_trace.methods:
            dist = _fingerprint_distance(student_fp, m.fingerprint)
            if dist < min_fingerprint_distance:
                return None  # 太接近已有方法

    # 5. 构建候选 SolutionMethod（不加入 canonical）
    nodes = []
    edges = []
    prev_id = None
    for step in steps:
        node = GraphNode(
            id=step.get("id", f"s{len(nodes)+1}"),
            type=step.get("operation", "compute"),
            label=step.get("label", "")[:80],
            output=step.get("output_state", ""),
            input_state=step.get("input_state", ""),
            operation=step.get("operation", "compute"),
            input_refs=[prev_id] if prev_id else [],
            weight=1.0,
        )
        nodes.append(node)
        if prev_id:
            edges.append(GraphEdge(source=prev_id, target=node.id))
        prev_id = node.id

    graph = SolutionGraph(
        question_id=question_id,
        final_answer=student_trace.get("final_answer", ""),
        nodes=nodes, edges=edges,
        total_score=float(total_score),
        grading_mode="step",
    )

    method = SolutionMethod(
        method_name=student_trace.get("method_name", "学生解法"),
        graph=graph,
        final_answer=student_trace.get("final_answer", ""),
        source="student",
        usage_count=0,
    )

    # 6. 保存到 pending_methods/
    candidate_id = _save_pending(
        question_id, method, score, total_score,
        grading_summary or {},
        student_fp,
    )

    return {"submitted": True, "candidate_id": candidate_id}


def list_pending() -> list[dict]:
    """列出所有待审核的候选方法。"""
    os.makedirs(_PENDING_ROOT, exist_ok=True)
    candidates = []
    for fname in sorted(os.listdir(_PENDING_ROOT)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(_PENDING_ROOT, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            candidates.append(data)
        except Exception:
            pass
    return candidates


def approve_candidate(candidate_id: str) -> bool:
    """审核通过：将候选方法提升到 canonical_solutions。"""
    pending_path = os.path.join(_PENDING_ROOT, f"{candidate_id}.json")
    if not os.path.exists(pending_path):
        return False

    try:
        with open(pending_path, "r", encoding="utf-8") as f:
            candidate = json.load(f)
    except Exception:
        return False

    question_id = candidate.get("question_id", "")
    method_dict = candidate.get("method")

    # 加载或创建 CanonicalSolutionTrace
    from solution_graph import CanonicalSolutionTrace, SolutionMethod
    qpath = os.path.join(_QDATA_ROOT, f"{question_id}.json")
    if os.path.exists(qpath):
        with open(qpath, "r", encoding="utf-8") as f:
            qdata = json.load(f)
        trace = CanonicalSolutionTrace.from_question_json(qdata)
    else:
        return False

    if not trace:
        trace = CanonicalSolutionTrace(question_id=question_id, methods=[])
    if not trace.methods:
        from solution_graph import SolutionMethod as SM
        trace = CanonicalSolutionTrace(question_id=question_id, methods=[])

    # 添加方法
    new_method = SolutionMethod.from_dict(method_dict)
    new_method.source = "student"
    new_method.usage_count = 0
    trace.add_method(new_method, source="student")

    # 保存到 question JSON
    trace.save_to_question_json(qdata)
    with open(qpath, "w", encoding="utf-8") as f:
        json.dump(qdata, f, ensure_ascii=False, indent=2)

    # 移除 pending 文件
    os.rename(pending_path, pending_path + ".approved")
    return True


def reject_candidate(candidate_id: str, reason: str = "") -> bool:
    """审核拒绝：存档并移除。"""
    pending_path = os.path.join(_PENDING_ROOT, f"{candidate_id}.json")
    if not os.path.exists(pending_path):
        return False

    try:
        with open(pending_path, "r", encoding="utf-8") as f:
            candidate = json.load(f)
    except Exception:
        os.remove(pending_path)
        return True

    candidate["rejected_at"] = datetime.now(timezone.utc).isoformat()
    candidate["reject_reason"] = reason

    rejected_path = pending_path + ".rejected"
    with open(rejected_path, "w", encoding="utf-8") as f:
        json.dump(candidate, f, ensure_ascii=False, indent=2)

    os.remove(pending_path)
    return True


def get_pending_stats() -> dict:
    """获取待审核队列统计。"""
    candidates = list_pending()
    by_question = {}
    for c in candidates:
        qid = c.get("question_id", "?")
        by_question[qid] = by_question.get(qid, 0) + 1
    return {
        "total_pending": len(candidates),
        "by_question": by_question,
    }


# ═══════════════════════════════════════════
#  内部函数
# ═══════════════════════════════════════════

def _save_pending(question_id: str, method, score: float,
                  total_score: float, summary: dict,
                  fingerprint: str) -> str:
    """保存候选方法到 pending 目录。"""
    os.makedirs(_PENDING_ROOT, exist_ok=True)

    candidate_id = f"{question_id}_{fingerprint.replace(':', '_')[:40]}_{int(datetime.now(timezone.utc).timestamp())}"
    candidate = {
        "candidate_id": candidate_id,
        "question_id": question_id,
        "method": method.to_dict(),
        "score": score,
        "total_score": total_score,
        "fingerprint": fingerprint,
        "grading_summary": summary,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    path = os.path.join(_PENDING_ROOT, f"{candidate_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(candidate, f, ensure_ascii=False, indent=2)

    return candidate_id


def _build_fingerprint(steps: list[dict]) -> str:
    ops = [s.get("operation", "compute") for s in steps]
    return ":".join(ops)


def _fingerprint_distance(fp1: str, fp2: str) -> int:
    ops1, ops2 = fp1.split(":"), fp2.split(":")
    m, n = len(ops1), len(ops2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = (dp[i - 1][j - 1] if ops1[i - 1] == ops2[j - 1]
                        else 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]))
    return dp[m][n]
