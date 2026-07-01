def test_max_event_text_becomes_inline_math():
    from services.grading_adapter import normalize_text_block_math

    blocks = normalize_text_block_math(r"事件 {\max(X,Y)\le1} 表示 X 和 Y 中较大者不超过 1")
    assert len(blocks) == 1 and blocks[0]["type"] == "text"
    content = blocks[0]["content"]
    assert r"\max(X,Y)\le1" in content
    assert "$" in content or r"\(" in content


def test_bad_subscript_becomes_inline_math():
    from services.grading_adapter import normalize_text_block_math

    text = normalize_text_block_math(r"令 Z 为 X_\{10\} 与前 9 个样本均值的差。")[0]["content"]
    assert "X_{10}" in text
    assert "$" in text or r"\(X_{10}\)" in text


def test_infy_is_repaired():
    from services.grading_adapter import normalize_text_block_math

    text = normalize_text_block_math(r"x\to+\infy 时收敛")[0]["content"]
    assert r"\infty" in text


def test_lim_x_to_is_repaired():
    from services.grading_adapter import normalize_text_block_math

    text = normalize_text_block_math(r"\lim_x\to0 f(x)=1")[0]["content"]
    assert r"\lim_{x\to0" in text


def test_dxdy_is_repaired():
    from services.grading_adapter import normalize_differential_tokens

    assert normalize_differential_tokens(r"\iint_D f(x,y) dxdy") == r"\iint_D f(x,y) dx\,dy"


def test_orphan_a_merges_with_latex_display():
    from services.grading_adapter import merge_orphan_lhs_with_formula_blocks

    blocks = merge_orphan_lhs_with_formula_blocks([
        {"type": "text", "content": "A="},
        {"type": "latex_display", "content": r"\iint_D f(x,y)\,dxdy"},
    ])
    assert len(blocks) == 1
    assert blocks[0]["type"] == "latex_display"
    content = blocks[0]["content"]
    assert "A" in content and r"\iint_D" in content
    assert r"dx\,dy" in content
    assert "&=" in content


def test_orphan_c_merges_with_latex_display():
    from services.grading_adapter import merge_orphan_lhs_with_formula_blocks

    blocks = merge_orphan_lhs_with_formula_blocks([
        {"type": "text", "content": "C="},
        {"type": "latex_display", "content": r"\frac{1}{2}"},
    ])
    content = blocks[0]["content"]
    assert r"\frac{1}{2}" in content
    assert "C" in content
    assert "$" in content or "&=" in content


def test_orphan_y_merges_with_latex_display():
    from services.grading_adapter import merge_orphan_lhs_with_formula_blocks

    blocks = merge_orphan_lhs_with_formula_blocks([
        {"type": "text", "content": "y="},
        {"type": "latex_display", "content": "x+1"},
    ])
    content = blocks[0]["content"]
    assert "y" in content and "x+1" in content
    assert "$" in content or "&=" in content


def test_short_formula_prefers_inline():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "填空题",
        "sections": [{"title": "结论", "blocks": [{"type": "latex_display", "content": r"A=\frac{1}{2}"}]}],
    })
    assert view["sections"][0]["blocks"][0]["type"] == "text"


def test_latex_explicit_block_display_not_demoted():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{
            "title": "结论",
            "blocks": [{"type": "latex", "display": "block", "content": r"x=1"}],
        }],
    })
    assert view["sections"][0]["blocks"][0]["type"] == "latex_display"


def test_matrix_remains_display():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "矩阵", "blocks": [{"type": "latex_display", "content": r"\begin{pmatrix}1&0\\0&1\end{pmatrix}"}]}],
    })
    assert view["sections"][0]["blocks"][0]["type"] == "latex_display"


def test_cases_lhs_and_alternating_conditions_are_preserved():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{
            "title": "步骤1",
            "blocks": [{
                "type": "latex_display",
                "content": (
                    r"\varphi(x)=\begin{cases}"
                    r"e^{x-1}\\x<1\\x-1\\x>1"
                    r"\end{cases}"
                ),
            }],
        }],
    })

    block = view["sections"][0]["blocks"][0]
    assert block["type"] == "cases"
    assert block["lhs"] == r"\varphi(x)"
    assert block["rows"] == [
        {"expr": r"e^{x-1}", "condition": "x<1"},
        {"expr": "x-1", "condition": "x>1"},
    ]


