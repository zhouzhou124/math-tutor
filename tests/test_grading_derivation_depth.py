"""AI grading standard-solution derivation depth regressions."""


class _FakeContainer:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_structured_step_body_markdown_is_rendered_first(monkeypatch):
    import streamlit as st
    import renderers.math_render_policy as policy
    from latex_utils import render_structured_safe

    rendered: list[str] = []
    monkeypatch.setattr(st, "container", lambda **kw: _FakeContainer())
    monkeypatch.setattr(st, "markdown", lambda *args, **kw: None)
    monkeypatch.setattr(policy, "render_grading_latex", lambda text: rendered.append(text))

    render_structured_safe({
        "steps": [{
            "label": "步骤1：求解递推",
            "operation": "solve",
            "body_markdown": "推导动机：解递推式。关键变形：$D_n=2aD_{n-1}-a^2D_{n-2}$。由特征方程和初值可得结论。",
            "blocks": [{"type": "text", "content": "summary only"}],
        }],
        "final_answer": {"type": "latex", "content": "D_n=(n+1)a^n"},
    })

    assert rendered
    assert "推导动机" in rendered[0]
    assert "summary only" not in "\n".join(rendered)


def test_conclusion_only_structured_solution_is_incomplete():
    from services.solution_quality import solution_is_complete

    sol = {
        "standard_answer": "最终答案为 $D_n=(n+1)a^n$。",
        "_structured": {
            "steps": [{
                "label": "步骤1：得到结论",
                "operation": "conclude",
                "blocks": [{"type": "latex", "content": "D_n=(n+1)a^n"}],
            }],
            "final_answer": {"type": "latex", "content": "D_n=(n+1)a^n"},
        },
    }

    assert solution_is_complete(sol, {"question_type": "解答题"}) is False


def test_multipart_requires_derivation_for_each_subpart():
    from services.solution_quality import solution_quality_report

    q = {"question_type": "解答题", "question": "第(1)问 证明行列式公式。\n第(2)问 求唯一解。"}
    sol = {
        "standard_answer": "（1）证明。 （2）结论。",
        "_structured": {
            "steps": [
                {
                    "label": "第(1)问：证明行列式公式",
                    "body_markdown": "第(1)问推导动机：建立递推式。关键变形为 $D_n=2aD_{n-1}-a^2D_{n-2}$，根据特征方程和初值推出 $D_n=(n+1)a^n$，因此完成证明。",
                    "blocks": [],
                },
                {
                    "label": "第(2)问：求唯一解",
                    "blocks": [{"type": "latex", "content": "x_1=\\frac{1}{(n+1)a}"}],
                },
            ],
            "final_answer": {"type": "latex", "content": "x_1=\\frac{1}{(n+1)a}"},
        },
    }

    report = solution_quality_report(sol, q)
    assert report["complete"] is False
    assert "missing_subpart_derivations:2" in report["issues"]


def test_standard_solution_not_ready_when_only_final_formula():
    from services.grading_adapter import normalize_solution_for_render

    sol = normalize_solution_for_render({
        "standard_answer": "最终答案为 $x=1$。",
        "_structured": {
            "steps": [{
                "label": "步骤1：结论",
                "blocks": [{"type": "latex", "content": "x=1"}],
            }],
            "final_answer": {"type": "latex", "content": "x=1"},
        },
    })

    assert sol["standard_solution_status"] == "incomplete"


def test_blocks_with_text_and_formula_count_as_detailed_without_body_markdown():
    from services.solution_quality import solution_quality_report

    sol = {
        "standard_answer": (
            "步骤1：根据递推关系先写出特征方程并代入初值。"
            "步骤2：由特征方程求得通项，因此最终答案为 $D_n=(n+1)a^n$。"
        ),
        "_structured": {
            "steps": [
                {
                    "label": "步骤1：建立递推关系",
                    "blocks": [
                        {"type": "text", "content": "根据第一行展开行列式，并利用分块矩阵行列式性质，得到递推关系。"},
                        {"type": "latex", "content": r"D_n=2aD_{n-1}-a^2D_{n-2}"},
                    ],
                },
                {
                    "label": "步骤2：解递推式",
                    "blocks": [
                        {"type": "text", "content": "利用特征方程和初值条件完整求解递推，因此得到本题行列式公式。"},
                        {"type": "latex", "content": r"D_n=(n+1)a^n"},
                    ],
                },
            ],
            "final_answer": {"type": "latex", "content": r"D_n=(n+1)a^n"},
        },
    }

    report = solution_quality_report(sol, {"question_type": "解答题"})

    assert report["detailed"] is True
    assert "missing_detailed_steps" not in report["issues"]
