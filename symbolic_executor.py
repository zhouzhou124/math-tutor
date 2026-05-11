"""
Symbolic Execution Engine v3.2 — 数学表达式可执行验证

核心思想: 不再判断"你写了什么", 而是判断"你算出来的数学结果对不对"

架构:
  Student Step → Parser → SymPy AST → Execution → Compare with Standard
"""
import re
from typing import Optional

try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False


# ═══════════════════════════════════════════════
# Error Level System
# ═══════════════════════════════════════════════

class ErrorLevel:
    LEVEL_0 = 0   # 未执行任何数学计算 (解题路径缺失)
    LEVEL_1 = 1   # 计算错误 (表达式不等价)
    LEVEL_2 = 2   # 推理错误 (步骤顺序/逻辑断裂)
    CORRECT  = -1  # 正确

    LABELS = {
        LEVEL_0: "解题路径缺失: 未执行该步骤",
        LEVEL_1: "计算错误: 表达式不等价",
        LEVEL_2: "推理错误: 步骤逻辑断裂",
        CORRECT: "正确",
    }


# ═══════════════════════════════════════════════
# SymPy Expression Parser
# ═══════════════════════════════════════════════

def parse_expression(latex_or_text: str) -> Optional['sp.Expr']:
    """
    将 LaTeX 或自然文本中的数学表达式解析为 SymPy 表达式。
    支持: x^2, sin(x), ln(y), e^x, (x+1)^2, etc.
    """
    if not _HAS_SYMPY or not latex_or_text or not latex_or_text.strip():
        return None

    s = latex_or_text.strip()
    s = s.replace('$', '').replace('$$', '')
    s = s.replace(r'\sin', 'sin').replace(r'\cos', 'cos').replace(r'\tan', 'tan')
    s = s.replace(r'\ln', 'ln').replace(r'\log', 'log').replace(r'\exp', 'exp')
    s = s.replace(r'\sqrt', 'sqrt').replace(r'\pi', 'pi').replace(r'\infty', 'oo')
    s = s.replace(r'\frac', '').replace(r'\cdot', '*').replace(r'\times', '*')
    s = s.replace(r'\le', '<=').replace(r'\ge', '>=').replace(r'\ne', '!=')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = re.sub(r'\{([^}]*)\}\{([^}]*)\}', r'(\1)/(\2)', s)
    s = s.replace('{', '(').replace('}', ')')
    s = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', s)
    s = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', s)
    s = re.sub(r'\)\(', ')*(', s)
    s = re.sub(r'(\d)\(', r'\1*(', s)
    s = re.sub(r'\)(\d)', r')*\1', s)
    s = re.sub(r'e\^', 'exp', s)

    try:
        expr = sp.sympify(s, evaluate=False)
        return expr
    except (sp.SympifyError, TypeError, SyntaxError):
        return None


# ═══════════════════════════════════════════════
# Symbolic Execution + Comparison
# ═══════════════════════════════════════════════

def symbolic_compare(student_text: str, standard_expr: str) -> dict:
    """
    对学生表达式和标准表达式进行符号等价比较。

    Returns:
        {
            "equivalent": bool,
            "student_parsed": str,
            "standard_parsed": str,
            "difference": str or None,
            "error_level": int,
        }
    """
    # 如果学生什么都没写
    if not student_text or not student_text.strip():
        return {
            "equivalent": False,
            "student_parsed": None,
            "standard_parsed": standard_expr,
            "difference": None,
            "error_level": ErrorLevel.LEVEL_0,
        }

    student_expr = parse_expression(student_text)
    std_expr = parse_expression(standard_expr)

    if student_expr is None:
        return {
            "equivalent": False,
            "student_parsed": student_text,
            "standard_parsed": str(std_expr) if std_expr else standard_expr,
            "difference": "无法解析学生表达式",
            "error_level": ErrorLevel.LEVEL_0,
        }

    if std_expr is None:
        return {
            "equivalent": False,
            "student_parsed": str(student_expr),
            "standard_parsed": standard_expr,
            "difference": "标准表达式无法解析",
            "error_level": ErrorLevel.LEVEL_0,
        }

    # 符号化简比较
    try:
        diff = sp.simplify(student_expr - std_expr)
        equivalent = (diff == 0)
    except Exception:
        equivalent = False
        diff = None

    if equivalent:
        return {
            "equivalent": True,
            "student_parsed": str(student_expr),
            "standard_parsed": str(std_expr),
            "difference": None,
            "error_level": ErrorLevel.CORRECT,
        }
    else:
        # 尝试扩展形式再比较
        try:
            diff2 = sp.simplify(sp.expand(student_expr) - sp.expand(std_expr))
            if diff2 == 0:
                return {
                    "equivalent": True,
                    "student_parsed": str(sp.expand(student_expr)),
                    "standard_parsed": str(sp.expand(std_expr)),
                    "difference": "expand 后等价",
                    "error_level": ErrorLevel.CORRECT,
                }
        except Exception:
            pass

        return {
            "equivalent": False,
            "student_parsed": str(student_expr),
            "standard_parsed": str(std_expr),
            "difference": str(diff) if diff is not None else "比较失败",
            "error_level": ErrorLevel.LEVEL_1,
        }


