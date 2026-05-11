"""
多格式题目分割器 — 将整份试卷文本分割为独立题目块

按格式分派:
  - 老格式(1987-1996): # N、章节头 + （N）题号，每节独立编号
  - 过渡格式(1997-2008): 同上但 (N) 题号 + 连续编号
  - 现代格式(2009-2024): 【N】定位符 + 连续编号
  - 混合格式(2025+): N．题号 + 【答案】+【解析】内联
"""

import re
from dataclasses import dataclass, field
from .format_detector import FormatInfo, PaperFormat


@dataclass
class QuestionBlock:
    """一道独立题目"""
    question_number: int
    section_order: int       # 章节序号（1=一, 2=二, ...）
    section_title: str       # "一、填空题"
    question_type: str       # "选择题"/"填空题"/"解答题"/"证明题"
    raw_text: str            # 完整题目文本（含选项、答案标注）
    start_pos: int           # 在原文中的起始位置
    end_pos: int             # 在原文中的结束位置
    candidate_answer: str = ""       # 内联【答案】内容
    candidate_solution: str = ""     # 内联【解】/【解析】内容
    options: dict[str, str] = field(default_factory=dict)  # {A: "text", B: ...}


@dataclass
class SplitResult:
    format: PaperFormat
    year: int | None
    math_type: str
    sections: list[dict]        # [{title, type, question_count, order}]
    questions: list[QuestionBlock]
    orphan_text: str
    warnings: list[str] = field(default_factory=list)


