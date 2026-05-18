"""
MathIR — 数学推理统一中间表示层 (Intermediate Representation)

═══════════════════════════════════════════════════════════════
设计原则
═══════════════════════════════════════════════════════════════

  1. 单一语义源 (Single Source of Truth)
     所有模块对"操作/步骤/状态/错误"的理解必须基于 MathIR，
     不允许各自重新定义。

  2. 向后兼容 (Backward Compatible)
     MathIR 提供适配器，现有模块无需立即重写，
     通过 from_legacy_*() 逐步迁移。

  3. 不可变核心 (Immutable Core)
     MathState / MathOperation / ReasoningStep 一旦创建不可修改，
     修改产生新版本（函数式风格）。

  4. 可序列化 (Serializable)
     所有核心类型支持 to_dict() / from_dict()，
     可直接 JSON 持久化。

═══════════════════════════════════════════════════════════════
统一语义协议
═══════════════════════════════════════════════════════════════

  替代关系:
    operations.Op          →  MathOperation.op_type  (Op 枚举保留，作为 op_type 的值域)
    solution_graph.NODE_TYPES  →  MathOperation.op_type  (不再使用独立字符串)
    reasoning_dag.NodeType →  ReasoningStep.step_type
    expression_ast.ExprType →  MathExpression.expr_type
    symbolic_executor.ErrorLevel →  ErrorSeverity
    各模块自定义 step     →  ReasoningStep
    各模块自定义 graph    →  ReasoningTrace
    各模块自定义 state    →  MathState

═══════════════════════════════════════════════════════════════
核心类型层次
═══════════════════════════════════════════════════════════════

  MathState          — 数学状态快照（表达式集 + 假设 + 约束 + 变量作用域）
  MathExpression     — 数学表达式（LaTeX + 可选 SymPy + 可选 ExprNode）
  MathOperation      — 推导操作（类型 + 输入状态 + 输出状态 + 定理 + 合法性）
  ReasoningStep      — 推理步骤（操作 + 依据 + 依赖 + 错误标记）
  ReasoningTrace     — 推理轨迹（步骤序列 + 图结构 + 最终状态）
  ErrorAnnotation    — 错误标注（严重度 + 类型 + 位置 + 诊断）
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from operations import Op, normalize_op, infer_op_from_text, ops_compatible


# ══════════════════════════════════════════════════════════════
# 1. ErrorSeverity — 统一错误严重度
# ══════════════════════════════════════════════════════════════

class ErrorSeverity(Enum):
    CORRECT = "correct"
    MINOR = "minor"
    CALCULATION = "calculation"
    REASONING = "reasoning"
    CONCEPTUAL = "conceptual"
    MISSING = "missing"

    @property
    def numeric(self) -> int:
        return {
            ErrorSeverity.CORRECT: -1,
            ErrorSeverity.MINOR: 0,
            ErrorSeverity.CALCULATION: 1,
            ErrorSeverity.REASONING: 2,
            ErrorSeverity.CONCEPTUAL: 3,
            ErrorSeverity.MISSING: 4,
        }[self]

    @property
    def label(self) -> str:
        return {
            ErrorSeverity.CORRECT: "正确",
            ErrorSeverity.MINOR: "笔误",
            ErrorSeverity.CALCULATION: "计算错误",
            ErrorSeverity.REASONING: "推理错误",
            ErrorSeverity.CONCEPTUAL: "概念错误",
            ErrorSeverity.MISSING: "步骤缺失",
        }[self]


class StepType(Enum):
    PREMISE = "premise"
    OPERATION = "operation"
    EXPRESSION = "expression"
    CONCLUSION = "conclusion"
    ASSUMPTION = "assumption"
    GOAL = "goal"
    ERROR = "error"
    FINAL_ANSWER = "final_answer"


class EdgeKind(Enum):
    DEPENDS_ON = "depends_on"
    DERIVES_FROM = "derives_from"
    INPUT_TO = "input_to"
    OUTPUT_FROM = "output_from"
    ASSUMES = "assumes"


class Legality(Enum):
    VALID = "valid"
    SUSPECT = "suspect"
    INVALID = "invalid"
    UNKNOWN = "unknown"


# ══════════════════════════════════════════════════════════════
# 2. MathExpression — 统一数学表达式
# ══════════════════════════════════════════════════════════════

class ExprCategory(Enum):
    NUMBER = "number"
    VARIABLE = "variable"
    CONSTANT = "constant"
    BINARY_OP = "binary_op"
    UNARY_OP = "unary_op"
    FUNCTION = "function"
    DERIVATIVE = "derivative"
    INTEGRAL = "integral"
    LIMIT = "limit"
    EQUALITY = "equality"
    INEQUALITY = "inequality"
    MATRIX = "matrix"
    SET = "set"
    COMPOUND = "compound"


@dataclass(frozen=True)
class MathExpression:
    latex: str = ""
    category: ExprCategory = ExprCategory.COMPOUND
    sympy_repr: str = ""
    raw_text: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.latex and not self.raw_text

    def to_dict(self) -> dict:
        d = {"latex": self.latex, "category": self.category.value}
        if self.sympy_repr:
            d["sympy_repr"] = self.sympy_repr
        if self.raw_text:
            d["raw_text"] = self.raw_text
        return d

    @classmethod
    def from_dict(cls, d: dict) -> MathExpression:
        return cls(
            latex=d.get("latex", ""),
            category=ExprCategory(d.get("category", "compound")),
            sympy_repr=d.get("sympy_repr", ""),
            raw_text=d.get("raw_text", ""),
        )

    @classmethod
    def from_latex(cls, latex: str) -> MathExpression:
        return cls(latex=latex, category=ExprCategory.COMPOUND)

    @classmethod
    def from_text(cls, text: str) -> MathExpression:
        return cls(raw_text=text, category=ExprCategory.COMPOUND)


# ══════════════════════════════════════════════════════════════
# 3. MathState — 数学状态快照
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MathState:
    expressions: tuple[MathExpression, ...] = ()
    assumptions: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    variable_scope: tuple[str, ...] = ()

    @property
    def constraint_graph(self):
        from constraints import ConstraintGraph
        return ConstraintGraph.from_strings(list(self.constraints))

    def with_constraint_graph(self, graph) -> MathState:
        return MathState(
            expressions=self.expressions,
            assumptions=self.assumptions,
            constraints=tuple(graph.to_string_list()),
            variable_scope=self.variable_scope,
        )

    def with_expression(self, expr: MathExpression) -> MathState:
        return MathState(
            expressions=self.expressions + (expr,),
            assumptions=self.assumptions,
            constraints=self.constraints,
            variable_scope=self.variable_scope,
        )

    def with_assumption(self, assumption: str) -> MathState:
        return MathState(
            expressions=self.expressions,
            assumptions=self.assumptions + (assumption,),
            constraints=self.constraints,
            variable_scope=self.variable_scope,
        )

    def with_constraint(self, constraint: str) -> MathState:
        return MathState(
            expressions=self.expressions,
            assumptions=self.assumptions,
            constraints=self.constraints + (constraint,),
            variable_scope=self.variable_scope,
        )

    def with_variable(self, var: str) -> MathState:
        return MathState(
            expressions=self.expressions,
            assumptions=self.assumptions,
            constraints=self.constraints,
            variable_scope=self.variable_scope + (var,),
        )

    @property
    def is_empty(self) -> bool:
        return not self.expressions and not self.assumptions and not self.constraints

    @property
    def fingerprint(self) -> str:
        parts = [
            "|".join(e.latex for e in self.expressions),
            "|".join(self.assumptions),
            "|".join(self.constraints),
            "|".join(self.variable_scope),
        ]
        raw = ";;".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        d = {}
        if self.expressions:
            d["expressions"] = [e.to_dict() for e in self.expressions]
        if self.assumptions:
            d["assumptions"] = list(self.assumptions)
        if self.constraints:
            d["constraints"] = list(self.constraints)
        if self.variable_scope:
            d["variable_scope"] = list(self.variable_scope)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> MathState:
        exprs = tuple(MathExpression.from_dict(e) for e in d.get("expressions", []))
        return cls(
            expressions=exprs,
            assumptions=tuple(d.get("assumptions", [])),
            constraints=tuple(d.get("constraints", [])),
            variable_scope=tuple(d.get("variable_scope", [])),
        )

    @classmethod
    def empty(cls) -> MathState:
        return cls()

    def semantic_hash(self) -> str:
        from canonicalization.fingerprint import state_fingerprint
        expr_texts = tuple(e.latex or e.raw_text or "" for e in self.expressions)
        return state_fingerprint(
            expressions=expr_texts,
            constraints=self.constraints,
            assumptions=self.assumptions,
            variable_scope=self.variable_scope,
        )

    def canonicalize(self) -> MathState:
        from canonicalization.state import canonicalize_state
        from canonicalization.expression import CanonicalForm
        expr_texts = tuple(e.latex or e.raw_text or "" for e in self.expressions)
        result = canonicalize_state(
            expressions=expr_texts,
            constraints=self.constraints,
            assumptions=self.assumptions,
            variable_scope=self.variable_scope,
            form=CanonicalForm.EXPANDED,
        )
        canon_exprs = tuple(
            MathExpression(latex=t, category=ExprCategory.COMPOUND)
            for t in result['expressions']
        )
        return MathState(
            expressions=canon_exprs,
            assumptions=result['assumptions'],
            constraints=result['constraints'],
            variable_scope=result['variable_scope'],
        )

    def is_equivalent_to(self, other: MathState) -> bool:
        from canonicalization.fingerprint import states_are_equivalent
        expr_a = tuple(e.latex or e.raw_text or "" for e in self.expressions)
        expr_b = tuple(e.latex or e.raw_text or "" for e in other.expressions)
        return states_are_equivalent(
            state_a_expressions=expr_a,
            state_a_constraints=self.constraints,
            state_b_expressions=expr_b,
            state_b_constraints=other.constraints,
        )


# ══════════════════════════════════════════════════════════════
# 4. MathOperation — 统一推导操作
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MathOperation:
    op_type: Op = Op.COMPUTE
    input_state: MathState = field(default_factory=MathState.empty)
    output_state: MathState = field(default_factory=MathState.empty)
    theorem: str = ""
    legality: Legality = Legality.UNKNOWN
    goal: str = ""
    strategy: str = ""
    reasoning: str = ""

    @property
    def is_valid(self) -> bool:
        return self.legality in (Legality.VALID, Legality.UNKNOWN)

    @property
    def display_name(self) -> str:
        from operations import _ALIASES
        reverse = {v: k for k, v in _ALIASES.items() if isinstance(v, Op)}
        cn = reverse.get(self.op_type, "")
        if cn:
            return cn
        display_map = {
            Op.DIFFERENTIATE: "求导",
            Op.PARTIAL_DIFF: "偏导",
            Op.INTEGRATE: "积分",
            Op.COMPUTE_LIMIT: "极限",
            Op.EXPAND: "展开",
            Op.EXPAND_SERIES: "级数展开",
            Op.FACTOR: "因式分解",
            Op.SIMPLIFY: "化简",
            Op.SUBSTITUTE: "代入",
            Op.COLLECT: "合并同类项",
            Op.CANCEL: "约分",
            Op.SOLVE_EQUATION: "解方程",
            Op.SOLVE_SYSTEM: "解方程组",
            Op.SOLVE_INEQUALITY: "解不等式",
            Op.MATRIX_OP: "矩阵运算",
            Op.ROW_REDUCE: "行变换",
            Op.EIGEN_SOLVE: "特征值求解",
            Op.DETERMINANT: "行列式",
            Op.ORTHOGONALIZE: "正交化",
            Op.QUADRATIC_FORM: "二次型",
            Op.CONVERGENCE_TEST: "收敛性判断",
            Op.SUM_SERIES: "级数求和",
            Op.PROBABILITY_CALC: "概率计算",
            Op.EXPECTATION: "期望方差",
            Op.MLE_DERIVE: "极大似然估计",
            Op.MOMENT_ESTIMATE: "矩估计",
            Op.HYPOTHESIS_TEST: "假设检验",
            Op.APPLY_THEOREM: "应用定理",
            Op.CLASSIFY: "分类讨论",
            Op.INDUCTION_STEP: "数学归纳",
            Op.CONTRADICTION: "反证法",
            Op.COMPUTE: "计算",
            Op.DEFINE: "定义",
            Op.FINAL_ANSWER: "最终答案",
            Op.CROSS_PRODUCT: "叉积",
            Op.DOT_PRODUCT: "点积",
            Op.NORM: "范数",
        }
        return display_map.get(self.op_type, self.op_type.value)

    def to_dict(self) -> dict:
        d = {"op_type": self.op_type.value}
        if not self.input_state.is_empty:
            d["input_state"] = self.input_state.to_dict()
        if not self.output_state.is_empty:
            d["output_state"] = self.output_state.to_dict()
        if self.theorem:
            d["theorem"] = self.theorem
        if self.legality != Legality.UNKNOWN:
            d["legality"] = self.legality.value
        if self.goal:
            d["goal"] = self.goal
        if self.strategy:
            d["strategy"] = self.strategy
        if self.reasoning:
            d["reasoning"] = self.reasoning
        return d

    @classmethod
    def from_dict(cls, d: dict) -> MathOperation:
        op = normalize_op(d.get("op_type", "compute"))
        input_state = MathState.from_dict(d["input_state"]) if "input_state" in d else MathState.empty()
        output_state = MathState.from_dict(d["output_state"]) if "output_state" in d else MathState.empty()
        legality = Legality(d.get("legality", "unknown"))
        return cls(
            op_type=op,
            input_state=input_state,
            output_state=output_state,
            theorem=d.get("theorem", ""),
            legality=legality,
            goal=d.get("goal", ""),
            strategy=d.get("strategy", ""),
            reasoning=d.get("reasoning", ""),
        )

    @classmethod
    def from_text(cls, text: str) -> MathOperation:
        op = infer_op_from_text(text)
        return cls(op_type=op)


# ══════════════════════════════════════════════════════════════
# 5. ErrorAnnotation — 统一错误标注
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ErrorAnnotation:
    severity: ErrorSeverity = ErrorSeverity.CORRECT
    error_type: str = ""
    description: str = ""
    position: str = ""
    root_cause: str = ""
    suggestion: str = ""

    @property
    def is_error(self) -> bool:
        return self.severity != ErrorSeverity.CORRECT

    def to_dict(self) -> dict:
        d = {"severity": self.severity.value}
        if self.error_type:
            d["error_type"] = self.error_type
        if self.description:
            d["description"] = self.description
        if self.position:
            d["position"] = self.position
        if self.root_cause:
            d["root_cause"] = self.root_cause
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ErrorAnnotation:
        return cls(
            severity=ErrorSeverity(d.get("severity", "correct")),
            error_type=d.get("error_type", ""),
            description=d.get("description", ""),
            position=d.get("position", ""),
            root_cause=d.get("root_cause", ""),
            suggestion=d.get("suggestion", ""),
        )

    @classmethod
    def correct(cls) -> ErrorAnnotation:
        return cls(severity=ErrorSeverity.CORRECT)

    @classmethod
    def missing(cls, description: str = "") -> ErrorAnnotation:
        return cls(severity=ErrorSeverity.MISSING, description=description)

    @classmethod
    def calculation_error(cls, description: str = "") -> ErrorAnnotation:
        return cls(severity=ErrorSeverity.CALCULATION, description=description)

    @classmethod
    def reasoning_error(cls, description: str = "") -> ErrorAnnotation:
        return cls(severity=ErrorSeverity.REASONING, description=description)

    @classmethod
    def conceptual_error(cls, description: str = "") -> ErrorAnnotation:
        return cls(severity=ErrorSeverity.CONCEPTUAL, description=description)


# ══════════════════════════════════════════════════════════════
# 6. ReasoningStep — 统一推理步骤
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ReasoningStep:
    step_id: str = ""
    step_type: StepType = StepType.OPERATION
    operation: MathOperation = field(default_factory=MathOperation)
    label: str = ""
    content: str = ""
    dependencies: tuple[str, ...] = ()
    weight: float = 0.0
    required: bool = True
    alternatives: tuple[str, ...] = ()
    error: ErrorAnnotation = field(default_factory=ErrorAnnotation.correct)
    confidence: float = 1.0
    metadata: tuple[tuple[str, Any], ...] = ()

    @property
    def is_correct(self) -> bool:
        return not self.error.is_error

    @property
    def op_type(self) -> Op:
        return self.operation.op_type

    @property
    def fingerprint(self) -> str:
        parts = [
            self.operation.op_type.value,
            self.operation.output_state.fingerprint,
            self.label,
        ]
        raw = "::".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()[:8]

    def with_error(self, error: ErrorAnnotation) -> ReasoningStep:
        return ReasoningStep(
            step_id=self.step_id,
            step_type=self.step_type,
            operation=self.operation,
            label=self.label,
            content=self.content,
            dependencies=self.dependencies,
            weight=self.weight,
            required=self.required,
            alternatives=self.alternatives,
            error=error,
            confidence=self.confidence,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict:
        d = {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "operation": self.operation.to_dict(),
        }
        if self.label:
            d["label"] = self.label
        if self.content:
            d["content"] = self.content
        if self.dependencies:
            d["dependencies"] = list(self.dependencies)
        if self.weight != 0.0:
            d["weight"] = self.weight
        if not self.required:
            d["required"] = self.required
        if self.alternatives:
            d["alternatives"] = list(self.alternatives)
        if self.error.is_error:
            d["error"] = self.error.to_dict()
        if self.confidence != 1.0:
            d["confidence"] = self.confidence
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ReasoningStep:
        op = MathOperation.from_dict(d.get("operation", {}))
        step_type = StepType(d.get("step_type", "operation"))
        error = ErrorAnnotation.from_dict(d.get("error", {})) if "error" in d else ErrorAnnotation.correct()
        return cls(
            step_id=d.get("step_id", ""),
            step_type=step_type,
            operation=op,
            label=d.get("label", ""),
            content=d.get("content", ""),
            dependencies=tuple(d.get("dependencies", [])),
            weight=d.get("weight", 0.0),
            required=d.get("required", True),
            alternatives=tuple(d.get("alternatives", [])),
            error=error,
            confidence=d.get("confidence", 1.0),
            metadata=tuple(d.get("metadata", {}).items()) if "metadata" in d else (),
        )


# ══════════════════════════════════════════════════════════════
# 7. TraceEdge — 推理图边
# ══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TraceEdge:
    source_id: str = ""
    target_id: str = ""
    kind: EdgeKind = EdgeKind.DERIVES_FROM
    label: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict:
        d = {
            "source": self.source_id,
            "target": self.target_id,
            "kind": self.kind.value,
        }
        if self.label:
            d["label"] = self.label
        if self.weight != 1.0:
            d["weight"] = self.weight
        return d

    @classmethod
    def from_dict(cls, d: dict) -> TraceEdge:
        return cls(
            source_id=d.get("source", ""),
            target_id=d.get("target", ""),
            kind=EdgeKind(d.get("kind", "derives_from")),
            label=d.get("label", ""),
            weight=d.get("weight", 1.0),
        )


# ══════════════════════════════════════════════════════════════
# 8. ReasoningTrace — 统一推理轨迹
# ══════════════════════════════════════════════════════════════

@dataclass
class ReasoningTrace:
    trace_id: str = ""
    question_id: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    edges: list[TraceEdge] = field(default_factory=list)
    final_state: MathState = field(default_factory=MathState.empty)
    total_score: float = 10.0
    source: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = hashlib.md5(
                f"{self.question_id}:{time.time()}".encode()
            ).hexdigest()[:12]
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def operation_sequence(self) -> list[Op]:
        return [s.operation.op_type for s in self.steps if s.step_type == StepType.OPERATION]

    @property
    def fingerprint(self) -> str:
        ops = [s.operation.op_type.value for s in self.steps]
        raw = ":".join(ops)
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @property
    def error_count(self) -> int:
        return sum(1 for s in self.steps if s.error.is_error)

    @property
    def error_steps(self) -> list[ReasoningStep]:
        return [s for s in self.steps if s.error.is_error]

    @property
    def coverage(self) -> float:
        if not self.steps:
            return 0.0
        present = sum(1 for s in self.steps if s.is_correct and s.step_type == StepType.OPERATION)
        total = sum(1 for s in self.steps if s.step_type == StepType.OPERATION)
        return present / max(total, 1)

    def get_step(self, step_id: str) -> Optional[ReasoningStep]:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def get_dependencies(self, step_id: str) -> list[str]:
        return [e.source_id for e in self.edges if e.target_id == step_id]

    def get_dependents(self, step_id: str) -> list[str]:
        return [e.target_id for e in self.edges if e.source_id == step_id]

    def topological_order(self) -> list[str]:
        in_degree = {s.step_id: 0 for s in self.steps}
        step_ids = {s.step_id for s in self.steps}
        for e in self.edges:
            if e.target_id in in_degree:
                in_degree[e.target_id] += 1
        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            sid = queue.pop(0)
            result.append(sid)
            for e in self.edges:
                if e.source_id == sid and e.target_id in in_degree:
                    in_degree[e.target_id] -= 1
                    if in_degree[e.target_id] == 0:
                        queue.append(e.target_id)
        return result

    def error_path(self, error_step_id: str) -> list[str]:
        path = []
        current = error_step_id
        visited = set()
        while current and current not in visited:
            visited.add(current)
            path.append(current)
            deps = self.get_dependencies(current)
            current = deps[0] if deps else None
        return list(reversed(path))

    def add_step(self, step: ReasoningStep) -> str:
        if not step.step_id:
            step = ReasoningStep(
                step_id=f"s{len(self.steps) + 1}",
                step_type=step.step_type,
                operation=step.operation,
                label=step.label,
                content=step.content,
                dependencies=step.dependencies,
                weight=step.weight,
                required=step.required,
                alternatives=step.alternatives,
                error=step.error,
                confidence=step.confidence,
                metadata=step.metadata,
            )
        self.steps.append(step)
        return step.step_id

    def add_edge(self, source_id: str, target_id: str,
                 kind: EdgeKind = EdgeKind.DERIVES_FROM,
                 label: str = "", weight: float = 1.0) -> None:
        self.edges.append(TraceEdge(
            source_id=source_id,
            target_id=target_id,
            kind=kind,
            label=label,
            weight=weight,
        ))

    def compute_score(self) -> float:
        score = 0.0
        for s in self.steps:
            if s.is_correct and s.weight > 0:
                score += s.weight
            elif s.error.severity == ErrorSeverity.MINOR and s.weight > 0:
                score += s.weight * 0.8
        return round(score, 1)

    def to_dict(self) -> dict:
        d = {
            "trace_id": self.trace_id,
            "question_id": self.question_id,
            "steps": [s.to_dict() for s in self.steps],
            "edges": [e.to_dict() for e in self.edges],
            "total_score": self.total_score,
        }
        if not self.final_state.is_empty:
            d["final_state"] = self.final_state.to_dict()
        if self.source:
            d["source"] = self.source
        if self.created_at:
            d["created_at"] = self.created_at
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ReasoningTrace:
        steps = [ReasoningStep.from_dict(s) for s in d.get("steps", [])]
        edges = [TraceEdge.from_dict(e) for e in d.get("edges", [])]
        final_state = MathState.from_dict(d["final_state"]) if "final_state" in d else MathState.empty()
        return cls(
            trace_id=d.get("trace_id", ""),
            question_id=d.get("question_id", ""),
            steps=steps,
            edges=edges,
            final_state=final_state,
            total_score=d.get("total_score", 10.0),
            source=d.get("source", ""),
            created_at=d.get("created_at", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> ReasoningTrace:
        return cls.from_dict(json.loads(json_str))

    def to_mermaid(self) -> str:
        lines = ["graph TD"]
        step_map = {s.step_id: s for s in self.steps}
        for s in self.steps:
            style_map = {
                StepType.PREMISE: "style fill:#E8F4FD,stroke:#2563EB",
                StepType.OPERATION: "style fill:#FEF3C7,stroke:#D97706",
                StepType.CONCLUSION: "style fill:#D1FAE5,stroke:#059669",
                StepType.ERROR: "style fill:#FEE2E2,stroke:#DC2626",
                StepType.GOAL: "style fill:#E9D5FF,stroke:#7C3AED",
                StepType.ASSUMPTION: "style fill:#F3E8FF,stroke:#9333EA",
                StepType.EXPRESSION: "style fill:#F0FDF4,stroke:#16A34A",
                StepType.FINAL_ANSWER: "style fill:#D1FAE5,stroke:#059669",
            }
            label = s.label or s.content[:30] if s.content else s.step_id
            label = label.replace('"', "'")
            lines.append(f'    {s.step_id}["{label}"]')
            style = style_map.get(s.step_type)
            if style:
                lines.append(f'    {s.step_id} {style}')
        for e in self.edges:
            edge_label = f"|{e.label}|" if e.label else ""
            lines.append(f'    {e.source_id} -->{edge_label} {e.target_id}')
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# 9. TraceBuilder — 推理轨迹构建器
# ══════════════════════════════════════════════════════════════

class TraceBuilder:
    def __init__(self, question_id: str = "", total_score: float = 10.0):
        self._trace = ReasoningTrace(
            question_id=question_id,
            total_score=total_score,
        )
        self._counter = 0

    def _next_id(self, prefix: str = "s") -> str:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def add_premise(self, content: str, label: str = "前提",
                    expressions: list[MathExpression] = None) -> str:
        sid = self._next_id("p")
        state = MathState.empty()
        if expressions:
            for e in expressions:
                state = state.with_expression(e)
        step = ReasoningStep(
            step_id=sid,
            step_type=StepType.PREMISE,
            operation=MathOperation(op_type=Op.DEFINE),
            label=label,
            content=content,
            weight=0.0,
        )
        self._trace.steps.append(step)
        return sid

    def add_goal(self, content: str, label: str = "目标") -> str:
        sid = self._next_id("g")
        step = ReasoningStep(
            step_id=sid,
            step_type=StepType.GOAL,
            operation=MathOperation(op_type=Op.COMPUTE),
            label=label,
            content=content,
            weight=0.0,
        )
        self._trace.steps.append(step)
        return sid

    def add_operation(self, op_type: Op, content: str = "",
                      label: str = "", weight: float = 0.0,
                      input_state: MathState = None,
                      output_state: MathState = None,
                      goal: str = "", strategy: str = "",
                      theorem: str = "",
                      dependencies: list[str] = None) -> str:
        sid = self._next_id()
        if not label:
            op = MathOperation(op_type=op_type)
            label = op.display_name
        op = MathOperation(
            op_type=op_type,
            input_state=input_state or MathState.empty(),
            output_state=output_state or MathState.empty(),
            goal=goal,
            strategy=strategy,
            theorem=theorem,
        )
        step = ReasoningStep(
            step_id=sid,
            step_type=StepType.OPERATION,
            operation=op,
            label=label,
            content=content,
            dependencies=tuple(dependencies or []),
            weight=weight,
        )
        self._trace.steps.append(step)
        return sid

    def add_conclusion(self, content: str, label: str = "结论",
                       expression: MathExpression = None) -> str:
        sid = self._next_id("c")
        output_state = MathState.empty()
        if expression:
            output_state = output_state.with_expression(expression)
        step = ReasoningStep(
            step_id=sid,
            step_type=StepType.CONCLUSION,
            operation=MathOperation(op_type=Op.FINAL_ANSWER, output_state=output_state),
            label=label,
            content=content,
            weight=0.0,
        )
        self._trace.steps.append(step)
        return sid

    def add_assumption(self, content: str, label: str = "假设") -> str:
        sid = self._next_id("a")
        step = ReasoningStep(
            step_id=sid,
            step_type=StepType.ASSUMPTION,
            operation=MathOperation(op_type=Op.DEFINE),
            label=label,
            content=content,
            weight=0.0,
        )
        self._trace.steps.append(step)
        return sid

    def add_error_step(self, content: str, error: ErrorAnnotation,
                       op_type: Op = Op.COMPUTE, label: str = "") -> str:
        sid = self._next_id("e")
        step = ReasoningStep(
            step_id=sid,
            step_type=StepType.ERROR,
            operation=MathOperation(op_type=op_type),
            label=label or error.severity.label,
            content=content,
            error=error,
            weight=0.0,
        )
        self._trace.steps.append(step)
        return sid

    def connect(self, source_id: str, target_id: str,
                kind: EdgeKind = EdgeKind.DERIVES_FROM,
                label: str = "") -> TraceBuilder:
        self._trace.add_edge(source_id, target_id, kind, label)
        return self

    def depends_on(self, source_id: str, target_id: str, label: str = "") -> TraceBuilder:
        return self.connect(source_id, target_id, EdgeKind.DEPENDS_ON, label)

    def derives_from(self, source_id: str, target_id: str, label: str = "") -> TraceBuilder:
        return self.connect(source_id, target_id, EdgeKind.DERIVES_FROM, label)

    def input_to(self, source_id: str, target_id: str, label: str = "") -> TraceBuilder:
        return self.connect(source_id, target_id, EdgeKind.INPUT_TO, label)

    def output_from(self, source_id: str, target_id: str, label: str = "") -> TraceBuilder:
        return self.connect(source_id, target_id, EdgeKind.OUTPUT_FROM, label)

    def set_final_state(self, state: MathState) -> TraceBuilder:
        self._trace.final_state = state
        return self

    def set_source(self, source: str) -> TraceBuilder:
        self._trace.source = source
        return self

    def build(self) -> ReasoningTrace:
        return self._trace


# ══════════════════════════════════════════════════════════════
# 10. 适配器 — 从现有模块桥接到 MathIR
# ══════════════════════════════════════════════════════════════

def from_solution_graph(sg: 'SolutionGraph') -> ReasoningTrace:
    """
    将 solution_graph.SolutionGraph 转换为 ReasoningTrace。
    SolutionGraph 的 GraphNode → ReasoningStep
    """
    from solution_graph import SolutionGraph as _SG

    builder = TraceBuilder(
        question_id=sg.question_id,
        total_score=sg.total_score,
    )

    id_map = {}
    for node in sg.nodes:
        op = normalize_op(node.operation or node.type)
        step_type = StepType.OPERATION
        if node.type == "final_answer":
            step_type = StepType.FINAL_ANSWER

        input_state = MathState.empty()
        if node.input_state:
            input_state = input_state.with_expression(MathExpression.from_latex(node.input_state))

        output_state = MathState.empty()
        if node.output:
            output_state = output_state.with_expression(MathExpression.from_latex(node.output))

        operation = MathOperation(
            op_type=op,
            input_state=input_state,
            output_state=output_state,
            goal=node.goal if hasattr(node, 'goal') else "",
            strategy=node.strategy if hasattr(node, 'strategy') else "",
            reasoning=node.reasoning if hasattr(node, 'reasoning') else "",
        )

        sid = builder.add_operation(
            op_type=op,
            content=node.label or node.type,
            label=node.label or op.value,
            weight=node.weight,
            input_state=input_state,
            output_state=output_state,
            goal=node.goal if hasattr(node, 'goal') else "",
            strategy=node.strategy if hasattr(node, 'strategy') else "",
            dependencies=node.input_refs if node.input_refs else None,
        )
        id_map[node.id] = sid

        step = builder._trace.steps[-1]
        builder._trace.steps[-1] = ReasoningStep(
            step_id=sid,
            step_type=step_type,
            operation=operation,
            label=node.label or op.value,
            content=node.label or node.type,
            dependencies=tuple(node.input_refs) if node.input_refs else (),
            weight=node.weight,
            required=node.required,
            alternatives=tuple(node.alternatives) if node.alternatives else (),
        )

    for edge in sg.edges:
        src = id_map.get(edge.source, edge.source)
        tgt = id_map.get(edge.target, edge.target)
        builder.derives_from(src, tgt)

    builder.set_source("solution_graph")
    return builder.build()


def from_reasoning_dag(dag: 'ReasoningDAG') -> ReasoningTrace:
    """
    将 reasoning_dag.ReasoningDAG 转换为 ReasoningTrace。
    DagNode → ReasoningStep
    """
    from reasoning_dag import ReasoningDAG as _RD, NodeType as _NT, EdgeType as _ET

    builder = TraceBuilder(question_id="")

    type_map = {
        _NT.PREMISE: StepType.PREMISE,
        _NT.EXPRESSION: StepType.EXPRESSION,
        _NT.OPERATION: StepType.OPERATION,
        _NT.CONCLUSION: StepType.CONCLUSION,
        _NT.ASSUMPTION: StepType.ASSUMPTION,
        _NT.GOAL: StepType.GOAL,
        _NT.ERROR: StepType.ERROR,
    }

    edge_kind_map = {
        _ET.DEPENDS_ON: EdgeKind.DEPENDS_ON,
        _ET.DERIVES_FROM: EdgeKind.DERIVES_FROM,
        _ET.INPUT_TO: EdgeKind.INPUT_TO,
        _ET.OUTPUT_FROM: EdgeKind.OUTPUT_FROM,
        _ET.ASSUMES: EdgeKind.ASSUMES,
    }

    id_map = {}
    for nid, node in dag.nodes.items():
        step_type = type_map.get(node.type, StepType.OPERATION)
        op = node.operation if node.operation else Op.COMPUTE

        if step_type == StepType.PREMISE:
            sid = builder.add_premise(node.content, label=node.label)
        elif step_type == StepType.GOAL:
            sid = builder.add_goal(node.content, label=node.label)
        elif step_type == StepType.CONCLUSION:
            sid = builder.add_conclusion(node.content, label=node.label)
        elif step_type == StepType.ASSUMPTION:
            sid = builder.add_assumption(node.content, label=node.label)
        elif step_type == StepType.ERROR:
            sid = builder.add_error_step(
                node.content,
                ErrorAnnotation.missing(node.metadata.get("error", "")),
                op_type=op,
                label=node.label,
            )
        else:
            sid = builder.add_operation(
                op_type=op,
                content=node.content,
                label=node.label,
            )
        id_map[nid] = sid

    for edge in dag.edges:
        src = id_map.get(edge.source_id, edge.source_id)
        tgt = id_map.get(edge.target_id, edge.target_id)
        kind = edge_kind_map.get(edge.type, EdgeKind.DERIVES_FROM)
        builder.connect(src, tgt, kind, edge.label)

    builder.set_source("reasoning_dag")
    return builder.build()


def from_student_trace(trace_dict: dict) -> ReasoningTrace:
    """
    将 student_trace_extractor.extract_student_trace() 的输出转换为 ReasoningTrace。
    """
    builder = TraceBuilder(question_id="")

    steps_data = trace_dict.get("steps", [])
    id_map = {}

    for i, s in enumerate(steps_data):
        op = normalize_op(s.get("operation", "compute"))
        input_state = MathState.empty()
        if s.get("input_state"):
            input_state = input_state.with_expression(MathExpression.from_text(s["input_state"]))
        output_state = MathState.empty()
        if s.get("output_state"):
            output_state = output_state.with_expression(MathExpression.from_text(s["output_state"]))

        error = ErrorAnnotation.correct()
        if s.get("has_error"):
            error = ErrorAnnotation(
                severity=ErrorSeverity.CALCULATION,
                description=s.get("error_description", ""),
            )

        sid = builder.add_operation(
            op_type=op,
            content=s.get("label", ""),
            label=s.get("label", f"步骤{i+1}"),
            weight=0.0,
            input_state=input_state,
            output_state=output_state,
        )

        step = builder._trace.steps[-1]
        builder._trace.steps[-1] = ReasoningStep(
            step_id=sid,
            step_type=StepType.OPERATION,
            operation=MathOperation(
                op_type=op,
                input_state=input_state,
                output_state=output_state,
            ),
            label=s.get("label", f"步骤{i+1}"),
            content=s.get("label", ""),
            error=error,
            confidence=s.get("confidence", 1.0),
        )
        id_map[s.get("id", f"s{i+1}")] = sid

    builder.set_source(f"student_trace:{trace_dict.get('extraction_method', 'unknown')}")
    return builder.build()


def from_question_ast_steps(steps: list) -> ReasoningTrace:
    """
    将 question_ast.SolutionStep 列表转换为 ReasoningTrace。
    """
    builder = TraceBuilder(question_id="")

    prev_id = None
    for i, step in enumerate(steps):
        if isinstance(step, dict):
            content = step.get("content", "")
            label = step.get("label", f"步骤{i+1}")
            operation_str = step.get("operation", "")
        else:
            content = getattr(step, 'content', "")
            label = getattr(step, 'label', f"步骤{i+1}")
            operation_str = getattr(step, 'operation', "")

        op = normalize_op(operation_str)
        deps = [prev_id] if prev_id else None
        sid = builder.add_operation(
            op_type=op,
            content=content,
            label=label,
            dependencies=deps,
        )
        if prev_id:
            builder.derives_from(prev_id, sid)
        prev_id = sid

    builder.set_source("question_ast")
    return builder.build()


# ══════════════════════════════════════════════════════════════
# 11. 反向适配器 — 从 MathIR 桥接回现有模块
# ══════════════════════════════════════════════════════════════

def to_solution_graph(trace: ReasoningTrace) -> 'SolutionGraph':
    """
    将 ReasoningTrace 转换回 solution_graph.SolutionGraph。
    """
    from solution_graph import SolutionGraph, GraphNode, GraphEdge

    nodes = []
    id_map = {}
    for s in trace.steps:
        if s.step_type in (StepType.PREMISE, StepType.GOAL):
            continue
        output_latex = ""
        if s.operation.output_state.expressions:
            output_latex = s.operation.output_state.expressions[0].latex
        input_state_latex = ""
        if s.operation.input_state.expressions:
            input_state_latex = s.operation.input_state.expressions[0].latex

        gn = GraphNode(
            id=s.step_id,
            type=s.operation.op_type.value,
            label=s.label,
            output=output_latex,
            input_state=input_state_latex,
            operation=s.operation.op_type.value,
            input_refs=list(s.dependencies),
            weight=s.weight,
            required=s.required,
            alternatives=list(s.alternatives),
            goal=s.operation.goal,
            strategy=s.operation.strategy,
            reasoning=s.operation.reasoning,
        )
        nodes.append(gn)
        id_map[s.step_id] = s.step_id

    edges = [GraphEdge(source=e.source_id, target=e.target_id) for e in trace.edges]

    final_answer = ""
    for s in reversed(trace.steps):
        if s.step_type == StepType.FINAL_ANSWER or s.operation.op_type == Op.FINAL_ANSWER:
            final_answer = s.content
            break

    return SolutionGraph(
        question_id=trace.question_id,
        final_answer=final_answer,
        nodes=nodes,
        edges=edges,
        total_score=trace.total_score,
    )


def to_reasoning_dag(trace: ReasoningTrace) -> 'ReasoningDAG':
    """
    将 ReasoningTrace 转换回 reasoning_dag.ReasoningDAG。
    """
    from reasoning_dag import ReasoningDAG, DagNode, DagEdge, NodeType, EdgeType

    dag = ReasoningDAG()

    step_type_map = {
        StepType.PREMISE: NodeType.PREMISE,
        StepType.EXPRESSION: NodeType.EXPRESSION,
        StepType.OPERATION: NodeType.OPERATION,
        StepType.CONCLUSION: NodeType.CONCLUSION,
        StepType.ASSUMPTION: NodeType.ASSUMPTION,
        StepType.GOAL: NodeType.GOAL,
        StepType.ERROR: NodeType.ERROR,
        StepType.FINAL_ANSWER: NodeType.CONCLUSION,
    }

    edge_kind_map = {
        EdgeKind.DEPENDS_ON: EdgeType.DEPENDS_ON,
        EdgeKind.DERIVES_FROM: EdgeType.DERIVES_FROM,
        EdgeKind.INPUT_TO: EdgeType.INPUT_TO,
        EdgeKind.OUTPUT_FROM: EdgeType.OUTPUT_FROM,
        EdgeKind.ASSUMES: EdgeType.ASSUMES,
    }

    for s in trace.steps:
        nt = step_type_map.get(s.step_type, NodeType.OPERATION)
        dag.nodes[s.step_id] = DagNode(
            id=s.step_id,
            type=nt,
            label=s.label,
            content=s.content,
            operation=s.operation.op_type,
        )

    for e in trace.edges:
        et = edge_kind_map.get(e.kind, EdgeType.DERIVES_FROM)
        dag.edges.append(DagEdge(
            source_id=e.source_id,
            target_id=e.target_id,
            type=et,
            label=e.label,
            weight=e.weight,
        ))

    return dag


def to_student_trace_dict(trace: ReasoningTrace) -> dict:
    """
    将 ReasoningTrace 转换回 student_trace_extractor 的输出格式。
    """
    steps = []
    for s in trace.steps:
        if s.step_type in (StepType.PREMISE, StepType.GOAL):
            continue
        input_state = ""
        if s.operation.input_state.expressions:
            input_state = s.operation.input_state.expressions[0].latex or s.operation.input_state.expressions[0].raw_text
        output_state = ""
        if s.operation.output_state.expressions:
            output_state = s.operation.output_state.expressions[0].latex or s.operation.output_state.expressions[0].raw_text

        steps.append({
            "id": s.step_id,
            "operation": s.operation.op_type.value,
            "input_state": input_state,
            "output_state": output_state,
            "label": s.label,
            "has_error": s.error.is_error,
            "error_description": s.error.description if s.error.is_error else "",
            "confidence": s.confidence,
        })

    final_answer = ""
    for s in reversed(trace.steps):
        if s.step_type == StepType.FINAL_ANSWER or s.operation.op_type == Op.FINAL_ANSWER:
            final_answer = s.content
            break

    return {
        "steps": steps,
        "final_answer": final_answer,
        "method_name": "",
        "extraction_method": trace.source or "math_ir",
    }


# ══════════════════════════════════════════════════════════════
# 12. Diff Engine — 基于 MathIR 的统一对比
# ══════════════════════════════════════════════════════════════

@dataclass
class TraceDiff:
    coverage: float = 0.0
    matched_steps: list[tuple[str, str]] = field(default_factory=list)
    missing_steps: list[str] = field(default_factory=list)
    extra_steps: list[str] = field(default_factory=list)
    error_steps: list[str] = field(default_factory=list)
    structure_broken: bool = False
    score: float = 0.0
    total: float = 10.0
    details: list[str] = field(default_factory=list)

    @property
    def is_correct(self) -> bool:
        return not self.error_steps and not self.missing_steps and not self.structure_broken

    def to_dict(self) -> dict:
        return {
            "coverage": round(self.coverage, 3),
            "matched_steps": self.matched_steps,
            "missing_steps": self.missing_steps,
            "extra_steps": self.extra_steps,
            "error_steps": self.error_steps,
            "structure_broken": self.structure_broken,
            "score": self.score,
            "total": self.total,
            "details": self.details,
        }


def diff_traces(standard: ReasoningTrace, student: ReasoningTrace) -> TraceDiff:
    """
    对比标准轨迹与学生轨迹，返回结构化差异。

    匹配策略:
      1. 按 op_type 精确匹配
      2. 按 ops_compatible() 宽松匹配
      3. 按 output_state 指纹匹配
    """
    std_ops = {s.step_id: s for s in standard.steps if s.step_type == StepType.OPERATION}
    stu_ops = {s.step_id: s for s in student.steps if s.step_type == StepType.OPERATION}

    matched = []
    missing = []
    used_student = set()

    std_list = list(std_ops.items())
    stu_list = list(stu_ops.items())

    for std_id, std_step in std_list:
        best_match = None
        best_score = 0.0

        for stu_id, stu_step in stu_list:
            if stu_id in used_student:
                continue

            score = 0.0
            if std_step.op_type == stu_step.op_type:
                score += 0.5
            elif ops_compatible(std_step.op_type, stu_step.op_type):
                score += 0.3

            if (std_step.operation.output_state.fingerprint
                    and std_step.operation.output_state.fingerprint == stu_step.operation.output_state.fingerprint):
                score += 0.3

            if std_step.label and std_step.label == stu_step.label:
                score += 0.2

            if score > best_score:
                best_score = score
                best_match = stu_id

        if best_match and best_score >= 0.3:
            matched.append((std_id, best_match))
            used_student.add(best_match)
        else:
            missing.append(std_id)

    extra = [sid for sid in stu_ops if sid not in used_student]
    error_steps = [s.step_id for s in student.steps if s.error.is_error]

    structure_broken = False
    for std_id, stu_id in matched:
        std_deps = set(standard.get_dependencies(std_id))
        stu_deps = set(student.get_dependencies(stu_id))
        if std_deps and not std_deps.intersection(stu_deps):
            structure_broken = True
            break

    score = 0.0
    for std_id, stu_id in matched:
        std_step = std_ops[std_id]
        stu_step = stu_ops[stu_id]
        if stu_step.is_correct:
            score += std_step.weight
        elif stu_step.error.severity == ErrorSeverity.MINOR:
            score += std_step.weight * 0.8

    details = []
    if missing:
        labels = [std_ops[sid].label for sid in missing if sid in std_ops]
        if labels:
            details.append(f"缺失步骤: {', '.join(labels)}")
    if structure_broken:
        details.append("解题逻辑链断裂")
    if error_steps:
        details.append(f"存在 {len(error_steps)} 个错误步骤")

    coverage = len(matched) / max(len(std_ops), 1)

    return TraceDiff(
        coverage=coverage,
        matched_steps=matched,
        missing_steps=missing,
        extra_steps=extra,
        error_steps=error_steps,
        structure_broken=structure_broken,
        score=round(score, 1),
        total=standard.total_score,
        details=details,
    )


def explain_diff(diff_result: TraceDiff) -> str:
    return "; ".join(diff_result.details) if diff_result.details else "解题过程完整"
