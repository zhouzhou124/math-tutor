"""
Solution Graph Generator v3.6 — 题型+方法→解题路径编译器

核心: 标准答案不是"真理来源", 而是"提示种子 (hint seed)"
- 有答案 → Completion Engine (扩展为完整步骤)
- 无答案 → Generation Engine (从题型模板生成)
- 评估 → Method-to-Step Compiler (方法名→具体步骤)

统一输出: SolutionGraph
"""
from dataclasses import dataclass, field
from problem_space import (classify_problem_space, ProblemSpace,
                            detect_theorems_in_student, THEOREM_KB)
from solution_graph import (SolutionGraph, GraphNode, GraphEdge,
                            make_solution_graph)


# ═══════════════════════════════════════════════
# Method-to-Step Templates (方法→步骤编译器)
# ═══════════════════════════════════════════════

METHOD_TEMPLATES = {
    # ── 极限方法 ──
    "等价无穷小替换": [
        ("识别未定式类型", "pattern_recognition", "0/0型或∞/∞型"),
        ("选择等价替换", "method_selection", "x→0时 sinx~x, tanx~x, e^x-1~x"),
        ("执行替换", "substitute", ""),
        ("计算极限值", "compute_limit", ""),
    ],
    "洛必达法则": [
        ("验证洛必达条件", "check_conditions", "0/0或∞/∞, 分子分母可导"),
        ("分子分母分别求导", "differentiate", ""),
        ("代入求极限", "compute_limit", ""),
        ("若仍为未定式, 继续洛必达", "iterate", ""),
    ],
    "泰勒展开": [
        ("确定展开阶数", "method_selection", "展开到最低阶非零项"),
        ("逐项泰勒展开", "expand_series", ""),
        ("合并同类项", "simplify", ""),
        ("代入求极限", "compute_limit", ""),
    ],
    "夹逼准则": [
        ("构造下界表达式", "construct_bound", "lower"),
        ("构造上界表达式", "construct_bound", "upper"),
        ("证明上下界极限相等", "verify_bounds", ""),
        ("由夹逼准则得极限", "apply_theorem", "squeeze"),
    ],

    # ── 积分方法 ──
    "分部积分": [
        ("选择u和dv", "method_selection", "LIATE原则"),
        ("计算du和v", "differentiate+integrate", ""),
        ("代入分部积分公式", "substitute", "∫udv=uv-∫vdu"),
        ("计算剩余积分", "integrate", ""),
    ],
    "换元积分": [
        ("选择换元变量", "method_selection", "t=φ(x)"),
        ("计算dx与dt关系", "differentiate", ""),
        ("代入并调整积分限", "substitute", ""),
        ("计算新积分", "integrate", ""),
    ],

    # ── 证明方法 ──
    "构造函数+零点定理": [
        ("构造函数F(x)", "construct_aux_function", ""),
        ("验证F连续且端点异号", "check_conditions", ""),
        ("应用零点定理", "apply_theorem", "zero_point"),
        ("得出结论", "conclude", ""),
    ],
    "拉格朗日中值定理": [
        ("验证连续可导条件", "check_conditions", "continuous+differentiable"),
        ("写出拉格朗日公式", "apply_theorem", "MVT"),
        ("代入端点值", "substitute", ""),
        ("解得ξ", "solve", ""),
    ],
    "构造辅助函数+罗尔定理": [
        ("构造辅助函数", "construct_aux_function", ""),
        ("验证端点函数值相等", "check_conditions", "f(a)=f(b)"),
        ("应用罗尔定理", "apply_theorem", "rolle"),
        ("得出结论", "conclude", ""),
    ],

    # ── 线代方法 ──
    "二次型→矩阵编译": [
        ("构造二次型矩阵A: f(x)=x^T A x", "quadratic_form",
         "交叉项系数平分到对称位置"),
        ("写出矩阵A的具体数值", "matrix_op", ""),
    ],
    "特征值求解": [
        ("写出特征方程|λE-A|=0", "eigen_solve", ""),
        ("展开行列式得特征多项式", "eigen_solve", ""),
        ("求解特征多项式的根得特征值", "solve", "λ1,λ2,λ3"),
    ],
    "特征向量计算": [
        ("对每个特征值λ_i, 解(A-λ_i I)x=0", "eigen_solve", ""),
        ("写出特征向量的基础解系", "eigen_solve", ""),
    ],
    "正交化与归一化": [
        ("验证A对称→不同特征值对应特征向量自动正交", "check_conditions", "spectral theorem"),
        ("对同特征值内的向量施密特正交化(如需)", "orthogonalize", ""),
        ("将所有特征向量归一化为单位向量", "orthogonalize", "||e_i||=1"),
    ],
    "构造正交矩阵Q": [
        ("以归一化特征向量为列构成Q", "matrix_op", "Q=(e1,e2,e3)"),
        ("验证Q^T A Q = Λ (对角矩阵)", "verify", ""),
    ],
    "写出标准形": [
        ("由Λ写出标准形: λ1·y1² + λ2·y2² + λ3·y3²", "quadratic_form", ""),
        ("匹配题目给定的标准形参数", "solve", ""),
    ],
    "二次型标准化": [
        ("构造二次型矩阵A: x^T A x", "quadratic_form", ""),
        ("求特征值|λE-A|=0", "eigen_solve", ""),
        ("求特征向量", "eigen_solve", ""),
        ("正交化归一化得Q", "orthogonalize", ""),
        ("写出标准形", "quadratic_form", ""),
    ],
    "Spectral Theorem Pipeline": [
        ("识别: 实对称矩阵→谱定理→A=QΛQ^T", "apply_theorem", "spectral theorem"),
        ("计算特征值: |λE-A|=0", "eigen_solve", ""),
        ("计算特征向量: (A-λI)x=0", "eigen_solve", ""),
        ("构造正交矩阵Q: 归一化特征向量为列", "orthogonalize", ""),
        ("验证: Q^T A Q = diag(λ1,λ2,λ3)", "verify", ""),
        ("写出标准形: λ1·y1²+λ2·y2²+λ3·y3²", "quadratic_form", ""),
        ("Answer Backmapping: 匹配题目参数", "conclude", ""),
    ],

    # ── 概率方法 ──
    "分布函数法": [
        ("确定Z与X,Y的关系", "probability_calc", ""),
        ("写出Z的分布函数F_Z(z)", "probability_calc", ""),
        ("分区域积分", "integrate", ""),
        ("求导得密度", "differentiate", ""),
    ],
    "求偏导": [
        ("求偏导数 fx = ∂f/∂x", "differentiate", ""),
        ("求偏导数 fy = ∂f/∂y", "differentiate", ""),
        ("解驻点方程组 fx=0, fy=0", "solve_system", ""),
        ("计算二阶偏导 A=fxx, B=fxy, C=fyy", "differentiate", ""),
        ("Hessian判别: AC-B²>0 且 A>0极小/A<0极大", "hessian_test", ""),
    ],
    "求导分析": [
        ("求一阶导数 f'(x)", "differentiate", ""),
        ("解 f'(x)=0 得驻点", "solve", ""),
        ("求二阶导数 f''(x)", "differentiate", ""),
        ("判断极值/拐点/单调性", "classify", ""),
    ],
    "矩估计+极大似然": [
        ("求总体矩E(X)", "moment_estimate", ""),
        ("令样本矩等于总体矩", "moment_estimate", ""),
        ("写出似然函数L(θ)", "mle_derive", ""),
        ("取对数并求导", "mle_derive", ""),
        ("解得估计量", "solve", ""),
    ],
}


