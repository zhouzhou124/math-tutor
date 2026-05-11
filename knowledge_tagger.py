"""
知识图谱自动标注器

用数学指纹自动映射题目到知识点分类体系。

映射层:
  LaTeX对象 → 知识点
  中文数学术语 → 知识点
  题型 → 学科分类

输出:
  - knowledge_points: list[str]  (如 ["极限与连续", "导数与微分"])
  - subjects: list[str]          (如 ["高等数学"])
  - difficulty: str              (基础/中等/较难/难题)
"""

import re
from collections import Counter

# ═══════════════════════════════════════════════
# 知识点分类体系（与 config.py KNOWLEDGE_POINTS 对齐）
# ═══════════════════════════════════════════════

KNOWLEDGE_TAXONOMY = {
    "高等数学": {
        "极限与连续": {
            "objects": ["limit", "limit_or_map", "infinity"],
            "terms": ["极限", "连续", "等价无穷小", "同阶无穷小", "间断点"],
            "formulas": [r"\\lim", r"\\to\s*0", r"\\to\s*\\infty", r"\\infty"],
        },
        "导数与微分": {
            "objects": ["derivative", "partial_derivative", "partial"],
            "terms": ["导数", "微分", "可导", "可微", "极值", "最值", "拐点", "切线", "法线",
                      "曲率", "渐近线"],
            "formulas": [r"f'", r"\\frac\{d", r"\\partial"],
        },
        "中值定理": {
            "terms": ["中值定理", "泰勒公式", "洛必达", "拉格朗日", "罗尔定理"],
            "formulas": [r"\\text\{泰勒\}"],
        },
        "不定积分": {
            "objects": ["integral"],
            "terms": ["不定积分", "换元", "分部积分"],
            "formulas": [r"\\int.*dx"],
        },
        "定积分": {
            "objects": ["integral"],
            "terms": ["定积分", "反常积分", "积分"],
            "formulas": [r"\\int_\{.*\}\^\{.*\}", r"\\int_0"],
        },
        "定积分应用": {
            "terms": ["面积", "体积", "弧长", "旋转体"],
        },
        "微分方程": {
            "objects": ["ode"],
            "terms": ["微分方程", "通解", "特解", "齐次", "非齐次"],
            "formulas": [r"y'+\s*", r"y''+", r"\\frac\{d\^?\d*y\}"],
        },
        "多元函数微分": {
            "objects": ["partial_derivative", "partial"],
            "terms": ["偏导数", "全微分", "方向导数", "梯度", "切平面"],
            "formulas": [r"\\frac\{\\partial"],
        },
        "二重积分": {
            "objects": ["double_integral"],
            "terms": ["二重积分", "极坐标", "积分区域"],
            "formulas": [r"\\iint", r"dxdy", r"d\\sigma"],
        },
        "三重积分": {
            "objects": ["triple_integral"],
            "terms": ["三重积分", "柱坐标", "球坐标"],
            "formulas": [r"\\iiint"],
        },
        "曲线曲面积分": {
            "objects": ["line_integral", "integral"],
            "terms": ["曲线积分", "曲面积分", "第一类", "第二类", "格林公式"],
            "formulas": [r"\\oint", r"\\iint_\{.*\}"],
        },
        "无穷级数": {
            "objects": ["infinite_series", "summation"],
            "terms": ["级数", "幂级数", "收敛", "发散", "条件收敛", "绝对收敛",
                      "收敛半径", "收敛域", "和函数", "傅里叶级数"],
            "formulas": [r"\\sum_\{n", r"\\sum_\{n\s*=\s*1\}.*\\infty"],
        },
        "向量代数与空间解析几何": {
            "terms": ["平面方程", "直线方程", "曲面", "曲线", "向量", "法向量",
                      "单位向量", "正交"],
        },
    },
    "线性代数": {
        "行列式": {
            "objects": ["determinant"],
            "terms": ["行列式", "代数余子式", "克莱姆法则"],
            "formulas": [r"\\begin\{vmatrix\}", r"\\det\b", r"\|[A-Z]\|"],
        },
        "矩阵运算": {
            "objects": ["matrix", "matrix_vector"],
            "terms": ["矩阵", "逆矩阵", "伴随矩阵", "初等变换"],
            "formulas": [r"\\begin\{pmatrix\}", r"\\begin\{bmatrix\}"],
        },
        "线性方程组": {
            "terms": ["线性方程组", "齐次方程组", "基础解系", "通解"],
            "objects": ["rank"],
        },
        "向量组与线性空间": {
            "objects": ["vector"],
            "terms": ["向量组", "线性相关", "线性无关", "线性空间", "基", "维数",
                      "线性变换", "过渡矩阵"],
        },
        "特征值与特征向量": {
            "objects": ["eigenvalue"],
            "terms": ["特征值", "特征向量", "相似", "相似对角化", "正交矩阵"],
            "formulas": [r"\\lambda\b"],
        },
        "二次型": {
            "terms": ["二次型", "正定", "合同", "标准形", "规范形", "正定矩阵"],
        },
    },
    "概率论与数理统计": {
        "随机事件与概率": {
            "objects": ["probability"],
            "terms": ["概率", "随机事件", "样本空间", "古典概型"],
            "formulas": [r"P\(", r"P\{", r"P\{"],
        },
        "条件概率与独立性": {
            "terms": ["条件概率", "独立性", "全概率", "贝叶斯"],
            "formulas": [r"P\([A-Z]\|[A-Z]\)", r"P\(AB\)"],
        },
        "随机变量及其分布": {
            "objects": ["distribution"],
            "terms": ["随机变量", "分布函数", "密度函数", "常见分布", "正态分布",
                      "指数分布", "均匀分布", "二项分布", "泊松分布"],
        },
        "多维随机变量": {
            "terms": ["多维随机变量", "边缘分布", "条件分布", "联合分布"],
        },
        "数字特征": {
            "objects": ["expectation", "variance", "covariance"],
            "terms": ["期望", "方差", "协方差", "相关系数", "矩"],
            "formulas": [r"E\(", r"D\(", r"\\operatorname\{cov\}", r"\\operatorname\{var\}"],
        },
        "大数定律与中心极限定理": {
            "terms": ["大数定律", "中心极限定理"],
        },
        "数理统计": {
            "terms": ["数理统计", "样本", "统计量", "抽样分布", "参数估计",
                      "极大似然", "无偏估计", "假设检验", "置信区间"],
        },
    },
}

