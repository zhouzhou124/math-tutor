"""
Error Renderer — 数学级错误可视化

═══════════════════════════════════════════════════════════════
核心问题
═══════════════════════════════════════════════════════════════

  现在:
    错误：constraint lost

  未来:
    ⚠️ 约分时遗漏条件：

    x - 1 ≠ 0

    或者:

    ⚠️ 不等式方向错误：

    两边同时乘负数时，
    不等号方向必须改变。

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  ErrorType / ErrorSeverity / WarningBlock
      ↓
  ErrorRenderer
      ↓
  VisualError
    ├── icon          — ⚠️ / ❌ / 💡
    ├── title         — "约分时遗漏条件"
    ├── condition     — "x - 1 ≠ 0"  (display math)
    ├── explanation   — "约去公因子时，必须保证..."
    ├── suggestion    — "添加条件 x ≠ 1"
    └── severity      — warning / error / info

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Sequence

from rendering.document_ast import (
    BlockType,
    DocumentNode,
    WarningBlock,
)


# ═══════════════════════════════════════════════════════════
# Error Visualization Data Structure
# ═══════════════════════════════════════════════════════════

class ErrorLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class VisualError:
    """
    可视化错误 — 数学级错误展示结构.

    相比 WarningBlock，增加了:
      - icon: 视觉图标
      - title: 错误标题（人类可读）
      - condition: 数学条件（display math）
      - explanation: 详细解释
      - correction: 正确做法
      - related_concept: 关联知识点
    """
    icon: str = "⚠️"
    title: str = ""
    condition: str = ""
    explanation: str = ""
    suggestion: str = ""
    correction: str = ""
    related_concept: str = ""
    severity: ErrorLevel = ErrorLevel.WARNING
    source_error_type: str = ""
    source_step_id: str = ""

    @property
    def is_critical(self) -> bool:
        return self.severity == ErrorLevel.CRITICAL

    @property
    def is_error(self) -> bool:
        return self.severity in (ErrorLevel.ERROR, ErrorLevel.CRITICAL)

    def to_dict(self) -> dict:
        d = {
            "icon": self.icon,
            "title": self.title,
            "severity": self.severity.value,
        }
        if self.condition:
            d["condition"] = self.condition
        if self.explanation:
            d["explanation"] = self.explanation
        if self.suggestion:
            d["suggestion"] = self.suggestion
        if self.correction:
            d["correction"] = self.correction
        if self.related_concept:
            d["related_concept"] = self.related_concept
        if self.source_error_type:
            d["source_error_type"] = self.source_error_type
        if self.source_step_id:
            d["source_step_id"] = self.source_step_id
        return d


# ═══════════════════════════════════════════════════════════
# Error Pattern Registry
# ═══════════════════════════════════════════════════════════

@dataclass
class ErrorPattern:
    """
    错误可视化模式 — 将机器错误码映射为人类可读展示.

    每个模式定义:
      - error_type: 错误类型标识（匹配 ErrorType / DiagnosisErrorType）
      - icon: 视觉图标
      - title_template: 标题模板（支持 {variable} 插值）
      - condition_template: 数学条件模板
      - explanation_template: 解释模板
      - suggestion_template: 建议模板
      - correction_template: 正确做法模板
      - related_concept: 关联知识点
      - severity: 默认严重度
    """
    error_type: str = ""
    icon: str = "⚠️"
    title_template: str = ""
    condition_template: str = ""
    explanation_template: str = ""
    suggestion_template: str = ""
    correction_template: str = ""
    related_concept: str = ""
    severity: ErrorLevel = ErrorLevel.WARNING

    def render(self, **kwargs) -> VisualError:
        title = self.title_template.format(**kwargs) if self.title_template else ""
        condition = self.condition_template.format(**kwargs) if self.condition_template else ""
        explanation = self.explanation_template.format(**kwargs) if self.explanation_template else ""
        suggestion = self.suggestion_template.format(**kwargs) if self.suggestion_template else ""
        correction = self.correction_template.format(**kwargs) if self.correction_template else ""

        return VisualError(
            icon=self.icon,
            title=title,
            condition=condition,
            explanation=explanation,
            suggestion=suggestion,
            correction=correction,
            related_concept=self.related_concept,
            severity=self.severity,
            source_error_type=self.error_type,
        )


_BUILTIN_PATTERNS: list[ErrorPattern] = [
    ErrorPattern(
        error_type="constraint_lost",
        icon="⚠️",
        title_template="约分时遗漏条件",
        condition_template="{constraint}",
        explanation_template="约去公因子 {factor} 时，必须保证 {constraint}，否则等价性被破坏。",
        suggestion_template="添加条件 {constraint}",
        related_concept="等价变换 / 非零条件",
        severity=ErrorLevel.ERROR,
    ),
    ErrorPattern(
        error_type="division_by_zero",
        icon="❌",
        title_template="除以零错误",
        condition_template="{denominator} ≠ 0",
        explanation_template="除数 {denominator} 可能为零，除以零无定义。需先验证 {denominator} ≠ 0。",
        suggestion_template="讨论 {denominator} = 0 和 {denominator} ≠ 0 两种情况",
        related_concept="除法运算 / 定义域",
        severity=ErrorLevel.CRITICAL,
    ),
    ErrorPattern(
        error_type="direction_error",
        icon="⚠️",
        title_template="不等式方向错误",
        condition_template="",
        explanation_template="两边同时乘以负数时，不等号方向必须改变。",
        suggestion_template="乘以负数后翻转不等号方向",
        correction_template="若 a < b 且 k < 0，则 ka > kb",
        related_concept="不等式性质",
        severity=ErrorLevel.ERROR,
    ),
    ErrorPattern(
        error_type="sign_error",
        icon="⚠️",
        title_template="符号错误",
        condition_template="",
        explanation_template="运算过程中负号丢失或符号改变不正确。",
        suggestion_template="仔细检查每一步的符号变化",
        related_concept="代数运算 / 符号规则",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="equivalence_broken",
        icon="❌",
        title_template="等价性被破坏",
        condition_template="",
        explanation_template="该变换不是等价变换，可能引入增解或丢失解。",
        suggestion_template="使用等价变换，或补充条件保证等价性",
        related_concept="等价变换 / 充要条件",
        severity=ErrorLevel.ERROR,
    ),
    ErrorPattern(
        error_type="domain_changed",
        icon="⚠️",
        title_template="定义域改变",
        condition_template="{old_domain} → {new_domain}",
        explanation_template="变换后定义域从 {old_domain} 变为 {new_domain}，可能引入或丢失解。",
        suggestion_template="检查定义域变化，补充约束条件",
        related_concept="定义域 / 函数性质",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="assumption_unjustified",
        icon="⚠️",
        title_template="假设未验证",
        condition_template="{assumption}",
        explanation_template="使用了未验证的假设：{assumption}。需先证明或验证该假设成立。",
        suggestion_template="先证明 {assumption}，再使用",
        related_concept="数学证明 / 假设验证",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="wrong_operation",
        icon="❌",
        title_template="操作错误",
        condition_template="",
        explanation_template="使用了错误的数学操作或公式。",
        suggestion_template="回顾相关公式和操作规则",
        related_concept="数学运算规则",
        severity=ErrorLevel.ERROR,
    ),
    ErrorPattern(
        error_type="incomplete_transform",
        icon="⚠️",
        title_template="变换不完整",
        condition_template="",
        explanation_template="变换未完成，遗漏了某些情况或步骤。",
        suggestion_template="检查是否遗漏分支或特殊情况",
        related_concept="分类讨论 / 完备性",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="rule_misapplication",
        icon="❌",
        title_template="规则误用",
        condition_template="",
        explanation_template="错误地应用了数学规则，该规则在当前条件下不适用。",
        suggestion_template="检查规则的适用条件",
        related_concept="数学规则 / 适用条件",
        severity=ErrorLevel.ERROR,
    ),
    ErrorPattern(
        error_type="variable_scope_error",
        icon="⚠️",
        title_template="变量作用域错误",
        condition_template="",
        explanation_template="变量在当前作用域内未定义或超出有效范围。",
        suggestion_template="检查变量定义和作用域",
        related_concept="变量 / 作用域",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="branch_missing",
        icon="⚠️",
        title_template="遗漏分支",
        condition_template="",
        explanation_template="分类讨论时遗漏了某些情况，导致解不完整。",
        suggestion_template="补充遗漏的情况，确保讨论完备",
        related_concept="分类讨论 / 完备性",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="conceptual_error",
        icon="❌",
        title_template="概念错误",
        condition_template="",
        explanation_template="对数学概念的理解有误，导致推导方向错误。",
        suggestion_template="回顾相关概念的定义和性质",
        related_concept="数学概念",
        severity=ErrorLevel.ERROR,
    ),
    ErrorPattern(
        error_type="calculation_error",
        icon="⚠️",
        title_template="计算错误",
        condition_template="",
        explanation_template="数值计算或代数运算中出现错误。",
        suggestion_template="逐步检查计算过程",
        related_concept="代数运算",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="reasoning_error",
        icon="❌",
        title_template="推理错误",
        condition_template="",
        explanation_template="逻辑推理链中出现断裂或错误跳跃。",
        suggestion_template="检查每一步推理的依据",
        related_concept="逻辑推理 / 证明方法",
        severity=ErrorLevel.ERROR,
    ),
    ErrorPattern(
        error_type="missing_step",
        icon="💡",
        title_template="步骤缺失",
        condition_template="",
        explanation_template="推导过程中缺少关键步骤，导致逻辑不连贯。",
        suggestion_template="补充中间步骤，使推理链完整",
        related_concept="推理步骤 / 逻辑链",
        severity=ErrorLevel.INFO,
    ),
    ErrorPattern(
        error_type="algebraic_error",
        icon="⚠️",
        title_template="代数运算错误",
        condition_template="",
        explanation_template="代数运算（化简、展开、合并等）中出现错误。",
        suggestion_template="逐步验证代数运算的正确性",
        related_concept="代数运算",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="arithmetic_error",
        icon="⚠️",
        title_template="算术错误",
        condition_template="",
        explanation_template="基本数值计算（加减乘除）中出现错误。",
        suggestion_template="重新检查数值计算",
        related_concept="算术运算",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="logical_gap",
        icon="⚠️",
        title_template="推理断裂",
        condition_template="",
        explanation_template="前后步骤之间缺乏逻辑联系，推理链断裂。",
        suggestion_template="补充中间推理步骤",
        related_concept="逻辑推理",
        severity=ErrorLevel.WARNING,
    ),
    ErrorPattern(
        error_type="method_error",
        icon="❌",
        title_template="方法错误",
        condition_template="",
        explanation_template="选择了错误的解题方法或策略。",
        suggestion_template="重新审视题目，选择合适的方法",
        related_concept="解题策略",
        severity=ErrorLevel.ERROR,
    ),
]


class ErrorPatternRegistry:
    """
    错误模式注册表 — 管理所有错误可视化模式.

    支持:
      - 内置模式（覆盖常见数学错误）
      - 自定义模式（用户/模块注册）
      - 模式查找（按 error_type）
    """

    def __init__(self):
        self._patterns: dict[str, ErrorPattern] = {}
        for p in _BUILTIN_PATTERNS:
            self._patterns[p.error_type] = p

    def register(self, pattern: ErrorPattern) -> None:
        self._patterns[pattern.error_type] = pattern

    def get(self, error_type: str) -> Optional[ErrorPattern]:
        return self._patterns.get(error_type)

    def has(self, error_type: str) -> bool:
        return error_type in self._patterns

    def list_types(self) -> list[str]:
        return sorted(self._patterns.keys())

    def render(self, error_type: str, **kwargs) -> VisualError:
        pattern = self._patterns.get(error_type)
        if pattern:
            return pattern.render(**kwargs)
        return VisualError(
            icon="⚠️",
            title=error_type.replace("_", " ").title(),
            explanation=kwargs.get("message", ""),
            severity=ErrorLevel.WARNING,
            source_error_type=error_type,
        )


_default_registry = ErrorPatternRegistry()


# ═══════════════════════════════════════════════════════════
# Severity Mapping
# ═══════════════════════════════════════════════════════════

_SEVERITY_TO_LEVEL = {
    "correct": None,
    "minor": ErrorLevel.INFO,
    "info": ErrorLevel.INFO,
    "calculation": ErrorLevel.WARNING,
    "warning": ErrorLevel.WARNING,
    "reasoning": ErrorLevel.ERROR,
    "error": ErrorLevel.ERROR,
    "conceptual": ErrorLevel.ERROR,
    "missing": ErrorLevel.INFO,
    "critical": ErrorLevel.CRITICAL,
}

_SEVERITY_TO_ICON = {
    "info": "💡",
    "minor": "💡",
    "warning": "⚠️",
    "calculation": "⚠️",
    "error": "❌",
    "reasoning": "❌",
    "conceptual": "❌",
    "critical": "🚨",
    "missing": "💡",
}


# ═══════════════════════════════════════════════════════════
# Error Renderer
# ═══════════════════════════════════════════════════════════

@dataclass
class ErrorRendererConfig:
    show_condition: bool = True
    show_explanation: bool = True
    show_suggestion: bool = True
    show_correction: bool = True
    show_related_concept: bool = False
    show_icon: bool = True
    use_blockquote: bool = True


class ErrorRenderer:
    """
    错误可视化渲染器 — 将机器错误转为数学级可视化展示.

    核心能力:
      1. WarningBlock → VisualError → DocumentNode[]
      2. ErrorType → VisualError → DocumentNode[]
      3. dict → VisualError → DocumentNode[]
      4. 自定义错误模式注册
    """

    def __init__(
        self,
        config: ErrorRendererConfig = None,
        registry: ErrorPatternRegistry = None,
    ):
        self.config = config or ErrorRendererConfig()
        self._registry = registry or _default_registry

    def visualize_warning(self, warning: WarningBlock, step_id: str = "") -> VisualError:
        """WarningBlock → VisualError"""
        pattern = self._registry.get(warning.message) if warning.message else None

        if pattern:
            return pattern.render(
                constraint=warning.message,
                factor=warning.message,
                denominator=warning.message,
                assumption=warning.message,
                old_domain="",
                new_domain="",
                message=warning.message,
            )

        level = _SEVERITY_TO_LEVEL.get(warning.severity, ErrorLevel.WARNING)
        icon = _SEVERITY_TO_ICON.get(warning.severity, "⚠️")

        return VisualError(
            icon=icon,
            title=self._extract_title(warning.message),
            condition="",
            explanation=warning.message,
            suggestion=warning.suggestion,
            severity=level or ErrorLevel.WARNING,
            source_step_id=step_id or warning.location,
        )

    def visualize_error_type(
        self, error_type: str, step_id: str = "", **kwargs
    ) -> VisualError:
        """ErrorType 字符串 → VisualError"""
        ve = self._registry.render(error_type, **kwargs)
        if step_id:
            ve = VisualError(
                icon=ve.icon,
                title=ve.title,
                condition=ve.condition,
                explanation=ve.explanation,
                suggestion=ve.suggestion,
                correction=ve.correction,
                related_concept=ve.related_concept,
                severity=ve.severity,
                source_error_type=ve.source_error_type,
                source_step_id=step_id,
            )
        return ve

    def visualize_dict(self, error: dict) -> VisualError:
        """dict → VisualError"""
        error_type = error.get("error_type", error.get("type", ""))
        message = error.get("message", error.get("description", ""))
        suggestion = error.get("suggestion", "")
        severity_str = error.get("severity", "warning")
        condition = error.get("condition", "")
        step_id = error.get("step_id", error.get("location", ""))

        kwargs = {k: v for k, v in error.items() if k not in (
            "error_type", "type", "severity", "step_id", "location",
        )}
        kwargs.setdefault("constraint", condition or message)
        kwargs.setdefault("factor", error.get("factor", ""))
        kwargs.setdefault("denominator", error.get("denominator", ""))
        kwargs.setdefault("assumption", error.get("assumption", ""))

        if error_type and self._registry.has(error_type):
            ve = self._registry.render(error_type, **kwargs)
        else:
            level = _SEVERITY_TO_LEVEL.get(severity_str, ErrorLevel.WARNING)
            icon = _SEVERITY_TO_ICON.get(severity_str, "⚠️")
            ve = VisualError(
                icon=icon,
                title=self._extract_title(error_type or message),
                condition=condition,
                explanation=message,
                suggestion=suggestion,
                severity=level or ErrorLevel.WARNING,
                source_error_type=error_type,
                source_step_id=step_id,
            )

        if step_id:
            ve = VisualError(
                icon=ve.icon, title=ve.title, condition=ve.condition,
                explanation=ve.explanation, suggestion=ve.suggestion,
                correction=ve.correction, related_concept=ve.related_concept,
                severity=ve.severity, source_error_type=ve.source_error_type,
                source_step_id=step_id,
            )

        return ve

    def render_visual_error(self, ve: VisualError) -> list[DocumentNode]:
        """VisualError → DocumentNode[]"""
        nodes = []

        header = ve.title if ve.title else "错误"
        nodes.append(DocumentNode(
            type=BlockType.WARNING,
            content=WarningBlock(
                severity=ve.severity.value,
                message=header,
                suggestion="",
            ),
            metadata={"role": "error_header", "error_type": ve.source_error_type, "icon": ve.icon},
        ))

        if ve.condition and self.config.show_condition:
            nodes.append(DocumentNode(
                type=BlockType.DISPLAY_MATH,
                content=ve.condition,
                metadata={"role": "error_condition"},
            ))

        if ve.explanation and self.config.show_explanation:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=ve.explanation,
                metadata={"role": "error_explanation"},
            ))

        if ve.suggestion and self.config.show_suggestion:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"💡 建议：{ve.suggestion}",
                metadata={"role": "error_suggestion"},
            ))

        if ve.correction and self.config.show_correction:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"✅ 正确做法：{ve.correction}",
                metadata={"role": "error_correction"},
            ))

        if ve.related_concept and self.config.show_related_concept:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"📚 相关概念：{ve.related_concept}",
                metadata={"role": "error_concept"},
            ))

        return nodes

    def render_warning(self, warning: WarningBlock, step_id: str = "") -> list[DocumentNode]:
        """WarningBlock → DocumentNode[] (一步完成)"""
        ve = self.visualize_warning(warning, step_id)
        return self.render_visual_error(ve)

    def render_error_type(self, error_type: str, step_id: str = "", **kwargs) -> list[DocumentNode]:
        """ErrorType → DocumentNode[] (一步完成)"""
        ve = self.visualize_error_type(error_type, step_id, **kwargs)
        return self.render_visual_error(ve)

    def render_dict_error(self, error: dict) -> list[DocumentNode]:
        """dict → DocumentNode[] (一步完成)"""
        ve = self.visualize_dict(error)
        return self.render_visual_error(ve)

    def _extract_title(self, text: str) -> str:
        if not text:
            return "错误"
        title = text.replace("_", " ").strip()
        if " " in title:
            words = title.split()
            title = " ".join(w.capitalize() for w in words)
        else:
            title = title.capitalize()

        cn_map = {
            "Constraint Lost": "约分时遗漏条件",
            "Division By Zero": "除以零错误",
            "Direction Error": "不等式方向错误",
            "Sign Error": "符号错误",
            "Equivalence Broken": "等价性被破坏",
            "Domain Changed": "定义域改变",
            "Assumption Unjustified": "假设未验证",
            "Wrong Operation": "操作错误",
            "Incomplete Transform": "变换不完整",
            "Rule Misapplication": "规则误用",
            "Variable Scope Error": "变量作用域错误",
            "Branch Missing": "遗漏分支",
            "Conceptual Error": "概念错误",
            "Calculation Error": "计算错误",
            "Reasoning Error": "推理错误",
            "Missing Step": "步骤缺失",
            "Algebraic Error": "代数运算错误",
            "Arithmetic Error": "算术错误",
            "Logical Gap": "推理断裂",
            "Method Error": "方法错误",
        }
        return cn_map.get(title, title)


# ═══════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════

_default_renderer = ErrorRenderer()


def visualize_warning(warning: WarningBlock, step_id: str = "") -> VisualError:
    return _default_renderer.visualize_warning(warning, step_id)


def visualize_error_type(error_type: str, step_id: str = "", **kwargs) -> VisualError:
    return _default_renderer.visualize_error_type(error_type, step_id, **kwargs)


def visualize_dict(error: dict) -> VisualError:
    return _default_renderer.visualize_dict(error)


def render_warning(warning: WarningBlock, step_id: str = "") -> list[DocumentNode]:
    return _default_renderer.render_warning(warning, step_id)


def render_error_type(error_type: str, step_id: str = "", **kwargs) -> list[DocumentNode]:
    return _default_renderer.render_error_type(error_type, step_id, **kwargs)


def render_dict_error(error: dict) -> list[DocumentNode]:
    return _default_renderer.render_dict_error(error)


def register_error_pattern(pattern: ErrorPattern) -> None:
    _default_registry.register(pattern)


def get_error_registry() -> ErrorPatternRegistry:
    return _default_registry
