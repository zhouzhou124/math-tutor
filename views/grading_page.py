"""pages/grading_page.py — AI 批改"""
import time
import json
import threading
import traceback
import streamlit as st
import logging
from concurrent.futures import ThreadPoolExecutor
from config import LLM_BASE_URL, LLM_MODEL
from agents import GradingAgent, DiagnosisAgent, SolverAgent
from renderers.components.grading_result import render_grading_result_cards
from ._shared import get_client
from .mobile import set_grading_active
from storage.grading_task_store import (
    create_task, complete_task, fail_task, get_task,
    get_recent_task, mark_viewed, cleanup_old,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
#  Unicode math wrapping — AI 生成内容专用
# ═══════════════════════════════════════════════

import re as _re

_UNICODE_MATH_PAT = _re.compile(
    '['
    'Ͱ-Ͽ'          # Greek
    '∀-⋿'          # Math operators
    '←-⇿'          # Arrows
    '±×÷'          # Plus/minus/multiply/divide
    '∞∂∫∬∭∑∏√'  # Infinity/partial/integral/sum/product/sqrt
    '∈∉⊂⊃⊆⊇∪∩∅'  # Set membership
    '∀∃∧∨¬⊕⊗'    # Quantifiers/logic
    '≈≡∼∝∠⊥⋅≠'   # Relations
    '≤≥'           # Inequalities
    ']'
)

_MATH_COMPAT_PAT = _re.compile(
    r'[a-zA-Z0-9=\+\-\*/\^\(\)\[\]\{\}\,\;\.\:\|\\\_\s'
    r'Ͱ-Ͽ∀-⋿←-⇿±×÷≤≥≠]+'
)

def _wrap_unicode_math(text: str) -> str:
    """Wrap Unicode math/greek symbols in $...$ for KaTeX rendering.

    Only called on AI-generated grading output, never on question bank data.
    """
    if not text or not _UNICODE_MATH_PAT.search(text):
        return text

    # Phase 1: collect all math runs (expand from each Unicode math char)
    runs = []
    for m in _UNICODE_MATH_PAT.finditer(text):
        left = m.start()
        while left > 0 and _MATH_COMPAT_PAT.match(text[left - 1]):
            left -= 1
        right = m.end()
        while right < len(text) and _MATH_COMPAT_PAT.match(text[right]):
            right += 1
        runs.append((left, right))

    # Phase 2: merge overlapping runs
    runs.sort()
    merged = []
    for left, right in runs:
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))

    # Phase 3: filter runs containing Chinese
    merged = [(l, r) for l, r in merged
              if not any('一' <= c <= '鿿' for c in text[l:r])]

    # Phase 4: build output with $ wrapping
    parts = []
    last = 0
    for left, right in merged:
        if left > last:
            parts.append(text[last:left])
        parts.append('$' + text[left:right].strip() + '$')
        last = right
    if last < len(text):
        parts.append(text[last:])

    return ''.join(parts)


def _wrap_ascii_math(text: str) -> str:
    """Wrap ASCII math expressions (B^2=E, a^Tx=0, k>0) in $...$.

    Strategy: split by Chinese/punctuation, detect math-like segments, wrap them.
    """
    if not text:
        return text

    # Protect existing $...$ and $$...$$ regions
    protected = []
    def _protect(m):
        protected.append(m.group(0))
        return f'\x00A{len(protected)-1}\x00'
    text = _re.sub(r'\$\$[^$]+\$\$', _protect, text)
    text = _re.sub(r'\$[^$]+\$', _protect, text)

    # Split on Chinese chars, certain punctuation — keep delimiters
    parts = _re.split(r'([一-鿿，。、；：！？\n]+)', text)
    result = []
    for part in parts:
        stripped = part.strip()
        # Skip Chinese-only parts and already-protected
        if not stripped or '\x00A' in part:
            result.append(part)
            continue
        if all('一' <= c <= '鿿' or c in '，。、；：！？\n ' for c in stripped):
            result.append(part)
            continue
        # Check if this segment looks like math (has operator + variables)
        has_math_op = bool(_re.search(r'[=\^\_\+\-\*/<>]', stripped))
        has_var = bool(_re.search(r'[a-zA-Z]', stripped))
        is_pure_digit = _re.match(r'^[\d\s\.\-]+$', stripped)
        if has_math_op and has_var and not is_pure_digit and len(stripped) >= 3:
            # Wrap in $...$
            result.append(part.replace(stripped, '$' + stripped + '$'))
        else:
            result.append(part)

    text = ''.join(result)
    # Restore protected regions
    for i, block in enumerate(protected):
        text = text.replace(f'\x00A{i}\x00', block)

    return text


def _extract_question_preview(text: str, max_len: int = 70) -> str:
    """Strip LaTeX/markdown, return plain text fingerprint of a question."""
    if not text:
        return ""
    s = text
    s = _re.sub(r'\$\$[^$]*\$\$', '', s)
    s = _re.sub(r'\$([^$]+?)\$', r'\1', s)
    s = _re.sub(r'\\[a-zA-Z]+(?:\{[^}]*\})*', '', s)
    s = _re.sub(r'\\begin\{[^}]*\}', '', s)
    s = _re.sub(r'\\end\{[^}]*\}', '', s)
    s = _re.sub(r'\\[;:,.\s]', ' ', s)
    s = s.replace('{', '').replace('}', '')
    s = _re.sub(r'[&_^~]', ' ', s)
    s = _re.sub(r'\s+', ' ', s)
    s = s.strip(' ，。、；：！？\n\r\t0123456789.()（）[]【】')
    s = _re.sub(r'^\s*\$?\d+\.?\$?\s*', '', s)
    s = _re.sub(r'^\s*[（(]\s*\d+\s*[）)]\s*', '', s)
    s = _re.sub(r'\s*本题满分\d+分\s*', '', s)
    if len(s) > max_len:
        s = s[:max_len].rsplit(' ', 1)[0]
    return s.strip()


def _compute_preview_hash(question_text: str) -> str:
    """Stable 8-char hash of normalized question text for dedup/fast search."""
    import hashlib
    normalized = _extract_question_preview(question_text, max_len=200)
    return hashlib.md5(normalized.encode('utf-8', errors='replace')).hexdigest()[:8]


def _compute_render_cost(answer_text: str) -> str:
    """Heuristic render cost: LOW (<500 chars), MEDIUM (500-2000), HIGH (>2000)."""
    length = len(answer_text or '')
    if length < 500:
        return "LOW"
    elif length < 2000:
        return "MEDIUM"
    return "HIGH"


# ═══════════════════════════════════════════════
#  Helpers for thread-safe state access
# ═══════════════════════════════════════════════

def _ss_get(key, default=None, *, _state=None):
    """Read from _state dict (bg thread) or st.session_state (main thread)."""
    if _state is not None:
        return _state.get(key, default)
    return st.session_state.get(key, default)


def _ss_set(key, value, *, _state=None):
    """Write to _state dict (bg thread) or st.session_state (main thread)."""
    if _state is not None:
        _state[key] = value
    else:
        st.session_state[key] = value


