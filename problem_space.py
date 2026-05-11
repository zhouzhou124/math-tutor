"""
Problem Space Engine v3.6 — 三空间分类 + Proof Graph

核心: 数学题不是统一类型, 而是三种空间之一:
  Computation Space — 计算型 (极限/导数/积分)
  Strategy Space   — 策略型 (极限技巧/分类讨论)
  Proof Space      — 证明型 (中值定理/存在性/构造函数)

系统必须区分这三种空间, 用不同的评分模型.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from solution_graph import GraphNode, GraphEdge, SolutionGraph, make_solution_graph


# ═══════════════════════════════════════════════
# Space Types
# ═══════════════════════════════════════════════

class ProblemSpace(str, Enum):
    COMPUTATION = "computation"   # 计算型
    STRATEGY    = "strategy"      # 策略型
    PROOF       = "proof"         # 证明型
    HYBRID      = "hybrid"        # 混合型


# ═══════════════════════════════════════════════
# Theorem Knowledge Graph
# ═══════════════════════════════════════════════

THEOREM_KB = {
    "拉格朗日中值定理": {
        "aliases": ["Lagrange MVT", "中值定理", "拉格朗日", "MVT"],
        "type": "proof_tool",
        "requires": ["continuous", "differentiable"],
        "produces": "existence_of_xi",
        "signature": r"(拉格朗日|中值定理|MVT|Lagrange|f\(b\)-f\(a\)|f'\(ξ\))",
    },
    "罗尔定理": {
        "aliases": ["Rolle", "罗尔"],
        "type": "proof_tool",
        "requires": ["continuous", "differentiable", "f(a)=f(b)"],
        "produces": "existence_of_zero_derivative",
        "signature": r"(罗尔|Rolle|f\(a\)=f\(b\))",
    },
    "零点定理": {
        "aliases": ["介值定理", "Bolzano", "零点存在"],
        "type": "proof_tool",
        "requires": ["continuous", "f(a)f(b)<0"],
        "produces": "existence_of_root",
        "signature": r"(零点|介值|Bolzano|f\(a\)f\(b\)<0|存在.*ξ.*f\(ξ\)=0)",
    },
    "柯西中值定理": {
        "aliases": ["Cauchy MVT", "柯西"],
        "type": "proof_tool",
        "requires": ["continuous", "differentiable"],
        "produces": "ratio_equality",
        "signature": r"(柯西|Cauchy)",
    },
    "积分中值定理": {
        "aliases": ["积分均值定理"],
        "type": "proof_tool",
        "requires": ["continuous", "integrable"],
        "produces": "integral_equality",
        "signature": r"(积分.*中值|∫.*f.*=.*f\(ξ\))",
    },
    "泰勒定理": {
        "aliases": ["Taylor", "泰勒公式", "泰勒展开"],
        "type": "proof_tool",
        "requires": ["n_times_differentiable"],
        "produces": "polynomial_approximation",
        "signature": r"(泰勒|Taylor|f\(x\)=.*\+.*R_n)",
    },
}

PROOF_PATTERNS = [
    r"证明[:：\s]",
    r"求证[:：\s]",
    r"试证[:：\s]",
    r"存在.*ξ.*使得",
    r"存在.*η.*使得",
    r"至少有一个.*ξ",
    r"至少存在一个",
    r"唯一.*ξ",
    r"构造函数",
    r"证明.*收敛",
    r"证明.*存在",
]

STRATEGY_PATTERNS = [
    r"求极限",
    r"lim",
    r"\\lim",
    r"分类讨论",
    r"讨论.*的取值范围",
    r"求.*取值范围",
    r"讨论.*不同实根",
]

COMPUTATION_PATTERNS = [
    r"求导",
    r"求.*积分",
    r"计算",
    r"求.*极值",
    r"解微分方程",
    r"求.*通解",
    r"求.*特解",
]


# ═══════════════════════════════════════════════
# Space Classifier
# ═══════════════════════════════════════════════

def classify_problem_space(question_text: str,
                           question_type: str = "") -> ProblemSpace:
    """
    三空间分类器: 识别题目属于计算/策略/证明.

    Returns: ProblemSpace enum
    """
    # Explicit type from DB
    if question_type == "证明题":
        return ProblemSpace.PROOF

    # Proof patterns
    proof_score = sum(1 for p in PROOF_PATTERNS if re.search(p, question_text))
    if proof_score >= 1:
        return ProblemSpace.PROOF

    # Strategy patterns
    strategy_score = sum(1 for p in STRATEGY_PATTERNS if re.search(p, question_text))
    comp_score = sum(1 for p in COMPUTATION_PATTERNS if re.search(p, question_text))

    if strategy_score > comp_score:
        return ProblemSpace.STRATEGY
    elif strategy_score > 0 and comp_score > 0:
        return ProblemSpace.HYBRID
    else:
        return ProblemSpace.COMPUTATION


def detect_theorems_in_student(student_text: str) -> list[str]:
    """检测学生答案中引用的定理."""
    found = []
    for name, info in THEOREM_KB.items():
        if re.search(info["signature"], student_text):
            found.append(name)
    return found


def detect_theorems_missing(student_text: str,
                            solution_text: str) -> list[str]:
    """检测学生遗漏的定理 (标准解答有, 学生没有)."""
    std_theorems = detect_theorems_in_student(solution_text)
    stu_theorems = detect_theorems_in_student(student_text)
    return [t for t in std_theorems if t not in stu_theorems]


# ═══════════════════════════════════════════════
# Proof Graph Builder
# ═══════════════════════════════════════════════

PROOF_NODE_TYPES = {
    "construct_aux_function":    "构造函数",
    "apply_zero_point_theorem":  "应用零点定理",
    "apply_mvt":                 "应用拉格朗日中值定理",
    "apply_rolle":               "应用罗尔定理",
    "apply_cauchy":              "应用柯西中值定理",
    "apply_integral_mvt":        "应用积分中值定理",
    "multiply_results":          "等式相乘",
    "derive_inequality":         "导出不等式",
    "check_conditions":          "验证定理条件",
    "conclude":                  "得出结论",
}

def build_proof_graph(question_id: str, final_answer: str,
                      theorem_chain: list[str]) -> SolutionGraph:
    """
    从定理链构建 Proof Graph.

    Args:
        theorem_chain: ["construct_aux_function", "apply_zero_point_theorem",
                        "apply_mvt", "multiply_results"]
    """
    nodes = []
    edges = []
    for i, t in enumerate(theorem_chain):
        label = PROOF_NODE_TYPES.get(t, t)
        nid = f"p{i+1}"
        nodes.append(GraphNode(
            id=nid, type=t, label=label,
            output="", input_refs=[],
            weight=0.0,
        ))
        if i > 0:
            edges.append(GraphEdge(f"p{i}", nid))

    return make_solution_graph(question_id, final_answer, nodes, edges,
                               total=12.0)


# ═══════════════════════════════════════════════
# Strategy Activation Detector
# ═══════════════════════════════════════════════

def detect_strategy_activation(student_text: str,
                               question_text: str = "") -> dict:
    """
    检测学生是否激活了正确的解题策略.
    返回: {activated: bool, strategies_found: [], strategies_missing: []}
    """
    found = []
    missing = []

    is_limit = re.search(r'(极限|lim|\\lim)', question_text + student_text)
    is_proof = re.search(r'(证明|求证)', question_text)

    if is_limit:
        strategies = {
            "等价无穷小替换": r'(等价|无穷小|~|o\()',
            "洛必达法则": r'(洛必达|l\'Hôpital|\\frac\{[^}]*0\}.*\\frac)',
            "泰勒展开": r'(泰勒|Taylor|\\sum.*x\^n)',
            "夹逼准则": r'(夹逼|squeeze)',
            "重要极限": r'(重要极限|e.*lim|lim.*e)',
        }
        for name, sig in strategies.items():
            if re.search(sig, student_text):
                found.append(name)
            else:
                missing.append(name)

    if is_proof:
        for theorem_name, info in THEOREM_KB.items():
            if re.search(info["signature"], student_text):
                found.append(theorem_name)

    return {
        "activated": len(found) > 0,
        "strategies_found": found,
        "strategies_missing": missing if not found else [],
        "is_strategy_blind": len(found) == 0 and (is_limit or is_proof),
    }


# ═══════════════════════════════════════════════
# Unified Grading Adapter
# ═══════════════════════════════════════════════

def grade_by_space(question_text: str, student_text: str,
                   question_type: str = "",
                   solution_graph: SolutionGraph = None) -> dict:
    """
    根据问题空间类型选择评分策略.

    Computation → symbolic_compare
    Strategy    → strategy_activation + symbolic_compare
    Proof       → proof_graph_match + theorem_detection
    """
    space = classify_problem_space(question_text, question_type)

    base_result = {
        "space": space.value,
        "score": 0.0,
        "max_score": 10.0,
    }

    if space == ProblemSpace.PROOF:
        theorems_found = detect_theorems_in_student(student_text)
        base_result.update({
            "theorems_detected": theorems_found,
            "theorem_count": len(theorems_found),
            "diagnosis": "proof_graph_analysis",
        })
        if not theorems_found:
            base_result["score"] = 0.0
            base_result["failure_type"] = "proof_schema_absence"
            base_result["root_cause"] = "student lacks proof structure + theorem knowledge"

    elif space == ProblemSpace.STRATEGY:
        activation = detect_strategy_activation(student_text, question_text)
        base_result.update({
            "strategy_activated": activation["activated"],
            "strategies_found": activation["strategies_found"],
        })
        if activation["is_strategy_blind"]:
            base_result["score"] = 0.0
            base_result["failure_type"] = "strategy_non_activation"
            base_result["root_cause"] = "no recognition of solution strategy"

    elif space == ProblemSpace.COMPUTATION:
        if solution_graph:
            from symbolic_executor import execute_against_graph
            exec_result = execute_against_graph(student_text, solution_graph)
            base_result.update({
                "total_score": exec_result["total_score"],
                "max_score": exec_result["max_score"],
                "coverage": exec_result["coverage"],
                "error_level": exec_result["dominant_error_level"],
                "score": exec_result["total_score"],
                "max_score": exec_result["max_score"],
            })

    return base_result
