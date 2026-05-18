"""
Method Classifier — 快速识别学生解题方法类别

核心思想:
  - 不暴力遍历所有 canonical trace
  - 先通过 Operation 序列指纹快速分类方法
  - 再只匹配同家族的 canonical trace
  - 复杂度从 O(n*m) 降到 O(n)

方法家族定义:
  substitution       — 换元法
  trig_substitution  — 三角代换
  parts              — 分部积分
  eigenvalue         — 特征值法
  determinant        — 行列式展开
  row_reduce         — 行变换
  series_expand      — 级数展开
  factorization      — 因式分解
  differentiation    — 求导分析
  unknown            — 未识别
"""

import re
from operations import Op, infer_op_from_text, normalize_op


# ═══════════════════════════════════════════
#  方法家族定义
# ═══════════════════════════════════════════

METHOD_FAMILIES = {
    "substitution": {
        "name": "换元法",
        "core_ops": {Op.SUBSTITUTE},
        "support_ops": {Op.SIMPLIFY, Op.INTEGRATE, Op.DIFFERENTIATE, Op.EXPAND, Op.COMPUTE},
    },
    "trig_substitution": {
        "name": "三角代换",
        "core_ops": {Op.SUBSTITUTE},
        "support_ops": {Op.INTEGRATE, Op.SIMPLIFY, Op.FACTOR, Op.COMPUTE},
        "keywords": [r'sin|cos|tan|\\\\sin|\\\\cos|\\\\tan', r'三角'],
    },
    "parts": {
        "name": "分部积分",
        "core_ops": {Op.INTEGRATE},
        "support_ops": {Op.DIFFERENTIATE, Op.SIMPLIFY, Op.EXPAND, Op.COMPUTE},
        "keywords": [r'u\s*=|dv\s*=|分部', r'∫u|\\\\int.*u'],
    },
    "eigenvalue": {
        "name": "特征值法",
        "core_ops": {Op.EIGEN_SOLVE, Op.DETERMINANT},
        "support_ops": {Op.MATRIX_OP, Op.SOLVE_EQUATION, Op.SIMPLIFY},
        "keywords": [r'\\\\lambda|特征值|特征向量|特征方程'],
    },
    "determinant": {
        "name": "行列式展开",
        "core_ops": {Op.DETERMINANT, Op.MATRIX_OP},
        "support_ops": {Op.SIMPLIFY, Op.EXPAND, Op.FACTOR, Op.COMPUTE},
        "keywords": [r'det|行列式|展开'],
    },
    "row_reduce": {
        "name": "行变换/高斯消元",
        "core_ops": {Op.ROW_REDUCE, Op.MATRIX_OP},
        "support_ops": {Op.SIMPLIFY, Op.SOLVE_SYSTEM, Op.COMPUTE},
        "keywords": [r'行变换|初等|高斯|消元|行阶梯'],
    },
    "series_expand": {
        "name": "级数展开",
        "core_ops": {Op.EXPAND_SERIES},
        "support_ops": {Op.SIMPLIFY, Op.EXPAND, Op.CONVERGENCE_TEST, Op.COMPUTE},
        "keywords": [r'泰勒|麦克劳林|幂级数|展开'],
    },
    "factorization": {
        "name": "因式分解",
        "core_ops": {Op.FACTOR},
        "support_ops": {Op.SIMPLIFY, Op.EXPAND, Op.COLLECT, Op.COMPUTE},
    },
    "differentiation": {
        "name": "求导分析",
        "core_ops": {Op.DIFFERENTIATE, Op.PARTIAL_DIFF},
        "support_ops": {Op.SIMPLIFY, Op.SOLVE_EQUATION, Op.FACTOR, Op.SUBSTITUTE, Op.COMPUTE},
    },
    "limit": {
        "name": "极限计算",
        "core_ops": {Op.COMPUTE_LIMIT},
        "support_ops": {Op.SIMPLIFY, Op.SUBSTITUTE, Op.EXPAND, Op.EXPAND_SERIES, Op.COMPUTE},
    },
    "probability": {
        "name": "概率/统计",
        "core_ops": {Op.PROBABILITY_CALC, Op.EXPECTATION, Op.MLE_DERIVE, Op.MOMENT_ESTIMATE},
        "support_ops": {Op.INTEGRATE, Op.DIFFERENTIATE, Op.SIMPLIFY, Op.COMPUTE},
    },
    "theorem_apply": {
        "name": "定理应用",
        "core_ops": {Op.APPLY_THEOREM, Op.CLASSIFY},
        "support_ops": {Op.SIMPLIFY, Op.COMPUTE, Op.SUBSTITUTE},
    },
}