def _clear_grading_state():
    """清理所有批改相关的状态，释放内存"""
    keys_to_clear = [
        'grading_result',
        'diagnosis_result',
        'standard_answer',
        'standard_answer_structured',
        'answer_view_mode',
        'grading_triggered',
        '_poll_start',
        'ocr_result',            # OCR 数据可能很大
        'ocr_progress',          # OCR 进度
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    # 清理过期的搜索缓存（5分钟以上）
    import time as _time
    _now = _time.time()
    for key in list(st.session_state.keys()):
        if key.startswith("search_cache_time_"):
            if _now - st.session_state[key] > 300:
                cache_key = "search_cache_" + key[len("search_cache_time_"):]
                st.session_state.pop(key, None)
                st.session_state.pop(cache_key, None)
        elif key.startswith("search_cache_") and key.count("_") == 5:
            # 检查是否有对应的时间戳，如果没有就删除
            pass  # handled above
    # 强制垃圾回收
    import gc
    gc.collect()


def _standard_answer_needs_expansion(answer: str, steps: list, q_type: str,
                                    selected_q: dict = None) -> bool:
    """Return True when the question has no canonical solution yet.

    The canonical solution is the "one-time generation, permanent reuse"
    asset.  Once saved, this function returns False and the LLM is never
    called again for this question.

    This implements the Read-through Cache pattern:
      Cache Miss → AI generate → save canonical → return
      Cache Hit  → return canonical directly
    """
    if steps:
        return False

    # ── Primary check: canonical pool has solutions → never re-expand ──
    pool = (selected_q or {}).get("canonical_solutions") or []
    meta = (selected_q or {}).get("solution_metadata") or {}
    if pool and meta.get("canonical", True) and meta.get("has_steps", True):
        return False  # Already have verified canonical traces with steps → use them
    if meta.get("canonical"):
        # canonical=True 但 has_steps=False → 只有最终答案没有推导，仍需展开
        if meta.get("has_steps") is False:
            return True
        return False  # Legacy single-canonical → never re-expand

    # ── Fallback: legacy checks for pre-metadata answers ──
    text = (answer or "").strip()
    if not text:
        return True

    if '\x00' in text:
        return True

    # Only match multi-char placeholders.  Single "略" is too common in
    # normal Chinese text (策略, 简略, 省略, etc.) and causes false positives.
    placeholders = ("证明略", "解析略", "过程略", "答案略", "方法略")
    if any(p in text for p in placeholders):
        return True
    # Single "略" only when it's clearly a standalone answer placeholder:
    # the entire text is just "略" or "（略）"
    if text in ("略", "（略）", "(略)"):
        return True

    import re
    # Has step markers → genuinely detailed
    if re.search(r'步骤\s*\d+\s*[：:]', text):
        _migrate_to_canonical(selected_q)
        return False

    # ── Metadata-only detection (applies to ALL question types) ──
    # AI sometimes generates ## headings + bullet lists without any derivation.
    # Detect and reject these so the system regenerates a real solution.
    if len(text) >= 150 and re.search(r'##\s*\S+', text):
        has_display_math = bool(re.search(r'\$\$[^$]+\$\$|\\\[[^\]]+\\\]', text))
        has_step_markers = bool(re.search(r'步骤\s*\d+\s*[：:]', text))
        bullet_ratio = len(re.findall(r'^\s*[-*]\s', text, re.MULTILINE)) / max(len(text.split(chr(10))), 1)
        if not has_display_math and not has_step_markers and bullet_ratio > 0.3:
            return True  # Metadata-only → needs real expansion

    # ── MC / fill-in-the-blank: short answers need expansion ──
    if q_type in ("选择题", "填空题"):
        if len(text) >= 250:
            _migrate_to_canonical(selected_q)
            return False
        return True

    # ── 解答题 / 证明题 ──
    if len(text) >= 200:
        _migrate_to_canonical(selected_q)
        return False
    # Legacy _ai_expanded_at tiebreaker → auto-migrate
    if selected_q and selected_q.get("_ai_expanded_at") and len(text) >= 80:
        _migrate_to_canonical(selected_q)
        return False
    return True


def _migrate_to_canonical(selected_q: dict) -> None:
    """Auto-migrate legacy expanded answers to canonical pool format.

    Only migrates when the answer has actual step-by-step derivation content
    (step markers or substantial math).  Skips metadata-only answers.
    """
    if not selected_q or not selected_q.get("question_id"):
        return
    if selected_q.get("canonical_solutions"):
        return
    meta = selected_q.get("solution_metadata") or {}
    if meta.get("canonical") and meta.get("pool_size", 0) > 0:
        return
    try:
        from database.question_db import get_question_path
        path = get_question_path(selected_q["question_id"])
        if not path.exists():
            return
        import json, os, tempfile, re
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("canonical_solutions"):
            return
        ans = data.get("standard_answer", "")
        # Safety: don't migrate metadata-only answers
        has_steps = bool(re.search(r'步骤\s*\d+\s*[：:]', ans))
        has_display_math = bool(re.search(r'\$\$[^$]+\$\$|\\\[[^\]]+\\\]', ans))
        bullet_ratio = len(re.findall(r'^\s*[-*]\s', ans, re.MULTILINE)) / max(len(ans.split(chr(10))), 1)
        if not has_steps and not has_display_math and bullet_ratio > 0.3:
            return  # Metadata-only → don't pollute the pool
        pool = [{
            "solution_id": "default",
            "method_name": "标准解法",
            "semantic_tags": [],
            "standard_answer": ans,
            "generated_by": data.get("solution_metadata", {}).get("generated_by", "legacy"),
            "generated_at": data.get("solution_metadata", {}).get("generated_at", ""),
            "reviewed": False,
        }] if ans else []
        data["canonical_solutions"] = pool
        data["solution_metadata"] = {
            "canonical": True,
            "has_steps": has_steps,
            "pool_size": len(pool),
            "generated_by": "auto-migrated",
            "generated_at": data.get("_ai_expanded_at", ""),
            "reviewed": False,
            "render_version": "v2",
        }
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".json", prefix=".migr_", dir=path.parent,
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception:
        pass


def _verify_answer_consistency(expanded: str, known_answer: str) -> bool:
    """Check whether the AI-generated detailed answer is consistent with the known correct answer.

    Extracts the final answer from the generated text (looking for "最终答案",
    "标准答案", "结论" sections) and compares it against known_answer
    using symbolic comparison. Returns True when consistent or when comparison
    is inconclusive (don't block on uncertain results).
    """
    if not known_answer or not expanded:
        return True  # Can't verify → assume OK

    known = known_answer.strip()
    if not known:
        return True

    import re

    # Extract final answer from generated text — try multiple patterns
    final_candidates = []

    # Pattern 1: "## 标准答案" or "## 最终答案" section
    for section_name in ["标准答案", "最终答案"]:
        m = re.search(
            rf'##\s*{section_name}\s*\n(.*?)(?=\n##|\n\Z|\Z)',
            expanded, re.DOTALL,
        )
        if m:
            final_candidates.append(m.group(1).strip())

    # Pattern 2: "## 结论" section
    m = re.search(r'##\s*结论\s*\n(.*?)(?=\n##|\n\Z|\Z)', expanded, re.DOTALL)
    if m:
        final_candidates.append(m.group(1).strip())

    # Pattern 3: Last LaTeX block in the text (often the final answer)
    latex_blocks = re.findall(r'\$\$([^$]+)\$\$', expanded)
    if latex_blocks:
        final_candidates.append(latex_blocks[-1].strip())
    else:
        inline_blocks = re.findall(r'\$([^$]+)\$', expanded)
        if inline_blocks:
            final_candidates.append(inline_blocks[-1].strip())

    if not final_candidates:
        return True  # Can't extract → assume OK

    # Compare each candidate against known_answer
    from symbolic_executor import quick_compare

    for candidate in final_candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        result = quick_compare(candidate, known)
        if result.get("equivalent"):
            return True  # At least one candidate matches → consistent

    # No candidate matched — this is suspicious. Check if the known answer
    # text appears anywhere in the expanded text (fuzzy match).
    known_clean = re.sub(r'[\s$]+', '', known)[:30]
    expanded_clean = re.sub(r'[\s$]+', '', expanded)
    if known_clean in expanded_clean:
        return True  # Known answer found in text → likely consistent

    return False  # Contradiction detected


def _validate_latex_quality(expanded: str) -> tuple[bool, list[str]]:
    """Validate LaTeX quality of AI-generated detailed answer.

    Returns (is_valid, list_of_issues). Issues are non-fatal warnings about
    potential rendering problems. Only critical issues (unbalanced $$) cause
    rejection.
    """
    issues = []
    if not expanded:
        return True, issues

    import re

    # Check 1: $$ balance (critical — causes rendering failure)
    display_count = len(re.findall(r'\$\$', expanded))
    if display_count % 2 != 0:
        issues.append("$$ 分隔符不平衡，可能无法渲染")
        return False, issues

    # Check 1b: $ balance in non-$$ context (critical)
    text_no_display = re.sub(r'\$\$.*?\$\$', '', expanded, flags=re.DOTALL)
    inline_dollars = text_no_display.count('$')
    if inline_dollars % 2 != 0:
        issues.append("$ 行内分隔符不平衡，部分公式可能断裂")
        return False, issues

    # Check 2: Common corrupted LaTeX patterns
    if '\x0c' in expanded:
        issues.append("检测到损坏的LaTeX字符(form feed)，可能是frac命令断裂")

    # Check 3: Empty \underline{} — won't render
    if re.search(r'\\underline\{\s*\}', expanded):
        issues.append("存在空 \\underline{}，填空线未正确闭合")

    # Check 4: Unclosed \begin without \end
    begins = re.findall(r'\\begin\{(\w+)\}', expanded)
    ends = re.findall(r'\\end\{(\w+)\}', expanded)
    if sorted(begins) != sorted(ends):
        issues.append("\\begin{} 和 \\end{} 不匹配")

    # Check 5: Nested math delimiters — 3+ consecutive $ signs always bad
    if re.search(r'\${3,}', expanded):
        issues.append("检测到嵌套数学分隔符($$$)，可能导致渲染失败")

    # Check 6: Stray backslash — backslash not followed by a known LaTeX command
    # letter, another backslash, or a common LaTeX punctuation escape
    # Valid LaTeX escapes: \$ \% \# \& \_ \{ \} \, \; \: \! \space
    valid_escapes = r'[a-zA-Z\\$%#&_{},;:! \t\n\r\[\]\{\}\(\)\^\~]'
    stray = re.findall(r'(?<!\\)\\(?!' + valid_escapes + r')', expanded)
    if len(stray) > 10:
        issues.append(f"检测到过多孤立反斜杠({len(stray)}处)，LaTeX可能已损坏")

    # Check 7: Minimum length
    if len(expanded.strip()) < 50:
        issues.append("生成内容过短，可能不完整")

    return True, issues  # Non-critical issues don't block


def _solution_to_text(solution: dict) -> str:
    """Build a complete plain/markdown representation from all solution fields."""
    if not solution:
        return ""

    parts = []
    steps = solution.get("steps") or []
    for i, step in enumerate(steps):
        if isinstance(step, dict):
            label = step.get("label") or f"步骤{i + 1}"
            block_parts = []
            if step.get("content"):
                block_parts.append(str(step["content"]))
            for block in step.get("blocks") or []:
                content = block.get("content", "")
                if not content:
                    continue
                if block.get("type") == "latex":
                    block_parts.append(f"$${content}$$" if block.get("display") == "block" else f"${content}$")
                else:
                    block_parts.append(str(content))
            if block_parts:
                parts.append(f"### {label.rstrip('：:')}：\n" + "\n".join(block_parts))
        elif isinstance(step, str) and step.strip():
            parts.append(f"### 步骤{i + 1}：\n{step.strip()}")

    structured = solution.get("_structured") or {}
    if not parts and isinstance(structured, dict):
        for i, step in enumerate(structured.get("steps", [])):
            label = step.get("label") or f"步骤{i + 1}"
            block_parts = []
            for block in step.get("blocks") or []:
                content = block.get("content", "")
                if not content:
                    continue
                if block.get("type") == "latex":
                    block_parts.append(f"$${content}$$" if block.get("display") == "block" else f"${content}$")
                else:
                    block_parts.append(str(content))
            if block_parts:
                parts.append(f"### {label.rstrip('：:')}：\n" + "\n".join(block_parts))

    answer = (solution.get("standard_answer") or "").strip()
    final_answer = ""
    if isinstance(structured, dict):
        fa = structured.get("final_answer") or {}
        if isinstance(fa, dict):
            final_answer = (fa.get("content") or "").strip()

    final = final_answer or answer
    if final:
        parts.append(f"### 最终答案\n{final}")

    return "\n\n".join(parts).strip()


def _cache_detailed_answer(selected_q: dict, expanded: str, model: str = ""):
    """Backward-compatible wrapper for save_as_canonical_solution."""
    save_as_canonical_solution(selected_q, expanded, model=model)


def get_canonical_solutions(selected_q: dict) -> list[dict]:
    """Return all canonical solutions for a question (from pool or legacy)."""
    if not selected_q:
        return []
    pool = selected_q.get("canonical_solutions") or []
    if pool:
        return pool
    # Legacy: single canonical_solution stored in standard_answer
    meta = selected_q.get("solution_metadata") or {}
    if meta.get("canonical") and selected_q.get("standard_answer"):
        return [{
            "solution_id": "default",
            "method_name": "标准解法",
            "semantic_tags": [],
            "steps": selected_q.get("solution_steps", []),
            "standard_answer": selected_q.get("standard_answer", ""),
            "generated_by": meta.get("generated_by", "legacy"),
            "generated_at": meta.get("generated_at", ""),
        }]
    return []


def save_as_canonical_solution(selected_q: dict, expanded: str,
                                model: str = "", method_name: str = "标准解法",
                                semantic_tags: list = None) -> bool:
    """Append a new canonical solution to the question's solution pool.

    Multi-canonical architecture: each question can have multiple valid
    reasoning traces (e.g., 换元法, 定义法, 几何法).  New solutions are
    appended rather than overwriting, forming a self-growing knowledge base.

    Returns True if saved successfully.
    """
    if not selected_q or not expanded:
        return False
    qid = selected_q.get("question_id", "")
    if not qid:
        return False
    try:
        from database.question_db import get_question_path
        path = get_question_path(qid)
        if not path.exists():
            return False
        import json, os, tempfile, re, time as _time

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False

        # LaTeX 验证
        is_valid, issues = _validate_latex_quality(expanded)
        if not is_valid:
            import logging
            logging.getLogger(__name__).warning(
                "Canonical solution has LaTeX issues, not saving: %s", issues)
            return False

        # 拒绝明显的思考草稿（>5000字 或 含"此路不通""另一种思路"等自问自答标记）
        if len(expanded) > 5000 or re.search(r'此路不通|不对，|另一种思路|尝试构造|不行。', expanded):
            import logging
            logging.getLogger(__name__).warning(
                "Canonical solution looks like chain-of-thought draft, not saving: %s", qid)
            return False

        # 步骤标记检查：确保答案包含真正的步骤推导
        # 选择题/填空题接受 display math 作为替代标志
        qtype = data.get("question_type", "")
        has_step_markers = bool(re.search(r'(?:步骤\s*\d+\s*[：:]|第\s*\d+\s*步\s*[：:])', expanded))
        has_display_math = bool(re.search(r'\$\$[^$]+\$\$|\\\[[^\]]+\\\]', expanded))
        is_long_enough = len(expanded.strip()) >= 300
        if not has_step_markers:
            if qtype in ("选择题", "填空题") and (has_display_math or is_long_enough):
                pass  # 选择题/填空题接受 display-math 或长度足够的内容
            else:
                import logging
                logging.getLogger(__name__).warning(
                    "Canonical solution without step markers, not saving: %s", qid)
                return False

        # 迁移原始短答案到 final_answer（仅首次）
        old_answer = data.get("standard_answer", "")
        if not data.get("final_answer") and old_answer and len(old_answer) < 200:
            data["final_answer"] = old_answer

        # Build new solution entry
        new_solution = {
            "solution_id": f"sol_{int(_time.time())}",
            "method_name": method_name,
            "semantic_tags": semantic_tags or [],
            "standard_answer": expanded,
            "generated_by": model or "AI",
            "generated_at": _time.strftime("%Y-%m-%d %H:%M"),
            "reviewed": False,
        }
        if issues:
            new_solution["latex_warnings"] = issues

        # Append to pool (dedup by method_name)
        pool = data.get("canonical_solutions") or []
        # Migrate legacy: if old single-canonical exists, move it into pool
        legacy_meta = data.get("solution_metadata") or {}
        if legacy_meta.get("canonical") and not pool:
            pool.append({
                "solution_id": "default",
                "method_name": "标准解法",
                "semantic_tags": [],
                "standard_answer": data.get("standard_answer", ""),
                "generated_by": legacy_meta.get("generated_by", "legacy"),
                "generated_at": legacy_meta.get("generated_at", ""),
                "reviewed": False,
            })
        # Avoid exact duplicates by method_name
        existing_names = {s.get("method_name", "") for s in pool}
        if method_name not in existing_names:
            pool.append(new_solution)
        # Check if the source answer was a placeholder (证明略 etc.)
        # If so, NEVER mark as canonical — the AI answer needs verification
        _src_ans = (data.get("raw_answer_text") or old_answer or "").strip()
        _is_placeholder = _src_ans in ("证明略", "解析略", "过程略", "答案略", "方法略", "略", "")
        # Update legacy metadata and standard_answer for backward compat
        data["solution_metadata"] = {
            "canonical": not _is_placeholder,  # placeholder源 → 不锁死
            "has_steps": True,
            "pool_size": len(pool),
            "generated_by": model or "AI",
            "generated_at": _time.strftime("%Y-%m-%d %H:%M"),
            "reviewed": False,
            "render_version": "v2",
        }
        data["standard_answer"] = expanded  # latest as default display
        data["canonical_solutions"] = pool

        # 原子写入
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".json", prefix=".canon_", dir=path.parent,
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
            return True
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return False
    except Exception:
        return False


def find_best_canonical_match(student_trace: dict,
                               canonical_solutions: list[dict]) -> dict:
    """Find the canonical solution that best matches the student's reasoning.

    Returns {"solution": best_match, "score": float, "method_name": str}.
    When no canonical solutions exist, returns empty dict.
    """
    if not canonical_solutions or not student_trace:
        return {}
    best = None
    best_score = -1.0
    for sol in canonical_solutions:
        # Simple textual similarity as baseline — graph matching is preferred
        # when available (handled by the caller via Engine C).
        sol_text = sol.get("standard_answer", "")
        stu_text = str(student_trace.get("final_answer", ""))
        if not sol_text or not stu_text:
            continue
        from symbolic_executor import quick_compare
        result = quick_compare(stu_text, sol.get("final_answer", sol_text[:100]))
        score = 1.0 if result.get("equivalent") else 0.0
        if score > best_score:
            best_score = score
            best = sol
    if best:
        return {"solution": best, "score": best_score,
                "method_name": best.get("method_name", "")}
    return {}


class _ThreadSafeStatus:
    """Wraps a Streamlit status object so writes work safely from background threads.
    In a thread, messages are buffered and replayed on the main thread via flush()."""

    def __init__(self, st_status=None):
        self._st_status = st_status
        self._buffer = []

    def write(self, msg: str):
        if self._st_status:
            try:
                self._st_status.write(msg)
            except Exception:
                self._buffer.append(msg)
        else:
            self._buffer.append(msg)

    def flush(self, to_status):
        """Replay buffered messages to a Streamlit status on the main thread."""
        for msg in self._buffer:
            try:
                to_status.write(msg)
            except Exception:
                pass
        self._buffer.clear()


class _NoOpStatus:
    """A status-like object that silently discards all writes.

    Used in background threads where no Streamlit script context exists.
    """
    def write(self, msg: str): pass
    def update(self, *, label=None, state=None, expanded=None): pass


class _NoOpContext:
    """A st-like object whose .status() returns a _NoOpStatus.

    Used as the *container* argument to _execute_grading_process when
    running in a background thread.
    """
    def status(self, label: str, expanded: bool = True) -> _NoOpStatus:
        return _NoOpStatus()


def _parse_steps_from_text(text: str) -> list:
    """从 AI 生成的详细解答文本中提取步骤列表。

    支持多种步骤标记格式：
      - "步骤N：" / "步骤N: "（N 为阿拉伯数字）
      - "第N步：" / "第N步: "
      - "### 步骤N：" / "### 步骤N: "
      - Markdown 标题后的内容块
      - 中文数字：第一步、第二步...
    用于在 from_legacy_text 解析失败时给旧版渲染路径提供兜底。
    """
    if not text:
        return []
    import re

    cn_num_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

    # Pattern: match "步骤N：" / "第N步：" / "### 步骤N：" with Arabic or Chinese numbers
    patterns = [
        # 步骤1： or 步骤1: or ### 步骤1：
        r'(?:###\s*)?步骤\s*(\d+|[一二三四五六七八九十]+)\s*(?:步)?\s*[：:]\s*',
        # 第1步： or 第一步：
        r'第\s*(\d+|[一二三四五六七八九十]+)\s*步\s*[：:]\s*',
    ]

    markers = []
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            num_str = m.group(1)
            if num_str.isdigit():
                step_num = int(num_str)
            else:
                step_num = cn_num_map.get(num_str, 0)
            if step_num > 0:
                markers.append((m.start(), m.end(), step_num))

    # Deduplicate by position and step number
    markers.sort()
    seen_positions = set()
    seen_step_nums = set()
    unique_markers = []
    for start, end, step_num in markers:
        if start in seen_positions or step_num in seen_step_nums:
            continue
        seen_positions.add(start)
        seen_step_nums.add(step_num)
        unique_markers.append((start, end, step_num))

    if not unique_markers:
        return []

    # Find content boundaries: stop at metadata section headings
    boundary_pattern = re.compile(
        r'^#{1,3}\s*(?:关键知识点|易错提示|常见误区|秒杀技巧|结论|题目重述|'
        r'题型补充|标准答案|最终答案|知识点总结|注意事项|解题技巧)\s*$',
        re.MULTILINE,
    )

    steps = []
    for i, (start, end, step_num) in enumerate(unique_markers):
        content_start = end
        if i + 1 < len(unique_markers):
            content_end = unique_markers[i + 1][0]
        else:
            content_end = len(text)

        content = text[content_start:content_end].strip()

        # Strip redundant step number prefix (LLM often outputs
        # "### 步骤1：\n步骤1：xxx" — the content line also has the number)
        content = re.sub(
            rf'^步骤\s*{step_num}\s*(?:步)?\s*[：:]\s*',
            '', content, count=1
        )

        # Trim trailing sections that belong to metadata, not steps
        boundary_match = boundary_pattern.search(content)
        if boundary_match:
            content = content[:boundary_match.start()].strip()

        if content:
            steps.append({"label": f"步骤{step_num}", "content": content})

    return steps


def _build_standard_solution(question, ocr_data, selected_q, client, status,
                             force_expansion: bool = False, *, _state=None, model=None) -> dict:
    """获取/生成标准解答。空作答和正常批改共用同一逻辑。

    _state=None 时使用 st.session_state（主线程），传入 dict 时使用 dict（后台线程）。
    model 参数覆盖 _state 中的 model 配置。
    """
    import re
    cached_answer = selected_q.get("standard_answer", "")
    correct_option = selected_q.get("correct_option", "")
    q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))
    opts = selected_q.get("options") or {}
    _model = model or _ss_get("model", LLM_MODEL, _state=_state)

    _known_answer = cached_answer or ""

    _has_real_steps = bool(re.search(r'步骤\s*\d+\s*[：:]', _known_answer))
    _has_display_math = bool(re.search(r'\$\$[^$]+\$\$|\\\[[^\]]+\\\]', _known_answer))
    _is_metadata_only = (
        bool(re.search(r'##\s*(?:关键知识点|易错提示|常见误区|秒杀技巧)', _known_answer))
        and not _has_real_steps
    )

    if _is_metadata_only:
        _known_answer = ""

    # 检测占位符答案："证明略"、"答案略" 等不是真实答案，必须清空让 LLM 独立求解
    _placeholder_answers = ("证明略", "解析略", "过程略", "答案略", "方法略", "证明见解析", "略")
    if _known_answer.strip() in _placeholder_answers:
        _known_answer = ""

    if q_type == "选择题" and correct_option:
        _is_detailed = _has_real_steps or (_has_display_math and not _is_metadata_only)
        if not _is_detailed:
            if correct_option in opts:
                _known_answer = f"正确选项: {correct_option}. {opts[correct_option]}"
            else:
                _known_answer = f"正确选项: {correct_option}"

    # 判断是否需要 AI 生成详细解答
    _needs_exp = _standard_answer_needs_expansion(
        _known_answer, selected_q.get("solution_steps", []) or [], q_type,
        selected_q=selected_q,
    ) or force_expansion

    # 路径1：缓存够详细 → 直接用
    if not _needs_exp and _known_answer and (len(_known_answer.strip()) > 1 or q_type == "选择题"):
        solution = {
            "success": True,
            "standard_answer": _known_answer,
            "total_score": selected_q.get("score", 10),
            "steps": selected_q.get("solution_steps", []) or [],
        }
        status.write("✓ 标准答案已加载（缓存）")

    # 路径2：有已知答案但太简短 → 直接用 generate_detailed_answer 生成详细版（1次LLM）
    elif _needs_exp and _known_answer and client is not None:
        status.write("⏳ AI 生成详细解答...")
        try:
            full_question_dict = dict(selected_q or {})
            raw_q = selected_q.get("raw_question_text") or selected_q.get("question", question)
            full_question_dict.setdefault("question", raw_q)
            if selected_q.get("options"):
                full_question_dict["question"] += "\n" + "\n".join(
                    f"({key}) {value}" for key, value in sorted(selected_q["options"].items())
                )
            from choice_explainer import generate_detailed_answer
            expanded = generate_detailed_answer(
                question=full_question_dict,
                known_answer=_known_answer,
                question_type=q_type or ocr_data.get("question_type", "解答题"),
                client=client, model=_model,
            )
            solution = {
                "success": True,
                "standard_answer": expanded if expanded else _known_answer,
                "total_score": selected_q.get("score", 10),
                "steps": _parse_steps_from_text(expanded) if expanded else [],
            }
            if expanded:
                # 检测 LLM 空壳：有 ## 标题但全是元数据/结论类，无步骤标记
                _has_step = bool(re.search(r'步骤\s*\d+\s*[：:]', expanded))
                _all_headings = re.findall(r'##\s*(\S+)', expanded)
                _meta_headings = {'关键知识点', '易错提示', '常见误区', '秒杀技巧',
                    '考查知识点', '核心概念', '结论', '总结', '注意', '提示',
                    '分析', '考查内容', '考点', '知识回顾', '预备知识', '思路'}
                _is_empty_shell = (
                    _all_headings
                    and not _has_step
                    and all(h in _meta_headings for h in _all_headings)
                )
                if _is_empty_shell:
                    solution["standard_answer"] = ""
                    solution["steps"] = []
                    solution["_structured"] = {}
                    status.write("⚠️ AI 返回了元数据壳子（无实际推导），尝试降级...")
                else:
                    try:
                        from latex_utils import from_legacy_text
                        solution["_structured"] = from_legacy_text(expanded)
                    except Exception:
                        pass

                if expanded != _known_answer and not _is_empty_shell:
                    consistent = _verify_answer_consistency(expanded, _known_answer)
                    # Always save as canonical — consistency check only
                    # controls the warning, never blocks persistence.
                    _cache_detailed_answer(selected_q, expanded, _model)
                    if not consistent:
                        status.write("⚠️ AI 生成的答案与已知正确答案不完全一致，已保存为参考")
                        solution["_ai_consistency_warning"] = True
                else:
                    status.write("⚠️ AI 未生成新内容，将使用简略答案")
            status.write("✓ 详细解答已生成")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Detailed answer generation failed: %s", exc)
            solution = {
                "success": True,
                "standard_answer": _known_answer or "解答生成失败",
                "total_score": selected_q.get("score", 10), "steps": [],
            }

        # 降级：如果 main answer 仍然太短（AI 生成失败或返回简略答案），
        # 尝试用 SolverAgent 再生成一次。SolverAgent 使用不同的 prompt 路径
        # 可能在主提示词失败时仍然成功。
        # 注意：不能仅用 standard_answer 长度判断（选择题的最终答案本身就短），
        # 必须检查整体内容（steps + _structured + standard_answer）。
        _ans = solution.get("standard_answer", "")
        _steps = solution.get("steps") or []
        _struc = solution.get("_structured") or {}
        _total_content = len(_ans.strip()) + sum(
            len(str(b.get("content", ""))) for s in (_struc.get("steps") or [])
            for b in (s.get("blocks") or []) if isinstance(s, dict)
        ) + sum(len(str(s.get("content", ""))) for s in _steps)
        if _total_content < 80:
            status.write("⏳ 主生成路径未产生详细解答，尝试 SolverAgent 降级...")
            try:
                full_question = question
                if selected_q.get("options"):
                    for key in sorted(selected_q.get("options", {}).keys()):
                        full_question += f"\n({key}) {selected_q['options'][key]}"
                from agents.solver_agent import SolverAgent
                solver = SolverAgent(client, _model)
                fallback_solution = solver.solve(
                    question=full_question,
                    math_type=ocr_data.get("math_type", "数学一"),
                    question_type=q_type or ocr_data.get("question_type", "解答题"),
                    knowledge_point=ocr_data.get("knowledge_point", "未指定"),
                )
                if fallback_solution.get("success"):
                    fb_steps = fallback_solution.get("steps") or []
                    fb_struc = fallback_solution.get("_structured") or {}
                    fb_answer = fallback_solution.get("standard_answer", "")
                    _fb_all = re.findall(r'##\s*(\S+)', fb_answer)
                    _fb_meta = {'关键知识点', '易错提示', '常见误区', '秒杀技巧',
                        '考查知识点', '核心概念', '结论', '总结', '注意', '提示',
                        '分析', '考查内容', '考点', '知识回顾', '预备知识', '思路'}
                    _fb_has_step = bool(re.search(r'步骤\s*\d+\s*[：:]', fb_answer))
                    _fb_is_shell = (_fb_all and not _fb_has_step
                                    and all(h in _fb_meta for h in _fb_all))
                    if _fb_is_shell:
                        solution["standard_answer"] = fb_answer
                        solution["_solver_fallback"] = True
                    else:
                        fb_total = len(fb_answer.strip()) + sum(
                            len(str(b.get("content", ""))) for s in (fb_struc.get("steps") or [])
                            for b in (s.get("blocks") or []) if isinstance(s, dict)
                        ) + sum(len(str(s.get("content", ""))) for s in fb_steps)
                        if fb_total >= 80:
                            solution["standard_answer"] = fb_answer
                            solution["steps"] = fb_steps
                            solution["_structured"] = fb_struc
                            solution["_solver_fallback"] = True
                        status.write("✓ SolverAgent 降级成功，已生成详细解答")
                        _cache_detailed_answer(selected_q,
                            _solution_to_text(fallback_solution) or fb_answer, _model)
            except Exception as _fb_exc:
                logging.getLogger(__name__).warning(
                    "SolverAgent fallback also failed: %s", _fb_exc)

    # 路径3：无任何已知答案 → 文本生成优先（快），空壳时 SolverAgent 降级
    elif client is not None:
        status.write("⏳ AI 生成详细解答...")
        full_question = question
        if selected_q.get("options"):
            for key in sorted(selected_q.get("options", {}).keys()):
                full_question += f"\n({key}) {selected_q['options'][key]}"
        try:
            from choice_explainer import generate_detailed_answer
            expanded = generate_detailed_answer(
                question={"question": full_question},
                known_answer="",
                question_type=q_type or ocr_data.get("question_type", "解答题"),
                client=client, model=_model,
            )
            # 空壳检测
            _has_step = bool(re.search(r'步骤\s*\d+\s*[：:]', expanded or ''))
            _headings = re.findall(r'##\s*(\S+)', expanded or '')
            _meta_set = {'关键知识点', '易错提示', '常见误区', '秒杀技巧',
                '考查知识点', '核心概念', '结论', '总结', '注意', '提示',
                '分析', '考查内容', '考点', '知识回顾', '预备知识', '思路'}
            _is_shell = (_headings and not _has_step
                         and all(h in _meta_set for h in _headings))
            if expanded and len(expanded.strip()) >= 30 and not _is_shell:
                solution = {
                    "success": True,
                    "standard_answer": expanded,
                    "total_score": selected_q.get("score", 10),
                    "steps": _parse_steps_from_text(expanded),
                    "_ai_unverified": True,
                }
                status.write("✓ 详细解答已生成")
            else:
                # 空壳或太短 → SolverAgent 降级
                status.write("⏳ 文本生成不理想，SolverAgent 降级...")
                try:
                    from agents.solver_agent import SolverAgent
                    solver = SolverAgent(client, _model)
                    fb = solver.solve(
                        question=full_question,
                        math_type=ocr_data.get("math_type", "数学一"),
                        question_type=q_type or ocr_data.get("question_type", "解答题"),
                        knowledge_point=ocr_data.get("knowledge_point", "未指定"),
                    )
                    if fb.get("success") and fb.get("standard_answer"):
                        solution = {
                            "success": True,
                            "standard_answer": fb.get("standard_answer", ""),
                            "total_score": selected_q.get("score", 10),
                            "steps": fb.get("steps") or [],
                            "_structured": fb.get("_structured") or {},
                            "_ai_unverified": True,
                        }
                        _cache_detailed_answer(selected_q,
                            _solution_to_text(fb) or fb.get("standard_answer", ""), _model)
                        status.write("✓ SolverAgent 降级成功")
                    else:
                        solution = {
                            "success": True,
                            "standard_answer": expanded or "解答生成失败，请重试",
                            "total_score": selected_q.get("score", 10),
                            "steps": _parse_steps_from_text(expanded) if expanded else [],
                        }
                        status.write("⚠️ SolverAgent 也失败了")
                except Exception:
                    solution = {
                        "success": True,
                        "standard_answer": expanded or "解答生成失败，请重试",
                        "total_score": selected_q.get("score", 10),
                        "steps": _parse_steps_from_text(expanded) if expanded else [],
                    }
                    status.write("⚠️ SolverAgent 异常")
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Detailed answer generation failed: %s", exc)
            solution = {
                "success": True,
                "standard_answer": "解答生成失败",
                "total_score": selected_q.get("score", 10), "steps": [],
            }

    # 路径4：无 API Key → 显示已有内容
    else:
        solution = {
            "success": True,
            "standard_answer": _known_answer or "暂无标准答案（请配置 API Key 以自动生成）",
            "total_score": selected_q.get("score", 10), "steps": [],
        }
        status.write("⚠️ 未配置 API Key，无法生成标准解答")

    # 规范化 LaTeX（仅对 AI 生成的批改内容，不影响题库）
    try:
        from latex_normalizer import normalize_latex_style
        solution["standard_answer"] = normalize_latex_style(solution.get("standard_answer", ""))
        # Unicode 数学符号包裹（π, ≤, →, Δ 等）——仅 AI 生成内容需要
        solution["standard_answer"] = _wrap_unicode_math(solution["standard_answer"])
        # ASCII 数学表达式包裹（B^2=E, a^Tx=0 等）
        solution["standard_answer"] = _wrap_ascii_math(solution["standard_answer"])
        steps = solution.get("steps", [])
        if steps:
            normalized_steps = []
            for s in steps:
                if isinstance(s, dict):
                    if s.get("content"):
                        s["content"] = normalize_latex_style(s.get("content", ""))
                        s["content"] = _wrap_unicode_math(s["content"])
                        s["content"] = _wrap_ascii_math(s["content"])
                    for b in s.get("blocks") or []:
                        if isinstance(b, dict) and b.get("type") == "latex":
                            b["content"] = normalize_latex_style(b.get("content", ""))
                            b["content"] = _wrap_unicode_math(b["content"])
                            b["content"] = _wrap_ascii_math(b["content"])
                elif isinstance(s, str):
                    s = normalize_latex_style(s)
                    s = _wrap_unicode_math(s)
                    s = _wrap_ascii_math(s)
                normalized_steps.append(s)
            solution["steps"] = normalized_steps
    except Exception:
        pass

    _ss_set("standard_answer", solution, _state=_state)
    # 构建 _structured（如果还没有）
    if solution.get("_structured"):
        _ss_set("standard_answer_structured", solution["_structured"], _state=_state)
    else:
        try:
            from latex_utils import from_legacy_text
            raw = _solution_to_text(solution)
            if raw:
                _ss_set("standard_answer_structured", from_legacy_text(raw), _state=_state)
                solution["_structured"] = _ss_get("standard_answer_structured", _state=_state)
        except Exception:
            _ss_set("standard_answer_structured", None, _state=_state)

    return solution


