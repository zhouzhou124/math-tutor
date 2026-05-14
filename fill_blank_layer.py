"""fill_blank_layer.py — 填空题处理层

完整的填空题系统：

1. 表达式标准化
   - 1/2, 0.5, \frac12 统一

2. 符号等价验证
   - sympy.simplify(a-b)==0

3. 数值稳定验证
   - 避免浮点误差

4. 多答案支持
   - ±1

5. 定义域检查
   - x=1 虽然代数成立但不满足题意
"""

from __future__ import annotations

import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Union
from enum import Enum
from dataclasses_json import dataclass_json

try:
    import sympy
    from sympy import sympify, simplify, expand, factor, N
    from sympy.parsing.latex import parse_latex
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False


# ═══════════════════════════════════════════════
# 填空题类型定义
# ═══════════════════════════════════════════════

class FillBlankType(Enum):
    """填空题类型"""
    NUMERICAL = "numerical"      # 数值填空
    EXPRESSION = "expression"    # 表达式填空
    EQUATION = "equation"        # 方程填空
    INTERVAL = "interval"       # 区间填空
    DOMAIN = "domain"           # 定义域填空


# ═══════════════════════════════════════════════
# 数据模型定义
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class DomainConstraint:
    """定义域约束"""
    variable: str
    constraint_type: str
    constraint_expr: str
    description: str


@dataclass_json
@dataclass
class FillBlankAnswer:
    """填空题答案"""
    answer_id: str
    answer_type: str
    standard_form: str
    alternatives: List[str] = field(default_factory=list)
    tolerance: float = 0.0


@dataclass_json
@dataclass
class FillBlankQuestion:
    """填空题"""
    question_id: str
    question_text: str
    blank_position: int
    question_type: FillBlankType
    expected_answer: str
    accepted_answers: List[FillBlankAnswer] = field(default_factory=list)
    domain_constraints: List[DomainConstraint] = field(default_factory=list)
    explanation: str = ""
    common_wrong_answers: List[str] = field(default_factory=list)


@dataclass_json
@dataclass
class FillBlankScoringResult:
    """填空题评分结果"""
    is_correct: bool
    student_answer: str
    normalized_answer: str
    correct_answer: str
    score: float
    max_score: float
    equivalence_verified: bool
    domain_check_passed: bool
    domain_violation: str = ""
    equivalence_score: float = 0.0
    domain_score: float = 0.0
    tolerance_applied: float = 0.0
    detailed_feedback: str = ""


# ═══════════════════════════════════════════════
# 表达式标准化器
# ═══════════════════════════════════════════════