# ═══════════════════════════════════════════════
# Problem Interpreter — 题型识别
# ═══════════════════════════════════════════════

def interpret_problem(question_text: str, question_type: str = "") -> dict:
    """
    问题理解器: 判断题型→匹配方法库.

    Returns: {"problem_type": str, "recommended_methods": [...], "space": ProblemSpace}
    """
    space = classify_problem_space(question_text, question_type)

    # Method matching: scan keywords → recommend methods
    methods = []
    text_lower = question_text.lower()

    # Limit patterns
    if '极限' in question_text or 'lim' in text_lower or '\\lim' in text_lower:
        methods.append("等价无穷小替换")
        methods.append("洛必达法则")
        if any(kw in question_text for kw in ['x→0', 'x^', 'sin', 'cos', 'tan', 'e^', 'ln']):
            methods.append("泰勒展开")
        if any(kw in question_text for kw in ['夹逼', 'squeeze', '≤']):
            methods.append("夹逼准则")

    # Extremum / differentiation patterns
    if any(kw in question_text for kw in ['极值', '极值点', '驻点', '单调', '凹凸', '拐点']):
        if any(kw in question_text for kw in ['多元', 'f(x,y)', '偏导', 'f_x', 'f_y']):
            methods.append("求偏导")
        else:
            methods.append("求导分析")

    # Integral patterns
    if any(kw in question_text for kw in ['积分', '∫', 'int', '\\int']):
        methods.append("分部积分")
        methods.append("换元积分")

    # Proof patterns
    if space == ProblemSpace.PROOF:
        if any(kw in question_text for kw in ['ξ', 'η', '存在', '至少']):
            methods.append("构造函数+零点定理")
            methods.append("拉格朗日中值定理")
        if 'f(a)=f(b)' in question_text or '罗尔' in question_text:
            methods.append("构造辅助函数+罗尔定理")

    # Linear algebra — enhanced detection
    is_eigen = any(kw in question_text for kw in ['特征值', 'eigenvalue', '对角化', '特征向量'])
    is_quad = any(kw in question_text for kw in ['二次型', '标准形', '规范形', '正交变换', 'x^TAx'])
    is_symmetric = any(kw in question_text for kw in ['对称矩阵', '实对称', 'Q^TAQ'])

    if is_quad and (is_eigen or is_symmetric):
        # Full spectral decomposition pipeline
        methods.append("Spectral Theorem Pipeline")
    elif is_eigen:
        methods.append("特征值求解")
        methods.append("特征向量计算")
        methods.append("正交化与归一化")
    elif is_quad:
        methods.append("二次型→矩阵编译")
        methods.append("二次型标准化")
        methods.append("构造正交矩阵Q")

    # Probability/statistics
    if any(kw in question_text for kw in ['概率密度', '分布函数', 'X+Y']):
        methods.append("分布函数法")
    if any(kw in question_text for kw in ['矩估计', '极大似然', 'MLE', '估计量']):
        methods.append("矩估计+极大似然")

    return {
        "problem_type": question_type or "未知",
        "space": space.value,
        "recommended_methods": methods[:3],  # Top 3
        "knowledge_domain": (
            "极限与连续" if '极限' in question_text or 'lim' in text_lower else
            "微积分" if any(kw in question_text for kw in ['导数', '积分', '极值']) else
            "线性代数" if any(kw in question_text for kw in ['矩阵', '特征值', '二次型']) else
            "概率统计" if any(kw in question_text for kw in ['概率', '分布', '估计']) else
            "数学分析"
        ),
    }