def _execute_grading_process(question, student_ans, ocr_data, selected_q, container=None,
                             *, _state=None, model=None, user_id=None, memory=None,
                             client=None):
    """执行批改流程。

    Args:
        _state: None=使用 st.session_state（主线程），dict=使用 dict（后台线程）
        model: LLM model 名称
        user_id: 用户ID（用于错题本）
        memory: MemoryService 实例（用于错题本）
        client: LLM client（None 则从 _state 获取 API key 自行创建）

    Returns:
        dict: results with keys grading_result, diagnosis_result, standard_answer,
              standard_answer_structured, error_record (for saving to error notebook).
              返回 None 表示前置条件不满足（如无 API key）。
    """
    ctx = container if container is not None else _NoOpContext()
    _model = model or _ss_get("model", LLM_MODEL, _state=_state)
    _user_id = user_id or (_ss_get("auth", {}, _state=_state).get("user_id", ""))
    _memory = memory or _ss_get("memory", _state=_state)

    # 获取或创建 LLM client
    if client is None:
        if _state is not None:
            # 后台线程：从 _state 获取配置自行创建
            api_key = str(_state.get("api_key", "") or "")
            if api_key:
                from llm_client import create_client
                base_url = str(_state.get("base_url", LLM_BASE_URL) or "")
                protocol = str(_state.get("protocol", "openai") or "openai")
                client = create_client(api_key=api_key, base_url=base_url, protocol=protocol)
        else:
            client = get_client()

    # ── 空作答快速通道：只展示标准答案，不进行AI批改和诊断 ──
    # force_expansion=False: if canonical exists, use it; if not, _standard_answer_needs_expansion
    # will naturally return True for short/empty answers, triggering generation.
    if not (student_ans or "").strip():
        status = ctx.status("📖 查看标准答案...", expanded=True)
        solution = _build_standard_solution(question, ocr_data, selected_q, client, status,
                                             force_expansion=False, _state=_state, model=_model)
        if solution is None:
            _ss_set("grading_triggered", False, _state=_state)
            return None

        _ss_set("standard_answer", solution, _state=_state)
        gresult = {
            "success": True, "total": 0, "step_score": 0, "result_score": 0,
            "step_analysis": [], "deductions": [],
            "comment": "未作答，仅查看标准答案",
            "engine": "view_only",
        }
        _q_kps = (selected_q or {}).get("knowledge_points", []) or []
        if not _q_kps:
            _ocr_kp = ocr_data.get("knowledge_point", "") if ocr_data else ""
            _q_kps = [_ocr_kp] if _ocr_kp and _ocr_kp != "未指定" else []
        _q_mistakes = (selected_q or {}).get("common_mistakes", []) or []
        if _q_mistakes and selected_q:
            selected_q["common_mistakes"] = selected_q.get("common_mistakes") or _q_mistakes
        dresult = {
            "error_type": "未作答",
            "root_cause": "学生未输入任何作答内容，建议先尝试独立解题再看答案",
            "is_repeat": False, "repeat_count": 0, "affects_future": False,
            "weak_points": _q_kps[:5],
            "common_mistakes": _q_mistakes[:4],
            "recommendations": [
                "先独立尝试解答，再对照标准答案检查思路",
                f"重点掌握【{'、'.join(_q_kps[:3])}】相关知识点" if _q_kps else "可在错题本中回顾同类题",
                "可对照标准答案逐步骤检查自己的思路差异",
            ],
        }
        _ss_set("grading_result", gresult, _state=_state)
        _ss_set("diagnosis_result", dresult, _state=_state)
        status.write("✓ 完成")
        _ss_set("answer_view_mode", True, _state=_state)
        _ss_set("grading_triggered", False, _state=_state)
        status.update(label="✅ 查看答案完成", state="complete", expanded=False)
        return {
            "grading_result": gresult,
            "diagnosis_result": dresult,
            "standard_answer": solution,
            "standard_answer_structured": _ss_get("standard_answer_structured", _state=_state),
            "error_record": None,
        }

    # client 已在函数开头获取，此处检查是否可用
    if client is None:
        if _state is not None:
            # 后台线程：标记失败
            return None  # caller will handle
        st.warning("请先在「系统设置」中配置 API Key")
        _ss_set("grading_triggered", False, _state=_state)
        return None

    _t_start = time.time()
    status = ctx.status("🔍 正在准备批改...", expanded=True)
    status.write("⏳ 获取标准答案...")
    selected_q = selected_q or _ss_get("selected_question", _state=_state) or {}
    q_type = selected_q.get("question_type", ocr_data.get("question_type", ""))

    # 解答题/证明题：标准答案生成 与 lock_question 可并行
    is_complex = q_type in ("解答题", "证明题")
    solution = None
    _future_solution = None
    _ts_status = None

    if is_complex and selected_q.get("question_id"):
        _ts_status = _ThreadSafeStatus()
        _executor = ThreadPoolExecutor(max_workers=1)
        _future_solution = _executor.submit(
            _build_standard_solution, question, ocr_data, selected_q, client, _ts_status,
            force_expansion=False, _state=_state, model=_model,
        )
        status.write("⏳ 标准答案与规范解并行生成中...")
    else:
        # 选择题和填空题也需要详细解答，方便用户查看标准解法。
        # 但如果题库中已有详细解答则不再强制展开，避免浪费 LLM 调用。
        _cached = selected_q.get("standard_answer", "")
        _cached_detailed = (
            (_cached or "").strip()
            and len(_cached) >= 120
        )
        solution = _build_standard_solution(question, ocr_data, selected_q, client, status,
                                            force_expansion=not _cached_detailed,
                                            _state=_state, model=_model)
        if solution is None:
            _ss_set("grading_triggered", False, _state=_state)
            return None

    # Step 2: 批改 — Engine A 快速路径(选择/填空) vs Engine B LLM路径(解答/证明)
    std_ans = ""
    total_score = 10
    is_fast_path = q_type in ("选择题", "填空题")

    if is_fast_path and not is_complex:
        if _future_solution:
            solution = _future_solution.result()
            _ts_status.flush(status)
        std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
        total_score = solution.get("total_score", 10)
        # Engine A: 规则引擎快速判分 (<100ms, 无LLM调用)
        import re
        stu = (student_ans or "").strip()
        correct_option = selected_q.get("correct_option", "")
        if q_type == "选择题" and correct_option:
            stu_letter = None
            for m in re.finditer(r'[A-D]', stu.upper()):
                stu_letter = m.group(0)
            is_correct = (stu_letter == correct_option)
            score = total_score if is_correct else 0
            gresult = {
                "success": True, "total": score, "step_score": score, "result_score": 0,
                "step_analysis": [], "deductions": [],
                "comment": "正确" if is_correct else f"错误, 正确选项为 {correct_option}",
            }
        else:
            from symbolic_executor import quick_compare, ErrorLevel
            result = quick_compare(stu, std_ans)
            is_correct = result["equivalent"]
            score = total_score if is_correct else 0
            gresult = {
                "success": True, "total": score, "step_score": score, "result_score": 0,
                "step_analysis": [], "deductions": [],
                "comment": "正确" if is_correct else (
                    "计算错误" if result["error_level"] == ErrorLevel.LEVEL_1
                    else "答案错误，请查看标准解法"
                ),
            }
        if is_correct:
            dresult = {
                "error_type": "无错误", "root_cause": "",
                "is_repeat": False, "repeat_count": 0,
                "affects_future": False, "weak_points": [],
            }
        else:
            if q_type == "选择题":
                correct_opt = selected_q.get("correct_option", "")
                dresult = {
                    "error_type": "选择题答案错误",
                    "root_cause": f"正确答案是 {correct_opt}，你选择了 {student_ans[:10]}。请分析每个选项的数学含义。",
                    "is_repeat": False, "repeat_count": 0,
                    "affects_future": False, "weak_points": selected_q.get("knowledge_points", []),
                }
            else:
                dresult = {
                    "error_type": "填空题错误",
                    "root_cause": "答案与标准答案不等价，请查看标准解法了解正确答案。",
                    "is_repeat": False, "repeat_count": 0,
                    "affects_future": False, "weak_points": selected_q.get("knowledge_points", []),
                }
        status.write("✓ 快速批改完成（规则引擎）")
    else:
        # ── 解答题/证明题：lock_question + extract 与标准答案生成并行 ──
        status.write("⏳ 启动图对齐批改引擎...")
        engine_c_ok = False
        _canonical = None
        locked = None
        _trace_result = None
        if selected_q.get("question_id"):
            try:
                from question_locker import lock_question
                from graph_matching import grade_with_graph
                _qdb = _ss_get("question_db", _state=_state)
                locked = lock_question(selected_q, _qdb, client, _model)
                _canonical = locked.get("canonical_trace")

                from student_trace_extractor import extract_student_trace
                from symbolic_executor import build_student_graph_from_trace
                _trace_result = extract_student_trace(
                    student_ans or "", question, client, _model
                )
                student_graph = build_student_graph_from_trace(_trace_result)

                if _future_solution:
                    solution = _future_solution.result()
                    _ts_status.flush(status)
                    _executor.shutdown(wait=False)
                std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
                total_score = solution.get("total_score", 10)
                status.write("✓ 标准答案与规范解就绪")

                best_score = -1.0
                best_gresult = None
                best_method_name = ""
                method_count = 0

                if _canonical and _canonical.is_multimethod():
                    status.write(f"⏳ 多解法图对齐批改中（{_canonical.method_count()}种解法）...")
                else:
                    status.write("⏳ 图对齐批改中...")

                for method in (_canonical.methods if _canonical else []):
                    mg = method.graph
                    if not mg or len(mg.nodes) <= 1:
                        continue
                    method_count += 1
                    try:
                        graph_result = grade_with_graph(
                            student_ans or "", mg,
                            student_graph=student_graph,
                            student_trace=_trace_result,
                        )
                        score = graph_result.get("score", 0)
                        if score > best_score:
                            best_score = score
                            best_gresult = {
                                "success": True,
                                "total": round(score, 1),
                                "step_score": round(score * 0.5, 1),
                                "result_score": round(score * 0.5, 1),
                                "step_analysis": [
                                    {"num": i+1, "content": m.get("label", ""),
                                     "judgment": "正确" if m.get("matched") else "缺失/错误",
                                     "score": f"{m.get('weight', 0):.1f}",
                                     "comment": m.get("error", "")}
                                    for i, m in enumerate(graph_result.get("matched_steps", []))
                                ],
                                "deductions": [],
                                "comment": graph_result.get("error_label", ""),
                                "_engine": "C_graph",
                            }
                            best_method_name = method.method_name
                    except Exception:
                        continue

                if best_gresult is not None:
                    gresult = best_gresult
                    try:
                        from method_classifier import classify_student_method
                        classification = classify_student_method(_trace_result, _canonical)
                        gresult["method_family"] = classification["family_name"]
                        gresult["tier"] = (
                            "t1_fast_path" if (
                                classification["recommendation"] != "semantic_fallback"
                                and _compute_confidence(None, None) > 0.8
                            ) else "t3_graph_match" if classification["recommendation"] != "semantic_fallback"
                            else "t4_semantic_fallback"
                        )
                    except Exception:
                        pass
                    if best_method_name and _canonical:
                        gresult["method_matched"] = best_method_name
                        for m in _canonical.methods:
                            if m.method_name == best_method_name:
                                m.usage_count += 1
                                break

                    if locked.get("standard_answer"):
                        solution["standard_answer"] = locked["standard_answer"]
                        std_ans = _solution_to_text(solution) or solution["standard_answer"]
                    engine_c_ok = True
                    status.write(f"✓ 图对齐批改完成（{method_count}法，最佳匹配: {best_method_name}）")
            except Exception as _e_c:
                logger.error(f"[Engine C 失败] {_e_c}")

        if _future_solution and solution is None:
            solution = _future_solution.result()
            _ts_status.flush(status)
            _executor.shutdown(wait=False)
            std_ans = _solution_to_text(solution) or solution.get("standard_answer", "")
            total_score = solution.get("total_score", 10)

        if not engine_c_ok:
            # Try multi-canonical pool matching before falling back to LLM
            canonical_pool = get_canonical_solutions(selected_q)
            if canonical_pool and _trace_result:
                pool_best = find_best_canonical_match(_trace_result, canonical_pool)
                if pool_best:
                    gresult["method_matched"] = pool_best.get("method_name", "")
                    gresult["_matched_from_pool"] = True
                    status.write(f"✓ 解法池匹配完成（{pool_best.get('method_name', '')}）")
                else:
                    grading = GradingAgent(client, _model)
                    gresult = grading.grade(
                        question=question, standard_answer=std_ans,
                        student_answer=student_ans, total_score=total_score,
                        knowledge_points=ocr_data.get("knowledge_point", ""),
                        difficulty=selected_q.get("difficulty", "中等"),
                        canonical_trace=_canonical,
                    )
                    status.write("✓ LLM批改完成")
            else:
                grading = GradingAgent(client, _model)
                gresult = grading.grade(
                    question=question, standard_answer=std_ans,
                    student_answer=student_ans, total_score=total_score,
                    knowledge_points=ocr_data.get("knowledge_point", ""),
                    difficulty=selected_q.get("difficulty", "中等"),
                    canonical_trace=_canonical,
                )
                status.write("✓ LLM批改完成")

        # Step 3: 诊断（高正确率跳过LLM，直接用本地诊断，节省5-30秒）
        status.write("⏳ 正在诊断分析...")
        _score = gresult.get("total", 0)
        _max = solution.get("total_score", 10)
        _is_high_score = _max > 0 and _score / _max >= 0.9

        if _is_high_score:
            diagnosis = DiagnosisAgent(None, _model)
            history = []
            dresult = diagnosis._local_diagnose(gresult, history)
            status.write("✓ 诊断完成（高分快速通道）")
        else:
            diagnosis = DiagnosisAgent(client, _model)
            history = []
            if _memory and _user_id:
                try:
                    history = _memory.get_errors(
                        user_id=_user_id,
                        knowledge_point=ocr_data.get("knowledge_point", "")
                    )
                except Exception:
                    pass
            dresult = diagnosis.diagnose(
                question=question, student_answer=student_ans,
                standard_answer=std_ans, grading_result=gresult,
                error_history=history,
            )
            status.write("✓ 诊断完成")
    _ss_set("grading_result", gresult, _state=_state)
    _ss_set("diagnosis_result", dresult, _state=_state)
    status.write("⏳ 检查候选方法...")

    # Step 3.5: 候选方法提交 — 高分低匹配时提交到人工审核队列
    try:
        _total = gresult.get("total", 0)
        _max = solution.get("total_score", 10)
        if _total >= _max * 0.85 and selected_q.get("question_id"):
            from trace_evolver import submit_candidate
            if _trace_result and _trace_result.get("steps"):
                submitted = submit_candidate(
                    question_id=selected_q["question_id"],
                    student_trace=_trace_result,
                    score=_total,
                    total_score=_max,
                    existing_trace=_canonical,
                    grading_summary={"comment": gresult.get("comment", ""),
                                     "engine": gresult.get("engine", "")},
                )
                if submitted:
                    gresult["candidate_submitted"] = True
                    status.write("✓ 候选方法已提交审核队列")
    except Exception as _evo_err:
        pass  # 非关键路径

    # Step 3.6: VerifierAgent — post-hoc reasoning quality check.
    #   SolverAgent → generates standard answer   (pure solve)
    #   VerifierAgent → checks bidirectional logic, missing conditions,
    #                    illegal derivations (pure verify)
    #   Renderer → displays results                (pure display)
    try:
        from agents.verifier_agent import VerifierAgent
        verifier = VerifierAgent()
        report = verifier.verify(
            reasoning_text=gresult.get("comment", ""),
            step_analysis=gresult.get("step_analysis", []),
            diagnosis_text=dresult.get("root_cause", ""),
        )
        if not report.passed:
            gresult["_verification"] = report.to_dict()
            gresult["_obligation_warning"] = report.summary
    except Exception:
        pass  # Verification is advisory; never block grading

    status.write("⏳ 保存到错题本...")

    # Step 4: 构建错题记录
    error_record = None
    if gresult.get("total", 0) < solution.get("total_score", 10) * 0.9:
        full_standard_answer = _solution_to_text(solution) or solution.get("standard_answer", "")

        # Prefer structured steps (blocks, LaTeX-aware) over simple steps (content, plain text).
        # 1) _structured from from_legacy_text (blocks format)
        # 2) standard_answer_structured from session state
        # 3) _parse_steps_from_text on the raw answer (simple content format, last resort)
        saved_steps = []
        structured = solution.get("_structured")
        if isinstance(structured, dict) and structured.get("steps"):
            saved_steps = structured["steps"]
        if not saved_steps:
            structured_from_state = _ss_get("standard_answer_structured", _state=_state)
            if isinstance(structured_from_state, dict) and structured_from_state.get("steps"):
                saved_steps = structured_from_state["steps"]
        if not saved_steps:
            raw_answer = solution.get("standard_answer", "")
            if raw_answer:
                saved_steps = _parse_steps_from_text(raw_answer)

        error_record = {
            "question_id": selected_q.get("question_id", ""),
            "math_type": ocr_data.get("math_type", ""),
            "question_type": ocr_data.get("question_type", ""),
            "knowledge_point": ocr_data.get("knowledge_point", ""),
            "knowledge_points": selected_q.get("knowledge_points", []) or dresult.get("knowledge_points", []),
            "difficulty": selected_q.get("difficulty", "中等"),
            "student_answer": student_ans,
            "score": gresult.get("total", 0),
            "max_score": solution.get("total_score", 10),
            "is_correct": gresult.get("total", 0) >= solution.get("total_score", 10) * 0.9,
            "comment": gresult.get("comment", ""),
            "step_analysis": gresult.get("step_analysis", []),
            "method_matched": gresult.get("method_matched", ""),
            "engine": gresult.get("engine", gresult.get("_engine", "unknown")),
            "confidence": gresult.get("confidence", 0.0),
            "obligation_warning": gresult.get("_obligation_warning", ""),
            "error_type": dresult.get("error_type", ""),
            "root_cause": dresult.get("root_cause", ""),
            "weak_points": dresult.get("weak_points", []),
            "recommendations": dresult.get("recommendations", []),
            "common_mistakes": dresult.get("common_mistakes", []),
            "is_repeat_diagnosis": dresult.get("is_repeat", False),
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            # ── 热列表四层字段 ──
            "question_preview": _extract_question_preview(question),
            "question_preview_hash": _compute_preview_hash(question),
            "wrong_reason_short": (dresult.get("root_cause") or dresult.get("error_type") or "答错")[:40],
            "preview": (dresult.get("root_cause") or dresult.get("error_type") or "答错")[:60],
            "semantic_tags": list(set(
                (selected_q.get("knowledge_points") or []) +
                (dresult.get("weak_points") or [])
            ))[:6],
            "render_cost_level": _compute_render_cost(
                solution.get("standard_answer", "")),
        }

        # Save to 错题本.  In the background thread (_state is not None) we
        # defer the actual save to _restore_results_to_session() on the main
        # thread, avoiding a duplicate when both paths write.
        if _memory and _user_id:
            if _state is None:
                # Main thread — save immediately
                try:
                    _memory.add_error_record(_user_id, error_record)
                except Exception:
                    pass
            # Background thread — error_record is returned in results;
            # _restore_results_to_session will save it.
        if _state is not None:
            _state["mistakes_force_reload"] = True
        else:
            st.session_state.mistakes_force_reload = True
        st.session_state["_invalidate_dashboard"] = True

    _elapsed = time.time() - _t_start
    status.write(f"✓ 批改完成！（总耗时 {_elapsed:.1f} 秒）")
    _ss_set("answer_view_mode", True, _state=_state)
    _ss_set("grading_triggered", False, _state=_state)
    status.update(label=f"✅ 批改完成（{_elapsed:.1f}s）", state="complete", expanded=False)

    return {
        "grading_result": gresult,
        "diagnosis_result": dresult,
        "standard_answer": solution,
        "standard_answer_structured": _ss_get("standard_answer_structured", _state=_state),
        "error_record": error_record,
    }


