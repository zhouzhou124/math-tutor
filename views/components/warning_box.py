"""WarningBox — 错误可视化组件

═══════════════════════════════════════════════════════════════
核心 API
═══════════════════════════════════════════════════════════════

  render_warning(error)              → 多种输入 → 错误框
  render_warning_dict(error_dict)    → dict → 错误框
  render_warning_type(error_type)    → ErrorType → 错误框

═══════════════════════════════════════════════════════════════
渲染效果
═══════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────┐
  │ ⚠️ 约分时遗漏条件                       │
  │                                         │
  │ x - 1 ≠ 0                              │
  │                                         │
  │ 约去公因子 x-1 时，必须保证 x-1≠0，    │
  │ 否则等价性被破坏。                      │
  │                                         │
  │ 💡 建议：添加条件 x-1≠0                │
  └─────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import streamlit as st

from rendering.document_ast import WarningBlock
from rendering.error_renderer import (
    ErrorRenderer,
    ErrorRendererConfig,
    VisualError,
    ErrorLevel,
)
from rendering.math_formatter import MathFormatter


_fmt = MathFormatter()
_renderer = ErrorRenderer()


_LEVEL_TO_ST = {
    ErrorLevel.INFO: st.info,
    ErrorLevel.WARNING: st.warning,
    ErrorLevel.ERROR: st.error,
    ErrorLevel.CRITICAL: st.error,
}


def render_warning(
    error: Any,
    step_id: str = "",
) -> None:
    """
    渲染错误可视化.

    支持多种输入:
      - WarningBlock → 通过 ErrorRenderer 可视化
      - VisualError → 直接渲染
      - str → 作为 error_type 处理
      - dict → 通过 ErrorRenderer.visualize_dict 处理
    """
    if isinstance(error, VisualError):
        _render_visual_error(error)
    elif isinstance(error, WarningBlock):
        ve = _renderer.visualize_warning(error, step_id)
        _render_visual_error(ve)
    elif isinstance(error, str):
        ve = _renderer.visualize_error_type(error, step_id)
        _render_visual_error(ve)
    elif isinstance(error, dict):
        ve = _renderer.visualize_dict(error)
        _render_visual_error(ve)
    else:
        st.error(f"⚠️ {str(error)}")


def render_warning_dict(error: dict) -> None:
    """dict → 错误框."""
    render_warning(error)


def render_warning_type(
    error_type: str,
    step_id: str = "",
    **kwargs,
) -> None:
    """ErrorType → 错误框."""
    ve = _renderer.visualize_error_type(error_type, step_id, **kwargs)
    _render_visual_error(ve)


def render_warnings(errors: Sequence[Any], step_id: str = "") -> None:
    """批量渲染错误."""
    for error in errors:
        render_warning(error, step_id)


# ═══════════════════════════════════════════════════════════
# Internal
# ═══════════════════════════════════════════════════════════

def _render_visual_error(ve: VisualError) -> None:
    st_fn = _LEVEL_TO_ST.get(ve.severity, st.warning)

    header = f"{ve.icon} {ve.title}" if ve.title else f"{ve.icon} 错误"

    if ve.condition or ve.explanation or ve.suggestion or ve.correction:
        with st_fn(header):
            if ve.condition:
                condition = _strip_dollars(_fmt.normalize(ve.condition))
                st.latex(condition)

            if ve.explanation:
                st.markdown(ve.explanation)

            if ve.suggestion:
                st.markdown(f"💡 **建议：** {ve.suggestion}")

            if ve.correction:
                st.markdown(f"✅ **正确做法：** {ve.correction}")

            if ve.related_concept:
                st.caption(f"📚 相关概念：{ve.related_concept}")
    else:
        st_fn(header)


def _strip_dollars(s: str) -> str:
    s = s.strip()
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()
    return s