class ExpressionNormalizer:
    """
    表达式标准化器

    将各种输入格式规范化为标准形式：
    - 1/2 → 1/2 (分数)
    - 0.5 → 1/2 (分数)
    - \frac12 → 1/2 (LaTeX)
    """

    @staticmethod
    def normalize_expression(raw_input: str) -> str:
        """
        规范化表达式

        Returns:
            标准化后的表达式字符串
        """
        if not raw_input:
            return ""

        normalized = raw_input.strip()

        normalized = ExpressionNormalizer._normalize_whitespace(normalized)
        normalized = ExpressionNormalizer._normalize_latex(normalized)
        normalized = ExpressionNormalizer._normalize_fractions(normalized)
        normalized = ExpressionNormalizer._normalize_decimals(normalized)
        normalized = ExpressionNormalizer._normalize_exponents(normalized)

        return normalized

    @staticmethod
    def _normalize_whitespace(expr: str) -> str:
        """规范化空白字符"""
        expr = expr.strip()
        expr = re.sub(r'\s+', '', expr)
        return expr

    @staticmethod
    def _normalize_latex(expr: str) -> str:
        """规范化LaTeX表达式"""
        latex_to_unicode = {
            r'\frac': '/',
            r'\sqrt': 'sqrt',
            r'\pi': 'pi',
            r'\theta': 'theta',
            r'\alpha': 'alpha',
            r'\beta': 'beta',
        }

        result = expr
        for latex, unicode_rep in latex_to_unicode.items():
            result = result.replace(latex, unicode_rep)

        result = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', result)
        result = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', result)
        result = re.sub(r'\^{([^}]+)}', r'**(\1)', result)

        return result

    @staticmethod
    def _normalize_fractions(expr: str) -> str:
        """规范化分数表示"""
        if '/' in expr and '(' not in expr:
            parts = expr.split('/')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                numerator = int(parts[0])
                denominator = int(parts[1])
                if denominator != 0:
                    gcd = math.gcd(numerator, denominator)
                    numerator //= gcd
                    denominator //= gcd
                    if denominator == 1:
                        return str(numerator)
                    if numerator == 0:
                        return "0"
                    return f"{numerator}/{denominator}"

        fraction_pattern = r'\(([^)]+)\)/\(([^)]+)\)'
        matches = re.findall(fraction_pattern, expr)
        for num, den in matches:
            if num.isdigit() and den.isdigit():
                numerator = int(num)
                denominator = int(den)
                if denominator != 0:
                    gcd = math.gcd(numerator, denominator)
                    numerator //= gcd
                    denominator //= gcd
                    if denominator == 1:
                        expr = expr.replace(f"({num})/({den})", str(numerator))
                    else:
                        expr = expr.replace(f"({num})/({den})", f"{numerator}/{denominator}")

        return expr

    @staticmethod
    def _normalize_decimals(expr: str) -> str:
        """规范化小数（转换为分数）"""
        decimal_pattern = r'(\d+)\.(\d+)'
        matches = re.findall(decimal_pattern, expr)

        for int_part, frac_part in matches:
            if len(frac_part) <= 10:
                decimal_value = float(f"{int_part}.{frac_part}")
                numerator = int(decimal_value * (10 ** len(frac_part)))
                denominator = 10 ** len(frac_part)
                gcd = math.gcd(numerator, denominator)
                numerator //= gcd
                denominator //= gcd

                if denominator == 1:
                    replacement = str(numerator)
                else:
                    replacement = f"{numerator}/{denominator}"

                full_match = f"{int_part}.{frac_part}"
                expr = expr.replace(full_match, f"({replacement})", 1)

        return expr

    @staticmethod
    def _normalize_exponents(expr: str) -> str:
        """规范化指数表示"""
        expr = expr.replace('^', '**')
        expr = re.sub(r'(\d+)\*\*(\d+)', r'\1**\2', expr)
        return expr


# ═══════════════════════════════════════════════
# 符号等价验证器
# ═══════════════════════════════════════════════

class SymbolicEquivalenceVerifier:
    """
    符号等价验证器

    使用 sympy 验证两个表达式是否等价：
    - sympy.simplify(a-b) == 0
    """

    @staticmethod
    def are_equivalent(
        student_expr: str,
        standard_expr: str,
        variable: str = 'x'
    ) -> Tuple[bool, float]:
        """
        验证两个表达式是否等价

        Args:
            student_expr: 学生答案
            standard_expr: 标准答案
            variable: 变量名

        Returns:
            (is_equivalent, confidence_score)
        """
        if not HAS_SYMPY:
            return SymbolicEquivalenceVerifier._fallback_equivalence(
                student_expr, standard_expr
            )

        try:
            s_student = sympify(student_expr)
            s_standard = sympify(standard_expr)

            diff = simplify(s_student - s_standard)
            diff_expanded = expand(diff)

            if diff_expanded == 0:
                return True, 1.0

            if diff_expanded.free_symbols:
                symbols = diff_expanded.free_symbols
                if len(symbols) == 1 and variable in str(symbols):
                    test_values = [-2, -1, 0, 1, 2, 0.5]
                    matches = 0
                    for val in test_values:
                        try:
                            student_val = float(N(s_student.subs(variable, val)))
                            standard_val = float(N(s_standard.subs(variable, val)))
                            if abs(student_val - standard_val) < 1e-9:
                                matches += 1
                        except:
                            pass
                    confidence = matches / len(test_values)
                    return matches == len(test_values), confidence

            return False, 0.0

        except Exception as e:
            return SymbolicEquivalenceVerifier._fallback_equivalence(
                student_expr, standard_expr
            )

    @staticmethod
    def _fallback_equivalence(
        student_expr: str,
        standard_expr: str
    ) -> Tuple[bool, float]:
        """当 sympy 不可用时的备用验证"""
        norm_student = ExpressionNormalizer.normalize_expression(student_expr)
        norm_standard = ExpressionNormalizer.normalize_expression(standard_expr)

        if norm_student == norm_standard:
            return True, 1.0

        try:
            val_student = float(eval(norm_student))
            val_standard = float(eval(norm_standard))
            if abs(val_student - val_standard) < 1e-9:
                return True, 1.0
        except:
            pass

        return False, 0.0


