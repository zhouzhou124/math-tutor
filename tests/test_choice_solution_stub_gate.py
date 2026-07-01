def test_is_choice_solution_stub_detects_option_only_line():
    from services.grading_adapter import is_choice_solution_stub

    assert is_choice_solution_stub(
        {"standard_answer": "正确选项: D. $1 - \\cos \\sqrt{x}$", "question_type": "选择题"},
        {"question_type": "选择题", "correct_option": "D"},
    )


def test_is_choice_solution_stub_rejects_full_steps():
    from services.grading_adapter import is_choice_solution_stub

    text = "## 步骤1：思路\n求极限。\n\n## 步骤3：选项分析\nA: 错\n\n## 最终答案\n故选 D。"
    assert not is_choice_solution_stub(
        {"standard_answer": text, "question_type": "选择题"},
        {"question_type": "选择题"},
    )
