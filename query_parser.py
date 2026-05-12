"""
Query Parser — 自然语言搜题解析

将用户输入的自然语言查询解析为结构化过滤器 + 关键词，
对接 hybrid_search.hybrid_search()。

示例:
    "2020 二重积分 解答题"  → filters={year: 2020, question_type: "解答题"}, keywords="二重积分"
    "极限 洛必达 较难"      → filters={difficulty: "较难"}, keywords="极限 洛必达"
    "概率 选择题 2024"     → filters={year: 2024, question_type: "选择题"}, keywords="概率"
"""

import re

from config import QUESTION_TYPES, DIFFICULTY_LEVELS, KNOWLEDGE_POINTS

# 合并所有知识点为扁平列表
_ALL_KNOWLEDGE_POINTS: list[str] = []
for _subject, _points in KNOWLEDGE_POINTS.items():
    _ALL_KNOWLEDGE_POINTS.extend(_points)

# 缩短后有歧义的知识点别名
_KP_ALIASES: dict[str, str] = {
    "二重积分": "二重积分",
    "三重积分": "三重积分",
    "定积分": "定积分",
    "不定积分": "不定积分",
    "反常积分": "反常积分",
    "定积分应用": "定积分应用",
    "微分方程": "微分方程",
    "无穷级数": "无穷级数",
    "曲线积分": "曲线曲面积分",
    "曲面积分": "曲线曲面积分",
    "多元函数": "多元函数微分",
    "条件概率": "条件概率与独立性",
    "随机变量": "随机变量及其分布",
    "多维随机变量": "多维随机变量",
    "大数定律": "大数定律与中心极限定理",
    "参数估计": "参数估计",
    "假设检验": "假设检验",
    "向量空间": "向量组与线性空间",
    "二次型": "二次型",
    "线性变换": "线性变换",
    "特征值": "特征值与特征向量",
    "特征向量": "特征值与特征向量",
    "矩阵": "矩阵运算",
    "行列式": "行列式",
    "线性方程组": "线性方程组",
}


def _extract_years(text: str) -> tuple[list[int], str]:
    """提取4位年份，返回(年份列表, 去除年份后的文本)。"""
    years = []
    year_pattern = re.compile(r'\b(19[89]\d|20[012]\d)\b')

    def _collect(m: re.Match) -> str:
        y = int(m.group(0))
        if 1987 <= y <= 2026:
            years.append(y)
        return ""

    remaining = year_pattern.sub(_collect, text)
    return years, remaining


def _extract_difficulty(text: str) -> tuple[str | None, str]:
    """提取难度标签。"""
    # 直接匹配
    for diff in DIFFICULTY_LEVELS:
        if diff in text:
            return diff, text.replace(diff, "")

    # 别名
    alias_map = {
        "简单": "基础", "容易": "基础", "基本": "基础",
        "中等": "中等", "一般": "中等",
        "难": "较难", "较难": "较难", "困难": "较难",
        "最难": "难题", "超难": "难题",
    }
    for alias, diff in alias_map.items():
        if alias in text:
            return diff, text.replace(alias, "")
    return None, text


def _extract_question_type(text: str) -> tuple[str | None, str]:
    """提取题型。"""
    for qt in QUESTION_TYPES:
        if qt in text:
            return qt, text.replace(qt, "")
    # 别名
    type_aliases = {"选择": "选择题", "填空": "填空题", "解答": "解答题", "证明": "证明题"}
    for alias, qt in type_aliases.items():
        if alias in text:
            return qt, text.replace(alias, "")
    return None, text


def _extract_knowledge_points(text: str) -> tuple[list[str], str]:
    """提取知识点（最长匹配优先）。"""
    matched = []
    remaining = text

    # 按长度降序排列，优先匹配长名称
    sorted_points = sorted(_ALL_KNOWLEDGE_POINTS, key=len, reverse=True)
    for point in sorted_points:
        if point in remaining:
            matched.append(point)
            remaining = remaining.replace(point, "")

    # 再试别名（仅匹配未被完整名称捕获的）
    for alias, canonical in sorted(_KP_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if canonical not in matched and alias in remaining:
            matched.append(canonical)
            remaining = remaining.replace(alias, "")

    return matched, remaining


def parse_query(query: str) -> dict:
    """
    解析自然语言搜索查询。

    Args:
        query: 用户输入的自然语言，如 "2020 二重积分 解答题 较难"

    Returns:
        {
            "keywords": str,          # 剩余关键词，用于 BM25/vector 匹配
            "filters": dict,           # hybrid_search 过滤器
            "year": int | None,        # 提取的年份
            "question_type": str | None,
            "knowledge_points": [str],
            "difficulty": str | None,
            "math_type": str | None,
        }
    """
    text = query.strip()

    # 逐层提取，每层消耗掉匹配的文本
    years, text = _extract_years(text)
    difficulty, text = _extract_difficulty(text)
    qtype, text = _extract_question_type(text)
    knowledge_points, text = _extract_knowledge_points(text)

    # 剩余文本清理：去除多余空白和标点
    keywords = re.sub(r'\s+', ' ', text).strip()

    # 构建 filters dict
    filters: dict = {}
    year = years[0] if years else None
    if year:
        filters["year"] = year
    if difficulty:
        filters["difficulty"] = difficulty
    if qtype:
        filters["question_type"] = qtype
    if knowledge_points:
        # 多个知识点用 __contains 匹配（hybrid_search 的 metadata_filter 支持）
        filters["knowledge_points__contains"] = knowledge_points[0]

    # 如果没有提取到关键词但有知识点，用第一个知识点作为关键词
    if not keywords and knowledge_points:
        keywords = knowledge_points[0]

    return {
        "keywords": keywords,
        "filters": filters,
        "year": year,
        "question_type": qtype,
        "knowledge_points": knowledge_points,
        "difficulty": difficulty,
        "math_type": None,
    }