# ═══════════════════════════════════════════════
# Generation Engine (无答案时)
# ═══════════════════════════════════════════════

def generate_solution_graph(question_text: str,
                            question_type: str = "",
                            question_id: str = "auto") -> SolutionGraph:
    """
    从题型模板自动生成 Solution Graph (无需参考答案).
    """
    info = interpret_problem(question_text, question_type)
    methods = info["recommended_methods"]

    if not methods:
        # Fallback: single-node graph
        return make_solution_graph(question_id, "", [
            GraphNode(id="n1", type="compute", label="解题", output="", weight=10.0)
        ], [])

    # Compile steps from method templates
    all_steps = []
    for method in methods:
        if method in METHOD_TEMPLATES:
            all_steps.extend(METHOD_TEMPLATES[method])

    # Deduplicate by step label
    seen = set()
    unique_steps = []
    for label, stype, output in all_steps:
        if label not in seen:
            seen.add(label)
            unique_steps.append((label, stype, output))

    nodes = []
    edges = []
    for i, (label, stype, output) in enumerate(unique_steps):
        nid = f"n{i+1}"
        nodes.append(GraphNode(id=nid, type=stype, label=label, output=output,
                               input_refs=[f"n{i}"] if i > 0 else [], weight=0.0))
        if i > 0:
            edges.append(GraphEdge(f"n{i}", nid))

    # Set default score weights
    if nodes:
        w = 10.0 / len(nodes)
        for n in nodes:
            n.weight = round(w, 1)

    return SolutionGraph(
        question_id=question_id,
        final_answer="",
        nodes=nodes,
        edges=edges,
        total_score=10.0,
        grading_mode="step",
    )


