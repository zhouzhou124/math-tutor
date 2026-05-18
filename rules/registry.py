"""
Rule Registry — 内置规则注册表

═══════════════════════════════════════════════════════════════
设计思想
═══════════════════════════════════════════════════════════════

  按操作类型组织规则，每条规则声明式定义。

  规则分类：
    1. 代数变换规则 (EXPAND, FACTOR, SIMPLIFY, CANCEL, SUBSTITUTE, ...)
    2. 微积分规则 (DIFFERENTIATE, INTEGRATE, COMPUTE_LIMIT, ...)
    3. 方程/不等式规则 (SOLVE_EQUATION, SOLVE_INEQUALITY, ...)
    4. 线性代数规则 (ROW_REDUCE, DETERMINANT, ...)
    5. 证明/逻辑规则 (APPLY_THEOREM, CLASSIFY, ...)

  每条规则包含：
    - 前提条件 (preconditions)
    - 后置条件 (postconditions)
    - 生成的约束 (generated_constraints)
    - 生成的子目标 (generated_subgoals)
    - 可能丢失的约束 (may_lose)
    - 可能引入的假设 (may_introduce)
    - 证明义务 (proof_obligations)

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from operations import Op
from rules.dsl import (
    Rule,
    Condition,
    ConditionKind,
    ProofObligation,
    ObligationSeverity,
)


# ══════════════════════════════════════════════════════════════
# 1. 代数变换规则
# ══════════════════════════════════════════════════════════════

ALGEBRA_RULES: list[Rule] = [

    Rule(
        name="expand_equivalence",
        op=Op.EXPAND,
        description="展开是等价变换",
        domain="algebra",
        priority=10,
        generated_constraints=(),
        may_lose=(),
        may_introduce=(),
        proof_obligations=(),
        confidence=0.95,
    ),

    Rule(
        name="factor_equivalence",
        op=Op.FACTOR,
        description="因式分解是等价变换",
        domain="algebra",
        priority=10,
        generated_constraints=(),
        may_lose=(),
        may_introduce=(),
        proof_obligations=(),
        confidence=0.95,
    ),

    Rule(
        name="simplify_sqrt_domain",
        op=Op.SIMPLIFY,
        description="化简可能丢失定义域约束",
        domain="algebra",
        priority=10,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"sqrt|√|\\sqrt",
                description="表达式含根号",
            ),
        ),
        may_lose=("x ≥ 0",),
        proof_obligations=(
            ProofObligation(
                description="确认根号内表达式非负",
                severity=ObligationSeverity.MANDATORY,
                related_constraint="x ≥ 0",
            ),
        ),
        confidence=0.85,
    ),

    Rule(
        name="simplify_abs_domain",
        op=Op.SIMPLIFY,
        description="化简绝对值可能丢失约束",
        domain="algebra",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"\\||abs|\\abs",
                description="表达式含绝对值",
            ),
        ),
        may_lose=("x ≥ 0",),
        proof_obligations=(
            ProofObligation(
                description="确认绝对值化简条件",
                severity=ObligationSeverity.MANDATORY,
                related_constraint="x ≥ 0",
            ),
        ),
        confidence=0.85,
    ),

    Rule(
        name="cancel_divisor_nonzero",
        op=Op.CANCEL,
        description="约分要求约去的因子不为零",
        domain="algebra",
        priority=10,
        generated_constraints=("divisor ≠ 0",),
        may_lose=("divisor ≠ 0",),
        proof_obligations=(
            ProofObligation(
                description="证明约去的因子不为零",
                severity=ObligationSeverity.MANDATORY,
                related_constraint="divisor ≠ 0",
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="cancel_fraction_domain",
        op=Op.CANCEL,
        description="约分 (x^2-1)/(x-1) → x+1 需 x≠1",
        domain="algebra",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"/|\\frac|÷",
                description="表达式含除法",
            ),
        ),
        generated_constraints=("denominator ≠ 0",),
        may_lose=("denominator ≠ 0",),
        proof_obligations=(
            ProofObligation(
                description="证明分母不为零",
                severity=ObligationSeverity.MANDATORY,
                related_constraint="denominator ≠ 0",
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="substitute_range",
        op=Op.SUBSTITUTE,
        description="换元需要确认换元范围",
        domain="algebra",
        priority=10,
        may_introduce=("换元函数单调可导",),
        generated_subgoals=("回代原变量",),
        proof_obligations=(
            ProofObligation(
                description="确认换元函数的范围限制",
                severity=ObligationSeverity.RECOMMENDED,
            ),
            ProofObligation(
                description="回代原变量",
                severity=ObligationSeverity.INFORMATIONAL,
            ),
        ),
        confidence=0.75,
    ),

    Rule(
        name="collect_equivalence",
        op=Op.COLLECT,
        description="合并同类项是等价变换",
        domain="algebra",
        priority=10,
        confidence=0.95,
    ),
]


# ══════════════════════════════════════════════════════════════
# 2. 微积分规则
# ══════════════════════════════════════════════════════════════

CALCULUS_RULES: list[Rule] = [

    Rule(
        name="differentiate_basic",
        op=Op.DIFFERENTIATE,
        description="求导是合法操作",
        domain="calculus",
        priority=10,
        may_introduce=("函数可导",),
        proof_obligations=(
            ProofObligation(
                description="确认函数在定义域内可导",
                severity=ObligationSeverity.RECOMMENDED,
            ),
        ),
        confidence=0.90,
    ),

    Rule(
        name="differentiate_implicit",
        op=Op.DIFFERENTIATE,
        description="隐函数求导需确认可导条件",
        domain="calculus",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"隐函数|implicit|F\(",
                description="隐函数求导",
            ),
        ),
        may_introduce=("F(x,y) 可导",),
        proof_obligations=(
            ProofObligation(
                description="确认隐函数可导条件",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="differentiate_parametric",
        op=Op.DIFFERENTIATE,
        description="参数方程求导需 dx/dt ≠ 0",
        domain="calculus",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"参数|parametric",
                description="参数方程求导",
            ),
        ),
        generated_constraints=("dx/dt ≠ 0",),
        may_introduce=("参数可导且 dx/dt ≠ 0",),
        proof_obligations=(
            ProofObligation(
                description="证明 dx/dt ≠ 0",
                severity=ObligationSeverity.MANDATORY,
                related_constraint="dx/dt ≠ 0",
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="integrate_by_parts",
        op=Op.INTEGRATE,
        description="分部积分需 u,v 可导",
        domain="calculus",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"分部|parts|uv|u dv",
                description="分部积分",
            ),
        ),
        may_introduce=("u, v 可导",),
        proof_obligations=(
            ProofObligation(
                description="确认 u, v 可导",
                severity=ObligationSeverity.RECOMMENDED,
            ),
        ),
        confidence=0.85,
    ),

    Rule(
        name="integrate_substitution",
        op=Op.INTEGRATE,
        description="换元积分需换元函数单调可导",
        domain="calculus",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"换元|substitut|t =|u =",
                description="换元积分",
            ),
        ),
        may_introduce=("换元函数单调可导",),
        generated_subgoals=("回代原变量",),
        proof_obligations=(
            ProofObligation(
                description="确认换元函数单调可导",
                severity=ObligationSeverity.RECOMMENDED,
            ),
            ProofObligation(
                description="回代原变量",
                severity=ObligationSeverity.INFORMATIONAL,
            ),
        ),
        confidence=0.85,
    ),

    Rule(
        name="integrate_1_over_x",
        op=Op.INTEGRATE,
        description="1/x 积分需 x ≠ 0",
        domain="calculus",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"1/x|1\\x|\\frac\{1\}\{x\}",
                description="1/x 积分",
            ),
        ),
        generated_constraints=("x ≠ 0",),
        may_introduce=("x ≠ 0",),
        proof_obligations=(
            ProofObligation(
                description="确认 x ≠ 0",
                severity=ObligationSeverity.MANDATORY,
                related_constraint="x ≠ 0",
            ),
        ),
        confidence=0.85,
    ),

    Rule(
        name="integrate_basic",
        op=Op.INTEGRATE,
        description="基本积分操作",
        domain="calculus",
        priority=5,
        confidence=0.90,
    ),

    Rule(
        name="limit_lhopital",
        op=Op.COMPUTE_LIMIT,
        description="洛必达法则需 0/0 或 ∞/∞ 型",
        domain="calculus",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"洛必达|l.hopital|0/0|∞/∞",
                description="洛必达法则",
            ),
        ),
        may_introduce=("0/0 或 ∞/∞ 型",),
        proof_obligations=(
            ProofObligation(
                description="确认是 0/0 或 ∞/∞ 未定式",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="limit_equivalent_infinitesimal",
        op=Op.COMPUTE_LIMIT,
        description="等价无穷小替换需极限存在",
        domain="calculus",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"等价无穷小|equivalent.*infinitesimal|~|≈",
                description="等价无穷小替换",
            ),
        ),
        may_introduce=("极限存在",),
        proof_obligations=(
            ProofObligation(
                description="确认等价无穷小替换条件",
                severity=ObligationSeverity.RECOMMENDED,
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="limit_basic",
        op=Op.COMPUTE_LIMIT,
        description="基本极限计算",
        domain="calculus",
        priority=5,
        confidence=0.90,
    ),
]


# ══════════════════════════════════════════════════════════════
# 3. 方程/不等式规则
# ══════════════════════════════════════════════════════════════

EQUATION_RULES: list[Rule] = [

    Rule(
        name="solve_multiply_both_sides",
        op=Op.SOLVE_EQUATION,
        description="方程两边乘以 x 需 x ≠ 0",
        domain="equation",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"两边乘|乘以|multiply",
                description="两边乘以变量",
            ),
        ),
        generated_constraints=("x ≠ 0",),
        may_lose=("x ≠ 0",),
        proof_obligations=(
            ProofObligation(
                description="讨论 x = 0 的情况",
                severity=ObligationSeverity.MANDATORY,
                related_constraint="x ≠ 0",
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="solve_sqrt_both_sides",
        op=Op.SOLVE_EQUATION,
        description="方程两边开方需讨论正负",
        domain="equation",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"开方|sqrt|√|平方根",
                description="两边开方",
            ),
        ),
        generated_subgoals=("需讨论正负",),
        proof_obligations=(
            ProofObligation(
                description="开方后需讨论正负两种情况",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.75,
    ),

    Rule(
        name="solve_abs_equation",
        op=Op.SOLVE_EQUATION,
        description="含绝对值方程需分类讨论",
        domain="equation",
        priority=9,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"\\||abs|绝对值",
                description="含绝对值方程",
            ),
        ),
        generated_subgoals=("分类讨论",),
        proof_obligations=(
            ProofObligation(
                description="绝对值方程需分类讨论",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.75,
    ),

    Rule(
        name="solve_parametric",
        op=Op.SOLVE_EQUATION,
        description="含参数方程需参数讨论",
        domain="equation",
        priority=8,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"参数|parametric|a>|a<",
                description="含参数方程",
            ),
        ),
        generated_subgoals=("参数讨论",),
        proof_obligations=(
            ProofObligation(
                description="含参数方程需讨论参数范围",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.70,
    ),

    Rule(
        name="solve_basic",
        op=Op.SOLVE_EQUATION,
        description="基本方程求解",
        domain="equation",
        priority=5,
        confidence=0.85,
    ),

    Rule(
        name="inequality_multiply_negative",
        op=Op.SOLVE_INEQUALITY,
        description="不等式两边乘以负数需反转方向",
        domain="inequality",
        priority=10,
        may_lose=("不等号方向反转",),
        proof_obligations=(
            ProofObligation(
                description="乘以负数时不等号方向需反转",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="inequality_parametric",
        op=Op.SOLVE_INEQUALITY,
        description="含参数不等式需参数讨论",
        domain="inequality",
        priority=8,
        preconditions=(
            Condition(
                kind=ConditionKind.EXPRESSION_MATCHES,
                pattern=r"参数|parametric",
                description="含参数不等式",
            ),
        ),
        generated_subgoals=("参数讨论",),
        proof_obligations=(
            ProofObligation(
                description="含参数不等式需讨论参数范围",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.70,
    ),

    Rule(
        name="inequality_basic",
        op=Op.SOLVE_INEQUALITY,
        description="基本不等式求解",
        domain="inequality",
        priority=5,
        confidence=0.85,
    ),
]


# ══════════════════════════════════════════════════════════════
# 4. 线性代数规则
# ══════════════════════════════════════════════════════════════

LINEAR_ALGEBRA_RULES: list[Rule] = [

    Rule(
        name="row_reduce_back_substitute",
        op=Op.ROW_REDUCE,
        description="行变换后需回代求解",
        domain="linear_algebra",
        priority=10,
        generated_subgoals=("回代求解",),
        proof_obligations=(
            ProofObligation(
                description="行变换后需回代求解",
                severity=ObligationSeverity.INFORMATIONAL,
            ),
        ),
        confidence=0.90,
    ),

    Rule(
        name="determinant_properties",
        op=Op.DETERMINANT,
        description="行列式计算",
        domain="linear_algebra",
        priority=10,
        confidence=0.90,
    ),
]


# ══════════════════════════════════════════════════════════════
# 5. 证明/逻辑规则
# ══════════════════════════════════════════════════════════════

LOGIC_RULES: list[Rule] = [

    Rule(
        name="classify_exhaustive",
        op=Op.CLASSIFY,
        description="分类讨论需覆盖所有情况",
        domain="logic",
        priority=10,
        generated_subgoals=("需覆盖所有情况", "各类互斥"),
        proof_obligations=(
            ProofObligation(
                description="分类讨论需覆盖所有情况",
                severity=ObligationSeverity.MANDATORY,
            ),
            ProofObligation(
                description="各类之间需互斥",
                severity=ObligationSeverity.RECOMMENDED,
            ),
        ),
        confidence=0.75,
    ),

    Rule(
        name="apply_theorem_conditions",
        op=Op.APPLY_THEOREM,
        description="应用定理需验证定理条件",
        domain="logic",
        priority=10,
        proof_obligations=(
            ProofObligation(
                description="验证定理的所有前提条件",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.80,
    ),

    Rule(
        name="induction_base_and_step",
        op=Op.INDUCTION_STEP,
        description="数学归纳法需验证基础步骤",
        domain="logic",
        priority=10,
        generated_subgoals=("验证 n=1 (基础步骤)",),
        proof_obligations=(
            ProofObligation(
                description="数学归纳法需验证基础步骤",
                severity=ObligationSeverity.MANDATORY,
            ),
        ),
        confidence=0.80,
    ),
]


# ══════════════════════════════════════════════════════════════
# 6. 汇总注册表
# ══════════════════════════════════════════════════════════════

ALL_RULES: list[Rule] = (
    ALGEBRA_RULES
    + CALCULUS_RULES
    + EQUATION_RULES
    + LINEAR_ALGEBRA_RULES
    + LOGIC_RULES
)


def build_registry() -> dict[Op, list[Rule]]:
    """构建按 Op 分类的规则注册表。"""
    registry: dict[Op, list[Rule]] = {}
    for rule in ALL_RULES:
        if rule.op not in registry:
            registry[rule.op] = []
        registry[rule.op].append(rule)
    for op in registry:
        registry[op].sort(key=lambda r: r.priority, reverse=True)
    return registry


RULES: dict[Op, list[Rule]] = build_registry()