def test_cases_three_piece_alternating_conditions_are_preserved():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{
            "title": "步骤2",
            "blocks": [{
                "type": "latex_display",
                "content": (
                    r"y=\begin{cases}"
                    r"xe^{x-1}\\x<1\\1\\x=1\\2e^{x-1}-x\\x>1"
                    r"\end{cases}"
                ),
            }],
        }],
    })

    block = view["sections"][0]["blocks"][0]
    assert block["type"] == "cases"
    assert block["lhs"] == "y"
    assert block["rows"][1] == {"expr": "1", "condition": "x=1"}
    assert block["rows"][2] == {"expr": r"2e^{x-1}-x", "condition": "x>1"}


def test_mixed_text_cases_keep_lhs_and_conditions():
    from services.grading_adapter import normalize_text_block_math

    blocks = normalize_text_block_math(
        r"\varphi(x)=\begin{cases}e^{x-1}\\x<1\\x-1\\x>1\end{cases}"
    )

    assert blocks == [{
        "type": "cases",
        "lhs": r"\varphi(x)",
        "rows": [
            {"expr": r"e^{x-1}", "condition": "x<1"},
            {"expr": "x-1", "condition": "x>1"},
        ],
    }]


def test_double_integral_remains_display():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "积分", "blocks": [{"type": "latex_display", "content": r"\iint_D f(x,y)\,dxdy"}]}],
    })
    assert view["sections"][0]["blocks"][0]["type"] == "latex_display"
    assert r"dx\,dy" in view["sections"][0]["blocks"][0]["content"]


def test_ai_grading_malformed_integral_text_becomes_inline():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({
        "_structured": {"steps": [{
            "label": "步骤1",
            "blocks": [{"type": "text", "content": r"$(\int) \\(\frac{e^x}{(e^x+3)^2})$ dx"}],
        }]}
    }, "解答题")
    blocks = view["sections"][0]["blocks"]
    assert len(blocks) == 1
    assert blocks[0]["type"] == "text"
    assert r"\int" in blocks[0]["content"]
    assert "frac" in blocks[0]["content"]


def test_ai_grading_placeholder_and_unclosed_inline_are_removed():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({
        "_structured": {"steps": [{
            "label": "步骤2",
            "blocks": [{"type": "text", "content": r"dx\Rightarrow\(u=e^x+3,\,du=e^x dx,\\int @@MATH2@@ du)"}],
        }]}
    }, "解答题")
    text = str(view)
    assert "@@MATH" not in text
    assert r"\(" not in text
    assert view["sections"][0]["blocks"][0]["content"].endswith(r"\int\,du")


def test_ai_grading_differential_newline_fragment_is_repaired():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({
        "_structured": {"steps": [{
            "label": "步骤3",
            "blocks": [{"type": "text", "content": r"$(\int) \\(\frac{1}{u^2})\\ du\Rightarrow-(\frac{1}{u})$ + C"}],
        }]}
    }, "解答题")
    content = view["sections"][0]["blocks"][0]["content"]
    assert r"\,du" in content
    assert r"\\ du" not in content
    assert r"\Rightarrow" in content


def test_ai_grading_back_substitution_rightarrow_stays_inline():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({
        "_structured": {"steps": [{
            "label": "步骤4",
            "blocks": [{"type": "text", "content": r"C\Rightarrow-(\\frac{1}{e^x+3}) + C"}],
        }]}
    }, "解答题")
    block = view["sections"][0]["blocks"][0]
    assert block["type"] == "text"
    assert r"\Rightarrow" in block["content"]
    assert r"\frac{1}{e" in block["content"]


def test_reason_duplicates_first_block_removed():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "步骤1", "reason": "由题意可得 x=1", "blocks": [{"type": "text", "content": "由题意可得 x=1"}]}],
    })
    assert "由题意可得" in view["sections"][0]["reason"]
    assert "x=1" in view["sections"][0]["reason"].replace("$", "").replace("\\(", "").replace("\\)", "")
    assert view["sections"][0]["blocks"] == []


def test_conclusion_duplicates_final_answer_removed():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "步骤", "blocks": [{"type": "text", "content": "所以 x=1"}], "conclusion": "所以 x=1"}],
        "final_answer": {"type": "text", "content": "所以 x=1"},
    })
    assert view["sections"][0]["conclusion"] == ""
    assert view["final_answer"] == {}


def test_final_answer_does_not_extract_long_analysis():
    from services.grading_adapter import _extract_final_answer

    text = "步骤1：先分析。" * 50 + "步骤2：继续计算。"
    assert _extract_final_answer({"standard_answer": text}, "解答题") == {}


