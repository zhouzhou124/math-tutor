"""parsing_layer.py — 解析层 (Parsing Layer)

负责将文本转换为 AST（抽象语法树）

支持的题型：
  - 选择题：识别 A/B/C/D 选项
  - 填空题：识别下划线标记的空格
  - 解答题：识别步骤1、步骤2、步骤3
  - 证明题：识别证明步骤

架构：
  ┌─────────────────────────────────────────────────────────────┐
  │                    Parsing Layer                              │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │  │ ChoiceParser │  │  FillParser  │  │SolutionParser│     │
  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
  │         │                 │                  │              │
  │         └─────────────────┼──────────────────┘              │
  │                           ▼                                   │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │                  UnifiedParser                          │  │
  │  │            (自动识别题型并分发)                       │  │
  │  └───────────────────────────────────────────────────────┘  │
  │                           │                                   │
  │                           ▼                                   │
  │  ┌───────────────────────────────────────────────────────┐  │
  │  │                    QuestionAST                          │  │
  │  └───────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────┘
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum


# ═══════════════════════════════════════════════
# 题型枚举
# ═══════════════════════════════════════════════

class QuestionType(Enum):
    """题型枚举"""
    CHOICE = "choice"           # 选择题
    FILL = "fill"               # 填空题
    SOLUTION = "solution"       # 解答题
    PROOF = "proof"             # 证明题
    UNKNOWN = "unknown"          # 未知题型


# ═══════════════════════════════════════════════
# 解析结果
# ═══════════════════════════════════════════════

@dataclass
class ParsedChoice:
    """选择题解析结果"""
    stem: str
    options: List[Dict[str, str]]  # [{"label": "A", "content": "..."}]
    correct_answer: str = ""


@dataclass
class ParsedFill:
    """填空题解析结果"""
    stem: str
    blanks: List[Dict[str, Any]]  # [{"position": 0, "blank": "___", "expected": "..."}]
    correct_answers: List[str] = field(default_factory=list)


@dataclass
class ParsedStep:
    """解答步骤解析结果"""
    label: str           # "步骤1"
    content: str         # 步骤内容
    operation: str = ""  # 操作类型（可选）
    sub_steps: List['ParsedStep'] = field(default_factory=list)  # 子步骤


@dataclass
class ParsedSolution:
    """解答题解析结果"""
    stem: str
    steps: List[ParsedStep] = field(default_factory=list)
    final_answer: str = ""
    sub_parts: Dict[str, 'ParsedSolution'] = field(default_factory=dict)  # 多问题目


@dataclass
class ParsedProof:
    """证明题解析结果"""
    stem: str
    proof_steps: List[ParsedStep] = field(default_factory=list)
    target: str = ""  # 待证明结论


@dataclass
class ParsingResult:
    """统一解析结果"""
    question_type: QuestionType
    raw_text: str
    parsed: Any  # ParsedChoice | ParsedFill | ParsedSolution | ParsedProof
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0


# ═══════════════════════════════════════════════
# 选择题解析器
# ═══════════════════════════════════════════════

class ChoiceParser:
    """选择题解析器"""

    # 选项标签模式
    OPTION_PATTERNS = [
        # $(A)$ 格式
        re.compile(r'\$\(\\left\(\\mathrm\{([A-D])\}\\right\)\)\$'),
        # $(A)$ 简洁格式
        re.compile(r'\$\(([A-D])\)\$'),
        # (A) 中文括号
        re.compile(r'[（(]\s*([A-D])\s*[）)]'),
        # A. 或 A、
        re.compile(r'^([A-D])[.．、]\s*', re.MULTILINE),
        # $A$ 格式
        re.compile(r'\$([A-D])\$'),
    ]

    # 分隔符模式（在选项之间）
    SEPARATOR_PATTERNS = [
        r'\\qquad',
        r'\\quad',
        r'\s{4,}',  # 4个以上空格
        r'\n\n',    # 双换行
    ]

    @classmethod
    def parse(cls, text: str, options: Dict[str, str] = None) -> ParsedChoice:
        """
        解析选择题文本

        Args:
            text: 原始文本
            options: 可选的已知选项字典 {"A": "选项A内容", ...}

        Returns:
            ParsedChoice
        """
        # 如果有已知选项，使用已知选项
        if options and isinstance(options, dict) and len(options) >= 2:
            stem = cls._extract_stem(text)
            parsed_options = [{"label": label, "content": content}
                            for label, content in options.items()
                            if label.upper() in "ABCD"]
            return ParsedChoice(stem=stem, options=parsed_options)

        # 从文本中提取选项
        stem, raw_options = cls._extract_from_text(text)

        # 如果提取到至少2个选项，使用提取结果
        if len(raw_options) >= 2:
            return ParsedChoice(stem=stem, options=raw_options)

        # 回退：尝试其他模式
        stem, raw_options = cls._extract_with_fallback(text)
        return ParsedChoice(stem=stem, options=raw_options)

    @classmethod
    def _extract_stem(cls, text: str) -> str:
        """提取题干（移除选项部分）"""
        # 尝试找到第一个选项标记的位置
        first_option_pos = len(text)

        for pattern in cls.OPTION_PATTERNS:
            matches = list(pattern.finditer(text))
            if matches:
                first_option_pos = min(first_option_pos, matches[0].start())

        if first_option_pos < len(text):
            stem = text[:first_option_pos].strip()
        else:
            stem = text

        # 清理题号前缀
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', stem)
        stem = re.sub(r'^\s*[（(]\s*\d+\s*[）)]\s*', '', stem)

        return stem.strip()

    @classmethod
    def _extract_from_text(cls, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """从文本中提取选项"""
        # 预处理：替换分隔符
        processed = text
        for sep in cls.SEPARATOR_PATTERNS:
            processed = re.sub(sep, '\n', processed)

        options = []
        lines = processed.split('\n')

        current_option = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否为选项行
            matched_label = None
            for pattern in cls.OPTION_PATTERNS:
                m = pattern.match(line)
                if m:
                    matched_label = m.group(1)
                    break

            if matched_label:
                # 保存上一个选项
                if current_option and current_content:
                    content = ' '.join(current_content).strip()
                    options.append({"label": current_option, "content": content})

                current_option = matched_label
                # 移除选项标签，保留内容
                content_part = line
                for pattern in cls.OPTION_PATTERNS:
                    content_part = pattern.sub('', content_part)
                current_content = [content_part.strip()]
            elif current_option:
                # 继续添加内容
                current_content.append(line)

        # 保存最后一个选项
        if current_option and current_content:
            content = ' '.join(current_content).strip()
            options.append({"label": current_option, "content": content})

        # 提取题干
        stem = cls._extract_stem(text)

        # 去重（按label）
        seen = set()
        deduped = []
        for opt in options:
            if opt["label"] not in seen:
                seen.add(opt["label"])
                deduped.append(opt)

        return stem, deduped

    @classmethod
    def _extract_with_fallback(cls, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """备用提取方法"""
        # 尝试匹配所有选项标签
        all_labels = set()
        for pattern in cls.OPTION_PATTERNS:
            matches = pattern.findall(text)
            all_labels.update(matches)

        if len(all_labels) >= 2:
            # 找到了多个选项，尝试按位置分割
            positions = []
            for pattern in cls.OPTION_PATTERNS:
                for m in pattern.finditer(text):
                    positions.append((m.start(), m.group(1) if m.lastindex else m.group(0)))

            positions.sort()
            stem = text[:positions[0][0]].strip()

            options = []
            for i, (pos, label) in enumerate(positions):
                next_pos = positions[i + 1][0] if i + 1 < len(positions) else len(text)
                content = text[pos:next_pos].strip()
                # 清理标签
                for pattern in cls.OPTION_PATTERNS:
                    content = pattern.sub('', content)
                options.append({"label": label, "content": content.strip()})

            return stem, options

        return text, []


# ═══════════════════════════════════════════════
# 填空题解析器
# ═══════════════════════════════════════════════

class FillParser:
    """填空题解析器"""

    # 填空标记模式
    BLANK_PATTERNS = [
        r'____+',           # ___ 或 _______
        r'\\underline\{[^}]+\}',  # \underline{...}
        r'\\blank',         # \blank
        r'\[\_\_\_\_+\]',     # [____]
        r'（\_\_\_\_）',      # （____）
    ]

    @classmethod
    def parse(cls, text: str, answers: List[str] = None) -> ParsedFill:
        """
        解析填空题文本

        Args:
            text: 原始文本
            answers: 已知的正确答案列表

        Returns:
            ParsedFill
        """
        blanks = []
        stem = text

        # 查找所有填空标记
        for pattern_str in cls.BLANK_PATTERNS:
            pattern = re.compile(pattern_str)
            for m in pattern.finditer(stem):
                blank_text = m.group(0)
                position = m.start()

                # 构建blank对象
                blank = {
                    "position": position,
                    "blank": blank_text,
                    "expected": answers[len(blanks)] if answers and len(blanks) < len(answers) else ""
                }
                blanks.append(blank)

        # 如果没有找到填空标记，尝试智能检测
        if not blanks:
            blanks = cls._detect_blanks_smart(stem)
            for i, b in enumerate(blanks):
                if answers and i < len(answers):
                    b["expected"] = answers[i]

        # 清理题干中的填空标记（保留位置信息）
        for blank in blanks:
            stem = stem.replace(blank["blank"], f"[填空{len(blanks)}]", 1)

        return ParsedFill(
            stem=stem,
            blanks=blanks,
            correct_answers=answers or []
        )

    @classmethod
    def _detect_blanks_smart(cls, text: str) -> List[Dict[str, Any]]:
        """智能检测填空位置"""
        blanks = []

        # 常见的填空表达模式
        patterns = [
            r'(?:求|计算|证明|推导)\s*[=:]\s*',  # 求 = 或 证明：
            r'[,，]\s*(?:其中|设)\s+',            # , 其中 或 , 设
            r'\(\s*\w+\s*=\s*\)',                # ( x = )
        ]

        for pattern_str in patterns:
            pattern = re.compile(pattern_str)
            for m in pattern.finditer(text):
                # 在匹配后插入填空标记
                blanks.append({
                    "position": m.end(),
                    "blank": "____",
                    "expected": ""
                })

        return blanks[:5]  # 最多5个


# ═══════════════════════════════════════════════
# 解答题解析器
# ═══════════════════════════════════════════════

class SolutionParser:
    """解答题解析器"""

    # 步骤分隔模式
    STEP_PATTERNS = [
        # 步骤一：步骤二：
        re.compile(r'^(####?\s*)?(步骤|第[一二三四五六七八九十\d]+)[：:：]?\s*', re.MULTILINE),
        # (1) (2)
        re.compile(r'^\s*\(\s*(\d+)\s*\)\s*', re.MULTILINE),
        # 1. 2.
        re.compile(r'^\s*(\d+)\.\s+', re.MULTILINE),
        # 【1】【2】
        re.compile(r'^\s*【(\d+)】\s*', re.MULTILINE),
        # 【X分】
        re.compile(r'^\s*【(\d+)分】\s*', re.MULTILINE),
    ]

    # 子问题分隔模式
    SUBQUESTION_PATTERNS = [
        re.compile(r'^\s*\((\d+)\)\s*', re.MULTILINE),      # (1)
        re.compile(r'^\s*第[一二三四五六七八九十]+问\s*', re.MULTILINE),  # 第一问
        re.compile(r'^\s*【问(\d+)】', re.MULTILINE),        # 【问1】
    ]

    # 子步骤分隔模式
    SUBSUBSTEP_PATTERNS = [
        re.compile(r'^(①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩)\s*'),
        re.compile(r'^(substep\d+)', re.IGNORECASE),
    ]

    @classmethod
    def parse(cls, text: str, steps_data: List[Dict] = None) -> ParsedSolution:
        """
        解析解答题文本

        Args:
            text: 原始文本
            steps_data: 已有的步骤数据 [{"label": "步骤1", "content": "..."}, ...]

        Returns:
            ParsedSolution
        """
        # 如果有预定义步骤，使用预定义步骤
        if steps_data and isinstance(steps_data, list):
            parsed_steps = cls._parse_steps_data(steps_data)
            stem = cls._extract_stem(text)
            return ParsedSolution(stem=stem, steps=parsed_steps)

        # 从文本中解析步骤
        stem, parsed_steps, sub_parts = cls._extract_steps(text)

        return ParsedSolution(
            stem=stem,
            steps=parsed_steps,
            sub_parts=sub_parts
        )

    @classmethod
    def _extract_stem(cls, text: str) -> str:
        """提取题干"""
        # 移除题号前缀
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', text)
        stem = re.sub(r'^\s*[（(]\s*\d+\s*[）)]\s*', '', stem)
        stem = re.sub(r'\(本题满分\d+分\)', '', stem)
        return stem.strip()

    @classmethod
    def _extract_steps(cls, text: str) -> Tuple[str, List[ParsedStep], Dict[str, 'ParsedSolution']]:
        """从文本中提取步骤"""
        stem = cls._extract_stem(text)

        # 检测是否为多问题目
        sub_parts = cls._detect_subquestions(text)

        if sub_parts:
            # 多问题目，分别解析每一问
            parsed_sub_parts = {}
            for q_num, q_text in sub_parts.items():
                # 递归解析子问题
                _, steps, _ = cls._extract_steps(q_text)
                parsed_sub_parts[q_num] = ParsedSolution(stem=q_text, steps=steps)

            # 第一问作为主题干
            first_q_text = sub_parts.get("1", text)
            _, main_steps, _ = cls._extract_steps(first_q_text)

            return stem, main_steps, parsed_sub_parts

        # 单问题目，解析步骤
        steps = cls._split_steps(text)

        return stem, steps, {}

    @classmethod
    def _detect_subquestions(cls, text: str) -> Dict[str, str]:
        """检测多问题目"""
        sub_parts = {}

        for pattern in cls.SUBQUESTION_PATTERNS:
            matches = list(pattern.finditer(text))
            if len(matches) >= 2:
                # 找到多问标记，按位置分割
                positions = [(m.start(), pattern.pattern, m.group(1) if m.lastindex else "") for m in matches]

                for i, (start, _, q_num) in enumerate(positions):
                    end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
                    sub_parts[q_num] = text[start:end].strip()

                return sub_parts

        return sub_parts

    @classmethod
    def _split_steps(cls, text: str) -> List[ParsedStep]:
        """分割步骤"""
        steps = []

        # 尝试使用步骤分隔模式
        for pattern in cls.STEP_PATTERNS:
            matches = list(pattern.finditer(text))
            if len(matches) >= 2:
                # 按分隔符分割
                positions = [(m.start(), m.group(0), m.group(1) if m.lastindex else m.group(2) if m.lastindex else "") for m in matches]

                for i, (start, marker, label) in enumerate(positions):
                    end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
                    content = text[start:end].strip()

                    # 清理标签
                    for p in cls.STEP_PATTERNS:
                        content = p.sub('', content)

                    # 确定步骤标签
                    if not label:
                        label = f"步骤{i + 1}"
                    else:
                        # 标准化标签格式
                        label = label.replace('#', '').strip()
                        if not label.startswith('步骤') and not label.startswith('第'):
                            label = f"步骤{label}"

                    # 检测子步骤
                    sub_steps = cls._split_sub_steps(content)

                    steps.append(ParsedStep(
                        label=label,
                        content=content,
                        sub_steps=sub_steps
                    ))

                return steps

        # 如果没有找到明确的步骤分隔，尝试按段落分割
        paragraphs = text.split('\n\n')
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if para:
                steps.append(ParsedStep(
                    label=f"步骤{i + 1}",
                    content=para
                ))

        return steps

    @classmethod
    def _split_sub_steps(cls, content: str) -> List[ParsedStep]:
        """分割子步骤"""
        sub_steps = []

        for pattern in cls.SUBSUBSTEP_PATTERNS:
            matches = list(pattern.finditer(content))
            if matches:
                positions = [(m.start(), m.group(0)) for m in matches]

                for i, (start, marker) in enumerate(positions):
                    end = positions[i + 1][0] if i + 1 < len(positions) else len(content)
                    sub_content = content[start:end].strip()

                    # 清理标记
                    for p in cls.SUBSUBSTEP_PATTERNS:
                        sub_content = p.sub('', sub_content)

                    sub_steps.append(ParsedStep(
                        label=marker,
                        content=sub_content
                    ))

                break

        return sub_steps

    @classmethod
    def _parse_steps_data(cls, steps_data: List[Dict]) -> List[ParsedStep]:
        """解析预定义步骤数据"""
        parsed_steps = []

        for i, step_data in enumerate(steps_data):
            if isinstance(step_data, dict):
                label = step_data.get("label", f"步骤{i + 1}")
                content = step_data.get("content", "")
                operation = step_data.get("operation", "")

                # 检测子步骤
                sub_steps_data = step_data.get("sub_steps", [])
                sub_steps = cls._parse_steps_data(sub_steps_data) if sub_steps_data else []

                parsed_steps.append(ParsedStep(
                    label=label,
                    content=content,
                    operation=operation,
                    sub_steps=sub_steps
                ))
            elif isinstance(step_data, str):
                parsed_steps.append(ParsedStep(
                    label=f"步骤{i + 1}",
                    content=str(step_data)
                ))

        return parsed_steps


# ═══════════════════════════════════════════════
# 证明题解析器
# ═══════════════════════════════════════════════

class ProofParser:
    """证明题解析器"""

    # 证明步骤模式
    PROOF_PATTERNS = [
        re.compile(r'^(证明|解题)[：:：]?\s*', re.MULTILINE),
        re.compile(r'^(即证|要证)[：:：]?\s*', re.MULTILINE),
        re.compile(r'^(得证|证毕|Q\.E\.D\.)', re.MULTILINE),
    ]

    @classmethod
    def parse(cls, text: str, proof_steps: List[Dict] = None) -> ParsedProof:
        """
        解析证明题文本

        Args:
            text: 原始文本
            proof_steps: 已有的证明步骤数据

        Returns:
            ParsedProof
        """
        # 如果有预定义步骤，使用预定义步骤
        if proof_steps and isinstance(proof_steps, list):
            parsed_steps = SolutionParser._parse_steps_data(proof_steps)
            stem = SolutionParser._extract_stem(text)
            return ParsedProof(stem=stem, proof_steps=parsed_steps)

        # 从文本中解析
        stem, proof_steps_list = cls._extract_proof_steps(text)

        return ParsedProof(
            stem=stem,
            proof_steps=proof_steps_list
        )

    @classmethod
    def _extract_proof_steps(cls, text: str) -> Tuple[str, List[ParsedStep]]:
        """提取证明步骤"""
        stem = SolutionParser._extract_stem(text)

        # 查找"证明"标记的位置
        proof_start = len(text)
        for pattern in cls.PROOF_PATTERNS:
            m = pattern.search(text)
            if m:
                proof_start = min(proof_start, m.start())

        if proof_start < len(text):
            stem = text[:proof_start].strip()
            proof_text = text[proof_start:]
        else:
            proof_text = text

        # 分割证明步骤
        steps = SolutionParser._split_steps(proof_text)

        return stem, steps


# ═══════════════════════════════════════════════
# 统一解析器
# ═══════════════════════════════════════════════

class UnifiedParser:
    """统一解析器 - 自动识别题型并分发到对应解析器"""

    # 题型识别模式
    TYPE_PATTERNS = {
        QuestionType.CHOICE: [
            r'选择',
            r'\([A-D]\)',
            r'\$\([A-D]\)\$',
            r'[（(][A-D][）)]',
            r'[A-D][.．、]',
        ],
        QuestionType.FILL: [
            r'填空',
            r'____+',
            r'\\underline',
            r'\[\_\_\_\_+\]',
        ],
        QuestionType.PROOF: [
            r'证明',
            r'求证',
            r'验证',
        ],
    }

    @classmethod
    def parse(cls, text: str, question_type: str = None,
              options: Dict = None, steps_data: List = None,
              answers: List = None) -> ParsingResult:
        """
        统一解析入口

        Args:
            text: 原始文本
            question_type: 已知的题型（可选）
            options: 选择题选项
            steps_data: 解答步骤数据
            answers: 正确答案

        Returns:
            ParsingResult
        """
        warnings = []
        confidence = 1.0

        # 如果已知题型，直接使用
        if question_type:
            qtype = cls._normalize_type(question_type)
        else:
            # 自动识别题型
            qtype, confidence = cls._detect_type(text)

        # 根据题型分发到对应解析器
        if qtype == QuestionType.CHOICE:
            parsed = ChoiceParser.parse(text, options)
            if answers:
                parsed.correct_answer = answers[0] if answers else ""

        elif qtype == QuestionType.FILL:
            parsed = FillParser.parse(text, answers)

        elif qtype == QuestionType.SOLUTION:
            parsed = SolutionParser.parse(text, steps_data)

        elif qtype == QuestionType.PROOF:
            parsed = ProofParser.parse(text, steps_data)

        else:
            # 尝试所有解析器，返回最可信的结果
            qtype, parsed, confidence = cls._try_all_parsers(text)

        return ParsingResult(
            question_type=qtype,
            raw_text=text,
            parsed=parsed,
            warnings=warnings,
            confidence=confidence
        )

    @classmethod
    def _normalize_type(cls, question_type: str) -> QuestionType:
        """标准化题型名称"""
        type_map = {
            "选择题": QuestionType.CHOICE,
            "选择": QuestionType.CHOICE,
            "choice": QuestionType.CHOICE,
            "填空题": QuestionType.FILL,
            "填空": QuestionType.FILL,
            "fill": QuestionType.FILL,
            "解答题": QuestionType.SOLUTION,
            "解答": QuestionType.SOLUTION,
            "solution": QuestionType.SOLUTION,
            "证明题": QuestionType.PROOF,
            "证明": QuestionType.PROOF,
            "proof": QuestionType.PROOF,
        }
        return type_map.get(question_type, QuestionType.UNKNOWN)

    @classmethod
    def _detect_type(cls, text: str) -> Tuple[QuestionType, float]:
        """检测题型"""
        scores = {qtype: 0 for qtype in QuestionType}

        for qtype, patterns in cls.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    scores[qtype] += 1

        # 找到最高分的题型
        if scores[QuestionType.CHOICE] >= 2:
            return QuestionType.CHOICE, 0.9
        elif scores[QuestionType.FILL] >= 1:
            return QuestionType.FILL, 0.8
        elif scores[QuestionType.PROOF] >= 1:
            return QuestionType.PROOF, 0.8
        elif scores[QuestionType.CHOICE] >= 1:
            return QuestionType.CHOICE, 0.7

        # 默认返回解答题
        return QuestionType.SOLUTION, 0.5

    @classmethod
    def _try_all_parsers(cls, text: str) -> Tuple[QuestionType, Any, float]:
        """尝试所有解析器，返回最可信的结果"""
        # 依次尝试
        parsers = [
            (QuestionType.CHOICE, ChoiceParser.parse),
            (QuestionType.FILL, FillParser.parse),
            (QuestionType.SOLUTION, SolutionParser.parse),
            (QuestionType.PROOF, ProofParser.parse),
        ]

        for qtype, parser_func in parsers:
            try:
                if qtype == QuestionType.CHOICE:
                    result = parser_func(text, {})
                    if len(result.options) >= 2:
                        return qtype, result, 0.6
                elif qtype == QuestionType.FILL:
                    result = parser_func(text, None)
                    if result.blanks:
                        return qtype, result, 0.6
                elif qtype == QuestionType.SOLUTION:
                    result = parser_func(text, None)
                    if result.steps:
                        return qtype, result, 0.6
            except Exception:
                continue

        # 默认返回解析结果
        return QuestionType.UNKNOWN, ParsedSolution(stem=text, steps=[]), 0.3


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def parse_question(text: str, question_type: str = None,
                  **kwargs) -> ParsingResult:
    """
    解析题目的便捷函数

    Args:
        text: 原始文本
        question_type: 题型（可选）
        **kwargs: 其他参数（options, steps_data, answers 等）

    Returns:
        ParsingResult
    """
    return UnifiedParser.parse(text, question_type, **kwargs)


# ═══════════════════════════════════════════════
# 示例用法
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    # 示例1: 解析选择题
    choice_text = """
    1. 设函数 f(x) = x^2，求 f'(2)。

    $(A)$ 2  $(B)$ 4  $(C)$ 6  $(D)$ 8

    答案：B
    """
    result = parse_question(choice_text, "选择题")
    print("=== 选择题解析 ===")
    print(f"题型: {result.question_type.value}")
    print(f"题干: {result.parsed.stem}")
    print(f"选项数: {len(result.parsed.options)}")
    for opt in result.parsed.options:
        print(f"  {opt['label']}: {opt['content'][:30]}...")

    # 示例2: 解析解答题
    solution_text = """
    1. 求极限 $\\lim_{x \\to 0} \\frac{\\sin x}{x}$。

    #### 步骤一：识别极限类型
    当 $x \\to 0$ 时，$\\sin x \\to 0$，分子分母都趋于 0，
    这是 $\\frac{0}{0}$ 型极限。

    #### 步骤二：应用重要极限
    根据重要极限 $\\lim_{u \\to 0} \\frac{\\sin u}{u} = 1$，
    可得 $\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1$。

    #### 步骤三：得出结论
    因此，原极限等于 1。
    """
    result = parse_question(solution_text, "解答题")
    print("\n=== 解答题解析 ===")
    print(f"题型: {result.question_type.value}")
    print(f"题干: {result.parsed.stem[:50]}...")
    print(f"步骤数: {len(result.parsed.steps)}")
    for step in result.parsed.steps:
        print(f"  {step.label}: {step.content[:40]}...")
