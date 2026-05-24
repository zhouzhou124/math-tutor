"""Global UI theme — design tokens, CSS, page header, and shared components."""

import streamlit as st

# ═══════════════════════════════════════════════
#  CSS injection
# ═══════════════════════════════════════════════

_THEME_INJECTED = False


def inject_app_theme() -> None:
    """Inject global design-system CSS once per session."""
    global _THEME_INJECTED
    if _THEME_INJECTED:
        return
    _THEME_INJECTED = True

    st.markdown(
        """
        <style>
        :root {
            --primary: #2563eb;
            --primary-soft: #eff6ff;
            --purple: #7c3aed;
            --success: #16a34a;
            --warning: #f59e0b;
            --danger: #dc2626;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e5e7eb;
            --card-bg: #ffffff;
            --page-bg: #f8fafc;
            --radius-lg: 18px;
            --shadow-soft: 0 8px 24px rgba(15, 23, 42, 0.06);
        }

        .block-container {
            padding-top: 1.4rem;
            max-width: 1180px;
        }

        /* ── Page headers ── */
        .app-page-title {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--text-main);
            margin-bottom: 0.25rem;
            letter-spacing: -0.02em;
        }

        .app-page-subtitle {
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-bottom: 1.2rem;
        }

        /* ── Cards ── */
        .app-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 18px;
            box-shadow: var(--shadow-soft);
            margin-bottom: 14px;
        }

        .app-card-compact {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
            margin-bottom: 10px;
        }

        /* ── Section titles ── */
        .app-section-title {
            font-size: 1.05rem;
            font-weight: 750;
            color: var(--text-main);
            margin-bottom: 0.55rem;
        }

        .app-muted {
            color: var(--text-muted);
            font-size: 0.88rem;
        }

        /* ── Chips / badges ── */
        .app-chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 9px;
            border-radius: 999px;
            background: #f1f5f9;
            color: #475569;
            font-size: 0.78rem;
            font-weight: 600;
            margin: 2px 4px 2px 0;
        }

        .app-chip-blue  { background: #eff6ff; color: #1d4ed8; }
        .app-chip-green { background: #f0fdf4; color: #15803d; }
        .app-chip-orange{ background: #fff7ed; color: #c2410c; }
        .app-chip-red   { background: #fef2f2; color: #b91c1c; }
        .app-chip-purple{ background: #f5f3ff; color: #6d28d9; }

        /* ── Error / mistake card severity left-border ── */
        .mistake-card-hot  { border-left: 5px solid #dc2626; }
        .mistake-card-warm { border-left: 5px solid #f59e0b; }
        .mistake-card-cool { border-left: 5px solid #2563eb; }
        .mistake-card-done { border-left: 5px solid #16a34a; }

        /* ── Question preview: clamp to 2 lines ── */
        .app-question-preview {
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.5;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin: 6px 0 8px 0;
        }

        /* ── Buttons ── */
        .stButton > button {
            border-radius: 14px !important;
            min-height: 42px;
            font-weight: 650 !important;
        }

        /* ── Metric cards ── */
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 12px 14px;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
        }

        /* ── Flow steps ── */
        .flow-steps {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }

        /* ── Mobile ── */
        @media (max-width: 768px) {
            .block-container {
                padding: 0.85rem 0.85rem 6.8rem 0.85rem !important;
            }

            .app-page-title {
                font-size: 1.38rem;
            }

            .app-page-subtitle {
                font-size: 0.86rem;
                margin-bottom: 0.9rem;
            }

            .app-card {
                padding: 14px;
                border-radius: 16px;
                margin-bottom: 12px;
            }

            .app-card-compact {
                padding: 12px;
                border-radius: 14px;
                margin-bottom: 8px;
            }

            .app-section-title {
                font-size: 1rem;
            }

            .stButton > button {
                min-height: 48px !important;
                width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════
#  Page header
# ═══════════════════════════════════════════════

def render_page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render a unified page title + optional subtitle."""
    safe_title = f"{icon} {title}" if icon else title
    st.markdown(
        f'<div class="app-page-title">{safe_title}</div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f'<div class="app-page-subtitle">{subtitle}</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════
#  Shared components
# ═══════════════════════════════════════════════

def render_flow_steps(steps: list[str], active: int = 1) -> None:
    """Render a horizontal step indicator: ① → ② → ③"""
    html_parts = ['<div class="flow-steps">']
    for i, label in enumerate(steps, 1):
        cls = "app-chip-blue" if i == active else "app-chip"
        html_parts.append(f'<span class="{cls}">{i}. {label}</span>')
    html_parts.append('</div>')
    st.markdown(" ".join(html_parts), unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  Chip rendering (centralized, XSS-safe)
# ═══════════════════════════════════════════════

_CHIP_STYLE_ALLOWLIST = {"blue", "green", "orange", "red", "purple"}


def _render_chip_html(label: str, style: str = "blue") -> str:
    """Render a single chip as safe HTML. Style is allowlist-validated."""
    import html as _h
    safe_label = _h.escape(str(label or ""))
    safe_style = style if style in _CHIP_STYLE_ALLOWLIST else "blue"
    return f'<span class="app-chip app-chip-{safe_style}">{safe_label}</span>'


def render_question_list_card(q: dict, show_actions: bool = True,
                               show_preview: bool = False) -> None:
    """Render a compact question card header for lists (bank, search results).

    Only renders metadata and chips. Full question rendering is done separately
    by the page via render_question().

    Args:
        q: question dict or VM from build_question_card_vm
        show_actions: if True, render [练习] [批改] [解析] buttons
        show_preview: if True, render plain-text preview below the header
    """
    import html as _h

    qid = _h.escape(str(q.get("question_id", "")))
    year = _h.escape(str(q.get("year", ""))) if q.get("year") else ""
    qtype = _h.escape(str(q.get("question_type", "")))
    difficulty = _h.escape(str(q.get("difficulty", "中等")))

    diff_style = {
        "基础": "green", "中等": "blue",
        "较难": "orange", "难": "red", "难题": "red",
    }.get(difficulty, "blue")

    # ── Build chips from structured data only ──
    chip_parts = []

    # Difficulty chip
    chip_parts.append(_render_chip_html(difficulty, diff_style))

    # Status chips: list of (label, style) tuples from build_question_card_vm
    for c in q.get("status_chips", []) or []:
        if isinstance(c, (list, tuple)):
            chip_parts.append(_render_chip_html(str(c[0]), str(c[1]) if len(c) > 1 else "blue"))
        elif isinstance(c, dict):
            chip_parts.append(_render_chip_html(
                str(c.get("label", "")),
                str(c.get("style", "blue")),
            ))

    # Knowledge point chips
    for kp in (q.get("knowledge_points", []) or [])[:4]:
        chip_parts.append(_render_chip_html(str(kp), "blue"))

    chips_html = "".join(chip_parts)

    # Preview (only when requested)
    preview_html = ""
    if show_preview:
        preview = q.get("preview") or q.get("question_preview") or ""
        if not preview:
            raw = q.get("raw_question") or q.get("question") or ""
            from services.question_bank_service import latex_to_plain_preview
            preview = latex_to_plain_preview(raw)
        preview = _h.escape(str(preview))
        if preview:
            preview_html = f'<div class="app-question-preview">{preview}</div>'

    st.markdown(
        f"""
        <div class="app-card-compact">
            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
                <div style="font-weight:750;color:#0f172a;">
                    {year + " · " if year else ""}{qtype}
                </div>
            </div>
            <div style="margin-top:8px;">{chips_html}</div>
            {preview_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if show_actions:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.button("✏️ 练习", key=f"practice_{qid}", use_container_width=True)
        with c2:
            st.button("🤖 批改", key=f"grade_{qid}", use_container_width=True)
        with c3:
            st.button("📖 解析", key=f"solution_{qid}", use_container_width=True)


def render_mistake_card(record: dict) -> None:
    """Render a mistake notebook card with severity-colored left border."""
    import html as _h

    score = record.get("score", 0)
    max_s = record.get("max_score", 10)
    ratio = score / max(max_s, 1)

    if ratio < 0.4:
        severity = "hot"
    elif ratio < 0.7:
        severity = "warm"
    elif ratio < 0.9:
        severity = "cool"
    else:
        severity = "done"

    sev_labels = {"hot": "🔥 高优先级", "warm": "⚠️ 需复习", "cool": "💡 轻微错误", "done": "✅ 已掌握"}
    sev_label = sev_labels.get(severity, "")

    kp = _h.escape(str(record.get("knowledge_point", "")))
    root_cause = _h.escape(str((record.get("root_cause") or record.get("error_type", ""))[:80]))
    ts = _h.escape(str(record.get("timestamp", "")[:10]))
    preview = _h.escape(str(record.get("preview") or record.get("question_preview", "")[:80]))
    qid = _h.escape(str(record.get("question_id", "")))

    st.markdown(
        f"""
        <div class="app-card-compact mistake-card-{severity}">
            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center;">
                <span style="font-weight:750;color:#0f172a;">{sev_label}</span>
                <span class="app-muted">{ts}</span>
            </div>
            <div style="font-weight:650;color:#475569;margin:4px 0;">
                {kp} · 得分 {score}/{max_s}
            </div>
            <div class="app-muted" style="margin:2px 0;">{root_cause}</div>
            <div class="app-question-preview">{preview}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.button("🔄 重做", key=f"retry_{qid}", use_container_width=True)
    with c2:
        st.button("📖 解析", key=f"view_{qid}", use_container_width=True)
