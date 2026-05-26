"""CanonicalIR to Markdown compiler.

This is intentionally test-only infrastructure for P29-3. It does not plug into
the generation, quality, cache, or UI paths.
"""

from __future__ import annotations

import re
from typing import Any


class SolutionMarkdownCompileError(ValueError):
    """Raised when CanonicalIR cannot be compiled safely."""


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_BAD_FORMULA_RE = re.compile(
    r"(?<!\\)\$|##|\\u0000|\x00|\ufffd|\\to\s*\$\s*\\infty\s*\$|"
    r"\$\s*\\begin\{aligned\}\s*\$|\$\s*\\end\{aligned\}\s*\$"
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _append_text(lines: list[str], value: Any) -> None:
    text = _text(value)
    if text:
        lines.extend([text, ""])


def _validate_formula(value: Any, *, path: str = "formula") -> str:
    formula = _text(value)
    if not formula:
        return ""
    if _BAD_FORMULA_RE.search(formula):
        raise SolutionMarkdownCompileError(f"{path} contains unsafe formula markup")
    if _CJK_RE.search(formula):
        raise SolutionMarkdownCompileError(f"{path} contains Chinese text")
    return formula


def _append_formula(lines: list[str], value: Any, *, display: bool, path: str) -> None:
    formula = _validate_formula(value, path=path)
    if not formula:
        return
    if display:
        lines.extend(["$$", formula, "$$", ""])
    else:
        lines.extend([f"${formula}$", ""])


def _formula_from_obj(obj: Any, *, default_display: bool = True) -> tuple[str, bool] | None:
    if isinstance(obj, str):
        return obj, default_display
    if not isinstance(obj, dict):
        return None
    for key in ("latex", "formula", "content", "value"):
        if obj.get(key):
            display = obj.get("display", default_display)
            if isinstance(display, str):
                display = display.lower() not in {"inline", "false", "0", "no"}
            return str(obj.get(key)), bool(display)
    return None


def _append_formula_list(lines: list[str], values: Any, *, path: str, default_display: bool = True) -> None:
    if not values:
        return
    if not isinstance(values, list):
        values = [values]
    for idx, item in enumerate(values):
        parsed = _formula_from_obj(item, default_display=default_display)
        if not parsed:
            continue
        formula, display = parsed
        _append_formula(lines, formula, display=display, path=f"{path}[{idx}]")


def _step_title(step: dict[str, Any], index: int) -> str:
    label = _text(step.get("label") or step.get("title") or step.get("name"))
    if label:
        return label if label.startswith("步骤") else f"步骤{index}：{label}"
    return f"步骤{index}"


def _compile_step(step: dict[str, Any], index: int, lines: list[str]) -> None:
    lines.extend([f"### {_step_title(step, index)}", ""])

    _append_text(lines, step.get("body") or step.get("body_markdown"))
    _append_text(lines, step.get("derivation") or step.get("derivation_markdown"))
    _append_text(lines, step.get("text"))

    input_state = _text(step.get("input_state"))
    output_state = _text(step.get("output_state"))
    if input_state and output_state:
        inp = _validate_formula(input_state, path=f"steps[{index}].input_state")
        out = _validate_formula(output_state, path=f"steps[{index}].output_state")
        _append_formula(lines, rf"{inp} \Rightarrow {out}", display=True, path=f"steps[{index}].transition")
    elif output_state:
        _append_formula(lines, output_state, display=True, path=f"steps[{index}].output_state")
    elif input_state:
        _append_formula(lines, input_state, display=True, path=f"steps[{index}].input_state")

    _append_formula_list(lines, step.get("display_formulas"), path=f"steps[{index}].display_formulas")
    _append_formula_list(lines, step.get("formulas"), path=f"steps[{index}].formulas")
    _append_formula_list(
        lines,
        step.get("inline_formulas"),
        path=f"steps[{index}].inline_formulas",
        default_display=False,
    )

    if step.get("latex") or step.get("formula"):
        display = step.get("display", True)
        if isinstance(display, str):
            display = display.lower() not in {"inline", "false", "0", "no"}
        _append_formula(
            lines,
            step.get("latex") or step.get("formula"),
            display=bool(display),
            path=f"steps[{index}].formula",
        )

    _append_text(lines, step.get("explanation") or step.get("justification"))
    _append_text(lines, step.get("conclusion"))


def _steps_from_ir(ir: dict[str, Any]) -> list[dict[str, Any]]:
    trace = ir.get("proof_trace")
    if isinstance(trace, dict) and isinstance(trace.get("steps"), list):
        return [s for s in trace.get("steps") or [] if isinstance(s, dict)]
    return [s for s in (ir.get("steps") or []) if isinstance(s, dict)]


def _final_answer(ir: dict[str, Any]) -> Any:
    trace = ir.get("proof_trace")
    if isinstance(trace, dict) and trace.get("final_answer"):
        return trace.get("final_answer")
    return ir.get("final_answer")


def _compile_final_answer(final_answer: Any, lines: list[str]) -> None:
    if not final_answer:
        return
    lines.extend(["## 最终答案", ""])
    if isinstance(final_answer, dict):
        if final_answer.get("text") or final_answer.get("body") or final_answer.get("conclusion"):
            _append_text(
                lines,
                final_answer.get("text") or final_answer.get("body") or final_answer.get("conclusion"),
            )
            return
        parsed = _formula_from_obj(final_answer)
        if parsed:
            formula, display = parsed
            _append_formula(lines, formula, display=display, path="final_answer")
            return
    _append_formula(lines, final_answer, display=True, path="final_answer")


def _compile_subparts(ir: dict[str, Any], lines: list[str]) -> bool:
    subparts = ir.get("subparts")
    if not isinstance(subparts, list) or not subparts:
        return False
    for pidx, subpart in enumerate(subparts, start=1):
        if not isinstance(subpart, dict):
            continue
        label = _text(subpart.get("label") or f"({pidx})")
        title = _text(subpart.get("title"))
        heading = f"## 第 {label} 问" if not title else f"## 第 {label} 问：{title}"
        lines.extend([heading, ""])
        _append_text(lines, subpart.get("body") or subpart.get("body_markdown"))
        for sidx, step in enumerate(subpart.get("steps") or [], start=1):
            if isinstance(step, dict):
                _compile_step(step, sidx, lines)
        _compile_final_answer(subpart.get("final_answer"), lines)
    return True


def compile_canonical_ir_to_markdown(ir: dict) -> str:
    """Compile CanonicalIR-like JSON into safe Markdown without side effects."""
    if not isinstance(ir, dict):
        raise SolutionMarkdownCompileError("CanonicalIR must be a dict")

    lines: list[str] = ["## 标准解答", ""]

    if not _compile_subparts(ir, lines):
        for idx, step in enumerate(_steps_from_ir(ir), start=1):
            _compile_step(step, idx, lines)

    _compile_final_answer(_final_answer(ir), lines)

    markdown = "\n".join(lines).strip() + "\n"
    if "$$$" in markdown:
        raise SolutionMarkdownCompileError("compiler produced triple dollars")
    for match in re.finditer(r"\$\$([\s\S]*?)\$\$", markdown):
        if _CJK_RE.search(match.group(1)):
            raise SolutionMarkdownCompileError("compiler placed Chinese text in display math")
    return markdown
