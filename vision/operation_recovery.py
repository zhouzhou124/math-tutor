"""vision/operation_recovery.py — Operation Recovery（操作类型恢复）

═══════════════════════════════════════════════════════════════
核心思想 — 视觉步骤 → 操作类型
═══════════════════════════════════════════════════════════════

  你已经有：
    Op                    — 标准化操作类型枚举
    TransformationVerifier — 变换合法性验证
    ConstraintGraph       — 约束图
    RuntimeState          — 运行时状态

  现在需要：
    视觉步骤 → 操作类型恢复

  例如：
    x² - 1 → (x-1)(x+1)     恢复：Op.FACTOR
    (x+1)² → x² + 2x + 1    恢复：Op.EXPAND
    f(x)   → f'(x)           恢复：Op.DIFFERENTIATE
    ∫f(x)dx → F(x)           恢复：Op.INTEGRATE

  这是你的真正优势：
    别人的系统：OCR → LLM
    你的系统：  Vision → Op Recovery → TransformationVerifier
                                    → ConstraintGraph
                                    → RuntimeState

  完全不同层级。

═══════════════════════════════════════════════════════════════
恢复策略（三级）
═══════════════════════════════════════════════════════════════

  Level 1: 结构特征分析（纯视觉，无 OCR）
    - 括号数量变化 → EXPAND / FACTOR
    - 分数线出现/消失 → SIMPLIFY / CANCEL
    - d/dx 符号出现 → DIFFERENTIATE
    - ∫ 符号出现 → INTEGRATE
    - lim 符号出现 → COMPUTE_LIMIT

  Level 2: LaTeX 文本分析（需要 OCR/pix2tex 输出）
    - 关键词匹配 → Op 推断
    - 表达式结构对比 → 变换类型

  Level 3: LLM 推断（最后手段）
    - 将 before/after 发给 LLM → Op 分类

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Optional, Dict

from operations import Op, infer_op_from_text, normalize_op


class RecoveryLevel(Enum):
    STRUCTURAL = "structural"
    TEXTUAL = "textual"
    LLM = "llm"


class StructuralFeature(Enum):
    PARENTHESES_ADDED = auto()
    PARENTHESES_REMOVED = auto()
    FRACTION_APPEARED = auto()
    FRACTION_DISAPPEARED = auto()
    DERIVATIVE_SYMBOL = auto()
    INTEGRAL_SYMBOL = auto()
    LIMIT_SYMBOL = auto()
    SUM_SYMBOL = auto()
    PRODUCT_SYMBOL = auto()
    MATRIX_APPEARED = auto()
    RADICAL_APPEARED = auto()
    EQUALS_SIGN = auto()
    ARROW_SIGN = auto()
    NUMBER_OF_TERMS_INCREASED = auto()
    NUMBER_OF_TERMS_DECREASED = auto()
    NO_CHANGE = auto()


@dataclass
class StructuralDiff:
    """结构差异 — 两个视觉步骤之间的结构变化"""
    before_features: List[StructuralFeature] = field(default_factory=list)
    after_features: List[StructuralFeature] = field(default_factory=list)
    changes: List[StructuralFeature] = field(default_factory=list)
    parentheses_delta: int = 0
    terms_delta: int = 0
    has_fraction_before: bool = False
    has_fraction_after: bool = False
    has_derivative_after: bool = False
    has_integral_after: bool = False
    has_limit_after: bool = False
    has_sum_after: bool = False
    has_matrix_after: bool = False


@dataclass
class RecoveredOperation:
    """恢复的操作 — 视觉步骤间推断出的操作类型"""
    op: Op = Op.COMPUTE
    confidence: float = 0.0
    recovery_level: RecoveryLevel = RecoveryLevel.STRUCTURAL
    structural_diff: Optional[StructuralDiff] = None
    evidence: List[str] = field(default_factory=list)
    alternatives: List[Tuple[Op, float]] = field(default_factory=list)
    before_latex: str = ""
    after_latex: str = ""
    before_step_id: str = ""
    after_step_id: str = ""

    def to_dict(self) -> dict:
        return {
            "op": self.op.value,
            "confidence": self.confidence,
            "recovery_level": self.recovery_level.value,
            "evidence": self.evidence,
            "alternatives": [(op.value, conf) for op, conf in self.alternatives],
            "before_latex": self.before_latex,
            "after_latex": self.after_latex,
            "before_step_id": self.before_step_id,
            "after_step_id": self.after_step_id,
        }


@dataclass
class OperationRecoveryResult:
    """操作恢复结果"""
    operations: List[RecoveredOperation] = field(default_factory=list)
    total_pairs: int = 0
    avg_confidence: float = 0.0
    level_counts: Dict[str, int] = field(default_factory=dict)


class StructuralAnalyzer:
    """结构特征分析器 — 纯视觉层面分析公式结构变化

    不依赖 OCR 文本，仅分析视觉结构特征：
      - 括号数量
      - 分数线
      - 运算符符号（d/dx, ∫, lim, Σ）
      - 项数变化
    """

    def analyze(self, before_latex: str, after_latex: str) -> StructuralDiff:
        diff = StructuralDiff()

        before_features = self._extract_features(before_latex)
        after_features = self._extract_features(after_latex)

        diff.before_features = before_features
        diff.after_features = after_features

        # 括号变化
        before_parens = self._count_parentheses(before_latex)
        after_parens = self._count_parentheses(after_latex)
        diff.parentheses_delta = after_parens - before_parens

        if diff.parentheses_delta > 0:
            diff.changes.append(StructuralFeature.PARENTHESES_ADDED)
        elif diff.parentheses_delta < 0:
            diff.changes.append(StructuralFeature.PARENTHESES_REMOVED)

        # 分数线变化
        diff.has_fraction_before = self._has_fraction(before_latex)
        diff.has_fraction_after = self._has_fraction(after_latex)

        if not diff.has_fraction_before and diff.has_fraction_after:
            diff.changes.append(StructuralFeature.FRACTION_APPEARED)
        elif diff.has_fraction_before and not diff.has_fraction_after:
            diff.changes.append(StructuralFeature.FRACTION_DISAPPEARED)

        # 运算符检测
        diff.has_derivative_after = self._has_derivative(after_latex)
        diff.has_integral_after = self._has_integral(after_latex)
        diff.has_limit_after = self._has_limit(after_latex)
        diff.has_sum_after = self._has_sum(after_latex)
        diff.has_matrix_after = self._has_matrix(after_latex)

        if diff.has_derivative_after and not self._has_derivative(before_latex):
            diff.changes.append(StructuralFeature.DERIVATIVE_SYMBOL)
        if diff.has_integral_after and not self._has_integral(before_latex):
            diff.changes.append(StructuralFeature.INTEGRAL_SYMBOL)
        if diff.has_limit_after and not self._has_limit(before_latex):
            diff.changes.append(StructuralFeature.LIMIT_SYMBOL)
        if diff.has_sum_after and not self._has_sum(before_latex):
            diff.changes.append(StructuralFeature.SUM_SYMBOL)
        if diff.has_matrix_after and not self._has_matrix(before_latex):
            diff.changes.append(StructuralFeature.MATRIX_APPEARED)

        # 项数变化
        before_terms = self._count_terms(before_latex)
        after_terms = self._count_terms(after_latex)
        diff.terms_delta = after_terms - before_terms

        if diff.terms_delta > 1:
            diff.changes.append(StructuralFeature.NUMBER_OF_TERMS_INCREASED)
        elif diff.terms_delta < -1:
            diff.changes.append(StructuralFeature.NUMBER_OF_TERMS_DECREASED)

        if not diff.changes:
            diff.changes.append(StructuralFeature.NO_CHANGE)

        return diff

    def _extract_features(self, latex: str) -> List[StructuralFeature]:
        features = []
        if self._has_fraction(latex):
            features.append(StructuralFeature.FRACTION_APPEARED)
        if self._has_derivative(latex):
            features.append(StructuralFeature.DERIVATIVE_SYMBOL)
        if self._has_integral(latex):
            features.append(StructuralFeature.INTEGRAL_SYMBOL)
        if self._has_limit(latex):
            features.append(StructuralFeature.LIMIT_SYMBOL)
        if self._has_sum(latex):
            features.append(StructuralFeature.SUM_SYMBOL)
        if self._has_matrix(latex):
            features.append(StructuralFeature.MATRIX_APPEARED)
        if self._has_radical(latex):
            features.append(StructuralFeature.RADICAL_APPEARED)
        return features

    def _count_parentheses(self, latex: str) -> int:
        count = 0
        for ch in latex:
            if ch in "([{":
                count += 1
        return count

    def _has_fraction(self, latex: str) -> bool:
        return "\\frac" in latex or "/" in latex or "⁄" in latex

    def _has_derivative(self, latex: str) -> bool:
        patterns = [
            r"\\frac\{d\}",
            r"\\frac\{\\partial\}",
            r"\\dfrac\{d\}",
            r"f'",
            r"\\frac\{d\^",
            r"\\partial",
        ]
        return any(re.search(p, latex) for p in patterns)

    def _has_integral(self, latex: str) -> bool:
        return "\\int" in latex or "∫" in latex

    def _has_limit(self, latex: str) -> bool:
        return "\\lim" in latex or "lim" in latex

    def _has_sum(self, latex: str) -> bool:
        return "\\sum" in latex or "Σ" in latex or "∑" in latex

    def _has_matrix(self, latex: str) -> bool:
        return any(m in latex for m in ["\\begin{pmatrix}", "\\begin{bmatrix}",
                                         "\\begin{vmatrix}", "\\begin{matrix}"])

    def _has_radical(self, latex: str) -> bool:
        return "\\sqrt" in latex or "√" in latex

    def _count_terms(self, latex: str) -> int:
        clean = latex.strip()
        clean = re.sub(r"\\frac\{[^}]*\}\{[^}]*\}", "TERM", clean)
        clean = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "TERM", clean)
        terms = re.split(r"\s*[+\-]\s*", clean)
        terms = [t for t in terms if t.strip() and t.strip() != ""]
        return len(terms)


class OperationRecovery:
    """操作类型恢复器 — 视觉步骤 → 操作类型

    三级恢复策略：
      Level 1: 结构特征分析（纯视觉）
      Level 2: LaTeX 文本分析
      Level 3: LLM 推断

    用法：
        recovery = OperationRecovery(llm_client=client, model="gpt-4o")
        result = recovery.recover(steps)

        for op in result.operations:
            print(f"{op.before_latex} → {op.after_latex}: {op.op.value} (conf={op.confidence})")
    """

    def __init__(self, llm_client=None, model: str = ""):
        self._llm_client = llm_client
        self._model = model
        self._structural = StructuralAnalyzer()

    def recover_from_pair(self, before_latex: str, after_latex: str,
                          before_step_id: str = "",
                          after_step_id: str = "") -> RecoveredOperation:
        """从一对步骤恢复操作类型

        三级策略依次尝试，取置信度最高的结果。
        """
        # ── Level 1: 结构特征分析 ──
        structural_result = self._recover_structural(before_latex, after_latex)

        # ── Level 2: LaTeX 文本分析 ──
        textual_result = self._recover_textual(before_latex, after_latex)

        # ── 合并 Level 1 + Level 2 ──
        best = self._merge_results(structural_result, textual_result)

        # ── Level 3: LLM 推断（如果置信度不够）──
        if best.confidence < 0.5 and self._llm_client is not None:
            llm_result = self._recover_llm(before_latex, after_latex)
            best = self._merge_results(best, llm_result)

        best.before_latex = before_latex
        best.after_latex = after_latex
        best.before_step_id = before_step_id
        best.after_step_id = after_step_id

        return best

    def recover(self, steps: list) -> OperationRecoveryResult:
        """从步骤列表恢复所有相邻步骤间的操作类型

        Args:
            steps: VisualReasoningStep 或 VisualStep 列表

        Returns:
            OperationRecoveryResult
        """
        operations = []
        level_counts = {"structural": 0, "textual": 0, "llm": 0}

        for i in range(len(steps) - 1):
            before = steps[i]
            after = steps[i + 1]

            before_latex = self._get_latex(before)
            after_latex = self._get_latex(after)

            before_id = self._get_step_id(before)
            after_id = self._get_step_id(after)

            if not before_latex or not after_latex:
                continue

            op = self.recover_from_pair(
                before_latex, after_latex,
                before_step_id=before_id,
                after_step_id=after_id,
            )

            operations.append(op)
            level_counts[op.recovery_level.value] = level_counts.get(op.recovery_level.value, 0) + 1

        avg_conf = sum(op.confidence for op in operations) / max(len(operations), 1)

        return OperationRecoveryResult(
            operations=operations,
            total_pairs=len(operations),
            avg_confidence=avg_conf,
            level_counts=level_counts,
        )

    # ════════════════════════════════════════════════════════════
    # Level 1: 结构特征分析
    # ════════════════════════════════════════════════════════════

    def _recover_structural(self, before: str, after: str) -> RecoveredOperation:
        """Level 1: 基于结构特征推断操作类型

        规则：
          括号减少 + 项数增加 → EXPAND
          括号增加 + 项数减少 → FACTOR
          分数线消失         → SIMPLIFY / CANCEL
          d/dx 出现          → DIFFERENTIATE
          ∫ 出现             → INTEGRATE
          lim 出现           → COMPUTE_LIMIT
          Σ 出现             → SUM_SERIES
          矩阵出现           → MATRIX_OP
        """
        diff = self._structural.analyze(before, after)
        evidence = []
        candidates: List[Tuple[Op, float]] = []

        # 括号减少 + 项数增加 → 展开
        if StructuralFeature.PARENTHESES_REMOVED in diff.changes:
            if diff.terms_delta > 0:
                candidates.append((Op.EXPAND, 0.75))
                evidence.append("括号减少 + 项数增加 → 展开")
            else:
                candidates.append((Op.SIMPLIFY, 0.5))
                evidence.append("括号减少 → 化简")

        # 括号增加 + 项数减少 → 因式分解
        if StructuralFeature.PARENTHESES_ADDED in diff.changes:
            if diff.terms_delta < 0:
                candidates.append((Op.FACTOR, 0.75))
                evidence.append("括号增加 + 项数减少 → 因式分解")
            else:
                candidates.append((Op.SUBSTITUTE, 0.4))
                evidence.append("括号增加 → 可能代入")

        # 分数线变化
        if StructuralFeature.FRACTION_DISAPPEARED in diff.changes:
            candidates.append((Op.SIMPLIFY, 0.6))
            evidence.append("分数线消失 → 化简/约分")

        if StructuralFeature.FRACTION_APPEARED in diff.changes:
            candidates.append((Op.COMPUTE, 0.4))
            evidence.append("分数线出现 → 可能除法运算")

        # 微积分符号
        if StructuralFeature.DERIVATIVE_SYMBOL in diff.changes:
            candidates.append((Op.DIFFERENTIATE, 0.85))
            evidence.append("导数符号出现 → 求导")

        if StructuralFeature.INTEGRAL_SYMBOL in diff.changes:
            candidates.append((Op.INTEGRATE, 0.85))
            evidence.append("积分符号出现 → 积分")

        if StructuralFeature.LIMIT_SYMBOL in diff.changes:
            candidates.append((Op.COMPUTE_LIMIT, 0.85))
            evidence.append("极限符号出现 → 求极限")

        if StructuralFeature.SUM_SYMBOL in diff.changes:
            candidates.append((Op.SUM_SERIES, 0.8))
            evidence.append("求和符号出现 → 级数求和")

        if StructuralFeature.MATRIX_APPEARED in diff.changes:
            candidates.append((Op.MATRIX_OP, 0.8))
            evidence.append("矩阵出现 → 矩阵运算")

        # 项数大幅增加 → 展开
        if StructuralFeature.NUMBER_OF_TERMS_INCREASED in diff.changes:
            if not any(c[0] == Op.EXPAND for c in candidates):
                candidates.append((Op.EXPAND, 0.5))
                evidence.append("项数大幅增加 → 可能展开")

        # 项数大幅减少 → 因式分解/合并
        if StructuralFeature.NUMBER_OF_TERMS_DECREASED in diff.changes:
            if not any(c[0] == Op.FACTOR for c in candidates):
                candidates.append((Op.COLLECT, 0.5))
                evidence.append("项数大幅减少 → 可能合并同类项")

        if not candidates:
            candidates.append((Op.COMPUTE, 0.2))
            evidence.append("无明显结构变化 → 通用计算")

        best_op, best_conf = max(candidates, key=lambda c: c[1])

        return RecoveredOperation(
            op=best_op,
            confidence=best_conf,
            recovery_level=RecoveryLevel.STRUCTURAL,
            structural_diff=diff,
            evidence=evidence,
            alternatives=[(op, conf) for op, conf in candidates if op != best_op],
        )

    # ════════════════════════════════════════════════════════════
    # Level 2: LaTeX 文本分析
    # ════════════════════════════════════════════════════════════

    def _recover_textual(self, before: str, after: str) -> RecoveredOperation:
        """Level 2: 基于 LaTeX 文本推断操作类型

        利用已有的 infer_op_from_text + 额外的 LaTeX 模式匹配。
        """
        combined = f"{before} → {after}"
        evidence = []

        # 使用已有的关键词推断
        text_op = infer_op_from_text(combined)
        text_conf = 0.4

        # LaTeX 特定模式
        latex_patterns = [
            (r"\\frac\{d\}\{d[xy]\}", Op.DIFFERENTIATE, 0.8),
            (r"\\frac\{\\partial\}", Op.PARTIAL_DIFF, 0.8),
            (r"\\int[_\^]?", Op.INTEGRATE, 0.8),
            (r"\\lim_", Op.COMPUTE_LIMIT, 0.8),
            (r"\\sum_", Op.SUM_SERIES, 0.75),
            (r"\\prod_", Op.COMPUTE, 0.7),
            (r"\\sqrt", Op.SIMPLIFY, 0.3),
            (r"\\begin\{[pvb]?matrix\}", Op.MATRIX_OP, 0.8),
            (r"\\det", Op.DETERMINANT, 0.8),
            (r"\\Rightarrow|\\implies|\\to", Op.APPLY_THEOREM, 0.5),
        ]

        best_op = text_op
        best_conf = text_conf

        for pattern, op, conf in latex_patterns:
            if re.search(pattern, after) and not re.search(pattern, before):
                if conf > best_conf:
                    best_op = op
                    best_conf = conf
                    evidence.append(f"LaTeX 模式匹配: {pattern} → {op.value}")

        # 检测因式分解模式: (a)(b) 出现
        if re.search(r"\)\s*\(", after) and not re.search(r"\)\s*\(", before):
            if best_conf < 0.6:
                best_op = Op.FACTOR
                best_conf = 0.6
                evidence.append("检测到因式分解模式: (…)(…) 出现")

        # 检测展开模式: 括号表达式消失，多项出现
        if re.search(r"\([^\)]+\)", before) and not re.search(r"\([^\)]+\)", after):
            if best_conf < 0.5:
                best_op = Op.EXPAND
                best_conf = 0.5
                evidence.append("检测到展开模式: 括号表达式消失")

        if not evidence:
            evidence.append(f"关键词推断: {text_op.value}")

        return RecoveredOperation(
            op=best_op,
            confidence=best_conf,
            recovery_level=RecoveryLevel.TEXTUAL,
            evidence=evidence,
        )

    # ════════════════════════════════════════════════════════════
    # Level 3: LLM 推断
    # ════════════════════════════════════════════════════════════

    def _recover_llm(self, before: str, after: str) -> RecoveredOperation:
        """Level 3: 使用 LLM 推断操作类型

        将 before/after 发给 LLM，让其判断操作类型。
        """
        if self._llm_client is None:
            return RecoveredOperation(
                op=Op.COMPUTE,
                confidence=0.1,
                recovery_level=RecoveryLevel.LLM,
                evidence=["LLM 不可用"],
            )

        try:
            valid_ops = [op.value for op in Op]
            ops_str = ", ".join(valid_ops)

            response = self._llm_client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是数学操作类型分类器。给定变换前后的表达式，"
                            f"判断操作类型。可选类型: {ops_str}\n"
                            "只输出操作类型名称，不要其他内容。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"变换前: {before}\n变换后: {after}\n操作类型:",
                    },
                ],
                temperature=0.0,
                max_tokens=20,
            )

            result_text = response.choices[0].message.content.strip()

            try:
                recovered_op = normalize_op(result_text)
            except (ValueError, KeyError):
                recovered_op = Op.COMPUTE

            return RecoveredOperation(
                op=recovered_op,
                confidence=0.6,
                recovery_level=RecoveryLevel.LLM,
                evidence=[f"LLM 推断: {result_text}"],
            )

        except Exception:
            return RecoveredOperation(
                op=Op.COMPUTE,
                confidence=0.1,
                recovery_level=RecoveryLevel.LLM,
                evidence=["LLM 调用失败"],
            )

    # ════════════════════════════════════════════════════════════
    # 辅助
    # ════════════════════════════════════════════════════════════

    def _merge_results(self, *results: RecoveredOperation) -> RecoveredOperation:
        """合并多个恢复结果，取置信度最高的"""
        if not results:
            return RecoveredOperation()

        best = max(results, key=lambda r: r.confidence)

        all_evidence = []
        all_alternatives = []
        for r in results:
            all_evidence.extend(r.evidence)
            all_alternatives.extend(r.alternatives)

        best.evidence = all_evidence
        best.alternatives = list(set(all_alternatives))

        return best

    @staticmethod
    def _get_latex(step) -> str:
        if hasattr(step, "latex") and step.latex:
            return step.latex
        if hasattr(step, "to_latex"):
            return step.to_latex()
        if hasattr(step, "raw_text") and step.raw_text:
            return step.raw_text
        return ""

    @staticmethod
    def _get_step_id(step) -> str:
        if hasattr(step, "step_id"):
            return step.step_id
        return ""
