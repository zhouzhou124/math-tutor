"""P24: strict quality gate for AI-generated standard solutions."""


def test_quality_report_accepts_detailed_solution():
    from services.solution_quality import solution_quality_report

    sol = {
        "standard_answer": (
            "步骤1：由题设 $x+1=2$ 可知，只需求出未知量 $x$。"
            "步骤2：两边同时减去 $1$，得到 $x=1$，再代回原式有 $1+1=2$。"
            "因此，最终答案为 $x=1$。"
        )
    }

    report = solution_quality_report(sol, {"question_type": "解答题"})
    assert report["ok"] is True
    assert report["issues"] == []


def test_quality_report_rejects_broken_latex():
    from services.solution_quality import solution_quality_report

    sol = {
        "standard_answer": (
            "步骤1：先写出分式 $\\frac{1}$。"
            "步骤2：继续化简得到结论。"
            "因此，最终答案为 $1$。"
        )
    }

    report = solution_quality_report(sol, {"question_type": "解答题"})
    assert report["ok"] is False
    assert "not_renderable" in report["issues"]


def test_choice_solution_must_analyze_options():
    from services.solution_quality import solution_quality_report

    q = {
        "question_type": "选择题",
        "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
        "correct_option": "B",
    }
    weak = {
        "standard_answer": (
            "步骤1：直接计算可得结果为 $1$。"
            "步骤2：所以本题选择正确答案。"
            "因此，正确选项是 B。"
        )
    }
    strong = {
        "standard_answer": (
            "步骤1：检验选项 A，代入后不满足题设条件。"
            "步骤2：检验选项 B，代入后满足全部条件。"
            "步骤3：选项 C 与 D 代入后均与条件矛盾。"
            "因此，正确选项是 B。"
        )
    }

    assert "choice_options_not_analyzed" in solution_quality_report(weak, q)["issues"]
    assert solution_quality_report(strong, q)["ok"] is True


def test_multipart_solution_must_cover_each_subpart():
    from services.solution_quality import solution_quality_report

    q = {"question_type": "解答题", "question": "（1）求极限；（2）证明单调性。"}
    sol = {
        "standard_answer": (
            "（1）步骤1：先代入等价无穷小进行化简。"
            "步骤2：计算得到第一问的极限为 $1$。"
            "因此，最终答案为 $1$。"
        )
    }

    report = solution_quality_report(sol, q)
    assert report["ok"] is False
    assert "missing_subparts:2" in report["issues"]


def test_detailed_answer_guard_rejects_metadata_shell():
    from choice_explainer import _is_answer_good_enough

    text = (
        "## 标准答案\n$x=1$\n\n"
        "## 关键知识点\n- 方程求解\n- 代入验证\n\n"
        "## 易错提示\n- 注意符号\n" + "补充说明" * 80
    )

    assert _is_answer_good_enough(text) is False


def test_detailed_answer_guard_accepts_steps_and_final_answer():
    from choice_explainer import _is_answer_good_enough

    text = (
        "## 步骤1：分析题意\n由题设可得 $x+1=2$，目标是求 $x$。\n\n"
        "## 步骤2：求解并验证\n两边减去 $1$ 得 $x=1$，代回原式成立。\n\n"
        "## 最终答案\n故最终答案为 $x=1$。"
    )

    assert _is_answer_good_enough(text) is True
