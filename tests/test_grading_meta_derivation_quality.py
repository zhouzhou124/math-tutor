from services.grading_adapter import (
    contains_raw_tex_outside_math,
    normalize_text_block_math,
)


def test_meta_only_structured_steps_are_not_accepted_as_detailed_solution():
    from services.solution_quality import solution_quality_report

    sol = {
        "standard_answer": "步骤1。步骤2。最终答案：S=\\pi/4。",
        "_structured": {
            "steps": [
                {
                    "label": "步骤1：列切线距离条件",
                    "goal": "写出切线距离条件",
                    "reason": "由参数方程求切线斜率，再利用距离公式得到关系式。",
                },
                {
                    "label": "步骤2：求解 f'(t)",
                    "goal": "求解导数并积分",
                    "reason": "移项开方，利用 f'(t)>0 和 cos t>0 去掉绝对值。",
                },
            ],
            "final_answer": {"type": "latex", "content": r"S=\frac{\pi}{4}"},
        },
    }

    report = solution_quality_report(sol, {"question_type": "解答题"})

    assert report["detailed"] is False
    assert report["complete"] is False
    assert "missing_derivation_body" in report["issues"]


def test_derivative_inequality_and_plain_trig_are_wrapped_inline():
    text = "移项开方，利用已知 f'(t)>0，cos t > 0，sec t + tan t > 0 去掉绝对值。"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$f'(t)>0$" in rendered
    assert r"$\cos{} t > 0$" in rendered
    assert r"$\sec{} t + \tan{} t > 0$" in rendered
    assert "sec t + tan t" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_exp_times_variable_formula_is_not_truncated():
    text = "代入整理得到 f''(t)-f'(t)=e^t t=xy>0。"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$f''(t)-f'(t)=e^t t=xy>0$" in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_unicode_integral_and_log_relations_are_wrapped_as_whole_formulas():
    text = (
        "\u4e24\u8fb9\u79ef\u5206\uff1a\u5de6\u8fb9 \u222b(1/y)dy = ln|y|\uff0c"
        "\u53f3\u8fb9 \u222b(1/x - 1)dx = ln|x| - x + C"
    )

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$\int (1/y)dy = \ln|y|$" in rendered
    assert r"$\int (1/x - 1)dx = \ln|x| - x + C$" in rendered
    assert "\u222b" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_bare_log_equation_is_wrapped_as_single_inline_formula():
    text = "ln|y|=ln|x|-x+C_1"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"$\ln|y|=\ln|x|-x+C_1$" in rendered
    assert "ln|y|=ln|x|" not in rendered
    assert not contains_raw_tex_outside_math(rendered)


def test_malformed_integral_shorthand_line_is_dropped_when_no_formula_body():
    text = "\u4e24\u8fb9\u79ef\u5206\uff1a\u5de6\u8fb9 (1/y),d\u53f3\u8fb9 (1/x - 1),d"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert "(1/y),d" not in rendered
    assert "(1/x - 1),d" not in rendered


def test_constant_absorption_artifact_is_removed_from_general_solution():
    text = r"y=Cxe^{-x}C=\pm e^{C_1}"

    blocks = normalize_text_block_math(text)
    rendered = "\n".join(str(block.get("content", "")) for block in blocks)

    assert r"y=Cxe^{-x}" in rendered
    assert r"C=\pm" not in rendered
