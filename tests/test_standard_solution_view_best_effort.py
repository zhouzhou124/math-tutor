class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Recorder:
    def __init__(self):
        self.calls = []
        self.session_state = {}

    def markdown(self, text, *args, **kwargs):
        self.calls.append(("markdown", str(text), kwargs))

    def success(self, text, *args, **kwargs):
        self.calls.append(("success", str(text), kwargs))

    def warning(self, text, *args, **kwargs):
        self.calls.append(("warning", str(text), kwargs))

    def info(self, text, *args, **kwargs):
        self.calls.append(("info", str(text), kwargs))

    def caption(self, text, *args, **kwargs):
        self.calls.append(("caption", str(text), kwargs))

    def code(self, text, *args, **kwargs):
        self.calls.append(("code", str(text), kwargs))

    def write(self, text, *args, **kwargs):
        self.calls.append(("write", str(text), kwargs))

    def latex(self, text, *args, **kwargs):
        self.calls.append(("latex", str(text), kwargs))

    def container(self, *args, **kwargs):
        return _Ctx()

    def expander(self, *args, **kwargs):
        return _Ctx()


def _patch_streamlit(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    return mod, rec


def test_latex_display_failure_keeps_section_title_and_code(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    import renderers.math_render_policy as policy

    monkeypatch.setattr(policy, "render_grading_latex", lambda text: (_ for _ in ()).throw(RuntimeError("boom")))
    ok = mod.render_standard_solution_view({
        "question_type": "解答题",
        "answer_card": {},
        "sections": [{"title": "步骤1", "blocks": [{"type": "latex_display", "content": r"\bad"}]}],
        "final_answer": {},
    })
    assert ok is True
    assert any(c[0] == "markdown" and "步骤1" in c[1] for c in rec.calls)
    assert any(c[0] == "code" and r"\bad" in c[1] for c in rec.calls)


def test_equation_group_failure_shows_items(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(rec, "latex", lambda text, *a, **k: (_ for _ in ()).throw(RuntimeError("bad latex")))
    assert mod.render_solution_block({"type": "equation_group", "items": ["x=1", "y=2"]})
    assert [c[1] for c in rec.calls if c[0] == "code"] == ["x=1", "y=2"]


def test_derivation_chain_failure_shows_items(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(rec, "latex", lambda text, *a, **k: (_ for _ in ()).throw(RuntimeError("bad latex")))
    assert mod.render_solution_block({"type": "derivation_chain", "items": ["x+1", "2"]})
    assert [c[1] for c in rec.calls if c[0] == "code"] == ["x+1", "2"]


def test_cases_failure_shows_lhs_and_rows(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(rec, "latex", lambda text, *a, **k: (_ for _ in ()).throw(RuntimeError("bad latex")))
    assert mod.render_solution_block({"type": "cases", "lhs": "f(x)", "rows": [{"expr": "1", "condition": "x>0"}]})
    codes = [c[1] for c in rec.calls if c[0] == "code"]
    assert "f(x)" in codes
    assert any("x>0" in c for c in codes)


def test_failed_block_does_not_hide_later_block(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    import renderers.math_render_policy as policy

    monkeypatch.setattr(policy, "render_grading_latex", lambda text: (_ for _ in ()).throw(RuntimeError("boom")))
    mod.render_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "步骤1", "blocks": [
            {"type": "latex_display", "content": r"\bad"},
            {"type": "text", "content": "后续文字"},
        ]}],
        "final_answer": {},
    })
    assert any(c[0] in {"write", "markdown"} and "后续文字" in c[1] for c in rec.calls)


def test_failed_section_does_not_hide_later_section(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(mod, "render_solution_section", lambda section, **kw: (_ for _ in ()).throw(RuntimeError("section")) if section["title"] == "坏步骤" else True)
    mod.render_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "坏步骤", "blocks": []}, {"title": "好步骤", "blocks": []}],
        "final_answer": {},
    })
    assert any(c[0] == "markdown" and "坏步骤" in c[1] for c in rec.calls)


def test_answer_card_failure_does_not_hide_sections(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(mod, "_render_answer_card", lambda view, **kw: (_ for _ in ()).throw(RuntimeError("card")))
    mod.render_standard_solution_view({
        "question_type": "选择题",
        "answer_card": {"correct_answer": "B"},
        "sections": [{"title": "核心依据", "blocks": [{"type": "text", "content": "理由"}]}],
        "final_answer": {},
    })
    assert any(c[0] == "success" and "B" in c[1] for c in rec.calls)
    assert any(c[0] == "markdown" and "核心依据" in c[1] for c in rec.calls)


def test_final_answer_failure_does_not_hide_sections(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(mod, "render_final_answer", lambda final_answer, **kw: (_ for _ in ()).throw(RuntimeError("final")))
    mod.render_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "步骤", "blocks": [{"type": "text", "content": "过程"}]}],
        "final_answer": {"type": "text", "content": "结论"},
    })
    assert any(c[0] == "markdown" and "步骤" in c[1] for c in rec.calls)
    assert any(c[0] in {"write", "code", "markdown"} and "结论" in c[1] for c in rec.calls)


