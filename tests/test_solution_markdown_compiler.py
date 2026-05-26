"""P29-3: CanonicalIR Markdown compiler tests."""

import re

import pytest


def _single_step_ir():
    return {
        "proof_trace": {
            "steps": [{
                "id": "s1",
                "label": "求解方程",
                "operation": "solve",
                "input_state": "x+1=2",
                "output_state": "x=1",
                "justification": "根据等式性质两边同减 1，得到方程的解。",
            }],
            "final_answer": "x=1",
        }
    }


def _compile(ir):
    from services.solution_markdown_compiler import compile_canonical_ir_to_markdown

    return compile_canonical_ir_to_markdown(ir)


def test_single_step_ir_compiles_to_stable_markdown():
    md = _compile(_single_step_ir())

    assert md.startswith("## 标准解答")
    assert "### 步骤1：求解方程" in md
    assert "根据等式性质" in md
    assert "$$\nx+1=2 \\Rightarrow x=1\n$$" in md
    assert "## 最终答案" in md


def test_multi_step_ir_compiles():
    ir = {
        "proof_trace": {
            "steps": [
                {
                    "id": "s1", "label": "建立方程", "operation": "transform",
                    "output_state": "x+1=2", "justification": "根据题意建立等式关系。",
                },
                {
                    "id": "s2", "label": "求解方程", "operation": "solve",
                    "input_state": "x+1=2", "output_state": "x=1",
                    "justification": "利用等式性质化简，得到最终结果。",
                },
            ],
            "final_answer": "x=1",
        }
    }

    md = _compile(ir)

    assert md.count("### 步骤") == 2
    assert "$$\nx+1=2\n$$" in md
    assert "$$\nx+1=2 \\Rightarrow x=1\n$$" in md


def test_multi_subpart_ir_compiles_by_subpart():
    ir = {
        "subparts": [
            {
                "label": "(1)",
                "title": "求极限",
                "steps": [{
                    "label": "等价无穷小替换",
                    "body": "先使用等价无穷小把分式化简。",
                    "display_formulas": [r"\lim_{x\to 0}\frac{\sin x}{x}=1"],
                    "explanation": "根据基本极限可得第一问结论。",
                }],
                "final_answer": {"latex": "1"},
            },
            {
                "label": "(2)",
                "title": "证明单调性",
                "steps": [{
                    "label": "求导判断",
                    "body": "对函数求导并判断导数符号。",
                    "display_formulas": ["f'(x)>0"],
                    "conclusion": "因此函数单调递增。",
                }],
                "final_answer": {"text": "函数单调递增。"},
            },
        ]
    }

    md = _compile(ir)

    assert "## 第 (1) 问：求极限" in md
    assert "## 第 (2) 问：证明单调性" in md
    assert md.count("## 最终答案") == 2


def test_display_formula_is_wrapped_by_compiler():
    ir = {"steps": [{"label": "写出公式", "display_formulas": ["a=b"], "explanation": "根据定义写出公式。"}]}

    md = _compile(ir)

    assert "$$\na=b\n$$" in md


def test_inline_formula_is_wrapped_by_compiler():
    ir = {"steps": [{"label": "说明条件", "inline_formulas": ["x>0"], "explanation": "根据定义需要满足该条件。"}]}

    md = _compile(ir)

    assert "$x>0$" in md
    assert "$$\nx>0\n$$" not in md


def test_formula_with_inline_dollar_is_rejected():
    from services.solution_markdown_compiler import (
        SolutionMarkdownCompileError,
        compile_canonical_ir_to_markdown,
    )

    ir = {"steps": [{"label": "坏公式", "formula": "$x=1$", "explanation": "根据等式性质。"}]}

    with pytest.raises(SolutionMarkdownCompileError):
        compile_canonical_ir_to_markdown(ir)


def test_formula_with_display_dollars_is_rejected():
    from services.solution_markdown_compiler import (
        SolutionMarkdownCompileError,
        compile_canonical_ir_to_markdown,
    )

    ir = {"steps": [{"label": "坏公式", "formula": "$$x=1$$", "explanation": "根据等式性质。"}]}

    with pytest.raises(SolutionMarkdownCompileError):
        compile_canonical_ir_to_markdown(ir)


def test_compiler_never_produces_triple_dollars():
    md = _compile(_single_step_ir())

    assert "$$$" not in md


def test_compiler_does_not_put_chinese_inside_display_math():
    md = _compile(_single_step_ir())

    for match in re.finditer(r"\$\$([\s\S]*?)\$\$", md):
        assert not re.search(r"[\u4e00-\u9fff]", match.group(1))


def test_limit_ir_markdown_is_renderable():
    from services.solution_quality import solution_is_renderable

    ir = {
        "proof_trace": {
            "steps": [
                {
                    "id": "s1", "label": "确定主项", "operation": "transform",
                    "output_state": r"\frac{1}{x}\to 0",
                    "justification": "根据无穷大量倒数为无穷小，先确定极限主项。",
                },
                {
                    "id": "s2", "label": "计算极限", "operation": "evaluate",
                    "input_state": r"\lim_{x\to\infty}\frac{1}{x}",
                    "output_state": "0",
                    "justification": "利用极限运算法则计算，得到最终极限值。",
                },
            ],
            "final_answer": "0",
        }
    }
    md = _compile(ir)

    assert solution_is_renderable({"standard_answer": md}) is True


def test_double_integral_ir_markdown_is_renderable():
    from services.solution_quality import solution_is_renderable

    ir = {
        "proof_trace": {
            "steps": [
                {
                    "id": "s1", "label": "确定积分区域", "operation": "classify",
                    "output_state": r"D=\{(x,y)\mid 0\le x\le 1,\ 0\le y\le x\}",
                    "justification": "根据题设边界先写出二重积分区域。",
                },
                {
                    "id": "s2", "label": "计算二重积分", "operation": "integrate",
                    "input_state": r"\int_0^1\int_0^x (x+y)\,dy\,dx",
                    "output_state": r"\frac{1}{2}",
                    "justification": "先对内层变量积分，再对外层变量积分得到结果。",
                },
            ],
            "final_answer": r"\frac{1}{2}",
        }
    }
    md = _compile(ir)

    assert solution_is_renderable({"standard_answer": md}) is True


def test_matrix_ir_markdown_does_not_trigger_missing_subparts():
    from services.solution_quality import solution_quality_report

    ir = {
        "proof_trace": {
            "steps": [
                {
                    "id": "s1", "label": "建立递推", "operation": "transform",
                    "output_state": r"D_n=2aD_{n-1}-a^2D_{n-2}",
                    "justification": "根据第一行展开行列式并整理，得到递推关系。",
                },
                {
                    "id": "s2", "label": "解递推", "operation": "solve",
                    "input_state": r"D_n=2aD_{n-1}-a^2D_{n-2}",
                    "output_state": r"D_n=(n+1)a^n",
                    "justification": "利用特征方程和初值条件求解递推式。",
                },
            ],
            "final_answer": r"D_n=(n+1)a^n",
        }
    }
    question = {
        "question_type": "解答题",
        "question": r"设矩阵 A=\begin{pmatrix}1&2\\3&4\end{pmatrix}，求行列式。",
    }
    md = _compile(ir)
    report = solution_quality_report({"standard_answer": md}, question)

    assert not any(issue.startswith("missing_subparts") for issue in report["issues"])
