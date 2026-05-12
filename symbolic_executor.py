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

def _convert_nested_frac(s: str) -> str:
    """将 \\frac{a}{b} 递归转换为 ((a)/(b))，从最内层开始处理。"""
    for _ in range(10):  # 最多 10 层嵌套
        m = re.search(r'\\frac\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', s)
        if not m:
            break
        num, den = m.group(1), m.group(2)
        replacement = f'(({num})/({den}))'
        s = s[:m.start()] + replacement + s[m.end():]
    return s


def _convert_nested_sqrt(s: str) -> str:
    """将 \\sqrt{expr} 转换为 sqrt((expr))。"""
    for _ in range(5):
        m = re.search(r'\\sqrt\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', s)
        if not m:
            break
        inner = m.group(1)
        replacement = f'sqrt(({inner}))'
        s = s[:m.start()] + replacement + s[m.end():]
    return s


def parse_expression(latex_or_text: str) -> Optional['sp.Expr']:
    """
    将 LaTeX 或自然文本中的数学表达式解析为 SymPy 表达式。
    支持: x^2, sin(x), ln(y), e^x, (x+1)^2, 嵌套分数, 嵌套根号, etc.
    """
    if not _HAS_SYMPY or not latex_or_text or not latex_or_text.strip():
        return None

    s = latex_or_text.strip()
    s = s.replace('$', '').replace('$$', '')
    s = s.replace(r'\sin', 'sin').replace(r'\cos', 'cos').replace(r'\tan', 'tan')
    s = s.replace(r'\arctan', 'atan').replace(r'\arcsin', 'asin').replace(r'\arccos', 'acos')
    s = s.replace(r'\ln', 'ln').replace(r'\log', 'log').replace(r'\exp', 'exp')
    s = s.replace(r'\pi', 'pi').replace(r'\infty', 'oo')
    s = s.replace(r'\cdot', '*').replace(r'\times', '*')
    s = s.replace(r'\le', '<=').replace(r'\ge', '>=').replace(r'\ne', '!=')

    # 先处理嵌套的 \frac 和 \sqrt（从内到外）
    s = _convert_nested_frac(s)
    s = _convert_nested_sqrt(s)

    # 清理剩余的 LaTeX 命令
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = s.replace('{', '(').replace('}', ')')

    # 隐式乘法: 2x → 2*x, (a)(b) → (a)*(b)
    s = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', s)
    s = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', s)
    s = re.sub(r'\)\(', ')*(', s)
    s = re.sub(r'(\d)\(', r'\1*(', s)
    s = re.sub(r'\)(\d)', r')*\1', s)
    s = re.sub(r'e\^', 'exp', s)

    try:
        expr = sp.sympify(s, evaluate=False)
        return expr
    except (sp.SympifyError, TypeError, SyntaxError, IndexError, ValueError):
        return None


# ═══════════════════════════════════════════════
# Symbolic Execution + Comparison
# ═══════════════════════════════════════════════

def _norm_str(s: str) -> str:
    """字符串规范化：去掉空格、$符号，小写化。"""
    return re.sub(r'\s+', '', s.lower().replace('$', ''))


def _numeric_sample(expr, n_points: int = 5, radius: float = 2.0) -> bool:
    """
    数值采样比较。在 [-radius, radius] 区间内采样 n_points 个值，
    如果全部匹配则认为等价。快速排除大多数不等价表达式。
    只对单变量表达式有效。
    """
    try:
        import random
        free_vars = list(expr.free_symbols)
        if not free_vars:
            # 常量表达式：直接 evalf
            return abs(float(expr.evalf())) < 1e-10 if hasattr(expr, 'evalf') else False
        for _ in range(n_points):
            subs = {}
            for v in free_vars:
                subs[v] = random.uniform(-radius, radius)
            val = float(expr.subs(subs).evalf())
            if abs(val) > 1e-8:
                return False
        return True
    except Exception:
        return None  # 无法判断


