"""P29-4.5: dry-run Solution IR shadow evaluation harness tests."""

import json


def _valid_ir(step_count: int = 2):
    from tests.test_p29_ir_shadow_mode import _valid_ir as make_ir

    return make_ir(step_count=step_count)


def _valid_legacy_answer():
    from tests.test_p29_solution_ir_passthrough import _valid_solution_payload

    answer, _structured = _valid_solution_payload()
    return answer


def _write_question(root, name, question):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(question, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _question(entries, qid="q1"):
    return {
        "question_id": qid,
        "question_type": "解答题",
        "question": "求方程的解。",
        "canonical_solutions": entries,
    }


def test_entry_without_ir_is_counted_but_not_compiled(tmp_path):
    from scripts.eval_solution_ir_shadow import build_report

    _write_question(tmp_path, "q1.json", _question([
        {"standard_answer": _valid_legacy_answer()}
    ]))

    report = build_report(tmp_path)
    summary = report["summary"]

    assert summary["total_entries"] == 1
    assert summary["entries_with_ir"] == 0
    assert summary["compiled_ok_count"] == 0
    assert report["samples"][0]["has_ir"] is False


def test_valid_ir_compiles_and_counts_compiled_ok(tmp_path):
    from scripts.eval_solution_ir_shadow import build_report

    _write_question(tmp_path, "q1.json", _question([
        {"standard_answer": _valid_legacy_answer(), "solution_ir": _valid_ir()}
    ]))

    report = build_report(tmp_path)
    sample = report["samples"][0]

    assert report["summary"]["entries_with_ir"] == 1
    assert report["summary"]["ir_valid_count"] == 1
    assert report["summary"]["compile_success_count"] == 1
    assert sample["compiled_ok"] is True
    assert sample["compiled_preview"].startswith("## 标准解答")
    assert len(sample["compiled_preview"]) <= 200


def test_invalid_ir_records_invalid_reason(tmp_path):
    from scripts.eval_solution_ir_shadow import build_report

    ir = _valid_ir()
    ir["proof_trace"]["steps"][0]["output_state"] = "$x=1$"
    _write_question(tmp_path, "q1.json", _question([
        {"standard_answer": _valid_legacy_answer(), "solution_ir": ir}
    ]))

    report = build_report(tmp_path)
    sample = report["samples"][0]

    assert sample["ir_valid"] is False
    assert "canonical_ir_formula_not_clean" in sample["ir_errors"]
    assert report["summary"]["invalid_ir_reasons"][0]["reason"] == "canonical_ir_formula_not_clean"
    assert sample["recommendation"] == "invalid_ir"


def test_compiled_better_recommends_use_compiled(tmp_path):
    from scripts.eval_solution_ir_shadow import build_report

    _write_question(tmp_path, "q1.json", _question([
        {"standard_answer": "x", "solution_ir": _valid_ir()}
    ]))

    report = build_report(tmp_path)
    sample = report["samples"][0]

    assert sample["compiled_ok"] is True
    assert sample["legacy_ok"] is False
    assert sample["recommendation"] == "use_compiled"
    assert report["summary"]["compiled_better_count"] == 1


def test_compiled_failure_keeps_legacy_or_regenerates(tmp_path):
    from scripts.eval_solution_ir_shadow import build_report

    _write_question(tmp_path, "q1.json", _question([
        {"standard_answer": _valid_legacy_answer(), "solution_ir": _valid_ir(step_count=1)},
        {"standard_answer": "x", "solution_ir": _valid_ir(step_count=1)},
    ]))

    report = build_report(tmp_path)
    recommendations = [sample["recommendation"] for sample in report["samples"]]

    assert recommendations == ["keep_legacy", "regenerate"]
    assert report["summary"]["compiled_worse_count"] == 1


def test_dry_run_does_not_write_back_question_cache(tmp_path):
    from scripts.eval_solution_ir_shadow import build_report

    path = _write_question(tmp_path, "q1.json", _question([
        {"standard_answer": "x", "solution_ir": _valid_ir()}
    ]))
    before = path.read_text(encoding="utf-8")

    build_report(tmp_path)

    assert path.read_text(encoding="utf-8") == before


def test_save_report_flag_writes_json_report(tmp_path, monkeypatch):
    import scripts.eval_solution_ir_shadow as eval_script

    questions_root = tmp_path / "questions"
    report_dir = tmp_path / "eval_runs"
    _write_question(questions_root, "q1.json", _question([
        {"standard_answer": "x", "solution_ir": _valid_ir()}
    ]))

    monkeypatch.setattr(eval_script, "DEFAULT_QUESTIONS_ROOT", questions_root)
    monkeypatch.setattr(eval_script, "DEFAULT_REPORT_DIR", report_dir)

    assert eval_script.main(["--save-report"]) == 0
    paths = list(report_dir.glob("solution_ir_shadow_*.json"))
    assert len(paths) == 1
    path = paths[0]
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert path.name.startswith("solution_ir_shadow_")
    assert saved["summary"]["total_entries"] == 1
    assert saved["samples"][0]["question_id"] == "q1"
