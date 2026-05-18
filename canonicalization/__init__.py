"""
canonicalization — 数学状态规范化系统

统一导出所有规范化组件。

Diff Pipeline:
  LaTeX → AST → Canonical Form → Semantic Diff → DiffResult → Renderer → HTML

IR Pipeline:
  LLM → Math AST → Canonical IR → Constraint Engine → Diagnosis → ViewModel → Renderer → UI
"""

from canonicalization.expression import (
    CanonicalForm,
    parse_to_sympy,
    canonicalize_expression,
    canonicalize_expression_multi,
    expressions_are_equivalent,
)
from canonicalization.constraints import (
    canonicalize_constraint,
    canonicalize_constraint_set,
    constraints_are_equivalent,
)
from canonicalization.fingerprint import (
    expression_fingerprint,
    expression_fingerprint_multi,
    constraint_fingerprint,
    state_fingerprint,
    states_are_equivalent,
)
from canonicalization.state import (
    CanonicalizationResult,
    canonicalize_state,
)
from canonicalization.semantic_diff import (
    DiffType,
    DiffLevel,
    ExpressionDiff,
    StepDiff,
    SemanticDiffResult,
    diff_expressions,
    diff_reasoning_steps,
    diff_to_viewmodel_data,
)
from canonicalization.ir import (
    StepStatus,
    StepType,
    ErrorCategory,
    FormulaNode,
    Constraint,
    ErrorTrace,
    ReasoningStep,
    ProofTree,
    IRBuilder,
    create_proof_tree_from_steps,
    compare_proof_trees,
)
