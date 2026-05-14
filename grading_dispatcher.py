"""grading_dispatcher.py — 统一批改调度器

根据题型自动选择对应的批改系统：

┌─────────────────────────────────────────────────────────┐
│                   GradingDispatcher                      │
│                                                          │
│   输入: question_type + student_answer                   │
│                 │                                        │
│         ┌───────┴───────┐                               │
│         ▼               ▼                                │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│   │  选择题   │   │  填空题   │   │  解答题   │   ...   │
│   │  Choice   │   │  Fill    │   │ Solution │          │
│   │  Grader   │   │  Grader  │   │  Grader  │          │
│   └──────────┘   └──────────┘   └──────────┘          │
│          │               │               │               │
│          └───────────────┴───────────────┘               │
│                          │                               │
│                          ▼                               │
│                  GradingResult                           │
└─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
from dataclasses_json import dataclass_json

from common_enums import ErrorLevel, StepStatus


# ═══════════════════════════════════════════════
# 题型枚举
# ═══════════════════════════════════════════════

class QuestionType(Enum):
    """题目类型"""
    SINGLE_CHOICE = "single_choice"     # 单选题
    MULTIPLE_CHOICE = "multiple_choice" # 多选题
    FILL_BLANK = "fill_blank"          # 填空题
    SOLUTION = "solution"               # 解答题
    PROOF = "proof"                     # 证明题
    UNKNOWN = "unknown"                 # 未知类型


# ═══════════════════════════════════════════════
# 统一批改结果
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class GradingResult:
    """统一批改结果"""
    question_id: str
    question_type: str
    is_correct: bool
    score: float
    max_score: float
    score_percentage: float

    answer_correct: bool = True
    error_level: str = "correct"
    error_message: str = ""

    step_evaluations: List[Dict[str, Any]] = field(default_factory=list)
    error_analysis: List[Dict[str, Any]] = field(default_factory=list)
    learning_suggestions: List[Dict[str, Any]] = field(default_factory=list)

    standard_solution: List[str] = field(default_factory=list)
    alternative_solutions: List[Dict[str, Any]] = field(default_factory=list)

    detailed_feedback: str = ""
    partial_credit_explanation: str = ""

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatcherConfig:
    """调度器配置"""
    enable_partial_credit: bool = True
    enable_multi_solution: bool = True
    enable_learning_suggestions: bool = True
    enable_detailed_feedback: bool = True


# ═══════════════════════════════════════════════
# 批改调度器
# ═══════════════════════════════════════════════

class GradingDispatcher:
    """
    统一批改调度器

    根据题型自动选择对应的批改系统
    """

    def __init__(self, config: DispatcherConfig = None):
        self.config = config or DispatcherConfig()
        self._grader_cache: Dict[str, Any] = {}

    def grade(
        self,
        question_id: str,
        question_type: Union[QuestionType, str],
        question_text: str,
        student_answer: str,
        options: List[str] = None,
        standard_answer: str = None,
        rubrics: Dict[str, Any] = None
    ) -> GradingResult:
        """
        统一的批改入口

        Args:
            question_id: 题目ID
            question_type: 题型
            question_text: 题目文本
            student_answer: 学生答案
            options: 选项列表（用于选择题）
            standard_answer: 标准答案
            rubrics: 评分细则

        Returns:
            GradingResult: 统一的批改结果
        """
        qtype = self._normalize_question_type(question_type)

        if qtype == QuestionType.SINGLE_CHOICE:
            return self._grade_single_choice(
                question_id, question_text, student_answer,
                options, standard_answer
            )
        elif qtype == QuestionType.MULTIPLE_CHOICE:
            return self._grade_multiple_choice(
                question_id, question_text, student_answer,
                options, standard_answer
            )
        elif qtype == QuestionType.FILL_BLANK:
            return self._grade_fill_blank(
                question_id, question_text, student_answer,
                standard_answer, rubrics
            )
        elif qtype == QuestionType.SOLUTION:
            return self._grade_solution(
                question_id, question_text, student_answer,
                standard_answer, rubrics
            )
        elif qtype == QuestionType.PROOF:
            return self._grade_proof(
                question_id, question_text, student_answer,
                standard_answer, rubrics
            )
        else:
            return self._grade_unknown(question_id, question_text, student_answer)

    def _normalize_question_type(
        self, question_type: Union[QuestionType, str]
    ) -> QuestionType:
        """规范化题型"""
        if isinstance(question_type, QuestionType):
            return question_type

        type_str = str(question_type).lower().strip()

        type_mapping = {
            "single": QuestionType.SINGLE_CHOICE,
            "choice": QuestionType.SINGLE_CHOICE,
            "单选": QuestionType.SINGLE_CHOICE,
            "单选题": QuestionType.SINGLE_CHOICE,
            "multiple": QuestionType.MULTIPLE_CHOICE,
            "多选": QuestionType.MULTIPLE_CHOICE,
            "多选题": QuestionType.MULTIPLE_CHOICE,
            "fill": QuestionType.FILL_BLANK,
            "blank": QuestionType.FILL_BLANK,
            "填空": QuestionType.FILL_BLANK,
            "填空题": QuestionType.FILL_BLANK,
            "solution": QuestionType.SOLUTION,
            "解答": QuestionType.SOLUTION,
            "解答题": QuestionType.SOLUTION,
            "proof": QuestionType.PROOF,
            "证明": QuestionType.PROOF,
            "证明题": QuestionType.PROOF,
        }

        for key, qtype in type_mapping.items():
            if key in type_str:
                return qtype

        return QuestionType.UNKNOWN

    # ═══════════════════════════════════════════════
    # 单选题批改
    # ═══════════════════════════════════════════════

    def _grade_single_choice(
        self,
        question_id: str,
        question_text: str,
        student_answer: str,
        options: List[str],
        standard_answer: str
    ) -> GradingResult:
        """批改单选题"""
        try:
            from choice_question_layer import (
                OptionNormalizer,
                DistractorAnalyzer,
                ChoiceType,
                SingleChoiceGrader
            )

            normalized, _ = OptionNormalizer.normalize(student_answer, ChoiceType.SINGLE)
            is_correct = normalized.upper() == standard_answer.upper()

            if is_correct:
                score = 5.0
                error_level = "correct"
                feedback = "回答正确！"
            else:
                score = 0.0
                error_level = "wrong"

                distractor = DistractorAnalyzer()
                distractor_info = distractor.get_distractor_info(normalized)
                feedback = f"您选择了{normalized}。{distractor_info.wrong_reason}。相关知识点：{distractor_info.related_knowledge}。"

            return GradingResult(
                question_id=question_id,
                question_type="single_choice",
                is_correct=is_correct,
                score=score,
                max_score=5.0,
                score_percentage=100.0 if is_correct else 0.0,
                answer_correct=is_correct,
                error_level=error_level,
                error_message="" if is_correct else f"正确答案是{standard_answer}",
                detailed_feedback=feedback
            )
        except ImportError:
            return self._grade_with_fallback(
                question_id, "single_choice", student_answer, standard_answer, 5.0
            )

    def _grade_multiple_choice(
        self,
        question_id: str,
        question_text: str,
        student_answer: str,
        options: List[str],
        standard_answer: str
    ) -> GradingResult:
        """批改多选题"""
        try:
            from choice_question_layer import (
                OptionNormalizer,
                ChoiceType
            )

            normalized, _ = OptionNormalizer.normalize(student_answer, ChoiceType.MULTIPLE)

            student_set = set(normalized.upper())
            standard_set = set(standard_answer.upper())

            if student_set == standard_set:
                is_correct = True
                score = 5.0
                feedback = "回答正确！"
            elif student_set & standard_set:
                is_correct = False
                score = 2.5
                feedback = f"部分正确。你选择了{normalized}，正确答案应该是{standard_answer}。"
            else:
                is_correct = False
                score = 0.0
                feedback = f"回答错误。你选择了{normalized}，正确答案应该是{standard_answer}。"

            return GradingResult(
                question_id=question_id,
                question_type="multiple_choice",
                is_correct=is_correct,
                score=score,
                max_score=5.0,
                score_percentage=50.0 if score == 2.5 else (100.0 if is_correct else 0.0),
                answer_correct=is_correct,
                error_level="correct" if is_correct else "wrong",
                detailed_feedback=feedback
            )
        except ImportError:
            return self._grade_with_fallback(
                question_id, "multiple_choice", student_answer, standard_answer, 5.0
            )

    # ═══════════════════════════════════════════════
    # 填空题批改
    # ═══════════════════════════════════════════════

    def _grade_fill_blank(
        self,
        question_id: str,
        question_text: str,
        student_answer: str,
        standard_answer: str,
        rubrics: Dict[str, Any]
    ) -> GradingResult:
        """批改填空题"""
        try:
            from fill_blank_layer import (
                ExpressionNormalizer,
                SymbolicEquivalenceVerifier
            )

            student_normalized = ExpressionNormalizer.normalize_expression(student_answer)
            standard_normalized = ExpressionNormalizer.normalize_expression(standard_answer)

            is_equivalent, confidence = SymbolicEquivalenceVerifier.are_equivalent(
                student_normalized, standard_normalized
            )

            if is_equivalent:
                score = 10.0
                is_correct = True
                feedback = "回答正确！"
            elif confidence >= 0.8:
                score = 8.0
                is_correct = True
                feedback = f"答案正确（置信度{confidence:.0%}）"
            elif confidence >= 0.5:
                score = 5.0
                is_correct = False
                feedback = f"答案部分正确（置信度{confidence:.0%}）"
            else:
                score = 0.0
                is_correct = False
                feedback = f"答案错误。正确答案应为：{standard_answer}"

            return GradingResult(
                question_id=question_id,
                question_type="fill_blank",
                is_correct=is_correct,
                score=score,
                max_score=10.0,
                score_percentage=score / 10.0 * 100,
                answer_correct=is_correct,
                error_level="correct" if is_correct else "wrong",
                detailed_feedback=feedback
            )
        except ImportError:
            return self._grade_with_fallback(
                question_id, "fill_blank", student_answer, standard_answer, 10.0
            )

    # ═══════════════════════════════════════════════
    # 解答题批改
    # ═══════════════════════════════════════════════

    def _grade_solution(
        self,
        question_id: str,
        question_text: str,
        student_answer: str,
        standard_answer: str,
        rubrics: Dict[str, Any]
    ) -> GradingResult:
        """批改解答题"""
        try:
            from solution_question_layer import (
                SolutionQuestion,
                UnifiedSolutionScorer
            )

            question = SolutionQuestion(
                question_id=question_id,
                question_text=question_text,
                correct_solution=standard_answer,
                rubric=rubrics or {}
            )

            scorer = UnifiedSolutionScorer()
            scoring_result = scorer.score_solution(question, student_answer, standard_answer)

            feedback = self._generate_solution_feedback(
                [], scoring_result, True, "标准解法"
            )

            return GradingResult(
                question_id=question_id,
                question_type="solution",
                is_correct=scoring_result.is_correct,
                score=scoring_result.total_score,
                max_score=scoring_result.max_score,
                score_percentage=scoring_result.score_percentage,
                step_evaluations=getattr(scoring_result, 'step_scores', []),
                error_analysis=getattr(scoring_result, 'error_analysis', []),
                learning_suggestions=getattr(scoring_result, 'learning_suggestions', []),
                standard_solution=standard_answer.split('\n') if standard_answer else [],
                detailed_feedback=feedback,
                metadata={"method": "solution_layer"}
            )
        except Exception:
            return self._grade_with_fallback(
                question_id, "solution", student_answer, standard_answer, 15.0
            )

    # ═══════════════════════════════════════════════
    # 证明题批改
    # ═══════════════════════════════════════════════

    def _grade_proof(
        self,
        question_id: str,
        question_text: str,
        student_answer: str,
        standard_answer: str,
        rubrics: Dict[str, Any]
    ) -> GradingResult:
        """批改证明题"""
        try:
            from proof_question_layer import (
                ProofQuestion,
                UnifiedProofScorer,
                ProofStrategy
            )

            expected_strategies = rubrics.get("expected_strategies", []) if rubrics else []
            expected_theorems = rubrics.get("expected_theorems", []) if rubrics else []

            question = ProofQuestion(
                question_id=question_id,
                question_text=question_text,
                conditions=rubrics.get("conditions", []) if rubrics else [],
                conclusion=rubrics.get("conclusion", "") if rubrics else "",
                expected_strategies=[ProofStrategy(s) for s in expected_strategies],
                expected_theorems=expected_theorems,
                key_steps=rubrics.get("key_steps", []) if rubrics else []
            )

            scorer = UnifiedProofScorer()
            result = scorer.score_proof(question, student_answer)

            feedback = scorer._generate_detailed_feedback(
                ProofStrategy(result.strategy_used),
                result.strategy_confidence,
                [],
                result.logical_gaps,
                result.missing_justifications
            )

            return GradingResult(
                question_id=question_id,
                question_type="proof",
                is_correct=result.is_correct,
                score=result.total_score,
                max_score=result.max_score,
                score_percentage=result.score_percentage,
                step_evaluations=[],
                error_analysis=[{"type": "logic_gap", "gaps": result.logical_gaps}],
                learning_suggestions=[],
                detailed_feedback=feedback,
                partial_credit_explanation=result.partial_credit_explanation,
                metadata={
                    "strategy_used": result.strategy_used,
                    "strategy_confidence": result.strategy_confidence
                }
            )
        except ImportError:
            return self._grade_with_fallback(
                question_id, "proof", student_answer, standard_answer, 15.0
            )

    # ═══════════════════════════════════════════════
    # 未知类型处理
    # ═══════════════════════════════════════════════

    def _grade_unknown(
        self,
        question_id: str,
        question_text: str,
        student_answer: str
    ) -> GradingResult:
        """处理未知题型"""
        return GradingResult(
            question_id=question_id,
            question_type="unknown",
            is_correct=False,
            score=0.0,
            max_score=0.0,
            score_percentage=0.0,
            answer_correct=False,
            error_level="unknown_type",
            error_message="无法识别题型",
            detailed_feedback="抱歉，无法处理未知题型的批改。"
        )

    # ═══════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════

    def _grade_with_fallback(
        self,
        question_id: str,
        question_type: str,
        student_answer: str,
        standard_answer: str,
        max_score: float
    ) -> GradingResult:
        """备用批改方法（当对应模块不可用时）"""
        is_correct = student_answer.strip() == standard_answer.strip()
        score = max_score if is_correct else 0.0

        return GradingResult(
            question_id=question_id,
            question_type=question_type,
            is_correct=is_correct,
            score=score,
            max_score=max_score,
            score_percentage=score / max_score * 100 if max_score > 0 else 0,
            answer_correct=is_correct,
            error_level="correct" if is_correct else "wrong",
            detailed_feedback="正确！" if is_correct else f"错误。正确答案：{standard_answer}"
        )

    def _parse_solution_steps(self, solution_text: str) -> List[Dict[str, str]]:
        """解析解答文本为步骤列表"""
        lines = solution_text.strip().split('\n')
        steps = []

        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                steps.append({
                    "step_index": i,
                    "operation": line,
                    "input_state": "",
                    "output_state": line
                })

        return steps

    def _generate_partial_credit_explanation(self, scoring_result: Any) -> str:
        """生成部分得分说明"""
        if hasattr(scoring_result, 'partial_credit_explanation'):
            return scoring_result.partial_credit_explanation

        dim_scores = getattr(scoring_result, 'dimension_scores', {})
        explanations = []

        for dim, score_data in dim_scores.items():
            if hasattr(score_data, 'score') and hasattr(score_data, 'max_score'):
                ratio = score_data.score / score_data.max_score if score_data.max_score > 0 else 0
                explanations.append(f"{dim}: {score_data.score:.1f}/{score_data.max_score:.1f}")

        return ", ".join(explanations) if explanations else ""

    def _generate_solution_feedback(
        self,
        steps: List[Dict],
        scoring_result: Any,
        is_valid_method: bool,
        method_name: str = "unknown"
    ) -> str:
        """生成解答题反馈"""
        lines = []

        lines.append(f"总分：{scoring_result.total_score:.1f}/{scoring_result.max_score:.1f}")
        lines.append(f"得分率：{scoring_result.score_percentage:.0f}%")
        lines.append("")

        if is_valid_method:
            lines.append(f"【方法】{method_name}")
        else:
            lines.append("【方法评估】")
            lines.append("您使用的方法与标准解法不同。")
            if hasattr(scoring_result, 'method_confidence'):
                lines.append(f"方法置信度：{scoring_result.method_confidence:.0%}")
            lines.append("")

        if hasattr(scoring_result, 'step_scores') and scoring_result.step_scores:
            lines.append("【步骤评估】")
            for step_score in scoring_result.step_scores[:5]:
                status = "OK" if step_score.get('correctness', 0) > 0.5 else "NG"
                lines.append(f"  [{status}] Step{step_score.get('step_index', 0) + 1}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def grade_question(
    question_id: str,
    question_type: str,
    question_text: str,
    student_answer: str,
    **kwargs
) -> GradingResult:
    """
    快速批改题目

    Args:
        question_id: 题目ID
        question_type: 题型（如 "single_choice", "solution", "proof"）
        question_text: 题目文本
        student_answer: 学生答案
        **kwargs: 其他参数（options, standard_answer, rubrics等）

    Returns:
        GradingResult: 批改结果
    """
    dispatcher = GradingDispatcher()
    return dispatcher.grade(
        question_id=question_id,
        question_type=question_type,
        question_text=question_text,
        student_answer=student_answer,
        **kwargs
    )
