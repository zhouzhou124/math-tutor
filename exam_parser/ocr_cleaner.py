"""
OCR乱码清理器 — 处理严重损坏的OCR文本

两种策略:
  1. 规则驱动: 已知OCR错误映射 + 乱码字符过滤 + LaTeX修复
  2. LLM辅助: 当客户端可用时，用LLM做上下文感知清理
"""

import re
from dataclasses import dataclass, field
from .latex_fixer import LaTeXFixer


@dataclass
class OCRReport:
    original: str
    cleaned: str
    quality_before: float
    quality_after: float
    chars_fixed: int
    sections_detected: int
    questions_detected: int
    needs_manual_review: bool
    warnings: list[str] = field(default_factory=list)


class OCRCleaner:
    """OCR乱码清理器"""

    # 已知OCR错误符号映射（在文本环境中）
    _SYMBOL_MAP = {
        '∫': r'\int',
        '∬': r'\iint',
        '∭': r'\iiint',
        '∮': r'\oint',
        '∞': r'\infty',
        '±': r'\pm',
        '→': r'\to',
        '∂': r'\partial',
        '∑': r'\sum',
        '∏': r'\prod',
        '≤': r'\leq',
        '≥': r'\geq',
        '≠': r'\neq',
        '≈': r'\approx',
        '≡': r'\equiv',
        '∈': r'\in',
        '∉': r'\notin',
        '⊂': r'\subset',
        '⊃': r'\supset',
        '∀': r'\forall',
        '∃': r'\exists',
        '∠': r'\angle',
        '°': r'^\circ',
        '×': r'\times',
        '⋅': r'\cdot',
        '…': r'\dots',
    }

    # 乱码字符
    _GARBLED_REPLACEMENT = re.compile(r'[�￾￿]')
    _NON_STANDARD_PATTERN = re.compile(r'[^\x00-\x7F一-鿿　-〿＀-￯\n\r\t\$\{\}\\\[\]\(\)\_\^\+\-\*\/\=\.\,\;\:\!\?\@\#\%\&]')

    def __init__(self, llm_client=None, model: str = "deepseek-chat"):
        self.client = llm_client
        self.model = model
        self.latex_fixer = LaTeXFixer()

    def clean(self, text: str, use_llm: bool = True) -> OCRReport:
        """主入口：清理OCR文本"""
        quality_before = self._assess_quality(text)

        if use_llm and self.client:
            cleaned = self._clean_llm(text)
        else:
            cleaned = self._clean_rule_based(text)

        quality_after = self._assess_quality(cleaned)

        return OCRReport(
            original=text, cleaned=cleaned,
            quality_before=quality_before,
            quality_after=quality_after,
            chars_fixed=max(0, len(text) - len(cleaned)),
            sections_detected=self._detect_sections(cleaned),
            questions_detected=self._detect_questions(cleaned),
            needs_manual_review=(quality_after < 0.5),
            warnings=[] if quality_after >= 0.3 else ["文本质量仍然较低，建议人工检查"],
        )

    def _clean_rule_based(self, text: str) -> str:
        """规则驱动清理"""
        # 1. 删除替换字符
        text = self._GARBLED_REPLACEMENT.sub('', text)

        # 2. 替换已知OCR符号
        for sym, latex in self._SYMBOL_MAP.items():
            if sym in text:
                text = text.replace(sym, latex)

        # 3. 标准化空白
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 4. 修复OCR导致的常见单词拼接
        # "选择 题" → "选择题"
        text = re.sub(r'(选择|填空|解答|证明|计算)\s+(题)', r'\1\2', text)

        # 5. LaTeX修复
        latex_report = self.latex_fixer.fix(text, ocr_mode=True)
        return latex_report.fixed

    def _clean_llm(self, text: str) -> str:
        """LLM辅助清理"""
        try:
            from prompts.system_prompts import OCR_CLEANUP_PROMPT
            prompt = OCR_CLEANUP_PROMPT.format(ocr_raw=text[:3000])

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "请清理这份OCR识别结果。"},
                ],
                temperature=0.1,
                max_tokens=4096,
            )
            cleaned = response.choices[0].message.content

            # 尝试解析LLM输出中的题干和作答
            q_match = re.search(r'##\s*题干\s*\n(.*?)(?=##\s*学生作答|\Z)', cleaned, re.DOTALL)
            if q_match:
                return q_match.group(1).strip()

            return cleaned
        except Exception:
            return self._clean_rule_based(text)

    def _assess_quality(self, text: str) -> float:
        """评估文本质量 0-1"""
        if not text or len(text) < 20:
            return 0.0

        total_chars = 0
        valid_chars = 0
        for ch in text:
            if ch in '\n\r\t ':
                continue
            total_chars += 1
            if (ch.isascii() or
                '一' <= ch <= '鿿' or
                '　' <= ch <= '〿' or
                '＀' <= ch <= '￯'):
                valid_chars += 1

        if total_chars == 0:
            return 0.0

        ratio = valid_chars / total_chars
        # 额外加分项：有章节头、有LaTeX $
        bonus = 0.0
        if re.search(r'[一二三四五六七八九十]+[、，.]\s*(?:填空|选择|解答|证明|计算)', text):
            bonus += 0.1
        if '$' in text:
            bonus += 0.05

        return min(1.0, ratio + bonus)

    def _detect_sections(self, text: str) -> int:
        """检测可识别的章节头数量"""
        pattern = re.compile(r'[一二三四五六七八九十]+[、，.]\s*(?:填空|选择|解答|证明|计算)', re.MULTILINE)
        return len(pattern.findall(text))

    def _detect_questions(self, text: str) -> int:
        """检测可识别的题目标记数量"""
        count = 0
        count += len(re.findall(r'【(\d{1,2})】', text))
        count += len(re.findall(r'(?:^|\n)\s*[（(](\d{1,2})[）)]', text))
        count += len(re.findall(r'(?:^|\n)\s*(\d{1,2})[．.]\s', text))
        return max(count, 0)
