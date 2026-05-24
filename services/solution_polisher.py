"""SolutionPolisher — clean up AI-generated solution text formatting.

Post-processes structured solutions to look like standard exam answers:
  - Strips leading punctuation (，。；：) and bullet markers (•-*) from text blocks
  - Drops punctuation-only blocks and orphan formula numbers like "(1)"
  - Merges adjacent short text blocks
  - Adds sentence periods only to standalone complete sentences
  - Normalizes step labels

Pure functions — no side effects, no LLM calls.
"""

import re as _re

_LEADING_BAD = "，。；：、,.；;：:•-*· "
_SENTENCE_END = ("。", "！", "？", "：", "；", ".", "!", "?", ":", ";")

# Words that are formula prefixes / connectors — too short to be standalone sentences
_CONNECTOR_WORDS = {
    "由", "将", "把", "利用", "因为", "由于", "设", "令", "记",
    "则", "得", "即", "故", "于是", "所以", "其中", "可得",
    "代入", "化简得", "整理得", "移项得", "分解因式得",
    "表示为", "写成", "如下", "有",
}

# Words that typically precede a display formula — don't add period after them
_DISPLAY_PRECEDING = {"得", "为", "如下", "有", "可得", "即", "故", "则", "于是"}


def strip_leading_punctuation(text: str) -> str:
    """Remove orphaned punctuation and bullet markers at the start of a text block."""
    if not text:
        return text
    return str(text).strip().lstrip(_LEADING_BAD).strip()


def strip_bullet_prefix(text: str) -> str:
    """Remove bullet markers like • - * at the start of text."""
    if not text:
        return text
    return str(text).strip().lstrip("•-*· ").strip()


def is_punctuation_only(text: str) -> bool:
    """True if text contains only punctuation / whitespace."""
    return bool(text) and all(
        ch in "，。；：、,.；;：:()（） \n\t" for ch in text
    )


def ensure_sentence_period(text: str) -> str:
    """Add a period if the text block doesn't end with sentence punctuation."""
    if not text:
        return text
    s = str(text).strip()
    if s and not s.endswith(_SENTENCE_END):
        s += "。"
    return s


def is_orphan_formula_number(text: str) -> bool:
    """True if text is just a formula number like '(1)' or '。(1)'."""
    s = str(text or "").strip()
    s = s.lstrip("，。；：、,.；;：:").strip()
    return bool(_re.fullmatch(r"[（(]?\d+[）)]?", s))


def is_inline_latex(block: dict) -> bool:
    """True if block is inline LaTeX."""
    return (isinstance(block, dict) and block.get("type") == "latex"
            and block.get("display", "inline") != "block")


def is_display_latex(block: dict) -> bool:
    """True if block is display/block LaTeX."""
    return (isinstance(block, dict) and block.get("type") == "latex"
            and block.get("display", "inline") == "block")


def should_add_period(text: str, prev_block=None, next_block=None) -> bool:
    """Only add period to standalone complete sentences.

    Don't add period to: connector words, formula prefixes, text near inline LaTeX.
    """
    s = str(text or "").strip()
    if not s or s.endswith(_SENTENCE_END):
        return False
    # Too short to be a standalone sentence
    if len(s) <= 4:
        return False
    # Connector/fragment words
    if s in _CONNECTOR_WORDS:
        return False
    if s.endswith(tuple(_CONNECTOR_WORDS)):
        return False
    # Adjacent to inline LaTeX — this text is part of a compound expression
    if is_inline_latex(prev_block) or is_inline_latex(next_block):
        return False
    # Precedes display formula — not a standalone sentence
    if is_display_latex(next_block) and s.endswith(tuple(_DISPLAY_PRECEDING)):
        return False
    return True


