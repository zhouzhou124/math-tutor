"""
状态+事件 题目分割器（格式无关）

一个状态机，一个转换表，处理所有时代的试卷格式。
FormatInfo 仅用于 post-split 验证，不参与分割逻辑。

事件优先级（显式优先）：
  SECTION_HEADER > ANSWER_MARKER > SOLUTION_MARKER > OPTION_START > QUESTION_START > TEXT_LINE

状态:
  OUTSIDE → IN_SECTION → IN_QUESTION → IN_OPTIONS → IN_ANSWER → IN_SOLUTION → DONE
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto

from .format_detector import FormatInfo, PaperFormat
from .question_splitter import QuestionBlock, SplitResult


# ═══════════════════════════════════════════════
# Event 类型
# ═══════════════════════════════════════════════

class Event(Enum):
    SECTION_HEADER = auto()     # # 一、选择题 / # 二、（本题满分8分）
    QUESTION_START = auto()     # （1）/ (1) / 【1】 / 1．
    OPTION_START = auto()       # A. / (A) / （A）/ A．
    ANSWER_MARKER = auto()      # 【答案】
    SOLUTION_MARKER = auto()    # 【解】 / 【解析】 / 【分析】
    BLANK_LINE = auto()         # 空行
    TEXT_LINE = auto()          # 普通文本/LaTeX
    EOF = auto()                # 结束


# ═══════════════════════════════════════════════
# State 类型
# ═══════════════════════════════════════════════

class State(Enum):
    OUTSIDE = auto()
    IN_SECTION = auto()
    IN_QUESTION = auto()
    IN_OPTIONS = auto()
    IN_ANSWER = auto()
    IN_SOLUTION = auto()
    DONE = auto()


# ═══════════════════════════════════════════════
# Event Detector（格式无关 + 显式优先）
# ═══════════════════════════════════════════════

class EventDetector:
    """从单行文本检测事件。显式标记优先于模式猜测。"""

    # 显式标记 — 最高优先级
    _ANSWER_RE = re.compile(r'^【答案】')
    _SOLUTION_RE = re.compile(r'^【解】|^【解析】|^【分析】|^【详解】')

    # 章节头 — 需要类型关键词或分值标注
    _SECTION_TYPE_RE = re.compile(
        r'^(?:#+\s*)?([一二三四五六七八九十]+)[、，.]\s*'
        r'(填空题|选择题|解答题|证明题|计算题)'
    )
    _SECTION_SCORE_RE = re.compile(
        r'^(?:#+\s*)?([一二三四五六七八九十]+)[、，.]\s*'
        r'(?:（本题满分\d+分）|\(本题满分\d+分\))'
    )
    # 章节头通用: # 一、任意的短标题行
    _SECTION_GENERIC_RE = re.compile(
        r'^(?:#+\s*)?([一二三四五六七八九十]+)[、，.]\s*(.+)'
    )

    # 选项 — 显式优先于题号猜测
    _OPTION_RE = re.compile(r'^[（(]?\s*([A-D])\s*[）).．、]?\s*(.+)')

    # 题号 — 多种模式
    _QNUM_MODERN = re.compile(r'^【(\d{1,2})】')          # 【1】
    _QNUM_PAREN = re.compile(r'^[（(](\d{1,2})[）)]')     # （1）或 (1)
    _QNUM_DOT = re.compile(r'^(\d{1,2})[．.]')              # 1．或 1. (中文无空格)

    @classmethod
    def is_explicit_question_start(cls, line: str) -> bool:
        """检查是否为显式题号（【N】），在答案/解析中不会被误判。"""
        return bool(cls._QNUM_MODERN.match(line.strip()))

    @classmethod
    def is_likely_real_question(cls, line: str) -> bool:
        """判断QUESTION_START行是否可能是真实题目（而非答案内的子引用）。
        真实题目：数字标记后跟≥15字符的实质内容（中文+LaTeX）。
        子引用：数字标记后内容很短（如'泰勒公式'、'把（1）代入'）。
        """
        stripped = line.strip()
        # 【N】 always counts
        if cls._QNUM_MODERN.match(stripped):
            return True
        # Remove the number marker and check remaining length
        remaining = stripped
        remaining = cls._QNUM_PAREN.sub('', remaining)
        remaining = cls._QNUM_DOT.sub('', remaining)
        return len(remaining.strip()) >= 10

    @classmethod
    def detect(cls, line: str) -> Event:
        """检测单行的事件类型。显式优先。"""
        stripped = line.strip()

        # 空行
        if not stripped:
            return Event.BLANK_LINE

        # 显式标记（最高优先）
        if cls._ANSWER_RE.match(stripped):
            return Event.ANSWER_MARKER
        if cls._SOLUTION_RE.match(stripped):
            return Event.SOLUTION_MARKER

        # 章节头（比分值标注先匹配）
        if cls._SECTION_TYPE_RE.match(stripped):
            return Event.SECTION_HEADER
        if cls._SECTION_SCORE_RE.match(stripped):
            return Event.SECTION_HEADER
        # 通用章节头: # 一、xxx (短标题)
        m = cls._SECTION_GENERIC_RE.match(stripped)
        if m and len(stripped) <= 60:
            return Event.SECTION_HEADER

        # 选项
        if cls._OPTION_RE.match(stripped):
            return Event.OPTION_START

        # 题号（现代格式显式标记优先）
        if cls._QNUM_MODERN.match(stripped):
            return Event.QUESTION_START
        if cls._QNUM_PAREN.match(stripped):
            return Event.QUESTION_START
        if cls._QNUM_DOT.match(stripped):
            # 排除年份: 1987. 2024.
            num_str = cls._QNUM_DOT.match(stripped).group(1)
            if 1900 <= int(num_str) <= 2100:
                return Event.TEXT_LINE
            return Event.QUESTION_START

        # 默认文本行
        return Event.TEXT_LINE


# ═══════════════════════════════════════════════
# State Machine
# ═══════════════════════════════════════════════

class StateMachineSplitter:
    """格式无关的状态机分割器。

    用法:
      splitter = StateMachineSplitter()
      result = splitter.split(text, format_info)
      # result 是 SplitResult，与 question_splitter.QuestionSplitter 兼容
    """

    # 题型映射
    _TYPE_MAP = {
        "填空题": "填空题", "选择题": "选择题",
        "解答题": "解答题", "证明题": "证明题",
        "计算题": "解答题",
    }

    def split(self, text: str, format_info: FormatInfo | None = None) -> SplitResult:
        """主入口：分割文本为题目块。"""
        lines = text.split('\n')
        state = State.OUTSIDE
        accumulator = _QuestionAccumulator()
        sections_found: list[dict] = []
        warnings: list[str] = []

        for i, line in enumerate(lines):
            event = EventDetector.detect(line)
            if event == Event.BLANK_LINE:
                accumulator._blank_lines_since_last_text += 1
                continue
            # Save blank-gap before resetting (2+ blank lines = strong break)
            accumulator._had_blank_gap = (accumulator._blank_lines_since_last_text >= 2)
            accumulator._blank_lines_since_last_text = 0
            state = self._transition(state, event, line, accumulator, sections_found, i)

            if state == State.DONE:
                break

        # 刷新最后一道题
        accumulator.flush()

        # Post-processing: 合并碎片 — 答案子步骤被误分割的短文本块
        questions = _merge_fragments(accumulator.questions)

        # Post-split 验证
        if format_info:
            warnings.extend(self._validate(questions, format_info))

        return SplitResult(
            format=format_info.format if format_info else PaperFormat.UNKNOWN,
            year=format_info.year if format_info else None,
            math_type=format_info.math_type if format_info else "数学一",
            sections=sections_found,
            questions=questions,
            orphan_text="",
            warnings=warnings,
        )

    def _transition(self, state: State, event: Event, line: str,
                    acc: '_QuestionAccumulator', sections: list[dict],
                    line_num: int) -> State:
        """核心状态转换表。"""

        # ── OUTSIDE ──
        if state == State.OUTSIDE:
            if event == Event.SECTION_HEADER:
                acc.start_section(_extract_section_name(line))
                return State.IN_SECTION
            elif event == Event.QUESTION_START:
                acc.flush()
                acc.start_question(line)
                return State.IN_QUESTION
            elif event == Event.EOF:
                return State.DONE
            else:
                return State.OUTSIDE  # preamble text, skip

        # ── IN_SECTION ──
        elif state == State.IN_SECTION:
            if event == Event.SECTION_HEADER:
                acc.flush()
                sections.append({"title": acc.current_section or "", "order": len(sections) + 1})
                acc.start_section(_extract_section_name(line))
                return State.IN_SECTION
            elif event == Event.QUESTION_START:
                acc.flush()
                acc.start_question(line)
                return State.IN_QUESTION
            elif event == Event.EOF:
                acc.flush()
                return State.DONE
            else:
                return State.IN_SECTION  # section description text

        # ── IN_QUESTION ──
        elif state == State.IN_QUESTION:
            if event == Event.SECTION_HEADER:
                acc.flush()
                sections.append({"title": acc.current_section or "", "order": len(sections) + 1})
                acc.start_section(_extract_section_name(line))
                return State.IN_SECTION
            elif event == Event.QUESTION_START:
                acc.flush()
                acc.start_question(line)
                return State.IN_QUESTION
            elif event == Event.OPTION_START:
                acc.add_option(line)
                return State.IN_OPTIONS
            elif event == Event.ANSWER_MARKER:
                acc.set_answer(line)
                return State.IN_ANSWER
            elif event == Event.SOLUTION_MARKER:
                acc.set_solution(line)
                return State.IN_SOLUTION
            elif event == Event.EOF:
                acc.flush()
                return State.DONE
            else:
                acc.add_text(line)
                return State.IN_QUESTION

        # ── IN_OPTIONS ──
        elif state == State.IN_OPTIONS:
            if event == Event.OPTION_START:
                acc.add_option(line)
                return State.IN_OPTIONS
            elif event == Event.ANSWER_MARKER:
                acc.set_answer(line)
                return State.IN_ANSWER
            elif event == Event.SOLUTION_MARKER:
                acc.set_solution(line)
                return State.IN_SOLUTION
            elif event == Event.QUESTION_START:
                acc.flush()
                acc.start_question(line)
                return State.IN_QUESTION
            elif event == Event.SECTION_HEADER:
                acc.flush()
                acc.start_section(_extract_section_name(line))
                return State.IN_SECTION
            elif event == Event.EOF:
                acc.flush()
                return State.DONE
            else:
                acc.add_text(line)  # continued option text
                return State.IN_OPTIONS

        # ── IN_ANSWER ──
        elif state == State.IN_ANSWER:
            if event == Event.SOLUTION_MARKER:
                acc.set_solution(line)
                return State.IN_SOLUTION
            elif event == Event.SECTION_HEADER:
                acc.flush()
                acc.start_section(_extract_section_name(line))
                return State.IN_SECTION
            elif event == Event.QUESTION_START:
                # 允许过渡：post-processing 会合并碎片
                acc.flush()
                acc.start_question(line)
                return State.IN_QUESTION
            elif event == Event.EOF:
                acc.flush()
                return State.DONE
            else:
                acc.add_text(line)
                return State.IN_ANSWER

        # ── IN_SOLUTION ──
        elif state == State.IN_SOLUTION:
            if event == Event.SECTION_HEADER:
                acc.flush()
                acc.start_section(_extract_section_name(line))
                return State.IN_SECTION
            elif event == Event.QUESTION_START:
                acc.flush()
                acc.start_question(line)
                return State.IN_QUESTION
            elif event == Event.EOF:
                acc.flush()
                return State.DONE
            else:
                acc.add_text(line)
                return State.IN_SOLUTION

        return state  # fallback

    def _validate(self, questions: list[QuestionBlock], fi: FormatInfo) -> list[str]:
        """Post-split 验证：用 FormatInfo 做合理性检查。"""
        warnings = []
        qc = len(questions)

        # 老格式期望: 15-20题
        if fi.format == PaperFormat.OLD_1987_1996 and qc < 10:
            warnings.append(
                f"OLD格式仅{qc}题（期望≥15）。可能存在未识别的章节头或题号。"
            )

        # 现代格式期望: 20-25题
        if fi.format == PaperFormat.MODERN_2009_2024 and qc < 15:
            warnings.append(
                f"MODERN格式仅{qc}题（期望≥20）。"
            )

        return warnings


# ═══════════════════════════════════════════════
# Question Accumulator
# ═══════════════════════════════════════════════

class _QuestionAccumulator:
    """累积当前题目文本和元数据。"""

    def __init__(self):
        self.questions: list[QuestionBlock] = []
        self._lines: list[str] = []
        self._question_num: int = 0
        self._section_title: str = ""
        self._section_order: int = 0
        self._qtype: str = "解答题"
        self._answer: str = ""
        self._solution: str = ""
        self._options: dict[str, str] = {}
        self._start_line: int = 0
        self._global_num: int = 0
        self._blank_lines_since_last_text: int = 0
        self._had_blank_gap: bool = False

    def last_was_blank(self) -> bool:
        """2+ consecutive blank lines → strong paragraph break."""
        return self._blank_lines_since_last_text >= 2

    @property
    def current_section(self) -> str:
        return self._section_title

    def start_section(self, title: str):
        self._section_title = title
        self._section_order += 1
        self._qtype = _extract_question_type(title)

    def start_question(self, first_line: str):
        self._lines = [first_line]
        self._answer = ""
        self._solution = ""
        self._options = {}

    def add_text(self, line: str):
        self._lines.append(line)

    def add_option(self, line: str):
        self._lines.append(line)
        m = re.match(r'^[（(]?\s*([A-D])\s*[）).．、]?\s*(.+)', line.strip())
        if m:
            self._options[m.group(1)] = m.group(2).strip()

    def set_answer(self, line: str):
        self._lines.append(line)
        # 提取答案内容: 【答案】C  或 【答案】$...$
        content = re.sub(r'^【答案】\s*', '', line.strip())
        self._answer = content

    def set_solution(self, line: str):
        self._lines.append(line)

    def flush(self):
        """将当前累积的文本输出为 QuestionBlock。"""
        if not self._lines:
            return
        raw_text = '\n'.join(self._lines).strip()
        if len(raw_text) < 5:
            self._lines = []
            return

        self._global_num += 1
        # 记录原始首行（用于碎片检测）
        first_line_original = self._lines[0].strip() if self._lines else ''
        # 检查是否为子步骤碎片：首行是 (N) 编号 + 超短 + 无LaTeX + 无答案
        is_substep = bool(
            re.match(r'^[（(]\d{1,2}[）)]', first_line_original) and
            len(raw_text) < 80 and
            '【答案】' not in raw_text and
            '【解】' not in raw_text and
            '$' not in raw_text and       # 无LaTeX → 不是真题目
            '\\' not in raw_text
        )
        # 清理题号前缀，保持纯题目文本
        clean = raw_text
        clean = re.sub(r'^(?:【\d{1,2}】)\s*', '', clean)
        clean = re.sub(r'^[（(]\d{1,2}[）)]\s*', '', clean)
        clean = re.sub(r'^\d{1,2}[．.]\s*', '', clean)

        # 推断题型（如果section未设置）
        qtype = self._qtype or _infer_question_type_from_text(raw_text)

        # 提取内联答案和解析
        inline_ans = ""
        inline_sol = ""
        ans_m = re.search(r'【答案】\s*(.+?)(?=\n\s*【解】|\n\s*【解析】|\n\s*【\d|$)', raw_text, re.DOTALL)
        if ans_m:
            inline_ans = ans_m.group(1).strip()[:500]
        sol_m = re.search(r'(?:【解】|【解析】)\s*(.+?)(?=\n\s*【\d|$)', raw_text, re.DOTALL)
        if sol_m:
            inline_sol = sol_m.group(1).strip()[:2000]

        # 碎片合并：子步骤文本追加到上一题
        if is_substep and self.questions:
            prev = self.questions[-1]
            prev.raw_text += '\n' + clean
            self._lines = []
            self._answer = ''
            self._solution = ''
            self._options = {}
            return

        block = QuestionBlock(
            question_number=self._global_num,
            section_order=self._section_order,
            section_title=self._section_title,
            question_type=qtype,
            raw_text=clean,
            start_pos=0,
            end_pos=len(raw_text),
            candidate_answer=inline_ans or self._answer,
            candidate_solution=inline_sol or self._solution,
            options=dict(self._options),
        )
        self.questions.append(block)
        self._lines = []
        self._answer = ""
        self._solution = ""
        self._options = {}


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════

def _merge_fragments(questions: list[QuestionBlock]) -> list[QuestionBlock]:
    """合并被误分割的答案子步骤碎片。
    规则：如果一道题目的文本很短（<40字符）且以数字标记开头，
    它很可能是上一道题目的答案子步骤，应合并回去。
    """
    if len(questions) <= 1:
        return questions

    merged = []
    for q in questions:
        text = q.raw_text.strip()
        if not merged:
            merged.append(q)
            continue

        # 检查是否为碎片：文本短 + 以子步骤编号开头 + 无独立问题特征
        is_fragment = (
            len(text) < 120 and
            not q.candidate_answer and
            not q.candidate_solution and
            bool(re.match(r'^[（(]\d{1,2}[）)]', text))
        )

        if is_fragment:
            # 合并到上一道题目
            prev = merged[-1]
            prev.raw_text += '\n' + q.raw_text
            if q.candidate_answer:
                prev.candidate_answer = q.candidate_answer
            if q.options:
                prev.options.update(q.options)
        else:
            merged.append(q)

    return merged


def _extract_section_name(line: str) -> str:
    """从行中提取章节名"""
    line = line.strip()
    line = re.sub(r'^#+\s*', '', line)
    return line[:40]


def _extract_question_type(title: str) -> str:
    """从章节标题推理题型"""
    for kw, qt in {
        "填空题": "填空题", "选择题": "选择题",
        "解答题": "解答题", "证明题": "证明题",
        "计算题": "解答题",
    }.items():
        if kw in title:
            return qt
    return "解答题"


def _infer_question_type_from_text(text: str) -> str:
    """从题目文本推理题型"""
    first_line = text.split('\n')[0][:50]
    m = re.match(r'^[（(]?\s*([A-D])\s*[）).．、]', text.strip())
    if m:
        return "选择题"
    if '证明' in first_line or '求证' in first_line:
        return "证明题"
    return "解答题"
