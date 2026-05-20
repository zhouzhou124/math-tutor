"""proof_obligation.py — Template-based proof obligation checker.

Detects logical patterns in AI-generated grading/diagnosis text that
require bidirectional proof (e.g. 同解, 充要条件, 极值), generates a
list of obligations, and scans the reasoning for coverage.

This is a lightweight symbolic layer — no theorem prover, just pattern
matching + obligation tracking.  Catches the common LLM failure mode of
"只证一边" (proving only one direction).
"""

import re
from typing import List, Dict, Tuple

# ═══════════════════════════════════════════════════════════════
#  Pattern definitions — each maps a trigger phrase to obligations
# ═══════════════════════════════════════════════════════════════

_PATTERNS: List[Dict] = [
    # ── 同解 / 等价方程组 ──
    {
        "name": "同解/等价变换",
        "triggers": [
            r"同解", r"等价.*方程", r"解.*相同", r"同解方程组",
            r"有相同的解", r"解空间.*相同",
        ],
        "obligations": [
            {"id": "forward", "label": "原方程组的解都是新方程组的解 (A⊆B)"},
            {"id": "backward", "label": "新方程组的解都是原方程组的解 (B⊆A)"},
        ],
        "coverage_markers": {
            "forward": [r"若.*是.*解", r"设.*是.*解", r"任取.*解", r"代入"],
            "backward": [r"反之", r"反过来", r"另一方面", r"同理.*可证", r"若.*满足"],
        },
    },
    # ── 充要条件 / iff ──
    {
        "name": "充要条件",
        "triggers": [
            r"充要条件", r"当且仅当", r"iff", r"充分必要",
            r"等价于", r"充分必要条件",
        ],
        "obligations": [
            {"id": "necessity", "label": "必要性 (⇒)"},
            {"id": "sufficiency", "label": "充分性 (⇐)"},
        ],
        "coverage_markers": {
            "necessity": [r"若.*则", r"必要性", r"⇒", r"假设.*成立", r"由.*可得"],
            "sufficiency": [r"反之", r"反过来", r"充分性", r"⇐", r"若.*满足"],
        },
    },
    # ── 解集描述 ──
    {
        "name": "解集描述",
        "triggers": [
            r"解集.*=", r"解.*为", r"通解.*为", r"所有解.*满足",
            r"解空间.*=.*", r"通解.*=.*",
        ],
        "obligations": [
            {"id": "inclusion", "label": "任意解都属于该解集"},
            {"id": "completeness", "label": "解集中任意元素都是解"},
        ],
        "coverage_markers": {
            "inclusion": [r"若.*是解", r"设.*为.*解", r"任取.*解", r"代入"],
            "completeness": [r"反之", r"反过来", r"验证", r"易见", r"显然.*满足", r"代入.*成立"],
        },
    },
    # ── 极值 / 最值 ──
    {
        "name": "极值/最值",
        "triggers": [
            r"极值", r"最值", r"最大值", r"最小值", r"极大值", r"极小值",
            r"驻点", r"临界点",
        ],
        "obligations": [
            {"id": "stationary", "label": "求驻点（一阶导数为零）"},
            {"id": "boundary", "label": "检查边界点（如果区域有界）"},
            {"id": "classify", "label": "验证极值类型（二阶导数检验或比较法）"},
        ],
        "coverage_markers": {
            "stationary": [r"导.*=.*0", r"f'.*=.*0", r"驻点", r"临界点", r"偏导"],
            "boundary": [r"边界", r"端点", r"闭区间", r"区域"],
            "classify": [r"二阶导", r"Hess", r"判别", r"比较", r"代入.*验"],
        },
    },
    # ── 线性相关/无关 ──
    {
        "name": "线性相关/无关",
        "triggers": [
            r"线性相关", r"线性无关", r"线性表示", r"线性组合",
        ],
        "obligations": [
            {"id": "existence", "label": "存在性：存在一组不全为零的系数"},
            {"id": "deduction", "label": "推导：验证系数满足定义"},
        ],
        "coverage_markers": {
            "existence": [r"存在", r"不全为零", r"设有", r"令"],
            "deduction": [r"代入", r"可得", r"因此", r"即"],
        },
    },
    # ── 收敛 / 发散 ──
    {
        "name": "收敛性判断",
        "triggers": [
            r"收敛", r"发散", r"级数.*收", r"级数.*发",
        ],
        "obligations": [
            {"id": "test", "label": "应用审敛法（比值/根值/比较/积分）"},
            {"id": "conclusion", "label": "明确陈述收敛或发散结论"},
        ],
        "coverage_markers": {
            "test": [r"比值", r"根值", r"比较", r"积分", r"极限", r"通项"],
            "conclusion": [r"因此.*收敛", r"因此.*发散", r"所以.*收敛", r"所以.*发散", r"故.*收敛"],
        },
    },
]


def detect_obligations(text: str) -> List[Dict]:
    """Scan reasoning text and return a list of triggered obligation sets.

    Each entry:
      {
        "pattern": "同解/等价变换",
        "obligations": [
          {"id": "forward",  "label": "原→新", "covered": True/False},
          {"id": "backward", "label": "新→原", "covered": False},
        ],
        "all_covered": False,
      }
    """
    if not text:
        return []

    results = []
    for pat in _PATTERNS:
        # Check if any trigger phrase appears in the text
        triggered = False
        for trig in pat["triggers"]:
            if re.search(trig, text):
                triggered = True
                break
        if not triggered:
            continue

        # Build obligation list with coverage check
        obligations = []
        all_covered = True
        for obl in pat["obligations"]:
            markers = pat.get("coverage_markers", {}).get(obl["id"], [])
            covered = any(re.search(m, text) for m in markers) if markers else False
            obligations.append({
                "id": obl["id"],
                "label": obl["label"],
                "covered": covered,
            })
            if not covered:
                all_covered = False

        results.append({
            "pattern": pat["name"],
            "obligations": obligations,
            "all_covered": all_covered,
        })

    return results


def format_obligation_warning(obligations: List[Dict]) -> str:
    """Build a human-readable warning about incomplete proof obligations."""
    lines = []
    for obl_set in obligations:
        if obl_set["all_covered"]:
            continue
        missing = [o for o in obl_set["obligations"] if not o["covered"]]
        lines.append(f"**⚠ {obl_set['pattern']}**: 推理可能不完整。")
        for o in missing:
            lines.append(f"  - [ ] {o['label']}")
        covered = [o for o in obl_set["obligations"] if o["covered"]]
        if covered:
            lines.append(f"  已覆盖: {' | '.join(o['label'] for o in covered)}")
    return "\n".join(lines)


def check_obligations(text: str) -> Tuple[bool, str]:
    """Main entry point: check reasoning text and return (is_complete, warning).

    Returns:
      is_complete: True if all triggered obligations are covered
      warning:     empty string if complete, otherwise a markdown warning
    """
    obligations = detect_obligations(text)
    if not obligations:
        return True, ""

    all_covered = all(o["all_covered"] for o in obligations)
    if all_covered:
        return True, ""

    warning = format_obligation_warning(obligations)
    return False, warning