def symbolic_compare(student_text: str, standard_expr: str) -> dict:
    """
    分级符号等价比较（从快到慢）。

    Level 1: 字符串规范化比较
    Level 2: 数值采样（快速排除不等价）
    Level 3: expand/factor 比较
    Level 4: simplify（最后手段，加保护）

    Returns:
        {"equivalent", "student_parsed", "standard_parsed", "difference", "error_level", "method"}
    """

    def _result(equiv: bool, method: str, diff: str = None, level=ErrorLevel.CORRECT):
        return {
            "equivalent": equiv,
            "student_parsed": student_text,
            "standard_parsed": standard_expr,
            "difference": diff,
            "error_level": level if not equiv else ErrorLevel.CORRECT,
            "method": method,
        }

    if not student_text or not student_text.strip():
        return _result(False, "empty", "未作答", ErrorLevel.LEVEL_0)

    # ── Level 1: 字符串规范化 ──
    if _norm_str(student_text) == _norm_str(standard_expr):
        return _result(True, "string_norm")

    # ── 无 SymPy：只能做到 L1 ──
    if not _HAS_SYMPY:
        return _result(False, "string_norm", "字符串不匹配（无SymPy）", ErrorLevel.LEVEL_1)

    # 解析
    student_expr = parse_expression(student_text)
    std_expr = parse_expression(standard_expr)

    if student_expr is None:
        return _result(False, "parse_fail", "无法解析学生表达式", ErrorLevel.LEVEL_0)
    if std_expr is None:
        return _result(False, "parse_fail", "标准表达式无法解析", ErrorLevel.LEVEL_0)

    diff_expr = student_expr - std_expr

    # ── Level 2: 数值采样（快速路径）──
    numeric_result = _numeric_sample(diff_expr)
    if numeric_result is True:
        return _result(True, "numeric_sample")
    elif numeric_result is False:
        return _result(False, "numeric_sample", "数值采样不等价", ErrorLevel.LEVEL_1)

    # ── Level 3: expand/factor（比 simplify 快）──
    try:
        if sp.expand(diff_expr) == 0:
            return _result(True, "expand")
    except Exception:
        pass
    try:
        if sp.factor(diff_expr) == 0:
            return _result(True, "factor")
    except Exception:
        pass

    # ── Level 4: simplify（最后手段，带线程超时保护）──
    try:
        import concurrent.futures as _futures
        with _futures.ThreadPoolExecutor(max_workers=1) as _pool:
            _future = _pool.submit(lambda: sp.simplify(diff_expr))
            diff_simplified = _future.result(timeout=5)
        if diff_simplified == 0:
            return _result(True, "simplify")
    except (_futures.TimeoutError, Exception):
        return _result(False, "simplify_timeout", "simplify 超时，结果不可靠", ErrorLevel.LEVEL_1)

    return _result(False, "simplify", "不等价", ErrorLevel.LEVEL_1)


# ═══════════════════════════════════════════════
#  Domain-Aware Comparison（填空题专用）
# ═══════════════════════════════════════════════

# 常见定义域假设
_DOMAIN_ASSUMPTIONS = [
    {"label": "x>=0", "symbols": {"x": "positive"}},
    {"label": "x in Reals", "symbols": {"x": "real"}},
    {"label": "n positive integer", "symbols": {"n": ("integer", "positive")}},
    {"label": "all variables positive", "mode": "all_positive"},
    {"label": "all variables real", "mode": "all_real"},
]


