"""AI grading final-answer rendering regressions."""


def test_mixed_final_answer_uses_grading_renderer(monkeypatch):
    import latex_utils
    import renderers.math_render_policy as policy

    rendered: list[str] = []
    monkeypatch.setattr(policy, "render_grading_latex", lambda text: rendered.append(text))
    monkeypatch.setattr(
        latex_utils,
        "_render_blocks_safe",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("raw latex block path used")),
    )

    latex_utils._render_final_answer_safe({
        "type": "latex",
        "content": r"\boxed{(1) 证毕。(2) 当 \(a \ne 0\) 时，\[x_1=\frac{1}{(n+1)a}\]}",
    })

    assert rendered == [r"(1) 证毕。(2) 当 \(a \ne 0\) 时，\[x_1=\frac{1}{(n+1)a}\]"]


def test_simple_final_answer_still_uses_boxed_formula_path(monkeypatch):
    import latex_utils

    rendered_blocks = []
    monkeypatch.setattr(
        latex_utils,
        "_render_blocks_safe",
        lambda blocks, highlight=False: rendered_blocks.append((blocks, highlight)),
    )

    latex_utils._render_final_answer_safe({
        "type": "latex",
        "content": r"\boxed{x=1}",
    })

    assert rendered_blocks == [([{"type": "latex", "content": "x=1"}], True)]