# ═══════════════════════════════════════════════
#  Background grading — runs grading in a daemon
#  thread so the user can leave the page and come
#  back later without losing results.
# ═══════════════════════════════════════════════

def _build_client_from_state(state: dict):
    """Create an LLM client from the flat config stored in *state* (or session_state)."""
    api_key = state.get("api_key", "")
    if not api_key:
        return None
    from llm_client import create_client
    return create_client(
        api_key=str(api_key),
        base_url=str(state.get("base_url", LLM_BASE_URL)),
        protocol=str(state.get("protocol", "openai")),
    )


def _run_grading_bg(task_id: str, task_data: dict):
    """Execute grading in a background thread — writes results to SQLite."""
    try:
        _state = task_data["_state"]
        _model = task_data["model"]
        _user_id = task_data["user_id"]
        _memory = task_data["memory"]
        _client = task_data["client"]

        results = _execute_grading_process(
            question=task_data["question"],
            student_ans=task_data["student_ans"],
            ocr_data=task_data["ocr_data"],
            selected_q=task_data["selected_q"],
            container=None,
            _state=_state,
            model=_model,
            user_id=_user_id,
            memory=_memory,
            client=_client,
        )

        if results is None:
            fail_task(task_id, "LLM client unavailable or grading returned no results")
            return

        complete_task(task_id, results)
    except Exception as exc:
        logger.error(f"Background grading failed for task {task_id}: {exc}")
        logger.error(traceback.format_exc())
        fail_task(task_id, str(exc))


