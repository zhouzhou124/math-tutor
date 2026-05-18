"""Semantic Diff Engine — 语义差异引擎

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  数学 Diff ≠ 文本 Diff

  x^2-1 和 (x-1)(x+1) 文本不同，但数学等价。
  sin(x+y) 和 sin(x)+sin(y) 文本相似，但数学不等价。

  正确的 Diff 流程：
    LaTeX
      ↓
    AST (SymPy Expr)
      ↓
    Canonical Form
      ↓
    Semantic Diff
      ↓
    DiffResult (ViewModel 可消费)
      ↓
    Renderer → HTML

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from canonicalization.expression import (
    canonicalize_expression,
    canonicalize_expression_multi,
    expressions_are_equivalent,
    parse_to_sympy,
    CanonicalForm,
)
from canonicalization.fingerprint import expression_fingerprint


class DiffType(str, Enum):
    EQUIVALENT = "equivalent"
    DIFFERENT = "different"
    PARTIAL = "partial"
    INCOMPARABLE = "incomparable"


class DiffLevel(str, Enum):
    TEXT_IDENTICAL = "text_identical"
    CANONICAL_IDENTICAL = "canonical_identical"
    SEMANTIC_EQUIVALENT = "semantic_equivalent"
    FORM_DIFFERENT = "form_different"
    SEMANTIC_DIFFERENT = "semantic_different"


@dataclass
class ExpressionDiff:
    """单个表达式的语义差异结果"""
    student_expr: str
    correct_expr: str
    diff_type: DiffType = DiffType.INCOMPARABLE
    diff_level: DiffLevel = DiffLevel.SEMANTIC_DIFFERENT
    
    student_canonical: str = ""
    correct_canonical: str = ""
    
    is_equivalent: bool = False
    is_text_identical: bool = False
    
    student_forms: dict = field(default_factory=dict)
    correct_forms: dict = field(default_factory=dict)
    
    explanation: str = ""


@dataclass
class StepDiff:
    """步骤级别的语义差异"""
    step_number: int
    expression_diff: Optional[ExpressionDiff] = None
    reasoning_match: bool = False
    theorem_match: bool = False
    
    is_correct: bool = False
    is_equivalent: bool = False
    error_type: str = ""


@dataclass
class SemanticDiffResult:
    """完整的语义差异结果"""
    diffs: List[StepDiff] = field(default_factory=list)
    overall_equivalent: bool = False
    total_steps: int = 0
    correct_steps: int = 0
    equivalent_steps: int = 0
    error_steps: int = 0
    
    summary: str = ""


def diff_expressions(
    student_expr: str,
    correct_expr: str,
) -> ExpressionDiff:
    """
    比较两个表达式的语义差异。
    
    Pipeline:
      1. 文本比较（快速路径）
      2. 规范化比较
      3. 语义等价判断
      4. 多形式比较
    
    Returns:
        ExpressionDiff 包含详细的差异信息
    """
    if not student_expr or not correct_expr:
        return ExpressionDiff(
            student_expr=student_expr,
            correct_expr=correct_expr,
            diff_type=DiffType.INCOMPARABLE,
            diff_level=DiffLevel.SEMANTIC_DIFFERENT,
            explanation="表达式为空",
        )
    
    s_stripped = student_expr.strip().replace(" ", "")
    c_stripped = correct_expr.strip().replace(" ", "")
    
    if s_stripped == c_stripped:
        return ExpressionDiff(
            student_expr=student_expr,
            correct_expr=correct_expr,
            diff_type=DiffType.EQUIVALENT,
            diff_level=DiffLevel.TEXT_IDENTICAL,
            is_equivalent=True,
            is_text_identical=True,
            student_canonical=canonicalize_expression(student_expr),
            correct_canonical=canonicalize_expression(correct_expr),
            explanation="文本完全相同",
        )
    
    s_canonical = canonicalize_expression(student_expr, CanonicalForm.EXPANDED)
    c_canonical = canonicalize_expression(correct_expr, CanonicalForm.EXPANDED)
    
    if s_canonical == c_canonical:
        return ExpressionDiff(
            student_expr=student_expr,
            correct_expr=correct_expr,
            diff_type=DiffType.EQUIVALENT,
            diff_level=DiffLevel.CANONICAL_IDENTICAL,
            is_equivalent=True,
            student_canonical=s_canonical,
            correct_canonical=c_canonical,
            explanation="规范化后相同（数学等价，形式不同）",
        )
    
    if expressions_are_equivalent(student_expr, correct_expr):
        s_forms = canonicalize_expression_multi(student_expr)
        c_forms = canonicalize_expression_multi(correct_expr)
        
        return ExpressionDiff(
            student_expr=student_expr,
            correct_expr=correct_expr,
            diff_type=DiffType.EQUIVALENT,
            diff_level=DiffLevel.SEMANTIC_EQUIVALENT,
            is_equivalent=True,
            student_canonical=s_canonical,
            correct_canonical=c_canonical,
            student_forms={k.value: v for k, v in s_forms.items()},
            correct_forms={k.value: v for k, v in c_forms.items()},
            explanation="语义等价（通过数值验证）",
        )
    
    s_forms = canonicalize_expression_multi(student_expr)
    c_forms = canonicalize_expression_multi(correct_expr)
    
    s_factored = s_forms.get(CanonicalForm.FACTORED, s_canonical)
    c_factored = c_forms.get(CanonicalForm.FACTORED, c_canonical)
    
    if s_factored == c_factored:
        return ExpressionDiff(
            student_expr=student_expr,
            correct_expr=correct_expr,
            diff_type=DiffType.PARTIAL,
            diff_level=DiffLevel.FORM_DIFFERENT,
            is_equivalent=False,
            student_canonical=s_canonical,
            correct_canonical=c_canonical,
            student_forms={k.value: v for k, v in s_forms.items()},
            correct_forms={k.value: v for k, v in c_forms.items()},
            explanation="因式形式相同但展开形式不同（部分等价）",
        )
    
    return ExpressionDiff(
        student_expr=student_expr,
        correct_expr=correct_expr,
        diff_type=DiffType.DIFFERENT,
        diff_level=DiffLevel.SEMANTIC_DIFFERENT,
        is_equivalent=False,
        student_canonical=s_canonical,
        correct_canonical=c_canonical,
        student_forms={k.value: v for k, v in s_forms.items()},
        correct_forms={k.value: v for k, v in c_forms.items()},
        explanation="语义不同",
    )


def diff_reasoning_steps(
    student_steps: list,
    correct_steps: list,
) -> SemanticDiffResult:
    """
    比较推理步骤的语义差异。
    
    Args:
        student_steps: 学生推理步骤列表，每个包含 output 字段
        correct_steps: 正确推理步骤列表，每个包含 output 字段
    
    Returns:
        SemanticDiffResult 包含步骤级别的差异信息
    """
    diffs = []
    total = max(len(student_steps), len(correct_steps))
    correct_count = 0
    equivalent_count = 0
    error_count = 0
    
    for i in range(total):
        s_step = student_steps[i] if i < len(student_steps) else None
        c_step = correct_steps[i] if i < len(correct_steps) else None
        
        if s_step is None:
            diffs.append(StepDiff(
                step_number=i + 1,
                is_correct=False,
                error_type="missing_step",
            ))
            error_count += 1
            continue
        
        if c_step is None:
            diffs.append(StepDiff(
                step_number=i + 1,
                is_correct=False,
                error_type="extra_step",
            ))
            error_count += 1
            continue
        
        s_output = getattr(s_step, 'output', '') or ''
        c_output = getattr(c_step, 'output', '') or ''
        
        expr_diff = diff_expressions(s_output, c_output)
        
        is_correct = expr_diff.is_equivalent
        
        step_diff = StepDiff(
            step_number=i + 1,
            expression_diff=expr_diff,
            is_correct=is_correct,
            is_equivalent=expr_diff.is_equivalent,
        )
        
        if is_correct:
            correct_count += 1
            if expr_diff.is_text_identical:
                equivalent_count += 1
        else:
            error_count += 1
            step_diff.error_type = "expression_error"
        
        diffs.append(step_diff)
    
    overall = error_count == 0 and total > 0
    
    summary = f"共 {total} 步，正确 {correct_count} 步，等价 {equivalent_count} 步，错误 {error_count} 步"
    
    return SemanticDiffResult(
        diffs=diffs,
        overall_equivalent=overall,
        total_steps=total,
        correct_steps=correct_count,
        equivalent_steps=equivalent_count,
        error_steps=error_count,
        summary=summary,
    )


def diff_to_viewmodel_data(expr_diff: ExpressionDiff) -> dict:
    """
    将 ExpressionDiff 转换为 DiffViewModel 可消费的数据。
    
    这是 Canonicalization → Presentation 的桥梁。
    """
    from rendering.tokens import DiffStatus
    
    status_map = {
        DiffType.EQUIVALENT: DiffStatus.CORRECT,
        DiffType.DIFFERENT: DiffStatus.ERROR,
        DiffType.PARTIAL: DiffStatus.PARTIAL,
        DiffType.INCOMPARABLE: DiffStatus.PARTIAL,
    }
    
    return {
        "student_expr": expr_diff.student_expr,
        "correct_expr": expr_diff.correct_expr,
        "status": status_map.get(expr_diff.diff_type, DiffStatus.PARTIAL),
        "is_equivalent": expr_diff.is_equivalent,
        "explanation": expr_diff.explanation,
        "diff_level": expr_diff.diff_level.value,
    }
