"""Subpart detection should only use explicit question subpart markers."""


def _detailed_matrix_solution():
    return {
        "standard_answer": (
            "步骤1：根据行列式展开，先把矩阵结构转化为递推式 $D_n=2aD_{n-1}-a^2D_{n-2}$。"
            "步骤2：利用特征方程和初值化简，得到 $D_n=(n+1)a^n$。"
            "因此，最终答案为 $D_n=(n+1)a^n$。"
        ),
        "_structured": {
            "steps": [
                {
                    "label": "步骤1：建立递推",
                    "blocks": [
                        {"type": "text", "content": "根据第一行展开行列式，把矩阵中的数字 1、2 只作为矩阵元素处理，不作为小问编号。"},
                        {"type": "latex", "content": r"D_n=2aD_{n-1}-a^2D_{n-2}"},
                    ],
                },
                {
                    "label": "步骤2：求解递推",
                    "blocks": [
                        {"type": "text", "content": "利用特征方程和初值条件完整求解递推式，因此得到行列式表达式。"},
                        {"type": "latex", "content": r"D_n=(n+1)a^n"},
                    ],
                },
            ],
            "final_answer": {"type": "latex", "content": r"D_n=(n+1)a^n"},
        },
    }


def test_matrix_numbers_do_not_trigger_missing_subpart_derivations():
    from services.solution_quality import solution_quality_report

    question = {
        "question_type": "解答题",
        "question": r"设矩阵 A=\begin{pmatrix}1&2\\3&4\end{pmatrix}，求行列式。",
    }

    report = solution_quality_report(_detailed_matrix_solution(), question)

    assert not any(i.startswith("missing_subpart_derivations") for i in report["issues"])
    assert not any(i.startswith("missing_subparts") for i in report["issues"])


def test_real_multi_subpart_question_still_detects_missing_part():
    from services.solution_quality import solution_quality_report

    question = {
        "question_type": "解答题",
        "question": "第(1)问 求极限。\n第(2)问 证明单调性。",
    }
    solution = {
        "standard_answer": (
            "第(1)问 步骤1：由等价无穷小替换得到关键变形 $\\sin x\\sim x$。"
            "步骤2：继续化简可得第一问极限为 $1$。因此，最终答案为 $1$。"
        )
    }

    report = solution_quality_report(solution, question)

    assert "missing_subparts:2" in report["issues"]