def _submit_grading_async(question, student_ans, ocr_data, selected_q):
    """Create task, start background thread, return task_id.

    Extracts all needed state from st.session_state before spawning the thread.
    Guards against duplicate submission: if user already has a processing task
    that is less than 2 minutes old, re-attach to it instead of creating a new one.
    """
    user_id = st.session_state.auth.get("user_id", "unknown")

    # Guard: re-attach to an existing processing task
    existing = get_recent_task(user_id, minutes=2)
    if existing and existing.get("status") == "processing":
        return existing["task_id"]

    model = st.session_state.get("model", LLM_MODEL)
    memory = st.session_state.get("memory")

    # Create the task row
    task_id = create_task(user_id, question, student_ans, ocr_data, selected_q)

    # Build a plain dict with everything the background thread needs
    _state = {
        "model": model,
        "_client": get_client(),
        "api_key": st.session_state.get("api_key", ""),
        "base_url": st.session_state.get("base_url", LLM_BASE_URL),
        "protocol": st.session_state.get("protocol", "openai"),
        "question_db": st.session_state.get("question_db"),
        "grading_result": None,
        "diagnosis_result": None,
        "standard_answer": None,
        "standard_answer_structured": None,
        "answer_view_mode": False,
        "grading_triggered": False,
        "mistakes_force_reload": False,
    }

    # Use the main thread's already-created client instead of building
    # from scratch (avoids KeyError: 'llm_client' on some servers).
    client = _state.get("_client") or get_client()

    task_data = {
        "_state": _state,
        "question": question,
        "student_ans": student_ans,
        "ocr_data": ocr_data,
        "selected_q": selected_q,
        "model": model,
        "user_id": user_id,
        "memory": memory,
        "client": client,
    }

    thread = threading.Thread(
        target=_run_grading_bg,
        args=(task_id, task_data),
        daemon=True,
    )
    thread.start()

    return task_id


