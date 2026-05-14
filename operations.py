"""
Operation Taxonomy — 标准化数学推导操作类型

所有模块统一使用这些枚举值，避免自由文本导致的匹配混乱。

注意：此类已迁移到 common_enums.OperationType
此文件保留用于向后兼容。
"""

from common_enums import OperationType

# 向后兼容别名
Op = OperationType

# 保留别名映射供外部使用
_ALIASES = {
    # differentiate
    "diff": OperationType.DIFFERENTIATE,
    "derivative": OperationType.DIFFERENTIATE,
    "compute_derivative": OperationType.DIFFERENTIATE,
    "求导": OperationType.DIFFERENTIATE,
    "微分": OperationType.DIFFERENTIATE,
    "偏导": OperationType.PARTIAL_DIFF,
    # integrate
    "integral": OperationType.INTEGRATE,
    "积分": OperationType.INTEGRATE,
    # limit
    "limit": OperationType.LIMIT_COMPUTE,
    "极限": OperationType.LIMIT_COMPUTE,
    # taylor
    "泰勒": OperationType.TAYLOR_EXPANSION,
    # factor
    "因式分解": OperationType.FACTOR,
    "分解": OperationType.FACTOR,
    # simplify
    "化简": OperationType.SIMPLIFY,
    "整理": OperationType.SIMPLIFY,
    # solve
    "solve": OperationType.SOLVE_EQUATION,
    "求解": OperationType.SOLVE_EQUATION,
    "解方程": OperationType.SOLVE_EQUATION,
    "方程组": OperationType.SOLVE_SYSTEM,
    # matrix
    "矩阵": OperationType.MATRIX_OP,
    "行列式": OperationType.DETERMINANT,
    "det": OperationType.DETERMINANT,
    "行变换": OperationType.ROW_REDUCE,
    "特征值": OperationType.EIGEN_SOLVE,
    "特征向量": OperationType.EIGEN_SOLVE,
    # probability
    "概率": OperationType.PROBABILITY_CALC,
    "期望": OperationType.EXPECTATION,
    "方差": OperationType.EXPECTATION,
    "似然": OperationType.MLE_DERIVE,
    # theorem
    "定理": OperationType.APPLY_THEOREM,
    # final
    "答案": OperationType.FINAL_ANSWER,
    "最终": OperationType.FINAL_ANSWER,
    "所以": OperationType.FINAL_ANSWER,
}

# 关键词模式 → OperationType（用于从文本推断，按优先级排列）
KEYWORD_PATTERNS: list[tuple[str, OperationType]] = [
    # 高优先级：特定操作
    (r'求解.*方程|解方程|令.*=.*0|求.*的根', OperationType.SOLVE_EQUATION),
    (r'分部积分', OperationType.INTEGRATION_BY_PARTS),
    (r'换元积分|换元', OperationType.SUBSTITUTION),
    (r'泰勒展开|麦克劳林展开', OperationType.TAYLOR_EXPANSION),
    (r'幂级数展开', OperationType.SERIES_EXPANSION),
    (r'因式分解|分解因式', OperationType.FACTOR),
    (r'行列式|计算行列式', OperationType.DETERMINANT),
    (r'行变换|初等变换|行阶梯', OperationType.ROW_REDUCE),
    (r'特征值|特征向量', OperationType.EIGEN_SOLVE),
    (r'极大似然|似然函数|MLE', OperationType.MLE_DERIVE),
    (r'矩估计', OperationType.MOMENT_ESTIMATE),
    (r'假设检验', OperationType.HYPOTHESIS_TEST),
    (r'数学归纳法', OperationType.PROOF_BY_INDUCTION),
    (r'反证法', OperationType.PROOF_BY_CONTRADICTION),

    # 中优先级：通用操作
    (r'求导|导数|微分|偏导数|偏导', OperationType.DIFFERENTIATE),
    (r'f\'|\'\'|y\'|y\'\'|dy/dx|d/dx|\\frac{d}{dx}', OperationType.DIFFERENTIATE),
    (r'积分|∫|\\int', OperationType.INTEGRATE),
    (r'极限|lim|\\lim|趋近', OperationType.LIMIT_COMPUTE),
    (r'代入|把.*代入|将.*代入', OperationType.SUBSTITUTION),
    (r'化简|整理|约分', OperationType.SIMPLIFY),
    (r'展开', OperationType.SERIES_EXPANSION),
    (r'方程组|线性方程', OperationType.SOLVE_SYSTEM),
    (r'矩阵', OperationType.MATRIX_OP),
    (r'概率|P\(|条件概率', OperationType.PROBABILITY_CALC),
    (r'期望|方差|E\[|D\[|标准差', OperationType.EXPECTATION),
    (r'定理|根据.*定理|由.*得|应用.*定理', OperationType.APPLY_THEOREM),
    (r'级数|收敛|发散', OperationType.CONVERGENCE_TEST),

    # 低优先级：通用词汇
    (r'所以|故|因此|最终|答案', OperationType.FINAL_ANSWER),
]


def normalize_op(raw: str) -> OperationType:
    """将任意字符串规范化为 OperationType 枚举。"""
    if not raw:
        return OperationType.COMPUTE
    if isinstance(raw, OperationType):
        return raw
    # 直接匹配枚举值
    try:
        return OperationType(raw)
    except ValueError:
        pass
    # 别名匹配
    low = raw.strip().lower()
    if low in _ALIASES:
        return _ALIASES[low]
    return OperationType.COMPUTE


def infer_op_from_text(text: str) -> OperationType:
    """从步骤文本推断操作类型。"""
    import re
    for pattern, op in KEYWORD_PATTERNS:
        if re.search(pattern, text):
            return op
    return OperationType.COMPUTE


# 操作兼容性表：允许哪些操作互相匹配（图匹配时使用）
COMPATIBLE_OPS: dict[OperationType, set[OperationType]] = {
    OperationType.DIFFERENTIATE: {OperationType.DIFFERENTIATE, OperationType.PARTIAL_DIFF},
    OperationType.INTEGRATE: {OperationType.INTEGRATE, OperationType.INTEGRATION_BY_PARTS},
    OperationType.TAYLOR_EXPANSION: {OperationType.TAYLOR_EXPANSION, OperationType.SERIES_EXPANSION},
    OperationType.SERIES_EXPANSION: {OperationType.SERIES_EXPANSION, OperationType.TAYLOR_EXPANSION},
    OperationType.FACTOR: {OperationType.FACTOR, OperationType.SIMPLIFY},
    OperationType.SIMPLIFY: {OperationType.SIMPLIFY, OperationType.FACTOR},
    OperationType.SOLVE_EQUATION: {OperationType.SOLVE_EQUATION, OperationType.SOLVE_SYSTEM},
    OperationType.MATRIX_OP: {OperationType.MATRIX_OP, OperationType.ROW_REDUCE, OperationType.DETERMINANT},
    OperationType.EIGEN_SOLVE: {OperationType.EIGEN_SOLVE, OperationType.MATRIX_OP},
    OperationType.FINAL_ANSWER: {OperationType.FINAL_ANSWER},
}


def ops_compatible(op1: str, op2: str) -> bool:
    """判断两个操作是否兼容（允许匹配）。"""
    o1, o2 = normalize_op(op1), normalize_op(op2)
    if o1 == o2:
        return True
    compat = COMPATIBLE_OPS.get(o1, set())
    return o2 in compat
