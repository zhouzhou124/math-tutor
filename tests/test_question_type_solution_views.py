import inspect


def test_choice_view_from_answer_card():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {"standard_answer": "B"},
        "选择题",
        {"correct_option": "B", "student_answer": "A", "is_correct": False},
    )
    assert view["question_type"] == "选择题"
    assert view["answer_card"]["correct_answer"] == "B"
    assert view["answer_card"]["student_answer"] == "A"
    assert view["final_answer"] == {}


def test_choice_view_option_analysis_section():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {"choice_solution": {"option_analysis": {"A": "错误", "B": "正确"}}},
        "选择题",
        {"correct_option": "B"},
    )
    sections = view["sections"]
    assert any(s["kind"] == "option_analysis" for s in sections)


def test_fill_view_answer_and_confidence():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {"standard_answer": r"\frac{1}{2}"},
        "填空题",
        {"student_answer": "0.5", "correct_answer": r"\frac{1}{2}", "is_correct": True, "quick_compare_confidence": 0.98},
    )
    assert view["question_type"] == "填空题"
    assert view["answer_card"]["is_equivalent"] is True
    assert view["answer_card"]["confidence"] == 0.98
    assert not view.get("final_answer") or not view["final_answer"].get("content")


def test_fill_long_answer_gets_legacy_structured_steps():
    from services.grading_adapter import build_standard_solution_view, ensure_structured_for_display

    long_text = (
        "步骤1：识别类型\n\n"
        "识别方程类型并化为可分离变量形式。\n\n"
        "步骤2：分离变量\n\n"
        "将 $y$ 与 $x$ 项分列等式两边。\n\n"
        "步骤3：积分\n\n"
        "两边积分得到通解。"
    )
    sol = ensure_structured_for_display({"standard_answer": long_text}, "填空题")
    steps = (sol.get("_structured") or {}).get("steps") or []
    assert len(steps) >= 2
    view = build_standard_solution_view(sol, "填空题", {"correct_answer": r"\frac{1}{x}"})
    assert len(view["sections"]) >= 2
    assert view["sections"][0].get("title", "").startswith("步骤")


def test_choice_long_text_not_truncated_to_option_only():
    from services.grading_adapter import ensure_structured_for_display

    text = (
        "步骤1：核心思路\n\n"
        "本题考查概率密度归一化，先写出积分方程。\n\n"
        "步骤2：计算\n\n"
        "代入条件求得参数。\n\n"
        "故选 B"
    )
    sol = ensure_structured_for_display({"standard_answer": text, "choice_solution": {"correct_option": "B"}}, "选择题")
    steps = (sol.get("_structured") or {}).get("steps") or []
    assert len(steps) >= 2


def test_fill_view_uses_step_sections_like_problem():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {
            "_structured": {
                "steps": [{
                    "label": "步骤1：求值",
                    "goal": "代入条件",
                    "reason": "由题意列方程。",
                    "blocks": [{"type": "text", "content": "令 $u=x$。"}],
                    "conclusion": r"\(y=1\)",
                }],
            },
        },
        "填空题",
        {"correct_answer": "1"},
    )
    sec = view["sections"][0]
    assert sec.get("goal") == "代入条件"
    assert sec.get("reason") == "由题意列方程。"
    assert sec["title"].startswith("步骤1")


def test_problem_view_from_structured_steps():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {"_structured": {"steps": [{"label": "步骤1：确定方法", "blocks": [{"type": "text", "content": "令 $u=x$。"}]}]}},
        "解答题",
        {"total": 8, "total_score": 10},
    )
    assert view["question_type"] == "解答题"
    assert view["sections"][0]["title"].startswith("步骤1")
    # P55: mixed Chinese/formula is split into separate blocks
    all_content = " ".join(b.get("content", "") for b in view["sections"][0]["blocks"])
    assert "\\(" in all_content or "$" in all_content


def test_proof_view_has_goal_and_conclusion():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "由条件可得结论。"}, "证明题")
    assert view["question_type"] == "证明题"
    assert view["sections"][0]["kind"] == "proof_goal"
    assert view["answer_card"]["proof_status"] == "证明过程"


def test_no_source_branch_in_view_builder():
    from services.grading_adapter import build_standard_solution_view

    source = inspect.getsource(build_standard_solution_view)
    assert "real_exam" not in source
    assert "mock" not in source
    real = build_standard_solution_view({"standard_answer": "B", "source": "real_exam"}, "选择题", {"correct_option": "B"})
    mock = build_standard_solution_view({"standard_answer": "B", "source": "mock"}, "选择题", {"correct_option": "B"})
    assert real["question_type"] == mock["question_type"]
    assert real["answer_card"].keys() == mock["answer_card"].keys()


