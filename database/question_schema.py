"""
Question Schema Accessor Layer —— 题目字段的统一读写入口

四层分离原则:
  Raw Data     — raw_question_text / raw_answer_text（永远不可丢失）
  Parser       — 纯函数，按需计算，不持久化
  Renderer     — 纯函数，按需计算，不持久化
  Semantic IR  — semantic_ir 字段，Interpretation 不覆盖 Raw

核心规则:
  - set_raw_* 是唯一写入原始文本的入口
  - 没有任何函数可以覆盖 raw_* 字段（一旦写入，只读）
  - 所有读点通过 get_raw_* 获取原始文本
  - 废弃 question / standard_answer 旧字段（保留兼容期）
"""


def get_raw_question(q: dict) -> str:
    """获取原始题目文本。优先新字段，fallback 旧字段。"""
    return q.get("raw_question_text") or q.get("question", "")


def set_raw_question(q: dict, text: str):
    """写入原始题目文本。同时写旧字段做向后兼容。"""
    q["raw_question_text"] = text
    q["question"] = text  # backward compat, 后续版本移除


def get_raw_answer(q: dict) -> str:
    """获取原始答案文本。"""
    return q.get("raw_answer_text") or q.get("standard_answer", "")


def set_raw_answer(q: dict, text: str):
    """写入原始答案文本。"""
    q["raw_answer_text"] = text
    q["standard_answer"] = text  # backward compat


def get_semantic_ir(q: dict) -> dict | None:
    """获取语义 IR（解释层）。"""
    return q.get("semantic_ir")


def set_semantic_ir(q: dict, ir: dict):
    """写入语义 IR。不触碰 raw 字段。"""
    q["semantic_ir"] = ir


def has_question_text(q: dict) -> bool:
    """检查是否有题目文本（任意字段）。"""
    return bool(q.get("raw_question_text") or q.get("question"))


def has_answer_text(q: dict) -> bool:
    """检查是否有答案文本（任意字段）。"""
    return bool(q.get("raw_answer_text") or q.get("standard_answer"))