def test_render_standard_solution_does_not_fallback_to_raw_renderer(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(mod, "render_standard_solution_view", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    mod.render_standard_solution({"standard_answer": "LLM_RAW_SHOULD_NOT_RENDER"}, expanded=True)
    rendered = "\n".join(c[1] for c in rec.calls)
    assert "LLM_RAW_SHOULD_NOT_RENDER" not in rendered
    assert "标准解答展示异常，已隐藏" not in rendered


def test_choice_answer_only_view_when_no_sections():
    from services.grading_adapter import build_answer_only_view

    view = build_answer_only_view({}, "选择题", {"correct_option": "B"})
    assert view["answer_card"]["correct_answer"] == "B"
    assert "详细解析暂未生成" in view["sections"][0]["blocks"][0]["content"]


def test_fill_answer_only_view_when_no_sections():
    from services.grading_adapter import build_answer_only_view

    view = build_answer_only_view({}, "填空题", {"correct_answer": r"\frac{1}{2}"})
    assert view["answer_card"]["correct_answer"] == r"\frac{1}{2}"
    assert view["sections"]


def test_correct_answer_prevents_empty_data_message(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    mod.render_standard_solution({}, expanded=True, grading_result={"question_type": "填空题", "correct_answer": "1"})
    rendered = "\n".join(c[1] for c in rec.calls)
    assert "暂无标准解法数据" not in rendered


def test_failed_empty_standard_solution_shows_generation_error(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)

    mod.render_standard_solution(
        {
            "standard_answer": "",
            "steps": [],
            "standard_solution_status": "failed",
            "standard_solution_error": "quality gate rejected empty solution",
        },
        expanded=True,
        grading_result={"question_type": "解答题", "standard_solution_status": "failed"},
    )

    rendered = "\n".join(c[1] for c in rec.calls)
    assert "暂无标准解法数据" not in rendered
    assert "quality gate rejected empty solution" in rendered
    assert any(c[0] == "warning" for c in rec.calls)


def test_failed_unrendered_standard_solution_does_not_show_empty_data(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    monkeypatch.setattr(mod, "render_standard_solution_view", lambda *a, **k: False)

    mod.render_standard_solution(
        {
            "standard_answer": "bad structured payload",
            "standard_solution_status": "failed",
            "standard_solution_error": "render gate failed",
        },
        expanded=True,
        grading_result={"question_type": "解答题"},
    )

    rendered = "\n".join(c[1] for c in rec.calls)
    assert "暂无标准解法数据" not in rendered
    assert "render gate failed" in rendered
    assert any(c[0] == "warning" for c in rec.calls)


def test_missing_standard_solution_shows_not_generated_state(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)

    mod.render_standard_solution(
        {"standard_answer": "", "steps": [], "standard_solution_status": "missing"},
        expanded=True,
        grading_result={"question_type": "解答题"},
    )

    rendered = "\n".join(c[1] for c in rec.calls)
    assert "暂无标准解法数据" not in rendered
    assert "标准解答尚未生成" in rendered


def test_extract_final_answer_rejects_long_solution():
    from services.grading_adapter import _extract_final_answer

    result = _extract_final_answer({"standard_answer": "步骤1：计算。" * 80}, "解答题")
    assert result == {}


def test_extract_final_answer_from_marker():
    from services.grading_adapter import _extract_final_answer

    result = _extract_final_answer({"standard_answer": "计算过程略。最终答案：x=1。"}, "解答题")
    assert result["content"] == "x=1"


def test_extract_final_answer_from_choice_marker():
    from services.grading_adapter import _extract_final_answer

    result = _extract_final_answer({"standard_answer": "比较可知，故选 B。"}, "选择题")
    assert result["content"] == "B"


def test_final_answer_in_conclusion_is_not_duplicated():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "解答题",
        "sections": [{"title": "步骤", "blocks": [], "conclusion": "最终答案：x=1"}],
        "final_answer": {"type": "text", "content": "x=1"},
    })
    assert view["final_answer"] == {}


def test_proof_neutral_without_explicit_conclusion():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "由条件推出所需关系。"}, "证明题")
    assert view["answer_card"]["proof_status"] == "证明过程"
    assert view["final_answer"]["content"] == "结论见上述证明过程。"


def test_proof_explicit_done_can_show_established():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "综上，原命题成立，得证。"}, "证明题")
    assert view["answer_card"]["proof_status"] == "命题成立"


def test_text_block_backslash_n_becomes_newline(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    mod.render_solution_block({"type": "text", "content": "第一行\\n第二行"})
    rendered = "\n".join(c[1] for c in rec.calls)
    assert "第一行\n第二行" in rendered


def test_raw_latex_text_block_uses_code(monkeypatch):
    mod, rec = _patch_streamlit(monkeypatch)
    rendered = []
    monkeypatch.setattr(mod, "_render_text_or_latex", lambda text: rendered.append(text))
    mod.render_solution_block({"type": "text", "content": r"\frac{1}{2}"})
    assert rendered == [r"$\frac{1}{2}$"]
