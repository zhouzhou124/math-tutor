"""algebra.py — 代数操作语义模板"""

from __future__ import annotations

from rendering.templates.op_templates import OpTemplate


def algebra_templates() -> list[OpTemplate]:
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
            category="algebra",
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
            category="algebra",
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
            category="algebra",
            color="#dc2626",
        ),
    ]
