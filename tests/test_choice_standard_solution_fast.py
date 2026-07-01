"""Fast choice standard-solution path — quality gate and timer helpers."""


def test_choice_display_quality_accepts_option_analysis_payload():
    from services.solution_quality import solution_quality_report_choice_display

    solution = {
        "standard_answer": (
            "## 步骤1：解题思路\n先对题目中的函数求导并分析单调性，再把临界点与四个选项逐一比较，确定只有 B 满足条件。\n\n"
            "## 步骤3：选项分析\nA: 错\nB: 对\n\n"
            "## 最终答案\n故选 B。"
        ),
        "choice_solution": {
            "thought_process": "先对题目中的函数求导并分析单调性，再把临界点与四个选项逐一比较，确定只有 B 满足条件。",
            "option_analysis": {"A": "错", "B": "对", "C": "错", "D": "错"},
            "answer": "B",
        },
    }
    report = solution_quality_report_choice_display(
        solution,
        {"question_type": "选择题", "correct_option": "B", "options": {"A": "1", "B": "2"}},
    )
    assert report["ok"] is True


def test_choice_display_quality_rejects_option_only_payload():
    from services.solution_quality import solution_quality_report_choice_display

    solution = {
        "standard_answer": (
            "## 步骤3：选项分析\n"
            "A: 错误：$I_1$\n"
            "B: 正确：$I_2$\n"
            "C: 错误：$I_3$\n"
            "D: 错误：$I_4$\n\n"
            "## 最终答案\n故选 B。"
        ),
        "choice_solution": {
            "thought_process": "",
            "option_analysis": {"A": "$I_1$", "B": "$I_2$", "C": "$I_3$", "D": "$I_4$"},
            "answer": "B",
        },
    }

    report = solution_quality_report_choice_display(
        solution,
        {"question_type": "选择题", "correct_option": "B", "options": {"A": "I_1", "B": "I_2"}},
    )

    assert report["ok"] is False
    assert "missing_core_reasoning" in report["issues"]


def test_choice_cached_option_only_answer_still_needs_expansion():
    from views.grading_page import _standard_answer_needs_expansion

    answer = (
        "## 步骤3：选项分析\n"
        "A: 错误：$I_1$\n"
        "B: 正确：$I_2$\n"
        "C: 错误：$I_3$\n"
        "D: 错误：$I_4$\n\n"
        "## 最终答案\n故选 B。"
    )

    assert _standard_answer_needs_expansion(
        answer,
        [],
        "选择题",
        selected_q={"question_type": "选择题", "correct_option": "B"},
    ) is True


def test_choice_explanation_to_markdown_has_steps_and_final():
    from choice_explainer import _choice_explanation_to_markdown

    text = _choice_explanation_to_markdown(
        {
            "thought_process": "先求导再比较端点。",
            "option_analysis": {"A": "错", "B": "对", "C": "错", "D": "错"},
        },
        "B",
    )
    assert "步骤1" in text
    assert "故选 B" in text
    assert "选项分析" in text


def test_choice_standard_solution_falls_back_to_detailed_answer(monkeypatch):
    import choice_explainer

    def fake_choice_explanation(*args, **kwargs):
        return {
            "thought_process": "",
            "option_analysis": {"A": "$I_1$", "B": "$I_2$", "C": "$I_3$", "D": "$I_4$"},
            "knowledge_points": [],
            "common_traps": [],
            "fast_method": "",
        }

    def fake_detailed_answer(**kwargs):
        return (
            "## 步骤1：求导分析\n"
            "由题设函数求导，得到关键方程并分析零点个数。\n\n"
            "## 步骤2：比较选项\n"
            "将计算结果与 A/B/C/D 逐项比较，只有 B 与结果一致。\n\n"
            "## 最终答案\n故选 B。"
        )

    monkeypatch.setattr(choice_explainer, "generate_choice_explanation", fake_choice_explanation)
    monkeypatch.setattr(choice_explainer, "generate_detailed_answer", fake_detailed_answer)

    solution = choice_explainer.generate_choice_standard_solution(
        "设函数 f(x)，求零点个数",
        {
            "question_type": "选择题",
            "question": "设函数 f(x)，求零点个数",
            "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
            "correct_option": "B",
        },
        object(),
        model="test-model",
    )

    assert "求导分析" in solution["standard_answer"]
    assert "比较选项" in solution["standard_answer"]
    assert solution["choice_solution"]["thought_process"].startswith("## 步骤1")
