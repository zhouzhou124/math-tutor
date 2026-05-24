"""Data contract tests — verify grading_result and solution dict shapes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _required_keys(d, *keys):
    missing = [k for k in keys if k not in d]
    assert not missing, f"Missing required keys: {missing}"


# ═══════════════════════════════════════════════
# normalize_grading_result
# ═══════════════════════════════════════════════

def test_normalize_grading_result_view_only():
    """view_only engine produces correct contract."""
    from services.grading_adapter import normalize_grading_result
    raw = {"success": True, "total": 0, "engine": "view_only", "comment": "test"}
    result = normalize_grading_result(raw, engine="view_only")
    _required_keys(result, "success", "total", "step_score", "result_score",
                   "step_analysis", "deductions", "comment", "method_matched",
                   "confidence", "engine")
    assert result["total"] == 0
    assert result["engine"] == "view_only"


def test_normalize_grading_result_uses_score_fallback():
    """Fallback: reads 'score' when 'total' is missing."""
    from services.grading_adapter import normalize_grading_result
    raw = {"score": 8}
    result = normalize_grading_result(raw)
    assert result["total"] == 8


def test_normalize_grading_result_detects_engine_from_raw():
    """Detects engine from '_engine' field."""
    from services.grading_adapter import normalize_grading_result
    raw = {"_engine": "choice_engine", "total": 10}
    result = normalize_grading_result(raw)
    assert result["engine"] == "choice_engine"


def test_normalize_grading_result_passthrough_fields():
    """Passes through _obligation_warning and _matched_from_pool."""
    from services.grading_adapter import normalize_grading_result
    raw = {"total": 5, "_obligation_warning": "可能缺步骤", "_matched_from_pool": True}
    result = normalize_grading_result(raw)
    assert result["_obligation_warning"] == "可能缺步骤"
    assert result["_matched_from_pool"] is True


def test_normalize_grading_result_coerces_types():
    """Confidence and total are always float/list."""
    from services.grading_adapter import normalize_grading_result
    result = normalize_grading_result({})
    assert isinstance(result["total"], float)
    assert isinstance(result["confidence"], float)
    assert isinstance(result["step_analysis"], list)


# ═══════════════════════════════════════════════
# normalize_standard_solution
# ═══════════════════════════════════════════════

def test_normalize_standard_solution_defaults():
    """Empty input produces sensible defaults."""
    from services.grading_adapter import normalize_standard_solution
    s = normalize_standard_solution({})
    _required_keys(s, "success", "standard_answer", "total_score",
                   "steps", "_structured", "_ai_unverified",
                   "_ai_consistency_warning", "_solver_fallback")
    assert s["total_score"] == 10
    assert s["steps"] == []
    assert s["_structured"] is None


def test_normalize_standard_solution_preserves_fields():
    """Known fields are preserved through normalization."""
    from services.grading_adapter import normalize_standard_solution
    raw = {
        "standard_answer": "x=1",
        "total_score": 5,
        "steps": [{"label": "步骤1"}],
        "_ai_unverified": True,
        "_ai_consistency_warning": True,
    }
    s = normalize_standard_solution(raw)
    assert s["standard_answer"] == "x=1"
    assert s["total_score"] == 5
    assert len(s["steps"]) == 1
    assert s["_ai_unverified"] is True
    assert s["_ai_consistency_warning"] is True


def test_normalize_standard_solution_coerces_types():
    """_ai_unverified and _ai_consistency_warning are always bool."""
    from services.grading_adapter import normalize_standard_solution
    s = normalize_standard_solution({})
    assert isinstance(s["_ai_unverified"], bool)
    assert isinstance(s["_ai_consistency_warning"], bool)
    assert isinstance(s["_solver_fallback"], bool)


# ═══════════════════════════════════════════════
# Adapter is wired in grading_page
# ═══════════════════════════════════════════════

def test_adapter_imported_in_grading_page():
    """normalize_grading_result and normalize_standard_solution are imported."""
    import ast
    # After P3-4, adapters are used in both grading_page and orchestrator
    for fname in ['views/grading_page.py', 'services/grading_orchestrator.py']:
        fp = os.path.join(os.path.dirname(__file__), '..', fname)
        with open(fp, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "grading_adapter" in source, (
            f"{fname} must import grading_adapter"
        )


if __name__ == "__main__":
    tests = [
        test_normalize_grading_result_view_only,
        test_normalize_grading_result_uses_score_fallback,
        test_normalize_grading_result_detects_engine_from_raw,
        test_normalize_grading_result_passthrough_fields,
        test_normalize_grading_result_coerces_types,
        test_normalize_standard_solution_defaults,
        test_normalize_standard_solution_preserves_fields,
        test_normalize_standard_solution_coerces_types,
        test_adapter_imported_in_grading_page,
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
