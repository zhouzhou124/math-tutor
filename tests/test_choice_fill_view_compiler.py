class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Recorder:
    def __init__(self):
        self.calls = []

    def markdown(self, text, *args, **kwargs):
        self.calls.append(("markdown", str(text), kwargs))

    def warning(self, text, *args, **kwargs):
        self.calls.append(("warning", str(text), kwargs))

    def code(self, text, *args, **kwargs):
        self.calls.append(("code", str(text), kwargs))

    def latex(self, text, *args, **kwargs):
        self.calls.append(("latex", str(text), kwargs))

    def caption(self, text, *args, **kwargs):
        self.calls.append(("caption", str(text), kwargs))

    def container(self, *args, **kwargs):
        return _Ctx()


def _titles(view):
    return [section["title"] for section in view["sections"]]


def test_choice_core_reason_is_consumed():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"choice_solution": {"core_reason": "比较单调性。", "answer": "B"}}, "选择题")
    assert "核心依据" in _titles(view)


def test_choice_calculation_steps_is_consumed():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"choice_solution": {"calculation_steps": ["计算 p=1-e^{-1}", "代入选项"], "answer": "B"}}, "选择题")
    section = next(s for s in view["sections"] if s["title"] == "关键计算")
    assert len(section["blocks"]) >= 2


def test_choice_option_analysis_is_consumed():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {"choice_solution": {"option_analysis": {"A": "不符合", "B": "符合"}, "answer": "B"}},
        "选择题",
    )
    section = next(s for s in view["sections"] if s["kind"] == "option_analysis")
    text = " ".join(b["content"] for b in section["blocks"])
    assert "A" in text and "B" in text


def test_choice_conclusion_not_repeated_as_final_answer():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"choice_solution": {"conclusion": "故选 B", "answer": "B"}}, "选择题")
    assert view["answer_card"]["correct_answer"] == "B"
    assert view["final_answer"] == {}


def test_choice_type_fields_compile_to_structured_contract():
    from services.grading_adapter import normalize_standard_solution

    solution = normalize_standard_solution({
        "question_type": "选择题",
        "choice_solution": {
            "answer": "B",
            "core_reason": "先判断函数单调性。",
            "calculation_steps": ["计算导数。"],
            "option_analysis": {"A": "不符合", "B": "符合"},
            "conclusion": "故选 B",
        },
    })
    structured = solution["_structured"]
    assert structured["final_answer"]["content"] == "故选 B"
    labels = [step["label"] for step in structured["steps"]]
    assert {"核心依据", "关键计算", "选项分析", "最终结论"} <= set(labels)


def test_choice_structured_steps_not_truncated():
    from services.grading_adapter import build_standard_solution_view

    steps = [
        {"label": f"步骤{i}", "blocks": [{"type": "text", "content": f"内容{i}"}]}
        for i in range(1, 5)
    ]
    view = build_standard_solution_view({"_structured": {"steps": steps}, "answer": "C"}, "选择题")
    assert len(view["sections"]) >= 4


def test_choice_structured_option_step_kept():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {"_structured": {"steps": [
            {"label": "步骤1", "blocks": [{"type": "text", "content": "先计算"}]},
            {"label": "步骤2", "blocks": [{"type": "text", "content": "继续计算"}]},
            {"label": "步骤3：选项分析", "blocks": [{"type": "text", "content": "A 错误，B 正确"}]},
        ]}, "answer": "B"},
        "选择题",
    )
    assert any(s["kind"] == "option_analysis" for s in view["sections"])


def test_choice_legacy_markdown_step_one_splits():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "## 步骤一\n分析题意。\n## 选项分析\nA 错误，B 正确。\n因此答案为 B"}, "选择题", {"correct_option": "B"})
    assert len(view["sections"]) >= 3


def test_choice_legacy_chinese_number_heading_splits():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "一、核心思路：先判断。二、关键计算：得 p=1-e^{-1}。三、选项分析：A项不对，B项符合。因此答案为 B"}, "选择题")
    assert {"核心依据", "关键计算", "选项分析"} <= set(_titles(view))


def test_choice_legacy_option_sentence_splits_options():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "核心思路：比较。选项分析：A项不对，B项符合。因此答案为 B"}, "选择题")
    section = next(s for s in view["sections"] if s["kind"] == "option_analysis")
    assert len(section["blocks"]) >= 2


def test_choice_legacy_answer_phrase_detected():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "先分析。因此答案为 B"}, "选择题")
    assert view["answer_card"]["correct_answer"] == "B"


def test_choice_legacy_markdown_list_options():
    from services.grading_adapter import build_standard_solution_view

    text = "核心思路：排除。\n选项分析：\nA. 错误\nB. 正确\nC. 错误\nD. 错误\n故选 B"
    view = build_standard_solution_view({"standard_answer": text}, "选择题")
    section = next(s for s in view["sections"] if s["kind"] == "option_analysis")
    assert len(section["blocks"]) >= 4


