"""
考研真题 Markdown 解析器

适配 TsekaLuk/Kaoyan-Math1-Papers 仓库的数据格式:
  - 每年一个 .md 文件
  - 一级标题: # 2024年考研数学一真题
  - 二级标题: ## 一、选择题 / 二、填空题 / 三、解答题
  - 题目: ### N. 或 N.
  - 答案: 【答案】 ...
  - 解析: 【解析】 ...

同时支持 fjh1997/China-NPEE-math 的格式变体。

用法:
  parser = MarkdownExamParser()
  questions = parser.parse_directory("storage/math1_source/")
  # questions 可直接传给 QuestionImporter.import_dict()
"""

import re
import json
from pathlib import Path
from database.question_db import KNOWLEDGE_TAGS


class MarkdownExamParser:
    """考研数学 Markdown 真题解析器"""

    # 题型映射: Markdown 章节标题 → 标准题型名
    TYPE_MAP = {
        "选择题": "选择题",
        "填空题": "填空题",
        "解答题": "解答题",
        "证明题": "证明题",
        "综合题": "解答题",
    }

    # 分值默认
    DEFAULT_SCORES = {
        "选择题": 4,
        "填空题": 4,
        "解答题": 10,
        "证明题": 12,
    }

    def parse_directory(self, dir_path: str) -> list[dict]:
        """解析整个目录下的 Markdown 文件，返回所有题目"""
        path = Path(dir_path)
        if not path.exists():
            print(f"目录不存在: {dir_path}")
            return []

        all_questions = []
        md_files = sorted(path.glob("*.md"))
        if not md_files:
            # 搜索子目录
            md_files = sorted(path.rglob("*.md"))

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                questions = self.parse_year(content, str(md_file.name))
                all_questions.extend(questions)
                print(f"  {md_file.name}: 解析出 {len(questions)} 题")
            except Exception as e:
                print(f"  {md_file.name}: 解析失败 - {e}")

        return all_questions

    def parse_year(self, content: str, filename: str = "") -> list[dict]:
        """解析单个年份的文件内容"""
        # 提取年份和数学类别
        year = self._extract_year(content, filename)
        math_type = self._extract_math_type(content, filename)

        questions = []

        # 按题型章节分割
        sections = self._split_sections(content)

        for section_title, section_text in sections:
            qtype = self._identify_type(section_title)
            if not qtype:
                continue

            # 按题号分割
            items = self._split_questions(section_text)
            for idx, item_text in enumerate(items):
                q = self._parse_question(item_text, year, math_type, qtype, idx + 1)
                if q and len(q.get("question", "")) > 15:
                    questions.append(q)

        return questions

    def _extract_year(self, content: str, filename: str) -> int:
        """提取年份"""
        # 从标题: # 2024年考研数学一真题
        m = re.search(r'(\d{4})\s*年', content[:200])
        if m:
            return int(m.group(1))
        # 从文件名: 2024-数学一.md
        m = re.search(r'(\d{4})', filename)
        if m:
            return int(m.group(1))
        return 2024

    def _extract_math_type(self, content: str, filename: str) -> str:
        """提取数学类别"""
        text = content[:200] + filename
        if "数一" in text or "数学一" in text or "数学(一)" in text:
            return "数学一"
        return "数学一"

    def _split_sections(self, content: str) -> list[tuple[str, str]]:
        """按二级标题 ## 分割章节"""
        # 匹配 ## 一、选择题 / ## 二、填空题 等
        pattern = r'^##\s+(.*?)$'
        lines = content.split("\n")

        sections = []
        current_title = "前言"
        current_text = []

        for line in lines:
            m = re.match(pattern, line.strip())
            if m:
                if current_text:
                    sections.append((current_title, "\n".join(current_text)))
                current_title = m.group(1).strip()
                current_text = []
            else:
                current_text.append(line)

        if current_text:
            sections.append((current_title, "\n".join(current_text)))

        return sections

    def _identify_type(self, title: str) -> str | None:
        """从章节标题识别题型"""
        title = title.strip()
        for keyword, qtype in self.TYPE_MAP.items():
            if keyword in title:
                return qtype
        # 尝试数字前缀 "一、" "二、"
        if re.match(r'[一二三四五六七八九十]、', title):
            # 无法确定时返回None，让调用方跳过
            pass
        return None

    def _split_questions(self, section_text: str) -> list[str]:
        """将章节内容按题号分割"""
        # 尝试多种题号模式
        patterns = [
            r'(?:^|\n)\s*###?\s*(\d{1,2})\s*[\.\、]?\s*\n',  # ### 1. 或 ## 1.
            r'(?:^|\n)\s*(\d{1,2})[\.\、\)）]\s+',            # "1. "  "1、"
        ]

        for pat in patterns:
            splits = re.split(pat, section_text)
            if len(splits) > 2:
                result = []
                for i in range(1, len(splits), 2):
                    if i + 1 < len(splits):
                        result.append(splits[i + 1].strip())
                if len(result) >= 2:
                    return result

        # 如果题目很少，整个section可能就是一道题
        text = section_text.strip()
        if len(text) > 20:
            return [text]
        return []

    def _parse_question(self, text: str, year: int, math_type: str,
                        qtype: str, number: int) -> dict | None:
        """解析单道题的结构化信息"""
        text = text.strip()
        if len(text) < 15:
            return None

        # 提取题目内容（答案标记之前的部分）
        question_text = self._extract_question_body(text)

        # 去掉 Markdown 标题前缀 (### 1. 或 **1.** 等)
        question_text = re.sub(r'^#{1,3}\s*\d+[\.\、]?\s*', '', question_text).strip()
        question_text = re.sub(r'^\*\*\d+[\.\、]?\*\*\s*', '', question_text).strip()

        # 提取答案
        answer = self._extract_answer(text)

        # 提取解析
        analysis = self._extract_analysis(text)

        # 自动识别知识点标签
        knowledge_points = self._detect_knowledge_points(question_text)

        # 推断难度
        difficulty = self._infer_difficulty(question_text, qtype, analysis)

        return {
            "year": year,
            "category": math_type,
            "question_type": qtype,
            "knowledge_points": knowledge_points,
            "difficulty": difficulty,
            "score": self.DEFAULT_SCORES.get(qtype, 10),
            "question": question_text.strip(),
            "standard_answer": answer.strip(),
            "solution_steps": self._split_steps(analysis),
            "common_mistakes": [],
            "tags": knowledge_points,
            "source": "github_markdown",
        }

    def _extract_question_body(self, text: str) -> str:
        """提取题目正文（去掉答案和解析部分）"""
        # 在【答案】或【解析】标记处截断
        for marker in ["【答案】", "【解】", "【解析】", "【分析】",
                       "**【答案】**", "**【解析】**"]:
            idx = text.find(marker)
            if idx > 0:
                text = text[:idx]
        return text.strip()

    def _extract_answer(self, text: str) -> str:
        """提取答案内容"""
        # 匹配 【答案】xxx 或 **答案** xxx
        patterns = [
            r'【答案】\s*(.*?)(?=【解析】|【分析】|【详解】|\Z)',
            r'【答案】(.*?)(?=【|$)',
            r'\*\*答案\*\*\s*[：:]\s*(.*?)(?=\n\n|\Z)',
            r'^答案[：:]\s*(.*?)$',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                ans = m.group(1).strip()
                if len(ans) > 1:
                    return ans[:500]
        return ""

    def _extract_analysis(self, text: str) -> str:
        """提取解析内容"""
        patterns = [
            r'【解析】\s*(.*?)(?=\Z)',
            r'【解析】(.*?)(?=\Z)',
            r'【分析】\s*(.*?)(?=\Z)',
            r'【详解】\s*(.*?)(?=\Z)',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL)
            if m:
                return m.group(1).strip()[:1000]
        return ""

    def _split_steps(self, analysis: str) -> list[str]:
        """从解析文本中拆分步骤"""
        if not analysis:
            return []
        # 按序号分割
        steps = re.split(r'(?:^|\n)\s*(?:\d+[\.\、\)]|步骤\s*\d+|Step\s*\d+)', analysis)
        steps = [s.strip() for s in steps if s.strip()]
        return steps[:8] if len(steps) > 1 else [analysis[:200]]

    # LaTeX 符号 → 知识点映射
    LATEX_TO_KNOWLEDGE = {
        r'\lim': '极限', r'\to': '极限', r'\infty': '极限',
        r'\frac{d}{dx}': '导数', r"f'": '导数', r'\partial': '偏导数',
        r'\int': '定积分', r'\iint': '二重积分', r'\iiint': '三重积分',
        r'\oint': '曲线积分', r'\sum': '无穷级数',
        r'\det': '行列式', r'\begin{vmatrix}': '行列式',
        r'\begin{pmatrix}': '矩阵', r'\text{tr}': '矩阵',
        r'\lambda': '特征值', r'\vec': '向量组',
        r'P(A|B)': '条件概率', r'P(AB)': '概率',
        r'E(X)': '数字特征', r'D(X)': '数字特征', r'Var': '数字特征',
        r'\lim_{n\to\infty}': '极限',
        r'\lim_{x \to': '极限',
    }

    def _detect_knowledge_points(self, text: str) -> list[str]:
        """从题目文本中识别知识点标签（支持中文关键词+LaTeX符号）"""
        found = []

        # 中文关键词匹配
        for tag in KNOWLEDGE_TAGS:
            if len(tag) >= 2 and tag in text:
                found.append(tag)

        # LaTeX 符号匹配
        for latex_sym, knowledge in self.LATEX_TO_KNOWLEDGE.items():
            if latex_sym in text and knowledge not in found:
                found.append(knowledge)

        # 去重
        seen = set()
        result = []
        for t in sorted(found, key=len, reverse=True):
            if t not in seen:
                result.append(t)
                seen.add(t)
        return result[:5]

    def _infer_difficulty(self, text: str, qtype: str, analysis: str) -> str:
        """推断题目难度"""
        if qtype == "证明题":
            return "较难"

        combined = text + analysis
        # 基础题特征
        basic_keywords = ["求极限", "求导数", "求积分", "计算定积分",
                         "计算不定积分", "求偏导", "求微分"]
        # 难题特征
        hard_keywords = ["证明", "求证", "二重积分", "三重积分", "曲线积分",
                        "曲面积分", "级数", "展开", "收敛"]

        basic_count = sum(1 for kw in basic_keywords if kw in combined[:100])
        hard_count = sum(1 for kw in hard_keywords if kw in combined[:100])

        if hard_count >= 2:
            return "较难"
        if basic_count >= 1:
            return "基础"
        return "中等"
