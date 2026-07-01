def test_derivation_conclusion_label_is_not_rendered_as_repeated_step_text():
    from services.grading_adapter import normalize_text_block_math

    blocks = normalize_text_block_math(r"因此本步得到结论： \(x=1\)")

    text = "\n".join(
        str(block.get("content") or "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    )
    assert "因此本步得到结论" not in text
    assert any(
        isinstance(block, dict)
        and block.get("type") in {"text", "latex_display", "equation_group", "derivation_chain"}
        and "x=1" in str(block.get("content") or block.get("items") or "")
        for block in blocks
    )


def test_step_conclusion_metadata_is_preserved_without_duplicate_blocks():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {
            "_structured": {
                "steps": [{
                    "label": "步骤1：建立方程",
                    "goal": "步骤1：确定未知量。",
                    "reason": "根据题设关系列式。",
                    "conclusion": "得到方程。",
                }]
            }
        },
        "解答题",
    )

    section = view["sections"][0]
    assert section["reason"] == "根据题设关系列式。"
    assert section["conclusion"] == "得到方程。"
