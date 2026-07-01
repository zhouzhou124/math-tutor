"""考研数学智能辅导系统 — 配置文件"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ── 结构化输出开关（Phase 1: 双栈运行） ──
# True  → LLM 输出 JSON，走 render_structured() 管道
# False → LLM 输出 Markdown，走 legacy regex 解析 + 4层回退渲染
USE_STRUCTURED_OUTPUT = os.getenv("USE_STRUCTURED_OUTPUT", "true").lower() == "true"

# ── LLM API（主模型） ──
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")

# ── 分 Agent 模型配置（留空则回退到主模型） ──
SOLVER_MODEL = os.getenv("SOLVER_MODEL", "")          # 解答 Agent
GRADING_MODEL = os.getenv("GRADING_MODEL", "")        # 批改 Agent
DIAGNOSIS_MODEL = os.getenv("DIAGNOSIS_MODEL", "")    # 诊断 Agent
MEMORY_MODEL = os.getenv("MEMORY_MODEL", "")          # 记忆 Agent

# ── API Key 轮换 ──
CREDENTIAL_STORE_PATH = os.path.join(
    os.path.dirname(__file__), "storage", ".credentials.json",
)
KEY_ROTATION_DAYS = int(os.getenv("KEY_ROTATION_DAYS", "15"))

# 考研数学类别
MATH_TYPES = ["数学一", "26宇哥八套卷", "26合工大超越", "26宇哥四套卷", "26李擂八套卷"]

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

# 评分规则说明（按题型分层）
GRADING_RULES = """
考研数学阅卷标准（题型分层）：
解答题: 数学正确性 50% + 关键步骤 30% + 完整性 20%
证明题: 逻辑链完整性 40% + 数学正确性 40% + 严谨性 20%

1. 只看有效步骤 — 无效或无关步骤不计分
2. 公式错误 → 扣关键步骤分（扣3-5分/处）
3. 计算错误 → 适当扣分（扣1-2分/处）
4. 概念错误 → 重扣（扣5分以上）
5. 笔误但方法正确 → 酌情给分
6. 跳过非关键步骤但数学正确 → 不扣分
7. 解题顺序与标准不同但逻辑正确 → 不扣分
"""

# 按题型的评分权重
SCORING_WEIGHTS = {
    "解答题": {"correctness": 0.5, "key_steps": 0.3, "completeness": 0.2},
    "证明题": {"logic_chain": 0.4, "correctness": 0.4, "rigor": 0.2},
    "选择题": {"answer_match": 1.0},
    "填空题": {"answer_match": 1.0},
}

# P39: 填空题 quick_compare 置信度阈值，低于此值降级 LLM
FILL_QUICK_COMPARE_CONFIDENCE_THRESHOLD = 0.9


def should_escalate_fill_to_llm(compare_result: dict, threshold: float | None = None) -> bool:
    """P39: 统一填空题 confidence 降级判断。

    Args:
        compare_result: result from symbolic_executor.quick_compare()
        threshold: confidence threshold (default: FILL_QUICK_COMPARE_CONFIDENCE_THRESHOLD)

    Returns:
        True if should escalate to LLM grading.
    """
    if threshold is None:
        threshold = FILL_QUICK_COMPARE_CONFIDENCE_THRESHOLD

    confidence = compare_result.get("confidence")
    status = compare_result.get("status", "")
    # Use explicit key check to avoid `False or other_value` pitfall
    if "ok" in compare_result:
        ok = compare_result["ok"]
    elif "equivalent" in compare_result:
        ok = compare_result["equivalent"]
    else:
        ok = None

    # Explicit match with high confidence → no escalation
    if ok is True and confidence is not None and confidence >= threshold:
        return False

    # Explicit non-match → always escalate for LLM verification
    if ok is False:
        return True

    # Low confidence → escalate
    if confidence is not None and confidence < threshold:
        return True

    # Unknown/ambiguous status → escalate
    if status in ("unknown", "ambiguous", "needs_review"):
        return True

    # Default: don't escalate
    return False


def get_scoring_weights(question_type: str) -> dict:
    """P39: 统一评分权重。从 config 读取，未配置题型返回默认值。

    Returns dict with keys: correctness, process, format (三维度).
    """
    _DEFAULT = {"correctness": 50, "process": 30, "format": 20}
    raw = SCORING_WEIGHTS.get(question_type)
    if not raw:
        return dict(_DEFAULT)
    # 映射到三维度: correctness / process / format
    if question_type == "解答题":
        return {"correctness": 50, "process": 30, "format": 20}
    if question_type == "证明题":
        return {"correctness": 40, "process": 40, "format": 20}
    # 选择题/填空题: 全部归入 correctness
    return {"correctness": 100, "process": 0, "format": 0}


def is_user_answer_empty(answer, question_type=None) -> bool:
    """P39: 统一判断用户是否作答。"""
    return not (answer or "").strip()


# P39: 批改意图模式
GRADING_INTENT_GRADE = "grade"
GRADING_INTENT_VIEW = "view_solution_only"


def resolve_grading_intent(question: dict | None = None, user_answer: str | None = None,
                           action: str | None = None) -> dict:
    """P39: 统一批改意图判断。

    Returns:
        {"intent": "grade" | "view_solution_only", "reason": str}
    """
    if action == "view_solution":
        return {"intent": GRADING_INTENT_VIEW, "reason": "explicit_view_request"}
    if is_user_answer_empty(user_answer):
        return {"intent": GRADING_INTENT_VIEW, "reason": "empty_answer"}
    return {"intent": GRADING_INTENT_GRADE, "reason": "has_answer"}

# OCR Vision API（pytesseract 不足时的云 fallback）
VISION_API_KEY = os.getenv("VISION_API_KEY", "")
VISION_BASE_URL = os.getenv("VISION_BASE_URL", "https://api.openai.com/v1")
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o")

# ── Mathpix OCR（商业级数学公式识别，优先级最高） ──
# 获取方式：https://dashboard.mathpix.com/
MATHPIX_APP_ID = os.getenv("MATHPIX_APP_ID", "")
MATHPIX_APP_KEY = os.getenv("MATHPIX_APP_KEY", "")

# 规范解题轨迹生成
CANONICAL_SOLVE_MODEL = os.getenv("CANONICAL_SOLVE_MODEL", "")
VERIFY_STEPS = os.getenv("VERIFY_STEPS", "true").lower() == "true"

# 批改提速策略
# True: 只有题目已经缓存 canonical trace 时才走图匹配；无缓存时跳过临时
# 生成多套规范解轨迹，直接进入标准答案 + LLM 批改，减少重型 LLM 调用。
FAST_GRADING_SKIP_UNCACHED_CANONICAL = (
    os.getenv("FAST_GRADING_SKIP_UNCACHED_CANONICAL", "true").lower() == "true"
)
FAST_GRADING_LOCAL_DIAGNOSIS_FOR_GRAPH = (
    os.getenv("FAST_GRADING_LOCAL_DIAGNOSIS_FOR_GRAPH", "true").lower() == "true"
)

# 存储路径
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
ERROR_NOTEBOOK_PATH = os.path.join(STORAGE_DIR, "error_notebook.json")
STUDENT_PROFILE_PATH = os.path.join(STORAGE_DIR, "student_profile.json")

# Repository Layer 配置
REPOSITORY_DB_PATH = os.path.join(STORAGE_DIR, "app.db")
REPOSITORY_USERS_DATA_DIR = os.path.join(STORAGE_DIR, "users_data")