# ═══════════════════════════════════════════════
# 数值稳定性验证器
# ═══════════════════════════════════════════════

class NumericalStabilityVerifier:
    """
    数值稳定性验证器

    避免浮点误差：
    - 使用分数精确比较
    - 支持容差范围
    """

    DEFAULT_TOLERANCE = 1e-9

    @staticmethod
    def verify_numerical(
        student_answer: str,
        standard_answer: str,
        tolerance: float = None
    ) -> Tuple[bool, float]:
        """
        验证数值答案

        Args:
            student_answer: 学生答案
            standard_answer: 标准答案
            tolerance: 容差（相对误差）

        Returns:
            (is_correct, actual_difference)
        """
        if tolerance is None:
            tolerance = NumericalStabilityVerifier.DEFAULT_TOLERANCE

        norm_student = ExpressionNormalizer.normalize_expression(student_answer)
        norm_standard = ExpressionNormalizer.normalize_expression(standard_answer)

        if norm_student == norm_standard:
            return True, 0.0

        try:
            val_student = NumericalStabilityVerifier._parse_to_number(norm_student)
            val_standard = NumericalStabilityVerifier._parse_to_number(norm_standard)

            if val_student is None or val_standard is None:
                return False, float('inf')

            abs_diff = abs(val_student - val_standard)
            rel_diff = abs_diff / (abs(val_standard) + 1e-15)

            is_correct = abs_diff <= tolerance or rel_diff <= tolerance

            return is_correct, abs_diff

        except Exception:
            return False, float('inf')

    @staticmethod
    def _parse_to_number(expr: str) -> Optional[float]:
        """将表达式解析为数值"""
        expr = expr.strip()

        if '/' in expr:
            parts = expr.split('/')
            if len(parts) == 2:
                try:
                    num = float(parts[0])
                    den = float(parts[1])
                    if den != 0:
                        return num / den
                except:
                    pass

        try:
            return float(eval(expr))
        except:
            return None

    @staticmethod
    def verify_with_tolerance(
        student_answer: str,
        standard_answer: str,
        relative_tolerance: float = 1e-6,
        absolute_tolerance: float = 1e-9
    ) -> Tuple[bool, float]:
        """带容差的验证"""
        is_correct, diff = NumericalStabilityVerifier.verify_numerical(
            student_answer, standard_answer
        )

        if is_correct:
            return True, diff

        norm_standard = ExpressionNormalizer.normalize_expression(standard_answer)
        try:
            val_standard = float(eval(norm_standard))
            rel_diff = diff / (abs(val_standard) + 1e-15)
            return rel_diff <= relative_tolerance, diff
        except:
            return False, diff


# ═══════════════════════════════════════════════
# 多答案支持
# ═══════════════════════════════════════════════

