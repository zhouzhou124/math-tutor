"""semantic_layer.py — 语义层 (Semantic Layer)

这是系统中最重要的层，负责理解数学的语义。

核心职责：
  1. 操作语义：理解每个数学操作的含义、输入输出、适用条件
  2. 知识点语义：理解知识点的关系、层次、依赖
  3. 语义推理：判断两个表达式是否语义等价
  4. 错误检测：识别学生作答中的常见错误类型

架构：
  ┌─────────────────────────────────────────────────────────────┐
  │                     Semantic Layer                             │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │  │ OperationSem│  │KnowledgeSem  │  │ SemanticMatch │     │
  │  │   操作语义   │  │   知识点语义  │  │   语义匹配    │     │
  │  └──────────────┘  └──────────────┘  └──────────────┘     │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple, Any
from enum import Enum
from operations import Op, normalize_op


# ═══════════════════════════════════════════════
# 操作语义定义
# ═══════════════════════════════════════════════

@dataclass
class OperationSemantics:
    """
    操作语义 — 理解每个数学操作的完整语义

    Attributes:
        op: 操作类型枚举
        name_cn: 中文名称
        name_en: 英文名称
        description: 语义描述
        input_type: 输入类型（如 "表达式"、"方程"、"矩阵"）
        output_type: 输出类型
        prerequisites: 前置知识/操作
        common_errors: 常见错误类型
        examples: 使用示例
    """
    op: Op
    name_cn: str
    name_en: str
    description: str
    input_type: str = "表达式"
    output_type: str = "表达式"
    prerequisites: List[str] = field(default_factory=list)
    common_errors: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


# 完整的操作语义库
OPERATION_SEMANTICS: Dict[Op, OperationSemantics] = {
    # ═══════════════════════════════════════════
    # 微积分
    # ═══════════════════════════════════════════
    Op.DIFFERENTIATE: OperationSemantics(
        op=Op.DIFFERENTIATE,
        name_cn="求导",
        name_en="Differentiation",
        description="计算函数的导数，描述函数的瞬时变化率",
        input_type="函数 f(x)",
        output_type="导函数 f'(x)",
        prerequisites=["极限概念", "函数基础"],
        common_errors=[
            "复合函数求导漏掉内层导数",
            "指数函数求导公式错误",
            "链式法则应用不当",
        ],
        examples=[
            "d/dx(x^2) = 2x",
            "d/dx(sin(x)) = cos(x)",
        ],
    ),

    Op.INTEGRATE: OperationSemantics(
        op=Op.INTEGRATE,
        name_cn="积分",
        name_en="Integration",
        description="计算函数的原函数或定积分，求解曲线下的面积",
        input_type="函数 f(x)",
        output_type="原函数 F(x) 或定积分值",
        prerequisites=["导数公式", "基本积分表"],
        common_errors=[
            "积分常数遗漏",
            "换元后忘记还原变量",
            "分部积分公式应用顺序错误",
        ],
        examples=[
            "∫x dx = x²/2 + C",
            "∫sin(x) dx = -cos(x) + C",
        ],
    ),

    Op.COMPUTE_LIMIT: OperationSemantics(
        op=Op.COMPUTE_LIMIT,
        name_cn="求极限",
        name_en="Limit Computation",
        description="计算函数的极限值，分析函数趋近于某点时的行为",
        input_type="函数和趋近点",
        output_type="极限值",
        prerequisites=["数列/函数基础", "无穷小概念"],
        common_errors=[
            "0/0 型直接代入",
            "忽略左右极限",
            "无穷减无穷型处理不当",
        ],
        examples=[
            "lim(x→0) sin(x)/x = 1",
            "lim(x→∞) (1+1/x)^x = e",
        ],
    ),

    Op.PARTIAL_DIFF: OperationSemantics(
        op=Op.PARTIAL_DIFF,
        name_cn="偏导数",
        name_en="Partial Differentiation",
        description="多元函数对其中一个变量求导，将其他变量视为常数",
        input_type="多元函数 f(x,y,...)",
        output_type="偏导函数 ∂f/∂x",
        prerequisites=["一元导数", "多元函数概念"],
        common_errors=[
            "对 x 求偏导时漏掉 y 的系数",
            "混淆偏导符号 ∂ 和 d",
        ],
        examples=[
            "∂/∂x(x²y) = 2xy",
        ],
    ),

    # ═══════════════════════════════════════════
    # 代数变换
    # ═══════════════════════════════════════════
    Op.EXPAND: OperationSemantics(
        op=Op.EXPAND,
        name_cn="展开",
        name_en="Algebraic Expansion",
        description="将括号内的表达式按照分配律展开",
        input_type="带括号的表达式 (a+b)(c+d)",
        output_type="展开后的多项式",
        prerequisites=["分配律", "幂的运算法则"],
        common_errors=[
            "符号处理错误",
            "漏乘某些项",
        ],
        examples=[
            "(x+1)² = x² + 2x + 1",
            "(a+b)(a-b) = a² - b²",
        ],
    ),

    Op.EXPAND_SERIES: OperationSemantics(
        op=Op.EXPAND_SERIES,
        name_cn="级数展开",
        name_en="Series Expansion",
        description="将函数展开为无穷级数（泰勒级数、麦克劳林级数）",
        input_type="函数 f(x) 和展开点",
        output_type="无穷级数",
        prerequisites=["导数", "极限概念"],
        common_errors=[
            "泰勒公式记忆错误",
            "忽略收敛域",
            "高阶项系数计算错误",
        ],
        examples=[
            "e^x = 1 + x + x²/2! + x³/3! + ...",
            "sin(x) = x - x³/3! + x⁵/5! - ...",
        ],
    ),

    Op.FACTOR: OperationSemantics(
        op=Op.FACTOR,
        name_cn="因式分解",
        name_en="Factorization",
        description="将多项式分解为若干个因式的乘积",
        input_type="多项式",
        output_type="因式乘积形式",
        prerequisites=["整式乘法", "根与系数关系"],
        common_errors=[
            "提取公因式不全",
            "公式误用",
        ],
        examples=[
            "x² - 1 = (x+1)(x-1)",
            "x² + 5x + 6 = (x+2)(x+3)",
        ],
    ),

    Op.SIMPLIFY: OperationSemantics(
        op=Op.SIMPLIFY,
        name_cn="化简",
        name_en="Simplification",
        description="通过合并同类项、約分等手段简化表达式",
        input_type="复杂表达式",
        output_type="最简形式",
        prerequisites=["同类项概念", "基本运算法则"],
        common_errors=[
            "不同类项错误合并",
            "約分不当",
        ],
        examples=[
            "(x² + x) / x = x + 1",
            "√18 = 3√2",
        ],
    ),

    Op.SUBSTITUTE: OperationSemantics(
        op=Op.SUBSTITUTE,
        name_cn="代入",
        name_en="Substitution",
        description="将变量替换为具体数值或表达式",
        input_type="表达式和替换规则",
        output_type="替换后的结果",
        prerequisites=["代数基础"],
        common_errors=[
            "代入顺序错误",
            "漏掉括号导致运算顺序错误",
        ],
        examples=[
            "f(x) = x², f(2) = 4",
            "将 x = 1 代入 2x + 3 = 5",
        ],
    ),

    Op.COLLECT: OperationSemantics(
        op=Op.COLLECT,
        name_cn="合并同类项",
        name_en="Collect Like Terms",
        description="将表达式中具有相同变量及其指数的项合并",
        input_type="多项式",
        output_type="合并后的多项式",
        prerequisites=["单项式概念"],
        common_errors=[
            "指数不同的项误认为同类项",
            "系数运算错误",
        ],
    ),

    Op.CANCEL: OperationSemantics(
        op=Op.CANCEL,
        name_cn="约分",
        name_en="Cancellation",
        description="在分子分母中消去公共因子",
        input_type="分式",
        output_type="约分后的分式",
        prerequisites=["因式分解", "分数基本性质"],
        common_errors=[
            "分子分母分别约分",
            "漏掉不能约分的情况",
        ],
        examples=[
            "(x²-1)/(x-1) = x+1",
        ],
    ),

    # ═══════════════════════════════════════════
    # 方程求解
    # ═══════════════════════════════════════════
    Op.SOLVE_EQUATION: OperationSemantics(
        op=Op.SOLVE_EQUATION,
        name_cn="解方程",
        name_en="Equation Solving",
        description="求出使方程成立的变量值",
        input_type="方程",
        output_type="解或解集",
        prerequisites=["等式性质", "代数运算"],
        common_errors=[
            "移项不变号",
            "方程两边除以零",
            "忽略增根",
        ],
        examples=[
            "x² - 4 = 0 → x = ±2",
        ],
    ),

    Op.SOLVE_SYSTEM: OperationSemantics(
        op=Op.SOLVE_SYSTEM,
        name_cn="解方程组",
        name_en="System Solving",
        description="求出同时满足多个方程的变量值",
        input_type="方程组",
        output_type="变量解集",
        prerequisites=["代入法", "消元法"],
        common_errors=[
            "消元不彻底",
            "代入错误",
        ],
        examples=[
            "x+y=2, x-y=0 → x=1, y=1",
        ],
    ),

    Op.SOLVE_INEQUALITY: OperationSemantics(
        op=Op.SOLVE_INEQUALITY,
        name_cn="解不等式",
        name_en="Inequality Solving",
        description="求出使不等式成立的变量范围",
        input_type="不等式",
        output_type="解集",
        prerequisites=["等式性质", "区间概念"],
        common_errors=[
            "不等号方向反转忘",
            "分式不等式通分错误",
        ],
        examples=[
            "x² - 4 < 0 → -2 < x < 2",
        ],
    ),

    # ═══════════════════════════════════════════
    # 线性代数
    # ═══════════════════════════════════════════
    Op.MATRIX_OP: OperationSemantics(
        op=Op.MATRIX_OP,
        name_cn="矩阵运算",
        name_en="Matrix Operations",
        description="矩阵的加法、乘法、转置等基本运算",
        input_type="矩阵",
        output_type="矩阵",
        prerequisites=["矩阵定义", "行列运算规则"],
        common_errors=[
            "矩阵乘法维度不匹配",
            "乘法顺序错误",
        ],
        examples=[
            "[1,2;3,4] · [5,6;7,8] = [19,22;43,50]",
        ],
    ),

    Op.ROW_REDUCE: OperationSemantics(
        op=Op.ROW_REDUCE,
        name_cn="行阶梯化",
        name_en="Row Reduction",
        description="通过行变换将矩阵化为行阶梯形或行最简形",
        input_type="矩阵",
        output_type="行阶梯矩阵",
        prerequisites=["行变换规则"],
        common_errors=[
            "变换步骤不记录",
            "某行同时乘以0",
        ],
    ),

    Op.DETERMINANT: OperationSemantics(
        op=Op.DETERMINANT,
        name_cn="行列式",
        name_en="Determinant",
        description="计算方阵的行列式值",
        input_type="方阵",
        output_type="数值",
        prerequisites=["行列式定义", "代数余子式"],
        common_errors=[
            "符号错误",
            "余子式计算错误",
        ],
        examples=[
            "det([a,b;c,d]) = ad - bc",
        ],
    ),

    Op.EIGEN_SOLVE: OperationSemantics(
        op=Op.EIGEN_SOLVE,
        name_cn="特征值求解",
        name_en="Eigenvalue Problem",
        description="求解矩阵的特征值和特征向量",
        input_type="方阵",
        output_type="特征值和特征向量",
        prerequisites=["行列式", "多项式求根"],
        common_errors=[
            "特征多项式计算错误",
            "遗漏重根情况",
        ],
    ),

    Op.ORTHOGONALIZE: OperationSemantics(
        op=Op.ORTHOGONALIZE,
        name_cn="正交化",
        name_en="Orthogonalization",
        description="将向量组化为正交向量组（施密特正交化）",
        input_type="线性无关向量组",
        output_type="正交向量组",
        prerequisites=["内积", "向量投影"],
        common_errors=[
            "投影公式记忆错误",
            "单位化忘开方",
        ],
    ),

    Op.QUADRATIC_FORM: OperationSemantics(
        op=Op.QUADRATIC_FORM,
        name_cn="二次型",
        name_en="Quadratic Form",
        description="二次型的标准化、规范化和正定判定",
        input_type="二次型表达式",
        output_type="标准形矩阵",
        prerequisites=["特征值", "矩阵合同"],
        common_errors=[
            "配方法步骤错误",
            "矩阵表示不正确",
        ],
    ),

    # ═══════════════════════════════════════════
    # 级数
    # ═══════════════════════════════════════════
    Op.SUM_SERIES: OperationSemantics(
        op=Op.SUM_SERIES,
        name_cn="级数求和",
        name_en="Series Summation",
        description="求无穷级数的和或部分和",
        input_type="级数通项",
        output_type="和值",
        prerequisites=["等差/等比数列", "求和公式"],
        common_errors=[
            "公式使用条件不清",
            "收敛性判断错误",
        ],
    ),

    Op.CONVERGENCE_TEST: OperationSemantics(
        op=Op.CONVERGENCE_TEST,
        name_cn="级数收敛性",
        name_en="Convergence Test",
        description="判断级数的收敛性",
        input_type="级数",
        output_type="收敛/发散判定",
        prerequisites=["极限概念"],
        common_errors=[
            "误用比较判别法",
            "比值法极限计算错误",
        ],
    ),

    # ═══════════════════════════════════════════
    # 概率统计
    # ═══════════════════════════════════════════
    Op.PROBABILITY_CALC: OperationSemantics(
        op=Op.PROBABILITY_CALC,
        name_cn="概率计算",
        name_en="Probability Calculation",
        description="计算事件的概率",
        input_type="概率模型",
        output_type="概率值",
        prerequisites=["概率公理", "排列组合"],
        common_errors=[
            "混淆独立与互斥",
            "条件概率公式用错",
        ],
    ),

    Op.EXPECTATION: OperationSemantics(
        op=Op.EXPECTATION,
        name_cn="期望方差",
        name_en="Expectation & Variance",
        description="计算随机变量的期望、方差等数字特征",
        input_type="随机变量分布",
        output_type="数字特征",
        prerequisites=["概率计算", "积分/求和"],
        common_errors=[
            "E(X+Y) = E(X)+E(Y) 误写为乘法",
            "D(X+Y) 展开错误",
        ],
    ),

    Op.MLE_DERIVE: OperationSemantics(
        op=Op.MLE_DERIVE,
        name_cn="极大似然估计",
        name_en="Maximum Likelihood Estimation",
        description="建立似然函数并求参数估计值",
        input_type="样本和分布",
        output_type="参数估计",
        prerequisites=["概率密度函数", "求导"],
        common_errors=[
            "似然函数写错",
            "对数求导错误",
        ],
    ),

    Op.MOMENT_ESTIMATE: OperationSemantics(
        op=Op.MOMENT_ESTIMATE,
        name_cn="矩估计",
        name_en="Moment Estimation",
        description="用样本矩估计总体矩",
        input_type="样本数据",
        output_type="参数估计",
        prerequisites=["矩的概念", "大数定律"],
        common_errors=[
            "样本矩公式记错",
            "总体矩与样本矩混淆",
        ],
    ),

    Op.HYPOTHESIS_TEST: OperationSemantics(
        op=Op.HYPOTHESIS_TEST,
        name_cn="假设检验",
        name_en="Hypothesis Testing",
        description="对总体参数进行假设检验",
        input_type="假设和样本",
        output_type="拒绝/接受判定",
        prerequisites=["分布函数", "显著性水平"],
        common_errors=[
            "原假设与备择假设设置错误",
            "临界值查表错误",
        ],
    ),

    # ═══════════════════════════════════════════
    # 证明/逻辑
    # ═══════════════════════════════════════════
    Op.APPLY_THEOREM: OperationSemantics(
        op=Op.APPLY_THEOREM,
        name_cn="应用定理",
        name_en="Theorem Application",
        description="应用数学定理进行推理证明",
        input_type="定理和条件",
        output_type="推理结论",
        prerequisites=["定理内容", "适用条件"],
        common_errors=[
            "定理条件不满足",
            "定理形式误用",
        ],
    ),

    Op.CLASSIFY: OperationSemantics(
        op=Op.CLASSIFY,
        name_cn="分类讨论",
        name_en="Case Analysis",
        description="根据不同情况分别讨论求解",
        input_type="问题",
        output_type="各情况解集",
        prerequisites=["逻辑推理"],
        common_errors=[
            "分类不全面",
            "遗漏边界情况",
        ],
    ),

    Op.INDUCTION_STEP: OperationSemantics(
        op=Op.INDUCTION_STEP,
        name_cn="数学归纳法",
        name_en="Mathematical Induction",
        description="用数学归纳法证明命题对所有自然数成立",
        input_type="命题",
        output_type="证明完成",
        prerequisites=["归纳假设", "归纳步骤"],
        common_errors=[
            "归纳假设写错",
            "归纳步骤推证不严",
        ],
    ),

    Op.CONTRADICTION: OperationSemantics(
        op=Op.CONTRADICTION,
        name_cn="反证法",
        name_en="Proof by Contradiction",
        description="假设结论不成立，导出矛盾",
        input_type="待证命题",
        output_type="矛盾导出",
        prerequisites=["否定命题", "逻辑推理"],
        common_errors=[
            "否定命题写错",
            "矛盾导出不明确",
        ],
    ),

    # ═══════════════════════════════════════════
    # 通用
    # ═══════════════════════════════════════════
    Op.COMPUTE: OperationSemantics(
        op=Op.COMPUTE,
        name_cn="计算",
        name_en="Computation",
        description="通用计算操作",
        input_type="表达式",
        output_type="结果",
        common_errors=["算术错误"],
    ),

    Op.DEFINE: OperationSemantics(
        op=Op.DEFINE,
        name_cn="引入定义",
        name_en="Definition Introduction",
        description="在解题过程中引入新的定义或记号",
        input_type="概念",
        output_type="定义表达式",
        prerequisites=["基本概念"],
        common_errors=["定义表述不准确"],
    ),

    Op.FINAL_ANSWER: OperationSemantics(
        op=Op.FINAL_ANSWER,
        name_cn="得出结论",
        name_en="Conclusion",
        description="根据前面的推导得出最终答案",
        input_type="推导结果",
        output_type="最终答案",
        prerequisites=["完整推导"],
        common_errors=["答案抄错"],
    ),

    # ═══════════════════════════════════════════
    # 几何/向量
    # ═══════════════════════════════════════════
    Op.CROSS_PRODUCT: OperationSemantics(
        op=Op.CROSS_PRODUCT,
        name_cn="叉积",
        name_en="Cross Product",
        description="计算向量的叉积（向量积）",
        input_type="两个三维向量",
        output_type="向量",
        prerequisites=["向量基础", "行列式"],
        common_errors=[
            "右手定则应用错误",
            "行列式计算错误",
        ],
    ),

    Op.DOT_PRODUCT: OperationSemantics(
        op=Op.DOT_PRODUCT,
        name_cn="点积",
        name_en="Dot Product",
        description="计算向量的点积（数量积）",
        input_type="两个向量",
        output_type="数量",
        prerequisites=["向量基础"],
        common_errors=["忘记是数量不是向量"],
    ),

    Op.NORM: OperationSemantics(
        op=Op.NORM,
        name_cn="范数",
        name_en="Vector Norm",
        description="计算向量的长度或模",
        input_type="向量",
        output_type="非负数",
        prerequisites=["点积", "平方根"],
        common_errors=["忘开方"],
    ),
}


# ═══════════════════════════════════════════════
# 知识点语义
# ═══════════════════════════════════════════════

@dataclass
class KnowledgePointSemantics:
    """
    知识点语义 — 理解每个知识点的关系和层次

    Attributes:
        id: 知识点唯一标识
        name_cn: 中文名称
        name_en: 英文名称
        category: 所属类别（极限、微积分、线性代数等）
        level: 难度等级（1-5）
        prerequisites: 前置知识点
        related_ops: 相关操作
        description: 知识点描述
    """
    id: str
    name_cn: str
    name_en: str
    category: str
    level: int = 1
    prerequisites: List[str] = field(default_factory=list)
    related_ops: List[Op] = field(default_factory=list)
    description: str = ""


# 知识点语义库
KNOWLEDGE_POINT_SEMANTICS: Dict[str, KnowledgePointSemantics] = {
    # ═══════════════════════════════════════════
    # 极限与连续
    # ═══════════════════════════════════════════
    "极限": KnowledgePointSemantics(
        id="极限",
        name_cn="极限",
        name_en="Limit",
        category="分析基础",
        level=2,
        prerequisites=["数列基础"],
        related_ops=[Op.COMPUTE_LIMIT],
        description="描述数列或函数随变量趋近某值时的行为趋势",
    ),
    "连续": KnowledgePointSemantics(
        id="连续",
        name_cn="连续",
        name_en="Continuity",
        category="分析基础",
        level=2,
        prerequisites=["极限"],
        related_ops=[Op.COMPUTE_LIMIT],
        description="函数在某点的极限值等于函数值",
    ),
    "导数": KnowledgePointSemantics(
        id="导数",
        name_cn="导数",
        name_en="Derivative",
        category="微分学",
        level=2,
        prerequisites=["极限"],
        related_ops=[Op.DIFFERENTIATE],
        description="描述函数瞬时变化率的概念",
    ),
    "微分": KnowledgePointSemantics(
        id="微分",
        name_cn="微分",
        name_en="Differential",
        category="微分学",
        level=2,
        prerequisites=["导数"],
        related_ops=[Op.DIFFERENTIATE],
        description="函数改变量的线性主部",
    ),
    "积分": KnowledgePointSemantics(
        id="积分",
        name_cn="积分",
        name_en="Integral",
        category="积分学",
        level=2,
        prerequisites=["导数", "原函数概念"],
        related_ops=[Op.INTEGRATE],
        description="求原函数或曲线下面积",
    ),

    # ═══════════════════════════════════════════
    # 线性代数
    # ═══════════════════════════════════════════
    "矩阵": KnowledgePointSemantics(
        id="矩阵",
        name_cn="矩阵",
        name_en="Matrix",
        category="线性代数",
        level=2,
        prerequisites=["行列式"],
        related_ops=[Op.MATRIX_OP, Op.ROW_REDUCE],
        description="由数排成矩形的数表",
    ),
    "行列式": KnowledgePointSemantics(
        id="行列式",
        name_cn="行列式",
        name_en="Determinant",
        category="线性代数",
        level=2,
        prerequisites=["矩阵基础"],
        related_ops=[Op.DETERMINANT],
        description="方阵对应的一个数值",
    ),
    "特征值": KnowledgePointSemantics(
        id="特征值",
        name_cn="特征值",
        name_en="Eigenvalue",
        category="线性代数",
        level=3,
        prerequisites=["行列式", "多项式"],
        related_ops=[Op.EIGEN_SOLVE],
        description="满足 Ax = λx 的数 λ",
    ),
    "特征向量": KnowledgePointSemantics(
        id="特征向量",
        name_cn="特征向量",
        name_en="Eigenvector",
        category="线性代数",
        level=3,
        prerequisites=["特征值"],
        related_ops=[Op.EIGEN_SOLVE],
        description="满足 Ax = λx 的非零向量 x",
    ),

    # ═══════════════════════════════════════════
    # 概率统计
    # ═══════════════════════════════════════════
    "概率": KnowledgePointSemantics(
        id="概率",
        name_cn="概率",
        name_en="Probability",
        category="概率统计",
        level=2,
        prerequisites=["排列组合"],
        related_ops=[Op.PROBABILITY_CALC],
        description="事件发生的可能性大小",
    ),
    "期望": KnowledgePointSemantics(
        id="期望",
        name_cn="期望",
        name_en="Expectation",
        category="概率统计",
        level=3,
        prerequisites=["概率", "积分/求和"],
        related_ops=[Op.EXPECTATION],
        description="随机变量的平均值",
    ),
    "方差": KnowledgePointSemantics(
        id="方差",
        name_cn="方差",
        name_en="Variance",
        category="概率统计",
        level=3,
        prerequisites=["期望"],
        related_ops=[Op.EXPECTATION],
        description="随机变量偏离期望的程度",
    ),

    # ═══════════════════════════════════════════
    # 常见错误类型
    # ═══════════════════════════════════════════
    "复合函数求导": KnowledgePointSemantics(
        id="复合函数求导",
        name_cn="复合函数求导",
        name_en="Chain Rule",
        category="微分学",
        level=2,
        prerequisites=["导数公式", "链式法则"],
        related_ops=[Op.DIFFERENTIATE],
        description="对复合函数 f(g(x)) 求导",
    ),
    "分部积分": KnowledgePointSemantics(
        id="分部积分",
        name_cn="分部积分",
        name_en="Integration by Parts",
        category="积分学",
        level=3,
        prerequisites=["积分基础", "导数公式"],
        related_ops=[Op.INTEGRATE],
        description="∫u dv = uv - ∫v du",
    ),
    "换元积分": KnowledgePointSemantics(
        id="换元积分",
        name_cn="换元积分",
        name_en="U-Substitution",
        category="积分学",
        level=3,
        prerequisites=["积分基础", "复合函数"],
        related_ops=[Op.INTEGRATE],
        description="通过变量替换简化积分",
    ),
    "泰勒展开": KnowledgePointSemantics(
        id="泰勒展开",
        name_cn="泰勒展开",
        name_en="Taylor Expansion",
        category="级数",
        level=3,
        prerequisites=["导数", "高阶导数"],
        related_ops=[Op.EXPAND_SERIES],
        description="将函数在某点展开为无穷级数",
    ),
}


# ═══════════════════════════════════════════════
# 语义匹配器
# ═══════════════════════════════════════════════

class SemanticMatcher:
    """
    语义匹配器 — 判断两个数学表达式/操作是否语义等价

    用法：
        matcher = SemanticMatcher()
        result = matcher.operations_match("求导", "differentiate")
        # result.score = 1.0, result.equivalent = True
    """

    def __init__(self):
        # 操作名称变体映射
        self._op_variants: Dict[str, Op] = self._build_op_variants()

        # 知识点的同义词映射
        self._kp_variants: Dict[str, str] = self._build_kp_variants()

    @staticmethod
    def _build_op_variants() -> Dict[str, Op]:
        """构建操作名称变体映射"""
        variants = {}

        # 中文变体
        chinese_variants = {
            "求导": Op.DIFFERENTIATE,
            "导数": Op.DIFFERENTIATE,
            "微分": Op.DIFFERENTIATE,
            "偏导数": Op.PARTIAL_DIFF,
            "偏导": Op.PARTIAL_DIFF,
            "积分": Op.INTEGRATE,
            "不定积分": Op.INTEGRATE,
            "定积分": Op.INTEGRATE,
            "极限": Op.COMPUTE_LIMIT,
            "求极限": Op.COMPUTE_LIMIT,
            "展开": Op.EXPAND,
            "因式分解": Op.FACTOR,
            "分解因式": Op.FACTOR,
            "化简": Op.SIMPLIFY,
            "代入": Op.SUBSTITUTE,
            "替换": Op.SUBSTITUTE,
            "求解": Op.SOLVE_EQUATION,
            "解方程": Op.SOLVE_EQUATION,
            "解方程组": Op.SOLVE_SYSTEM,
            "矩阵运算": Op.MATRIX_OP,
            "矩阵乘法": Op.MATRIX_OP,
            "行列式": Op.DETERMINANT,
            "行变换": Op.ROW_REDUCE,
            "特征值": Op.EIGEN_SOLVE,
            "特征向量": Op.EIGEN_SOLVE,
            "概率": Op.PROBABILITY_CALC,
            "期望": Op.EXPECTATION,
            "方差": Op.EXPECTATION,
            "定理": Op.APPLY_THEOREM,
            "应用定理": Op.APPLY_THEOREM,
            "分类": Op.CLASSIFY,
            "分类讨论": Op.CLASSIFY,
            "归纳": Op.INDUCTION_STEP,
            "数学归纳法": Op.INDUCTION_STEP,
            "反证法": Op.CONTRADICTION,
            "结论": Op.FINAL_ANSWER,
            "答案": Op.FINAL_ANSWER,
            "所以": Op.FINAL_ANSWER,
            "因此": Op.FINAL_ANSWER,
        }

        for variant, op in chinese_variants.items():
            variants[variant] = op
            variants[variant.lower()] = op

        # 英文变体
        english_variants = {
            "derivative": Op.DIFFERENTIATE,
            "deriv": Op.DIFFERENTIATE,
            "diff": Op.DIFFERENTIATE,
            "integrate": Op.INTEGRATE,
            "integral": Op.INTEGRATE,
            "limit": Op.COMPUTE_LIMIT,
            "expand": Op.EXPAND,
            "factor": Op.FACTOR,
            "factorize": Op.FACTOR,
            "simplify": Op.SIMPLIFY,
            "substitute": Op.SUBSTITUTE,
            "solve": Op.SOLVE_EQUATION,
            "matrix": Op.MATRIX_OP,
            "determinant": Op.DETERMINANT,
            "det": Op.DETERMINANT,
            "eigenvalue": Op.EIGEN_SOLVE,
            "eigenvector": Op.EIGEN_SOLVE,
            "probability": Op.PROBABILITY_CALC,
            "expectation": Op.EXPECTATION,
            "variance": Op.EXPECTATION,
            "theorem": Op.APPLY_THEOREM,
            "classify": Op.CLASSIFY,
            "induction": Op.INDUCTION_STEP,
            "contradiction": Op.CONTRADICTION,
            "answer": Op.FINAL_ANSWER,
            "conclusion": Op.FINAL_ANSWER,
        }

        for variant, op in english_variants.items():
            variants[variant] = op
            variants[variant.lower()] = op

        return variants

    @staticmethod
    def _build_kp_variants() -> Dict[str, str]:
        """构建知识点同义词映射"""
        return {
            "导数": "导数",
            "微分": "微分",
            "偏导": "偏导数",
            "积分": "积分",
            "不定积分": "积分",
            "定积分": "积分",
            "极限": "极限",
            "连续": "连续",
            "矩阵": "矩阵",
            "行列式": "行列式",
            "特征值": "特征值",
            "特征向量": "特征向量",
            "概率": "概率",
            "期望": "期望",
            "方差": "方差",
        }

    def operations_match(self, op1: str, op2: str) -> Tuple[bool, float]:
        """
        判断两个操作是否语义等价

        Args:
            op1: 操作1（中文或英文）
            op2: 操作2

        Returns:
            (equivalent, confidence)
        """
        # 规范化
        norm1 = self._normalize_op(op1)
        norm2 = self._normalize_op(op2)

        if norm1 == norm2:
            return True, 1.0

        # 检查兼容操作
        from operations import ops_compatible
        if ops_compatible(norm1, norm2):
            return True, 0.8

        return False, 0.0

    def _normalize_op(self, raw: str) -> Op:
        """规范化操作名称"""
        if not raw:
            return Op.COMPUTE

        raw_lower = raw.lower().strip()

        # 查变体映射
        if raw_lower in self._op_variants:
            return self._op_variants[raw_lower]

        # 尝试部分匹配
        for variant, op in self._op_variants.items():
            if variant in raw_lower or raw_lower in variant:
                return op

        # 回退到 operations.normalize_op
        return normalize_op(raw)

    def knowledge_match(self, kp1: str, kp2: str) -> Tuple[bool, float]:
        """
        判断两个知识点是否语义等价

        Args:
            kp1: 知识点1
            kp2: 知识点2

        Returns:
            (equivalent, confidence)
        """
        # 规范化
        norm1 = self._normalize_kp(kp1)
        norm2 = self._normalize_kp(kp2)

        if norm1 == norm2:
            return True, 1.0

        # 查同义词映射
        for synonym, canonical in self._kp_variants.items():
            if (norm1 == canonical and norm2 == synonym) or \
               (norm2 == canonical and norm1 == synonym):
                return True, 0.9

        # 查相关操作
        kp_sem1 = KNOWLEDGE_POINT_SEMANTICS.get(norm1)
        kp_sem2 = KNOWLEDGE_POINT_SEMANTICS.get(norm2)

        if kp_sem1 and kp_sem2:
            # 共享相关操作
            shared_ops = set(kp_sem1.related_ops) & set(kp_sem2.related_ops)
            if shared_ops:
                return True, 0.7

        return False, 0.0

    def _normalize_kp(self, raw: str) -> str:
        """规范化知识点名称"""
        if not raw:
            return ""

        raw = raw.strip()

        # 查同义词映射
        if raw in self._kp_variants:
            return self._kp_variants[raw]

        return raw


# ═══════════════════════════════════════════════
# 错误检测器
# ═══════════════════════════════════════════════

class ErrorDetector:
    """
    错误检测器 — 识别学生作答中的常见错误

    用法：
        detector = ErrorDetector()
        errors = detector.detect("x^2 + x = x(x+1)", Op.DIFFERENTIATE)
        # errors = [{"type": "...", "description": "...", "severity": "warning"}]
    """

    # 常见错误模式
    ERROR_PATTERNS: List[Dict[str, Any]] = [
        # 求导错误
        {
            "pattern": r"\(f.*g.*\)\'\s*=\s*f\'.*g\'",
            "operation": Op.DIFFERENTIATE,
            "error_type": "导数乘法法则错误",
            "description": "乘积求导应使用 (fg)' = f'g + fg'",
            "severity": "error",
        },
        {
            "pattern": r"\(f/g\)'\s*=\s*\(f\'-g\'\)/g",
            "operation": Op.DIFFERENTIATE,
            "error_type": "商法则错误",
            "description": "商的导数应使用 (f/g)' = (f'g - fg')/g²",
            "severity": "error",
        },
        {
            "pattern": r"\(x\^n\)'\s*=\s*n.*x\^\(n-1\)",
            "operation": Op.DIFFERENTIATE,
            "error_type": "幂函数求导系数错误",
            "description": "幂函数求导公式为 (x^n)' = nx^{n-1}",
            "severity": "error",
        },
        # 积分错误
        {
            "pattern": r"∫.*dx\s*=\s*.*\s*\+?\s*C",
            "operation": Op.INTEGRATE,
            "error_type": "积分常数遗漏",
            "description": "不定积分结果必须加常数 C",
            "severity": "warning",
        },
        # 矩阵错误
        {
            "pattern": r"det\(AB\)\s*=\s*det\(A\).*det\(B\)",
            "operation": Op.DETERMINANT,
            "error_type": "行列式乘法公式错误",
            "description": "det(AB) = det(A) × det(B) 是正确的",
            "severity": "info",
        },
    ]

    def detect(self, text: str, operation: Op) -> List[Dict[str, Any]]:
        """
        检测文本中的常见错误

        Args:
            text: 学生作答文本
            operation: 当前操作类型

        Returns:
            错误列表 [{"type": ..., "description": ..., "severity": ...}]
        """
        errors = []

        for error_pattern in self.ERROR_PATTERNS:
            # 检查操作是否匹配
            if error_pattern["operation"] != operation:
                continue

            # 检查文本是否匹配错误模式
            if re.search(error_pattern["pattern"], text):
                errors.append({
                    "type": error_pattern["error_type"],
                    "description": error_pattern["description"],
                    "severity": error_pattern["severity"],
                })

        return errors


# ═══════════════════════════════════════════════
# 语义层主类
# ═══════════════════════════════════════════════

class SemanticLayer:
    """
    语义层主类 — 整合所有语义功能

    用法：
        semantic = SemanticLayer()

        # 获取操作语义
        sem = semantic.get_operation_semantics(Op.DIFFERENTIATE)
        print(sem.name_cn)  # 求导

        # 判断操作等价
        equivalent, score = semantic.operations_equivalent("求导", "differentiate")
        print(equivalent)  # True

        # 判断知识点等价
        equivalent, score = semantic.knowledge_equivalent("导数", "微分")
        print(equivalent)  # True

        # 检测错误
        errors = semantic.detect_errors("f' = fg", Op.DIFFERENTIATE)
        print(errors)
    """

    def __init__(self):
        self.matcher = SemanticMatcher()
        self.error_detector = ErrorDetector()

    def get_operation_semantics(self, op: Op) -> OperationSemantics:
        """获取操作语义"""
        return OPERATION_SEMANTICS.get(op, OperationSemantics(
            op=op,
            name_cn="未知操作",
            name_en="Unknown",
            description="未定义的操作",
        ))

    def get_knowledge_semantics(self, kp_id: str) -> Optional[KnowledgePointSemantics]:
        """获取知识点语义"""
        return KNOWLEDGE_POINT_SEMANTICS.get(kp_id)

    def operations_equivalent(self, op1: str, op2: str) -> Tuple[bool, float]:
        """判断两个操作是否等价"""
        return self.matcher.operations_match(op1, op2)

    def knowledge_equivalent(self, kp1: str, kp2: str) -> Tuple[bool, float]:
        """判断两个知识点是否等价"""
        return self.matcher.knowledge_match(kp1, kp2)

    def detect_errors(self, text: str, operation: Op) -> List[Dict[str, Any]]:
        """检测常见错误"""
        return self.error_detector.detect(text, operation)

    def get_prerequisites(self, op: Op) -> List[str]:
        """获取操作的前置知识"""
        sem = self.get_operation_semantics(op)
        return sem.prerequisites

    def get_related_knowledge_points(self, op: Op) -> List[str]:
        """获取相关知识点"""
        sem = self.get_operation_semantics(op)
        related = []
        for kp_id, kp_sem in KNOWLEDGE_POINT_SEMANTICS.items():
            if op in kp_sem.related_ops:
                related.append(kp_id)
        return related

    def explain_operation(self, op: Op) -> str:
        """解释操作语义"""
        sem = self.get_operation_semantics(op)
        return f"{sem.name_cn}（{sem.name_en}）: {sem.description}"


# ═══════════════════════════════════════════════
# 全局实例
# ═══════════════════════════════════════════════

_semantic_layer: Optional[SemanticLayer] = None


def get_semantic_layer() -> SemanticLayer:
    """获取语义层全局实例"""
    global _semantic_layer
    if _semantic_layer is None:
        _semantic_layer = SemanticLayer()
    return _semantic_layer


# ═══════════════════════════════════════════════
# 示例用法
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    # 获取语义层实例
    semantic = get_semantic_layer()

    print("=== 操作语义示例 ===")
    sem = semantic.get_operation_semantics(Op.DIFFERENTIATE)
    print(f"操作: {sem.name_cn} ({sem.name_en})")
    print(f"描述: {sem.description}")
    print(f"输入: {sem.input_type}")
    print(f"输出: {sem.output_type}")
    print(f"常见错误: {sem.common_errors}")

    print("\n=== 操作等价判断 ===")
    equivalent, score = semantic.operations_equivalent("求导", "differentiate")
    print(f"'求导' ≈ 'differentiate': {equivalent} (score={score})")

    equivalent, score = semantic.operations_equivalent("积分", "integration")
    print(f"'积分' ≈ 'integration': {equivalent} (score={score})")

    print("\n=== 知识点等价判断 ===")
    equivalent, score = semantic.knowledge_equivalent("导数", "微分")
    print(f"'导数' ≈ '微分': {equivalent} (score={score})")

    print("\n=== 错误检测 ===")
    errors = semantic.detect_errors("f' = fg + gf'", Op.DIFFERENTIATE)
    print(f"检测到的错误: {errors}")

    print("\n=== 前置知识 ===")
    prereqs = semantic.get_prerequisites(Op.INTEGRATE)
    print(f"积分的前置知识: {prereqs}")

    print("\n=== 相关知识点 ===")
    related = semantic.get_related_knowledge_points(Op.DIFFERENTIATE)
    print(f"求导的相关知识点: {related}")
