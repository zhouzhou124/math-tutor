"""Regression: Chinese prose must stay inline; \\neq must not break on newline unescape."""





def test_unescape_json_newlines_preserves_neq():

    from services.grading_adapter import _unescape_json_newlines, repair_derivation_text_block



    assert r"\neq" in _unescape_json_newlines(r"x \neq 0")

    assert r"\neq" in repair_derivation_text_block(r"左、右导数不相等（-1 \neq 1），故")





def test_standard_answer_repair_preserves_neq_no_unicode_escape():

    from services.grading_adapter import _repair_text_field, sanitize_structured_solution_for_render



    raw = r"x \neq 0"

    assert r"\neq" in _repair_text_field(raw)

    sol = sanitize_structured_solution_for_render({"standard_answer": raw})

    assert r"\neq" in sol["standard_answer"]





def test_compile_text_block_keeps_chinese_prose_as_one_block():

    from services.grading_adapter import compile_text_block_to_math_blocks



    prose = (

        "去掉绝对值，由对数函数的符号可得：当 $|x|>1$ 时，"

        r"\ln |x|>0$，故 $f(x)=\ln|x|$。"

    )

    blocks = compile_text_block_to_math_blocks(prose)

    assert len(blocks) == 1

    assert blocks[0]["type"] == "text"

    assert "去掉绝对值" in blocks[0]["content"]

    assert "|x|>1" in blocks[0]["content"] or r"|x|>1" in blocks[0]["content"]





def test_merge_inline_structured_blocks_text_latex_text():

    from services.grading_adapter import merge_inline_structured_blocks



    blocks = merge_inline_structured_blocks([

        {"type": "text", "content": "当 "},

        {"type": "latex", "display": "inline", "content": r"|x|>1"},

        {"type": "text", "content": " 时，故 "},

        {"type": "latex", "display": "inline", "content": r"f(x)=\ln|x|"},

        {"type": "text", "content": "。"},

    ])

    assert len(blocks) == 1

    assert blocks[0]["type"] == "text"

    joined = blocks[0]["content"]

    assert "当" in joined and "时" in joined

    assert "$" in joined





def test_coalesce_prose_inline_math_blocks():

    from services.grading_adapter import consolidate_view_blocks



    blocks = consolidate_view_blocks([

        {"type": "text", "content": "当 "},

        {"type": "latex_display", "content": r"|x|>1"},

        {"type": "text", "content": " 时，故 "},

        {"type": "latex_display", "content": r"f(x)=\ln|x|"},

        {"type": "text", "content": "。"},

    ])

    assert len(blocks) == 1

    assert blocks[0]["type"] == "text"

    joined = blocks[0]["content"]

    assert "当" in joined and "时" in joined

    assert "$" in joined





def test_display_math_stays_separate_block():

    from services.grading_adapter import normalize_standard_solution_view



    view = normalize_standard_solution_view({

        "question_type": "解答题",

        "sections": [{

            "title": "步骤",

            "blocks": [

                {"type": "text", "content": "化简得"},

                {"type": "latex_display", "content": r"\begin{aligned}x&=1\\y&=2\end{aligned}"},

            ],

        }],

    })

    types = [b["type"] for b in view["sections"][0]["blocks"]]

    assert "latex_display" in types





def test_left_right_and_to_stay_inline():

    from services.grading_adapter import (

        formula_requires_display_layout,

        normalize_standard_solution_view,

    )



    assert not formula_requires_display_layout(r"\left(-x\right)")

    assert not formula_requires_display_layout(r"x \to 1^-")



    view = normalize_standard_solution_view({

        "question_type": "选择题",

        "sections": [{

            "title": "分析",

            "blocks": [

                {"type": "text", "content": "在"},

                {"type": "latex", "display": "inline", "content": r"\left(-x\right)"},

                {"type": "text", "content": "处，"},

                {"type": "latex", "display": "inline", "content": r"x \to 1^-"},

                {"type": "text", "content": "时连续。"},

            ],

        }],

    })

    assert len(view["sections"][0]["blocks"]) == 1

    assert view["sections"][0]["blocks"][0]["type"] == "text"

    assert r"\left" in view["sections"][0]["blocks"][0]["content"]





def test_render_math_text_cjk_inline_uses_markdown_not_split(monkeypatch):

    from renderers.components import grading_result as mod



    split_called = []

    markdown_calls = []



    def _fake_split(_text):

        split_called.append(True)

        return []



    monkeypatch.setattr("latex_utils.split_latex_text", _fake_split)

    monkeypatch.setattr(mod.st, "markdown", lambda text, **kw: markdown_calls.append(text))



    mod.render_math_text("当 $x>1$ 时，$f(x)=\\ln x$。")

    assert markdown_calls

    assert not split_called





def test_conclusion_label_dropped_but_formula_kept():

    from services.grading_adapter import _dedupe_derivation_conclusion_blocks



    blocks = _dedupe_derivation_conclusion_blocks([

        {"type": "latex_display", "content": r"a=1"},

        {"type": "text", "content": "因此本步得到结论："},

        {"type": "latex_display", "content": r"b=2"},

    ])

    assert not any("因此本步得到结论" in str(b.get("content") or "") for b in blocks)

    assert any(r"b=2" in str(b.get("content") or "") for b in blocks)





def test_normalize_standard_solution_view_prose_not_fragmented():

    from services.grading_adapter import normalize_standard_solution_view



    view = normalize_standard_solution_view({

        "question_type": "选择题",

        "sections": [{

            "title": "选项分析",

            "blocks": [{

                "type": "text",

                "content": (

                    "分析 $x=-1$ 是否为驻点：当 $x<-1$（即 $|x|>1$ 且 $x<0$）时，"

                    r"$f(x)=\ln(-x)$。"

                ),

            }],

        }],

    })

    blocks = view["sections"][0]["blocks"]

    text_blocks = [b for b in blocks if b.get("type") == "text"]

    display_blocks = [b for b in blocks if b.get("type") == "latex_display"]

    assert len(text_blocks) >= 1

    assert len(display_blocks) <= 1

    assert "分析" in text_blocks[0]["content"]





def test_normalize_block_list_merges_fragmented_prose_chain():

    from services.grading_adapter import _normalize_block_list, normalize_standard_solution_view



    fragmented = [

        {"type": "text", "content": "当"},

        {"type": "latex_display", "content": r"|x|>1"},

        {"type": "text", "content": "时，"},

        {"type": "text", "content": "故"},

        {"type": "latex_display", "content": r"|x|=-1"},

        {"type": "text", "content": "不是驻点。"},

    ]

    merged = _normalize_block_list(fragmented)

    assert len(merged) == 1

    assert merged[0]["type"] == "text"

    assert "当" in merged[0]["content"] and "不是驻点" in merged[0]["content"]



    view = normalize_standard_solution_view({

        "question_type": "选择题",

        "sections": [{"title": "选项分析", "blocks": fragmented}],

    })

    assert len(view["sections"][0]["blocks"]) == 1

