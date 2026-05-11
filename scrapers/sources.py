"""
具体站点爬虫实现

⚠️ 说明:
  - 仅爬取公开可访问的教育网站内容
  - 所有爬虫遵守 robots.txt
  - 请求间隔 >= 3 秒，避免对目标服务器造成压力
  - 爬取结果标注数据来源

支持的来源类型:
  1. 公开教育网站 (PublicEduScraper) — 自动爬取
  2. 用户粘贴HTML (ManualHTMLScraper) — 手动复制粘贴
"""

import re
import json
from html import unescape
from .base import BaseScraper


class PublicEduScraper(BaseScraper):
    """
    公开教育网站通用爬虫

    适配常见的中文教育网站 HTML 结构:
      - <div class="question-item"> 或 <div class="exam-question">
      - 包含题目类型标签 (选择题/填空题/解答题)
      - 包含年份和数学类别信息

    使用方法:
      scraper = PublicEduScraper()
      questions = scraper.scrape_from_url("https://example.com/exam/2024-math1")
    """

    # 常见的题目容器 class/id
    QUESTION_CONTAINERS = [
        r'<div[^>]*class="[^"]*(?:question|timu|exam-item|problem|subject)[^"]*"[^>]*>',
        r'<div[^>]*id="[^"]*(?:question|timu|problem)[^"]*"[^>]*>',
        r'<article[^>]*>',
        r'<section[^>]*class="[^"]*(?:question|exam|problem)[^"]*"[^>]*>',
        r'<li[^>]*class="[^"]*(?:question|exam-item|list-item)[^"]*"[^>]*>',
    ]

    def __init__(self):
        super().__init__(
            name="public_edu",
            base_url="",
            rate_limit=3.0,
        )

    def scrape_from_url(self, url: str, math_type: str = "数学一",
                        year: int = None) -> list[dict]:
        """从指定 URL 爬取题目"""
        html = self.fetch(url)
        if not html:
            return []

        questions = self.parse(html)

        # 如果 URL 或页面中没有年份/类别信息，用参数补全
        for q in questions:
            if not q.get("year") and year:
                q["year"] = year
            if not q.get("category"):
                q["category"] = math_type

        return questions

    def parse(self, html: str) -> list[dict]:
        """从 HTML 中提取题目"""
        # 清理 HTML
        html = unescape(html)
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        html = re.sub(r'<br\s*/?>', '\n', html)

        questions = []

        # 尝试按题号分割
        blocks = self._split_by_number(html)
        if len(blocks) <= 1:
            # 如果题号分割失败，尝试按容器分割
            blocks = self._split_by_container(html)

        for i, block in enumerate(blocks):
            q = self._extract_question(block, i + 1)
            if q and len(q.get("question", "")) > 20:
                questions.append(q)

        return questions

    def _split_by_number(self, html: str) -> list[str]:
        """按题号分割 (如 '1.', '（1）', '一、')"""
        # 移除 HTML 标签以便按题号分割
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()

        # 匹配各类题号
        number_patterns = [
            r'(?:^|\n)\s*(\d{1,2})[\.\、\)）]\s*',       # "1." "12."
            r'(?:^|\n)\s*[（(](\d{1,2})[）)]\s*',         # "（1）"
            r'(?:^|\n)\s*(第[一二三四五六七八九十\d]+题)',    # "第一题"
        ]

        for pat in number_patterns:
            splits = re.split(pat, html)
            if len(splits) > 3:
                result = []
                for j in range(1, len(splits), 2):
                    if j + 1 < len(splits):
                        result.append(splits[j + 1].strip())
                return result

        return [html]

    def _split_by_container(self, html: str) -> list[str]:
        """按容器标签分割"""
        for pattern in self.QUESTION_CONTAINERS:
            matches = list(re.finditer(pattern, html, re.IGNORECASE))
            if len(matches) >= 2:
                blocks = []
                for i, m in enumerate(matches):
                    start = m.start()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
                    blocks.append(html[start:end])
                return blocks
        return [html]

    def _extract_question(self, block: str, index: int) -> dict | None:
        """从题目块中提取结构化信息"""
        # 清理 HTML 保留文本
        text = re.sub(r'<[^>]+>', ' ', block)
        text = unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 20:
            return None

        # 推断题型
        qtype = self._detect_type(text)
        # 推断知识点
        kps = self._detect_knowledge_points(text)
        # 推断难度
        diff = self._detect_difficulty(text, qtype)
        # 尝试从 URL 或页面获取年份
        year = self._detect_year(block)

        return {
            "year": year or 2024,
            "category": "",  # 由调用方填充
            "question_type": qtype,
            "knowledge_points": kps,
            "difficulty": diff,
            "score": {"选择题": 4, "填空题": 4, "解答题": 10, "证明题": 12}.get(qtype, 10),
            "question": text[:2000],
            "standard_answer": "",
            "solution_steps": [],
            "common_mistakes": [],
            "tags": kps,
            "source": "public_edu_scraper",
        }

    def _detect_type(self, text: str) -> str:
        first_50 = text[:50]
        if any(w in first_50 for w in ["选择", "下列选", "正确的一项是"]):
            return "选择题"
        if any(w in first_50 for w in ["填空", "______"]):
            return "填空题"
        if any(w in first_50 for w in ["证明", "求证"]):
            return "证明题"
        # 有选项标记 (A. B. C. D.)
        if re.search(r'[A-D][\.\、]', first_50):
            return "选择题"
        return "解答题"

    def _detect_knowledge_points(self, text: str) -> list[str]:
        """从文本中检测知识点"""
        from database.question_db import KNOWLEDGE_TAGS
        found = []
        for tag in KNOWLEDGE_TAGS:
            if len(tag) >= 2 and tag in text:
                found.append(tag)
        # 去重，限制数量
        seen = set()
        result = []
        for t in found:
            if t not in seen and not any(t in s for s in seen):
                result.append(t)
                seen.add(t)
        return result[:5]

    def _detect_difficulty(self, text: str, qtype: str) -> str:
        if qtype == "证明题":
            return "较难"
        text_100 = text[:100]
        if any(w in text_100 for w in ["求极限", "求导数", "计算不定积分", "计算定积分"]):
            return "基础"
        if any(w in text_100 for w in ["证明", "二重积分", "级数", "微分方程"]):
            return "中等"
        return "中等"

    def _detect_year(self, html: str) -> int | None:
        match = re.search(r'(19[8-9]\d|20[0-2]\d)\s*年', html)
        if match:
            return int(match.group(1))
        return None


class ManualHTMLScraper(BaseScraper):
    """
    手动粘贴 HTML 爬虫

    用户从任意教育网站复制 HTML 内容，粘贴后自动解析。

    使用场景:
      - 目标网站有反爬机制
      - 需要登录才能访问
      - 只想提取特定页面的题目
    """

    def __init__(self):
        super().__init__(name="manual_html", base_url="", rate_limit=0)

    def parse(self, html: str) -> list[dict]:
        """使用 PublicEduScraper 的解析逻辑"""
        edu = PublicEduScraper()
        return edu.parse(html)

    def paste_and_parse(self, html: str, math_type: str = "数学一",
                        year: int = None) -> list[dict]:
        """
        解析用户粘贴的 HTML

        参数:
          html: 用户粘贴的网页内容
          math_type: 数学类别 (数学一/二/三)
          year: 年份 (如果无法自动检测)

        返回: 题目列表
        """
        questions = self.parse(html)
        for q in questions:
            if not q.get("year"):
                q["year"] = year or 2024
            q["category"] = math_type
        return questions
