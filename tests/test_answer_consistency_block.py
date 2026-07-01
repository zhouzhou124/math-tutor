from types import SimpleNamespace


class _Status:
    def __init__(self):
        self.messages = []

    def write(self, message):
        self.messages.append(str(message))


def test_inconsistent_generated_answer_is_blocked_not_cached(monkeypatch):
    import choice_explainer
    import views.grading_page as page

    cached = []

    monkeypatch.setattr(
        choice_explainer,
        "generate_detailed_answer",
        lambda **kwargs: "## 标准答案\n$y=2$",
    )
    monkeypatch.setattr(page, "_verify_answer_consistency", lambda expanded, known: False)
    monkeypatch.setattr(page, "_cache_detailed_answer", lambda *args, **kwargs: cached.append(args))

    status = _Status()
    result = page._build_standard_solution(
        question="设 $y(1)=1$，求 $y$。",
        ocr_data={"question_type": "解答题"},
        selected_q={
            "question": "设 $y(1)=1$，求 $y$。",
            "question_type": "解答题",
            "standard_answer": "$y=1$",
            "score": 10,
        },
        client=SimpleNamespace(),
        status=status,
        force_expansion=True,
        _state={},
        model="test-model",
    )

    assert result["success"] is True
    assert result["standard_answer"] == "$y=1$"
    assert result["standard_solution_status"] == "ready"
    assert result["_answer_consistency_blocked"] is True
    assert result["_ai_consistency_warning"] is True
    assert cached == []
    assert any("不一致" in message for message in status.messages)


def test_choice_letter_consistency_detects_conflicting_conclusion():
    import views.grading_page as page

    assert page._verify_answer_consistency("最终结论：故选 D。", "正确选项: A. 2/e") is False
    assert page._verify_answer_consistency("最终结论：故选 D。", "正确选项: D. 3/e^2") is True


def test_choice_generator_inconsistent_answer_is_blocked(monkeypatch):
    import choice_explainer
    import views.grading_page as page

    def _fake_choice_solution(*args, **kwargs):
        return {
            "success": True,
            "standard_answer": "关键计算：P(X\\ge EX)=3/e^2。最终结论：故选 D。",
            "choice_solution": {
                "core_reason": "计算概率后匹配选项。",
                "conclusion": "故选 D",
                "answer": "D",
            },
            "steps": [],
        }

    monkeypatch.setattr(choice_explainer, "generate_choice_standard_solution", _fake_choice_solution)

    status = _Status()
    result = page._build_standard_solution(
        question="求概率。",
        ocr_data={"question_type": "选择题"},
        selected_q={
            "question": "求概率。",
            "question_type": "选择题",
            "correct_option": "A",
            "options": {"A": "2/e", "D": "3/e^2"},
            "standard_answer": "A",
            "score": 5,
        },
        client=SimpleNamespace(),
        status=status,
        force_expansion=True,
        _state={},
        model="test-model",
    )

    assert result["success"] is True
    assert result["standard_answer"] == "A"
    assert result["standard_solution_status"] == "ready"
    assert result["_answer_consistency_blocked"] is True
    assert "3/e^2" in result["_debug_generated_answer_preview"]
    assert any("不一致" in message for message in status.messages)
