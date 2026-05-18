"""runtime_visualization — 运行时可视化层

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  WorldState / RuleApplicationResult / StepBlock
      ↓
  ┌─────────────────────────────────────────────────┐
  │ ObligationPanel       ← 证明义务面板（教学层）  │
  │ StateDiffEngine       ← 状态差异计算（调试器）  │
  │ StateTransitionViewer ← 状态转移查看器          │
  └─────────────────────────────────────────────────┘
      ↓
  ObligationView[] / StateDiff / TransitionChain
      ↓
  Streamlit UI / DocumentNode[] / Markdown / HTML

═══════════════════════════════════════════════════════════════
核心价值
═══════════════════════════════════════════════════════════════

  1. 数学规范性教学 — 不只看结果，更看过程是否严谨
     AI 判题器:  "你错了"
     数学导师:  "你缺少这个证明"

  2. 状态可视化 — 不只验证对错，更观察状态如何变化
     现在: "步骤 3 验证通过"
     未来: "步骤 3 新增约束 x>0，义务已证，置信度 +0.15"

═══════════════════════════════════════════════════════════════
"""

from runtime_visualization.obligation_panel import (
    ObligationView,
    ObligationTemplate,
    OBLIGATION_TEMPLATES,
    ObligationPanel,
    ObligationPanelConfig,
)

from runtime_visualization.state_diff import (
    ChangeCategory,
    ChangeDirection,
    ChangeRecord,
    StateDiff,
    StateDiffEngine,
    TransitionRecord,
    TransitionChain,
)

from runtime_visualization.state_transition_viewer import (
    TransitionViewerConfig,
    StateTransitionViewer,
)

__all__ = [
    "ObligationView",
    "ObligationTemplate",
    "OBLIGATION_TEMPLATES",
    "ObligationPanel",
    "ObligationPanelConfig",
    "ChangeCategory",
    "ChangeDirection",
    "ChangeRecord",
    "StateDiff",
    "StateDiffEngine",
    "TransitionRecord",
    "TransitionChain",
    "TransitionViewerConfig",
    "StateTransitionViewer",
]