# ═══════════════════════════════════════════════
# Step-Level Execution against Solution Graph
# ═══════════════════════════════════════════════

# ═══════════════════════════════════════════════
# Student Graph Builder v3.3
# ═══════════════════════════════════════════════

STEP_LABEL_PATTERNS = [
    r'(?:^|\n)\s*(?:\d+[\s\.、．]+)?(?:求|计算|解|证明|判断|讨论|写出|列出)',
    r'(?:^|\n)\s*[（(]\s*[IVXivx1-9]+\s*[）)]',
    r'(?:^|\n)\s*[一二三四五六七八九十]+[、．\s]',
]

def detect_math_content(text: str) -> bool:
    """检测文本中是否包含实际数学内容（非仅步骤描述）"""
    stripped = text.strip()
    if not stripped:
        return False
    # Strip common step prefixes: "1.", "①", "一、", "(1)"
    stripped = re.sub(r'^[\d\s\.、．①②③④⑤一二三四五六七八九十（(）)\[\]\s]+', '', stripped)
    stripped = stripped.strip()
    if not stripped:
        return False
    # Has LaTeX math mode markers
    if '$' in stripped:
        return True
    # Has LaTeX commands
    if re.search(r'\\[a-zA-Z]{2,}', stripped):
        return True
    # Has symbolic operators (not just step labels)
    if re.search(r'[+\-*/=<>^_()[\]{}]', stripped):
        return True
    if re.search(r'\b(sin|cos|tan|ln|log|exp|lim|int|sum|frac|sqrt|partial|infty)\b', stripped):
        return True
    if re.search(r'[a-zA-Z]\s*[=≠<>≤≥≈]\s*', stripped):
        return True
    # Has expressions with variables and numbers: 2x, x^2, 3y+1
    if re.search(r'[a-zA-Z]\s*[\^]', stripped):
        return True
    if re.search(r'\d+\s*[a-zA-Z]|[a-zA-Z]\s*\d+', stripped):
        return True
    if re.search(r'[a-zA-Z]\(\s*[a-zA-Z0-9]', stripped):
        return True
    # Has number expressions like "-1", "0.5", "1/2"
    if re.search(r'\d+\s*[+\-*/]\s*\d+', stripped):
        return True
    return False


def build_student_graph(student_text: str) -> dict:
    """
    将学生文本解析为 Student Graph。
    返回:
        {
            "nodes": [{"id": str, "label": str, "has_math": bool, "math_content": str}],
            "total_steps": int,
            "steps_with_math": int,
            "is_level_0": bool,  # 只有步骤名, 无数学执行
        }
    """
    nodes = []
    # 按自然段落或步骤编号拆分
    lines = student_text.strip().split('\n')
    current_step = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测是否为新步骤开始
        is_new_step = any(re.match(p, line) for p in STEP_LABEL_PATTERNS)
        if re.match(r'^\d+[\s\.、．]', line):
            is_new_step = True

        if is_new_step or current_step is None:
            if current_step:
                current_step["has_math"] = detect_math_content(current_step["raw"])
                if current_step["has_math"]:
                    current_step["math_content"] = current_step["raw"]
                nodes.append(current_step)

            current_step = {
                "id": f"s{len(nodes)+1}",
                "label": line[:80],
                "raw": line,
                "has_math": False,
                "math_content": "",
            }
        else:
            current_step["raw"] += "\n" + line

    if current_step:
        current_step["has_math"] = detect_math_content(current_step["raw"])
        if current_step["has_math"]:
            current_step["math_content"] = current_step["raw"]
        nodes.append(current_step)

    steps_with_math = sum(1 for n in nodes if n["has_math"])
    is_level_0 = (len(nodes) > 0 and steps_with_math == 0)

    return {
        "nodes": [{k: v for k, v in n.items() if k != "raw"} for n in nodes],
        "total_steps": len(nodes),
        "steps_with_math": steps_with_math,
        "is_level_0": is_level_0,
    }


