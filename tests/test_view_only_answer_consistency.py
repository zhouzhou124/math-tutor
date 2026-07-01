from types import SimpleNamespace


class _Status:
    def __init__(self):
        self.messages = []

    def write(self, message):
        self.messages.append(str(message))


def test_view_only_with_solution_steps_does_not_force_expansion(monkeypatch):
    import views.grading_page as page

    captured = {}

    def _spy_build(*args, force_expansion=False, **kwargs):
        captured["force_expansion"] = force_expansion
        return {
            "success": True,
            "standard_answer": r"$-\frac23$",
            "steps": ["步骤1：通分"],
            "total_score": 5,
            "standard_solution_status": "ready",
        }

    monkeypatch.setattr(page, "_build_standard_solution", _spy_build)
    monkeypatch.setattr(page, "_standard_solution_status", lambda *args, **kwargs: "ready")
    monkeypatch.setattr(page, "_standard_solution_wait_state", lambda *args, **kwargs: {
        "standard_solution_status": "ready",
    })

    page._execute_grading_process(
        question=r"$$\lim_{x\to0}(\cdots)=____$$",
        student_ans="",
        ocr_data={"question_type": "填空题"},
        selected_q={
            "question_id": "26李擂八套卷-卷三-011",
            "question_type": "填空题",
            "standard_answer": r"$-\frac23$",
            "solution_steps": [
                "首先将原式通分。",
                "利用泰勒展开。",
            ],
            "score": 5,
        },
        client=SimpleNamespace(),
        _state={},
    )

    assert captured.get("force_expansion") is False


def test_verify_answer_consistency_accepts_frac_brace_form():
    import views.grading_page as page

    expanded = "## 标准答案\n-\\frac{2}{3}"
    assert page._verify_answer_consistency(expanded, r"$-\frac23$") is True


def test_verify_answer_consistency_accepts_slash_form():
    import views.grading_page as page

    expanded = "## 标准答案\n-2/3"
    assert page._verify_answer_consistency(expanded, r"$-\frac23$") is True


def test_inconsistent_payload_preserves_bank_steps(monkeypatch):
    import choice_explainer
    import views.grading_page as page

    monkeypatch.setattr(
        choice_explainer,
        "generate_detailed_answer",
        lambda **kwargs: "## 标准答案\n$y=2$",
    )
    monkeypatch.setattr(page, "_verify_answer_consistency", lambda expanded, known: False)

    selected_q = {
        "question": "设 $y(1)=1$，求 $y$。",
        "question_type": "填空题",
        "standard_answer": r"$-\frac23$",
        "solution_steps": ["步骤1：代入条件。", "步骤2：解出结果。"],
        "score": 5,
    }
    status = _Status()
    result = page._build_standard_solution(
        question=selected_q["question"],
        ocr_data={"question_type": "填空题"},
        selected_q=selected_q,
        client=SimpleNamespace(),
        status=status,
        force_expansion=True,
        _state={},
        model="test-model",
    )

    assert result["_answer_consistency_blocked"] is True
    assert result["standard_answer"] == r"$-\frac23$"
    assert len(result["steps"]) == 2
    assert result["standard_solution_status"] == "ready"


def test_inconsistent_payload_with_bank_steps_builds_view_sections():
    import views.grading_page as page
    from services.grading_adapter import build_standard_solution_view

    payload = page._inconsistent_solution_payload(
        known_answer=r"$-\frac23$",
        generated_text="## 标准答案\n-2/3",
        score=5,
        selected_q={
            "standard_answer": r"$-\frac23$",
            "solution_steps": ["步骤1：通分。", "步骤2：泰勒展开。"],
            "question_type": "填空题",
        },
    )
    view = build_standard_solution_view(payload, "填空题")
    assert len(view.get("sections") or []) >= 1


def test_inconsistent_payload_without_bank_fallback_stays_empty_failed():
    import views.grading_page as page

    result = page._inconsistent_solution_payload(
        known_answer=r"$-\frac23$",
        generated_text="## 标准答案\n-2/3",
        score=5,
        selected_q={
            "question_type": "填空题",
            "standard_answer": "",
            "solution_steps": [],
        },
    )

    assert result["success"] is False
    assert result["standard_answer"] == ""
    assert result["steps"] == []
    assert result["standard_solution_status"] == "failed"
