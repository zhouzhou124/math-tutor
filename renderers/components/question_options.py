"""question_options.py — Choice option grid.

Layout: st.columns, math: st.latex. Label + content on same line.
"""
import re
import streamlit as st


def _has_chinese(content: str) -> bool:
    """Check if content contains Chinese characters."""
    return any('一' <= c <= '鿿' for c in content)


def _clean(content: str) -> str:
    """Strip $ wrappers while preserving internal math delimiters."""
    c = content.strip()

    has_chinese = _has_chinese(c)
    
    if has_chinese:
        # For mixed text+math content, only strip outer $ wrapper
        # Preserve internal $ delimiters for math expressions
        if c.startswith("$$") and c.endswith("$$"):
            c = c[2:-2].strip()
        elif c.startswith("$") and c.endswith("$") and c.count("$") == 2:
            c = c[1:-1].strip()
        # Keep internal $ as-is for mixed content
    else:
        # For pure math content, also strip outer $/$ wrappers
        # The renderer will use st.latex() which doesn't need $ delimiters
        if c.startswith("$$") and c.endswith("$$"):
            c = c[2:-2].strip()
        elif c.startswith("$") and c.endswith("$"):
            c = c[1:-1].strip()

    # Strip trailing punctuation
    c = re.sub(r"[。；;．]+$", "", c).strip()

    # Fix \frac without braces: \frac12 → \frac{1}{2}
    c = re.sub(r'\\frac(\d)(\d)', r'\\frac{\1}{\2}', c)

    return c


def _has_text(content: str) -> bool:
    """Check if content has Chinese characters or inner $ (mixed text+math)."""
    if any('一' <= c <= '鿿' for c in content):
        return True
    if '$' in content:
        return True
    return False


def _dedupe(options):
    """Remove duplicate options by label."""
    seen = set()
    result = []
    for opt in options:
        label = opt.label if hasattr(opt, 'label') else opt.get('label', '')
        if label and label not in seen:
            seen.add(label)
            result.append(opt)
    return result


def render_options(options, cols: int = 2) -> None:
    """Render choice options in a grid.

    Label as HTML, content as LaTeX — separate rendering for correct display.
      (A)                    ← HTML label
      k=2, c=-1/2           ← st.latex(content)
    """
    options = _dedupe(options)
    if not options:
        return

    col_objs = st.columns(cols, gap="medium")

    for i, opt in enumerate(options):
        label = opt.label if hasattr(opt, 'label') else opt.get('label', '?')
        content = opt.content if hasattr(opt, 'content') else opt.get('content', '')

        with col_objs[i % cols]:
            if i >= cols:
                st.markdown("")

            # Label as styled inline HTML
            st.markdown(
                f'<span style="font-weight:700;color:#6d28d9;margin-right:6px;">'
                f'({label})</span>',
                unsafe_allow_html=True,
            )

            # Content rendering: detect pure math vs mixed text+LaTeX
            clean = _clean(content)
            if clean:
                try:
                    # If content has Chinese chars, render directly (preserve internal $)
                    if _has_chinese(clean):
                        st.markdown(clean)
                    elif '$' in clean:
                        # Has $ delimiters but no Chinese - render as markdown
                        st.markdown(clean)
                    else:
                        # Pure math without $ - use st.latex
                        st.latex(clean)
                except Exception:
                    st.caption(clean[:200])
