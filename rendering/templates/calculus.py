"""calculus.py — 微积分操作语义模板"""

from __future__ import annotations

from rendering.templates.op_templates import OpTemplate


def calculus_templates() -> list[OpTemplate]:
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
            category="calculus",
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
            category="calculus",
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
            category="calculus",
            color="#0891b2",
        ),
    ]