class MultiAnswerVerifier:
    """
    多答案验证器

    支持：
    - ±1 → [1, -1]
    - {1, 2} → [1, 2]
    - [1,2] → [1, 2]
    """

    @staticmethod
    def parse_multi_answer(answer: str) -> List[str]:
        """解析多答案"""
        answer = answer.strip()

        answer = answer.replace('±', '+-')

        if '+-' in answer:
            base = answer.replace('+-', '').strip()
            return [f"+{base}", f"-{base}"]

        if '{' in answer and '}' in answer:
            content = re.search(r'\{([^}]+)\}', answer)
            if content:
                items = content.group(1).split(',')
                return [item.strip() for item in items]

        if '[' in answer and ']' in answer:
            content = re.search(r'\[([^\]]+)\]', answer)
            if content:
                items = content.group(1).split(',')
                return [item.strip() for item in items]

        if '~' in answer:
            parts = answer.split('~')
            if len(parts) == 2:
                try:
                    start = float(parts[0].strip())
                    end = float(parts[1].strip())
                    return [str(start), str(end)]
                except:
                    pass

        return [answer]

    @staticmethod
    def verify_multi_answer(
        student_answer: str,
        accepted_answers: List[str]
    ) -> Tuple[bool, str, float]:
        """
        验证多答案

        Returns:
            (is_correct, matched_answer, best_score)
        """
        if not accepted_answers:
            return False, "", 0.0

        best_match = None
        best_score = 0.0

        for answer in accepted_answers:
            candidates = MultiAnswerVerifier.parse_multi_answer(answer)

            for candidate in candidates:
                norm_student = ExpressionNormalizer.normalize_expression(student_answer)
                norm_candidate = ExpressionNormalizer.normalize_expression(candidate)

                is_correct, diff = NumericalStabilityVerifier.verify_numerical(
                    norm_student, norm_candidate
                )

                if is_correct:
                    return True, answer, 1.0

                is_equiv, conf = SymbolicEquivalenceVerifier.are_equivalent(
                    norm_student, norm_candidate
                )

                if is_equiv and conf > best_score:
                    best_score = conf
                    best_match = answer

        if best_match:
            return True, best_match, best_score

        if len(candidates) == 1:
            norm_single = ExpressionNormalizer.normalize_expression(candidates[0])
            norm_student = ExpressionNormalizer.normalize_expression(student_answer)
            is_correct, _ = NumericalStabilityVerifier.verify_numerical(
                norm_student, norm_single
            )
            if is_correct:
                return True, answer, 1.0

        return False, "", 0.0


# ═══════════════════════════════════════════════
# 定义域检查器
# ═══════════════════════════════════════════════

class DomainChecker:
    """
    定义域检查器

    例如：
    - x=1 虽然代数成立，但不满足题意（定义域限制）
    """

    @staticmethod
    def check_domain(
        student_answer: str,
        constraints: List[DomainConstraint]
    ) -> Tuple[bool, str]:
        """
        检查答案是否满足定义域约束

        Args:
            student_answer: 学生答案
            constraints: 定义域约束列表

        Returns:
            (is_valid, violation_message)
        """
        if not constraints:
            return True, ""

        for constraint in constraints:
            is_valid = DomainChecker._check_single_constraint(
                student_answer, constraint
            )

            if not is_valid:
                return False, f"{constraint.description}: {constraint.constraint_expr}"

        return True, ""

    @staticmethod
    def _check_single_constraint(
        answer: str,
        constraint: DomainConstraint
    ) -> bool:
        """检查单个约束"""
        constraint_type = constraint.constraint_type

        if constraint_type == "not_equal":
            return DomainChecker._check_not_equal(answer, constraint.constraint_expr)

        elif constraint_type == "greater_than":
            return DomainChecker._check_greater_than(answer, constraint.constraint_expr)

        elif constraint_type == "less_than":
            return DomainChecker._check_less_than(answer, constraint.constraint_expr)

        elif constraint_type == "in_domain":
            return DomainChecker._check_in_domain(answer, constraint.constraint_expr)

        elif constraint_type == "positive":
            return DomainChecker._check_positive(answer)

        elif constraint_type == "non_zero":
            return DomainChecker._check_nonzero(answer)

        return True

    @staticmethod
    def _check_not_equal(answer: str, not_value: str) -> bool:
        """检查答案不等于某值"""
        try:
            val_answer = float(eval(ExpressionNormalizer.normalize_expression(answer)))
            val_not = float(eval(ExpressionNormalizer.normalize_expression(not_value)))
            return abs(val_answer - val_not) > 1e-9
        except:
            return True

    @staticmethod
    def _check_greater_than(answer: str, threshold: str) -> bool:
        """检查答案大于某值"""
        try:
            val_answer = float(eval(ExpressionNormalizer.normalize_expression(answer)))
            val_threshold = float(eval(ExpressionNormalizer.normalize_expression(threshold)))
            return val_answer > val_threshold
        except:
            return True

    @staticmethod
    def _check_less_than(answer: str, threshold: str) -> bool:
        """检查答案小于某值"""
        try:
            val_answer = float(eval(ExpressionNormalizer.normalize_expression(answer)))
            val_threshold = float(eval(ExpressionNormalizer.normalize_expression(threshold)))
            return val_answer < val_threshold
        except:
            return True

    @staticmethod
    def _check_in_domain(answer: str, domain: str) -> bool:
        """检查答案在指定集合中"""
        domain_values = domain.split(',')
        try:
            val_answer = float(eval(ExpressionNormalizer.normalize_expression(answer)))
            for val in domain_values:
                val = val.strip()
                val = ExpressionNormalizer.normalize_expression(val)
                domain_val = float(eval(val))
                if abs(val_answer - domain_val) < 1e-9:
                    return True
            return False
        except:
            return True

    @staticmethod
    def _check_positive(answer: str) -> bool:
        """检查答案是否正数"""
        try:
            val_answer = float(eval(ExpressionNormalizer.normalize_expression(answer)))
            return val_answer > 0
        except:
            return True

    @staticmethod
    def _check_nonzero(answer: str) -> bool:
        """检查答案是否非零"""
        try:
            val_answer = float(eval(ExpressionNormalizer.normalize_expression(answer)))
            return abs(val_answer) > 1e-9
        except:
            return True


