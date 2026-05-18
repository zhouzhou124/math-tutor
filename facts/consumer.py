"""
FactConsumer / FactProducer — 操作的事实消耗/生产接口

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  所有推理操作不再直接依赖字符串，而是:

    操作 consume facts → 操作 produce facts

  例如: 积分换元

    consume:
      u = g(x)           (DEFINITION)
      g differentiable   (THEOREM)
      dx relation        (DERIVED)

    produce:
      substitution valid (DERIVED)
      Jacobian introduced (DERIVED)
      back substitution obligation (DERIVED)

  接口设计:
    ConsumeSpec — 声明操作需要什么事实
    ProduceSpec — 声明操作产生什么事实
    FactConsumer — 在 FactGraph 中查找匹配的事实
    FactProducer — 将新事实注入 FactGraph
    OperationFactFlow — 完整的 consume/produce 流

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from facts.fact import Fact, FactType, FactOrigin, FactEdge, FactEdgeType
from facts.graph import FactGraph


@dataclass(frozen=True)
class ConsumeSpec:
    """
    消耗规格 — 声明操作需要什么事实。

    字段:
      fact_type: 需要的事实类型
      expression_pattern: 表达式匹配模式 (子串匹配)
      scope_label: 作用域标签 (分类讨论分支)
      min_confidence: 最低置信度
      required: 是否必须 (缺失则操作失败)
      label: 规格标签 (用于 ProduceSpec 引用)
    """

    fact_type: FactType = FactType.DERIVED
    expression_pattern: str = ""
    scope_label: str = ""
    min_confidence: float = 0.5
    required: bool = True
    label: str = ""

    def find_in(self, graph: FactGraph) -> Optional[Fact]:
        for f in graph.facts:
            if f.fact_type != self.fact_type:
                continue
            if self.expression_pattern and self.expression_pattern not in f.expression:
                continue
            if self.scope_label and f.scope_label != self.scope_label:
                continue
            if f.confidence < self.min_confidence:
                continue
            return f
        return None

    def find_all_in(self, graph: FactGraph) -> tuple[Fact, ...]:
        results = []
        for f in graph.facts:
            if f.fact_type != self.fact_type:
                continue
            if self.expression_pattern and self.expression_pattern not in f.expression:
                continue
            if self.scope_label and f.scope_label != self.scope_label:
                continue
            if f.confidence < self.min_confidence:
                continue
            results.append(f)
        return tuple(results)


@dataclass(frozen=True)
class ProduceSpec:
    """
    生产规格 — 声明操作产生什么事实。

    字段:
      expression: 事实表达式 (支持模板变量 {label})
      fact_type: 事实类型
      confidence: 置信度
      justification: 推导理由
      scope_label: 作用域标签
      from_labels: 依赖哪些 ConsumeSpec 的结果
    """

    expression: str
    fact_type: FactType = FactType.DERIVED
    confidence: float = 1.0
    justification: str = ""
    scope_label: str = ""
    from_labels: tuple[str, ...] = ()

    def build_fact(self, operation: str,
                   dependency_fps: tuple[str, ...] = ()) -> Fact:
        return Fact(
            expression=self.expression,
            fact_type=self.fact_type,
            origin=FactOrigin.DERIVED,
            source_operation=operation,
            dependencies=dependency_fps,
            confidence=self.confidence,
            justification=self.justification,
            produced_by=operation,
            scope_label=self.scope_label,
        )


class FactConsumer:
    """
    事实消耗器 — 在 FactGraph 中查找匹配的事实。

    用法:
      consumer = FactConsumer(specs=[
          ConsumeSpec(FactType.DEFINITION, "u=g(x)", label="substitution"),
          ConsumeSpec(FactType.THEOREM, "differentiable", label="diff_condition"),
      ])
      result = consumer.consume(graph, operation="integrate_substitution")
      if result.all_satisfied:
          consumed = result.consumed_facts
    """

    def __init__(self, specs: tuple[ConsumeSpec, ...] = ()):
        self.specs = specs

    def consume(self, graph: FactGraph,
                operation: str = "") -> ConsumeResult:
        consumed = {}
        missing = []
        for spec in self.specs:
            fact = spec.find_in(graph)
            if fact:
                consumed[spec.label or spec.expression_pattern] = fact
            elif spec.required:
                missing.append(spec)
        return ConsumeResult(
            consumed=consumed,
            missing=tuple(missing),
            all_satisfied=len(missing) == 0,
            operation=operation,
        )


@dataclass(frozen=True)
class ConsumeResult:
    consumed: dict = None
    missing: tuple[ConsumeSpec, ...] = ()
    all_satisfied: bool = False
    operation: str = ""

    def __post_init__(self):
        if self.consumed is None:
            object.__setattr__(self, "consumed", {})

    @property
    def consumed_fps(self) -> tuple[str, ...]:
        return tuple(f.fingerprint for f in self.consumed.values())

    @property
    def consumed_facts(self) -> tuple[Fact, ...]:
        return tuple(self.consumed.values())

    @property
    def missing_labels(self) -> tuple[str, ...]:
        return tuple(s.label or s.expression_pattern for s in self.missing)


class FactProducer:
    """
    事实生产器 — 将新事实注入 FactGraph。

    用法:
      producer = FactProducer(specs=[
          ProduceSpec("substitution valid", FactType.DERIVED, from_labels=("substitution",)),
          ProduceSpec("Jacobian introduced", FactType.DERIVED, from_labels=("diff_condition",)),
      ])
      new_graph = producer.produce(graph, consume_result, operation="integrate_substitution")
    """

    def __init__(self, specs: tuple[ProduceSpec, ...] = ()):
        self.specs = specs

    def produce(
        self,
        graph: FactGraph,
        consume_result: ConsumeResult,
        operation: str = "",
    ) -> FactGraph:
        produced_facts = []
        produced_edges = []
        for spec in self.specs:
            dep_fps = ()
            for label in spec.from_labels:
                if label in consume_result.consumed:
                    dep_fps += (consume_result.consumed[label].fingerprint,)

            fact = spec.build_fact(operation, dep_fps)
            produced_facts.append(fact)

            for dep_fp in dep_fps:
                produced_edges.append(FactEdge(
                    source_fp=dep_fp,
                    target_fp=fact.fingerprint,
                    edge_type=FactEdgeType.DERIVES,
                    rule=operation,
                    confidence=fact.confidence,
                ))

        return graph.consume_produce(
            operation=operation,
            consumed_fps=consume_result.consumed_fps,
            produced_facts=tuple(produced_facts),
            produced_edges=tuple(produced_edges),
        )


@dataclass(frozen=True)
class OperationFactFlow:
    """
    操作事实流 — 完整的 consume/produce 声明。

    每个数学操作声明:
      1. 它需要什么事实 (consume_specs)
      2. 它产生什么事实 (produce_specs)
      3. 操作名称

    例如: 积分换元

      OperationFactFlow(
          operation="integrate_substitution",
          consume_specs=(
              ConsumeSpec(FactType.DEFINITION, "u=g(x)", label="substitution"),
              ConsumeSpec(FactType.THEOREM, "differentiable", label="diff_condition"),
              ConsumeSpec(FactType.DERIVED, "dx", label="dx_relation"),
          ),
          produce_specs=(
              ProduceSpec("substitution valid", FactType.DERIVED, from_labels=("substitution",)),
              ProduceSpec("Jacobian introduced", FactType.DERIVED, from_labels=("diff_condition",)),
              ProduceSpec("back substitution obligation", FactType.DERIVED, from_labels=("substitution",)),
          ),
      )
    """

    operation: str
    consume_specs: tuple[ConsumeSpec, ...] = ()
    produce_specs: tuple[ProduceSpec, ...] = ()

    @property
    def consumer(self) -> FactConsumer:
        return FactConsumer(specs=self.consume_specs)

    @property
    def producer(self) -> FactProducer:
        return FactProducer(specs=self.produce_specs)

    def execute(self, graph: FactGraph) -> FlowResult:
        consume_result = self.consumer.consume(graph, self.operation)
        if not consume_result.all_satisfied:
            return FlowResult(
                success=False,
                graph=graph,
                consume_result=consume_result,
                produce_result=None,
                missing=consume_result.missing_labels,
            )
        new_graph = self.producer.produce(graph, consume_result, self.operation)
        return FlowResult(
            success=True,
            graph=new_graph,
            consume_result=consume_result,
            produce_result=new_graph,
            missing=(),
        )


@dataclass(frozen=True)
class FlowResult:
    success: bool
    graph: FactGraph
    consume_result: ConsumeResult
    produce_result: Optional[FactGraph]
    missing: tuple[str, ...] = ()

    @property
    def consumed_facts(self) -> tuple[Fact, ...]:
        return self.consume_result.consumed_facts if self.consume_result else ()

    @property
    def produced_facts(self) -> tuple[Fact, ...]:
        if self.produce_result and self.consume_result:
            produced_fps = set()
            for r in self.produce_result.records:
                if r.operation == self.consume_result.operation:
                    produced_fps.update(r.produced_fps)
            return tuple(self.produce_result.fact_by_fp(fp) for fp in produced_fps if self.produce_result.fact_by_fp(fp))
        return ()


BUILTIN_FLOWS: dict[str, OperationFactFlow] = {
    "differentiate": OperationFactFlow(
        operation="differentiate",
        consume_specs=(
            ConsumeSpec(FactType.DEFINITION, "f(x)", label="function", required=True),
            ConsumeSpec(FactType.THEOREM, "differentiable", label="diff_condition", required=False),
            ConsumeSpec(FactType.DOMAIN, "", label="domain", required=False),
        ),
        produce_specs=(
            ProduceSpec("f'(x) computed", FactType.DERIVED, confidence=0.95,
                        justification="求导运算", from_labels=("function",)),
            ProduceSpec("f differentiable", FactType.PROVED, confidence=0.8,
                        justification="求导成功隐含可导", from_labels=("function",)),
        ),
    ),
    "integrate_substitution": OperationFactFlow(
        operation="integrate_substitution",
        consume_specs=(
            ConsumeSpec(FactType.DEFINITION, "u=g(x)", label="substitution", required=True),
            ConsumeSpec(FactType.THEOREM, "differentiable", label="diff_condition", required=True),
            ConsumeSpec(FactType.DERIVED, "dx", label="dx_relation", required=False),
        ),
        produce_specs=(
            ProduceSpec("substitution valid", FactType.DERIVED, confidence=0.9,
                        justification="换元条件满足", from_labels=("substitution", "diff_condition")),
            ProduceSpec("Jacobian introduced", FactType.DERIVED, confidence=0.9,
                        justification="引入 Jacobian", from_labels=("diff_condition",)),
            ProduceSpec("back substitution obligation", FactType.DERIVED, confidence=1.0,
                        justification="需要回代原变量", from_labels=("substitution",)),
        ),
    ),
    "solve_equation": OperationFactFlow(
        operation="solve_equation",
        consume_specs=(
            ConsumeSpec(FactType.CONSTRAINT, "=0", label="equation", required=True),
            ConsumeSpec(FactType.DOMAIN, "", label="domain", required=False),
        ),
        produce_specs=(
            ProduceSpec("solution found", FactType.DERIVED, confidence=0.9,
                        justification="方程求解", from_labels=("equation",)),
            ProduceSpec("verify solution obligation", FactType.DERIVED, confidence=1.0,
                        justification="需要验证解的正确性", from_labels=("equation",)),
        ),
    ),
    "cancel_divisor": OperationFactFlow(
        operation="cancel_divisor",
        consume_specs=(
            ConsumeSpec(FactType.CONSTRAINT, "divisor", label="divisor", required=True),
            ConsumeSpec(FactType.CONSTRAINT, "≠0", label="nonzero", required=True),
        ),
        produce_specs=(
            ProduceSpec("cancellation valid", FactType.DERIVED, confidence=0.95,
                        justification="约分条件满足", from_labels=("divisor", "nonzero")),
        ),
    ),
    "induction_step": OperationFactFlow(
        operation="induction_step",
        consume_specs=(
            ConsumeSpec(FactType.PROVED, "P(k)", label="induction_hypothesis", required=True),
            ConsumeSpec(FactType.GOAL, "P(n)", label="induction_goal", required=True),
        ),
        produce_specs=(
            ProduceSpec("P(k)⇒P(k+1) proved", FactType.PROVED, confidence=1.0,
                        justification="归纳步骤已证", from_labels=("induction_hypothesis",)),
            ProduceSpec("induction complete", FactType.PROVED, confidence=1.0,
                        justification="数学归纳法完成", from_labels=("induction_hypothesis", "induction_goal")),
        ),
    ),
    "case_analysis": OperationFactFlow(
        operation="case_analysis",
        consume_specs=(
            ConsumeSpec(FactType.ASSUMPTION, "", label="case_assumption", required=True),
        ),
        produce_specs=(
            ProduceSpec("case assumption active", FactType.CASE, confidence=0.9,
                        justification="分类讨论假设", from_labels=("case_assumption",)),
        ),
    ),
}
