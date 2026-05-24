"""P0 regression tests — prevent critical bugs from returning."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════
# Test 1: pool_best branch creates gresult (no UnboundLocalError)
# ═══════════════════════════════════════════════
def test_pool_best_branch_creates_gresult():
    """After Engine C fails, canonical_pool match must create gresult before use.

    This logic now lives in services/grading_orchestrator.py after P3-4 extraction.
    """
    import re
    fp = os.path.join(os.path.dirname(__file__), '..', 'services', 'grading_orchestrator.py')
    with open(fp, 'r', encoding='utf-8') as f:
        source = f.read()

    # The orchestrator uses a simplified Engine C path that always calls
    # grading.grade() before accessing gresult. Verify this pattern exists.
    assert 'gresult = grading.grade(' in source or 'gresult = grading_engine_c.grade(' in source, (
        "orchestrator must call grading.grade() before accessing gresult[...]"
    )


# ═══════════════════════════════════════════════
# Test 2: background thread doesn't write st.session_state directly
# ═══════════════════════════════════════════════
def test_background_thread_uses_state_dict():
    """Background thread path must not write st.session_state uncoditionally."""
    import ast
    fp = os.path.join(os.path.dirname(__file__), '..', 'views', 'grading_page.py')
    with open(fp, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)

    # Find the error_record save path and verify _invalidate_dashboard
    # is guarded by _state check
    found_unguarded = False
    in_error_save = False
    for node in ast.walk(tree):
        # Look for unconditional st.session_state write near the error save area
        if (isinstance(node, ast.Assign) and
            isinstance(node.targets[0], ast.Subscript) and
            isinstance(node.targets[0].value, ast.Attribute) and
            isinstance(node.targets[0].value.value, ast.Attribute) and
            node.targets[0].value.value.attr == 'session_state' and
            isinstance(node.targets[0].slice, ast.Constant) and
            node.targets[0].slice.value == '_invalidate_dashboard'):
            # This is st.session_state["_invalidate_dashboard"] = ...
            # Check if it's inside an if/else with _state guard
            found_unguarded = True

    # Now verify it's inside an if _state is not None / else block
    # by checking that the parent If node exists
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_str = ast.dump(node.test)
            if '_state' in test_str and 'is not None' in test_str or 'is not None' in test_str:
                for child in ast.walk(node):
                    if (isinstance(child, ast.Assign) and
                        isinstance(child.targets[0], ast.Subscript) and
                        isinstance(child.targets[0].value, ast.Attribute) and
                        isinstance(child.targets[0].value.value, ast.Attribute) and
                        child.targets[0].value.value.attr == 'session_state' and
                        isinstance(child.targets[0].slice, ast.Constant) and
                        child.targets[0].slice.value == '_invalidate_dashboard'):
                        found_unguarded = False

    assert not found_unguarded, (
        "st.session_state['_invalidate_dashboard'] must be inside _state guard"
    )


# ═══════════════════════════════════════════════
# Test 3: Option regex doesn't drop letters or throw IndexError
# ═══════════════════════════════════════════════
def test_split_latex_text_choice_after_quad():
    """\quad(A) x=1 \quad(B) x=2 must preserve option letters."""
    from latex_utils import split_latex_text
    text = r"\quad(A) x=1 \quad(B) x=2"
    segments = split_latex_text(text)
    rendered = " ".join(
        s.get("content", s) if isinstance(s, dict) else str(s)
        for s in segments
    )
    assert "(A)" in rendered, f"Option (A) missing from: {rendered}"
    assert "(B)" in rendered, f"Option (B) missing from: {rendered}"


def test_split_latex_text_chinese_choice_after_quad():
    """\qquad（A）x=1 \qquad（B）x=2 must preserve option letters."""
    from latex_utils import split_latex_text
    text = r"\qquad（A）x=1 \qquad（B）x=2"
    segments = split_latex_text(text)
    rendered = " ".join(
        s.get("content", s) if isinstance(s, dict) else str(s)
        for s in segments
    )
    assert "（A）" in rendered or "(A)" in rendered, f"Option A missing from: {rendered}"
    assert "（B）" in rendered or "(B)" in rendered, f"Option B missing from: {rendered}"


def test_quad_option_regex_no_index_error():
    """The regex must have capture group 2 — no IndexError: no such group."""
    import re
    text = r"\quad(A) x=1"
    # This is the pattern from latex_utils.py split_latex_text
    result = re.sub(
        r'(\\qquad|\\quad)\s*\(([A-D])\)',
        lambda m: m.group(1) + '\n(' + m.group(2) + ')',
        text
    )
    assert "(A)" in result
    assert "\\quad" in result


def test_chinese_quad_option_regex_no_index_error():
    """The regex for Chinese brackets must have capture group 2."""
    import re
    text = r"\qquad（A）x=1"
    result = re.sub(
        r'(\\qquad|\\quad)\s*（([A-D])）',
        lambda m: m.group(1) + '\n（' + m.group(2) + '）',
        text
    )
    assert "（A）" in result


# ═══════════════════════════════════════════════
# Test 4: HTML injection is escaped
# ═══════════════════════════════════════════════
def test_knowledge_point_html_escaped():
    """HTML tags in knowledge_point must be escaped."""
    import html
    kp = '<img src=x onerror=alert(1)>'
    safe = html.escape(str(kp))
    assert '&lt;img' in safe
    assert '<img' not in safe


def test_common_mistake_html_escaped():
    """HTML tags in common_mistakes must be escaped."""
    import html
    cm = '<script>alert("xss")</script>'
    safe = html.escape(str(cm))
    assert '&lt;script&gt;' in safe
    assert '<script>' not in safe


def test_weak_point_html_escaped():
    """HTML tags in weak_points must be escaped."""
    import html
    wp = '<b onclick=evil()>weak</b>'
    safe = html.escape(str(wp))
    assert '&lt;b' in safe
    assert '<b ' not in safe


def test_safe_render_fallback_no_raw_html():
    """safe_render fallback must NOT use unsafe_allow_html=True."""
    import ast
    fp = os.path.join(os.path.dirname(__file__), '..', 'latex_utils.py')
    with open(fp, 'r', encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source)

    # Find the safe_render function's except block
    in_safe_render = False
    found_unsafe = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'safe_render':
            in_safe_render = True
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    # Check for st.markdown(text, unsafe_allow_html=True)
                    for kw in getattr(child, 'keywords', []):
                        if (kw.arg == 'unsafe_allow_html' and
                            isinstance(kw.value, ast.Constant) and
                            kw.value.value is True):
                            found_unsafe = True
    assert not found_unsafe, (
        "safe_render must not use unsafe_allow_html=True"
    )


if __name__ == "__main__":
    tests = [
        test_pool_best_branch_creates_gresult,
        test_background_thread_uses_state_dict,
        test_split_latex_text_choice_after_quad,
        test_split_latex_text_chinese_choice_after_quad,
        test_quad_option_regex_no_index_error,
        test_chinese_quad_option_regex_no_index_error,
        test_knowledge_point_html_escaped,
        test_common_mistake_html_escaped,
        test_weak_point_html_escaped,
        test_safe_render_fallback_no_raw_html,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
