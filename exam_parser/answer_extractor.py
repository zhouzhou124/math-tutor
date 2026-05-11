"""
答案提取器 — 从题目块中提取结构化答案信息

三种来源:
  1. 内联 【答案】 和 【解】/【解析】
  2. 选择题选项解析: A．xxx B．xxx C．xxx D．xxx
  3. 从solution文件匹配（由solution_matcher处理）
"""

import re
from dataclasses import dataclass, field
from .question_splitter import QuestionBlock


@dataclass
class ExtractedAnswer:
    """一道题的结构化答案"""
    short_answer: str = ""           # 简短答案 "C", "2x+y=0", "$\\frac{1}{6}$"
    answer_type: str = ""            # "choice" / "fill_blank" / "expression" / "proof" / "none"
    options: dict[str, str] = field(default_factory=dict)  # {A: "text", ...}
    correct_option: str | None = None  # A/B/C/D
    solution_text: str = ""          # 完整解答/解析
    solution_steps: list[str] = field(default_factory=list)
    confidence: float = 0.0


class AnswerExtractor:
    """从QuestionBlock提取结构化答案"""

    # 内联答案标记
    _ANSWER_BLOCK = re.compile(r'【答案】\s*(.+?)(?=\n\s*【\d|\n\s*【解|\n\s*【解析|\Z)', re.DOTALL)
    _SOLUTION_BLOCK = re.compile(r'【解】\s*(.+?)(?=\n\s*【\d|\Z)', re.DOTALL)
    _ANALYSIS_BLOCK = re.compile(r'【解析】\s*(.+?)(?=\n\s*【\d|\Z)', re.DOTALL)

    # 选择题正确答案
    _CHOICE_ANSWER = re.compile(r'[（(]\s*([A-D])\s*[）)]|\b选\s*([A-D])\b')

    # 选项行
    _OPTION_LINE = re.compile(r'^[（(]?\s*([A-D])\s*[）).．、]?\s*(.+)')

    # 答案类型检测
    _FILL_BLANK_MARKER = re.compile(r'[＝=]\s*(.*?)(?:\n|$)')

    def extract_from_block(self, block: QuestionBlock) -> ExtractedAnswer:
        """从QuestionBlock提取答案"""
        text = block.raw_text
        result = ExtractedAnswer()

        # 1. 检查内联【答案】
        inline_ans = self._extract_inline_answer(text)
        inline_sol = self._extract_inline_solution(text)

        # 如果block已经有预提取的候选答案/解析
        if block.candidate_answer:
            inline_ans = block.candidate_answer
        if block.candidate_solution:
            inline_sol = block.candidate_solution

        # 2. 选择题处理
        if block.question_type == "选择题":
            options = block.options or self._parse_options(text)
            result.options = options
            result.answer_type = "choice"

            # 推断正确答案
            correct = self._infer_correct_option(inline_ans, options)
            if correct:
                result.correct_option = correct
                result.short_answer = correct
                result.confidence = 0.95
            else:
                result.confidence = 0.3
        elif block.question_type == "填空题":
            result.answer_type = "fill_blank"
            result.short_answer = inline_ans
            result.confidence = 0.8 if inline_ans else 0.0
        else:
            result.answer_type = "expression" if block.question_type == "解答题" else "expression"
            result.short_answer = inline_ans
            result.confidence = 0.8 if inline_ans else 0.0

        # 3. 解答文本
        result.solution_text = inline_sol
        if inline_sol:
            result.solution_steps = self._split_solution_steps(inline_sol)

        return result

    def _extract_inline_answer(self, text: str) -> str:
        m = self._ANSWER_BLOCK.search(text)
        return m.group(1).strip()[:500] if m else ""

    def _extract_inline_solution(self, text: str) -> str:
        for marker in [self._SOLUTION_BLOCK, self._ANALYSIS_BLOCK]:
            m = marker.search(text)
            if m:
                return m.group(1).strip()[:2000]
        return ""

    def _parse_options(self, text: str) -> dict[str, str]:
        """从文本解析选择题选项"""
        options = {}
        for line in text.split('\n'):
            m = self._OPTION_LINE.match(line.strip())
            if m:
                letter = m.group(1).strip()
                text_content = m.group(2).strip()
                if letter not in options:
                    options[letter] = text_content
        return options

    def _infer_correct_option(self, answer_text: str, options: dict) -> str | None:
        """从答案文本推断正确选项字母"""
        if not answer_text:
            return None
        # 单字母答案: "B", "C", "A"
        stripped = answer_text.strip()
        if len(stripped) == 1 and stripped in "ABCD":
            return stripped
        # 括号格式: "(C)", "（A）", "选B"
        m = self._CHOICE_ANSWER.search(answer_text)
        if m:
            return m.group(1) or m.group(2)
        # 如果答案文本长度>2，尝试匹配选项内容
        for letter, text in options.items():
            if text and len(answer_text) > 3 and text in answer_text:
                return letter
        return None

    def _split_solution_steps(self, solution_text: str) -> list[str]:
        """将解答文本拆分为解题步骤"""
        if not solution_text:
            return []
        # 按方法分割
        methods = re.split(r'(?:方法[一二三四五六七八九十\d]+[:：]|解法[一二三四五六七八九十\d]+[:：])', solution_text)
        if len(methods) > 1:
            return [m.strip() for m in methods if m.strip()][:8]

        # 按编号分割
        steps = re.split(r'(?:^|\n)\s*(?:\(\d+\)|\d+[\.\、\)]\s*|步骤\s*\d+)', solution_text)
        steps = [s.strip() for s in steps if s.strip()]
        if len(steps) > 1:
            return steps[:8]

        # 按双换行分割
        steps = [s.strip() for s in solution_text.split('\n\n') if s.strip()]
        if len(steps) > 1:
            return steps[:8]

        return [solution_text[:500]]
