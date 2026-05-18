"""
runtime — 可执行数学状态运行时

═══════════════════════════════════════════════════════════════
架构概览
═══════════════════════════════════════════════════════════════

  WorldState    — 统一数学世界状态 (替代 RuntimeState)
  RuntimeState  — 可执行数学状态 (兼容层)
  RuntimeExecutor — 状态执行引擎 (Op → State → State)
  Transaction   — 事务与回滚 (试探性推导 + 分类讨论)
  ExecutionHistory — 执行历史记录 (可追溯 + 可回放 + 可诊断)
  RuntimeContext — 运行时上下文 (统一入口)

  使用方式:
    from runtime import WorldState, Assumption, Goal
    ws = WorldState.empty()
    ws = ws.with_assumption(Assumption("x > 0", kind=AssumptionKind.GIVEN))
    ws = ws.with_goal(Goal("证明 sqrt(x^2) = x", kind=GoalKind.PROVE))

  向后兼容:
    from runtime import RuntimeContext
    ctx = RuntimeContext()
    ctx.initialize(question_id="2024-数一-001")
    result = ctx.execute(Op.DIFFERENTIATE, "x^2 + 1", "x")

═══════════════════════════════════════════════════════════════
"""

from runtime.world_state import (
    WorldState,
    Assumption,
    AssumptionKind,
    Goal,
    GoalStatus,
    GoalKind,
    MathFact,
    ProofObligation,
    ObligationStatus,
    DomainEntry,
    DomainKind,
    DomainRegistry,
    VariableBinding,
    VariableScope,
    ProofContext,
    ProofStrategy,
    ProofPhase,
    StateMetadata,
    ExecutionEvent,
    VerificationResult,
)
from facts.fact import (
    Fact,
    FactType,
    FactOrigin,
    FactEdge,
    FactEdgeType,
)
from facts.graph import (
    FactGraph,
    FactQuery,
    FactQueryResult,
    ConsumeProduceRecord,
)
from facts.consumer import (
    FactConsumer,
    FactProducer,
    ConsumeSpec,
    ProduceSpec,
    OperationFactFlow,
    ConsumeResult,
    FlowResult,
    BUILTIN_FLOWS,
)
from runtime.state import (
    RuntimeState,
    RuntimeMetadata,
)
from runtime.executor import (
    RuntimeExecutor,
    ExecutionResult,
    ExecutionStatus,
)
from runtime.transaction import (
    Transaction,
    TransactionManager,
    TransactionStatus,
    TransactionLog,
)
from runtime.history import (
    ExecutionHistory,
    HistoryEntry,
    HistoryDiff,
    StateSnapshot,
    EntryKind,
)
from runtime.context import (
    RuntimeContext,
    DiagnosisReport,
)
