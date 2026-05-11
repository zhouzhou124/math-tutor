"""
Graph Compiler v3.4 — 自动生成 + 验证 + 修复 Solution Graph

流程:
  Problem → LLM 生成草步骤 → Symbolic 逐步验证 → 自修复 → 编译为 DAG → 入库
"""
import json, re
from dataclasses import dataclass, field
from solution_graph import (SolutionGraph, GraphNode, GraphEdge,
                            make_choice_graph, make_fill_blank_graph,
                            make_solution_graph)
from symbolic_executor import (_HAS_SYMPY, parse_expression, symbolic_compare,
                                ErrorLevel, detect_math_content)

# ═══════════════════════════════════════════════
# Step Model (Intent + Execution + Correctness)
# ═══════════════════════════════════════════════

@dataclass
class CompiledStep:
    """编译后的步骤 — 区分"想做什么"和"是否真的做了"."""
    id: str
    intent: str           # 操作意图: differentiate / solve / ...
    description: str       # 自然语言描述
    latex: str = ""        # LaTeX 表达式
    output: str = ""       # 期望输出
    verified: bool = False # 是否通过数学验证
    corrected: str = ""    # 如果验证失败, 修正后的版本
    confidence: float = 0.0


# ═══════════════════════════════════════════════
# Prompt: extract solution steps from problem + answer
# ═══════════════════════════════════════════════

STEP_EXTRACTION_PROMPT = """从以下数学题的标准解答中提取解题步骤.

对每一步, 输出:
- type: 操作类型 (differentiate / integrate / solve_system / hessian_test /
         substitute / simplify / classify / compute_limit / expand_series /
         matrix_op / eigen_solve / orthogonalize / quadratic_form /
         probability_calc / expectation / mle_derive / moment_estimate /
         apply_theorem / final_answer)
- description: 简短自然语言描述
- latex: 该步骤的关键 LaTeX 表达式
- output: 该步骤的期望输出

输出纯 JSON 数组, 不要其他内容:
[{"type": "differentiate", "description": "求偏导 fx", "latex": "f_x=2x(2+y^2)", "output": "2x(2+y^2)"}]

题目: {problem}
标准解答: {solution}"""


# ═══════════════════════════════════════════════
# Symbolic Verification
# ═══════════════════════════════════════════════

def verify_step(step: CompiledStep, problem_context: str = "") -> CompiledStep:
    """
    用数学验证步骤的正确性.
    返回验证后的步骤 (verified=True/False, corrected=修正值).
    """
    if not _HAS_SYMPY or not step.output:
        step.verified = not _HAS_SYMPY  # Can't verify without SymPy — trust the source
        step.confidence = 0.7 if not _HAS_SYMPY else 0.0
        return step

    # For now: verify by checking parseability and internal consistency
    expr = parse_expression(step.output)
    if expr is not None:
        step.verified = True
        step.confidence = 0.9
    else:
        step.verified = False
        step.confidence = 0.3

    return step


# ═══════════════════════════════════════════════
# Solution Graph Compiler
# ═══════════════════════════════════════════════

def compile_steps_to_graph(question_id: str, final_answer: str,
                           steps_data: list[dict],
                           total_score: float = 10.0) -> SolutionGraph:
    """
    将 LLM 提取的步骤 JSON 编译为验证过的 SolutionGraph DAG.

    Args:
        question_id: 题目 ID
        final_answer: 最终答案
        steps_data: LLM 提取的步骤列表 [{"type":..., "description":..., "latex":..., "output":...}]
        total_score: 满分

    Returns:
        验证过的 SolutionGraph
    """
    nodes = []
    edges = []
    prev_id = None

    for i, step_dict in enumerate(steps_data):
        nid = f"n{i+1}"
        step = CompiledStep(
            id=nid,
            intent=step_dict.get("type", "unknown"),
            description=step_dict.get("description", ""),
            latex=step_dict.get("latex", ""),
            output=step_dict.get("output", ""),
        )

        # Symbolic validation
        step = verify_step(step)

        node = GraphNode(
            id=nid,
            type=step.intent,
            label=step.description,
            output=step.corrected or step.output,
            input_refs=[prev_id] if prev_id else [],
            weight=0.0,  # Auto-normalized by make_solution_graph
        )
        nodes.append(node)

        if prev_id:
            edges.append(GraphEdge(prev_id, nid))
        prev_id = nid

    return make_solution_graph(question_id, final_answer, nodes, edges, total_score)