# ═══════════════════════════════════════════════
# Completion Engine (有答案时)
# ═══════════════════════════════════════════════

def complete_solution_graph(question_text: str,
                            reference_answer: str,
                            question_type: str = "",
                            question_id: str = "auto") -> SolutionGraph:
    """
    有参考答案时: 以答案为"hint seed", 扩展为完整步骤 DAG.
    """
    # 1. Interpret problem type
    info = interpret_problem(question_text, question_type)

    # 2. Use reference answer as the final node
    # 3. Generate preceding steps from method templates
    methods = info["recommended_methods"]

    if not methods:
        # Single answer node
        return make_solution_graph(question_id, reference_answer, [
            GraphNode(id="n1", type="final_answer", label="标准答案",
                      output=reference_answer, weight=10.0)
        ], [])

    # Build step chain: method steps → final answer
    all_steps = []
    for method in methods[:2]:  # Top 2 methods
        if method in METHOD_TEMPLATES:
            all_steps.extend(METHOD_TEMPLATES[method])

    # Deduplicate
    seen = set()
    unique_steps = []
    for label, stype, output in all_steps:
        if label not in seen:
            seen.add(label)
            unique_steps.append((label, stype, output))

    nodes = []
    edges = []
    for i, (label, stype, output) in enumerate(unique_steps):
        nid = f"n{i+1}"
        nodes.append(GraphNode(id=nid, type=stype, label=label, output=output,
                               input_refs=[f"n{i}"] if i > 0 else [], weight=0.0))
        if i > 0:
            edges.append(GraphEdge(f"n{i}", nid))

    # Add final answer node
    final_nid = f"n{len(nodes)+1}"
    nodes.append(GraphNode(id=final_nid, type="final_answer", label="最终答案",
                           output=reference_answer,
                           input_refs=[f"n{len(nodes)}"] if nodes else [],
                           weight=0.0))
    if nodes:
        edges.append(GraphEdge(nodes[-1].id, final_nid))

    # Normalize weights
    if nodes:
        w = 10.0 / len(nodes)
        for n in nodes:
            n.weight = round(w, 1)

    return SolutionGraph(
        question_id=question_id, final_answer=reference_answer,
        nodes=nodes, edges=edges, total_score=10.0, grading_mode="step",
    )


# ═══════════════════════════════════════════════
# Unified entry point
# ═══════════════════════════════════════════════

def build_solution_graph(question_text: str,
                         reference_answer: str = "",
                         question_type: str = "",
                         question_id: str = "auto") -> SolutionGraph:
    """
    统一入口:
    - 有 answer → Completion Engine
    - 无 answer → Generation Engine
    """
    if reference_answer and len(reference_answer.strip()) > 5:
        return complete_solution_graph(question_text, reference_answer,
                                       question_type, question_id)
    return generate_solution_graph(question_text, question_type, question_id)
