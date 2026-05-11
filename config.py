"""考研数学智能辅导系统 — 配置文件"""

import os

# LLM API
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")

# 考研数学类别
MATH_TYPES = ["数学一", "26宇哥八套卷"]

# 学科
SUBJECTS = ["高等数学", "线性代数", "概率论与数理统计"]

# 题型
QUESTION_TYPES = ["选择题", "填空题", "解答题", "证明题"]

# 难度
DIFFICULTY_LEVELS = ["基础", "中等", "较难", "难题"]

# 知识点映射
KNOWLEDGE_POINTS = {
    "高等数学": [
        "极限与连续", "导数与微分", "中值定理", "不定积分",
        "定积分", "反常积分", "定积分应用", "微分方程",
        "多元函数微分", "二重积分", "三重积分", "曲线曲面积分",
        "无穷级数", "向量代数与空间解析几何",
    ],
    "线性代数": [
        "行列式", "矩阵运算", "线性方程组", "向量组与线性空间",
        "特征值与特征向量", "二次型", "线性变换",
    ],
    "概率论与数理统计": [
        "随机事件与概率", "条件概率与独立性", "随机变量及其分布",
        "多维随机变量", "数字特征", "大数定律与中心极限定理",
        "数理统计", "参数估计", "假设检验",
    ],
}

# 错误类型
ERROR_TYPES = [
    "概念错误", "公式记忆错误", "运算错误",
    "推导错误", "审题错误", "计算粗心", "知识点遗忘",
]

# 学习阶段
STAGES = ["基础薄弱", "强化阶段", "冲刺阶段"]

# 评分规则说明
GRADING_RULES = """
考研数学阅卷标准：
1. 只看有效步骤 — 无效或无关步骤不计分
2. 最终答案错误但过程正确 → 给步骤分（不超过满分的70%）
3. 公式错误 → 扣关键步骤分（扣3-5分/处）
4. 计算错误 → 适当扣分（扣1-2分/处）
5. 概念错误 → 重扣（扣5分以上）
6. 笔误但方法正确 → 酌情给分
7. 推导跳跃过大 → 酌情扣分
"""

# 存储路径
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
ERROR_NOTEBOOK_PATH = os.path.join(STORAGE_DIR, "error_notebook.json")
STUDENT_PROFILE_PATH = os.path.join(STORAGE_DIR, "student_profile.json")