class QuestionSplitter:
    """按格式分派的题目分割器"""

    # 章节头匹配
    _SECTION_HEADER = re.compile(
        r'^(?:#+\s*)?([一二三四五六七八九十]+)[、，.]\s*'
        r'(填空题|选择题|解答题|证明题|计算题)',
        re.MULTILINE,
    )
    # 也匹配纯题号的章节头: # 一、（本题满分8分）
    _SECTION_HEADER_ALT = re.compile(
        r'^(?:#+\s*)?([一二三四五六七八九十]+)[、，.]\s*(?:（.*?分）)?',
        re.MULTILINE,
    )
    # 老格式题号: （1） (2) (3)  -- 匹配全角/半角括号编号
    _OLD_NUM = re.compile(r'(?:^|\n)\s*[（(](\d{1,2})[）)]\s*')
    # 现代格式题号: 【1】 【22】
    _MODERN_NUM = re.compile(r'【(\d{1,2})】')
    # 混合格式题号: 1． 22． (全角点号) 也兼容 1. 2. 1, 2,
    _HYBRID_NUM = re.compile(r'(?:^|\n)\s*(\d{1,2})[．.、]\s*(?=[^\d]|$)')
    # 答案/解析/选项标记
    _ANSWER_MARKER = re.compile(r'【答案】\s*(.*?)(?=\s*【\d|【解|【解析|【分析|\Z)', re.DOTALL)
    _SOLUTION_MARKER = re.compile(r'【解】\s*(.*?)(?=\s*【答案】|\s*【\d|\Z)', re.DOTALL)
    _ANALYSIS_MARKER = re.compile(r'【解析】\s*(.*?)(?=\s*【答案】|\s*【\d|\Z)', re.DOTALL)
    # 选项: A． A. (A) （A）
    _OPTION_PATTERN = re.compile(
        r'(?:^|\n)\s*[（(]?\s*([A-D])\s*[）).．、]?\s*(.+?)(?=\n\s*[（(]?\s*[A-D]\s*[）).．、]?|\n\s*【答案】|\n\s*$|$)',
        re.DOTALL,
    )

    _TYPE_MAP = {
        "填空题": "填空题",
        "选择题": "选择题",
        "解答题": "解答题",
        "证明题": "证明题",
        "计算题": "解答题",
        "综合题": "解答题",
    }

    def split(self, text: str, format_info: FormatInfo) -> SplitResult:
        """主入口：根据格式信息分割题目"""
        fmt = format_info.format
        year = format_info.year
        math_type = format_info.math_type

        # 按章节分段
        sections = self._split_by_sections(text)

        if not sections:
            # 退化情况：没找到章节头，尝试直接按题号分割
            return self._fallback_split(text, format_info)

        questions = []
        global_num = 0  # 全局连续题号

        for order, (sect_title, sect_body) in enumerate(sections, 1):
            qtype = self._identify_type(sect_title)

            if fmt == PaperFormat.OLD_1987_1996:
                # 老格式：每节独立编号
                blocks = self._split_old_section(sect_body, order, sect_title, restart_numbering=True)
                for b in blocks:
                    b.section_order = order
                    b.section_title = sect_title
                    b.question_type = qtype
                    # 老格式无内联答案
                    questions.append(b)
            elif fmt == PaperFormat.TRANSITIONAL_1997_2008:
                blocks = self._split_old_section(sect_body, order, sect_title, restart_numbering=False)
                for b in blocks:
                    b.section_order = order
                    b.section_title = sect_title
                    b.question_type = qtype
                    b.question_number = global_num + 1
                    global_num += 1
                    questions.append(b)
            elif fmt in (PaperFormat.MODERN_2009_2024, PaperFormat.HYBRID_2025_PLUS):
                blocks = self._split_modern_section(sect_body, order, sect_title)
                for b in blocks:
                    b.section_order = order
                    b.section_title = sect_title
                    b.question_type = qtype
                    b.question_number = global_num + 1
                    global_num += 1
                    # 提取内联答案/解析
                    b.candidate_answer = self._extract_inline_answer(b.raw_text)
                    b.candidate_solution = self._extract_inline_solution(b.raw_text)
                    b.options = self._extract_options(b.raw_text)
                    questions.append(b)
            else:
                # UNKNOWN/OCR: 尝试现代格式
                blocks = self._split_modern_section(sect_body, order, sect_title)
                for b in blocks:
                    b.section_order = order
                    b.section_title = sect_title
                    b.question_type = qtype
                    b.question_number = global_num + 1
                    global_num += 1
                    questions.append(b)

        # 如果题目数异常少，尝试fallback
        if len(questions) < 3 and len(text) > 500:
            warnings = [f"仅分割出{len(questions)}题，可能分割不完整"]

        return SplitResult(
            format=fmt, year=year, math_type=math_type,
            sections=[{"title": s[0], "order": i + 1} for i, s in enumerate(sections)],
            questions=questions,
            orphan_text="",
            warnings=[],
        )

    def _split_by_sections(self, text: str) -> list[tuple[str, str]]:
        """将文本按章节头分割，返回 [(标题, 内容), ...]"""
        # 找到所有章节头位置
        positions = []
        for m in self._SECTION_HEADER.finditer(text):
            positions.append((m.start(), m.end(), m.group(1), m.group(2)))

        if not positions:
            # 尝试备用模式
            for m in re.finditer(
                r'^(?:#+\s*)?([一二三四五六七八九十]+)[、，.]\s*(.+)',
                text, re.MULTILINE,
            ):
                title = m.group(0).strip()
                if len(title) < 50:  # 合理的标题长度
                    positions.append((m.start(), m.end(), m.group(1), m.group(2)))

        if not positions:
            return []

        sections = []
        for i, (start, end, num, type_name) in enumerate(positions):
            next_start = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            body = text[end:next_start].strip()
            title = f"{num}、{type_name}" if type_name else f"{num}、"
            sections.append((title, body))

        return sections

    def _split_old_section(self, section_body: str, order: int,
                           section_title: str, restart_numbering: bool = True) -> list[QuestionBlock]:
        """分割老格式章节（1987-2008）"""
        # 找题号位置: （1）, (2) 等
        positions = []
        for m in self._OLD_NUM.finditer(section_body):
            positions.append((m.start(), m.end(), int(m.group(1))))

        if len(positions) < 2:
            # 可能整个section就是一道大题（如 # 二、（本题满分8分））
            if len(section_body.strip()) > 20:
                return [QuestionBlock(
                    question_number=1 if restart_numbering else 1,
                    section_order=order, section_title=section_title,
                    question_type="解答题",
                    raw_text=section_body.strip(),
                    start_pos=0, end_pos=len(section_body),
                )]
            return []

        # 提取每个题目的文本块
        blocks = []
        for i, (start, end, num) in enumerate(positions):
            next_start = positions[i + 1][0] if i + 1 < len(positions) else len(section_body)
            # 题目标号后面的内容作为本题文本
            q_text = section_body[end:next_start].strip()
            if len(q_text) > 5:
                blocks.append(QuestionBlock(
                    question_number=num if restart_numbering else num,  # 老格式用节内编号
                    section_order=order, section_title=section_title,
                    question_type="",
                    raw_text=q_text,
                    start_pos=end, end_pos=next_start,
                ))

        return blocks

    def _split_modern_section(self, section_body: str, order: int,
                              section_title: str) -> list[QuestionBlock]:
        """分割现代格式章节（2009-2025）"""
        # 先尝试 【N】 标记
        positions = []
        for m in self._MODERN_NUM.finditer(section_body):
            positions.append((m.start(), m.end(), int(m.group(1))))

        if len(positions) >= 2:
            # 使用 【N】 位置分割
            blocks = []
            for i, (start, end, num) in enumerate(positions):
                next_start = positions[i + 1][0] if i + 1 < len(positions) else len(section_body)
                q_text = section_body[start:next_start].strip()
                # 去掉开头的 【N】
                q_text = re.sub(r'^【\d{1,2}】\s*', '', q_text)
                if len(q_text) > 5:
                    blocks.append(QuestionBlock(
                        question_number=num,
                        section_order=order, section_title=section_title,
                        question_type="",
                        raw_text=q_text,
                        start_pos=start, end_pos=next_start,
                    ))
            return blocks

        # 再尝试 N． 标记（混合格式2025+）
        positions2 = []
        for m in self._HYBRID_NUM.finditer(section_body):
            pos = m.start()
            num = int(m.group(1))
            # 过滤掉选项行 (A. B. C. D.) 和章节编号
            line_start = section_body.rfind('\n', 0, pos) + 1
            line = section_body[line_start:pos + 10].strip()
            if re.match(r'^[A-D][．.]', line):
                continue
            positions2.append((pos, m.end(), num))

        if len(positions2) >= 2:
            blocks = []
            for i, (start, end, num) in enumerate(positions2):
                next_pos = positions2[i + 1][0] if i + 1 < len(positions2) else len(section_body)
                q_text = section_body[start:next_pos].strip()
                q_text = re.sub(r'^\d{1,2}[．.]\s*', '', q_text)
                if len(q_text) > 5:
                    blocks.append(QuestionBlock(
                        question_number=num,
                        section_order=order, section_title=section_title,
                        question_type="",
                        raw_text=q_text,
                        start_pos=start, end_pos=next_pos,
                    ))
            return blocks

        # 最后尝试一个section就是一道题（大题目格式）
        text = section_body.strip()
        if len(text) > 20:
            return [QuestionBlock(
                question_number=1,
                section_order=order, section_title=section_title,
                question_type="",
                raw_text=text,
                start_pos=0, end_pos=len(section_body),
            )]
        return []

    def _fallback_split(self, text: str, format_info: FormatInfo) -> SplitResult:
        """无章节头时的退化分割"""
        # 直接用【N】或题号分割全文
        section_title = "全文"
        order = 1

        # 尝试【N】模式
        blocks = self._split_modern_section(text, order, section_title)
        if blocks:
            return SplitResult(
                format=format_info.format,
                year=format_info.year, math_type=format_info.math_type,
                sections=[{"title": section_title, "order": 1}],
                questions=blocks, orphan_text="",
                warnings=["无章节头，直接按题号分割"],
            )

        return SplitResult(
            format=format_info.format,
            year=format_info.year, math_type=format_info.math_type,
            sections=[], questions=[], orphan_text=text,
            warnings=["无法分割：未找到章节头或题号"],
        )

    def _identify_type(self, section_title: str) -> str:
        """从章节标题识别题型"""
        for keyword, qtype in self._TYPE_MAP.items():
            if keyword in section_title:
                return qtype
        return "解答题"

    def _extract_inline_answer(self, block_text: str) -> str:
        """提取内联【答案】"""
        m = self._ANSWER_MARKER.search(block_text)
        return m.group(1).strip()[:500] if m else ""

    def _extract_inline_solution(self, block_text: str) -> str:
        """提取内联【解】/【解析】"""
        for marker in [self._SOLUTION_MARKER, self._ANALYSIS_MARKER]:
            m = marker.search(block_text)
            if m:
                return m.group(1).strip()[:2000]
        return ""

    def _extract_options(self, block_text: str) -> dict[str, str]:
        """提取选择题选项 {A: "text", B: "text", ...}"""
        options = {}
        lines = block_text.split('\n')
        for line in lines:
            line = line.strip()
            # A．xxx  A. xxx  (A)xxx  （A）xxx
            m = re.match(r'^[（(]?\s*([A-D])\s*[）).．、]?\s*(.+)', line)
            if m:
                letter = m.group(1)
                text = m.group(2).strip()
                if letter not in options:
                    options[letter] = text
        return options
