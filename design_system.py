"""
design_system.py — 统一设计系统

所有颜色、间距、样式必须从这里引用，禁止硬编码。
"""

# ═══════════════════════════════════════════════
# 难度颜色
# ═══════════════════════════════════════════════
DIFFICULTY = {
    "基础": {"bg": "#f1f5f9", "text": "#64748b", "border": "#cbd5e1", "stars": "★"},
    "中等": {"bg": "#eff6ff", "text": "#2563eb", "border": "#bfdbfe", "stars": "★★"},
    "较难": {"bg": "#fff7ed", "text": "#ea580c", "border": "#fed7aa", "stars": "★★★"},
    "难题": {"bg": "#fef2f2", "text": "#dc2626", "border": "#fecaca", "stars": "★★★★"},
}

# ═══════════════════════════════════════════════
# 题型颜色
# ═══════════════════════════════════════════════
QUESTION_TYPE = {
    "选择题": {"bg": "#faf5ff", "text": "#7c3aed", "border": "#ddd6fe", "icon": "📋"},
    "填空题": {"bg": "#ecfeff", "text": "#0891b2", "border": "#cffafe", "icon": "✍"},
    "解答题": {"bg": "#f0fdf4", "text": "#16a34a", "border": "#bbf7d0", "icon": "📝"},
    "证明题": {"bg": "#fef2f2", "text": "#b91c1c", "border": "#fecaca", "icon": "🔍"},
}

# ═══════════════════════════════════════════════
# 知识点 chip 样式（统一）
# ═══════════════════════════════════════════════
CHIP_STYLE = {
    "border-radius": "999px",
    "padding": "2px 10px",
    "font-size": "0.74rem",
    "font-weight": "600",
    "display": "inline-flex",
    "align-items": "center",
    "min-height": "1.5rem",
}

# 知识点 chip 颜色
CHIP_COLORS = {
    "bg": "#eef2ff",
    "text": "#4338ca",
    "border": "#c7d2fe",
}

# ═══════════════════════════════════════════════
# 卡片颜色
# ═══════════════════════════════════════════════
CARD = {
    "bg": "#ffffff",
    "border": "#e2e8f0",
    "shadow": "0 1px 3px rgba(0,0,0,0.05)",
    "radius": "12px",
}

# ═══════════════════════════════════════════════
# 操作颜色
# ═══════════════════════════════════════════════
OPERATION = {
    "classify":       {"label": "识别题型", "color": "#6b7280"},
    "recall":         {"label": "回忆定理", "color": "#2563eb"},
    "substitute":     {"label": "代入",     "color": "#7c3aed"},
    "simplify":       {"label": "化简",     "color": "#059669"},
    "expand":         {"label": "展开",     "color": "#059669"},
    "factor":         {"label": "因式分解", "color": "#059669"},
    "differentiate":  {"label": "求导",     "color": "#d97706"},
    "integrate":      {"label": "积分",     "color": "#d97706"},
    "solve":          {"label": "求解",     "color": "#dc2626"},
    "evaluate":       {"label": "计算",     "color": "#dc2626"},
    "apply_theorem":  {"label": "应用定理", "color": "#2563eb"},
    "transform":      {"label": "变换",     "color": "#7c3aed"},
    "conclude":       {"label": "结论",     "color": "#0891b2"},
    "check":          {"label": "验证",     "color": "#0891b2"},
}


def chip_html(label: str) -> str:
    """生成知识点 chip HTML。"""
    import html
    return (
        f'<span style="'
        f'display:{CHIP_STYLE["display"]};'
        f'align-items:{CHIP_STYLE["align-items"]};'
        f'min-height:{CHIP_STYLE["min-height"]};'
        f'border-radius:{CHIP_STYLE["border-radius"]};'
        f'padding:{CHIP_STYLE["padding"]};'
        f'font-size:{CHIP_STYLE["font-size"]};'
        f'font-weight:{CHIP_STYLE["font-weight"]};'
        f'border:1px solid {CHIP_COLORS["border"]};'
        f'background:{CHIP_COLORS["bg"]};'
        f'color:{CHIP_COLORS["text"]};'
        f'">'
        f'{html.escape(str(label))}'
        f'</span>'
    )


def diff_badge_html(difficulty: str) -> str:
    """生成难度 badge HTML。"""
    import html
    d = DIFFICULTY.get(difficulty, DIFFICULTY["中等"])
    return (
        f'<span style="'
        f'display:inline-flex;align-items:center;min-height:1.5rem;'
        f'border-radius:999px;padding:2px 10px;'
        f'font-size:0.74rem;font-weight:600;'
        f'border:1px solid {d["border"]};'
        f'background:{d["bg"]};color:{d["text"]};'
        f'">'
        f'{html.escape(difficulty)} {d["stars"]}'
        f'</span>'
    )


def qtype_badge_html(qtype: str) -> str:
    """生成题型 badge HTML。"""
    import html
    t = QUESTION_TYPE.get(qtype)
    if not t:
        return html.escape(qtype)
    return (
        f'<span style="'
        f'display:inline-flex;align-items:center;min-height:1.5rem;'
        f'border-radius:999px;padding:2px 10px;'
        f'font-size:0.74rem;font-weight:600;'
        f'border:1px solid {t["border"]};'
        f'background:{t["bg"]};color:{t["text"]};'
        f'">'
        f'{t["icon"]} {html.escape(qtype)}'
        f'</span>'
    )