def classify_student_method(
    student_trace: dict,
    canonical_trace=None,
) -> dict:
    """
    根据学生解题轨迹快速分类方法。

    Args:
        student_trace: extract_student_trace() 的输出
        canonical_trace: CanonicalSolutionTrace 实例（可选，用于匹配已有方法）

    Returns:
        {
            "family": str,
            "family_name": str,
            "confidence": float,          # 0-1
            "matched_canonical_index": int | None,  # 匹配到的 canonical method 索引
            "match_confidence": float,    # 与 canonical 的匹配置信度
            "recommendation": str,        # "targeted_match" | "broad_match" | "semantic_fallback"
            "canonical_count": int,
        }
    """
    steps = student_trace.get("steps", [])
    if not steps:
        return _unknown_result("无步骤")

    # 1. 从步骤提取操作序列
    operations = [normalize_op(s.get("operation", "compute")) for s in steps]

    # 2. 按家族打分
    family_scores = {}
    for fam_id, fam_info in METHOD_FAMILIES.items():
        score = _score_family(operations, steps, fam_info)
        family_scores[fam_id] = score

    # 3. 选最高分家族
    best_family = max(family_scores, key=family_scores.get)
    best_score = family_scores[best_family]
    # 归一化到 0-1
    max_possible = 3.0  # core_op + keywords + support_ops
    confidence = min(round(best_score / max_possible, 2), 1.0)
    family_name = METHOD_FAMILIES[best_family]["name"]

    # 4. 如果提供了 canonical_trace，找最匹配的方法
    matched_idx = None
    match_conf = 0.0
    recommendation = "broad_match"
    canon_count = 0

    if canonical_trace and canonical_trace.methods:
        canon_count = canonical_trace.method_count()
        best_match_val = 0.0
        for idx, method in enumerate(canonical_trace.methods):
            # 用 fingerprint 距离比较
            canon_ops = method.fingerprint.split(":")
            student_ops = [o.value for o in operations]
            similarity = _sequence_similarity(student_ops, canon_ops)
            if similarity > best_match_val:
                best_match_val = similarity
                matched_idx = idx

        match_conf = min(round(best_match_val, 2), 1.0)

        # 推荐策略
        if match_conf >= 0.7:
            recommendation = "targeted_match"   # 高匹配，精准匹对
        elif match_conf >= 0.3:
            recommendation = "broad_match"      # 中等匹配，窄范围搜索
        else:
            recommendation = "semantic_fallback" # 低匹配，LLM语义判断

    return {
        "family": best_family,
        "family_name": family_name,
        "confidence": confidence,
        "matched_canonical_index": matched_idx,
        "match_confidence": match_conf,
        "recommendation": recommendation,
        "canonical_count": canon_count,
    }


def filter_relevant_methods(
    student_trace: dict,
    canonical_trace,
) -> list:
    """
    根据分类结果，只返回相关的 canonical methods（优先级排序）。
    """
    if not canonical_trace or not canonical_trace.methods:
        return []

    classification = classify_student_method(student_trace, canonical_trace)
    methods = list(canonical_trace.methods)
    recommendation = classification["recommendation"]
    matched_idx = classification.get("matched_canonical_index")

    if recommendation == "targeted_match" and matched_idx is not None:
        # 精准匹配：把最可能的方法放最前面，其他跟随
        best = methods[matched_idx]
        others = [m for i, m in enumerate(methods) if i != matched_idx]
        return [best] + others

    if recommendation == "broad_match":
        # 窄范围：只返回 family 兼容的
        family = METHOD_FAMILIES.get(classification["family"])
        if family:
            core_ops = family["core_ops"]
            def relevance(m):
                canon_ops = {normalize_op(n.operation or n.type) for n in m.graph.nodes}
                return len(core_ops & canon_ops)
            methods.sort(key=relevance, reverse=True)
        return methods

    # semantic_fallback: 返回所有方法，按 usage_count 排
    return sorted(methods, key=lambda m: m.usage_count, reverse=True)


# ═══════════════════════════════════════════
#  评分逻辑
# ═══════════════════════════════════════════

def _score_family(operations: list, steps: list[dict], fam_info: dict) -> float:
    """计算操作序列对某个方法家族的匹配分。"""
    score = 0.0
    core_ops = fam_info.get("core_ops", set())
    support_ops = fam_info.get("support_ops", set())

    # 核心操作命中
    op_set = set(operations)
    core_hits = len(core_ops & op_set)
    if core_hits > 0:
        score += 2.0 * min(core_hits / len(core_ops), 1.0)

    # 辅助操作命中
    support_hits = len(support_ops & op_set)
    if support_hits > 0:
        score += 0.5 * min(support_hits / len(support_ops), 1.0)

    # 关键词命中
    keywords = fam_info.get("keywords", [])
    if keywords:
        all_text = " ".join(s.get("label", "") + str(s.get("output_state", "")) for s in steps)
        kw_hits = sum(1 for kw in keywords if re.search(kw, all_text))
        score += 1.0 * min(kw_hits / max(len(keywords), 1), 1.0)

    return score


def _sequence_similarity(seq1: list, seq2: list) -> float:
    """计算两个操作序列的相似度（基于最长公共子序列）。"""
    m, n = len(seq1), len(seq2)
    if m == 0 or n == 0:
        return 0.0
    # LCS
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]
    # 双向归一化
    return lcs / max(m, n)


def _unknown_result(reason: str) -> dict:
    return {
        "family": "unknown",
        "family_name": "未知方法",
        "confidence": 0.0,
        "matched_canonical_index": None,
        "match_confidence": 0.0,
        "recommendation": "semantic_fallback",
        "canonical_count": 0,
    }