# ═══════════════════════════════════════════════
# 统一填空题评分器
# ═══════════════════════════════════════════════

class UnifiedFillBlankScorer:
    """
    统一填空题评分器

    完整的填空题系统：
    1. 表达式标准化
    2. 符号等价验证
    3. 数值稳定性验证
    4. 多答案支持
    5. 定义域检查
    """

    def __init__(self):
        self.normalizer = ExpressionNormalizer()
        self.equiv_verifier = SymbolicEquivalenceVerifier()
        self.numerical_verifier = NumericalStabilityVerifier()
        self.multi_answer_verifier = MultiAnswerVerifier()
        self.domain_checker = DomainChecker()

    def score_fill_blank(
        self,
        question: FillBlankQuestion,
        student_input: str,
        score_if_correct: float = 100.0
    ) -> FillBlankScoringResult:
        """
        评分填空题

        Args:
            question: 填空题题目
            student_input: 学生输入
            score_if_correct: 正确时的得分

        Returns:
            完整评分结果
        """
        if not student_input or not student_input.strip():
            return FillBlankScoringResult(
                is_correct=False,
                student_answer=student_input,
                normalized_answer="",
                correct_answer=question.expected_answer,
                score=0.0,
                max_score=score_if_correct,
                equivalence_verified=False,
                domain_check_passed=True,
                detailed_feedback="答案不能为空"
            )

        raw_answer = student_input.strip()
        normalized = self.normalizer.normalize_expression(raw_answer)

        domain_valid, domain_violation = self.domain_checker.check_domain(
            normalized, question.domain_constraints
        )

        if not domain_valid:
            return FillBlankScoringResult(
                is_correct=False,
                student_answer=raw_answer,
                normalized_answer=normalized,
                correct_answer=question.expected_answer,
                score=0.0,
                max_score=score_if_correct,
                equivalence_verified=True,
                domain_check_passed=False,
                domain_violation=domain_violation,
                detailed_feedback=f"答案不满足定义域条件：{domain_violation}"
            )

        accepted = [a.standard_form for a in question.accepted_answers]
        if not accepted:
            accepted = [question.expected_answer]

        is_correct, matched_answer, equiv_score = self.multi_answer_verifier.verify_multi_answer(
            normalized, accepted
        )

        if is_correct:
            return FillBlankScoringResult(
                is_correct=True,
                student_answer=raw_answer,
                normalized_answer=normalized,
                correct_answer=matched_answer,
                score=score_if_correct,
                max_score=score_if_correct,
                equivalence_verified=True,
                domain_check_passed=True,
                equivalence_score=equiv_score,
                detailed_feedback=f"正确！答案 {normalized} 符合要求。"
            )

        is_equiv, conf = self.equiv_verifier.are_equivalent(
            normalized, question.expected_answer
        )

        if is_equiv:
            partial_score = score_if_correct * conf
            return FillBlankScoringResult(
                is_correct=True,
                student_answer=raw_answer,
                normalized_answer=normalized,
                correct_answer=question.expected_answer,
                score=partial_score,
                max_score=score_if_correct,
                equivalence_verified=True,
                domain_check_passed=True,
                equivalence_score=conf,
                detailed_feedback=f"答案等价！{normalized} 与标准答案 {question.expected_answer} 等价。（得分：{partial_score:.1f}）"
            )

        is_numerical_correct, diff = self.numerical_verifier.verify_with_tolerance(
            normalized, question.expected_answer
        )

        if is_numerical_correct:
            return FillBlankScoringResult(
                is_correct=True,
                student_answer=raw_answer,
                normalized_answer=normalized,
                correct_answer=question.expected_answer,
                score=score_if_correct,
                max_score=score_if_correct,
                equivalence_verified=True,
                domain_check_passed=True,
                tolerance_applied=diff,
                detailed_feedback=f"数值正确！{normalized} ≈ {question.expected_answer}"
            )

        wrong_answer_feedback = ""
        for wrong in question.common_wrong_answers:
            if self.normalizer.normalize_expression(wrong) == normalized:
                wrong_answer_feedback = f"这是一个常见错误答案，请重新思考。"
                break

        return FillBlankScoringResult(
            is_correct=False,
            student_answer=raw_answer,
            normalized_answer=normalized,
            correct_answer=question.expected_answer,
            score=0.0,
            max_score=score_if_correct,
            equivalence_verified=False,
            domain_check_passed=True,
            equivalence_score=0.0,
            detailed_feedback=f"答案不正确。您输入的是 {normalized}，标准答案是 {question.expected_answer}。{wrong_answer_feedback}\n解析：{question.explanation}"
        )


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def normalize_expression(expr: str) -> str:
    """快速规范化表达式"""
    return ExpressionNormalizer.normalize_expression(expr)


