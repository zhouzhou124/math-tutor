"""latex_engine — 数学表达式重写引擎

═══════════════════════════════════════════════════════════════
核心架构
═══════════════════════════════════════════════════════════════

  Expression Representation
      ↓
  Canonicalization
      ↓
  Rewrite Rules
      ↓
  Rewrite Strategy
      ↓
  Optimization Search

═══════════════════════════════════════════════════════════════
模块结构
═══════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────┐
  │ 核心类型                                               │
  │  - canonical_ir: Expr, Op, ExprCache                  │
  │  - ast: ASTNode (原始AST)                              │
  ├─────────────────────────────────────────────────────────┤
  │ 解析器                                                 │
  │  - parser: Pratt parser                                │
  │  - parselet: Parselet 模式匹配                         │
  ├─────────────────────────────────────────────────────────┤
  │ 重写规则                                               │
  │  - rewrite: Pattern matching + RewriteEngine          │
  │  - rewrite_ir: IR 级别重写规则                         │
  ├─────────────────────────────────────────────────────────┤
  │ 策略系统（核心）                                       │
  │  - strategy: Strategy combinators                     │
  │  - context: RewriteContext                            │
  │  - trace: RewriteTrace + RewriteStep                  │
  │  - result: RewriteResult                              │
  ├─────────────────────────────────────────────────────────┤
  │ 类型系统                                               │
  │  - types: MathType                                    │
  │  - type_inference: Type inference                     │
  │  - type_environment: Type environment                 │
  └─────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
关键原则
═══════════════════════════════════════════════════════════════

  1. Strategies Are Pure
     策略不修改全局状态，所有状态通过 RewriteContext 传递

  2. Rewrite Is Search
     重写是搜索问题，不是简单的替换

  3. Proof Is Runtime Artifact
     证明在重写时自然产生，不是事后生成

═══════════════════════════════════════════════════════════════
等价性证明流程
═══════════════════════════════════════════════════════════════

  expr --rule--> expr'  ← RewriteStep
         ↓
  RewriteTrace
         ↓
  EqualityProof
         ↓
  Verified Proof

═══════════════════════════════════════════════════════════════
"""

from .canonical_ir import (
    Expr,
    Op,
    ExprCache,
    from_ast,
    to_ast,
)

from .strategy import (
    Strategy,
    BottomUpStrategy,
    TopDownStrategy,
    RepeatStrategy,
    FixpointStrategy,
    ChoiceStrategy,
    SequenceStrategy,
    ConditionalStrategy,
    CostBasedStrategy,
    ParallelStrategy,
    DepthBoundStrategy,
    RuleSet,
    RewriteRule,
    Pattern,
    CostModel,
    DefaultCostModel,
    ProofComplexityModel,
    create_rule,
    make_rule,
)

from .context import (
    RewriteContext,
    ContextMode,
    TerminationReason,
    RewriteStatistics,
    MemoTable,
    CostCache,
    create_trace_context,
    create_proof_context,
    create_debug_context,
    create_optimize_context,
)

from .trace import (
    RewriteStep,
    RewriteLocation,
    RewriteBranch,
    RewriteTrace,
    EqualityProof,
    ProofStep,
)

from .result import (
    RewriteResult,
    SearchResult,
    unchanged_result,
    changed_result,
    failed_result,
)

from .rewrite import (
    RewriteEngine,
    RewriteRule as LegacyRewriteRule,
    RuleParser,
    create_default_rules,
    rewrite,
    parse_rule,
)

from .equality import (
    Equality,
    Theorem,
    Justification,
    JustificationType,
    EquivalenceClass,
    EqualitySystem,
    Proof,
    Substitution,
    EqualityReasoningRule,
    create_additive_identity,
    create_multiplicative_identity,
    create_multiplication_by_zero,
    create_additive_commutativity,
    create_multiplicative_commutativity,
    create_std_axioms,
    create_std_equality_system,
)

__all__ = [
    # Canonical IR
    "Expr",
    "Op",
    "ExprCache",
    "from_ast",
    "to_ast",
    # Strategy
    "Strategy",
    "BottomUpStrategy",
    "TopDownStrategy",
    "RepeatStrategy",
    "FixpointStrategy",
    "ChoiceStrategy",
    "SequenceStrategy",
    "ConditionalStrategy",
    "CostBasedStrategy",
    "ParallelStrategy",
    "DepthBoundStrategy",
    "RuleSet",
    "RewriteRule",
    "Pattern",
    "CostModel",
    "DefaultCostModel",
    "ProofComplexityModel",
    "create_rule",
    "make_rule",
    # Context
    "RewriteContext",
    "ContextMode",
    "TerminationReason",
    "RewriteStatistics",
    "MemoTable",
    "CostCache",
    "create_trace_context",
    "create_proof_context",
    "create_debug_context",
    "create_optimize_context",
    # Trace
    "RewriteStep",
    "RewriteLocation",
    "RewriteBranch",
    "RewriteTrace",
    "EqualityProof",
    "ProofStep",
    # Result
    "RewriteResult",
    "SearchResult",
    "unchanged_result",
    "changed_result",
    "failed_result",
    # Legacy rewrite
    "RewriteEngine",
    "LegacyRewriteRule",
    "RuleParser",
    "create_default_rules",
    "rewrite",
    "parse_rule",
    # Equality Kernel
    "Equality",
    "Theorem",
    "Justification",
    "JustificationType",
    "EquivalenceClass",
    "EqualitySystem",
    "Proof",
    "Substitution",
    "EqualityReasoningRule",
    "create_additive_identity",
    "create_multiplicative_identity",
    "create_multiplication_by_zero",
    "create_additive_commutativity",
    "create_multiplicative_commutativity",
    "create_std_axioms",
    "create_std_equality_system",
]
