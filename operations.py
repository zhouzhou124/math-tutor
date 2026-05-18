"""
Operation Taxonomy — 标准化数学推导操作类型

所有模块统一使用这些枚举值，避免自由文本导致的匹配混乱。
"""

from enum import Enum


class Op(str, Enum):
    """数学推导操作类型"""

    # ── 微积分 ──
    DIFFERENTIATE = "differentiate"
    INTEGRATE = "integrate"
    COMPUTE_LIMIT = "compute_limit"
    PARTIAL_DIFF = "partial_diff"

    # ── 代数变换 ──
    EXPAND = "expand"
    FACTOR = "factor"
    SIMPLIFY = "simplify"
    SUBSTITUTE = "substitute"
    COLLECT = "collect"         # 合并同类项
    CANCEL = "cancel"           # 约分

    # ── 方程 / 系统 ──
    SOLVE_EQUATION = "solve_equation"
    SOLVE_SYSTEM = "solve_system"
    SOLVE_INEQUALITY = "solve_inequality"

    # ── 线性代数 ──
    MATRIX_OP = "matrix_op"
    ROW_REDUCE = "row_reduce"
    EIGEN_SOLVE = "eigen_solve"
    DETERMINANT = "determinant"
    ORTHOGONALIZE = "orthogonalize"
    QUADRATIC_FORM = "quadratic_form"

    # ── 级数 ──
    EXPAND_SERIES = "expand_series"
    SUM_SERIES = "sum_series"
    CONVERGENCE_TEST = "convergence_test"

    # ── 概率统计 ──
    PROBABILITY_CALC = "probability_calc"
    EXPECTATION = "expectation"
    MLE_DERIVE = "mle_derive"
    MOMENT_ESTIMATE = "moment_estimate"
    HYPOTHESIS_TEST = "hypothesis_test"

    # ── 证明 / 逻辑 ──
    APPLY_THEOREM = "apply_theorem"
    CLASSIFY = "classify"
    INDUCTION_STEP = "induction_step"
    CONTRADICTION = "contradiction"

    # ── 通用 ──
    COMPUTE = "compute"         # 通用计算
    DEFINE = "define"           # 引入定义
    FINAL_ANSWER = "final_answer"

    # ── 几何 / 向量 ──
    CROSS_PRODUCT = "cross_product"
    DOT_PRODUCT = "dot_product"
    NORM = "norm"


# 别名映射：非标准名称 → 标准 Op
_ALIASES = {
    # differentiate
    "diff": Op.DIFFERENTIATE,
    "derivative": Op.DIFFERENTIATE,
    "compute_derivative": Op.DIFFERENTIATE,
    "求导": Op.DIFFERENTIATE,
    "微分": Op.DIFFERENTIATE,
    "偏导": Op.PARTIAL_DIFF,
    # integrate
    "integral": Op.INTEGRATE,
    "积分": Op.INTEGRATE,
    # limit
    "limit": Op.COMPUTE_LIMIT,
    "极限": Op.COMPUTE_LIMIT,
    # expand
    "展开": Op.EXPAND,
    "泰勒": Op.EXPAND_SERIES,
    # factor
    "因式分解": Op.FACTOR,
    "分解": Op.FACTOR,
    # simplify
    "化简": Op.SIMPLIFY,
    "整理": Op.SIMPLIFY,
    "合并": Op.COLLECT,
    "约分": Op.CANCEL,
    # solve
    "solve": Op.SOLVE_EQUATION,
    "求解": Op.SOLVE_EQUATION,
    "解方程": Op.SOLVE_EQUATION,
    "方程组": Op.SOLVE_SYSTEM,
    # matrix
    "矩阵": Op.MATRIX_OP,
    "行列式": Op.DETERMINANT,
    "det": Op.DETERMINANT,
    "行变换": Op.ROW_REDUCE,
    "特征值": Op.EIGEN_SOLVE,
    "特征向量": Op.EIGEN_SOLVE,
    # probability
    "概率": Op.PROBABILITY_CALC,
    "期望": Op.EXPECTATION,
    "方差": Op.EXPECTATION,
    "似然": Op.MLE_DERIVE,
    # theorem
    "定理": Op.APPLY_THEOREM,
    # classify
    "分类": Op.CLASSIFY,
    "讨论": Op.CLASSIFY,
    # final
    "答案": Op.FINAL_ANSWER,
    "最终": Op.FINAL_ANSWER,
    "所以": Op.FINAL_ANSWER,
}

