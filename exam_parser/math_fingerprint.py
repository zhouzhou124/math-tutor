"""
加权数学指纹 — 用于题目与解答的语义匹配

权重体系:
  公式结构:     5  (LaTeX formula structure)
  数学对象:     4  (\int, \sum, matrix dimension, limit direction)
  中文数学术语:  2  (极限, 导数, 积分, 矩阵)
  普通中文:     1  (其他文本)
"""

import re
from collections import Counter


# ═══════════════════════════════════════════════
# 公式提取 + 规范化
# ═══════════════════════════════════════════════

def extract_formulas(text: str) -> list[str]:
    """提取所有 LaTeX 公式并规范化"""
    formulas = []
    # $...$ 和 $$...$$
    for m in re.finditer(r'\$\$?(.+?)\$\$?', text, re.DOTALL):
        formulas.append(normalize_latex(m.group(1)))
    # \[...\] 和 \(...\)
    for m in re.finditer(r'\\\[(.+?)\\\]|\\\((.+?)\\\)', text, re.DOTALL):
        f = m.group(1) or m.group(2)
        formulas.append(normalize_latex(f))
    return formulas


def normalize_latex(latex: str) -> str:
    """规范化 LaTeX 表达式，消除格式差异"""
    s = latex.strip()
    # 移除多余空格（LaTeX命令后保留空格）
    s = re.sub(r'\s+', ' ', s)
    # 移除命令参数的单字符花括号: \sin{x} → \sin x, 但保留 \frac{a}{b}
    s = re.sub(r'(\\[a-zA-Z]+)\{([a-zA-Z0-9])\}', r'\1\2', s)
    # 统一 \frac 的空格
    s = re.sub(r'\\frac\s*\{', r'\\frac{', s)
    s = re.sub(r'\\sqrt\s*\{', r'\\sqrt{', s)
    # 移除末尾标点
    s = s.rstrip('.,;:')
    return s


# ═══════════════════════════════════════════════
# 数学对象签名
# ═══════════════════════════════════════════════

_MATH_OBJECT_PATTERNS = [
    # 积分及其变体
    (r'\\int\b', 'integral'),
    (r'\\iint\b', 'double_integral'),
    (r'\\iiint\b', 'triple_integral'),
    (r'\\oint\b', 'line_integral'),
    # 求和/求积极限
    (r'\\sum\b', 'summation'),
    (r'\\prod\b', 'product'),
    (r'\\lim\b', 'limit'),
    # 导数相关
    (r'\\frac\{d\}', 'derivative'),
    (r'\\frac\{\\partial\}', 'partial_derivative'),
    (r'\\partial\b', 'partial'),
    (r"f'", 'derivative'),
    (r'f\^\{?\\prime\}?', 'derivative'),
    # 矩阵/行列式
    (r'\\begin\{pmatrix\}', 'matrix'),
    (r'\\begin\{bmatrix\}', 'matrix'),
    (r'\\begin\{vmatrix\}', 'determinant'),
    (r'\\begin\{matrix\}', 'matrix'),
    (r'\\det\b', 'determinant'),
    (r'\\mathbf\{[A-Z]\}', 'matrix_vector'),
    (r'\\pmb\{[a-z]\}', 'vector'),
    # 概率统计
    (r'\\sim\b', 'distribution'),
    (r'P\(', 'probability'),
    (r'E\(', 'expectation'),
    (r'D\(', 'variance'),
    (r'\\operatorname\{cov\}', 'covariance'),
    (r'\\operatorname\{var\}', 'variance'),
    # 级数
    (r'\\sum_\{n\s*=\s*\d+\}\^\{?\\infty\}?', 'infinite_series'),
    (r'\\sum_\{n\s*=\s*1\}\^\{?\\infty\}?', 'infinite_series'),
    # 微分方程
    (r"y'+\s*.*y\s*=", 'ode'),
    (r"y''+", 'ode'),
    (r'\\frac\{d\^?\d*y\}\{d', 'ode'),
    # 特征值
    (r'\\lambda\b', 'eigenvalue'),
    # 行列式/秩
    (r'\|[A-Z]\|', 'determinant'),
    (r'\\operatorname\{rank\}', 'rank'),
    (r'\\operatorname\{tr\}', 'trace'),
    # 范数
    (r'\\left\\\|', 'norm'),
    (r'\\right\\\|', 'norm'),
    # 变换
    (r'\\to\b', 'limit_or_map'),
    (r'\\rightarrow\b', 'limit_or_map'),
    (r'\\infty\b', 'infinity'),
]


