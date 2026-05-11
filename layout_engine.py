"""
Layout Decision Engine v3.6 — 题目语义 → 自动布局 → Render Schema

核心: 不是"拼接 LaTeX", 而是"数学题 = 可执行 UI 语义结构"

规则:
  R1: 题目长度 → compact_inline / balanced / block
  R2: 公式密度 → inline / display
  R3: 选项策略 → single_row / grid / vertical
  R4: 小题数量 → compact / expanded
"""
import re
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════
# Layout decisions
# ═══════════════════════════════════════════════

@dataclass
class LayoutDecision:
    """自动布局决策"""
    layout_type: str        # compact_inline | balanced | block
    formula_mode: str       # inline | display
    options_mode: str       # single_row | two_row | grid | vertical
    wrap_policy: str        # auto | force_single_line | wrap_after_80
    subq_spacing: str       # compact | normal | expanded
    total_length: int = 0
    formula_count: int = 0
    option_count: int = 0
    avg_option_len: float = 0.0


# ═══════════════════════════════════════════════
# R1: Stem length → layout type
# ═══════════════════════════════════════════════

def _stem_layout(stem_len: int) -> str:
    if stem_len < 120:
        return "compact_inline"
    elif stem_len < 300:
        return "balanced"
    else:
        return "block"


# ═══════════════════════════════════════════════
# R2: Formula density → formula mode
# ═══════════════════════════════════════════════

def _formula_mode(text: str) -> str:
    """公式密度决定 inline vs display"""
    # Count $ signs (each inline math = 2 $)
    inline_count = text.count('$') - 2 * text.count('$$')
    # Count display math blocks
    display_count = text.count('$$') // 2
    total_chars = max(len(text), 1)

    formula_ratio = inline_count / total_chars

    # Complex environments → display
    if any(env in text for env in [r'\begin{pmatrix}', r'\begin{cases}',
                                     r'\begin{bmatrix}', r'\begin{aligned}']):
        return "display"

    if formula_ratio > 0.1:  # >10% of chars are in formulas
        return "display"
    if display_count >= 2:
        return "display"
    return "inline"


# ═══════════════════════════════════════════════
# R3: Option strategy
# ═══════════════════════════════════════════════

def _option_mode(options: list[str]) -> str:
    """根据选项数量和长度选择布局"""
    if not options:
        return "vertical"
    n = len(options)
    avg_len = sum(len(o) for o in options) / n

    if n <= 4 and avg_len < 10:
        return "single_row"
    elif n <= 4 and avg_len < 25:
        return "two_row"
    elif n <= 6:
        return "grid"
    else:
        return "vertical"


# ═══════════════════════════════════════════════
# R4: Subquestion spacing
# ═══════════════════════════════════════════════

def _subq_mode(text: str) -> str:
    sq_count = len(re.findall(r'\$\(\d+\)\$', text))
    if sq_count <= 2:
        return "normal"
    elif sq_count <= 4:
        return "expanded"
    else:
        return "compact"  # Many subquestions → save space


# ═══════════════════════════════════════════════
# Main engine
# ═══════════════════════════════════════════════

def decide_layout(question: dict) -> LayoutDecision:
    """
    输入: question dict (from DB)
    输出: LayoutDecision — 完整的自动布局策略
    """
    text = question.get("question", "")
    options = question.get("options", {})

    # Extract option values
    opt_values = list(options.values()) if isinstance(options, dict) else []

    stem_len = len(text)
    formula_count = text.count('$') // 2

    return LayoutDecision(
        layout_type=_stem_layout(stem_len),
        formula_mode=_formula_mode(text),
        options_mode=_option_mode(opt_values),
        wrap_policy="auto" if stem_len > 200 else "force_single_line",
        subq_spacing=_subq_mode(text),
        total_length=stem_len,
        formula_count=formula_count,
        option_count=len(opt_values),
        avg_option_len=sum(len(o) for o in opt_values) / max(len(opt_values), 1),
    )


# ═══════════════════════════════════════════════
# Render Schema Builder
# ═══════════════════════════════════════════════

@dataclass
class RenderBlock:
    """单个渲染块"""
    type: str           # stem | formula | options | subquestion | display_math
    content: str = ""
    mode: str = ""      # inline | display
    layout: str = ""    # row | grid | vertical
    items: list = field(default_factory=list)


@dataclass
class RenderSchema:
    """完整渲染方案"""
    question_id: str = ""
    question_type: str = ""
    layout: str = ""        # compact_inline | balanced | block
    blocks: list[RenderBlock] = field(default_factory=list)


def build_render_schema(question: dict) -> RenderSchema:
    """
    从 DB question dict 构建 RenderSchema.
    输出可用于前端 (React / Streamlit / KaTeX) 直接渲染.
    """
    decision = decide_layout(question)
    text = question.get("question", "")
    qtype = question.get("question_type", "")
    options = question.get("options", {})

    schema = RenderSchema(
        question_id=question.get("question_id", ""),
        question_type=qtype,
        layout=decision.layout_type,
    )

    # ── Block 1: Stem ──
    # Split stem from options (everything before first option label)
    stem = text
    opt_start = re.search(r'\$\(A\)\$', text)
    if opt_start:
        stem = text[:opt_start.start()].strip()

    if stem:
        schema.blocks.append(RenderBlock(
            type="stem", content=stem,
            mode=decision.formula_mode,
        ))

    # ── Block 2: Display math blocks ──
    if '$$' in text:
        for m in re.finditer(r'\$\$(.+?)\$\$', text, re.DOTALL):
            schema.blocks.append(RenderBlock(
                type="display_math",
                content=m.group(1).strip(),
                mode="display",
            ))

    # ── Block 3: Options ──
    if qtype == "选择题" and options:
        opt_items = []
        for label in ['A', 'B', 'C', 'D']:
            if label in options:
                opt_items.append(f"({label}) {options[label]}")
        if opt_items:
            schema.blocks.append(RenderBlock(
                type="options",
                items=opt_items,
                layout=decision.options_mode,
            ))

    # ── Block 4: Subquestions ──
    subqs = re.findall(r'\$\(\d+\)\$[^\n]+', text)
    for sq in subqs:
        schema.blocks.append(RenderBlock(
            type="subquestion",
            content=sq.strip(),
            mode="inline",
        ))

    return schema


def render_schema_to_html(schema: RenderSchema) -> str:
    """RenderSchema → HTML string (可直接嵌入 Streamlit)."""
    html = '<div class="question-block">'

    for block in schema.blocks:
        if block.type == "stem":
            html += f'<div class="stem">{block.content}</div>'
        elif block.type == "display_math":
            html += f'<div class="display-math">$${block.content}$$</div>'
        elif block.type == "options":
            cls = "options-row" if block.layout in ("single_row", "two_row") else "options-vertical"
            html += f'<div class="{cls}">'
            for item in block.items:
                html += f'<span class="option-item">{item}</span>'
            html += '</div>'
        elif block.type == "subquestion":
            html += f'<div class="subquestion">{block.content}</div>'

    html += '</div>'
    return html
