"""Tests for integrity_audit.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "scripts"))
from integrity_audit import (
    AuditDimension,
    AuditFinding,
    IntegrityAuditReport,
    audit_artifacts,
    audit_evidence_chain,
    audit_integrity_patterns,
    audit_reasoning_depth,
    to_markdown,
)


def _make_out_dir(**files: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    (tmp / "final_paper").mkdir()
    (tmp / "paper_spine_config.json").write_text('{"workflow": "rewrite_existing"}', encoding="utf-8")
    for name, content in files.items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp


class IntegrityAuditTests(unittest.TestCase):
    def test_finding_has_all_teaching_fields(self) -> None:
        f = AuditFinding("T-001", "BLOCKER", "Test", "what", "root cause", "fix", "downstream", "teaching")
        self.assertEqual(f.id, "T-001")
        self.assertEqual(f.severity, "BLOCKER")
        self.assertTrue(f.teaching_note)

    def test_dimension_blocked_with_blocker(self) -> None:
        dim = AuditDimension("Test")
        dim.findings.append(AuditFinding("A", "WARNING", "Test", "", "", "", "", ""))
        dim.findings.append(AuditFinding("B", "BLOCKER", "Test", "", "", "", "", ""))
        self.assertEqual(dim.status, "BLOCKED")

    def test_dimension_clean_with_no_findings(self) -> None:
        dim = AuditDimension("Test")
        self.assertEqual(dim.status, "CLEAN")

    def test_report_blocked_when_any_dimension_blocked(self) -> None:
        dim1 = AuditDimension("A")
        dim1.findings.append(AuditFinding("x", "BLOCKER", "A", "", "", "", "", ""))
        report = IntegrityAuditReport("test", [dim1])
        self.assertTrue(report.blocked)

    def test_report_not_blocked_when_clean(self) -> None:
        report = IntegrityAuditReport("test", [AuditDimension("A")])
        self.assertFalse(report.blocked)

    def test_audit_artifacts_detects_missing(self) -> None:
        tmp = _make_out_dir()
        tmp.joinpath("final_paper", "main.tex").write_text(r"\section{Test} text text text enough words for paragraphs", encoding="utf-8")
        # Missing most artifacts — should produce BLOCKED findings
        config = {"workflow": "rewrite_existing"}
        dim = audit_artifacts(tmp, config)
        self.assertEqual(dim.status, "BLOCKED")

    def test_audit_reasoning_depth_shallow_rows(self) -> None:
        tmp = _make_out_dir(**{
            "writing_rationale_matrix.md": (
                "| Row ID | Unit | Motivation | Reference | Evidence |\n"
                "|---|---|---|---|---|\n"
                "| 1 | Framework | short | short | short |\n"
                "| 2 | Para 1 | short | short | short |\n"
            ),
        })
        dim = audit_reasoning_depth(tmp, {})
        self.assertIn(dim.status, ("BLOCKED", "WARNINGS"))

    def test_audit_reasoning_depth_missing_matrix(self) -> None:
        tmp = _make_out_dir()
        dim = audit_reasoning_depth(tmp, {})
        self.assertEqual(dim.status, "BLOCKED")

    def test_audit_evidence_chain_no_issues(self) -> None:
        tmp = _make_out_dir(**{
            "rewrite_matrix.md": "| A | B |\n|---|---|\n| 1 | supported claim |\n",
            "evidence_bank.md": "# Evidence\n\nDetailed evidence content here with substantial detail. " + "x " * 200,
        })
        dim = audit_evidence_chain(tmp, {"workflow": "rewrite_existing"})
        self.assertEqual(dim.status, "CLEAN")

    def test_audit_integrity_patterns_orphan_citations(self) -> None:
        tmp = _make_out_dir(**{
            "final_paper/main.tex": r"\cite{nonexistent} text text text enough words for paragraph splitting test " + "x " * 50,
            "final_paper/references.bib": "@article{real2024, title={Real}}",
        })
        dim = audit_integrity_patterns(tmp, {})
        joined = " ".join(f.what_was_found for f in dim.findings)
        self.assertIn("Orphan", joined)

    def test_audit_integrity_patterns_no_manuscript(self) -> None:
        tmp = _make_out_dir()
        tmp.joinpath("final_paper").rmdir()
        dim = audit_integrity_patterns(tmp, {})
        self.assertTrue(any("No manuscript" in f.what_was_found for f in dim.findings))

    def test_to_markdown_includes_teaching(self) -> None:
        dim = AuditDimension("Test")
        dim.findings.append(AuditFinding("T-001", "BLOCKER", "Test", "what", "root", "fix", "downstream", "This teaches you something"))
        report = IntegrityAuditReport("test", [dim])
        md = to_markdown(report)
        self.assertIn("Integrity Audit", md)
        self.assertIn("This teaches you something", md)
        self.assertIn("BLOCKED", md)

    def test_json_output_structure(self) -> None:
        dim = AuditDimension("Test")
        dim.findings.append(AuditFinding("T-001", "WARNING", "Test", "w", "r", "f", "d", "t"))
        report = IntegrityAuditReport("test", [dim])
        output = json.dumps({"blocked": report.blocked, "total": report.total_findings})
        data = json.loads(output)
        self.assertFalse(data["blocked"])
        self.assertEqual(data["total"], 1)


if __name__ == "__main__":
    unittest.main()
