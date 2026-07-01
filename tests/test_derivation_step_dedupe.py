"""Dedupe redundant goal/conclusion/body in derivation steps."""


def test_proof_body_no_duplicate_middle_and_conclusion():
    from agents.solver_agent import _proof_step_body_markdown
    from types import SimpleNamespace

    step = SimpleNamespace(
        input_state="",
        output_state=r"D = \{(x, y) \mid y > 0\}",
    )
    body = _proof_step_body_markdown(step)
    assert body.count("中间公式为") == 1
    assert "因此本步得到结论" not in body
    assert body.count(r"D = \{(x, y) \mid y > 0\}") == 1


def test_goal_redundant_with_step_title():
    from services.grading_adapter import _goal_redundant_with_title

    assert _goal_redundant_with_title("确定定义域", "步骤1：确定定义域")
    assert _goal_redundant_with_title("步骤1：确定定义域", "步骤1：确定定义域")
    assert _goal_redundant_with_title("求一阶偏导数", "步骤2：求一阶偏导数")
    assert not _goal_redundant_with_title("利用链式法则", "步骤2：求一阶偏导数")


def test_strip_reason_display_tail():
    from services.grading_adapter import _strip_reason_display_tail

    reason = (
        "由 Fermat 引理，驻点处偏导为零。"
        "关键变形为：\\begin{cases} f_x = 0 \\\\ f_y = 0 \\end{cases}"
    )
    assert "关键变形" not in _strip_reason_display_tail(reason)
    assert "Fermat" in _strip_reason_display_tail(reason)


def test_dedupe_section_clears_redundant_goal_and_conclusion():
    from services.grading_adapter import dedupe_section_content

    view = dedupe_section_content({
        "sections": [{
            "title": "步骤1：确定定义域",
            "goal": "确定定义域",
            "reason": "函数含 \\(\\ln y\\)，需 \\(y>0\\)。",
            "blocks": [
                {"type": "latex_display", "content": r"D = \{(x, y) \mid y > 0\}"},
            ],
            "conclusion": r"D = \{(x, y) \mid y > 0\}",
        }],
    })
    sec = view["sections"][0]
    assert sec.get("goal") == ""
    assert sec.get("conclusion") == ""


def test_dedupe_section_clears_step_conclusion_even_when_unique():
    from services.grading_adapter import dedupe_section_content

    view = dedupe_section_content({
        "sections": [{
            "title": "步骤2：求偏导",
            "kind": "reasoning",
            "blocks": [{"type": "latex_display", "content": r"f_x = 2x"}],
            "conclusion": r"f_x = 2x + 1",
        }],
    })
    assert view["sections"][0].get("conclusion") == ""


def test_dedupe_aligned_tail_and_full_equation():
    from services.grading_adapter import _dedupe_derivation_conclusion_blocks

    blocks = _dedupe_derivation_conclusion_blocks([
        {
            "type": "latex_display",
            "content": (
                r"\begin{aligned}"
                r"I &= -\int_0^1 dx \int_x^1 e^{-y^2} dy \\"
                r"&= \frac{1}{2e}"
                r"\end{aligned}"
            ),
        },
        {
            "type": "latex_display",
            "content": r"I = \frac{1}{2e}",
        },
    ])
    assert len(blocks) == 1
