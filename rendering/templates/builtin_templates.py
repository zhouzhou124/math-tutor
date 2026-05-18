"""
Builtin Templates — 内置操作语义模板库

═══════════════════════════════════════════════════════════════
覆盖范围
═══════════════════════════════════════════════════════════════

  微积分 (4):  differentiate, integrate, compute_limit, partial_diff
  代数变换 (6): expand, factor, simplify, substitute, collect, cancel
  方程/系统 (3): solve_equation, solve_system, solve_inequality
  线性代数 (6): matrix_op, row_reduce, eigen_solve, determinant, orthogonalize, quadratic_form
  级数 (3):    expand_series, sum_series, convergence_test
  概率统计 (5): probability_calc, expectation, mle_derive, moment_estimate, hypothesis_test
  证明/逻辑 (4): apply_theorem, classify, induction_step, contradiction
  通用 (3):    compute, define, final_answer
  几何/向量 (3): cross_product, dot_product, norm

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from rendering.templates.op_templates import OpTemplate, TemplateRegistry, template_registry


def _calculus_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="differentiate",
            title="求导",
            explanation="对 {input} 关于 {variable} 求导",
            constraints=[
                "函数 {input} 在该点必须可导",
                "需确认 {variable} 是连续变量",
            ],
            error_hints=[
                "求导时漏用了链式法则",
                "复合函数求导需使用链式法则: 外层导数 × 内层导数",
                "乘积求导应使用乘法法则: (uv)' = u'v + uv'",
                "商的求导应使用除法法则: (u/v)' = (u'v - uv') / v²",
            ],
            latex_hint="\\frac{{d}}{{d{variable}}} {input} = {output}",
            category="calculus",
            color="#d97706",
        ),
        OpTemplate(
            op_key="integrate",
            title="积分",
            explanation="对 {input} 关于 {variable} 求不定积分",
            constraints=[
                "被积函数 {input} 在积分区间上必须可积",
                "不定积分结果需加常数 C",
            ],
            error_hints=[
                "不定积分漏加常数 C",
                "换元积分时未同时更换积分上下限",
                "分部积分时 u 和 dv 的选择不当",
                "有理函数积分应先做部分分式分解",
            ],
            latex_hint="\\int {input} \\, d{variable} = {output} + C",
            category="calculus",
            color="#d97706",
        ),
        OpTemplate(
            op_key="compute_limit",
            title="求极限",
            explanation="求 {input} 当 {variable} 趋近于 {point} 时的极限",
            constraints=[
                "需确认极限存在（左极限 = 右极限）",
            ],
            error_hints=[
                "0/0 型未定式应使用洛必达法则或等价无穷小",
                "∞/∞ 型未定式同样可使用洛必达法则",
                "重要极限: lim(x→0) sin(x)/x = 1",
                "注意区分 lim(x→0⁺) 和 lim(x→0⁻)",
            ],
            latex_hint="\\lim_{{{variable} \\to {point}}} {input} = {output}",
            category="calculus",
            color="#d97706",
        ),
        OpTemplate(
            op_key="partial_diff",
            title="偏导数",
            explanation="对 {input} 关于 {variable} 求偏导数（其余变量视为常数）",
            constraints=[
                "函数 {input} 关于 {variable} 的偏导数必须存在",
                "求偏导时其余变量视为常数",
            ],
            error_hints=[
                "偏导数求导时未将其余变量视为常数",
                "高阶混合偏导数在连续条件下与求导顺序无关",
            ],
            latex_hint="\\frac{{\\partial}}{{\\partial {variable}}} {input} = {output}",
            category="calculus",
            color="#d97706",
        ),
    ]


def _algebra_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="expand",
            title="展开",
            explanation="将 {input} 展开（去括号）",
            constraints=[],
            error_hints=[
                "展开时符号错误: 注意负号分配",
                "二项式展开 (a+b)ⁿ 应使用二项式定理",
                "完全平方展开: (a±b)² = a² ± 2ab + b²",
            ],
            latex_hint="{input} = {output}",
            category="algebra",
            color="#059669",
        ),
        OpTemplate(
            op_key="factor",
            title="因式分解",
            explanation="将 {input} 分解为因式的乘积",
            constraints=[],
            error_hints=[
                "因式分解不彻底: 检查是否还能继续分解",
                "二次三项式 ax²+bx+c 可用十字相乘法或求根公式",
                "注意提取公因式",
                "a²-b² = (a+b)(a-b) 差平方公式",
            ],
            latex_hint="{input} = {output}",
            category="algebra",
            color="#059669",
        ),
        OpTemplate(
            op_key="simplify",
            title="化简",
            explanation="将 {input} 化简为最简形式",
            constraints=[],
            error_hints=[
                "化简不彻底: 检查是否还能约分或合并",
                "根式化简需将根号内的完全平方因子提出",
                "分式化简需找最简公分母",
            ],
            latex_hint="{input} = {output}",
            category="algebra",
            color="#059669",
        ),
        OpTemplate(
            op_key="substitute",
            title="代入",
            explanation="将 {point} 代入 {input}",
            constraints=[
                "代入值必须在函数定义域内",
            ],
            error_hints=[
                "代入时符号错误: 注意负数和分数的代入",
                "代入前需确认代入点在定义域内",
                "分段函数需判断代入点属于哪一段",
            ],
            latex_hint="{input}|_{{{point}}} = {output}",
            category="algebra",
            color="#7c3aed",
        ),
        OpTemplate(
            op_key="collect",
            title="合并同类项",
            explanation="将 {input} 中的同类项合并",
            constraints=[],
            error_hints=[
                "合并时系数计算错误",
                "注意只有同类项才能合并（相同字母相同指数）",
            ],
            latex_hint="{input} = {output}",
            category="algebra",
            color="#059669",
        ),
        OpTemplate(
            op_key="cancel",
            title="约分",
            explanation="约去分子分母的公因子 {factor}",
            constraints=[
                "需满足 {factor} ≠ 0",
                "约分前需确认公因子不为零",
            ],
            error_hints=[
                "约分时遗漏非零条件: {factor} ≠ 0",
                "不能直接约去可能为零的因子",
                "约分后需补充条件: {factor} ≠ 0",
            ],
            latex_hint="\\frac{{{input}}}{{{factor}}} = \\frac{{{output}}}{{1}}",
            category="algebra",
            color="#059669",
        ),
    ]


def _equation_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="solve_equation",
            title="解方程",
            explanation="求解方程 {input}",
            constraints=[
                "需验证求得的解是否满足原方程",
            ],
            error_hints=[
                "解方程后未代入验证",
                "去分母时漏乘了某些项",
                "平方操作可能引入增根，需检验",
                "一元二次方程优先考虑因式分解，其次用求根公式",
            ],
            latex_hint="{input} \\implies {output}",
            category="equation",
            color="#dc2626",
        ),
        OpTemplate(
            op_key="solve_system",
            title="解方程组",
            explanation="求解方程组 {input}",
            constraints=[
                "需验证解是否满足方程组中每个方程",
            ],
            error_hints=[
                "消元时系数计算错误",
                "需验证解满足所有方程",
                "注意方程组可能无解或有无穷多解",
            ],
            latex_hint="{input} \\implies {output}",
            category="equation",
            color="#dc2626",
        ),
        OpTemplate(
            op_key="solve_inequality",
            title="解不等式",
            explanation="求解不等式 {input}",
            constraints=[
                "不等式两边乘以负数时不等号方向需反转",
                "分母含变量时需讨论分母正负",
            ],
            error_hints=[
                "乘以负数时未反转不等号方向",
                "分式不等式应移项通分，不能直接去分母",
                "绝对值不等式需分情况讨论",
            ],
            latex_hint="{input} \\implies {output}",
            category="equation",
            color="#dc2626",
        ),
    ]


def _linalg_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="matrix_op",
            title="矩阵运算",
            explanation="对矩阵 {input} 进行运算",
            constraints=[
                "矩阵运算需确认维度匹配",
            ],
            error_hints=[
                "矩阵乘法不满足交换律: AB ≠ BA",
                "矩阵加法要求同型矩阵",
                "逆矩阵存在的条件: 行列式不为零",
            ],
            latex_hint="{input} = {output}",
            category="linalg",
            color="#2563eb",
        ),
        OpTemplate(
            op_key="row_reduce",
            title="初等行变换",
            explanation="对矩阵 {input} 进行初等行变换化为行阶梯形",
            constraints=[
                "行变换不改变矩阵的秩",
                "行变换对应左乘初等矩阵",
            ],
            error_hints=[
                "行变换时某一行计算错误",
                "注意行变换的三种操作: 交换、倍乘、倍加",
                "化简目标是最简行阶梯形（主元上方也消为零）",
            ],
            latex_hint="{input} \\xrightarrow{{\\text{{行变换}}}} {output}",
            category="linalg",
            color="#2563eb",
        ),
        OpTemplate(
            op_key="eigen_solve",
            title="特征值求解",
            explanation="求矩阵 {input} 的特征值和特征向量",
            constraints=[
                "需先求解特征方程 det(A - λI) = 0",
                "不同特征值对应的特征向量线性无关",
            ],
            error_hints=[
                "特征方程展开时计算错误",
                "特征向量需代入 (A-λI)x=0 求解",
                "重特征值的代数重数 ≥ 几何重数",
            ],
            latex_hint="\\det({input} - \\lambda I) = 0 \\implies {output}",
            category="linalg",
            color="#2563eb",
        ),
        OpTemplate(
            op_key="determinant",
            title="行列式",
            explanation="计算 {input} 的行列式",
            constraints=[
                "只有方阵才有行列式",
            ],
            error_hints=[
                "行列式展开时符号错误: 注意 (-1)^(i+j)",
                "行列式的性质: 行列互换值不变、两行相同值为零",
                "上三角/下三角矩阵的行列式等于主对角线元素之积",
            ],
            latex_hint="\\det({input}) = {output}",
            category="linalg",
            color="#2563eb",
        ),
        OpTemplate(
            op_key="orthogonalize",
            title="正交化",
            explanation="对向量组 {input} 进行施密特正交化",
            constraints=[
                "输入向量组必须线性无关",
            ],
            error_hints=[
                "施密特正交化公式: bₖ = aₖ - Σ(aₖ·bᵢ/bᵢ·bᵢ)bᵢ",
                "正交化后需单位化才是标准正交基",
                "正交化过程是逐步进行的，顺序影响结果",
            ],
            latex_hint="\\text{{Schmidt}}({input}) = {output}",
            category="linalg",
            color="#2563eb",
        ),
        OpTemplate(
            op_key="quadratic_form",
            title="二次型",
            explanation="将二次型 {input} 化为标准形",
            constraints=[
                "正交变换保持二次型的几何性质",
            ],
            error_hints=[
                "化标准形可用配方法或正交变换法",
                "正交变换法: 求特征值和特征向量",
                "规范形中正负惯性指数不变",
            ],
            latex_hint="{input} \\xrightarrow{{\\text{{正交变换}}}} {output}",
            category="linalg",
            color="#2563eb",
        ),
    ]


def _series_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="expand_series",
            title="级数展开",
            explanation="将 {input} 在 {point} 处展开为泰勒级数",
            constraints=[
                "函数在该点必须无穷次可导",
                "需判断收敛域",
            ],
            error_hints=[
                "泰勒展开的余项不能忽略（除非在收敛域内）",
                "常见展开: eˣ = Σxⁿ/n!, sin(x) = Σ(-1)ⁿx²ⁿ⁺¹/(2n+1)!",
                "麦克劳林级数是 x=0 处的泰勒展开",
            ],
            latex_hint="{input} = {output}",
            category="series",
            color="#0891b2",
        ),
        OpTemplate(
            op_key="sum_series",
            title="级数求和",
            explanation="求级数 {input} 的和",
            constraints=[
                "需先判断级数收敛",
            ],
            error_hints=[
                "求和前需判断级数是否收敛",
                "等比级数: Σarⁿ = a/(1-r) (|r|<1)",
                "裂项相消法适用于分式型级数",
            ],
            latex_hint="\\sum {input} = {output}",
            category="series",
            color="#0891b2",
        ),
        OpTemplate(
            op_key="convergence_test",
            title="收敛性判断",
            explanation="判断级数 {input} 的收敛性",
            constraints=[],
            error_hints=[
                "比值判别法: lim|aₙ₊₁/aₙ| < 1 则收敛",
                "比较判别法: 与已知收敛/发散级数比较",
                "交错级数用莱布尼茨判别法",
                "通项不趋于零则级数必发散",
            ],
            latex_hint="\\sum {input}: \\text{{收敛性}} = {output}",
            category="series",
            color="#0891b2",
        ),
    ]


def _probability_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="probability_calc",
            title="概率计算",
            explanation="计算 {input} 的概率",
            constraints=[
                "概率值必须在 [0, 1] 范围内",
            ],
            error_hints=[
                "互斥事件: P(A∪B) = P(A) + P(B)",
                "独立事件: P(AB) = P(A)·P(B)",
                "条件概率: P(A|B) = P(AB)/P(B)",
                "全概率公式和贝叶斯公式的应用场景不同",
            ],
            latex_hint="P({input}) = {output}",
            category="probability",
            color="#be185d",
        ),
        OpTemplate(
            op_key="expectation",
            title="期望/方差",
            explanation="计算 {input} 的期望或方差",
            constraints=[
                "期望存在要求级数/积分收敛",
            ],
            error_hints=[
                "E(aX+b) = aE(X)+b, D(aX+b) = a²D(X)",
                "方差 D(X) = E(X²) - [E(X)]²",
                "独立随机变量: D(X+Y) = D(X) + D(Y)",
            ],
            latex_hint="E({input}) = {output}",
            category="probability",
            color="#be185d",
        ),
        OpTemplate(
            op_key="mle_derive",
            title="极大似然估计",
            explanation="对 {input} 求极大似然估计",
            constraints=[
                "似然函数必须正确构建",
                "需验证求得的确实是极大值",
            ],
            error_hints=[
                "似然函数 L(θ) = Πf(xᵢ;θ)，取对数简化计算",
                "对数似然求导令其为零解出 θ̂",
                "需验证二阶导数小于零确认是极大值",
            ],
            latex_hint="\\hat{{\\theta}} = \\arg\\max L({input}) = {output}",
            category="probability",
            color="#be185d",
        ),
        OpTemplate(
            op_key="moment_estimate",
            title="矩估计",
            explanation="对 {input} 用矩法求参数估计",
            constraints=[
                "样本矩必须存在",
            ],
            error_hints=[
                "矩估计: 用样本矩代替总体矩",
                "k 个参数需要 k 个矩方程",
                "矩估计可能不如极大似然估计有效",
            ],
            latex_hint="\\hat{{\\theta}}_{{\\text{{矩}}}}({input}) = {output}",
            category="probability",
            color="#be185d",
        ),
        OpTemplate(
            op_key="hypothesis_test",
            title="假设检验",
            explanation="对 {input} 进行假设检验",
            constraints=[
                "需明确原假设 H₀ 和备择假设 H₁",
                "需选择合适的显著性水平 α",
            ],
            error_hints=[
                "原假设和备择假设是互补的",
                "Z 检验: 大样本或总体方差已知",
                "t 检验: 小样本且总体方差未知",
                "χ² 检验: 拟合优度或独立性检验",
            ],
            latex_hint="H_0: {input} \\implies {output}",
            category="probability",
            color="#be185d",
        ),
    ]


def _proof_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="apply_theorem",
            title="应用定理",
            explanation="应用{theorem}处理 {input}",
            constraints=[
                "需验证{theorem}的前提条件是否满足",
                "定理的适用范围需确认",
            ],
            error_hints=[
                "应用定理前未验证前提条件",
                "定理的适用范围不满足",
                "注意定理的严格表述，避免误用",
            ],
            latex_hint="\\text{{由{theorem}}}: {input} \\implies {output}",
            category="proof",
            color="#7c3aed",
        ),
        OpTemplate(
            op_key="classify",
            title="分类讨论",
            explanation="对 {input} 进行分类讨论",
            constraints=[
                "分类必须不重不漏",
                "每种情况需独立推导",
            ],
            error_hints=[
                "分类不完整: 遗漏了某些情况",
                "分类有重叠: 某些情况被重复计算",
                "各分类的结论需最终合并",
            ],
            latex_hint="\\text{{分类讨论}}: {input}",
            category="proof",
            color="#6b7280",
        ),
        OpTemplate(
            op_key="induction_step",
            title="数学归纳法",
            explanation="用数学归纳法证明 {input}",
            constraints=[
                "需验证基础情形 (n=1 或 n=0)",
                "归纳假设到归纳步骤的推导必须严密",
            ],
            error_hints=[
                "归纳法需先验证基础情形",
                "归纳步骤中必须使用归纳假设",
                "归纳步骤的推导不能跳步",
                "强归纳法: 假设对所有 k<n 成立",
            ],
            latex_hint="\\text{{归纳法}}: {input}",
            category="proof",
            color="#0891b2",
        ),
        OpTemplate(
            op_key="contradiction",
            title="反证法",
            explanation="用反证法证明 {input}，假设结论不成立推出矛盾",
            constraints=[
                "需明确反证假设",
                "推出的矛盾必须是逻辑矛盾",
            ],
            error_hints=[
                "反证假设必须是否定原结论",
                "推出的矛盾需与已知条件或公理矛盾",
                "反证法的关键是找到矛盾点",
            ],
            latex_hint="\\text{{反证}}: \\neg({input}) \\implies \\bot",
            category="proof",
            color="#0891b2",
        ),
    ]


def _general_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="compute",
            title="计算",
            explanation="计算 {input}",
            constraints=[],
            error_hints=[
                "计算过程需逐步验证",
                "注意运算顺序: 先乘除后加减",
                "注意符号: 负负得正",
            ],
            latex_hint="{input} = {output}",
            category="general",
            color="#dc2626",
        ),
        OpTemplate(
            op_key="define",
            title="引入定义",
            explanation="引入 {input} 的定义",
            constraints=[],
            error_hints=[
                "定义必须清晰无歧义",
                "引入的符号需在后续步骤中一致使用",
            ],
            latex_hint="\\text{{令}}\\; {input}",
            category="general",
            color="#6b7280",
        ),
        OpTemplate(
            op_key="final_answer",
            title="最终答案",
            explanation="得出最终结果: {input}",
            constraints=[
                "最终答案需回验",
            ],
            error_hints=[
                "最终答案需代入原题验证",
                "注意答案的单位和精度",
                "多解情况需全部列出",
            ],
            latex_hint="\\boxed{{{output}}}",
            category="general",
            color="#059669",
        ),
    ]


def _geometry_templates() -> list[OpTemplate]:
    return [
        OpTemplate(
            op_key="cross_product",
            title="叉积",
            explanation="计算向量 {input} 的叉积",
            constraints=[
                "叉积仅适用于三维向量",
                "叉积结果垂直于两个输入向量",
            ],
            error_hints=[
                "叉积不满足交换律: a×b = -(b×a)",
                "叉积的行列式展开需注意符号",
            ],
            latex_hint="{input} \\times = {output}",
            category="geometry",
            color="#2563eb",
        ),
        OpTemplate(
            op_key="dot_product",
            title="点积",
            explanation="计算向量 {input} 的点积（内积）",
            constraints=[],
            error_hints=[
                "点积结果为标量",
                "a·b = |a||b|cosθ",
                "点积为零 ⟺ 两向量正交",
            ],
            latex_hint="{input} \\cdot = {output}",
            category="geometry",
            color="#2563eb",
        ),
        OpTemplate(
            op_key="norm",
            title="范数",
            explanation="计算 {input} 的范数（模长）",
            constraints=[
                "范数必须非负",
            ],
            error_hints=[
                "L² 范数: ||v|| = √(v₁² + v₂² + ...)",
                "范数为零 ⟺ 向量为零向量",
            ],
            latex_hint="\\|{input}\\| = {output}",
            category="geometry",
            color="#2563eb",
        ),
    ]


def register_all_builtins(registry: TemplateRegistry = None) -> None:
    """
    注册所有内置模板到全局注册表。

    在 rendering/templates/__init__.py 中自动调用。
    """
    target = registry or template_registry

    all_templates = (
        _calculus_templates()
        + _algebra_templates()
        + _equation_templates()
        + _linalg_templates()
        + _series_templates()
        + _probability_templates()
        + _proof_templates()
        + _general_templates()
        + _geometry_templates()
    )

    target.register_many(all_templates)