def verify_equivalence(student: str, standard: str) -> Tuple[bool, float]:
    """快速验证等价性"""
    return SymbolicEquivalenceVerifier.are_equivalent(student, standard)


def check_domain_constraints(
    answer: str,
    constraints: List[DomainConstraint]
) -> Tuple[bool, str]:
    """快速检查定义域"""
    return DomainChecker.check_domain(answer, constraints)


def score_fill_blank_question(
    question: FillBlankQuestion,
    student_input: str,
    score_if_correct: float = 100.0
) -> FillBlankScoringResult:
    """快速评分填空题"""
    scorer = UnifiedFillBlankScorer()
    return scorer.score_fill_blank(question, student_input, score_if_correct)


def format_fill_blank_feedback(result: FillBlankScoringResult) -> str:
    """格式化填空题反馈"""
    lines = []
    lines.append("=" * 60)
    lines.append("【填空题评分结果】")
    lines.append("=" * 60)
    lines.append(f"原始答案: {result.student_answer}")
    lines.append(f"标准化答案: {result.normalized_answer}")
    lines.append(f"正确答案: {result.correct_answer}")

    if result.is_correct:
        lines.append(f"评分: {result.score:.1f}/{result.max_score:.1f}")
        lines.append("")
        lines.append("【正确！】")
        lines.append(result.detailed_feedback)
    else:
        lines.append(f"评分: {result.score:.1f}/{result.max_score:.1f}")
        lines.append("")

        if not result.domain_check_passed:
            lines.append("【定义域错误】")
            lines.append(result.detailed_feedback)
        else:
            lines.append("【答案错误】")
            lines.append(result.detailed_feedback)

    lines.append("=" * 60)

    return "\n".join(lines)
