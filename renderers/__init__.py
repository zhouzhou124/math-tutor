"""renderers/ — Question Renderer Layer

语义渲染层，位于 latex_utils（底层）和页面模块（应用层）之间。
每个渲染器理解题目结构，做出正确的渲染决策。

层次:
  UI 层       → st.latex() / st.markdown()
  渲染器层    → render_question_card() / render_choice_options() / ...
  工具层      → latex_utils (safe_latex, split_latex_text, etc.)
  数据层      → QuestionDB / CanonicalTrace
"""

from question_ast import QuestionAST, parse_legacy


def to_ast(q) -> QuestionAST:
    """Convert dict or QuestionAST to QuestionAST. Shared by all renderers."""
    if isinstance(q, QuestionAST):
        return q
    return parse_legacy(q)


from .question_renderer import (
    render_question,            # 推荐入口：题型感知分发
    render_solution_question,   # 解答题
    render_proof_question,      # 证明题
    render_generic_question,    # 通用 fallback
    render_question_list,       # 题目列表
)
from .choice_renderer import render_choice_question
from .fill_renderer import render_fill_question
from .solution_renderer import render_solution_steps
from .proof_renderer import render_proof
from .metadata_renderer import render_question_meta
from .grading_renderer import render_grading_result

from .components import (
    CardOpen, CardClose,
    render_options, render_actions, render_meta_tags, confirm_delete,
)