def test_choice_does_not_degrade_to_single_large_core_section():
    from services.grading_adapter import build_standard_solution_view

    text = "## 步骤一\n思路。\n二、关键计算：p=1-e^{-1}。\n三、选项分析：A错，B对。故选 B"
    view = build_standard_solution_view({"standard_answer": text}, "选择题")
    assert len(view["sections"]) > 1


def test_choice_inline_bracket_labels_split_into_sections():
    from services.grading_adapter import build_standard_solution_view

    text = (
        "【解题思路】判断两个命题的真伪。命题①由洛必达法则可得。"
        "【选项分析】A：①正确，②不正确，故 A 正确。B：不符合。"
        "【知识点】- 洛必达法则的适用条件\n- 构造反例的方法"
        "【常见误区】误认为极限存在必推出导数极限存在。"
        "【秒杀技巧】遇到导函数极限与函数极限关系，优先构造振荡反例。"
    )

    view = build_standard_solution_view({"standard_answer": text}, "选择题", {"correct_option": "A"})
    titles = _titles(view)
    assert {"核心依据", "选项分析", "知识点", "常见误区", "秒杀技巧"} <= set(titles)

    core = next(s for s in view["sections"] if s["title"] == "核心依据")
    core_text = " ".join(b.get("content", "") for b in core["blocks"])
    assert "知识点" not in core_text
    assert "常见误区" not in core_text


def test_choice_structured_inline_bracket_labels_split_into_sections():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{
                        "type": "text",
                        "content": (
                            "【解题思路】先求导判断。"
                            "【知识点】导数与单调性。"
                            "【选项分析】A 错误，B 正确。"
                        ),
                    }],
                }]
            },
            "answer": "B",
        },
        "选择题",
        {"correct_option": "B"},
    )

    assert {"核心依据", "知识点", "选项分析"} <= set(_titles(view))


def test_choice_view_blocks_cached_solution_with_conflicting_final_choice():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {
            "standard_answer": "关键计算：P(X\\ge EX)=3/e^2。最终结论：故选 D。",
            "answer": "D",
        },
        "选择题",
        {"correct_option": "A"},
    )

    assert view["answer_card"]["correct_answer"] == "A"
    assert _titles(view) == ["答案一致性提示"]
    text = " ".join(
        block.get("content", "")
        for block in view["sections"][0]["blocks"]
    )
    assert "D" in text and "A" in text and "不一致" in text


def test_fill_correct_answer_from_grading_result_priority():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"correct_answer": "2"}, "填空题", {"correct_answer": "1"})
    assert view["answer_card"]["correct_answer"] == "1"


def test_fill_missing_correct_answer_does_not_use_long_standard_answer():
    from services.grading_adapter import build_standard_solution_view

    text = "步骤1：先分析。" * 20
    view = build_standard_solution_view({"standard_answer": text}, "填空题")
    assert view["answer_card"]["correct_answer"] == ""


def test_fill_extracts_short_final_answer_marker():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "计算可得。最终答案：\\frac{1}{2}。"}, "填空题")
    assert view["answer_card"]["correct_answer"] == r"\frac{1}{2}"


def test_fill_rejects_truncated_function_answer():
    from services.grading_adapter import build_standard_solution_view, extract_fill_final_answer

    assert extract_fill_final_answer({"standard_answer": "最终答案：f(x)="}) is None
    view = build_standard_solution_view({"standard_answer": "最终答案：f(x)="}, "填空题")
    assert view["answer_card"]["correct_answer"] == ""


def test_fill_rejects_multistep_as_answer():
    from services.grading_adapter import extract_fill_final_answer

    assert extract_fill_final_answer({"standard_answer": "步骤1：计算。步骤2：继续。最终答案：" + "很长解释" * 30}) is None


def test_fill_legacy_sections_split_conditions_calculation_form_final():
    from services.grading_adapter import build_standard_solution_view

    text = "由题意设 X_i。计算得 p=1-e^{-1}。答案可写为 \\frac12。最终答案：\\frac{1}{2}。"
    view = build_standard_solution_view({"standard_answer": text}, "填空题")
    assert {"关键条件", "关键计算", "答案形式"} <= set(_titles(view))


def test_fill_answer_form_note_section():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"answer": "1/2", "answer_form_note": "可写为 0.5。"}, "填空题")
    assert any(s["title"] == "答案形式" for s in view["sections"])


