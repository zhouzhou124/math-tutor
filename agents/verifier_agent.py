"""VerifierAgent — post-hoc reasoning quality checker.

Responsibilities (and ONLY these):
  1. Bidirectional check — detect one-direction proofs via proof_obligation
  2. Missing-condition check — scan for unstated assumptions
  3. Illegal-derivation check — catch dividing by zero, assuming convergence, etc.
  4. Produce a VerificationReport dict consumed by the Renderer.

The VerifierAgent does NOT:
  - Generate solutions (SolverAgent does that)
  - Grade student answers (GradingAgent does that)
  - Diagnose errors (DiagnosisAgent does that)
  - Render anything (Renderer does that)
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

from agents.proof_obligation import detect_obligations, format_obligation_warning


# ═══════════════════════════════════════════════════════════════
#  VerificationReport — structured output, no rendering mixed in
# ═══════════════════════════════════════════════════════════════

@dataclass
class ObligationIssue:
    pattern: str
    obligation: str
    covered: bool


@dataclass
class ConditionIssue:
    description: str
    severity: str  # "warning" | "error"


@dataclass
class DerivationIssue:
    description: str
    location: str = ""  # snippet of the suspicious step


@dataclass
class VerificationReport:
    """Structured report consumed by the Renderer — no Streamlit calls here."""
    passed: bool = True
    obligation_issues: List[ObligationIssue] = field(default_factory=list)
    condition_issues: List[ConditionIssue] = field(default_factory=list)
    derivation_issues: List[DerivationIssue] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "obligation_issues": [asdict(o) for o in self.obligation_issues],
            "condition_issues": [asdict(c) for c in self.condition_issues],
            "derivation_issues": [asdict(d) for d in self.derivation_issues],
            "summary": self.summary,
        }


# ═══════════════════════════════════════════════════════════════
#  Condition check patterns — unstated assumptions
# ═══════════════════════════════════════════════════════════════

_MISSING_CONDITION_PATTERNS = [
    {
        "name": "除零未声明非零",
        "pattern": r"除以|同除以|两边.*除|除.*得",
        "check": r"非零|不为\s*0|不为零|≠\s*0|!=\s*0|不等于\s*0|假设.*[≠≠]",
        "severity": "error",
        "desc": "可能未声明除数非零。在代数操作中除以表达式时必须先确保该表达式不为零。",
    },
    {
        "name": "求导未声明可导",
        "pattern": r"求导|导数|f'|\\\\frac\{d\}\{dx\}",
        "check": r"可导|连续可导|光滑|假设.*可导",
        "severity": "warning",
        "desc": "可能未声明函数可导。求导操作要求函数在该点可导。",
    },
    {
        "name": "积分未声明可积",
        "pattern": r"积分|∫|\\\\int|原函数",
        "check": r"可积|连续|Riemann|黎曼",
        "severity": "warning",
        "desc": "可能未声明函数可积/连续。积分操作需要函数满足可积条件。",
    },
    {
        "name": "极限交换未声明一致收敛",
        "pattern": r"交换.*极限|极限.*交换|求和.*求导|逐项.*导|逐项.*积",
        "check": r"一致收[敛]|Weierstrass|内闭一致",
        "severity": "error",
        "desc": "极限与求和/求导交换需要一致收敛或内闭一致收敛条件。",
    },
    {
        "name": "假设了结论本身",
        "pattern": r"由.*要证|根据.*结论|由.*目标",
        "check": None,
        "severity": "error",
        "desc": "可能使用了待证结论作为推理前提（循环论证）。",
    },
]


# ═══════════════════════════════════════════════════════════════
#  Illegal derivation patterns
# ═══════════════════════════════════════════════════════════════

_ILLEGAL_DERIVATION_PATTERNS = [
    {
        "name": "不等式方向错误",
        "pattern": r"(?:放大|缩小).*[<>≤≥].*[<>≤≥]",
        "detect": lambda text: _check_inequality_direction(text),
        "desc": "放缩方向可能错误。检查不等式链中每个不等号方向是否一致。",
    },
    {
        "name": "级数收敛假设未验证",
        "pattern": r"求和.*收敛|∑.*收[敛]|级数.*收",
        "check": r"比值.*审敛|根值.*审敛|比较.*审敛|积分.*审敛",
        "severity": "warning",
        "desc": "声称级数收敛但未提供审敛依据。",
    },
    {
        "name": "矩阵运算维度不匹配",
        "pattern": r"(?:\\\\times|\\\\cdot).*矩阵|AB.*=.*O",
        "check": r"维度|阶|可乘",
        "severity": "warning",
        "desc": "矩阵乘法可能涉及维度不匹配的操作。",
    },
]


def _check_inequality_direction(text: str) -> bool:
    """Return True if the inequality direction looks suspicious."""
    # Very simple heuristic: look for 放大 ... < ... > ... pattern
    m = re.search(r'放大.*?([<>≤≥]).*?([<>≤≥])', text)
    if m and m.group(1) != m.group(2):
        return True
    return False


# ═══════════════════════════════════════════════════════════════
#  VerifierAgent
# ═══════════════════════════════════════════════════════════════

class VerifierAgent:
    """Post-hoc verification of AI-generated reasoning text.

    Usage:
        verifier = VerifierAgent()
        report = verifier.verify(
            reasoning_text=gresult.get("comment", ""),
            step_analysis=gresult.get("step_analysis", []),
            diagnosis_text=dresult.get("root_cause", ""),
        )
        if not report.passed:
            gresult["_verification"] = report.to_dict()
    """

    def __init__(self):
        pass  # Stateless — all checks are rule-based

    def verify(
        self,
        reasoning_text: str = "",
        step_analysis: Optional[List[Dict]] = None,
        diagnosis_text: str = "",
    ) -> VerificationReport:
        """Run all verification checks and return a structured report."""

        # Build combined text for pattern scanning
        step_comments = " ".join(
            s.get("comment", "") for s in (step_analysis or [])
        )
        combined = " ".join(filter(None, [reasoning_text, step_comments, diagnosis_text]))

        report = VerificationReport()

        # ── Check 1: Bidirectional obligations ──
        obl_sets = detect_obligations(combined)
        for obl_set in obl_sets:
            for o in obl_set["obligations"]:
                if not o["covered"]:
                    report.obligation_issues.append(ObligationIssue(
                        pattern=obl_set["pattern"],
                        obligation=o["label"],
                        covered=False,
                    ))
                    report.passed = False

        # ── Check 2: Missing conditions ──
        for pat in _MISSING_CONDITION_PATTERNS:
            if re.search(pat["pattern"], combined):
                if pat["check"] and re.search(pat["check"], combined):
                    continue  # Condition stated, OK
                report.condition_issues.append(ConditionIssue(
                    description=pat["desc"],
                    severity=pat.get("severity", "warning"),
                ))
                if pat.get("severity") == "error":
                    report.passed = False

        # ── Check 3: Illegal derivations ──
        for pat in _ILLEGAL_DERIVATION_PATTERNS:
            if re.search(pat["pattern"], combined):
                if "check" in pat and pat["check"] and re.search(pat["check"], combined):
                    continue  # Validated, OK
                if "detect" in pat:
                    if not pat["detect"](combined):
                        continue
                report.derivation_issues.append(DerivationIssue(
                    description=pat["desc"],
                ))
                if pat.get("severity") == "error":
                    report.passed = False

        # ── Build summary ──
        parts = []
        if report.obligation_issues:
            missing = [o.obligation for o in report.obligation_issues]
            parts.append(f"**双向性**: {len(missing)} 项义务未覆盖")
        if report.condition_issues:
            parts.append(f"**条件遗漏**: {len(report.condition_issues)} 处可疑")
        if report.derivation_issues:
            parts.append(f"**推导问题**: {len(report.derivation_issues)} 处可疑")

        report.summary = " | ".join(parts) if parts else "全部检查通过"

        return report


def render_verification_report(report: VerificationReport) -> None:
    """Render a VerificationReport to Streamlit.  This is the ONLY rendering
    function — the VerifierAgent itself never touches st.*."""
    import streamlit as st

    if report.passed and not report.condition_issues and not report.derivation_issues:
        return  # Nothing to show

    with st.container(border=True):
        st.caption("🔬 推理验证报告")

        if report.obligation_issues:
            st.warning(format_obligation_warning(detect_obligations("")))
            # Rebuild the structured display
            lines = []
            by_pattern = {}
            for o in report.obligation_issues:
                by_pattern.setdefault(o.pattern, []).append(o)
            for pat, issues in by_pattern.items():
                lines.append(f"**{pat}**: 缺少以下证明义务：")
                for iss in issues:
                    lines.append(f"  - [ ] {iss.obligation}")
            st.warning("\n".join(lines))

        if report.condition_issues:
            for c in report.condition_issues:
                icon = "❌" if c.severity == "error" else "⚠️"
                st.warning(f"{icon} {c.description}")

        if report.derivation_issues:
            for d in report.derivation_issues:
                st.warning(f"⚠️ {d.description}")
