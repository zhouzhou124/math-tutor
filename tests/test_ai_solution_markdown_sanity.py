"""AI standard-answer markdown sanitation regressions."""


def test_bad_inline_aligned_is_repaired_for_ai_solution():
    from services.solution_legacy_repair import repair_legacy_solution_text

    raw = (
        "步骤1：计算极限。\n"
        r"$\begin{aligned}$"
        "\n"
        r"a_n&=\frac{1}{n}\\"
        "\n"
        r"\lim_{n\to$\infty$}a_n&=0"
        "\n"
        r"$\end{aligned}$"
        "\n最终答案：故极限为 $0$。"
    )

    fixed = repair_legacy_solution_text(raw)

    assert r"$\begin{aligned}$" not in fixed
    assert r"$\end{aligned}$" not in fixed
    assert fixed.count("$$") == 2
    assert r"\to\infty" in fixed
    assert "$$$" not in fixed


def test_control_chars_and_meta_sections_are_removed():
    from services.solution_legacy_repair import repair_legacy_solution_text

    raw = (
        "## 题目重述\n求二重积分。\n"
        "步骤1：由积分区域可知\x00A2，应先确定边界。\n"
        "## 关键知识点\n二重积分换元。\n"
        "## 易错提示\n注意符号。\n"
        "步骤2：根据区域条件继续计算，最终答案为 $1$。\\u0000A4"
    )

    fixed = repair_legacy_solution_text(raw)

    assert "\x00" not in fixed
    assert "\\u0000A4" not in fixed
    assert "题目重述" not in fixed
    assert "关键知识点" not in fixed
    assert "易错提示" not in fixed
    assert "步骤1" in fixed
    assert "步骤2" in fixed


def test_fragmented_inline_relation_math_is_repaired():
    from services.solution_legacy_repair import sanitize_ai_solution_markdown

    fixed = sanitize_ai_solution_markdown(
        r"区域满足 x $\geq$ 0，参数满足 \theta $\in$ (0,\pi)，面积为 \pi $\cdot$ r^2。"
    )

    assert r"x $\geq$ 0" not in fixed
    assert r"\theta $\in$" not in fixed
    assert r"\pi $\cdot$" not in fixed
    assert r"$x \geq 0" in fixed
    assert r"$\theta \in (0,\pi)" in fixed
    assert r"$\pi \cdot r^2" in fixed


def test_unpaired_display_math_is_not_renderable():
    from services.solution_quality import solution_is_renderable

    sol = {"standard_answer": "步骤1：建立公式。\n$$\nx=1\n最终答案：$x=1$。"}

    assert solution_is_renderable(sol) is False


def test_display_math_with_chinese_or_nested_inline_math_is_not_renderable():
    from services.solution_quality import solution_is_renderable

    chinese = {"standard_answer": "$$\n由题意可得 x=1\n$$\n最终答案：$x=1$。"}
    nested = {"standard_answer": "$$\nx=$1$\n$$\n最终答案：$x=1$。"}

    assert solution_is_renderable(chinese) is False
    assert solution_is_renderable(nested) is False