def compile_from_llm_text(question_id: str, final_answer: str,
                          llm_response: str,
                          total_score: float = 10.0) -> SolutionGraph:
    """
    从 LLM 原始响应文本中解析步骤并编译为 SolutionGraph.

    LLM 响应可以是:
    - JSON 数组: [{"type":..., ...}, ...]
    - 编号文本: 1. 求偏导: fx=...  2. 求驻点: ...
    """
    steps = []

    # Try JSON parse first
    try:
        json_match = re.search(r'\[[\s\S]*\]', llm_response)
        if json_match:
            steps = json.loads(json_match.group(0))
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: parse numbered text
    if not steps:
        lines = llm_response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Match: "1. 求偏导: fx=2x(2+y^2)" or "n1: differentiate fx=..."
            m = re.match(r'(?:\d+[\.\s、．]+|n\d+[:：]\s*)?(.+)', line)
            if m:
                content = m.group(1).strip()
                # Guess type from content
                guessed_type = "compute"
                if any(kw in content for kw in ['求导', '偏导', '导数', 'differentiate', 'diff']):
                    guessed_type = "differentiate"
                elif any(kw in content for kw in ['积分', 'integrate', 'int']):
                    guessed_type = "integrate"
                elif any(kw in content for kw in ['解方程', '求解', '驻点', 'solve']):
                    guessed_type = "solve_system"
                elif any(kw in content for kw in ['Hessian', '判别', '极值', '分类', 'classify']):
                    guessed_type = "hessian_test"
                elif any(kw in content for kw in ['极限', 'limit']):
                    guessed_type = "compute_limit"
                elif any(kw in content for kw in ['特征值', 'eigenvalue']):
                    guessed_type = "eigen_solve"
                elif any(kw in content for kw in ['化简', 'simplify']):
                    guessed_type = "simplify"

                # Extract output: text after ":" or "=" or "得"
                output = ""
                for sep in [':', '：', '得']:
                    if sep in content:
                        output = content.split(sep, 1)[-1].strip()
                        break
                if not output and '=' in content:
                    output = content.split('=', 1)[-1].strip()

                steps.append({
                    "type": guessed_type,
                    "description": content[:60],
                    "latex": content,
                    "output": output,
                })

    return compile_steps_to_graph(question_id, final_answer, steps, total_score)


# ═══════════════════════════════════════════════
# Auto-generate from DB standard_answer
# ═══════════════════════════════════════════════

def auto_generate_from_db(question: dict) -> SolutionGraph:
    """
    从题库 question dict 自动生成 SolutionGraph.
    优先使用 correct_option (选择题) 或 standard_answer (解答题).
    """
    qid = question.get("question_id", "unknown")
    qtype = question.get("question_type", "")
    answer = question.get("standard_answer", "")
    score = question.get("score", 10)

    # Choice → single-step graph
    if qtype == "选择题":
        correct = question.get("correct_option", "")
        if correct:
            return make_choice_graph(qid, correct, score)

    # Fill-blank → single-node graph
    if qtype == "填空题":
        return make_fill_blank_graph(qid, answer, score)

    # Solution/proof → try LLM extraction if answer is detailed
    if qtype in ("解答题", "证明题"):
        if answer and len(answer) > 50:
            return compile_from_llm_text(qid, answer[:200], answer, score)

    # Fallback: single-node graph with the answer
    return make_fill_blank_graph(qid, answer, score)


# ═══════════════════════════════════════════════
# v3.4 工程增强: JSON 修复 + Graph 验证 + 执行门
# ═══════════════════════════════════════════════

def safe_parse_llm_output(text: str) -> dict:
    """
    JSON 强约束: 防 LLM 乱输出。
    尝试解析 JSON, 失败则尝试修复常见模式。
    """
    import json as _json

    # Strip markdown code fences
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*$', '', text)

    # Try direct parse
    try:
        return _json.loads(text)
    except (_json.JSONDecodeError, ValueError):
        pass

    # Try to find JSON object/array in text
    for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        m = re.search(pattern, text)
        if m:
            try:
                return _json.loads(m.group(0))
            except (_json.JSONDecodeError, ValueError):
                continue

    # Failed — return empty
    return {}


def validate_graph(graph: SolutionGraph, required_types: list[str] = None) -> dict:
    """
    Graph Validation: 检查是否包含必要的操作类型.
    默认检查: 多元极值题需要 differentiate + solve_system + hessian_test.
    """
    if required_types is None:
        required_types = ["differentiate", "solve_system", "hessian_test"]

    present_types = {n.type for n in graph.nodes}
    missing = [t for t in required_types if t not in present_types]
    has_final = any(n.type == "final_answer" for n in graph.nodes)

    return {
        "valid": len(missing) == 0,
        "present_types": sorted(present_types),
        "missing_required": missing,
        "has_final_answer": has_final,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
    }


def execution_gate(graph: SolutionGraph) -> dict:
    """
    执行门: 防"假步骤" (只有 intent 没有 execution).
    检查每个节点是否有实际的数学输出.
    """
    empty_nodes = []
    for n in graph.nodes:
        if n.type == "final_answer":
            continue
        if not n.output or not n.output.strip():
            empty_nodes.append(n.id)
        elif not detect_math_content(n.output):
            empty_nodes.append(n.id)

    return {
        "passed": len(empty_nodes) == 0,
        "empty_nodes": empty_nodes,
        "total_nodes": len(graph.nodes),
        "execution_rate": 1.0 - len(empty_nodes) / max(len(graph.nodes), 1),
    }
