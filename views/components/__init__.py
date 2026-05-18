"""views/components/ — Streamlit 数学组件

═══════════════════════════════════════════════════════════════
核心组件
═══════════════════════════════════════════════════════════════

  MathBlock   — render_math_block(expr)     → st.latex
  StepCard    — render_step(step_block)      → 步骤卡片
  WarningBox  — render_warning(error)        → 错误可视化
  ProofBox    — render_obligation(obligation) → 证明义务

═══════════════════════════════════════════════════════════════
设计原则
═══════════════════════════════════════════════════════════════

  1. 每个组件只做一件事
  2. 输入来自 rendering/ 的 AST 结构
  3. 不依赖旧 renderers/ 的代码
  4. 所有组件可独立使用，也可组合

═══════════════════════════════════════════════════════════════
"""

from views.components.math_block import render_math_block
from views.components.step_card import render_step
from views.components.warning_box import render_warning
from views.components.proof_box import render_obligation, render_obligation_panel

__all__ = [
    "render_math_block",
    "render_step",
    "render_warning",
    "render_obligation",
    "render_obligation_panel",
]