def _restore_results_to_session(task: dict):
    """Load grading results from a SQLite task row into st.session_state."""
    for key, json_key in [
        ("grading_result", "grading_result_json"),
        ("diagnosis_result", "diagnosis_result_json"),
        ("standard_answer", "standard_answer_json"),
        ("standard_answer_structured", "standard_answer_structured_json"),
        ("ocr_result", "ocr_data_json"),
    ]:
        val = task.get(json_key)
        if val:
            try:
                st.session_state[key] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass

    st.session_state["answer_view_mode"] = True

    # Restore selected_question from task
    sq_json = task.get("selected_q_json")
    if sq_json:
        try:
            st.session_state["selected_question"] = json.loads(sq_json)
        except (json.JSONDecodeError, TypeError):
            pass

    # Save error record to 错题本 (deferred from background thread).
    # Guard: skip if a record with the same question_id was already saved
    # in this session (avoids duplicates from multi-path saves).
    error_json = task.get("error_record_json")
    if error_json:
        try:
            error_record = json.loads(error_json)
            if error_record and st.session_state.get("memory"):
                qid = error_record.get("question_id", "")
                _seen = st.session_state.get("_saved_error_qids", set())
                _dedup_key = f"{task['user_id']}:{qid}"
                if _dedup_key not in _seen:
                    _seen.add(_dedup_key)
                    st.session_state["_saved_error_qids"] = _seen
                    st.session_state.memory.add_error_record(
                        task["user_id"], error_record
                    )
                    st.session_state.mistakes_force_reload = True
        except (json.JSONDecodeError, TypeError):
            pass

    # Mark as viewed so it won't be auto-restored again
    mark_viewed(task["task_id"])


