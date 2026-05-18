"""
RuntimeExecutor — 状态执行引擎

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  执行引擎将操作 (Op) 作用于 RuntimeState，产生新的 RuntimeState。

  执行流程:
    RuntimeState + Operation
        │
        ├── 1. Pre-check (约束冲突? 定义域合法?)
        │
        ├── 2. Execute (SymPy 符号计算 / 规则推导)
        │
        ├── 3. Post-update (更新约束图, 累积事实, 生成义务)
        │
        └── 4. Record (写入 execution_history)

  关键设计:
    - 每次执行产生新 RuntimeState (不可变)
    - 执行结果包含 ExecutionResult (成功/失败 + 诊断)
    - 支持 dry_run 模式 (只检查不执行)
    - 自动约束传播 (执行后自动 propagate)

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from runtime.state import (
    RuntimeState,
    MathFact,
    ProofObligation,
    DomainEntry,
    DomainKind,
    DomainRegistry,
    FactOrigin,
    ObligationStatus,
    RuntimeMetadata,
    ExecutionEvent,
    VerificationResult,
)
from math_ir import MathExpression, MathOperation, MathState, ExprCategory, Legality
from operations import Op, normalize_op, infer_op_from_text
from constraints.graph import ConstraintGraph, ConstraintStatus

try:
    import sympy as sp
    _HAS_SYMPY = True
except ImportError:
    sp = None
    _HAS_SYMPY = False


class ExecutionStatus(Enum):
    SUCCESS = auto()
    PARTIAL = auto()
    FAILED = auto()
    SKIPPED = auto()
    CONFLICT = auto()
    DOMAIN_VIOLATION = auto()


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    new_state: RuntimeState = field(default_factory=RuntimeState.empty)
    message: str = ""
    warnings: tuple[str, ...] = ()
    derived_facts: tuple[MathFact, ...] = ()
    new_obligations: tuple[ProofObligation, ...] = ()
    duration_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.status in (ExecutionStatus.SUCCESS, ExecutionStatus.PARTIAL)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def to_dict(self) -> dict:
        d = {"status": self.status.name, "message": self.message}
        if self.warnings:
            d["warnings"] = list(self.warnings)
        if self.derived_facts:
            d["derived_facts"] = [f.to_dict() for f in self.derived_facts]
        if self.new_obligations:
            d["new_obligations"] = [o.to_dict() for o in self.new_obligations]
        if self.duration_ms > 0:
            d["duration_ms"] = self.duration_ms
        return d


@dataclass
class ExecutionStep:
    step_id: str = ""
    operation: Op = Op.COMPUTE
    input_fingerprint: str = ""
    output_fingerprint: str = ""
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    message: str = ""
    timestamp: str = ""
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "operation": self.operation.value,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "status": self.status.name,
            "message": self.message,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


class RuntimeExecutor:
    """
    状态执行引擎 — 将操作作用于 RuntimeState。

    使用方式:
        executor = RuntimeExecutor()
        result = executor.execute(state, Op.DIFFERENTIATE, "x^2 + 1")
        if result.is_success:
            new_state = result.new_state
    """

    def __init__(self, auto_propagate: bool = True,
                 auto_conflict_detect: bool = True):
        self.auto_propagate = auto_propagate
        self.auto_conflict_detect = auto_conflict_detect
        self._step_counter = 0

    @staticmethod
    def _fact_deps(state: RuntimeState, expression: str = "",
                   max_deps: int = 5) -> tuple[str, ...]:
        deps = []
        for f in state.derived_facts:
            if expression and f.expression == expression:
                deps.append(f.fingerprint)
            elif not expression:
                deps.append(f.fingerprint)
            if len(deps) >= max_deps:
                break
        return tuple(deps)

    def execute(self, state: RuntimeState, op: Op,
                expression: str = "",
                target_variable: str = "",
                extra_constraints: tuple[str, ...] = (),
                dry_run: bool = False) -> ExecutionResult:
        start = time.time()
        self._step_counter += 1
        step_id = f"exec_{self._step_counter}"
        input_fp = state.fingerprint

        pre_check = self._pre_check(state, op, expression, target_variable)
        if not pre_check.is_success:
            return ExecutionResult(
                status=pre_check.status,
                new_state=state,
                message=pre_check.message,
                warnings=pre_check.warnings,
                duration_ms=(time.time() - start) * 1000,
            )

        if dry_run:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=state,
                message="dry_run: pre-check passed",
                duration_ms=(time.time() - start) * 1000,
            )

        exec_result = self._do_execute(state, op, expression, target_variable,
                                        extra_constraints, step_id)

        if self.auto_propagate and exec_result.is_success:
            exec_result = self._post_propagate(exec_result)

        if self.auto_conflict_detect and exec_result.is_success:
            exec_result = self._post_conflict_detect(exec_result)

        new_state = exec_result.new_state

        if exec_result.status == ExecutionStatus.SUCCESS:
            v_result = VerificationResult.PASS
        elif exec_result.status == ExecutionStatus.PARTIAL:
            v_result = VerificationResult.WARNING
        elif exec_result.status == ExecutionStatus.FAILED:
            v_result = VerificationResult.FAIL
        elif exec_result.status in (ExecutionStatus.CONFLICT, ExecutionStatus.DOMAIN_VIOLATION):
            v_result = VerificationResult.FAIL
        else:
            v_result = VerificationResult.SKIPPED

        new_constraints = []
        old_constraint_set = set(state.constraints.active_expressions())
        for c in new_state.constraints.active_expressions():
            if c not in old_constraint_set:
                new_constraints.append(c)

        new_obligation_texts = []
        old_obl_set = {o.proposition for o in state.obligations}
        for o in exec_result.new_obligations:
            if o.proposition not in old_obl_set:
                new_obligation_texts.append(o.proposition)
        for o in new_state.obligations:
            if o.proposition not in old_obl_set and o.proposition not in new_obligation_texts:
                new_obligation_texts.append(o.proposition)

        event = ExecutionEvent(
            operation=op.value,
            input_state_hash=input_fp,
            output_state_hash=new_state.fingerprint,
            verification_result=v_result,
            generated_constraints=tuple(new_constraints),
            generated_obligations=tuple(new_obligation_texts),
            duration_ms=(time.time() - start) * 1000,
            message=exec_result.message,
        )

        final_state = RuntimeState(
            expressions=new_state.expressions,
            constraints=new_state.constraints,
            assumptions=new_state.assumptions,
            domains=new_state.domains,
            obligations=new_state.obligations,
            derived_facts=new_state.derived_facts,
            execution_history=new_state.execution_history + (event,),
            metadata=RuntimeMetadata(
                parent_fingerprint=input_fp,
                source_operation=op.value,
                source_step_id=step_id,
            ),
        )

        return ExecutionResult(
            status=exec_result.status,
            new_state=final_state,
            message=exec_result.message,
            warnings=exec_result.warnings,
            derived_facts=exec_result.derived_facts,
            new_obligations=exec_result.new_obligations,
            duration_ms=(time.time() - start) * 1000,
        )

    def execute_sequence(self, state: RuntimeState,
                         operations: list[tuple[Op, str, str]]) -> list[ExecutionResult]:
        results = []
        current = state
        for op, expr, var in operations:
            result = self.execute(current, op, expr, var)
            results.append(result)
            if result.is_success:
                current = result.new_state
            else:
                break
        return results

    def _pre_check(self, state: RuntimeState, op: Op,
                   expression: str, target_variable: str) -> ExecutionResult:
        warnings = []

        if not expression and op not in (Op.COMPUTE, Op.DEFINE, Op.FINAL_ANSWER):
            return ExecutionResult(
                status=ExecutionStatus.SKIPPED,
                new_state=state,
                message=f"操作 {op.value} 需要表达式输入",
            )

        if target_variable:
            domain = state.domains.domain_of(target_variable)
            if domain == DomainKind.POSITIVE:
                pass
            elif domain == DomainKind.NONZERO:
                pass

        conflict_report = state.constraints.detect_conflicts()
        if conflict_report.has_conflict:
            warnings.append(f"存在约束冲突: {'; '.join(conflict_report.explanations)}")

        if warnings:
            return ExecutionResult(
                status=ExecutionStatus.CONFLICT,
                new_state=state,
                message="pre-check: 约束冲突",
                warnings=tuple(warnings),
            )

        return ExecutionResult(status=ExecutionStatus.SUCCESS, new_state=state)

    def _do_execute(self, state: RuntimeState, op: Op,
                    expression: str, target_variable: str,
                    extra_constraints: tuple[str, ...],
                    step_id: str) -> ExecutionResult:
        new_facts = []
        new_obligations = []
        warnings = []
        new_state = state

        if op == Op.DIFFERENTIATE:
            result = self._exec_differentiate(state, expression, target_variable)
        elif op == Op.INTEGRATE:
            result = self._exec_integrate(state, expression, target_variable)
        elif op == Op.COMPUTE_LIMIT:
            result = self._exec_limit(state, expression, target_variable)
        elif op == Op.SIMPLIFY:
            result = self._exec_simplify(state, expression)
        elif op == Op.EXPAND:
            result = self._exec_expand(state, expression)
        elif op == Op.FACTOR:
            result = self._exec_factor(state, expression)
        elif op == Op.SUBSTITUTE:
            result = self._exec_substitute(state, expression, target_variable)
        elif op == Op.SOLVE_EQUATION:
            result = self._exec_solve(state, expression)
        elif op == Op.APPLY_THEOREM:
            result = self._exec_apply_theorem(state, expression)
        else:
            result = self._exec_generic(state, op, expression)

        return result

    def _exec_differentiate(self, state: RuntimeState, expression: str,
                            variable: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"d/d{variable}({expression})")),
                message="SymPy 不可用，仅记录操作",
                derived_facts=(MathFact(
                    expression=f"d/d{variable}({expression})",
                    origin=FactOrigin.COMPUTED,
                    source_operation="differentiate",
                    confidence=0.5,
                    dependencies=self._fact_deps(state, expression),
                ),),
            )

        try:
            from canonicalization.expression import _preprocess
            preprocessed = _preprocess(expression)
            expr = sp.sympify(preprocessed, evaluate=True)
            var = sp.Symbol(variable)
            result = sp.diff(expr, var)
            result_latex = str(result)

            new_expr = MathExpression(latex=result_latex, category=ExprCategory.DERIVATIVE)
            new_state = state.with_expression(new_expr)

            new_state = new_state.with_derived_fact(MathFact(
                expression=f"d/d{variable}({expression}) = {result_latex}",
                origin=FactOrigin.COMPUTED,
                source_operation="differentiate",
                confidence=1.0,
                justification="symbolic_differentiation",
                dependencies=self._fact_deps(state, expression),
            ))

            obligations = []
            if "log" in expression or "ln" in expression:
                obligations.append(ProofObligation(
                    proposition=f"{variable} > 0 (对数定义域)",
                    status=ObligationStatus.PENDING,
                    source_step="differentiate",
                    reason="对数函数要求参数 > 0",
                    priority=5,
                ))
                new_state = new_state.with_obligation(obligations[-1])

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"求导成功: d/d{variable}({expression}) = {result_latex}",
                derived_facts=new_state.derived_facts[len(state.derived_facts):],
                new_obligations=tuple(obligations),
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"求导失败: {e}",
            )

    def _exec_integrate(self, state: RuntimeState, expression: str,
                        variable: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"∫{expression}d{variable}")),
                message="SymPy 不可用，仅记录操作",
            )

        try:
            from canonicalization.expression import _preprocess
            preprocessed = _preprocess(expression)
            expr = sp.sympify(preprocessed, evaluate=True)
            var = sp.Symbol(variable)
            result = sp.integrate(expr, var)
            result_latex = str(result)

            new_expr = MathExpression(latex=result_latex, category=ExprCategory.INTEGRAL)
            new_state = state.with_expression(new_expr)
            new_state = new_state.with_derived_fact(MathFact(
                expression=f"∫{expression}d{variable} = {result_latex} + C",
                origin=FactOrigin.COMPUTED,
                source_operation="integrate",
                confidence=1.0,
                justification="symbolic_integration",
                dependencies=self._fact_deps(state, expression),
            ))

            obligations = []
            obligations.append(ProofObligation(
                proposition="验证积分结果 (求导还原)",
                status=ObligationStatus.PENDING,
                source_step="integrate",
                reason="积分结果应可求导还原",
                priority=3,
            ))
            new_state = new_state.with_obligation(obligations[-1])

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"积分成功: ∫{expression}d{variable} = {result_latex} + C",
                new_obligations=tuple(obligations),
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"积分失败: {e}",
            )

    def _exec_limit(self, state: RuntimeState, expression: str,
                    info: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"lim({expression})")),
                message="SymPy 不可用，仅记录操作",
            )

        try:
            import re
            m = re.match(r'(.+?)\s*(?:->|→|approaches)\s*(.+)', info)
            if m:
                expr_text, point_text = m.group(1).strip(), m.group(2).strip()
            else:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    new_state=state,
                    message="极限格式: 'expression -> point'",
                )

            from canonicalization.expression import _preprocess
            expr = sp.sympify(_preprocess(expr_text), evaluate=True)
            point = sp.sympify(_preprocess(point_text), evaluate=True)
            var = list(expr.free_symbols)[0] if expr.free_symbols else sp.Symbol('x')
            result = sp.limit(expr, var, point)
            result_latex = str(result)

            new_expr = MathExpression(latex=result_latex, category=ExprCategory.LIMIT)
            new_state = state.with_expression(new_expr)
            new_state = new_state.with_derived_fact(MathFact(
                expression=f"lim({expr_text} → {point_text}) = {result_latex}",
                origin=FactOrigin.COMPUTED,
                source_operation="compute_limit",
                confidence=1.0,
                dependencies=self._fact_deps(state, expr_text),
            ))

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"极限: lim({expr_text} → {point_text}) = {result_latex}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"极限计算失败: {e}",
            )

    def _exec_simplify(self, state: RuntimeState, expression: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"simplify({expression})")),
                message="SymPy 不可用",
            )
        try:
            from canonicalization.expression import _preprocess
            expr = sp.sympify(_preprocess(expression), evaluate=True)
            result = sp.simplify(expr)
            result_latex = str(result)
            new_expr = MathExpression(latex=result_latex)
            new_state = state.with_expression(new_expr)
            new_state = new_state.with_derived_fact(MathFact(
                expression=f"simplify({expression}) = {result_latex}",
                origin=FactOrigin.COMPUTED,
                source_operation="simplify",
                confidence=1.0,
                dependencies=self._fact_deps(state, expression),
            ))
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"化简: {expression} = {result_latex}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"化简失败: {e}",
            )

    def _exec_expand(self, state: RuntimeState, expression: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"expand({expression})")),
                message="SymPy 不可用",
            )
        try:
            from canonicalization.expression import _preprocess
            expr = sp.sympify(_preprocess(expression), evaluate=True)
            result = sp.expand(expr)
            result_latex = str(result)
            new_expr = MathExpression(latex=result_latex)
            new_state = state.with_expression(new_expr)
            new_state = new_state.with_derived_fact(MathFact(
                expression=f"expand({expression}) = {result_latex}",
                origin=FactOrigin.COMPUTED,
                source_operation="expand",
                confidence=1.0,
                dependencies=self._fact_deps(state, expression),
            ))
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"展开: {expression} = {result_latex}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"展开失败: {e}",
            )

    def _exec_factor(self, state: RuntimeState, expression: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"factor({expression})")),
                message="SymPy 不可用",
            )
        try:
            from canonicalization.expression import _preprocess
            expr = sp.sympify(_preprocess(expression), evaluate=True)
            result = sp.factor(expr)
            result_latex = str(result)
            new_expr = MathExpression(latex=result_latex)
            new_state = state.with_expression(new_expr)
            new_state = new_state.with_derived_fact(MathFact(
                expression=f"factor({expression}) = {result_latex}",
                origin=FactOrigin.COMPUTED,
                source_operation="factor",
                confidence=1.0,
                dependencies=self._fact_deps(state, expression),
            ))
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"因式分解: {expression} = {result_latex}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"因式分解失败: {e}",
            )

    def _exec_substitute(self, state: RuntimeState, expression: str,
                         substitution: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"subst({expression})")),
                message="SymPy 不可用",
            )
        try:
            import re
            m = re.match(r'(\w+)\s*=\s*(.+)', substitution)
            if not m:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    new_state=state,
                    message="代入格式: 'var=value'",
                )
            var_name, val_text = m.group(1), m.group(2)
            from canonicalization.expression import _preprocess
            expr = sp.sympify(_preprocess(expression), evaluate=True)
            val = sp.sympify(_preprocess(val_text), evaluate=True)
            result = expr.subs(sp.Symbol(var_name), val)
            result_latex = str(result)
            new_expr = MathExpression(latex=result_latex)
            new_state = state.with_expression(new_expr)
            new_state = new_state.with_derived_fact(MathFact(
                expression=f"subst({expression}, {substitution}) = {result_latex}",
                origin=FactOrigin.COMPUTED,
                source_operation="substitute",
                confidence=1.0,
                dependencies=self._fact_deps(state, expression),
            ))
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"代入: {expression}[{substitution}] = {result_latex}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"代入失败: {e}",
            )

    def _exec_solve(self, state: RuntimeState, expression: str) -> ExecutionResult:
        if not _HAS_SYMPY:
            return ExecutionResult(
                status=ExecutionStatus.PARTIAL,
                new_state=state.with_expression(MathExpression.from_latex(f"solve({expression})")),
                message="SymPy 不可用",
            )
        try:
            from canonicalization.expression import _preprocess
            expr = sp.sympify(_preprocess(expression), evaluate=True)
            vars_list = list(expr.free_symbols)
            if not vars_list:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    new_state=state,
                    message="无变量可解",
                )
            solutions = sp.solve(expr, vars_list)
            result_latex = str(solutions)
            new_expr = MathExpression(latex=result_latex)
            new_state = state.with_expression(new_expr)
            new_state = new_state.with_derived_fact(MathFact(
                expression=f"solve({expression}) = {result_latex}",
                origin=FactOrigin.COMPUTED,
                source_operation="solve_equation",
                confidence=1.0,
                dependencies=self._fact_deps(state, expression),
            ))
            new_state = new_state.with_obligation(ProofObligation(
                proposition="验证解的正确性 (代入原方程)",
                status=ObligationStatus.PENDING,
                source_step="solve_equation",
                reason="方程解应代入验证",
                priority=3,
            ))
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                new_state=new_state,
                message=f"求解: {expression} = {result_latex}",
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                new_state=state,
                message=f"求解失败: {e}",
            )

    def _exec_apply_theorem(self, state: RuntimeState,
                            theorem_name: str) -> ExecutionResult:
        new_state = state.with_obligation(ProofObligation(
            proposition=f"验证 {theorem_name} 的前提条件",
            status=ObligationStatus.PENDING,
            source_step="apply_theorem",
            reason="应用定理前需验证前提条件",
            priority=7,
        ))
        new_state = new_state.with_derived_fact(MathFact(
            expression=f"应用定理: {theorem_name}",
            origin=FactOrigin.ASSUMED,
            source_operation="apply_theorem",
            confidence=0.8,
            justification=f"theorem_application:{theorem_name}",
            dependencies=self._fact_deps(state, theorem_name),
        ))
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            new_state=new_state,
            message=f"应用定理: {theorem_name} (需验证前提)",
        )

    def _exec_generic(self, state: RuntimeState, op: Op,
                      expression: str) -> ExecutionResult:
        new_expr = MathExpression.from_latex(expression) if expression else MathExpression()
        new_state = state.with_expression(new_expr)
        new_state = new_state.with_derived_fact(MathFact(
            expression=expression,
            origin=FactOrigin.COMPUTED,
            source_operation=op.value,
            confidence=0.7,
            justification=f"generic_op:{op.value}",
            dependencies=self._fact_deps(state, expression),
        ))
        return ExecutionResult(
            status=ExecutionStatus.PARTIAL,
            new_state=new_state,
            message=f"通用执行: {op.value}({expression})",
        )

    def _post_propagate(self, result: ExecutionResult) -> ExecutionResult:
        propagated = result.new_state.with_constraints_propagated()
        new_facts = propagated.derived_facts[len(result.new_state.derived_facts):]
        return ExecutionResult(
            status=result.status,
            new_state=propagated,
            message=result.message,
            warnings=result.warnings,
            derived_facts=result.derived_facts + tuple(new_facts),
            new_obligations=result.new_obligations,
            duration_ms=result.duration_ms,
        )

    def _post_conflict_detect(self, result: ExecutionResult) -> ExecutionResult:
        conflict = result.new_state.constraints.detect_conflicts()
        if not conflict.has_conflict:
            return result
        warnings = list(result.warnings) + [
            f"约束冲突: {exp}" for exp in conflict.explanations
        ]
        return ExecutionResult(
            status=ExecutionStatus.CONFLICT if result.status == ExecutionStatus.SUCCESS else result.status,
            new_state=result.new_state,
            message=result.message + " [冲突检测: 发现约束矛盾]",
            warnings=tuple(warnings),
            derived_facts=result.derived_facts,
            new_obligations=result.new_obligations,
            duration_ms=result.duration_ms,
        )