def merge_adjacent_text_blocks(blocks: list[dict]) -> list[dict]:
    """Merge consecutive text blocks, dropping punctuation-only and orphan numbers."""
    merged = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            merged.append(block)
            continue

        content = strip_leading_punctuation(block.get("content", ""))
        if not content or is_punctuation_only(content) or is_orphan_formula_number(content):
            continue

        if merged and merged[-1].get("type") == "text":
            prev = merged[-1]["content"].rstrip()
            merged[-1]["content"] = prev + "，" + content
        else:
            block["content"] = content
            merged.append(block)

    return merged


def normalize_step_labels(solution: dict) -> dict:
    """Ensure all step labels follow '步骤N' format."""
    if not isinstance(solution, dict):
        return solution
    for i, step in enumerate(solution.get("steps", []), 1):
        if isinstance(step, dict):
            step["label"] = f"步骤{i}"
    return solution


def polish_solution(solution: dict) -> dict:
    """Clean up a structured solution dict for standard-answer formatting.

    - Normalizes step labels
    - Strips leading punctuation from text blocks
    - Drops punctuation-only blocks
    - Merges adjacent text blocks
    - Adds sentence periods only to standalone complete sentences (context-aware)
    - Preserves all LaTeX blocks unchanged
    """
    if not isinstance(solution, dict):
        return solution

    solution = normalize_step_labels(solution)

    for step in solution.get("steps", []):
        if not isinstance(step, dict):
            continue
        blocks = step.get("blocks", [])
        # P13-7: split \text{中文} out of latex blocks first
        blocks = split_latex_blocks_with_chinese_text(blocks)
        # Phase 1: merge + drop (no periods)
        blocks = list(blocks)  # copy
        cleaned = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                cleaned.append(block)
                continue
            content = strip_leading_punctuation(block.get("content", ""))
            if not content or is_punctuation_only(content) or is_orphan_formula_number(content):
                continue
            if cleaned and cleaned[-1].get("type") == "text":
                prev = cleaned[-1]["content"].rstrip()
                cleaned[-1]["content"] = prev + "，" + content
            else:
                block["content"] = content
                cleaned.append(block)

        # Phase 2: context-aware periods
        for idx, block in enumerate(cleaned):
            if block.get("type") != "text":
                continue
            prev_b = cleaned[idx - 1] if idx > 0 else None
            next_b = cleaned[idx + 1] if idx + 1 < len(cleaned) else None
            if should_add_period(block["content"], prev_b, next_b):
                block["content"] = ensure_sentence_period(block["content"])

        step["blocks"] = cleaned

    return solution


# ═══════════════════════════════════════════════
#  \text{中文} splitting — P13-7
# ═══════════════════════════════════════════════

_TEXT_CMD_WITH_CHINESE_RE = _re.compile(
    r"\\text\{([^{}]*[一-鿿][^{}]*)\}"
)


def _split_latex_block_by_chinese_text(block: dict) -> list[dict]:
    """Split a latex block containing \\text{中文} into latex + text + latex."""
    if not isinstance(block, dict):
        return [block]
    if block.get("type") != "latex":
        return [block]

    content = str(block.get("content") or "")
    if not _TEXT_CMD_WITH_CHINESE_RE.search(content):
        return [block]

    display = block.get("display", "block")
    out: list[dict] = []
    pos = 0

    for m in _TEXT_CMD_WITH_CHINESE_RE.finditer(content):
        before = content[pos:m.start()].strip(" ，,;；")
        text = m.group(1).strip()
        pos = m.end()

        if before:
            out.append({"type": "latex", "display": display, "content": before})
        if text:
            out.append({"type": "text", "content": text})

    after = content[pos:].strip(" ，,;；")
    if after:
        out.append({"type": "latex", "display": display, "content": after})

    return out or [block]


def split_latex_blocks_with_chinese_text(blocks: list[dict]) -> list[dict]:
    """Apply \\text{中文} splitting to a list of blocks."""
    new_blocks: list[dict] = []
    for block in blocks or []:
        new_blocks.extend(_split_latex_block_by_chinese_text(block))
    return new_blocks