def extract_math_objects(text: str) -> list[str]:
    """提取数学对象签名（带权重的类型标签）"""
    objects = []
    seen = set()
    for pattern, label in _MATH_OBJECT_PATTERNS:
        if re.search(pattern, text):
            if label not in seen:
                objects.append(label)
                seen.add(label)
    return objects


# ═══════════════════════════════════════════════
# 中文数学术语
# ═══════════════════════════════════════════════

_MATH_TERM_PATTERNS = [
    "极限", "导数", "微分", "积分", "不定积分", "定积分",
    "反常积分", "二重积分", "三重积分", "曲线积分", "曲面积分",
    "级数", "幂级数", "傅里叶级数", "无穷级数", "收敛", "发散",
    "矩阵", "行列式", "特征值", "特征向量", "二次型", "线性方程组",
    "向量", "线性空间", "线性变换", "基", "维数", "秩",
    "概率", "随机变量", "分布", "期望", "方差", "协方差",
    "假设检验", "参数估计", "极大似然", "无偏估计",
    "中值定理", "泰勒公式", "洛必达", "拉格朗日",
    "连续", "可导", "可微", "极值", "最值", "拐点",
    "渐近线", "切线", "法线", "曲率",
    "微分方程", "通解", "特解",
    "证明", "求证", "计算", "求",
    "奇函数", "偶函数", "周期函数", "单调", "有界",
    "等价无穷小", "同阶无穷小",
    "平面方程", "直线方程", "曲面", "曲线",
    "正交", "单位向量", "法向量",
    "条件收敛", "绝对收敛",
    "正定", "合同", "相似",
    "全概率", "贝叶斯",
    "大数定律", "中心极限定理",
    "第一类", "第二类", "曲面积分",
    "极坐标", "柱坐标", "球坐标",
    "换元", "分部积分",
]


def extract_math_terms(text: str) -> list[str]:
    """提取中文数学术语"""
    terms = []
    for term in _MATH_TERM_PATTERNS:
        if term in text:
            terms.append(term)
    return terms


# ═══════════════════════════════════════════════
# 加权指纹
# ═══════════════════════════════════════════════

class MathFingerprint:
    """一道题目的加权数学指纹"""

    def __init__(self, text: str):
        self.formulas = extract_formulas(text)           # weight 5
        self.math_objects = extract_math_objects(text)    # weight 4
        self.math_terms = extract_math_terms(text)        # weight 2
        self.plain_tokens = self._extract_plain_tokens(text)  # weight 1
        self._text = text

    def _extract_plain_tokens(self, text: str) -> list[str]:
        """提取普通中文/英文词汇（排除LaTeX和标点）"""
        # 去除 LaTeX
        clean = re.sub(r'\$[^$]*\$', '', text)
        clean = re.sub(r'\$\$[^$]*\$\$', '', clean)
        clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', clean)
        clean = re.sub(r'\\[a-zA-Z]+', '', clean)
        # 提取中文词（2-4字）
        words = re.findall(r'[一-鿿]{2,4}', clean)
        return words

    def weighted_items(self) -> dict[str, float]:
        """返回 {item: weight} 加权字典"""
        items = Counter()
        for f in self.formulas:
            items[f'FORMULA:{f}'] += 5
        for o in self.math_objects:
            items[f'OBJ:{o}'] += 4
        for t in self.math_terms:
            items[f'TERM:{t}'] += 2
        for w in self.plain_tokens:
            items[f'WORD:{w}'] += 1
        return dict(items)

    @staticmethod
    def weighted_jaccard(fp1: dict[str, float], fp2: dict[str, float]) -> float:
        """加权 Jaccard 相似度"""
        if not fp1 or not fp2:
            return 0.0

        all_keys = set(fp1.keys()) | set(fp2.keys())
        intersection_weight = 0.0
        union_weight = 0.0

        for key in all_keys:
            w1 = fp1.get(key, 0.0)
            w2 = fp2.get(key, 0.0)
            intersection_weight += min(w1, w2)
            union_weight += max(w1, w2)

        if union_weight == 0:
            return 0.0
        return intersection_weight / union_weight