def test_proof_default_is_neutral():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "根据条件进行推导。"}, "证明题")
    assert view["answer_card"]["proof_status"] == "证明过程"


class _Recorder:
    def __init__(self):
        self.calls = []

    def markdown(self, text, *args, **kwargs):
        self.calls.append(("markdown", str(text), kwargs))

    def code(self, text, *args, **kwargs):
        self.calls.append(("code", str(text), kwargs))

    def write(self, text, *args, **kwargs):
        self.calls.append(("write", str(text), kwargs))


def test_text_renderer_does_not_markdown_raw_frac(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    rendered = []
    monkeypatch.setattr(mod.st, "markdown", rec.markdown)
    monkeypatch.setattr(mod.st, "code", rec.code)
    monkeypatch.setattr(mod.st, "write", rec.write)
    monkeypatch.setattr(mod, "_render_text_or_latex", lambda text: rendered.append(text))
    mod.render_math_text(r"\frac{1}{2}")
    assert len(rendered) == 1
    assert "$" in rendered[0] and r"\frac{1}{2}" in rendered[0]
    assert not any(c[0] == "markdown" and r"\frac" in c[1] for c in rec.calls)


def test_bad_latex_fragment_fallback_is_code(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    monkeypatch.setattr(mod.st, "markdown", rec.markdown)
    monkeypatch.setattr(mod.st, "code", rec.code)
    monkeypatch.setattr(mod.st, "write", rec.write)
    mod.render_math_text(r"\sum_{")
    assert any(c[0] == "code" for c in rec.calls)


def test_a_c_i_structure_has_no_bare_dxdy():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "步骤", "blocks": [
            {"type": "text", "content": "A="},
            {"type": "latex_display", "content": r"\iint_D f(x,y) dxdy"},
            {"type": "text", "content": "I_1="},
            {"type": "latex_display", "content": r"\int_0^1 x dx"},
        ]}],
    })
    text = str(view)
    assert "dxdy" not in text
    assert "A" in text and "I_1" in text
    assert "&=" in text


def test_final_conclusion_does_not_repeat_bare_fraction():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "步骤", "blocks": [], "conclusion": r"A=\frac{1}{2}"}],
        "final_answer": {"type": "latex_display", "content": r"\frac{1}{2}"},
    })
    assert view["final_answer"] == {}


def test_p50_question_type_view_still_builds():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "B"}, "选择题", {"correct_option": "B"})
    assert view["question_type"] == "选择题"
    assert view["answer_card"]["correct_answer"] == "B"


def test_split_glued_nonhomogeneous_and_particular():
    from latex_utils import normalize_derivation_formula_block

    out = normalize_derivation_formula_block(r"2xe^x y_p = x(Ax + B)e^x")
    assert r"\begin{cases}" in out
    assert "2xe^x" in out
    assert "y_p" in out


def test_ode_and_homogeneous_solution_not_one_aligned_chain():
    from latex_utils import normalize_derivation_formula_block

    out = normalize_derivation_formula_block(r"y''-3y'+2y = 0, y_h = C_1 e^x + C_2 e^{2x}")
    assert r"\begin{cases}" in out
    assert "y_h" in out
    assert r"\begin{aligned}" not in out


def test_chained_cases_row_splits_coefficient_and_general_solution():
    from latex_utils import repair_system_display_latex

    raw = r"\begin{cases} B = -2y = C_1 e^x + C_2 e^{2x} - (x^2 + 2x)e^x \end{cases}"
    out = repair_system_display_latex(raw)
    assert "B = -2" in out
    assert "y = C_1" in out or "y =" in out
    assert "= C_1 e^x" in out


def test_reason_with_y_prime_gets_inline_math():
    from services.grading_adapter import normalize_section_meta

    sec = normalize_section_meta({
        "title": "步骤3",
        "reason": "求导得 y_p' = (Ax^2 + B)e^x，代入得 -2A=2",
    })
    assert r"\(" in sec["reason"] or "$" in sec["reason"]


def test_body_markdown_not_prepended_when_blocks_overlap():
    from services.grading_adapter import _ensure_body_markdown_blocks

    structured = _ensure_body_markdown_blocks({
        "steps": [{
            "body_markdown": "特征方程为 r^2-3r+2=0，解得 r_1=1",
            "blocks": [{"type": "text", "content": "特征方程为 r^2-3r+2=0，解得 r_1=1, r_2=2"}],
        }],
    })
    blocks = structured["steps"][0]["blocks"]
    assert sum(1 for b in blocks if b.get("_source") == "body_markdown") == 0