def symbolic_compare_with_domains(student_text: str, standard_expr: str) -> dict:
    """
    带定义域假设的符号等价比较。

    适用于填空题：
      sqrt(x^2) vs x  →  仅当 x>=0 时等价
      1/(1/x) vs x    →  仅当 x≠0 时等价

    先做标准比较，不等价时尝试常见定义域假设。
    """
    # 先标准比较
    result = symbolic_compare(student_text, standard_expr)
    if result.get("equivalent"):
        return result

    if not _HAS_SYMPY:
        return result

    student_expr = parse_expression(student_text)
    std_expr = parse_expression(standard_expr)
    if student_expr is None or std_expr is None:
        return result

    # 提取表达式中的自由变量
    free_vars = student_expr.free_symbols | std_expr.free_symbols
    var_names = [str(v) for v in free_vars]

    # 尝试常见定义域假设
    for assumption in _DOMAIN_ASSUMPTIONS:
        try:
            # 构建带假设的符号
            local_dict = {}
            for old_sym in free_vars:
                name = str(old_sym)
                if assumption.get("mode") == "all_positive":
                    new_sym = sp.Symbol(name, positive=True)
                elif assumption.get("mode") == "all_real":
                    new_sym = sp.Symbol(name, real=True)
                else:
                    sym_assumptions = assumption.get("symbols", {}).get(name)
                    if sym_assumptions:
                        kwargs = {}
                        if isinstance(sym_assumptions, tuple):
                            for a in sym_assumptions:
                                kwargs[a] = True
                        else:
                            kwargs[sym_assumptions] = True
                        new_sym = sp.Symbol(name, **kwargs)
                    else:
                        continue
                local_dict[old_sym] = new_sym

            if not local_dict:
                continue

            # 重建带假设的表达式
            s_expr = student_expr.subs(local_dict)
            t_expr = std_expr.subs(local_dict)

            diff = sp.simplify(s_expr - t_expr)
            if diff == 0:
                return {
                    "equivalent": True,
                    "student_parsed": str(student_expr),
                    "standard_parsed": str(std_expr),
                    "difference": None,
                    "error_level": ErrorLevel.CORRECT,
                    "method": f"domain_{assumption['label'].replace(' ', '_')}",
                }
        except Exception:
            continue

    return result


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
            "nodes": [{"id", "type", "label", "has_math", "math_content", "has_error"}],
            "total_steps": int,
            "steps_with_math": int,
            "is_level_0": bool,
        }
    """
    from operations import infer_op_from_text

    nodes = []
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
                _finalize_node(current_step)
                nodes.append(current_step)

            current_step = {
                "id": f"s{len(nodes)+1}",
                "label": line[:80],
                "raw": line,
                "has_math": False,
                "math_content": "",
                "type": "compute",
                "has_error": False,
            }
        else:
            current_step["raw"] += "\n" + line

    if current_step:
        _finalize_node(current_step)
        nodes.append(current_step)

    steps_with_math = sum(1 for n in nodes if n["has_math"])
    is_level_0 = (len(nodes) > 0 and steps_with_math == 0)

    return {
        "nodes": [{k: v for k, v in n.items() if k != "raw"} for n in nodes],
        "total_steps": len(nodes),
        "steps_with_math": steps_with_math,
        "is_level_0": is_level_0,
    }


def _finalize_node(node: dict):
    """填充节点的 has_math, math_content, type, has_error 字段。"""
    from operations import infer_op_from_text
    node["has_math"] = detect_math_content(node["raw"])
    if node["has_math"]:
        node["math_content"] = node["raw"]
    node["type"] = infer_op_from_text(node["raw"]).value
    node["has_error"] = bool(
        re.search(r'[×✗错误]|不正确|不对|算错|写错', node["raw"])
    )


def build_student_graph_from_trace(trace_result: dict) -> dict:
    """
    将 extract_student_trace() 的输出转换为 match_graphs() 兼容的 student graph。

    Args:
        trace_result: extract_student_trace() 的返回值

    Returns:
        {
            "nodes": [{"id", "type", "label", "output", "has_math", "math_content"}],
            "total_steps": int,
            "steps_with_math": int,
            "is_level_0": bool,
        }
    """
    steps = trace_result.get("steps", [])
    nodes = []
    for step in steps:
        output = step.get("output_state", "")
        has_math = bool(output) or detect_math_content(step.get("label", ""))
        nodes.append({
            "id": step.get("id", f"s{len(nodes)+1}"),
            "type": step.get("operation", "compute"),
            "label": step.get("label", ""),
            "output": output,
            "input_state": step.get("input_state", ""),
            "has_math": has_math,
            "math_content": output or step.get("label", ""),
            "has_error": step.get("has_error", False),
        })

    steps_with_math = sum(1 for n in nodes if n["has_math"])
    return {
        "nodes": nodes,
        "total_steps": len(nodes),
        "steps_with_math": steps_with_math,
        "is_level_0": len(nodes) > 0 and steps_with_math == 0,
        "final_answer": trace_result.get("final_answer", ""),
        "method_name": trace_result.get("method_name", ""),
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
    """快速符号比较（适用于填空/选择题）。带定义域意识。"""
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

    # 先标准比较
    result = symbolic_compare(student, standard)
    if result.get("equivalent"):
        return result

    # 标准比较不等价 → 尝试带定义域假设
    return symbolic_compare_with_domains(student, standard)
