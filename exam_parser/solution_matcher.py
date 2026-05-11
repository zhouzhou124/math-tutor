"""
解答匹配器 — 将试卷题目与solutions/目录中的解答交叉引用

solution目录结构:
  solutions/
    1987年解析/1987年解析.md
    1988年解析/1988年解析.md
    ...
    2024年解析/2024.md

匹配策略:
  1. 加载对应年份的解答文件
  2. 解析为 {question_number: {answer, solution}} 映射
  3. 按题号直接匹配（主力）
  4. 模糊文本相似度fallback
"""

import re
from pathlib import Path
from dataclasses import dataclass
from difflib import SequenceMatcher
from .format_detector import FormatInfo, PaperFormat
from .math_fingerprint import MathFingerprint


@dataclass
class SolutionMatch:
    question_number: int
    question_text_snippet: str
    matched: bool
    answer: str
    solution_text: str
    solution_steps: list[str]
    match_method: str     # "exact_number" / "fuzzy_text" / "none"
    confidence: float


class SolutionMatcher:
    """匹配试卷题目到solutions/目录"""

    def __init__(self, solutions_base: str = ""):
        self.solutions_base = Path(solutions_base) if solutions_base else None
        self._cache: dict[str, dict] = {}  # cache_key → {num: {answer, solution}}

    def match_year(self, questions: list, year: int,
                   math_type: str = "数学一") -> list[SolutionMatch]:
        """为某年份所有题目匹配解答"""
        if self.solutions_base is None:
            return [SolutionMatch(
                question_number=q.question_number,
                question_text_snippet=(q.raw_text or "")[:60],
                matched=False, answer="", solution_text="", solution_steps=[],
                match_method="none", confidence=0.0,
            ) for q in questions]

        # 加载解答文件
        solution_text = self._load_solution(year, math_type)
        if not solution_text:
            return [SolutionMatch(
                question_number=q.question_number,
                question_text_snippet=(q.raw_text or "")[:60],
                matched=False, answer="", solution_text="", solution_steps=[],
                match_method="none", confidence=0.0,
            ) for q in questions]

        # 解析解答文件为映射
        solution_map = self._parse_solution_blocks(solution_text, year)

        results = []
        for q in questions:
            q_text = q.raw_text or ""

            # Layer 1: 加权数学指纹匹配
            match = self._match_by_fingerprint(q_text, solution_map)
            if match:
                results.append(match)
                continue

            # Layer 2: 题号直接匹配
            match = self._match_by_number(q.question_number, solution_map)
            if match:
                results.append(match)
                continue

            # Layer 3: SeqMatcher 文本相似度
            match = self._match_by_fuzzy_text(q_text, solution_map)
            if match:
                results.append(match)
                continue

            # 未匹配
            results.append(SolutionMatch(
                question_number=q.question_number,
                question_text_snippet=q_text[:60],
                matched=False, answer="", solution_text="", solution_steps=[],
                match_method="none", confidence=0.0,
            ))

        return results

    def match_single(self, question_text: str, question_number: int,
                     year: int, math_type: str = "数学一") -> SolutionMatch:
        """匹配单道题"""
        if self.solutions_base is None:
            return SolutionMatch(
                question_number=question_number,
                question_text_snippet=question_text[:60],
                matched=False, answer="", solution_text="", solution_steps=[],
                match_method="none", confidence=0.0,
            )
        solution_text = self._load_solution(year, math_type)
        if not solution_text:
            return SolutionMatch(
                question_number=question_number,
                question_text_snippet=question_text[:60],
                matched=False, answer="", solution_text="", solution_steps=[],
                match_method="none", confidence=0.0,
            )
        solution_map = self._parse_solution_blocks(solution_text, year)
        return (
            self._match_by_number(question_number, solution_map) or
            self._match_by_fuzzy_text(question_text, solution_map) or
            SolutionMatch(
                question_number=question_number,
                question_text_snippet=question_text[:60],
                matched=False, answer="", solution_text="", solution_steps=[],
                match_method="none", confidence=0.0,
            )
        )

    def _load_solution(self, year: int, math_type: str = "数学一") -> str | None:
        """加载某年份的解答文件（带缓存）"""
        cache_key = f"{year}_{math_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 尝试多种文件名模式
        math_abbr = {"数学一": "数学一"}
        base = self.solutions_base

        patterns = [
            base / f"{year}年解析" / f"{year}年解析.md",
            base / f"{year}年解析" / f"{year}.md",
            base / f"{year}年解析" / f"{year}年{math_abbr.get(math_type, '')}解析.md",
        ]

        for path in patterns:
            if path.exists():
                try:
                    text = path.read_text(encoding="utf-8")
                    # 缓存原始文本（parse会缓存解析结果）
                    self._cache[cache_key] = text
                    return text
                except Exception as e:
                    import logging
                    logging.warning(f"SolutionMatcher: failed to read {path}: {e}")

        return None

    def _parse_solution_blocks(self, solution_text: str, year: int) -> dict:
        """解析解答文件为 {question_number: {answer, solution}} 映射"""
        # Try old format parser first (most widespread)
        result = self._parse_old_solution(solution_text)
        if result:
            return result
        # Fall back to modern format
        return self._parse_modern_solution(solution_text)

    def _parse_old_solution(self, text: str) -> dict:
        """解析老格式解答。用递增索引避免节内编号覆盖。
        返回 {unique_index: {answer, solution, steps}}"""
        result = {}
        unique_idx = 0

        # 模式: （N）【答案】... 【解】... 或 （N）【解】...
        pattern = re.compile(
            r'[（(](\d+)[）)]\s*(?:【答案】(.*?))?\s*(?:【解】(.*?))?(?=[（(]\d+[）)]|$)', re.DOTALL
        )
        for m in pattern.finditer(text):
            answer = m.group(2).strip()[:500] if m.group(2) else ""
            solution = m.group(3).strip()[:2000] if m.group(3) else ""
            # Skip entries with neither answer nor solution
            if not answer and not solution:
                continue
            result[unique_idx] = {
                "answer": answer,
                "solution": solution,
                "steps": self._split_steps(solution),
                "section_number": int(m.group(1)),  # 保留节内题号供参考
            }
            unique_idx += 1

        return result

    def _parse_modern_solution(self, text: str) -> dict:
        """解析现代格式解答: 【N】【答案】... 【解】..."""
        result = {}
        # 模式1: 【N】【答案】... 【解】...
        pattern1 = re.compile(
            r'【(\d+)】\s*【答案】(.*?)(?:【解】(.*?))?(?=【\d+】|$)', re.DOTALL
        )
        for m in pattern1.finditer(text):
            num = int(m.group(1))
            answer = m.group(2).strip()[:500]
            solution = m.group(3).strip()[:2000] if m.group(3) else ""
            result[num] = {
                "answer": answer, "solution": solution,
                "steps": self._split_steps(solution),
            }

        if result:
            return result

        # 模式2: N．【答案】... 【解】... (混合格式)
        pattern2 = re.compile(
            r'(?:^|\n)\s*(\d+)[．.]\s*【答案】(.*?)(?:【解】(.*?))?(?=\n\s*\d+[．.]|$)', re.DOTALL
        )
        for m in pattern2.finditer(text):
            num = int(m.group(1))
            answer = m.group(2).strip()[:500]
            solution = m.group(3).strip()[:2000] if m.group(3) else ""
            result[num] = {
                "answer": answer, "solution": solution,
                "steps": self._split_steps(solution),
            }

        return result

    def _match_by_fingerprint(self, question_text: str,
                              solution_map: dict) -> SolutionMatch | None:
        """加权数学指纹匹配"""
        if not question_text or not solution_map:
            return None

        q_fp = MathFingerprint(question_text)
        q_items = q_fp.weighted_items()
        if not q_items:
            return None

        best_score = 0.0
        best_entry = None

        for _idx, entry in solution_map.items():
            sol_text = entry.get("answer", "") + " " + entry.get("solution", "")
            if not sol_text.strip():
                continue
            s_fp = MathFingerprint(sol_text)
            s_items = s_fp.weighted_items()
            score = MathFingerprint.weighted_jaccard(q_items, s_items)

            if score > best_score:
                best_score = score
                best_entry = entry

        if best_score >= 0.15 and best_entry is not None:
            return SolutionMatch(
                question_number=0,
                question_text_snippet=question_text[:60],
                matched=True,
                answer=best_entry.get("answer", ""),
                solution_text=best_entry.get("solution", ""),
                solution_steps=best_entry.get("steps", []),
                match_method="fingerprint",
                confidence=min(0.85, best_score * 2.0),
            )
        return None

    def _match_by_number(self, question_number: int,
                         solution_map: dict) -> SolutionMatch | None:
        """按题号直接匹配"""
        if question_number in solution_map:
            sol = solution_map[question_number]
            return SolutionMatch(
                question_number=question_number,
                question_text_snippet="",
                matched=True,
                answer=sol["answer"],
                solution_text=sol["solution"],
                solution_steps=sol.get("steps", []),
                match_method="exact_number",
                confidence=0.95,
            )
        return None

    def _match_by_fuzzy_text(self, question_text: str,
                             solution_map: dict) -> SolutionMatch | None:
        """模糊文本相似度匹配（fallback）"""
        if not question_text or not solution_map:
            return None
        best_score = 0.0
        best_num = None
        for num, sol in solution_map.items():
            # 用解答文本与题目文本比较
            score = SequenceMatcher(None, question_text[:200],
                                   sol.get("solution", "")[:200]).ratio()
            if score > best_score:
                best_score = score
                best_num = num
        if best_score > 0.30 and best_num is not None:
            sol = solution_map[best_num]
            return SolutionMatch(
                question_number=best_num,
                question_text_snippet=question_text[:60],
                matched=True,
                answer=sol["answer"],
                solution_text=sol["solution"],
                solution_steps=sol.get("steps", []),
                match_method="fuzzy_text",
                confidence=min(0.85, best_score),
            )
        return None

    def _split_steps(self, solution_text: str) -> list[str]:
        """将解答文本拆分为步骤"""
        if not solution_text:
            return []
        methods = re.split(r'(?:方法[一二三四五六七八九十\d]+[:：]|解法[一二三四五六七八九十\d]+[:：])', solution_text)
        if len(methods) > 1:
            return [m.strip() for m in methods if m.strip()][:8]
        steps = re.split(r'(?:^|\n)\s*(?:\(?\d+\)?\s*[\.\、]|步骤\s*\d+)', solution_text)
        steps = [s.strip() for s in steps if s.strip()]
        if len(steps) > 1:
            return steps[:8]
        parts = [s.strip() for s in solution_text.split('\n\n') if s.strip()]
        if len(parts) > 1:
            return parts[:8]
        return [solution_text[:500]]
