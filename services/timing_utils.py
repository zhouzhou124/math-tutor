"""Timing utilities — lightweight stage-level latency tracking.

Provides timed_stage() context manager and helpers to accumulate
per-stage wall-clock times.  Used by the grading orchestrator to
record where time is spent so operators can identify bottlenecks.
"""

import time as _time
from contextlib import contextmanager


@contextmanager
def timed_stage(timing: dict, name: str):
    """Context manager that records elapsed wall-clock ms into timing dict.

    Usage:
        timing = {}
        with timed_stage(timing, "solution"):
            solution = build_solution(...)
        # timing == {"solution_ms": 8421}
    """
    start = _time.perf_counter()
    try:
        yield
    finally:
        timing[f"{name}_ms"] = int((_time.perf_counter() - start) * 1000)


def format_timing_summary(timing: dict) -> str:
    """Return a compact human-readable timing summary.

    Example: "solution:8.4s grading:3.7s diagnosis:0.9s total:13.2s"
    """
    parts = []
    total_ms = 0
    for key, val in sorted(timing.items()):
        if key.endswith("_ms"):
            label = key[:-3]
            ms = int(val)
            total_ms += ms
            parts.append(f"{label}:{ms / 1000:.1f}s")
    if total_ms:
        parts.append(f"total:{total_ms / 1000:.1f}s")
    return " ".join(parts)