# ═══════════════════════════════════════════════
#  Page renderer
# ═══════════════════════════════════════════════

def render_grading_page(db, render_latex):
    """..."""
    st.title("📖 查看答案" if st.session_state.get("answer_view_mode", False) else "📝 AI 批改")

    user_id = st.session_state.auth.get("user_id", "") if st.session_state.get("auth") else ""

    # ── 定期清理过期的批改任务（超过24小时的删除，释放磁盘）──
    try:
        cleanup_old(hours=24)
    except Exception:
        pass

    # ── 从磁盘刷新 selected_question，确保读到最新的 canonical 缓存 ──
    _sq = st.session_state.get("selected_question") or {}
    _sq_id = _sq.get("question_id", "")
    if _sq_id and db:
        try:
            _fresh = db.get(_sq_id)
            if _fresh:
                st.session_state["selected_question"] = _fresh
        except Exception:
            pass

    # ── 换题自动清理：释放上一题的批改结果，节省内存 ──
    selected_q = st.session_state.get("selected_question") or {}
    current_qid = selected_q.get("question_id", "")
    last_graded_qid = st.session_state.get("_last_graded_qid", "")
    if current_qid and last_graded_qid and current_qid != last_graded_qid:
        _clear_grading_state()
    if current_qid:
        st.session_state["_last_graded_qid"] = current_qid

    # ── Recovery: check SQLite for a recent completed task only ──
    # Note: Only recover completed tasks, not processing tasks.
    # Processing tasks from previous sessions may be stale (server crashed).
    # If user wants to retry, they should explicitly click "开始批改".
    if "ocr_result" not in st.session_state and user_id:
        recent = get_recent_task(user_id)
        if recent and recent.get("status") == "completed":
            _restore_results_to_session(recent)
            st.session_state.page = "grading"
            st.rerun()

    # 检查 ocr_result 是否已初始化
    if "ocr_result" not in st.session_state:
        st.session_state.ocr_result = None

    ocr_data = st.session_state.ocr_result

    # 如果 ocr_data 为空，但有选中的题目，尝试从 session state 恢复学生答案
    if ocr_data is None:
        selected_q = st.session_state.get("selected_question")
        if selected_q and isinstance(selected_q, dict) and selected_q.get("question"):
            student_answer_parts = []

            selected_option = st.session_state.get("selected_option")
            q_type = selected_q.get("question_type", "")
            if q_type == "选择题" and selected_option:
                student_answer_parts.append(f"选项: {selected_option}")

            bank_text_answer = st.session_state.get("bank_text_answer", "")
            if bank_text_answer and bank_text_answer.strip():
                student_answer_parts.append(bank_text_answer.strip())

            text_answer = st.session_state.get("a_text", "")
            if text_answer and text_answer.strip() and text_answer != bank_text_answer:
                student_answer_parts.append(text_answer.strip())

            merged_answer = "\n\n".join(student_answer_parts)

            mt = selected_q.get("category", "数学一")
            qt = selected_q.get("question_type", "解答题")
            kps = ", ".join(selected_q.get("knowledge_points", []))

            ocr_data = {
                "success": True,
                "question": selected_q["question"],
                "student_answer": merged_answer,
                "math_type": mt,
                "question_type": qt,
                "knowledge_point": kps,
                "confidence": 1.0,
                "warnings": [],
                "selected_option": selected_option,
            }
            st.session_state.ocr_result = ocr_data
        else:
            st.info("请先在「智能刷题」页面上传或输入题目")
            if st.button("➡️ 前往刷题", key="goto_practice_1"):
                st.session_state.page = "practice"
                st.rerun()
            return

    # 确保 ocr_data 不为空
    if ocr_data is None:
        st.info("请先在「智能刷题」页面上传或输入题目")
        if st.button("➡️ 前往刷题", key="goto_practice_2"):
            st.session_state.page = "practice"
            st.rerun()
        return

    question = ocr_data.get("question", "")
    student_ans = ocr_data.get("student_answer", "")
    answer_view_mode = st.session_state.get("answer_view_mode", False)

    # 题目信息
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.markdown(f"**数学类别**: {ocr_data.get('math_type', '未指定')}")
    mc2.markdown(f"**题型**: {ocr_data.get('question_type', '未识别')}")
    mc3.markdown(f"**知识点**: {ocr_data.get('knowledge_point', '未识别')}")
    mc4.markdown(f"**OCR置信度**: {ocr_data.get('confidence', 0):.0%}")

    # 两栏：题目 + 学生作答
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.caption("📋 题目")
            selected_q = st.session_state.get("selected_question") or {}
            if selected_q and isinstance(selected_q, dict) and selected_q.get("question"):
                from renderers import render_question
                try:
                    render_question(selected_q, show_actions=False)
                except Exception:
                    render_latex(question)
            else:
                render_latex(question)
    with col2:
        with st.container(border=True):
            st.caption("✍️ 学生作答")
            if student_ans:
                try:
                    render_latex(student_ans)
                except Exception:
                    try:
                        from latex_utils import from_legacy_text, render_structured_safe
                        render_structured_safe(from_legacy_text(student_ans))
                    except Exception:
                        st.text(str(student_ans)[:2000])
            else:
                st.markdown("（未作答）")

    # 知识点提示
    selected_q = st.session_state.get("selected_question") or {}
    kp_list = selected_q.get("knowledge_points", [])
    if kp_list:
        kp_tags = " · ".join(kp_list[:6])
        st.caption(f"🏷️ 考查知识点: {kp_tags}")

    # ── Async polling block ──
    pending_task_id = st.session_state.get("pending_task_id")
    if pending_task_id:
        task = get_task(pending_task_id)
        if task is None:
            del st.session_state["pending_task_id"]
            st.rerun()

        # Track when polling started to enforce a 30‑minute timeout
        poll_start = st.session_state.get("_poll_start", 0)
        if poll_start == 0:
            st.session_state["_poll_start"] = time.time()
            poll_start = st.session_state["_poll_start"]

        if task["status"] == "processing":
            elapsed = time.time() - poll_start
            if elapsed > 1800:  # 30 minutes
                fail_task(pending_task_id, "批改超时（超过30分钟未完成），请重试")
                del st.session_state["_poll_start"]
                set_grading_active(False)
                st.rerun()

            # ── Progress bar ──
            from views.components.grading_progress import (
                inject_progress_css, render_progress,
                estimate_smooth_progress, get_expected_grading_seconds,
            )
            inject_progress_css()
            expected_s = get_expected_grading_seconds(selected_q, ocr_data)
            smooth = estimate_smooth_progress(
                elapsed_s=elapsed, status="processing",
                base_progress=task.get("progress", 0),
                expected_s=expected_s, max_before_done=97,
            )
            # Map elapsed to phase
            _phase_map = [
                (10, "prepare", "正在准备题目与作答内容"),
                (25, "solution", "正在生成标准答案与解题步骤"),
                (50, "grading", "正在分析学生作答并进行 AI 批改"),
                (75, "grading", "正在计算得分与扣分点"),
                (90, "diagnosis", "正在分析错误原因与薄弱知识点"),
                (9999, "finalize", "正在整理结果"),
            ]
            _phase, _detail = "grading", "正在批改中…"
            for secs, ph, dt in _phase_map:
                if elapsed < secs:
                    _phase, _detail = ph, dt
                    break
            render_progress(
                progress=smooth, phase=_phase, detail=_detail,
                elapsed_s=int(elapsed),
            )
            time.sleep(1 if elapsed < 60 else 2)
            st.rerun()
        elif task["status"] == "completed":
            del st.session_state["_poll_start"]
            set_grading_active(False)
            _restore_results_to_session(task)
            del st.session_state["pending_task_id"]
            st.rerun()
        elif task["status"] == "failed":
            del st.session_state["_poll_start"]
            set_grading_active(False)
            err_msg = task.get("error_msg", "未知错误")
            # If server restarted mid-task, suggest a fresh retry
            if "Server restarted" in err_msg:
                st.warning("检测到服务曾重启，批改任务已中断。请重新提交。")
            else:
                st.error(f"批改失败: {err_msg}")
            if st.button("🔄 重新批改", key="retry_grading"):
                # Clear the failed task so a fresh one is created
                del st.session_state["pending_task_id"]
                _clear_grading_state()
                st.rerun()
        return

    # ── Auto-submit for "查看解析" (view-only mode) ──
    if st.session_state.pop("_auto_submit_view_solution", None):
        _clear_grading_state()
        task_id = _submit_grading_async(question, student_ans, ocr_data, selected_q)
        st.session_state["pending_task_id"] = task_id
        st.rerun()

    # ── 批改按钮 ──
    if not answer_view_mode and st.button("🔍 开始批改", type="primary", use_container_width=True):
        _clear_grading_state()
        set_grading_active(True)
        # Submit async: create task → start bg thread → store task_id for polling
        task_id = _submit_grading_async(question, student_ans, ocr_data, selected_q)
        st.session_state["pending_task_id"] = task_id
        st.rerun()

    # 结果/处理区域：用占位符统一管理
    result_placeholder = st.empty()

    # 检查是否需要开始批改流程（同步回退 — 当 pending_task_id 未设置时）
    if st.session_state.get("grading_triggered"):
        # 清理上一轮的大对象，释放内存
        _clear_grading_state()
        st.session_state["grading_triggered"] = True  # restore flag
        # Synchronous fallback path (kept for backward compatibility)
        model = st.session_state.get("model", LLM_MODEL)
        user_id = st.session_state.auth.get("user_id", "")
        memory = st.session_state.get("memory")
        client = get_client()

        with result_placeholder.container():
            results = _execute_grading_process(
                question, student_ans, ocr_data, selected_q, container=st,
                model=model, user_id=user_id, memory=memory, client=client,
            )
        if results:
            # Results already written to st.session_state, just need to trigger rerun
            st.rerun()
        return

    # 显示结果 — Card-based layout
    grading_result = st.session_state.get("grading_result")
    if grading_result:
        with result_placeholder.container():
            gr = grading_result
            sa = st.session_state.standard_answer or {}
            dr = st.session_state.diagnosis_result or {}
            total = sa.get("total_score", 10)

            selected_q = st.session_state.get("selected_question") or {}
            knowledge_points = selected_q.get("knowledge_points", []) or ocr_data.get("knowledge_point", "").split(",")

            render_grading_result_cards(
                gr, sa, dr, total,
                knowledge_points=knowledge_points,
                question=selected_q,
                question_db=db,
                solution_expanded=(gr.get("engine") == "view_only"),
            )

        # 释放 _structured 重复副本（已嵌套在 standard_answer 中）
        if "standard_answer_structured" in st.session_state:
            del st.session_state["standard_answer_structured"]

        return  # 提前返回，不执行后续的真题库部分

    # ==================== 真题库 ====================
    st.divider()
    st.subheader("📚 真题库")

    all_knowledge_points = []
    if db:
        try:
            all_knowledge_points = db.get_all_knowledge_points()
        except Exception:
            pass

    selected_kp = st.selectbox(
        "按知识点筛选",
        ["全部"] + sorted(all_knowledge_points),
        key="grading_kp_filter"
    )

    if db and selected_kp != "全部":
        try:
            related_questions = db.search(knowledge_point=selected_kp, limit=3)
            if related_questions:
                st.write(f"**{selected_kp}** 相关题目：")
                for q in related_questions:
                    with st.container(border=True):
                        st.markdown(f"**难度**: {q.get('difficulty', '中等')}")
                        render_latex(q.get("question", ""))
                        if st.button(f"▶️ 练习此题", key=f"practice_{q.get('question_id', '')}", width="stretch"):
                            st.session_state.selected_question = q
                            st.session_state.page = "practice"
                            st.rerun()
            else:
                st.info("暂无相关题目")
        except Exception as e:
            logger.error(f"Failed to fetch related questions: {e}")
            st.error("获取相关题目失败")