# 关键词模式 → Op（用于从文本推断，按优先级排列）
KEYWORD_PATTERNS: list[tuple[str, Op]] = [
    # 高优先级：特定操作
    (r'求解.*方程|解方程|令.*=.*0|求.*的根', Op.SOLVE_EQUATION),
    (r'求解.*不等式|解不等式', Op.SOLVE_INEQUALITY),
    (r'分部积分', Op.INTEGRATE),
    (r'换元积分', Op.INTEGRATE),
    (r'泰勒展开|麦克劳林展开', Op.EXPAND_SERIES),
    (r'幂级数展开', Op.EXPAND_SERIES),
    (r'因式分解|分解因式', Op.FACTOR),
    (r'合并同类项', Op.COLLECT),
    (r'行列式|计算行列式', Op.DETERMINANT),
    (r'行变换|初等变换|行阶梯', Op.ROW_REDUCE),
    (r'特征值|特征向量|\\lambda', Op.EIGEN_SOLVE),
    (r'正交化|施密特', Op.ORTHOGONALIZE),
    (r'二次型|标准形', Op.QUADRATIC_FORM),
    (r'极大似然|似然函数|MLE', Op.MLE_DERIVE),
    (r'矩估计', Op.MOMENT_ESTIMATE),
    (r'假设检验', Op.HYPOTHESIS_TEST),
    (r'数学归纳法', Op.INDUCTION_STEP),
    (r'反证法', Op.CONTRADICTION),
    (r'分类讨论|分.*种情况|当.*时|情形', Op.CLASSIFY),
    
    # 中优先级：通用操作
    (r'求导|导数|微分|偏导数|偏导', Op.DIFFERENTIATE),
    (r'f\'|\'\'|y\'|y\'\'|dy/dx|d/dx|\\frac{d}{dx}', Op.DIFFERENTIATE),
    (r'积分|∫|\\int', Op.INTEGRATE),
    (r'极限|lim|\\lim|趋近', Op.COMPUTE_LIMIT),
    (r'代入|把.*代入|将.*代入', Op.SUBSTITUTE),
    (r'化简|整理|约分', Op.SIMPLIFY),
    (r'展开', Op.EXPAND),
    (r'方程组|线性方程', Op.SOLVE_SYSTEM),
    (r'矩阵', Op.MATRIX_OP),
    (r'概率|P\(|条件概率', Op.PROBABILITY_CALC),
    (r'期望|方差|E\[|D\[|标准差', Op.EXPECTATION),
    (r'定理|根据.*定理|由.*得|应用.*定理', Op.APPLY_THEOREM),
    (r'级数|收敛|发散', Op.CONVERGENCE_TEST),
    
    # 低优先级：通用词汇
    (r'所以|故|因此|最终|答案', Op.FINAL_ANSWER),
]


def normalize_op(raw: str) -> Op:
    """将任意字符串规范化为 Op 枚举。"""
    if not raw:
        return Op.COMPUTE
    if isinstance(raw, Op):
        return raw
    # 直接匹配枚举值
    try:
        return Op(raw)
    except ValueError:
        pass
    # 别名匹配
    low = raw.strip().lower()
    if low in _ALIASES:
        return _ALIASES[low]
    return Op.COMPUTE