def test_text_block_does_not_contain_raw_begin():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {"standard_answer": r"$$\begin{aligned}x&=1\end{aligned}$$"},
        "解答题",
    )
    for section in view["sections"]:
        for block in section["blocks"]:
            if block["type"] == "text":
                assert r"\begin" not in block["content"]


def test_latex_display_strips_outer_dollars():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": r"$$x=1$$"}, "填空题")
    assert view["answer_card"]["correct_answer"] == "x=1"


def test_old_structured_and_legacy_fallback_displayable():
    from services.grading_adapter import build_standard_solution_view

    structured = {"steps": [{"label": "步骤1", "blocks": [{"type": "latex", "display": "block", "content": "x=1"}]}]}
    view = build_standard_solution_view({"_structured": structured}, "解答题")
    assert view["sections"][0]["blocks"][0]["type"] == "text"

    fallback = build_standard_solution_view({"standard_answer": "步骤1：计算。最终答案为 1。"}, "解答题")
    assert fallback["sections"]


def test_final_answer_only_once_in_view():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "最终答案为 1。"}, "解答题")
    assert isinstance(view["final_answer"], dict)
    assert "final_answer" in view


def test_equation_group_renderer(monkeypatch):
    from renderers.components import grading_result as mod

    rendered = []
    monkeypatch.setattr(mod.st, "latex", lambda text: rendered.append(text))
    mod.render_equation_group({"type": "equation_group", "items": ["x=1", "y=2"]})
    assert rendered and r"\begin{aligned}" in rendered[0]


def test_derivation_chain_renderer(monkeypatch):
    from renderers.components import grading_result as mod

    rendered = []
    monkeypatch.setattr(mod.st, "latex", lambda text: rendered.append(text))
    mod.render_derivation_chain({"type": "derivation_chain", "items": ["x+1", "2"]})
    assert rendered and "&= 2" in rendered[0]


def test_cases_renderer(monkeypatch):
    from renderers.components import grading_result as mod

    rendered = []
    monkeypatch.setattr(mod.st, "latex", lambda text: rendered.append(text))
    mod.render_cases_block({"type": "cases", "lhs": "f(x)", "rows": [{"expr": "1", "condition": "x>0"}]})
    assert rendered and r"\begin{cases}" in rendered[0]


def test_renderer_uses_view_not_source_branch():
    from renderers.components.grading_result import render_standard_solution_view

    source = inspect.getsource(render_standard_solution_view)
    assert "real_exam" not in source
    assert "mock" not in source


def test_renderer_does_not_read_raw_standard_answer_fields():
    from renderers.components.grading_result import render_standard_solution_view

    source = inspect.getsource(render_standard_solution_view)
    assert "standard_answer" not in source
    assert "_structured" not in source


def test_choice_missing_detail_has_friendly_fallback():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({}, "选择题", {"correct_option": "B"})
    assert view["answer_card"]["correct_answer"] == "B"
    assert view["final_answer"] == {}


def test_existing_standard_solution_view_passthrough():
    from services.grading_adapter import build_standard_solution_view

    existing = {
        "question_type": "填空题",
        "answer_card": {"correct_answer": "1"},
        "sections": [],
        "final_answer": {"type": "latex_display", "content": "1"},
        "meta": {},
    }
    normalized = build_standard_solution_view({"standard_solution_view": existing}, "填空题")
    assert normalized["answer_card"]["correct_answer"] == "1"


def test_render_solution_block_text_uses_safe_renderer(monkeypatch):
    from renderers.components import grading_result as mod

    rendered = []
    monkeypatch.setattr(mod.st, "markdown", lambda text, **kw: rendered.append(text))
    mod.render_solution_block({"type": "text", "content": "由 \\(x=1\\) 可得。"})
    assert rendered and "x=1" in rendered[0]


def test_mobile_layout_class_still_exists():
    from renderers.components.grading_result import _GRADING_MOBILE_CSS

    assert ".standard-solution-card" in _GRADING_MOBILE_CSS
    assert ".grading-math-scroll" in _GRADING_MOBILE_CSS


def test_ai_grading_result_shape_unaffected():
    from services.grading_adapter import normalize_grading_result

    gr = normalize_grading_result({"total": 5, "is_correct": True, "correct_option": "B"})
    assert gr["total"] == 5
    assert gr["is_correct"] is True
    assert gr["correct_option"] == "B"
