"""
格式检测器 — 自动识别考研数学试卷的时代/格式

检测决策树:
  1. OCR乱码率>30% → OCR_DEGRADED
  2. 【答案】+【解析】同在 → HYBRID_2025_PLUS
  3. 【答案】无【解析】 → MODERN_2009_2024
  4. （1）无【N】且年份≤1996 → OLD_1987_1996
  5. 同上1997-2008 → TRANSITIONAL_1997_2008
"""

import re
from dataclasses import dataclass
from enum import Enum, auto


class PaperFormat(Enum):
    OLD_1987_1996 = auto()
    TRANSITIONAL_1997_2008 = auto()
    MODERN_2009_2024 = auto()
    HYBRID_2025_PLUS = auto()
    OCR_DEGRADED = auto()
    UNKNOWN = auto()


@dataclass
class FormatInfo:
    format: PaperFormat
    year: int | None
    math_type: str
    has_inline_answers: bool
    has_inline_solutions: bool
    question_numbering: str  # "section_restart" | "continuous"
    confidence: float
    markers: list[str]
    filename: str = ""


class FormatDetector:
    """检测试卷格式时代"""

    _MODERN_MARKER = re.compile(r'【(\d{1,2})】')
    _ANSWER_MARKER = re.compile(r'【答案】')
    _SOLUTION_MARKER = re.compile(r'【解】|【解析】|【分析】|【详解】')
    _OLD_SECTION = re.compile(r'^#\s*([一二三四五六七八九十]+)[、，]', re.MULTILINE)
    _YEAR_PATTERN = re.compile(r'(\d{4})\s*年')
    _MATH_TYPE_RE = re.compile(r'数学[（(]?\s*([一二三])\s*[)）]?')

    def detect(self, text: str, filename: str = "") -> FormatInfo:
        """主入口：分析文本并返回格式分类"""
        # 提取元信息
        year = self._extract_year(text, filename)
        math_type = self._extract_math_type(text, filename)

        # 判断OCR退化
        if self._is_ocr_degraded(text):
            return FormatInfo(
                format=PaperFormat.OCR_DEGRADED,
                year=year, math_type=math_type,
                has_inline_answers=False, has_inline_solutions=False,
                question_numbering="unknown", confidence=0.9,
                markers=[], filename=filename,
            )

        has_answer = self._has_inline_answers(text)
        has_solution = self._has_inline_solutions(text)
        has_modern = self._has_modern_markers(text)
        numbering = self._detect_numbering_scheme(text)

        markers = []
        if has_answer: markers.append("【答案】")
        if has_solution: markers.append("【解】/【解析】")
        if has_modern: markers.append("【N】")

        # 决策树
        if has_answer and has_solution:
            fmt = PaperFormat.HYBRID_2025_PLUS
            conf = 0.95
        elif has_answer and not has_solution:
            fmt = PaperFormat.MODERN_2009_2024
            conf = 0.90
        elif has_modern and not has_answer:
            fmt = PaperFormat.MODERN_2009_2024
            conf = 0.80
        elif year is not None and year <= 1996:
            fmt = PaperFormat.OLD_1987_1996
            conf = 0.85
        elif year is not None and year <= 2010 and not has_modern:
            # 1997-2010 without 【N】 markers — transitional
            fmt = PaperFormat.TRANSITIONAL_1997_2008
            conf = 0.80
        elif not has_modern:
            # Any year without modern markers — treat as transitional
            fmt = PaperFormat.TRANSITIONAL_1997_2008
            conf = 0.70
        else:
            fmt = PaperFormat.MODERN_2009_2024
            conf = 0.65

        return FormatInfo(
            format=fmt, year=year, math_type=math_type,
            has_inline_answers=has_answer,
            has_inline_solutions=has_solution,
            question_numbering=numbering,
            confidence=conf, markers=markers, filename=filename,
        )

    def _extract_year(self, text: str, filename: str) -> int | None:
        m = self._YEAR_PATTERN.search(text[:300])
        if m:
            y = int(m.group(1))
            if 1987 <= y <= 2026:
                return y
        m = re.search(r'(\d{4})', filename)
        if m:
            y = int(m.group(1))
            if 1987 <= y <= 2026:
                return y
        return None

    def _extract_math_type(self, text: str, filename: str) -> str:
        search_text = text[:300] + filename
        m = self._MATH_TYPE_RE.search(search_text)
        if m:
            ch = m.group(1)
            return {"一": "数学一"}.get(ch, "数学一")
        return "数学一"

    def _has_modern_markers(self, text: str) -> bool:
        return bool(self._MODERN_MARKER.search(text[:500]))

    def _has_inline_answers(self, text: str) -> bool:
        return bool(self._ANSWER_MARKER.search(text))

    def _has_inline_solutions(self, text: str) -> bool:
        return bool(self._SOLUTION_MARKER.search(text))

    def _is_ocr_degraded(self, text: str) -> bool:
        """评估文本是否来自严重损坏的OCR"""
        if len(text) < 20:
            return True
        # 统计有效字符（中英文 + 常见标点 + LaTeX符号）vs 乱码
        valid = 0
        total = 0
        for ch in text:
            if ch in '\n\r\t ':
                continue
            total += 1
            if (ch.isascii() or
                '一' <= ch <= '鿿' or
                '　' <= ch <= '〿' or
                '＀' <= ch <= '￯' or
                ch in '，。、；：？！""''（）【】《》…—～·'):
                valid += 1
        if total == 0:
            return True
        ratio_invalid = 1.0 - (valid / total)
        return ratio_invalid > 0.30

    def _detect_numbering_scheme(self, text: str) -> str:
        """判断题目编号方式"""
        if self._has_modern_markers(text):
            return "continuous"
        if self._OLD_SECTION.search(text):
            return "section_restart"
        return "unknown"