# ═══════════════════════════════════════════════
# 难度推断
# ═══════════════════════════════════════════════

def infer_difficulty(text: str, question_type: str = "解答题") -> str:
    """从文本和题型推断难度"""
    if question_type == "证明题":
        return "较难"

    # 难题特征
    hard_signals = [
        r"证明", r"求证", r"二重积分", r"三重积分", r"曲线积分", r"曲面积分",
        r"级数", r"展开", r"收敛", r"幂级数", r"傅里叶",
        r"特征值", r"二次型", r"正定",
        r"假设检验", r"参数估计", r"极大似然",
    ]
    hard_count = sum(1 for s in hard_signals if re.search(s, text))

    # 基础题特征
    basic_signals = [
        r"求极限", r"求导数", r"求积分", r"计算定积分", r"计算不定积分",
        r"求偏导", r"求微分", r"计算二重积分",
    ]
    basic_count = sum(1 for s in basic_signals if re.search(s, text))

    if hard_count >= 3:
        return "难题"
    elif hard_count >= 2:
        return "较难"
    elif basic_count >= 2:
        return "基础"
    return "中等"


# ═══════════════════════════════════════════════
# 知识点标注
# ═══════════════════════════════════════════════

class KnowledgeTagger:
    """基于数学指纹的自动知识点标注器"""

    def tag(self, question_text: str, question_type: str = "解答题") -> dict:
        """
        输入题目文本，返回:
          {
            "knowledge_points": ["极限与连续", "导数与微分"],
            "subjects": ["高等数学"],
            "difficulty": "中等",
            "confidence": 0.85
          }
        """
        # 1. 按知识点评分
        scores = {}
        for subject, topics in KNOWLEDGE_TAXONOMY.items():
            for topic, patterns in topics.items():
                score = 0
                # Objects (from math_fingerprint)
                for obj in patterns.get("objects", []):
                    if re.search(re.escape(obj), question_text):
                        score += 3
                # Terms (Chinese math vocabulary)
                for term in patterns.get("terms", []):
                    if term in question_text:
                        score += 2
                # Formulas (LaTeX patterns)
                for fmt in patterns.get("formulas", []):
                    if re.search(fmt, question_text):
                        score += 2

                if score > 0:
                    scores[(subject, topic)] = score

        if not scores:
            return {
                "knowledge_points": [],
                "subjects": [],
                "difficulty": infer_difficulty(question_text, question_type),
                "confidence": 0.0,
            }

        # 2. 取top知识点（归一化阈值）
        max_score = max(scores.values())
        threshold = max(1, max_score * 0.4)
        top_topics = [(s, t) for (s, t), sc in scores.items() if sc >= threshold]
        top_topics.sort(key=lambda x: scores[x], reverse=True)

        knowledge_points = [t for s, t in top_topics[:8]]
        subjects = list(set(s for s, t in top_topics[:8]))
        confidence = min(1.0, max_score / 10)

        return {
            "knowledge_points": knowledge_points,
            "subjects": subjects,
            "difficulty": infer_difficulty(question_text, question_type),
            "confidence": round(confidence, 2),
        }

    def tag_question(self, question: dict) -> dict:
        """标注一道题目并返回更新后的dict"""
        text = question.get("question", "")
        qtype = question.get("question_type", "解答题")
        result = self.tag(text, qtype)

        # 合并现有标签
        existing_kp = question.get("knowledge_points", [])
        new_kp = result["knowledge_points"]
        merged_kp = list(dict.fromkeys(new_kp + existing_kp))  # 去重保序

        question["knowledge_points"] = merged_kp[:8]
        question["tags"] = merged_kp[:8]
        if "subjects" not in question:
            question["subjects"] = result["subjects"]
        if not question.get("difficulty") or question["difficulty"] == "中等":
            question["difficulty"] = result["difficulty"]
        return question

    def batch_tag(self, questions: list[dict]) -> list[dict]:
        """批量标注"""
        return [self.tag_question(q) for q in questions]


# ═══════════════════════════════════════════════
# 知识图谱关系
# ═══════════════════════════════════════════════

def build_knowledge_graph(questions: list[dict]) -> dict:
    """从题目集合构建知识图谱（共现关系）"""
    tagger = KnowledgeTagger()
    topic_cooccurrence = Counter()

    for q in questions:
        kps = q.get("knowledge_points", [])
        if not kps:
            result = tagger.tag(q.get("question", ""))
            kps = result["knowledge_points"]
        # 记录所有topic对
        for i, t1 in enumerate(kps):
            for t2 in kps[i + 1:]:
                pair = tuple(sorted([t1, t2]))
                topic_cooccurrence[pair] += 1

    # 构建图
    nodes = set()
    edges = []
    for (t1, t2), weight in topic_cooccurrence.most_common(50):
        nodes.add(t1)
        nodes.add(t2)
        if weight >= 2:  # 至少共现2次
            edges.append({"source": t1, "target": t2, "weight": weight})

    return {
        "nodes": sorted(nodes),
        "edges": edges,
        "total_cooccurrences": sum(topic_cooccurrence.values()),
    }
