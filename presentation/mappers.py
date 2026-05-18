"""Mapper 层 - Domain Model → ViewModel 转换

使用 Enum 和 Design Token，消除散落的字符串和颜色值。
Renderer 只负责 HTML/CSS 渲染，不做任何展示逻辑判断。
"""

from typing import List, Optional

from repository.models import (
    ReasoningStep,
    ReasoningChain,
    ErrorRecord,
    DiagnosisResult,
    GradingResult,
    Question,
    DashboardData,
)
from rendering.tokens import (
    StepStatus,
    FormulaStatus,
    DiffStatus,
    ErrorCategory,
    Difficulty,
    QuestionType,
    TagType,
    STEP_STATUS_ICON,
    FORMULA_STATUS_ICON,
    DIFF_STATUS_ICON,
    QUESTION_TYPE_ICON,
    DIFFICULTY_TAG,
    ERROR_CATEGORY_ICON,
    STATUS_CSS_CLASS,
    STATUS_BORDER_COLOR,
    STATUS_BG_COLOR,
    ColorToken,
)
from .viewmodels import (
    StepCardViewModel,
    ErrorViewModel,
    DiagnosisViewModel,
    ScoreViewModel,
    FormulaViewModel,
    DiffViewModel,
    ChainViewModel,
    QuestionViewModel,
    DashboardViewModel,
)


def _parse_error_category(error_type_str: str) -> ErrorCategory:
    """将字符串映射为 ErrorCategory Enum"""
    mapping = {
        "概念错误": ErrorCategory.CONCEPT,
        "计算错误": ErrorCategory.CALCULATION,
        "逻辑错误": ErrorCategory.LOGIC,
        "方法错误": ErrorCategory.METHOD,
        "粗心错误": ErrorCategory.CARELESS,
    }
    return mapping.get(error_type_str, ErrorCategory.UNKNOWN)


def _parse_difficulty(difficulty_str: str) -> Difficulty:
    """将字符串映射为 Difficulty Enum"""
    mapping = {
        "简单": Difficulty.EASY,
        "中等": Difficulty.MEDIUM,
        "困难": Difficulty.HARD,
    }
    return mapping.get(difficulty_str, Difficulty.MEDIUM)


def _parse_question_type(type_str: str) -> QuestionType:
    """将字符串映射为 QuestionType Enum"""
    mapping = {
        "选择题": QuestionType.CHOICE,
        "填空题": QuestionType.FILL,
        "解答题": QuestionType.SOLUTION,
    }
    return mapping.get(type_str, QuestionType.CHOICE)


def _parse_step_status(status_str: str) -> StepStatus:
    """将字符串映射为 StepStatus Enum"""
    mapping = {
        "correct": StepStatus.CORRECT,
        "error": StepStatus.WRONG,
        "wrong": StepStatus.WRONG,
        "partial": StepStatus.PARTIAL,
        "warning": StepStatus.WARNING,
        "": StepStatus.NEUTRAL,
    }
    return mapping.get(status_str, StepStatus.NEUTRAL)


def _parse_diff_status(status_str: str) -> DiffStatus:
    """将字符串映射为 DiffStatus Enum"""
    mapping = {
        "correct": DiffStatus.CORRECT,
        "error": DiffStatus.ERROR,
        "partial": DiffStatus.PARTIAL,
    }
    return mapping.get(status_str, DiffStatus.PARTIAL)


# ──────────────────────────────────────────────────────────
# ReasoningStep Mapper
# ──────────────────────────────────────────────────────────