def infer_op_from_text(text: str) -> Op:
    """从步骤文本推断操作类型。"""
    import re
    for pattern, op in KEYWORD_PATTERNS:
        if re.search(pattern, text):
            return op
    return Op.COMPUTE


# 操作兼容性表：允许哪些操作互相匹配（图匹配时使用）
COMPATIBLE_OPS: dict[Op, set[Op]] = {
    Op.DIFFERENTIATE: {Op.DIFFERENTIATE, Op.PARTIAL_DIFF},
    Op.INTEGRATE: {Op.INTEGRATE},
    Op.EXPAND: {Op.EXPAND, Op.EXPAND_SERIES, Op.SIMPLIFY},
    Op.FACTOR: {Op.FACTOR, Op.SIMPLIFY},
    Op.SIMPLIFY: {Op.SIMPLIFY, Op.EXPAND, Op.FACTOR, Op.COLLECT, Op.CANCEL},
    Op.SOLVE_EQUATION: {Op.SOLVE_EQUATION, Op.SOLVE_SYSTEM},
    Op.MATRIX_OP: {Op.MATRIX_OP, Op.ROW_REDUCE, Op.DETERMINANT},
    Op.EIGEN_SOLVE: {Op.EIGEN_SOLVE, Op.MATRIX_OP},
    Op.FINAL_ANSWER: {Op.FINAL_ANSWER},
}


def ops_compatible(op1: str, op2: str) -> bool:
    """判断两个操作是否兼容（允许匹配）。"""
    o1, o2 = normalize_op(op1), normalize_op(op2)
    if o1 == o2:
        return True
    compat = COMPATIBLE_OPS.get(o1, set())
    return o2 in compat


_OP_DISPLAY_CN: dict[Op, str] = {
    Op.DIFFERENTIATE: "求导",
    Op.PARTIAL_DIFF: "偏导数",
    Op.INTEGRATE: "积分",
    Op.COMPUTE_LIMIT: "求极限",
    Op.EXPAND: "展开",
    Op.FACTOR: "因式分解",
    Op.SIMPLIFY: "化简",
    Op.SUBSTITUTE: "代换/换元",
    Op.COLLECT: "合并同类项",
    Op.CANCEL: "约分",
    Op.SOLVE_EQUATION: "解方程",
    Op.SOLVE_SYSTEM: "解方程组",
    Op.SOLVE_INEQUALITY: "解不等式",
    Op.MATRIX_OP: "矩阵运算",
    Op.ROW_REDUCE: "行变换",
    Op.EIGEN_SOLVE: "特征值/特征向量",
    Op.DETERMINANT: "行列式计算",
    Op.ORTHOGONALIZE: "正交化",
    Op.QUADRATIC_FORM: "二次型标准化",
    Op.EXPAND_SERIES: "级数展开",
    Op.SUM_SERIES: "级数求和",
    Op.CONVERGENCE_TEST: "收敛性判别",
    Op.PROBABILITY_CALC: "概率计算",
    Op.EXPECTATION: "期望/方差",
    Op.MLE_DERIVE: "极大似然推导",
    Op.MOMENT_ESTIMATE: "矩估计",
    Op.HYPOTHESIS_TEST: "假设检验",
    Op.APPLY_THEOREM: "应用定理",
    Op.CLASSIFY: "分类讨论",
    Op.INDUCTION_STEP: "数学归纳法",
    Op.CONTRADICTION: "反证法",
    Op.COMPUTE: "计算",
    Op.DEFINE: "引入定义",
    Op.FINAL_ANSWER: "最终答案",
    Op.CROSS_PRODUCT: "叉积",
    Op.DOT_PRODUCT: "点积",
    Op.NORM: "范数",
}


def op_display_cn(op: str | Op) -> str:
    """操作类型 → 中文名称（统一入口，消除全局重复定义）"""
    normalized = normalize_op(op)
    return _OP_DISPLAY_CN.get(normalized, normalized.value if isinstance(normalized, Op) else str(op))

