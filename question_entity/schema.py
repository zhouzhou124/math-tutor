"""
QuestionEntity Schema — 不可变数学题实体

设计原则:
  - QuestionEntity 不可变（immutable），修改产生新版本
  - question_id 全局唯一，content_hash 检测内容漂移
  - 所有关联通过 question_id，禁止 [i] 位置式隐式关联
  - manual_review 是一级公民，不是错误状态
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto


# ═══════════════════════════════════════════════
# Entity Status
# ═══════════════════════════════════════════════

class EntityStatus(Enum):
    VERIFIED = auto()           # 人工校验通过
    AUTO_MATCHED = auto()       # 自动匹配（高置信度）
    MANUAL_REVIEW = auto()      # 待人工复核
    UNRESOLVED = auto()         # 尚未匹配
    DEPRECATED = auto()         # 已废弃（被新版本替代）


class FailureMode(Enum):
    """实体验证失败模式"""
    ANSWER_QUESTION_MISMATCH = auto()
    SOLUTION_QUESTION_MISMATCH = auto()
    OPTION_ANSWER_INVALID = auto()
    QUESTION_ID_CONFLICT = auto()
    LOW_ALIGNMENT_CONFIDENCE = auto()
    MISSING_OFFICIAL_ANSWER = auto()
    MISSING_SOLUTION = auto()
    MATH_SYNTAX_BROKEN = auto()
    CONTENT_DRIFT_DETECTED = auto()
    FINGERPRINT_COLLISION = auto()


# ═══════════════════════════════════════════════
# 子结构
# ═══════════════════════════════════════════════

@dataclass
class ChoiceOption:
    key: str          # A/B/C/D
    text: str         # LaTeX 选项文本


@dataclass
class QuestionStem:
    """题目正文（不可变）"""
    raw_text: str                          # 完整原始文本
    clean_text: str                        # 清理后的文本（去掉答案标记）
    options: list[ChoiceOption] = field(default_factory=list)
    question_type: str = "解答题"           # 选择题/填空题/解答题/证明题


@dataclass
class OfficialAnswer:
    """官方答案（通过 fingerprint 匹配，不可变）"""
    value: str                             # "C" / "2x+y=0" / "$\\frac{1}{6}$"
    source: str = ""                       # "solutions_2003.pdf"
    confidence: float = 0.0                # 匹配置信度
    matched_by: str = ""                   # "fingerprint" / "exact_number" / "manual"


@dataclass
class OfficialSolution:
    """官方解析（通过 fingerprint 匹配，不可变）"""
    steps_markdown: str = ""               # LaTeX 解析文本
    source: str = ""                       # 来源文件
    confidence: float = 0.0
    matched_by: str = ""


@dataclass
class AlignmentResult:
    """多阶段对齐验证结果"""
    numbering_score: float = 0.0           # 题号一致性
    formula_score: float = 0.0             # 公式一致性
    keyword_score: float = 0.0             # 关键词一致性
    structure_score: float = 0.0           # 结构一致性（选项/填空）
    option_score: float = 0.0              # 选项一致性（选择题专用）
    semantic_score: float = 0.0            # 语义整体一致性
    overall_score: float = 0.0             # 综合分数
    details: list[str] = field(default_factory=list)  # 可解释的细节


@dataclass
class EntityValidationResult:
    """实体级验证结果"""
    valid: bool = False
    status: EntityStatus = EntityStatus.UNRESOLVED
    failure_mode: FailureMode | None = None
    answer_alignment_score: float = 0.0
    solution_alignment_score: float = 0.0
    warnings: list[str] = field(default_factory=list)
    manual_review: bool = False


@dataclass
class BuildTrace:
    """构建过程追踪"""
    parser_version: str = ""
    entity_version: str = "v1"
    built_at: str = ""
    source_files: list[str] = field(default_factory=list)
    match_method: str = ""
    match_confidence: float = 0.0
    modifications: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════
# QuestionEntity (不可变)
# ═══════════════════════════════════════════════

@dataclass
class QuestionEntity:
    """数学题实体 — 系统唯一可信数据单元"""
    # 主键
    question_id: str                       # "math1_2003_choice_012"

    # 元数据
    year: int = 0
    subject: str = "math1"                 # math1/math2/math3
    status: EntityStatus = EntityStatus.UNRESOLVED

    # 题目内容
    stem: QuestionStem | None = None

    # 答案和解析（可选 — 通过匹配获得）
    official_answer: OfficialAnswer | None = None
    official_solution: OfficialSolution | None = None

    # 验证
    alignment: AlignmentResult | None = None
    validation: EntityValidationResult | None = None

    # 知识点
    knowledge_points: list[str] = field(default_factory=list)
    difficulty: str = "中等"
    score: int = 10

    # 指纹（用于检测内容漂移）
    content_hash: str = ""
    fingerprint: dict = field(default_factory=dict)

    # 构建追踪
    trace: BuildTrace | None = None
    revision: int = 1
    previous_hash: str = ""                # 上一版本 content_hash


# ═══════════════════════════════════════════════
# ID 生成
# ═══════════════════════════════════════════════

_TYPE_ABBR = {
    "选择题": "choice", "填空题": "fill",
    "解答题": "solve", "证明题": "proof",
}
_SUBJECT_ABBR = {
    "数学一": "math1", "数学二": "math2", "数学三": "math3",
}


def make_question_id(year: int, subject: str, qtype: str, number: int) -> str:
    """生成标准 question_id: math1_2003_choice_012"""
    subj = _SUBJECT_ABBR.get(subject, "math1")
    qtp = _TYPE_ABBR.get(qtype, "solve")
    return f"{subj}_{year}_{qtp}_{number:03d}"


def content_hash(text: str) -> str:
    """计算内容哈希（检测内容漂移）"""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def build_entity(
    question_data: dict,
    parser_version: str = "",
    match_method: str = "",
    match_confidence: float = 0.0,
) -> QuestionEntity:
    """从管道输出的 dict 构建 QuestionEntity"""
    year = question_data.get("year", 0)
    subject = question_data.get("category", "数学一")
    qtype = question_data.get("question_type", "解答题")

    # 生成 question_id（或用已有的）
    qid = question_data.get("question_id", "")
    if not qid:
        # 从旧格式 ID 转换: "2003-数一-012" → "math1_2003_choice_012"
        import re
        m = re.match(r"(\d{4})-数一-(\d{3})", qid)
        if m:
            qid = make_question_id(int(m.group(1)), "数学一", qtype, int(m.group(2)))
        else:
            qid = make_question_id(year, subject, qtype, len(question_data.get("question", "")))

    # 题目正文
    q_text = question_data.get("question", "")
    stem = QuestionStem(
        raw_text=q_text,
        clean_text=_clean_question_text(q_text),
        options=[
            ChoiceOption(key=k, text=v)
            for k, v in question_data.get("options", {}).items()
        ],
        question_type=qtype,
    )

    # 内容哈希
    ch = content_hash(q_text)

    # 官方答案
    std_ans = question_data.get("standard_answer", "")
    official_answer = None
    if std_ans and len(std_ans.strip()) > 0:
        official_answer = OfficialAnswer(
            value=std_ans,
            source=question_data.get("source", ""),
            confidence=match_confidence,
            matched_by=match_method,
        )

    # 官方解析
    sol_steps = question_data.get("solution_steps", [])
    official_solution = None
    if sol_steps:
        official_solution = OfficialSolution(
            steps_markdown="\n".join(sol_steps),
            source=question_data.get("source", ""),
            confidence=match_confidence,
            matched_by=match_method,
        )

    # 构建追踪
    trace = BuildTrace(
        parser_version=parser_version,
        entity_version="v1",
        built_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        source_files=[question_data.get("source", "")],
        match_method=match_method,
        match_confidence=match_confidence,
    )

    # 知识点
    kp = question_data.get("knowledge_points", [])

    entity = QuestionEntity(
        question_id=qid,
        year=year,
        subject=_SUBJECT_ABBR.get(subject, "math1"),
        stem=stem,
        official_answer=official_answer,
        official_solution=official_solution,
        knowledge_points=kp,
        difficulty=question_data.get("difficulty", "中等"),
        score=question_data.get("score", 10),
        content_hash=ch,
        trace=trace,
    )

    # 初始状态
    if official_answer and official_answer.confidence >= 0.70:
        entity.status = EntityStatus.AUTO_MATCHED
    elif official_answer:
        entity.status = EntityStatus.MANUAL_REVIEW
    else:
        entity.status = EntityStatus.UNRESOLVED

    return entity


def _clean_question_text(text: str) -> str:
    """清理题目文本（去掉答案标记）"""
    for marker in ["【答案】", "【解】", "【解析】", "【分析】"]:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]
    return text.strip()
