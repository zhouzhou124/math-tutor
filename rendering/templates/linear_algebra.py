"""linear_algebra.py — 线性代数操作语义模板"""

from __future__ import annotations

from rendering.templates.op_templates import OpTemplate


def linear_algebra_templates() -> list[OpTemplate]:
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
            category="linalg",
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
            category="linalg",
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
            category="linalg",
            color="#2563eb",
        ),
    ]
