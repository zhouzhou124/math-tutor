"""
LaTeX修复引擎 — 自动修复考研数学真题中的LaTeX损坏

修复策略（按顺序）:
  1. 双反斜杠: \\prime → \prime, \\begin → \begin
  2. OCR符号映射: ∫→f → \int, ∞→oo → \infty, ∑→E → \sum
  3. 花括号平衡: 用栈机统计{}，插入缺失的}
  4. 缺失定界符: 检测LaTeX命令缺少$包裹
"""

import re
from dataclasses import dataclass, field


@dataclass
class LaTeXReport:
    original: str
    fixed: str
    fixes_applied: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    fix_count: int = 0


class LaTeXFixer:
    """修复考研数学真题中常见的LaTeX损坏模式"""

    # 双反斜杠模式 — 在LaTeX命令前的多余反斜杠
    _DOUBLE_BS_PATTERNS = [
        (re.compile(r'\\\\(prime)'), r'\\\1'),
        (re.compile(r'\\\\(begin\{)'), r'\\\1'),
        (re.compile(r'\\\\(end\{)'), r'\\\1'),
        (re.compile(r'\\\\(frac\{)'), r'\\\1'),
        (re.compile(r'\\\\(sqrt\{)'), r'\\\1'),
        (re.compile(r'\\\\(int\b)'), r'\\\1'),
        (re.compile(r'\\\\(sum\b)'), r'\\\1'),
        (re.compile(r'\\\\(lim\b)'), r'\\\1'),
        (re.compile(r'\\\\(to\b)'), r'\\\1'),
        (re.compile(r'\\\\(infty\b)'), r'\\\1'),
        (re.compile(r'\\\\(partial\b)'), r'\\\1'),
        (re.compile(r'\\\\(mathbf\b)'), r'\\\1'),
        (re.compile(r'\\\\(mathrm\b)'), r'\\\1'),
        (re.compile(r'\\\\(text\b)'), r'\\\1'),
        (re.compile(r'\\\\(left\b)'), r'\\\1'),
        (re.compile(r'\\\\(right\b)'), r'\\\1'),
        (re.compile(r'\\\\(cdot\b)'), r'\\\1'),
        (re.compile(r'\\\\(times\b)'), r'\\\1'),
        (re.compile(r'\\\\(cdots\b)'), r'\\\1'),
        (re.compile(r'\\\\(alpha\b)'), r'\\\1'),
        (re.compile(r'\\\\(beta\b)'), r'\\\1'),
        (re.compile(r'\\\\(gamma\b)'), r'\\\1'),
        (re.compile(r'\\\\(delta\b)'), r'\\\1'),
        (re.compile(r'\\\\(lambda\b)'), r'\\\1'),
        (re.compile(r'\\\\(theta\b)'), r'\\\1'),
        (re.compile(r'\\\\(pi\b)'), r'\\\1'),
        (re.compile(r'\\\\(sigma\b)'), r'\\\1'),
        (re.compile(r'\\\\(omega\b)'), r'\\\1'),
        (re.compile(r'\\\\(varepsilon\b)'), r'\\\1'),
        (re.compile(r'\\\\(varphi\b)'), r'\\\1'),
        (re.compile(r'\\\\(Rightarrow\b)'), r'\\\1'),
        (re.compile(r'\\\\(rightarrow\b)'), r'\\\1'),
        (re.compile(r'\\\\(mathrm\{d\})'), r'\\\1'),
        (re.compile(r'\\\\(operatorname)'), r'\\\1'),
        (re.compile(r'\\\\(boxed)'), r'\\\1'),
        (re.compile(r'\\\\(displaystyle)'), r'\\\1'),
        (re.compile(r'\\\\(mathrm)'), r'\\\1'),
        (re.compile(r'\\\\(vec\b)'), r'\\\1'),
        (re.compile(r'\\\\(bar\b)'), r'\\\1'),
        (re.compile(r'\\\\(hat\b)'), r'\\\1'),
        (re.compile(r'\\\\(tilde\b)'), r'\\\1'),
        (re.compile(r'\\\\(dot\b)'), r'\\\1'),
    ]

    # OCR常见错误: 数学符号被识别为相似字母
    _OCR_SYMBOLS_IN_MATH = [
        # ∫ → f (当f出现在积分的上下限位置时)
        # ∞ → oo
        (re.compile(r'(?<!\\)oo(?=\s*[\.\)\]\}_,;:\n]|\s*$)'), r'\\infty'),
    ]

    def fix(self, text: str) -> LaTeXReport:
        """主入口: 应用所有修复策略"""
        if not text:
            return LaTeXReport(original="", fixed="")

        report = LaTeXReport(original=text, fixed=text)
        current = text

        current, n = self._fix_double_backslashes(current)
        if n > 0:
            report.fixes_applied.append(f"修复{n}处双反斜杠")
            report.fix_count += n

        current, n = self._fix_ocr_infty(current)
        if n > 0:
            report.fixes_applied.append(f"修复{n}处OCR ∞→oo")
            report.fix_count += n

        current, issues = self._fix_unmatched_braces(current)
        if issues:
            report.fixes_applied.append(f"修复花括号平衡 ({len(issues)}处)")
            report.fix_count += len(issues)

        current, n = self._fix_unmatched_dollars(current)
        if n > 0:
            report.fixes_applied.append(f"修复{n}处$配对")
            report.fix_count += n

        # 最终验证
        if not self._validate_dollar_balance(current):
            report.unresolved.append("$ 配对仍有问题")

        brace_ok, brace_issues = self._validate_brace_balance(current)
        if not brace_ok:
            report.unresolved.append(f"花括号仍有问题: {brace_issues}")

        report.fixed = current
        return report

    def _fix_double_backslashes(self, text: str) -> tuple[str, int]:
        """修复 \\prime → \prime 等双反斜杠"""
        total = 0
        for pattern, replacement in self._DOUBLE_BS_PATTERNS:
            new_text, count = pattern.subn(replacement, text)
            if count > 0:
                total += count
                text = new_text
        return text, total

    def _fix_ocr_infty(self, text: str) -> tuple[str, int]:
        """修复OCR中 ∞ 被识别为 oo"""
        total = 0
        for pattern, replacement in self._OCR_SYMBOLS_IN_MATH:
            new_text, count = pattern.subn(replacement, text)
            total += count
            text = new_text
        return text, total

    def _fix_unmatched_braces(self, text: str) -> tuple[str, list[str]]:
        """用栈机修复不配对的花括号"""
        issues = []
        # 只在疑似数学模式中处理
        segments = self._find_math_segments(text)
        if not segments:
            return text, []

        result = list(text)
        # 从后向前处理，避免偏移问题
        for start, end in reversed(segments):
            seg = text[start:end]
            fixed_seg, seg_issues = self._balance_braces_in_segment(seg)
            if seg_issues:
                for issue in seg_issues:
                    issues.append(f"[{start}-{end}] {issue}")
                result[start:end] = fixed_seg

        return "".join(result), issues

    def _find_math_segments(self, text: str) -> list[tuple[int, int]]:
        """找到所有数学模式段落 ($...$ 和 $$...$$)"""
        segments = []
        # $...$ (单美元)
        for m in re.finditer(r'\$(.+?)\$', text, re.DOTALL):
            segments.append((m.start(1), m.end(1)))
        # $$...$$
        for m in re.finditer(r'\$\$(.+?)\$\$', text, re.DOTALL):
            segments.append((m.start(1), m.end(1)))
        # \[...\]
        for m in re.finditer(r'\\\[(.+?)\\\]', text, re.DOTALL):
            segments.append((m.start(1), m.end(1)))
        return segments

    def _balance_braces_in_segment(self, text: str) -> tuple[str, list[str]]:
        """平衡单个数学段落内的花括号"""
        issues = []
        stack = []  # positions of opening {
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '{':
                stack.append(i)
            elif ch == '}':
                if stack:
                    stack.pop()
                else:
                    # 多余的} — 移除它
                    text = text[:i] + text[i + 1:]
                    i -= 1
                    issues.append("移除多余的 }")
            i += 1

        # 未闭合的{ — 在末尾追加}
        if stack:
            text = text + '}' * len(stack)
            issues.append(f"追加{len(stack)}个缺失的 }}")
        return text, issues

    def _fix_unmatched_dollars(self, text: str) -> tuple[str, int]:
        """修复不配对的$符号"""
        # 统计 $$$...$$$ 模式中的$是否成对
        # 排除 $$ 双美元符号
        fixes = 0
        # 保护 $$ 双美元
        double_dollar_positions = []
        for m in re.finditer(r'\$\$', text):
            double_dollar_positions.extend([m.start(), m.end() - 1])

        # 统计单美元符号
        single_dollar_positions = []
        for i, ch in enumerate(text):
            if ch == '$' and i not in double_dollar_positions:
                single_dollar_positions.append(i)

        if len(single_dollar_positions) % 2 != 0:
            # 奇数个$ — 在文本末尾补一个
            text = text + '$'
            fixes += 1

        return text, fixes

    def _validate_brace_balance(self, text: str) -> tuple[bool, list[str]]:
        """验证所有花括号是否配对"""
        issues = []
        depth = 0
        for i, ch in enumerate(text):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth < 0:
                    issues.append(f"位置{i}处多余的}}")
                    depth = 0
        if depth > 0:
            issues.append(f"{depth}个未闭合的{{")
        return len(issues) == 0, issues

    def _validate_dollar_balance(self, text: str) -> bool:
        """验证$配对"""
        # 排除 $$
        single_dollars = re.findall(r'(?<!\$)\$(?!\$)', text)
        return len(single_dollars) % 2 == 0

    @staticmethod
    def is_clean(text: str) -> bool:
        """快速检查文本是否需要LaTeX修复"""
        if not text:
            return True
        # 检查双反斜杠
        if re.search(r'\\\\(?:prime|begin|end|frac|sqrt|int|sum|lim|to|infty)', text):
            return False
        # 检查花括号
        if text.count('{') != text.count('}'):
            return False
        # 检查$配对
        single_dollars = re.findall(r'(?<!\$)\$(?!\$)', text)
        if len(single_dollars) % 2 != 0:
            return False
        return True