class ReasoningStepMapper:
    """推理步骤 Domain → ViewModel"""
    
    @staticmethod
    def to_step_card(step: ReasoningStep, step_number: int) -> StepCardViewModel:
        status = StepStatus.WARNING if step.is_critical else StepStatus.NEUTRAL
        
        title = step.operation
        if step.is_critical:
            title += " ⚠️ 关键步骤"
        
        return StepCardViewModel(
            step_number=step_number,
            title=step.operation,
            expression=step.output or "",
            reasoning=step.reasoning or "",
            status=status,
            status_icon=STEP_STATUS_ICON[status],
            status_color=STATUS_BORDER_COLOR[status],
            knowledge_tags=[step.strategy] if step.strategy else [],
            theorem_tag=step.goal or "",
            is_critical=step.is_critical,
            display_title=title,
        )
    
    @staticmethod
    def to_chain(chain: ReasoningChain) -> ChainViewModel:
        steps = [
            ReasoningStepMapper.to_step_card(step, i + 1)
            for i, step in enumerate(chain.steps)
        ]
        
        connectors = []
        for i in range(len(steps) - 1):
            next_status = steps[i + 1].status
            if next_status in (StepStatus.WRONG, StepStatus.WARNING):
                connectors.append("❌")
            else:
                connectors.append("↓")
        
        final_answer = None
        if chain.final_answer:
            final_answer = FormulaViewModel(
                latex=chain.final_answer,
                label="最终答案",
                status=FormulaStatus.CORRECT,
                status_icon=FORMULA_STATUS_ICON[FormulaStatus.CORRECT],
                display_label="最终答案",
            )
        
        return ChainViewModel(
            chain_id=chain.chain_id,
            steps=steps,
            final_answer=final_answer,
            connectors=connectors,
        )


# ──────────────────────────────────────────────────────────
# ErrorRecord Mapper
# ──────────────────────────────────────────────────────────

class ErrorRecordMapper:
    """错题记录 Domain → ViewModel"""
    
    @staticmethod
    def to_error_view(record: ErrorRecord) -> ErrorViewModel:
        error_cat = _parse_error_category(record.error_type)
        has_diff = bool(record.student_answer and record.correct_answer)
        
        return ErrorViewModel(
            error_type=error_cat,
            error_type_display=error_cat.value,
            error_type_icon=ERROR_CATEGORY_ICON[error_cat],
            knowledge_point=record.knowledge_point,
            student_expr=record.student_answer or "",
            correct_expr=record.correct_answer or "",
            has_diff=has_diff,
        )


# ──────────────────────────────────────────────────────────
# Diagnosis Mapper
# ──────────────────────────────────────────────────────────

class DiagnosisMapper:
    """诊断结果 Domain → ViewModel"""
    
    @staticmethod
    def to_diagnosis_view(diagnosis: DiagnosisResult) -> DiagnosisViewModel:
        error_cat = _parse_error_category(diagnosis.error_type)
        
        return DiagnosisViewModel(
            error_type=error_cat,
            error_type_display=error_cat.value,
            root_cause=diagnosis.root_cause or "",
            knowledge_tags=diagnosis.knowledge_points or [],
            recommendations=diagnosis.recommendations or [],
            common_mistakes=diagnosis.common_mistakes or [],
            confidence=0.0,
            confidence_pct="0%",
            is_repeat=diagnosis.is_repeat,
            repeat_count=diagnosis.repeat_count,
        )


# ──────────────────────────────────────────────────────────
# Grading Mapper
# ──────────────────────────────────────────────────────────

