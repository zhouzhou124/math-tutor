"""
荒原之梦 (zhaokaifeng.com) 真题爬虫

通过 WordPress REST API 获取考研数学一/二/三的历年真题文章，
解析 HTML 内容提取题目、答案和解析，导入 QuestionDB。

URL 模式:
  /wp-json/wp/v2/posts?search=考研数学{一/二/三}真题&per_page=100

内容结构:
  一、填空题  (每题含答案+解析)
  二、选择题
  三、解答题
"""

import re
import json
import time
import urllib.request
import urllib.parse
from database.question_db import KNOWLEDGE_TAGS

API_BASE = "https://zhaokaifeng.com/wp-json/wp/v2"


class ZhaokaifengScraper:
    """荒原之梦真题爬虫"""

    # 章节标题 → 题型映射
    SECTION_TYPE_MAP = {
        "填空": "填空题",
        "选择": "选择题",
        "解答": "解答题",
        "证明": "证明题",
        "计算": "解答题",
        "综合": "解答题",
    }

    # LaTeX → 知识点
    LATEX_KP = {
        r'\lim': '极限', r'\int': '定积分', r'\iint': '二重积分',
        r'\sum': '无穷级数', r'\frac{d}{dx}': '导数',
        r'\partial': '偏导数', r'\det': '行列式', r'\lambda': '特征值',
        r'\begin{pmatrix}': '矩阵', r'\begin{vmatrix}': '行列式',
        r'E(X)': '数字特征', r'D(X)': '数字特征', r'P(A|B)': '条件概率',
    }

    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self._last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def _api_get(self, url: str) -> dict | list:
        """调用 REST API"""
        self._rate_limit()
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Educational Research Bot)",
            "Accept": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode("utf-8"))

    def search_posts(self, keyword: str, per_page: int = 100) -> list[dict]:
        """搜索包含关键词的文章"""
        encoded = urllib.parse.quote(keyword)
        url = f"{API_BASE}/posts?search={encoded}&per_page={per_page}&_embed"
        return self._api_get(url)

    def get_post(self, post_id: int) -> dict:
        """获取单篇文章完整内容"""
        url = f"{API_BASE}/posts/{post_id}"
        return self._api_get(url)

    def scrape_all(self) -> list[dict]:
        """爬取所有数学一真题"""
        all_questions = []

        # 策略1: REST API 搜索真题文章
        for math_keyword in ["数一 真题", "真题解析"]:
            print(f"\n[REST API] 搜索: {math_keyword}")
            posts = self.search_posts(math_keyword, per_page=100)
            print(f"  找到 {len(posts)} 篇文章")

            for post in posts:
                title = post["title"]["rendered"]
                slug = post.get("slug", "")

                math_type = self._detect_math_type(title, slug)
                if not math_type:
                    continue

                year = self._detect_year(title, slug)
                if not year:
                    continue

                print(f"  [{year}] {math_type}: {title[:60]}...")

                try:
                    full_post = self.get_post(post["id"])
                    content = full_post["content"]["rendered"]
                    questions = self.parse_content(content, year, math_type)
                    all_questions.extend(questions)
                    print(f"    解析出 {len(questions)} 题")
                except Exception as e:
                    print(f"    失败: {e}")

        # 策略2: 直接抓取 deconstructing 风格的页面（2026-2010）
        for year in range(2026, 2010, -1):
            for paper_num, mt in [("i", "数学一")]:
                url = self._make_deconstruct_url(year, paper_num)
                try:
                    html = self._fetch_html(url)
                    if not html:
                        continue
                    print(f"  [Direct] [{year}] {mt}: {url.split('/')[-2][:60]}")
                    questions = self.parse_content(html, year, mt)
                    all_questions.extend(questions)
                    print(f"    解析出 {len(questions)} 题")
                except Exception:
                    pass  # 页面不存在

        return all_questions

    def _detect_math_type(self, title: str, slug: str) -> str | None:
        for kw, mt in [("数一", "数学一"), ("数学一", "数学一"), ("paper-i", "数学一")]:
            if kw in title + slug:
                return mt
        return None

    def _detect_year(self, title: str, slug: str) -> int | None:
        m = re.search(r'(\d{4})', title + slug)
        if m:
            y = int(m.group(1))
            if 1987 <= y <= 2026:
                return y
        return None

    def _make_deconstruct_url(self, year: int, paper: str) -> str:
        return (f"https://zhaokaifeng.com/"
                f"deconstructing-the-questions-in-the-{year}"
                f"-mathematics-paper-{paper}"
                f"-for-national-postgraduate-entrance-examination/")

    def _fetch_html(self, url: str) -> str | None:
        """直接抓取HTML页面"""
        self._rate_limit()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Educational Research Bot)",
            })
            resp = urllib.request.urlopen(req, timeout=30)
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return None

    def parse_content(self, html: str, year: int, math_type: str) -> list[dict]:
        """解析文章 HTML 内容 → 题目列表"""
        # 清理 HTML
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL)

        # 找到主要内容区域
        # 去除 WordPress 导航等
        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL)

        # 按章节分割
        sections = self._split_sections(html)
        if not sections:
            return []

        questions = []
        for section_title, section_html in sections:
            qtype = self._identify_type(section_title)
            if not qtype:
                continue

            # 按题号分割
            items = self._split_questions(section_html)
            for idx, item_html in enumerate(items):
                q = self._parse_question(item_html, year, math_type, qtype, idx + 1)
                if q and len(q.get("question", "")) > 10:
                    questions.append(q)

        return questions

    def _split_sections(self, html: str) -> list[tuple[str, str]]:
        """按 一、二、三、 章节分割"""
        # 匹配题型章节标题
        pattern = r'<[^>]*>\s*([一二三四五六七八九十])[、，]\s*(\S*?(?:填空|选择|解答|证明|计算|综合)\S*?)\s*</[^>]*>'
        matches = list(re.finditer(pattern, html))

        if not matches:
            # 尝试纯文本匹配
            text = re.sub(r'<[^>]+>', ' ', html)
            pattern2 = r'([一二三四五六七八九十])[、，]\s*(\S*?(?:填空|选择|解答|证明|计算|综合)\S*)'
            text_matches = list(re.finditer(pattern2, text))
            if text_matches:
                sections = []
                for i, m in enumerate(text_matches):
                    start = m.start()
                    end = text_matches[i + 1].start() if i + 1 < len(text_matches) else len(text)
                    title = m.group(0)
                    sections.append((title, text[start:end]))
                return sections
            return []

        sections = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
            title = m.group(1) + "、" + m.group(2)
            sections.append((title, html[start:end]))

        return sections

    def _identify_type(self, title: str) -> str | None:
        """从章节标题识别题型"""
        for keyword, qtype in self.SECTION_TYPE_MAP.items():
            if keyword in title:
                return qtype
        return None

    def _split_questions(self, html: str) -> list[str]:
        """按题号 (1) (2) 或 1. 2. 分割"""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()

        # 尝试多种题号格式
        patterns = [
            r'(?:^|\s)\s*[（(](\d{1,2})[）)]\s*',     # (1) （1）
            r'(?:^|\n)\s*(\d{1,2})[\.\、]?\s+(?=[A-Z一-鿿])',  # "1. 题目"
        ]

        for pat in patterns:
            splits = re.split(pat, text)
            if len(splits) > 2:
                result = []
                for i in range(1, len(splits), 2):
                    if i + 1 < len(splits):
                        result.append(f"({splits[i]}) {splits[i + 1].strip()}")
                if len(result) >= 2:
                    return result

        return [text] if len(text) > 20 else []

    def _parse_question(self, text: str, year: int, math_type: str,
                        qtype: str, number: int) -> dict | None:
        """解析单道题"""
        text = text.strip()
        if len(text) < 10:
            return None

        # 提取题干（去掉答案部分）
        question_body = text
        answer = ""
        analysis = ""

        # 找答案标记
        ans_patterns = [
            r'(?:正确)?答案[：:]\s*(.*?)(?=\n|解析|分析|解答|$)',
            r'(?:正确)?答案[：:](.*?)$',
        ]
        for pat in ans_patterns:
            m = re.search(pat, question_body)
            if m:
                answer = m.group(1).strip()[:200]
                question_body = question_body[:m.start()].strip()
                # 提取解析
                rest = text[m.end():]
                analysis = rest.strip()[:500]
                break

        # 清理题干
        question_body = re.sub(r'^[（(]\d+[）)]\s*', '', question_body).strip()

        # 知识标签
        knowledge_points = self._detect_kp(question_body)
        difficulty = self._infer_diff(question_body, qtype)

        return {
            "year": year,
            "category": math_type,
            "question_type": qtype,
            "knowledge_points": knowledge_points,
            "difficulty": difficulty,
            "score": {"选择题": 4, "填空题": 4, "解答题": 10, "证明题": 12}.get(qtype, 10),
            "question": question_body.strip()[:2000],
            "standard_answer": answer,
            "solution_steps": [analysis] if analysis else [],
            "common_mistakes": [],
            "tags": knowledge_points,
            "source": "zhaokaifeng_scraper",
        }

    def _detect_kp(self, text: str) -> list[str]:
        found = []
        for tag in KNOWLEDGE_TAGS:
            if len(tag) >= 2 and tag in text:
                found.append(tag)
        for latex, kp in self.LATEX_KP.items():
            if latex in text and kp not in found:
                found.append(kp)
        seen = set()
        result = []
        for t in sorted(found, key=len, reverse=True):
            if t not in seen:
                result.append(t)
                seen.add(t)
        return result[:5]

    def _infer_diff(self, text: str, qtype: str) -> str:
        if qtype == "证明题":
            return "较难"
        hard_kw = ["证明", "求证", "二重积分", "三重积分", "曲线积分", "曲面积分", "级数"]
        basic_kw = ["求极限", "求导数", "求偏导", "计算不定积分", "计算定积分"]
        if any(kw in text[:100] for kw in hard_kw):
            return "较难"
        if any(kw in text[:100] for kw in basic_kw):
            return "基础"
        return "中等"
