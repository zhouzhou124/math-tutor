"""
constraints — 约束传播图系统

统一导出所有约束相关组件。
"""

from constraints.graph import (
    ConstraintRelation,
    ConstraintStatus,
    ConstraintNode,
    ConstraintEdge,
    ConflictReport,
    PropagationResult,
    ConstraintGraph,
)
from constraints.implication_rules import (
    ImplicationRule,
    ConflictRule,
    IMPLICATION_RULES,
    CONFLICT_RULES,
    normalize_constraint,
    check_implication,
    check_equivalence,
    check_conflict,
    apply_rules,
)
from constraints.propagation import propagate_constraints
from constraints.simplifier import simplify_graph
from constraints.conflict_detector import detect_conflicts
