"""
LaTeX 整卷试卷解析 — 将完整 .tex 源码转为可分割的文本，再走 ExamParserPipeline。

支持常见考研卷面结构:
  - \\documentclass + \\begin{document}
  - \\section{一、选择题} / \\textbf{一、选择题}
  - \\begin{enumerate} + \\item
  - 行内/独立公式: $...$, \\(...\\), \\[...\\], equation 环境
  - 【答案】/【解析】标记（纯文本或 LaTeX 内）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .pipeline import ExamParserPipeline, PipelineResult


# 章节标题 → 题型提示（供分割器参考）
_SECTION_TYPE_HINTS = (
    ("选择", "选择题"),
    ("填空", "填空题"),
    ("解答", "解答题"),
    ("证明", "证明题"),
    ("计算", "解答题"),
    ("综合", "解答题"),
)


@dataclass
class LatexNormalizeReport:
    original_chars: int
    normalized_chars: int
    item_count: int
    section_count: int
    warnings: list[str] = field(default_factory=list)


class LatexExamParser:
    """完整 LaTeX 试卷 → 题库题目列表。"""

    _YEAR_RE = re.compile(r"(19[89]\d|20[0-2]\d)\s*年")
    _MATH_TYPE_RE = re.compile(
        r"数学\s*[\(（]?\s*一\s*[\)）]?|数学一|数一|"
        r"数学\s*[\(（]?\s*二\s*[\)）]?|数学二|数二|"
        r"数学\s*[\(（]?\s*三\s*[\)）]?|数学三|数三"
    )

    def normalize_latex_source(self, latex: str) -> tuple[str, LatexNormalizeReport]:
        """将 LaTeX 源码规范化为 Markdown 风格纯文本，供现有分割管道使用。"""
        warnings: list[str] = []
        text = latex.replace("\r\n", "\n").replace("\r", "\n")
        original_len = len(text)

        text = self._extract_document_body(text, warnings)
        text = self._strip_comments(text)
        text = self._strip_preamble_artifacts(text)
        text = self._convert_math_delimiters(text)
        text = self._convert_sections(text)
        text = self._unwrap_common_environments(text)
        text = self._convert_items(text)
        text = self._convert_option_lines(text)
        text = self._cleanup_whitespace(text)

        section_count = len(re.findall(r"^##\s+", text, re.MULTILINE))
        item_count = len(re.findall(r"【\d+】", text))

        if item_count == 0:
            warnings.append(
                "未识别到 \\item 或题号；请确认试卷使用 enumerate/\\item 或「1.」题号格式。"
            )
        if section_count == 0:
            warnings.append(
                "未识别到章节标题；建议在卷面中使用 \\section{一、选择题} 或 \\textbf{一、选择题}。"
            )

        return text, LatexNormalizeReport(
            original_chars=original_len,
            normalized_chars=len(text),
            item_count=item_count,
            section_count=section_count,
            warnings=warnings,
        )

    def parse(
        self,
        latex: str,
        year: int | None = None,
        math_type: str = "数学一",
        pipeline: ExamParserPipeline | None = None,
    ) -> PipelineResult:
        """解析整卷 LaTeX 并返回与 ExamParserPipeline 相同结构的结果。"""
        normalized, report = self.normalize_latex_source(latex)
        inferred_year = year or self._infer_year(latex)
        inferred_type = math_type if math_type != "数学一" else self._infer_math_type(latex)

        pipe = pipeline or ExamParserPipeline()
        result = pipe.process_text(
            normalized,
            year=inferred_year,
            math_type=inferred_type,
            filename="exam.tex",
        )
        result.warnings = list(result.warnings) + report.warnings
        if report.item_count and result.total_questions == 0:
            result.warnings.append(
                f"LaTeX 中识别到约 {report.item_count} 个 \\item，但分割器未拆出题目；"
                "请检查题号/章节格式是否与考研卷面一致。"
            )
        return result

    def parse_file(
        self,
        file_path: str,
        year: int | None = None,
        math_type: str = "数学一",
        pipeline: ExamParserPipeline | None = None,
    ) -> PipelineResult:
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            return PipelineResult(
                year=year or 0,
                math_type=math_type,
                format="unknown",
                total_questions=0,
                questions=[],
                errors=[f"文件不存在: {file_path}"],
            )
        return self.parse(
            path.read_text(encoding="utf-8"),
            year=year,
            math_type=math_type,
            pipeline=pipeline,
        )

  # ── 内部：LaTeX → 类 Markdown 文本 ─────────────────────────────

    def _extract_document_body(self, text: str, warnings: list[str]) -> str:
        m = re.search(r"\\begin\s*\{\s*document\s*\}", text, re.IGNORECASE)
        if m:
            text = text[m.end():]
        else:
            warnings.append("未找到 \\begin{document}，已按全文解析（忽略导言区命令）。")
            # 去掉常见导言行
            lines = []
            for line in text.split("\n"):
                s = line.strip()
                if s.startswith((r"\documentclass", r"\usepackage", r"\newcommand",
                                 r"\renewcommand", r"\setlength", r"\geometry")):
                    continue
                lines.append(line)
            text = "\n".join(lines)

        m_end = re.search(r"\\end\s*\{\s*document\s*\}", text, re.IGNORECASE)
        if m_end:
            text = text[: m_end.start()]
        return text

    def _strip_comments(self, text: str) -> str:
        out = []
        for line in text.split("\n"):
            cleaned = []
            i = 0
            while i < len(line):
                if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                    break
                cleaned.append(line[i])
                i += 1
            out.append("".join(cleaned).rstrip())
        return "\n".join(out)

    def _strip_preamble_artifacts(self, text: str) -> str:
        drop_cmds = (
            r"\\maketitle\b",
            r"\\tableofcontents\b",
            r"\\newpage\b",
            r"\\clearpage\b",
            r"\\thispagestyle\{[^}]*\}",
            r"\\pagestyle\{[^}]*\}",
            r"\\setcounter\{[^}]*\}\{[^}]*\}",
        )
        for pat in drop_cmds:
            text = re.sub(pat, "", text)
        text = re.sub(r"\\title\{[^}]*\}", "", text)
        text = re.sub(r"\\author\{[^}]*\}", "", text)
        text = re.sub(r"\\date\{[^}]*\}", "", text)
        return text

    def _convert_math_delimiters(self, text: str) -> str:
        # \[ ... \] → $$ ... $$
        text = re.sub(
            r"\\\[\s*(.*?)\s*\\\]",
            lambda m: f"\n$$\n{m.group(1).strip()}\n$$\n",
            text,
            flags=re.DOTALL,
        )
        # \( ... \) → $ ... $
        text = re.sub(
            r"\\\(\s*(.*?)\s*\\\)",
            lambda m: f"${m.group(1).strip()}$",
            text,
            flags=re.DOTALL,
        )
        # equation / equation* 环境
        for env in ("equation", "equation*", "align", "align*", "gather", "gather*"):
            text = re.sub(
                rf"\\begin\{{{re.escape(env)}\}}\s*(.*?)\s*\\end\{{{re.escape(env)}\}}",
                lambda m, _e=env: f"\n$$\n{m.group(1).strip()}\n$$\n",
                text,
                flags=re.DOTALL,
            )
        return text

    def _convert_sections(self, text: str) -> str:
        def _to_header(title: str) -> str:
            title = title.strip()
            for key, _ in _SECTION_TYPE_HINTS:
                if key in title:
                    break
            return f"\n## {title}\n"

        text = re.sub(
            r"\\section\*?\s*\{([^}]+)\}",
            lambda m: _to_header(m.group(1)),
            text,
        )
        text = re.sub(
            r"\\subsection\*?\s*\{([^}]+)\}",
            lambda m: f"\n### {m.group(1).strip()}\n",
            text,
        )
        # \textbf{一、选择题} 独立成行
        text = re.sub(
            r"(?:^|\n)\s*\\textbf\s*\{\s*([一二三四五六七八九十]+、[^}]+)\s*\}\s*(?:\n|$)",
            lambda m: _to_header(m.group(1)),
            text,
        )
        # 纯文本「一、选择题」
        text = re.sub(
            r"(?:^|\n)\s*([一二三四五六七八九十]+、(?:填空题|选择题|解答题|证明题|计算题|综合题)[^\n]*)",
            lambda m: _to_header(m.group(1)),
            text,
        )
        return text

    def _unwrap_common_environments(self, text: str) -> str:
        envs = (
            "enumerate", "itemize", "description", "questions", "exam",
            "center", "flushleft", "flushright", "minipage", "quote",
        )
        for env in envs:
            text = re.sub(rf"\\begin\{{{env}\}}(?:\[[^\]]*\])?", "", text)
            text = re.sub(rf"\\end\{{{env}\}}", "", text)
        return text

    def _convert_items(self, text: str) -> str:
        """\\item → 【n】题号标记（每遇到 ## 章节重置编号）。"""
        lines = text.split("\n")
        out: list[str] = []
        qnum = 0

        item_re = re.compile(r"\\item(?:\[[^\]]*\])?\s*")

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("##"):
                qnum = 0
                out.append(line)
                continue

            if "\\item" in line:
                def _repl(_m):
                    nonlocal qnum
                    qnum += 1
                    return f"\n【{qnum}】 "

                line = item_re.sub(_repl, line, count=1)
                # 一行内多个 \item 的罕见情况
                while "\\item" in line:
                    line = item_re.sub(_repl, line, count=1)

            out.append(line)

        return "\n".join(out)

    def _convert_option_lines(self, text: str) -> str:
        """(A) / \\textbf{(A)} 等选项行保持可读。"""
        text = re.sub(
            r"\\textbf\s*\{\s*\(([A-D])\)\s*\}",
            r"(\1)",
            text,
        )
        text = re.sub(
            r"(?:^|\n)\s*\\item\s*\[\s*([A-D])\s*\]\s*",
            r"\n(\1) ",
            text,
        )
        return text

    def _cleanup_whitespace(self, text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去掉孤立 LaTeX 换行 \\
        text = re.sub(r"\\\\\s*\n", "\n", text)
        return text.strip()

    def _infer_year(self, text: str) -> int:
        head = text[:800]
        m = self._YEAR_RE.search(head)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d{4})", head)
        if m and 1987 <= int(m.group(1)) <= 2026:
            return int(m.group(1))
        return 2024

    def _infer_math_type(self, text: str) -> str:
        head = text[:800]
        if re.search(r"数学\s*[\(（]?\s*二|数学二|数二", head):
            return "数学二"
        if re.search(r"数学\s*[\(（]?\s*三|数学三|数三", head):
            return "数学三"
        if re.search(r"数学\s*[\(（]?\s*一|数学一|数一", head):
            return "数学一"
        return "数学一"
