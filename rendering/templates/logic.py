"""logic.py — 证明/逻辑操作语义模板"""

from __future__ import annotations

from rendering.templates.op_templates import OpTemplate


def logic_templates() -> list[OpTemplate]:
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
