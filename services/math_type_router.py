"""Math type routing for AI calls.

Question-bank categories are metadata. Solver/grading prompt routes should use
the Math I contract consistently so simulated papers and Math II/III questions
do not accidentally hit a different prompt port.
"""

from __future__ import annotations

from typing import Any


MATH1_PORT = "数学一"


def source_math_type(value: Any = None) -> str:
    """Return the category the user/question originally selected."""
    if isinstance(value, dict):
        raw = (
            value.get("source_math_type")
            or value.get("category")
            or value.get("math_type")
            or MATH1_PORT
        )
    else:
        raw = value or MATH1_PORT
    return str(raw).strip() or MATH1_PORT


def math_type_for_ai(_value: Any = None) -> str:
    """Return the only math_type sent to AI solver/grading prompt ports."""
    return MATH1_PORT


def attach_math_port(payload: dict[str, Any] | None, source: Any = None) -> dict[str, Any]:
    """Copy payload and attach both source category and AI prompt math port."""
    result = dict(payload or {})
    origin = source_math_type(source if source is not None else result)
    result["source_math_type"] = origin
    result["math_type"] = math_type_for_ai(result)
    return result
