"""
Migration — 历史题库一次性修复引擎

运行顺序：
1. 双反斜杠修复
2. display 内嵌 inline 修复
3. $$$ 修复
4. display 未闭合修复
5. display 边界修复
6. 子题间距修复
7. 中文标点转英文
8. underline 修复
9. Validation 检查
"""
import json, os, re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('E:/math_tutor/storage/questions/data')

CN_PUNC = {"，": ",", "；": ";", "。": ".", "：": ":", "（": "(", "）": ")"}


def normalize_backslashes(text: str) -> str:
    """\\frac → \\frac, \\begin → \\begin"""
    return re.sub(r'\\\\([a-zA-Z])', r'\\\1', text)


def fix_nested_display_math(text: str) -> str:
    """$$ $...$ $$ → $$...$$"""
    return re.sub(
        r'\$\$\s*\$\s*(.*?)\s*\$\s*\$\$',
        lambda m: f"$$\n{m.group(1).strip()}\n$$",
        text, flags=re.DOTALL
    )


def fix_triple_dollar(text: str) -> str:
    """$$$ → $$ $"""
    return text.replace("$$$", "$$ $")


def fix_unclosed_display(text: str) -> str:
    """odd $$ count → add closing $$"""
    if text.count("$$") % 2 != 0:
        text += "\n$$"
    return text


def fix_subquestion_spacing(text: str) -> str:
    """Ensure blank line before $(N)$"""
    return re.sub(r'([^\n])\n?(\$\(\d+\)\$)', r'\1\n\n\2', text)


def normalize_display_boundary(text: str) -> str:
    """$$ followed by non-punct, non-space → insert newline."""
    return re.sub(r'\$\$([^\s\n,.，。；;:：])', r'$$\n\1', text)


def normalize_chinese_punctuation(text: str) -> str:
    for k, v in CN_PUNC.items():
        text = text.replace(k, v)
    return text


def normalize_blank_underline(text: str) -> str:
    """\\underline{} → \\underline{\\qquad\\qquad}"""
    return re.sub(
        r'\\underline\s*\{\s*\}',
        r'\\underline{\\qquad\\qquad}',
        text
    )


def clean_question(text: str) -> str:
    """Run all migration passes on a single question text."""
    text = normalize_backslashes(text)
    text = fix_nested_display_math(text)
    text = fix_triple_dollar(text)
    text = fix_unclosed_display(text)
    text = normalize_display_boundary(text)
    text = fix_subquestion_spacing(text)
    text = normalize_chinese_punctuation(text)
    text = normalize_blank_underline(text)
    return text


def migrate_database(dry_run: bool = False):
    """Run migration on all questions."""
    fixed_count = 0
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.json'):
            continue
        path = DATA_DIR / fname
        with open(path, 'r', encoding='utf-8') as f:
            q = json.load(f)

        modified = False
        for field in ['question', 'standard_answer']:
            text = q.get(field, '')
            if not text:
                continue
            cleaned = clean_question(text)
            if cleaned != text:
                q[field] = cleaned
                modified = True

        if modified and not dry_run:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(q, f, ensure_ascii=False, indent=2)
            fixed_count += 1
        elif modified:
            fixed_count += 1
            print(f'[dry-run] Would fix: {q["question_id"]}')

    print(f'Migration {"dry-run" if dry_run else "complete"}: {fixed_count} files changed')

    # Validate after migration
    from validator import validate
    errors = 0
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.json'):
            continue
        with open(DATA_DIR / fname, 'r', encoding='utf-8') as f:
            q = json.load(f)
        text = q.get('question', '')
        result = validate(text, strict=False)
        if not result['valid']:
            errors += 1
            print(f'  VALIDATION: {q["question_id"]} — {result["errors"]}')
    print(f'Post-migration validation: {errors} errors')
