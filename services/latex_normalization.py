"""Business-facing LaTeX normalization entry points."""

from __future__ import annotations


def normalize_latex(text: str) -> str:
    """Normalize LaTeX/text for business code and always return str."""
    from latex_normalizer import normalize_latex_style

    return str(normalize_latex_style(str(text or "")))


def normalize_latex_style(text: str) -> str:
    """Backward-compatible alias with a str-only contract."""
    return normalize_latex(text)