# ═══════════════════════════════════════════════
# Enhanced Execution against Solution Graph
# ═══════════════════════════════════════════════

def execute_against_graph(student_text: str,
                          solution_graph: 'SolutionGraph') -> dict:
    """
    对学生全文执行 Solution Graph 中的每个步骤，返回逐步骤评分。

    Args:
        student_text: 学生完整作答文本
        solution_graph: 标准解题图

    Returns:
        {
            "step_results": [{"node_id": str, "equivalent": bool, "error_level": int}],
            "total_score": float,
            "max_score": float,
            "coverage": float,
            "error_summary": str,
        }
    """
    # 先检测 Level 0: 学生只写了步骤名, 没有数学执行
    student_graph = build_student_graph(student_text)
    if student_graph["is_level_0"]:
        return {
            "step_results": [],
            "total_score": 0.0,
            "max_score": round(sum(n.weight for n in solution_graph.nodes), 1),
            "coverage": 0.0,
            "error_summary": "学生仅列出解题步骤名称，未执行任何数学计算",
            "dominant_error_level": ErrorLevel.LEVEL_0,
            "diagnosis": "no symbolic computation executed",
            "failed_nodes": [n.id for n in solution_graph.nodes],
            "comment": "学生仅表达了解题流程名称，没有任何数学执行",
            "student_graph": student_graph,
        }

    step_results = []
    total_weight = 0.0
    earned_score = 0.0

    for node in solution_graph.nodes:
        result = symbolic_compare(student_text, node.output)
        step_results.append({
            "node_id": node.id,
            "node_type": node.type,
            "label": node.label,
            "equivalent": result["equivalent"],
            "error_level": result["error_level"],
            "weight": node.weight,
        })

        if result["equivalent"]:
            earned_score += node.weight
        total_weight += node.weight

    coverage = earned_score / max(total_weight, 0.01)

    # 生成错误摘要
    errors = []
    level0 = [r for r in step_results if r["error_level"] == ErrorLevel.LEVEL_0]
    level1 = [r for r in step_results if r["error_level"] == ErrorLevel.LEVEL_1]
    if level0:
        errors.append(f"{len(level0)}个步骤未执行")
    if level1:
        errors.append(f"{len(level1)}个步骤计算错误")

    failed_ids = [r["node_id"] for r in step_results if r["error_level"] != ErrorLevel.CORRECT]
    return {
        "step_results": step_results,
        "total_score": round(earned_score, 1),
        "max_score": round(total_weight, 1),
        "coverage": round(coverage, 2),
        "error_summary": "; ".join(errors) if errors else "全部正确",
        "diagnosis": errors[0] if errors else "解题过程完整",
        "comment": "学生未执行数学计算" if len(level0) == len(step_results) else (
            errors[0] if errors else "解题过程完整"
        ),
        "failed_nodes": failed_ids,
        "dominant_error_level": (
            ErrorLevel.LEVEL_0 if level0 else
            ErrorLevel.LEVEL_1 if level1 else
            ErrorLevel.CORRECT
        ),
        "student_graph": student_graph,
    }


# ═══════════════════════════════════════════════
# 快速判定函数（Engine A fast path 使用）
# ═══════════════════════════════════════════════

def quick_compare(student: str, standard: str) -> dict:
    """快速符号比较（适用于填空/选择题）"""
    if not _HAS_SYMPY:
        def norm(s):
            return re.sub(r'\s+', '', str(s)).lower().replace('{','').replace('}','')
        student_s = norm(student)
        std_s = norm(standard)
        if not student_s:
            return {"equivalent": False, "student_parsed": "", "standard_parsed": standard,
                    "difference": None, "error_level": ErrorLevel.LEVEL_0}
        eq = student_s == std_s
        return {"equivalent": eq, "student_parsed": student, "standard_parsed": standard,
                "difference": None if eq else "string mismatch",
                "error_level": ErrorLevel.CORRECT if eq else ErrorLevel.LEVEL_1}
    return symbolic_compare(student, standard)
