from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class ContentType(Enum):
    TEXT = auto()
    INLINE_MATH = auto()
    BLOCK_MATH = auto()
    PROOF_TRANSITION = auto()
    QUESTION_STEM = auto()
    ANSWER = auto()
    THEOREM = auto()
    DEFINITION = auto()
    OPTION = auto()
    DERIVATION_STEP = auto()
    EQUALITY_CHAIN = auto()
    MATRIX = auto()
    ALIGNED = auto()
    CASES = auto()
    TIKZ = auto()
    TABLE = auto()
    LIST = auto()
    DIVIDER = auto()
    CODE = auto()
    WARNING = auto()
    ERROR = auto()
    OBLIGATION = auto()
    FINAL_ANSWER = auto()


@dataclass
class ContentSegment:
    type: ContentType
    content: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    @property
    def is_math(self) -> bool:
        return self.type in {
            ContentType.INLINE_MATH,
            ContentType.BLOCK_MATH,
            ContentType.MATRIX,
            ContentType.ALIGNED,
            ContentType.CASES,
            ContentType.EQUALITY_CHAIN,
        }

    @property
    def is_block_math(self) -> bool:
        return self.type in {
            ContentType.BLOCK_MATH,
            ContentType.MATRIX,
            ContentType.ALIGNED,
            ContentType.CASES,
        }


