"""P29-2: strict CanonicalIR validation regressions."""


def _canonical_ir(output_state="x=1", justification="根据等式性质两边同减 1，得到方程的解。"):
    return {
        "agent": "solver",
        "question": {
            "text": "求方程的解。",
            "math_type": "数学一",
            "question_type": "解答题",
            "knowledge_points": ["方程"],
            "total_score": 10,
        },
        "proof_trace": {
            "steps": [
                {
                    "id": "s1",
                    "operation": "solve",
                    "input_state": "x+1=2",
                    "output_state": output_state,
                    "justification": justification,
                    "label": "求解方程",
                }
            ],
            "final_answer": "x=1",
        },
        "metadata": {},
    }


def test_formula_with_inline_dollar_is_invalid():
    from semantic_output import canonical_ir_formulas_are_clean, validate_canonical_ir

    ir = _canonical_ir(output_state="$x=1$")

    assert canonical_ir_formulas_are_clean(ir) is False
    model, errors, _ = validate_canonical_ir(ir)
    assert model is None
    assert "canonical_ir_formula_not_clean" in errors


def test_formula_with_display_dollars_is_invalid():
    from semantic_output import canonical_ir_formulas_are_clean, validate_canonical_ir

    ir = _canonical_ir(output_state="$$x=1$$")

    assert canonical_ir_formulas_are_clean(ir) is False
    model, errors, _ = validate_canonical_ir(ir)
    assert model is None
    assert "canonical_ir_formula_not_clean" in errors


def test_formula_with_control_escape_is_invalid():
    from semantic_output import canonical_ir_formulas_are_clean, validate_canonical_ir

    ir = _canonical_ir(output_state=r"x=1\u0000A4")

    assert canonical_ir_formulas_are_clean(ir) is False
    model, errors, _ = validate_canonical_ir(ir)
    assert model is None
    assert "canonical_ir_formula_not_clean" in errors


def test_formula_with_fragmented_to_infty_is_invalid():
    from semantic_output import canonical_ir_formulas_are_clean, validate_canonical_ir

    ir = _canonical_ir(output_state=r"x\to$\infty$")

    assert canonical_ir_formulas_are_clean(ir) is False
    model, errors, _ = validate_canonical_ir(ir)
    assert model is None
    assert "canonical_ir_formula_not_clean" in errors


def test_formula_with_inline_aligned_delimiters_is_invalid():
    from semantic_output import canonical_ir_formulas_are_clean, validate_canonical_ir

    ir = _canonical_ir(output_state=r"$\begin{aligned}$x&=1$\end{aligned}$")

    assert canonical_ir_formulas_are_clean(ir) is False
    model, errors, _ = validate_canonical_ir(ir)
    assert model is None
    assert "canonical_ir_formula_not_clean" in errors


def test_step_without_derivation_depth_is_invalid():
    from semantic_output import canonical_ir_has_derivation_depth, validate_canonical_ir

    ir = _canonical_ir(justification="最终答案")

    assert canonical_ir_has_derivation_depth(ir) is False
    model, errors, _ = validate_canonical_ir(ir)
    assert model is None
    assert "canonical_ir_missing_derivation_depth" in errors


def test_canonical_ir_covers_explicit_subparts_only():
    from semantic_output import canonical_ir_covers_subparts

    ir = _canonical_ir()
    matrix_question = r"设矩阵 A=\begin{pmatrix}1&2\\3&4\end{pmatrix}，求行列式。"
    multipart_question = "第(1)问 求极限。\n第(2)问 证明单调性。"

    assert canonical_ir_covers_subparts(ir, matrix_question) is True
    assert canonical_ir_covers_subparts(ir, multipart_question) is False