def test_fill_type_fields_compile_to_structured_contract():
    from services.grading_adapter import normalize_standard_solution

    solution = normalize_standard_solution({
        "question_type": "填空题",
        "answer": r"\frac{1}{2}",
        "key_conditions": "由题意设参数。",
        "calculation_steps": ["代入计算。"],
        "answer_form_note": "也可写成 0.5。",
    })
    structured = solution["_structured"]
    assert structured["final_answer"]["content"] == r"\frac{1}{2}"
    labels = [step["label"] for step in structured["steps"]]
    assert {"关键条件", "关键计算", "答案形式"} <= set(labels)


def test_fill_inline_bracket_labels_split_into_sections():
    from services.grading_adapter import build_standard_solution_view

    text = (
        "【解题思路】先把原式化为关于函数零点的问题。"
        "【关键计算】计算端点符号并利用单调性。"
        "【知识点】连续函数零点定理；导数与单调性。"
        "【巩固建议】复习含参方程根个数的判断。"
        "【最终答案】1"
    )

    view = build_standard_solution_view({"standard_answer": text}, "填空题", {"correct_answer": "1"})
    titles = _titles(view)

    assert {"解题思路", "关键计算", "知识点", "巩固建议", "最终填空"} <= set(titles)
    thought = next(section for section in view["sections"] if section["title"] == "解题思路")
    thought_text = " ".join(block.get("content", "") for block in thought["blocks"])
    assert "知识点" not in thought_text
    assert "巩固建议" not in thought_text


def test_fill_structured_inline_bracket_labels_split_into_sections():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view(
        {
            "_structured": {
                "steps": [{
                    "label": "步骤1",
                    "blocks": [{
                        "type": "text",
                        "content": (
                            "【解题思路】构造辅助函数。"
                            "【知识点】零点定理。"
                            "【最终答案】2"
                        ),
                    }],
                }]
            },
            "answer": "2",
        },
        "填空题",
        {"correct_answer": "2"},
    )

    assert {"解题思路", "知识点", "最终填空"} <= set(_titles(view))


def test_problem_structured_goal_reason_conclusion_without_blocks_renders():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({
        "_structured": {
            "steps": [{
                "label": "步骤1：建立方程",
                "goal": "步骤1：确定未知量。",
                "reason": "根据题设关系列式。",
                "conclusion": "得到方程。",
            }]
        }
    }, "解答题")
    section = view["sections"][0]
    assert section["goal"] == "确定未知量。"
    assert section["reason"] == "根据题设关系列式。"
    assert section["conclusion"] == "得到方程。"
    text = " ".join(
        block["content"]
        for block in section["blocks"]
        if block["type"] == "text"
    )
    assert "得到方程" in text
    assert "推导目标" not in text
    assert "推导理由" not in text


def test_final_conclusion_section_hides_goal_and_reason():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({
        "_structured": {
            "steps": [{
                "label": "最终结论",
                "kind": "conclusion",
                "goal": "确定根个数并逐项分析选项",
                "reason": "由连续函数的零点定理及严格单调性",
                "conclusion": "故选 B",
            }]
        }
    }, "选择题", {"correct_option": "B"})

    section = next(sec for sec in view["sections"] if sec["title"] == "最终结论")
    assert section["goal"] == ""
    assert section["reason"] == ""
    text = " ".join(
        block["content"]
        for block in section["blocks"]
        if block["type"] == "text"
    )
    assert "推导目标" not in text
    assert "推导理由" not in text
    assert "故选 B" in text


def test_fill_answer_card_short_formula_inline(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    rendered = []
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "render_math_text", lambda text: rendered.append(text) or True)
    mod._render_answer_card({"question_type": "填空题", "answer_card": {"correct_answer": r"\frac{1}{2}"}})
    assert rendered == [r"\frac{1}{2}"]


def test_fill_answer_card_long_formula_display(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    rendered = []
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "render_solution_block", lambda block: rendered.append(block) or True)
    mod._render_answer_card({"question_type": "填空题", "answer_card": {"correct_answer": r"\begin{aligned}x&=1\\y&=2\end{aligned}"}})
    assert rendered and rendered[0]["type"] == "latex_display"


def test_fill_answer_card_mixed_text_uses_math_text(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    rendered = []
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "render_math_text", lambda text: rendered.append(text) or True)
    mod._render_answer_card({"question_type": "填空题", "answer_card": {"correct_answer": "任意常数 C"}})
    assert rendered == ["任意常数 C"]


def test_fill_unrecognized_answer_warns_but_sections_remain(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    mod._render_answer_card({"question_type": "填空题", "answer_card": {"correct_answer": ""}})
    assert any("暂未识别" in c[1] for c in rec.calls if c[0] == "warning")


def test_fill_no_source_branch_in_builder():
    import inspect
    from services.grading_adapter import build_fill_solution_view

    source = inspect.getsource(build_fill_solution_view)
    assert "real_exam" not in source
    assert "mock" not in source
