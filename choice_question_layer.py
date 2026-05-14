"""choice_question_layer.py — 选择题处理层

完整的单选题系统：

1. 选项解析
   - normalize: "BB" → "B"

2. 多选冲突检测
   - "BC" 对于单选题 → 直接判错

3. 选项语义识别
   - "选C" / "答案是C" / "我觉得是c" → "C"

4. 错误选项分析
   - 不是只说"你错了"
   - 而是"你为什么会选B"
   - distractor analysis

5. 反向知识点映射
   - 选B → 说明不会：凸函数性质
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from dataclasses_json import dataclass_json


# ═══════════════════════════════════════════════
# 选项类型定义
# ═══════════════════════════════════════════════

class ChoiceType(Enum):
    """选择题类型"""
    SINGLE = "single"      # 单选题
    MULTIPLE = "multiple"  # 多选题
    TRUE_FALSE = "true_false"  # 判断题


# ═══════════════════════════════════════════════
# 语义模式定义
# ═══════════════════════════════════════════════

OPTION_PATTERNS = {
    # 直接选项
    "direct": [
        r"^[A-Ea-e]$",
        r"^[A-Ea-e]{1}$",
    ],
    # 带冒号的选项
    "with_colon": [
        r"^[A-Ea-e]\s*[:：]",
        r"[：:]\s*([A-Ea-e])",
    ],
    # 语义选项
    "semantic": {
        "choose": [
            r"选\s*([A-Ea-e])",
            r"选择\s*([A-Ea-e])",
            r"选([A-Ea-e])",
            r"答案\s*[是为]?\s*([A-Ea-e])",
            r"我认为\s*([A-Ea-e])",
            r"我觉得\s*([A-Ea-e])",
            r"我选\s*([A-Ea-e])",
            r"是\s*([A-Ea-e])",
        ],
        "think": [
            r"觉得\s*是?\s*([A-Ea-e])",
            r"感觉\s*是?\s*([A-Ea-e])",
            r"大概\s*是?\s*([A-Ea-e])",
            r"应该\s*是?\s*([A-Ea-e])",
        ],
        "answer": [
            r"答案\s*[是为]?\s*([A-Ea-e])",
            r"正确\s*答案是?\s*([A-Ea-e])",
            r"应该\s*选?\s*([A-Ea-e])",
        ]
    }
}


# ═══════════════════════════════════════════════
# 数据模型定义
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class DistractorInfo:
    """干扰项信息"""
    option: str
    wrong_reason: str
    related_knowledge: str
    common_misconception: str
    frequency: int = 0


@dataclass_json
@dataclass
class KnowledgeMapping:
    """知识点映射"""
    topic: str
    topic_display: str
    related_options: List[str] = field(default_factory=list)
    knowledge_points: List[str] = field(default_factory=list)


@dataclass_json
@dataclass
class ChoiceQuestion:
    """选择题"""
    question_id: str
    question_text: str
    choice_type: ChoiceType
    options: Dict[str, str]
    correct_answer: str
    explanation: str = ""
    knowledge_topic: str = ""
    distractor_analysis: List[DistractorInfo] = field(default_factory=list)
    knowledge_mappings: List[KnowledgeMapping] = field(default_factory=list)


@dataclass_json
@dataclass
class ChoiceScoringResult:
    """选择题评分结果"""
    is_correct: bool
    student_answer: str
    correct_answer: str
    normalized_answer: str
    is_multi_select_conflict: bool
    choice_type: str
    score: float
    max_score: float
    distractor_feedback: Optional[DistractorInfo] = None
    knowledge_gaps: List[str] = field(default_factory=list)
    explanation: str = ""
    detailed_feedback: str = ""


# ═══════════════════════════════════════════════
# 选项规范化器
# ═══════════════════════════════════════════════

class OptionNormalizer:
    """
    选项规范化器

    将各种输入格式规范化为标准选项：
    - "BB" → "B"
    - "选C" → "C"
    - "答案是C" → "C"
    """

    @staticmethod
    def normalize(student_input: str, choice_type: ChoiceType = ChoiceType.SINGLE) -> Tuple[str, str]:
        """
        规范化学生输入

        Returns:
            (normalized_answer, original_cleaned)

        Examples:
            "BB" → "B"
            "选C" → "C"
            "答案是C" → "C"
        """
        if not student_input:
            return "", ""

        cleaned = student_input.strip()

        if choice_type == ChoiceType.SINGLE:
            return OptionNormalizer._normalize_single(cleaned)
        elif choice_type == ChoiceType.MULTIPLE:
            return OptionNormalizer._normalize_multiple(cleaned)
        else:
            return OptionNormalizer._normalize_single(cleaned)

    @staticmethod
    def _normalize_single(raw_input: str) -> Tuple[str, str]:
        """规范化单选题输入"""
        cleaned = raw_input.strip().upper()

        if re.match(r"^[A-E]$", cleaned):
            return cleaned, cleaned

        for option in re.findall(r"[A-Ea-e]", cleaned):
            return option.upper(), option.upper()

        for category, patterns in OPTION_PATTERNS["semantic"].items():
            for pattern in patterns:
                match = re.search(pattern, cleaned, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if groups:
                        return groups[0].upper(), raw_input.strip()

        return "", raw_input.strip()

    @staticmethod
    def _normalize_multiple(raw_input: str) -> Tuple[str, str]:
        """规范化多选题输入"""
        cleaned = raw_input.strip().upper()
        options = re.findall(r"[A-Ea-e]", cleaned)

        if not options:
            return "", raw_input.strip()

        unique_options = []
        for opt in options:
            if opt.upper() not in unique_options:
                unique_options.append(opt.upper())

        return "".join(unique_options), "".join(unique_options)


# ═══════════════════════════════════════════════
# 多选冲突检测器
# ═══════════════════════════════════════════════

class MultiSelectConflictDetector:
    """
    多选冲突检测器

    对于单选题，如果学生选了多个选项，应直接判错
    """

    @staticmethod
    def check_conflict(
        normalized_answer: str,
        choice_type: ChoiceType
    ) -> Tuple[bool, str]:
        """
        检测多选冲突

        Returns:
            (has_conflict, conflict_message)
        """
        if choice_type == ChoiceType.SINGLE:
            if len(normalized_answer) > 1:
                return True, f"单选题只能选择一个选项，您选择了 {normalized_answer}"
            elif len(normalized_answer) == 0:
                return True, "您没有选择任何选项"
            else:
                return False, ""

        elif choice_type == ChoiceType.TRUE_FALSE:
            valid_answers = {"A", "B", "T", "F", "TRUE", "FALSE", "0", "1"}
            if normalized_answer not in valid_answers:
                return True, f"判断题答案无效: {normalized_answer}"
            return False, ""

        return False, ""

    @staticmethod
    def is_multi_select_conflict(
        student_input: str,
        choice_type: ChoiceType
    ) -> bool:
        """快速检查是否存在多选冲突"""
        if choice_type != ChoiceType.SINGLE:
            return False

        cleaned = student_input.strip().upper()
        options = re.findall(r"[A-Ea-e]", cleaned)

        return len(options) > 1


# ═══════════════════════════════════════════════
# 干扰项分析器
# ═══════════════════════════════════════════════

class DistractorAnalyzer:
    """
    干扰项分析器 (Distractor Analysis)

    真正高级系统不是只说"你错了"，而是：
    "你为什么会选B"

    例如：
    - B 对应：误以为单调性推出凹凸性
    """

    def __init__(self):
        self.distractor_patterns = {
            "A": {
                "wrong_reason": "错误理解了基本概念",
                "related_knowledge": "函数基本性质",
                "common_misconception": "混淆了相关但不同的概念"
            },
            "B": {
                "wrong_reason": "误以为单调性推出凹凸性",
                "related_knowledge": "凸函数性质",
                "common_misconception": "从特殊案例推导一般结论"
            },
            "C": {
                "wrong_reason": "忽略了条件的必要性",
                "related_knowledge": "定理适用条件",
                "common_misconception": "忽视了定理使用的前提条件"
            },
            "D": {
                "wrong_reason": "计算或推导错误",
                "related_knowledge": "运算技巧",
                "common_misconception": "在复杂计算中出错"
            },
            "E": {
                "wrong_reason": "遗漏了关键情况",
                "related_knowledge": "分类讨论",
                "common_misconception": "只考虑了明显的情况"
            }
        }

    def get_distractor_info(self, wrong_answer: str) -> DistractorInfo:
        """获取干扰项详细信息"""
        pattern = self.distractor_patterns.get(wrong_answer, {})

        return DistractorInfo(
            option=wrong_answer,
            wrong_reason=pattern.get("wrong_reason", "选择了不正确的选项"),
            related_knowledge=pattern.get("related_knowledge", "相关知识点"),
            common_misconception=pattern.get("common_misconception", "常见误解"),
            frequency=0
        )

    def get_distractor_feedback(self, wrong_answer: str, question: ChoiceQuestion) -> str:
        """获取针对特定题目的干扰项反馈"""
        distractor = self.get_distractor_info(wrong_answer)

        for d in question.distractor_analysis:
            d_option = d.option if hasattr(d, 'option') else d.get('option', '')
            d_reason = d.wrong_reason if hasattr(d, 'wrong_reason') else d.get('wrong_reason', '')
            d_knowledge = d.related_knowledge if hasattr(d, 'related_knowledge') else d.get('related_knowledge', '')
            d_misconception = d.common_misconception if hasattr(d, 'common_misconception') else d.get('common_misconception', '')

            if d_option.upper() == wrong_answer.upper():
                return f"您选择了{wrong_answer}。{d_reason}。相关知识点：{d_knowledge}。{d_misconception}。"

        return f"您选择了{wrong_answer}。{distractor.wrong_reason}。建议复习：{distractor.related_knowledge}。{distractor.common_misconception}。"


# ═══════════════════════════════════════════════
# 知识点反向映射器
# ═══════════════════════════════════════════════

class KnowledgeReverseMapper:
    """
    知识点反向映射器

    选B → 说明不会：凸函数性质

    这帮助理解学生的知识薄弱点
    """

    KNOWLEDGE_MAPPINGS = {
        "A": {
            "knowledge_topic": "函数基本性质",
            "knowledge_points": ["定义域", "值域", "基本性质"],
            "missing_knowledge": "对函数基本概念的理解不准确"
        },
        "B": {
            "knowledge_topic": "凸函数性质",
            "knowledge_points": ["凸函数定义", "Jensen不等式", "凹凸性判别"],
            "missing_knowledge": "对凸函数性质的理解不透彻"
        },
        "C": {
            "knowledge_topic": "定理适用条件",
            "knowledge_points": ["定理前提条件", "使用范围", "注意事项"],
            "missing_knowledge": "对定理适用条件的掌握不牢固"
        },
        "D": {
            "knowledge_topic": "运算技巧",
            "knowledge_points": ["求导法则", "积分技巧", "化简方法"],
            "missing_knowledge": "运算能力需要加强"
        },
        "E": {
            "knowledge_topic": "分类讨论",
            "knowledge_points": ["情况分类", "边界处理", "特殊值分析"],
            "missing_knowledge": "缺乏分类讨论的意识"
        }
    }

    @classmethod
    def get_knowledge_gaps(cls, wrong_answer: str) -> List[str]:
        """获取知识点缺口"""
        mapping = cls.KNOWLEDGE_MAPPINGS.get(wrong_answer.upper(), {})

        gaps = []
        if mapping:
            gaps.append(f"知识点主题: {mapping.get('knowledge_topic', '未知')}")
            gaps.append(f"建议复习: {', '.join(mapping.get('knowledge_points', []))}")
            gaps.append(f"问题诊断: {mapping.get('missing_knowledge', '知识点掌握不牢固')}")

        return gaps

    @classmethod
    def get_knowledge_topic(cls, wrong_answer: str) -> str:
        """获取知识点主题"""
        mapping = cls.KNOWLEDGE_MAPPINGS.get(wrong_answer.upper(), {})
        return mapping.get("knowledge_topic", "未分类")

    @classmethod
    def get_study_suggestion(cls, wrong_answer: str) -> str:
        """获取学习建议"""
        mapping = cls.KNOWLEDGE_MAPPINGS.get(wrong_answer.upper(), {})
        return mapping.get("missing_knowledge", "建议系统复习相关知识点")


# ═══════════════════════════════════════════════
# 统一选择题评分器
# ═══════════════════════════════════════════════

class UnifiedChoiceScorer:
    """
    统一选择题评分器

    完整的单选题系统：
    1. 选项解析
    2. 多选冲突检测
    3. 选项语义识别
    4. 干扰项分析
    5. 知识点反向映射
    """

    def __init__(self):
        self.normalizer = OptionNormalizer()
        self.conflict_detector = MultiSelectConflictDetector()
        self.distractor_analyzer = DistractorAnalyzer()
        self.knowledge_mapper = KnowledgeReverseMapper()

    def score_choice(
        self,
        question: ChoiceQuestion,
        student_input: str,
        score_if_correct: float = 100.0
    ) -> ChoiceScoringResult:
        """
        评分选择题

        Args:
            question: 选择题题目
            student_input: 学生输入
            score_if_correct: 正确时的得分

        Returns:
            完整评分结果
        """
        choice_type = question.choice_type

        normalized_answer, original_cleaned = self.normalizer.normalize(
            student_input, choice_type
        )

        has_conflict, conflict_message = self.conflict_detector.check_conflict(
            normalized_answer, choice_type
        )

        if has_conflict:
            return ChoiceScoringResult(
                is_correct=False,
                student_answer=student_input.strip(),
                correct_answer=question.correct_answer,
                normalized_answer=normalized_answer,
                is_multi_select_conflict=True,
                choice_type=choice_type.value,
                score=0.0,
                max_score=score_if_correct,
                distractor_feedback=None,
                knowledge_gaps=[],
                explanation="",
                detailed_feedback=conflict_message
            )

        is_correct = normalized_answer.upper() == question.correct_answer.upper()

        if is_correct:
            return ChoiceScoringResult(
                is_correct=True,
                student_answer=student_input.strip(),
                correct_answer=question.correct_answer,
                normalized_answer=normalized_answer,
                is_multi_select_conflict=False,
                choice_type=choice_type.value,
                score=score_if_correct,
                max_score=score_if_correct,
                distractor_feedback=None,
                knowledge_gaps=[],
                explanation=question.explanation,
                detailed_feedback=f"正确！答案确实是 {question.correct_answer}。{question.explanation}"
            )

        distractor_feedback = self.distractor_analyzer.get_distractor_feedback(
            normalized_answer, question
        )

        knowledge_gaps = self.knowledge_mapper.get_knowledge_gaps(normalized_answer)

        wrong_reason = self._get_wrong_reason(normalized_answer, question)

        detailed_feedback = self._generate_detailed_feedback(
            question, normalized_answer, distractor_feedback, knowledge_gaps
        )

        return ChoiceScoringResult(
            is_correct=False,
            student_answer=student_input.strip(),
            correct_answer=question.correct_answer,
            normalized_answer=normalized_answer,
            is_multi_select_conflict=False,
            choice_type=choice_type.value,
            score=0.0,
            max_score=score_if_correct,
            distractor_feedback=self.distractor_analyzer.get_distractor_info(normalized_answer),
            knowledge_gaps=knowledge_gaps,
            explanation=question.explanation,
            detailed_feedback=detailed_feedback
        )

    def _get_wrong_reason(self, wrong_answer: str, question: ChoiceQuestion) -> str:
        """获取错误原因"""
        for d in question.distractor_analysis:
            d_option = d.option if hasattr(d, 'option') else d.get('option', '')
            d_reason = d.wrong_reason if hasattr(d, 'wrong_reason') else d.get('wrong_reason', '')

            if d_option.upper() == wrong_answer.upper():
                return d_reason

        return self.distractor_analyzer.get_distractor_info(wrong_answer).wrong_reason

    def _generate_detailed_feedback(
        self,
        question: ChoiceQuestion,
        wrong_answer: str,
        distractor_feedback: str,
        knowledge_gaps: List[str]
    ) -> str:
        """生成详细反馈"""
        lines = []
        lines.append(f"您的答案: {wrong_answer}")
        lines.append(f"正确答案: {question.correct_answer}")
        lines.append("")
        lines.append(distractor_feedback)
        lines.append("")
        lines.append("知识点分析:")

        for gap in knowledge_gaps:
            lines.append(f"  - {gap}")

        lines.append("")
        lines.append("解析:")
        lines.append(f"  {question.explanation}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def normalize_choice_input(
    student_input: str,
    choice_type: ChoiceType = ChoiceType.SINGLE
) -> str:
    """快速规范化学生输入"""
    normalized, _ = OptionNormalizer.normalize(student_input, choice_type)
    return normalized


def check_multi_select_conflict(
    student_input: str,
    choice_type: ChoiceType = ChoiceType.SINGLE
) -> Tuple[bool, str]:
    """快速检测多选冲突"""
    normalized, _ = OptionNormalizer.normalize(student_input, choice_type)
    return MultiSelectConflictDetector.check_conflict(normalized, choice_type)


def score_choice_question(
    question: ChoiceQuestion,
    student_input: str,
    score_if_correct: float = 100.0
) -> ChoiceScoringResult:
    """快速评分选择题"""
    scorer = UnifiedChoiceScorer()
    return scorer.score_choice(question, student_input, score_if_correct)


def format_choice_feedback(result: ChoiceScoringResult) -> str:
    """格式化选择题反馈"""
    lines = []
    lines.append("=" * 60)
    lines.append("【选择题评分结果】")
    lines.append("=" * 60)
    lines.append(f"题型: {result.choice_type}")
    lines.append(f"您的答案: {result.student_answer}")
    lines.append(f"规范化答案: {result.normalized_answer}")
    lines.append(f"正确答案: {result.correct_answer}")

    if result.is_multi_select_conflict:
        lines.append(f"评分: {result.score:.1f}/{result.max_score:.1f}")
        lines.append("")
        lines.append("【问题】")
        lines.append(result.detailed_feedback)
    elif result.is_correct:
        lines.append(f"评分: {result.score:.1f}/{result.max_score:.1f}")
        lines.append("")
        lines.append("【正确！】")
        lines.append(result.detailed_feedback)
    else:
        lines.append(f"评分: {result.score:.1f}/{result.max_score:.1f}")
        lines.append("")
        lines.append("【错误分析】")
        lines.append(result.detailed_feedback)

    lines.append("=" * 60)

    return "\n".join(lines)
