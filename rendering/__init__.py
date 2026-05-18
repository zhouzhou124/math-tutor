"""Rendering Layer - 数学 IDE 渲染层

Renderer 只消费 ViewModel，不直接接触 Domain Model。
数据流：Domain → Mapper → ViewModel → Renderer → HTML

Design Token 系统：所有颜色、状态、图标统一管理。

架构原则：
- Renderer 返回 HTML String，不调用任何 UI 框架
- Adapter 层负责将 HTML 渲染到具体 UI 框架（Streamlit/Web/PDF）
"""

from .tokens import (
    ColorToken,
    SpacingToken,
    RadiusToken,
    ShadowToken,
    FontToken,
    StepStatus,
    FormulaStatus,
    DiffStatus,
    ErrorCategory,
    Difficulty,
    QuestionType,
    UserRole,
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
)
from .adapters import render_html, render_markdown, render_component, render_components


def __getattr__(name):
    components = {
        "FormulaBlock": ".components",
        "KnowledgeTag": ".components",
        "ReasoningStepCard": ".cards",
        "ErrorHighlight": ".cards",
        "DiagnosisPanel": ".cards",
        "ScorePanel": ".cards",
        "MarkdownRenderer": ".renderers",
        "LatexRenderer": ".renderers",
        "ReasoningRenderer": ".renderers",
        "DiffRenderer": ".renderers",
    }
    if name in components:
        import importlib
        module = importlib.import_module(components[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ColorToken",
    "SpacingToken",
    "RadiusToken",
    "ShadowToken",
    "FontToken",
    "StepStatus",
    "FormulaStatus",
    "DiffStatus",
    "ErrorCategory",
    "Difficulty",
    "QuestionType",
    "UserRole",
    "TagType",
    "STEP_STATUS_ICON",
    "FORMULA_STATUS_ICON",
    "DIFF_STATUS_ICON",
    "QUESTION_TYPE_ICON",
    "DIFFICULTY_TAG",
    "ERROR_CATEGORY_ICON",
    "STATUS_CSS_CLASS",
    "STATUS_BORDER_COLOR",
    "STATUS_BG_COLOR",
    "render_html",
    "render_markdown",
    "render_component",
    "render_components",
    "FormulaBlock",
    "KnowledgeTag",
    "ReasoningStepCard",
    "ErrorHighlight",
    "DiagnosisPanel",
    "ScorePanel",
    "MarkdownRenderer",
    "LatexRenderer",
    "ReasoningRenderer",
    "DiffRenderer",
]