class ContentClassifier:
    """
    将混合内容（中文+LaTeX+英文）分类为语义片段。

    输入:
      "由 Sylvester 不等式：$$r(AB)\\ge r(A)+r(B)-n$$，将(2)代入(1)"
    输出:
      [
        ContentSegment(TEXT, "由 Sylvester 不等式："),
        ContentSegment(BLOCK_MATH, "r(AB)\\ge r(A)+r(B)-n"),
        ContentSegment(TEXT, "，将"),
        ContentSegment(INLINE_MATH, "(2)"),
        ContentSegment(TEXT, "代入"),
        ContentSegment(INLINE_MATH, "(1)"),
      ]
    """

    BLOCK_MATH_DELIMITERS = {"$$": "$$", "\\[": "\\]", "\\begin{": "\\end"}
    INLINE_MATH_DELIMITERS = {"$": "$", "\\(": "\\)"}
    BLOCK_ENVIRONMENTS = {
        "aligned", "align", "gather", "multline", "eqnarray",
        "matrix", "pmatrix", "bmatrix", "vmatrix", "cases",
        "array", "tabular"
    }

    def classify(self, text: str) -> list[ContentSegment]:
        """
        主入口：将混合文本分类为语义片段列表。
        """
        if not text:
            return []

        segments = []
        pos = 0
        i = 0
        n = len(text)

        while i < n:
            char = text[i]

            if char == "$":
                seg, new_pos = self._classify_dollar_math(text, i)
                segments.append(seg)
                i = new_pos
                continue

            if char == "\\":
                seg, new_pos = self._classify_latex_command(text, i)
                if seg:
                    segments.append(seg)
                    i = new_pos
                    continue

            seg, new_pos = self._classify_text_run(text, i)
            if seg.content:
                segments.append(seg)
            i = new_pos

        return self._post_process(segments)

    def _classify_dollar_math(self, text: str, start: int) -> tuple[ContentSegment, int]:
        if text.startswith("$$", start):
            return self._classify_block_math(text, start, "$$", "$$")
        else:
            return self._classify_inline_math(text, start, "$", "$")

    def _classify_block_math(self, text: str, start: int, open_delim: str, close_delim: str) -> tuple[ContentSegment, int]:
        seg_start = start
        content_start = start + len(open_delim)
        content_end = text.find(close_delim, content_start)

        if content_end == -1:
            return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)

        content = text[content_start:content_end].strip()
        math_type = self._detect_block_math_type(content)

        end = content_end + len(close_delim)
        return ContentSegment(math_type, content, seg_start, end), end

    def _classify_inline_math(self, text: str, start: int, open_delim: str, close_delim: str) -> tuple[ContentSegment, int]:
        seg_start = start
        content_start = start + len(open_delim)
        content_end = text.find(close_delim, content_start)

        if content_end == -1:
            return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)

        content = text[content_start:content_end].strip()
        end = content_end + len(close_delim)
        return ContentSegment(ContentType.INLINE_MATH, content, seg_start, end), end

    def _classify_latex_command(self, text: str, start: int) -> tuple[ContentSegment, int]:
        if text.startswith("\\[", start):
            content_end = text.find("\\]", start + 2)
            if content_end == -1:
                return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)
            content = text[start + 2:content_end].strip()
            end = content_end + 2
            math_type = self._detect_block_math_type(content)
            return ContentSegment(math_type, content, start, end), end

        if text.startswith("\\(", start):
            content_end = text.find("\\)", start + 2)
            if content_end == -1:
                return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)
            content = text[start + 2:content_end].strip()
            end = content_end + 2
            return ContentSegment(ContentType.INLINE_MATH, content, start, end), end

        if text.startswith("\\begin{"):
            return self._classify_block_environment(text, start)

        if text.startswith("\\text{") or text.startswith("\\mathrm{"):
            return self._classify_text_command(text, start)

        return ContentSegment(ContentType.TEXT, text[start], start, start + 1), start + 1

    def _classify_block_environment(self, text: str, start: int) -> tuple[ContentSegment, int]:
        end_brace = text.find("}", start + 7)
        if end_brace == -1:
            return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)

        env_name = text[start + 7:end_brace].strip()
        full_env = f"\\begin{{{env_name}}}"
        full_end = f"\\end{{{env_name}}}"

        env_start = start
        content_start = start + len(full_env)
        env_end_pos = text.find(full_end, content_start)

        if env_end_pos == -1:
            return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)

        content = text[content_start:env_end_pos].strip()
        end = env_end_pos + len(full_end)

        math_type = self._detect_block_math_type_from_env(env_name, content)
        return ContentSegment(math_type, content, env_start, end), end

    def _classify_text_command(self, text: str, start: int) -> tuple[ContentSegment, int]:
        brace_level = 0
        i = start
        n = len(text)
        content_parts = []
        cmd_start = -1

        while i < n:
            c = text[i]
            if c == "{" and brace_level == 0 and text[i:i + 6] in ("\\text{", "\\mathr"):
                cmd_start = i
                brace_level = 1
                i += 1
                continue
            if brace_level > 0:
                if c == "{":
                    brace_level += 1
                elif c == "}":
                    brace_level -= 1
                    if brace_level == 0:
                        content = text[cmd_start + 6:i].strip()
                        return ContentSegment(ContentType.TEXT, content, cmd_start, i + 1), i + 1
            i += 1

        return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)

    def _classify_text_run(self, text: str, start: int) -> tuple[ContentSegment, int]:
        j = start
        n = len(text)
        while j < n:
            c = text[j]
            if c in "$\\":
                break
            j += 1

        content = text[start:j].strip()
        if not content:
            return ContentSegment(ContentType.TEXT, "", start, start), start

        content_type = self._detect_text_type(content)
        return ContentSegment(content_type, content, start, j), j

    def _classify_inline_math(self, text: str, start: int, open_delim: str, close_delim: str) -> tuple[ContentSegment, int]:
        seg_start = start
        content_start = start + len(open_delim)
        content_end = text.find(close_delim, content_start)

        if content_end == -1:
            return ContentSegment(ContentType.TEXT, text[start:], start, len(text)), len(text)

        content = text[content_start:content_end].strip()
        end = content_end + len(close_delim)
        return ContentSegment(ContentType.INLINE_MATH, content, seg_start, end), end

    def _detect_block_math_type(self, content: str) -> ContentType:
        if any(env in content for env in ["\\begin{aligned}", "\\begin{align}", "\\begin{array}"]):
            return ContentType.ALIGNED
        if "\\begin{cases}" in content or "\\begin.switch}" in content:
            return ContentType.CASES
        if "\\begin{matrix}" in content or "\\begin{pmatrix}" in content:
            return ContentType.MATRIX
        if "\\\\" in content or "\\-" in content:
            return ContentType.EQUALITY_CHAIN
        return ContentType.BLOCK_MATH

    def _detect_block_math_type_from_env(self, env_name: str, content: str) -> ContentType:
        if env_name in ("aligned", "align", "eqnarray", "gather", "multline"):
            return ContentType.ALIGNED
        if env_name in ("cases",):
            return ContentType.CASES
        if env_name in ("matrix", "pmatrix", "bmatrix", "vmatrix", "Bmatrix", "smallmatrix"):
            return ContentType.MATRIX
        if env_name in ("array",):
            return ContentType.MATRIX
        return ContentType.BLOCK_MATH

    def _detect_text_type(self, content: str) -> ContentType:
        content = content.strip()

        if not content:
            return ContentType.TEXT

        if content in ("---", "***", "___"):
            return ContentType.DIVIDER

        if content.startswith("**答案**") or content.startswith("📌") or "最终答案" in content:
            return ContentType.FINAL_ANSWER

        if "证明" in content and ("假设" in content or "目标" in content or "由" in content):
            return ContentType.PROOF_TRANSITION

        if content.startswith("定义") or content.startswith("Definition"):
            return ContentType.DEFINITION

        if content.startswith("定理") or content.startswith("Theorem") or content.startswith("Lemma") or content.startswith("推论"):
            return ContentType.THEOREM

        if content.startswith("选项") or (len(content) == 1 and content in "ABCD"):
            return ContentType.OPTION

        if "待证" in content or "proof obligation" in content.lower():
            return ContentType.OBLIGATION

        if "\\begin{" in content or "\\[" in content or content.startswith("$$"):
            return ContentType.BLOCK_MATH

        return ContentType.TEXT

    def _post_process(self, segments: list[ContentSegment]) -> list[ContentSegment]:
        merged = []
        for seg in segments:
            if not seg.content.strip():
                continue
            if merged and merged[-1].type == seg.type == ContentType.TEXT:
                merged[-1] = ContentSegment(
                    type=ContentType.TEXT,
                    content=merged[-1].content + seg.content,
                    start=merged[-1].start,
                    end=seg.end,
                    confidence=min(merged[-1].confidence, seg.confidence)
                )
            else:
                merged.append(seg)
        return merged
