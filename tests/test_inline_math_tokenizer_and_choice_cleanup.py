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

    def write(self, text, *args, **kwargs):
        self.calls.append(("write", str(text), kwargs))

    def code(self, text, *args, **kwargs):
        self.calls.append(("code", str(text), kwargs))

    def container(self, *args, **kwargs):
        return _Ctx()


def test_exp_distribution_wrapped_inline():
    from services.grading_adapter import normalize_inline_math_tokens

    assert normalize_inline_math_tokens(r"X\sim \mathrm{Exp}(1)") == r"\(X\sim \mathrm{Exp}(1)\)"


def test_subscript_variable_wrapped_inline():
    from services.grading_adapter import normalize_inline_math_tokens

    assert normalize_inline_math_tokens("令 X_i 表示样本") == r"令 \(X_i\) 表示样本"


def test_event_with_escaped_braces_wrapped_inline():
    from services.grading_adapter import normalize_inline_math_tokens

    assert normalize_inline_math_tokens(r"\{X_i \le 1\}") == r"\(\{X_i \le 1\}\)"


def test_dfrac_wrapped_inline():
    from services.grading_adapter import normalize_inline_math_tokens

    assert normalize_inline_math_tokens(r"\dfrac{u_n(1)}{n}") == r"\(\dfrac{u_n(1)}{n}\)"


def test_simple_probability_equation_wrapped_inline():
    from services.grading_adapter import normalize_inline_math_tokens

    assert normalize_inline_math_tokens(r"其中 p=1-e^{-1}") == r"其中 \(p=1-e^{-1}\)"


def test_existing_inline_not_double_wrapped():
    from services.grading_adapter import normalize_inline_math_tokens

    assert normalize_inline_math_tokens(r"已有 \(X_i\)") == r"已有 \(X_i\)"


def test_dollar_inline_converted_to_parentheses():
    from services.grading_adapter import normalize_math_delimiters_in_text

    assert normalize_math_delimiters_in_text("$X_i$") == r"\(X_i\)"


def test_cases_plain_spacing_removed_as_newline():
    from services.grading_adapter import normalize_cases_spacing

    fixed = normalize_cases_spacing(r"\begin{cases}e^{-x}, & x>0, [2mm] 0, & x\le0\end{cases}")
    assert "[2mm]" not in fixed
    assert r"\\" in fixed


def test_cases_escaped_spacing_becomes_newline():
    from services.grading_adapter import normalize_cases_spacing

    fixed = normalize_cases_spacing(r"e^{-x}, & x>0\\[2mm]0, & x\le0")
    assert r"\\[2mm]" not in fixed
    assert r"\\" in fixed


def test_final_answer_dfrac_uses_math_renderer(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    rendered = []
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "_render_text_or_latex", lambda text: rendered.append(text))
    mod.render_final_answer({"type": "text", "content": r"\dfrac{u_n(1)}{n}"})
    assert rendered == [r"$\dfrac{u_n(1)}{n}$"]
    assert not any(c[0] in {"write", "markdown"} and r"\dfrac" in c[1] for c in rec.calls)


def test_render_math_text_does_not_write_raw_dfrac(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    rendered = []
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "_render_text_or_latex", lambda text: rendered.append(text))
    mod.render_math_text(r"\dfrac{u_n(1)}{n}")
    assert rendered == [r"$\dfrac{u_n(1)}{n}$"]
    assert not any(c[0] == "write" and r"\dfrac" in c[1] for c in rec.calls)


def test_render_math_text_demotes_bare_cjk_text_command(monkeypatch):
    from renderers.components import grading_result as mod

    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    mod.render_math_text(
        r"(1) f(t)=1-\mathrm{e}^{t}+t\mathrm{e}^{t}; (2) \text{平均值}2"
    )

    rendered = "\n".join(c[1] for c in rec.calls)
    assert r"\text" not in rendered
    assert "平均值2" in rendered
    assert rendered.count("$") == 2


def test_choice_legacy_text_splits_sections():
    from services.grading_adapter import build_standard_solution_view

    legacy = (
        r"本题为选择题。步骤1：X\sim \mathrm{Exp}(1)。"
        r"步骤2：实际计算结果为 p=1-e^{-1}。"
        "选项中若出现 A：正确 B：错误。故选 A。"
    )
    view = build_standard_solution_view({"standard_answer": legacy}, "选择题", {"correct_option": "A"})
    titles = [section["title"] for section in view["sections"]]
    assert "核心依据" in titles
    assert "关键计算" in titles
    assert "选项分析" in titles


def test_choice_answer_card_not_repeated_in_final_answer():
    from services.grading_adapter import build_standard_solution_view

    view = build_standard_solution_view({"standard_answer": "故选 A。"}, "选择题", {"correct_option": "A"})
    assert view["answer_card"]["correct_answer"] == "A"
    assert view["final_answer"] == {}


def test_screenshot_style_final_answer_no_raw_dfrac_after_normalize():
    from services.grading_adapter import normalize_standard_solution_view

    view = normalize_standard_solution_view({
        "question_type": "填空题",
        "answer_card": {"correct_answer": r"\dfrac{u_n(1)}{n}"},
        "sections": [],
        "final_answer": {"type": "text", "content": r"\dfrac{u_n(1)}{n}"},
    })
    assert view["final_answer"]["content"] == r"\(\dfrac{u_n(1)}{n}\)"


def test_p52_math_normalization_still_available():
    from services.grading_adapter import normalize_differential_tokens

    assert normalize_differential_tokens("dxdy") == r"dx\,dy"
