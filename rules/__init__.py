"""
rules — 数学规则声明语言 (Rule DSL)

统一导出所有规则相关组件。
"""

from rules.dsl import (
    Condition,
    ConditionKind,
    RuleContext,
    ProofObligation,
    ObligationSeverity,
    RuleApplicationResult,
    Rule,
)
from rules.engine import (
    EngineResult,
    RuleEngine,
)
from rules.registry import (
    ALGEBRA_RULES,
    CALCULUS_RULES,
    EQUATION_RULES,
    LINEAR_ALGEBRA_RULES,
    LOGIC_RULES,
    ALL_RULES,
    RULES,
    build_registry,
)
