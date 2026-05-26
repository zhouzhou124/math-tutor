"""
Unified Semantic Output Layer — Formal Mathematical Runtime
============================================================

This module defines the SINGLE output contract for ALL agents.
LLMs no longer generate "answer text" — they generate reasoning semantic structure.

Architecture:
  CanonicalIR (unified agent output)
      ↓
  ProofTrace (connected reasoning steps with justifications)
      ↓
  StructuredSolution (renderable format, existing pipeline)

The key insight: agent differences are in WHAT they fill in (solver fills all
steps, grader adds judgments, diagnosis adds error analysis), not in the FORMAT
they use. All agents share the same schema.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from enum import Enum
import re


# ═══════════════════════════════════════════════
# 1. Math Operation — the atomic transformations
# ═══════════════════════════════════════════════

class MathOperation(str, Enum):
    """Atomic mathematical operations — the only allowed step types."""
    CLASSIFY = "classify"
    RECALL = "recall"
    SUBSTITUTE = "substitute"
    SIMPLIFY = "simplify"
    EXPAND = "expand"
    FACTOR = "factor"
    DIFFERENTIATE = "differentiate"
    INTEGRATE = "integrate"
    SOLVE = "solve"
    EVALUATE = "evaluate"
    APPLY_THEOREM = "apply_theorem"
    TRANSFORM = "transform"
    CONCLUDE = "conclude"
    CHECK = "check"

    @property
    def label_cn(self) -> str:
        """Chinese label for rendering."""
        return _OP_CN.get(self.value, self.value)

    @property
    def color(self) -> str:
        """Hex color for rendering."""
        return _OP_COLOR.get(self.value, "#6b7280")


_OP_CN = {
    "classify": "识别题型", "recall": "回忆定理", "substitute": "代入",
    "simplify": "化简", "expand": "展开", "factor": "因式分解",
    "differentiate": "求导", "integrate": "积分", "solve": "求解",
    "evaluate": "计算", "apply_theorem": "应用定理", "transform": "变换",
    "conclude": "结论", "check": "验证",
}
_OP_COLOR = {
    "classify": "#6b7280", "recall": "#2563eb", "substitute": "#7c3aed",
    "simplify": "#059669", "expand": "#059669", "factor": "#059669",
    "differentiate": "#d97706", "integrate": "#d97706", "solve": "#dc2626",
    "evaluate": "#dc2626", "apply_theorem": "#2563eb", "transform": "#7c3aed",
    "conclude": "#0891b2", "check": "#0891b2",
}


# ═══════════════════════════════════════════════
# 2. Judgment — grader annotation
# ═══════════════════════════════════════════════

Judgment = Literal["correct", "partial", "wrong"]


# ═══════════════════════════════════════════════
# 3. ProofStep — one atomic reasoning step
# ═══════════════════════════════════════════════

class ProofStep(BaseModel):
    """A single atomic reasoning step in the proof trace.

    This is NOT free-form text. It is a structured mathematical operation
    with precisely defined input/output states and a justification.
    """
    id: str = Field(..., description="unique step id, e.g. s1, s2")
    operation: MathOperation = Field(..., description="the mathematical operation performed")
    input_state: str = Field(
        default="",
        description="LaTeX: the mathematical state BEFORE this step (can be empty for first step)"
    )
    output_state: str = Field(..., description="LaTeX: the mathematical state AFTER this step")
    justification: str = Field(
        ..., min_length=1,
        description="Chinese: why this step is mathematically valid (theorem name, rule applied)"
    )
    label: str = Field(default="", description="Chinese: human-readable step name")

    # ── Agent-specific annotations (filled by grader / diagnosis) ──
    judgment: Optional[Judgment] = Field(
        default=None, description="grader: correctness judgment"
    )
    score: Optional[float] = Field(
        default=None, ge=0, description="grader: score awarded for this step"
    )
    max_score: Optional[float] = Field(
        default=None, ge=0, description="grader: maximum score for this step"
    )
    error_analysis: Optional[str] = Field(
        default=None, description="diagnosis: why this step is wrong (if applicable)"
    )
    matched_canonical_step: Optional[str] = Field(
        default=None, description="grader: which canonical step this corresponds to"
    )

    model_config = {"extra": "ignore"}


# ═══════════════════════════════════════════════
# 4. ProofEdge — connection between steps
# ═══════════════════════════════════════════════

class ProofEdge(BaseModel):
    """Directed edge in the proof DAG."""
    source: str = Field(..., description="source step id")
    target: str = Field(..., description="target step id")
    relation: Literal["next", "depends_on", "alternative"] = "next"

    model_config = {"extra": "ignore"}


# ═══════════════════════════════════════════════
# 5. ProofTrace — the complete reasoning chain
# ═══════════════════════════════════════════════

class ProofTrace(BaseModel):
    """The complete reasoning chain — a sequence of connected proof steps.

    This is the semantic core. It captures WHAT was done (operation),
    FROM what (input_state), TO what (output_state), and WHY (justification).
    """
    steps: list[ProofStep] = Field(..., min_length=1)
    edges: list[ProofEdge] = Field(default_factory=list)
    final_answer: str = Field(
        default="", description="LaTeX: the final answer expression"
    )

    @field_validator("edges", mode="after")
    @classmethod
    def auto_edges(cls, v: list[ProofEdge], info) -> list[ProofEdge]:
        """If no edges provided, auto-generate linear chain from steps."""
        if not v:
            steps_data = info.data.get("steps", [])
            if len(steps_data) > 1:
                result = []
                for i in range(len(steps_data) - 1):
                    s0 = steps_data[i]
                    s1 = steps_data[i + 1]
                    sid0 = s0.id if isinstance(s0, ProofStep) else s0.get("id", f"s{i+1}")
                    sid1 = s1.id if isinstance(s1, ProofStep) else s1.get("id", f"s{i+2}")
                    result.append(ProofEdge(source=sid0, target=sid1))
                return result
        return v

    def is_linear(self) -> bool:
        """Check if the trace is a simple linear chain (most common)."""
        if not self.edges:
            return True
        return all(e.relation == "next" for e in self.edges)

    def get_step(self, step_id: str) -> ProofStep | None:
        """Look up a step by id."""
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    model_config = {"extra": "ignore"}


# ═══════════════════════════════════════════════
# 6. CanonicalIR — unified agent output
# ═══════════════════════════════════════════════

class QuestionRef(BaseModel):
    """Reference to the question being solved/graded/diagnosed."""
    text: str = Field(default="", description="full question text in LaTeX")
    math_type: str = "数学一"
    question_type: str = "解答题"
    knowledge_points: list[str] = Field(default_factory=list)
    difficulty: str = "中等"
    total_score: float = 10.0

    model_config = {"extra": "ignore"}


class CanonicalIR(BaseModel):
    """THE unified output format for ALL agents.

    This is the single source of truth. Every agent — solver, grader, diagnosis —
    outputs this exact schema. The difference is which fields they populate:

    Solver:    fills proof_trace (all steps, all operations), question, metadata
    Grader:    fills proof_trace.steps[].judgment, .score, .max_score
    Diagnosis: fills proof_trace.steps[].error_analysis, metadata.error_patterns
    """
    agent: Literal["solver", "grader", "diagnosis"] = "solver"
    question: QuestionRef = Field(default_factory=QuestionRef)
    proof_trace: ProofTrace
    metadata: dict = Field(
        default_factory=dict,
        description="agent-specific metadata (knowledge_points, common_mistakes, error_patterns, recommendations)"
    )

    model_config = {"extra": "ignore"}


# ═══════════════════════════════════════════════
# 7. Validation + Repair
# ═══════════════════════════════════════════════

_FORMULA_FIELD_NAMES = {
    "formula", "latex", "input_state", "output_state", "final_answer",
}
_DERIVATION_MARKERS = (
    "因为", "由于", "由", "利用", "根据", "代入", "化简", "整理", "解得",
    "可得", "得到", "推出", "所以", "故", "从而", "递推", "初值",
    "特征方程", "定理", "性质", "等式", "展开", "积分", "求导", "计算",
)
_CONCLUSION_ONLY_MARKERS = (
    "最终答案", "最终结论", "综上", "证毕", "故答案", "故选", "得到结论",
    "答案为", "结论",
)


def _explicit_subparts_from_question_text(question: str) -> list[str]:
    """Return explicit subpart labels only; never infer from formulas or steps."""
    qtext = str(question or "")
    patterns = [
        r"(?m)^\s*[（(]\s*([1-9])\s*[)）]\s*",
        r"第\s*[（(]\s*([1-9])\s*[)）]\s*问",
        r"第\s*[（]\s*([1-9])\s*[）]\s*问",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, qtext))
    unique: list[str] = []
    for n in found:
        if n not in unique:
            unique.append(n)
    return unique


def _iter_formula_fields(obj, path: str = ""):
    """Yield formula-like fields from nested CanonicalIR dictionaries."""
    if isinstance(obj, dict):
        if str(obj.get("type") or "").lower() == "latex" and isinstance(obj.get("content"), str):
            yield f"{path}.content" if path else "content", obj.get("content") or ""
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else str(key)
            key_l = str(key).lower()
            if isinstance(value, str) and (
                key_l in _FORMULA_FIELD_NAMES
                or "formula" in key_l
                or "latex" in key_l
            ):
                yield child_path, value
            else:
                yield from _iter_formula_fields(value, child_path)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from _iter_formula_fields(value, f"{path}[{idx}]")


def canonical_ir_has_required_fields(ir) -> bool:
    """Strict structural check for the CanonicalIR fields we rely on."""
    if not isinstance(ir, dict):
        return False
    trace = ir.get("proof_trace")
    if not isinstance(trace, dict):
        return False
    steps = trace.get("steps")
    if not isinstance(steps, list) or not steps:
        return False
    for step in steps:
        if not isinstance(step, dict):
            return False
        for key in ("id", "operation", "output_state", "justification"):
            if not str(step.get(key) or "").strip():
                return False
    return True


def canonical_ir_formulas_are_clean(ir) -> bool:
    """Reject Markdown/delimiter/control pollution in formula-like fields."""
    if not isinstance(ir, dict):
        return False
    bad_patterns = [
        r"(?<!\\)\$",
        r"##",
        r"\\u0000",
        "\x00",
        "\ufffd",
        r"\\to\s*\$\s*\\infty\s*\$",
        r"\$\s*\\begin\{aligned\}\s*\$",
        r"\$\s*\\end\{aligned\}\s*\$",
    ]
    for _path, value in _iter_formula_fields(ir):
        text = str(value or "")
        if any(re.search(pattern, text) for pattern in bad_patterns):
            return False
    return True


def canonical_ir_has_derivation_depth(ir) -> bool:
    """Each proof step must include substantive derivation text."""
    if not isinstance(ir, dict):
        return False
    steps = ((ir.get("proof_trace") or {}).get("steps") or [])
    if not isinstance(steps, list) or not steps:
        return False
    for step in steps:
        if not isinstance(step, dict):
            return False
        justification = str(step.get("justification") or "").strip()
        compact = "".join(justification.split())
        if len(compact) < 4 or compact == "(auto-generated)":
            return False
        conclusion_only = any(marker in justification for marker in _CONCLUSION_ONLY_MARKERS)
        has_reason = any(marker in justification for marker in _DERIVATION_MARKERS)
        has_state = bool(str(step.get("input_state") or "").strip() or str(step.get("output_state") or "").strip())
        if conclusion_only and not has_reason:
            return False
        if not has_reason and (len(compact) < 12 or not has_state):
            return False
    return True


def canonical_ir_covers_subparts(ir, question) -> bool:
    """Check explicit question subparts only; ignore matrix/formula numbers."""
    if not isinstance(ir, dict):
        return False
    if isinstance(question, dict):
        qtext = str(question.get("question") or question.get("text") or "")
    else:
        qtext = str(question or "")
    subparts = _explicit_subparts_from_question_text(qtext)
    if len(subparts) < 2:
        return True
    steps = ((ir.get("proof_trace") or {}).get("steps") or [])
    haystack = "\n".join(
        "\n".join(
            str(step.get(key) or "")
            for key in ("label", "justification", "input_state", "output_state")
        )
        for step in steps
        if isinstance(step, dict)
    )
    compact = "".join(haystack.split())
    missing = []
    for n in subparts:
        markers = [f"({n})", f"（{n}）", f"第({n})问", f"第（{n}）问", f"第{n}问"]
        if not any(marker in compact for marker in markers):
            missing.append(n)
    return not missing


def _canonical_ir_strict_errors(ir, question=None) -> list[str]:
    errors: list[str] = []
    if not canonical_ir_has_required_fields(ir):
        errors.append("canonical_ir_missing_required_fields")
    if not canonical_ir_formulas_are_clean(ir):
        errors.append("canonical_ir_formula_not_clean")
    if not canonical_ir_has_derivation_depth(ir):
        errors.append("canonical_ir_missing_derivation_depth")
    if not canonical_ir_covers_subparts(ir, question):
        errors.append("canonical_ir_missing_subparts")
    return errors


def validate_canonical_ir(data: dict) -> tuple[CanonicalIR | None, list[str], list[str]]:
    """Validate + repair a CanonicalIR dict from LLM output.

    Returns (model, errors, repair_log).
    """
    repairs = []

    if not isinstance(data, dict):
        return None, ["CanonicalIR must be a dict"], repairs

    # Drop extra root fields
    allowed_root = {"agent", "question", "proof_trace", "metadata"}
    extra = [k for k in data if k not in allowed_root]
    if extra:
        repairs.append(f"dropped extra root fields: {extra}")
        data = {k: v for k, v in data.items() if k in allowed_root}

    # Ensure proof_trace exists
    if "proof_trace" not in data:
        return None, ["missing required field: proof_trace"], repairs
    if not isinstance(data["proof_trace"], dict):
        return None, ["proof_trace must be a dict"], repairs

    trace = data["proof_trace"]

    # Ensure steps exist
    if "steps" not in trace:
        return None, ["proof_trace.steps is required"], repairs
    if not isinstance(trace["steps"], list):
        return None, ["proof_trace.steps must be a list"], repairs

    # Fix each step
    for i, step in enumerate(trace["steps"]):
        if not isinstance(step, dict):
            repairs.append(f"steps[{i}]: replaced non-dict")
            trace["steps"][i] = {
                "id": f"s{i+1}", "operation": "simplify",
                "input_state": "", "output_state": "",
                "justification": "(auto-generated)",
            }
            continue

        # Auto-fill id
        if not step.get("id"):
            step["id"] = f"s{i+1}"
            repairs.append(f"steps[{i}]: auto-filled id")

        # Fix operation
        valid_ops = {o.value for o in MathOperation}
        if step.get("operation", "") not in valid_ops:
            old = step.get("operation", "missing")
            step["operation"] = "simplify"
            repairs.append(f"steps[{i}]: operation '{old}' -> 'simplify'")

        # Auto-fill missing output_state (required)
        if not step.get("output_state"):
            step["output_state"] = ""
            repairs.append(f"steps[{i}]: auto-filled empty output_state")

        # Auto-fill missing input_state: infer from previous step
        if not step.get("input_state", "").strip() and i > 0:
            prev = trace["steps"][i - 1]
            prev_out = prev.get("output_state", "") if isinstance(prev, dict) else ""
            if prev_out and prev_out.strip():
                step["input_state"] = prev_out
                repairs.append(f"steps[{i}]: inferred input_state from steps[{i-1}].output_state")

        # Auto-fill missing justification
        if not step.get("justification", "").strip():
            step["justification"] = "(auto-generated)"
            repairs.append(f"steps[{i}]: auto-filled empty justification")

        if not step.get("label"):
            step["label"] = f"步骤{i+1}"

        # Drop extra fields
        allowed_step = {"id", "operation", "input_state", "output_state",
                        "justification", "label",
                        "judgment", "score", "max_score",
                        "error_analysis", "matched_canonical_step"}
        extra_step = [k for k in step if k not in allowed_step]
        if extra_step:
            repairs.append(f"steps[{i}]: dropped extra: {extra_step}")
            for k in extra_step:
                step.pop(k, None)

    # Auto-generate edges if missing
    if "edges" not in trace:
        trace["edges"] = []

    try:
        model = CanonicalIR(**data)
        strict_errors = _canonical_ir_strict_errors(data, data.get("question"))
        if strict_errors:
            return None, strict_errors, repairs
        return model, [], repairs
    except Exception as e:
        return None, [str(e)], repairs


# ═══════════════════════════════════════════════
# 8. Conversion: ProofTrace → StructuredSolution
# ═══════════════════════════════════════════════

def proof_trace_to_structured(trace: ProofTrace) -> dict:
    """Convert a ProofTrace to a StructuredSolution dict for rendering.

    Each ProofStep becomes a MathStep with:
      - text block: label + justification (Chinese)
      - latex block: input_state → output_state (math)
    """
    steps = []
    import re as _re

    def _clean_latex(s: str) -> str:
        """Strip $ delimiters and fix common LLM artifacts without breaking LaTeX structure."""
        s = s.strip()
        if s.startswith("$$") and s.endswith("$$"):
            s = s[2:-2].strip()
        elif s.startswith("$") and s.endswith("$"):
            s = s[1:-1].strip()
        # Remove stray $ inside the expression
        s = _re.sub(r'(?<!\\)\$', '', s)
        # Replace JSON literal \n with space, but preserve LaTeX \\ (line breaks)
        # Strategy: protect \\ first, then collapse \n, then restore \\
        s = s.replace('\\\\', '\x00BSBS\x00')
        s = _re.sub(r'\s*\n\s*', ' ', s)
        s = s.replace('\x00BSBS\x00', '\\\\')
        # Collapse multiple spaces/tabs (not newlines)
        s = _re.sub(r'[ \t]+', ' ', s)
        return s.strip()

    _has_chinese = _re.compile(r'[一-鿿]')

    def _is_pure_math(s: str) -> bool:
        """Check if string is pure LaTeX (no Chinese characters)."""
        return not bool(_has_chinese.search(s)) if s else True

    for ps in trace.steps:
        blocks = []

        # Normalize operation to value string
        op_value = ps.operation.value if isinstance(ps.operation, MathOperation) else str(ps.operation)
        op_label = MathOperation(op_value).label_cn if op_value else ""

        # Justification as text block (strip redundant op_label prefix)
        just = ps.justification or ""
        if op_label and just.startswith(op_label + "："):
            just = just[len(op_label) + 1:]
        elif op_label and just.startswith(op_label + ":"):
            just = just[len(op_label) + 1:]
        if just:
            if ps.judgment and ps.judgment != "correct":
                judgment_cn = {"correct": "✓", "partial": "△", "wrong": "✗"}
                just += f" 【{judgment_cn.get(ps.judgment, ps.judgment)}】"
            blocks.append({"type": "text", "content": just})

        # Input/output states: separate Chinese text from pure LaTeX
        inp = _clean_latex(ps.input_state) if ps.input_state else ""
        out = _clean_latex(ps.output_state) if ps.output_state else ""

        if not _is_pure_math(inp) and inp:
            blocks.append({"type": "text", "content": inp})
            inp = ""
        if not _is_pure_math(out) and out:
            blocks.append({"type": "text", "content": out})
            out = ""

        # Pure LaTeX: show only the key result (output), not the full chain
        # The justification text already explains the transformation
        if out:
            # Short expressions → inline, long/complex → block
            is_long = len(out) > 60 or '\n' in out or '\\\\' in out
            blocks.append({
                "type": "latex",
                "content": out,
                "display": "block" if is_long else "inline",
            })
        elif inp and _is_pure_math(inp):
            blocks.append({
                "type": "latex",
                "content": inp,
                "display": "block" if len(inp) > 60 else "inline",
            })

        # Error analysis
        if ps.error_analysis:
            blocks.append({"type": "text", "content": f"错因分析：{ps.error_analysis}"})

        steps.append({
            "label": ps.label or ps.id,
            "blocks": blocks,
            "operation": op_value,
        })

    final_answer = None
    if trace.final_answer:
        final_answer = {"type": "latex", "content": _clean_latex(trace.final_answer)}

    return {
        "steps": steps,
        "final_answer": final_answer,
        "metadata": {},
    }


# ═══════════════════════════════════════════════
# 9. End-to-end pipeline
# ═══════════════════════════════════════════════

def canonical_to_rendered(canonical_dict: dict) -> dict:
    """Full pipeline: LLM JSON dict → CanonicalIR → ProofTrace → StructuredSolution.

    Returns the StructuredSolution dict ready for render_structured().
    """
    model, errors, repairs = validate_canonical_ir(canonical_dict)
    if errors:
        raise ValueError(f"CanonicalIR validation failed: {errors}")
    return proof_trace_to_structured(model.proof_trace)
