"""Derivation goal/reason layout for standard solution sections."""


def test_strip_step_prefix_from_goal():
    from services.grading_adapter import _strip_step_title_prefix

    assert _strip_step_title_prefix("步骤3：利用初始条件") == "利用初始条件"


def test_extract_goal_reason_from_legacy_body():
    from services.grading_adapter import _extract_goal_reason_from_body

    body = (
        "推导目标：步骤2：积分求通解。\n\n"
        "推导理由：两边对 x 积分。\n\n"
        "关键变形为：\n\n$$\n(xy)' = 0\n$$\n"
    )
    goal, reason, rest = _extract_goal_reason_from_body(body)
    assert goal == "步骤2：积分求通解"
    assert reason == "两边对 x 积分"
    assert "关键变形" in rest


def test_normalize_step_derivation_meta_splits_body():
    from services.grading_adapter import _normalize_step_derivation_meta

    step = _normalize_step_derivation_meta({
        "body_markdown": (
            "推导目标：步骤1：化简方程。\n\n"
            "推导理由：利用乘积求导。\n\n"
            "中间公式为：\n\n$$\n(xy)'=0\n$$"
        ),
    })
    assert step["goal"] == "化简方程"
    assert step["reason"] == "利用乘积求导"
    assert "推导目标" not in step["body_markdown"]
    assert "$$" in step["body_markdown"]


def test_render_derivation_meta_uses_separate_headings(monkeypatch):
    from renderers.components import grading_result as mod

    calls = []
    monkeypatch.setattr(mod, "render_math_text", lambda text: calls.append(f"MATH:{text}") or True)

    class _St:
        @staticmethod
        def markdown(text, *args, **kwargs):
            calls.append(str(text))

    monkeypatch.setattr(mod, "st", _St)

    mod._render_derivation_meta({
        "goal": "利用初始条件确定常数。",
        "reason": "代入初始条件。",
    })
    assert calls[0] == "**推导目标**"
    assert calls[1] == "MATH:利用初始条件确定常数。"
    assert calls[2] == "**推导理由**"
    assert calls[3] == "MATH:代入初始条件。"