class GradingMapper:
    """批改结果 Domain → ViewModel"""
    
    @staticmethod
    def to_score_view(grading: GradingResult) -> ScoreViewModel:
        accuracy = (grading.score / grading.max_score * 100) if grading.max_score > 0 else 0
        
        deductions = []
        process_score = 0
        
        if grading.step_analysis:
            for step in grading.step_analysis:
                if step.get("status") == "error":
                    deductions.append({
                        "reason": step.get("analysis", "步骤错误"),
                        "points": str(step.get("deduction", 1)),
                    })
                else:
                    process_score += step.get("score", 0)
        
        deduction_total = grading.max_score - grading.score
        
        return ScoreViewModel(
            total_score=grading.score,
            max_score=grading.max_score,
            total_display=f"{grading.score}/{grading.max_score}",
            process_score=process_score,
            max_process=grading.max_score,
            process_display=f"{process_score}/{grading.max_score}",
            deduction_total=deduction_total,
            deduction_display=f"-{deduction_total}",
            is_correct=grading.is_correct,
            accuracy_pct=f"{accuracy:.1f}%",
            deductions=deductions,
        )
    
    @staticmethod
    def to_formula_view(grading: GradingResult) -> FormulaViewModel:
        status = FormulaStatus.NEUTRAL if grading.is_correct else FormulaStatus.WRONG
        
        return FormulaViewModel(
            latex=grading.student_answer,
            label="学生答案",
            status=status,
            status_icon=FORMULA_STATUS_ICON[status],
            display_label="学生答案",
        )
    
    @staticmethod
    def to_diff_views(grading: GradingResult) -> List[DiffViewModel]:
        diffs = []
        
        if grading.step_analysis:
            for step in grading.step_analysis:
                diff_status = _parse_diff_status(step.get("status", ""))
                diffs.append(DiffViewModel(
                    student_expr=step.get("student_expr", ""),
                    correct_expr=step.get("correct_expr", ""),
                    student_label=f"步骤 {step.get('step', '?')} - 学生",
                    correct_label=f"步骤 {step.get('step', '?')} - 正确",
                    status=diff_status,
                ))
        
        return diffs


# ──────────────────────────────────────────────────────────
# Question Mapper
# ──────────────────────────────────────────────────────────

class QuestionMapper:
    """题目 Domain → ViewModel"""
    
    @staticmethod
    def to_question_view(question: Question) -> QuestionViewModel:
        display_title = f"{question.year}-{question.category}"
        if question.volume:
            display_title += f"-{question.volume}"
        display_title += f"-{question.question_no:03d}"
        
        q_type = _parse_question_type(question.question_type)
        diff = _parse_difficulty(question.difficulty)
        diff_tag = DIFFICULTY_TAG[diff]
        
        correct_display = ""
        if question.correct_option:
            correct_display = f"✅ {question.correct_option}"
        
        has_ocr = bool(question.ocr_raw or question.ocr_fixed)
        
        return QuestionViewModel(
            question_id=question.question_id,
            display_title=display_title,
            question_type=q_type,
            question_type_icon=QUESTION_TYPE_ICON[q_type],
            difficulty=diff,
            difficulty_tag_type=diff_tag,
            score=question.score,
            score_display=f"{question.score}分",
            knowledge_tags=question.knowledge_points,
            question_text=question.question,
            options=question.options,
            correct_option=question.correct_option or "",
            correct_option_display=correct_display,
            answer=question.answer or "",
            analysis=question.analysis or "",
            has_ocr_fix=has_ocr,
            ocr_raw=question.ocr_raw or "",
            ocr_fixed=question.ocr_fixed or "",
        )


# ──────────────────────────────────────────────────────────
# Dashboard Mapper
# ──────────────────────────────────────────────────────────

class DashboardMapper:
    """仪表盘 Domain → ViewModel"""
    
    @staticmethod
    def to_dashboard_view(dashboard: DashboardData, username: str = "") -> DashboardViewModel:
        accuracy = f"{dashboard.overall_accuracy * 100:.1f}%"
        
        streak_display = f"{dashboard.streak_days} 天" if dashboard.streak_days > 0 else "今天开始"
        
        level_map = {
            "基础阶段": "🌱 基础阶段",
            "强化阶段": "💪 强化阶段",
            "冲刺阶段": "🚀 冲刺阶段",
        }
        level_display = level_map.get(dashboard.current_level, dashboard.current_level)
        
        return DashboardViewModel(
            username=username,
            welcome_message=f"欢迎回来，{username}",
            total_questions=dashboard.total_questions,
            total_errors=dashboard.total_errors,
            accuracy=accuracy,
            streak_days=dashboard.streak_days,
            streak_display=streak_display,
            weak_points=dashboard.weak_points,
            level=dashboard.current_level,
            level_display=level_display,
        )
