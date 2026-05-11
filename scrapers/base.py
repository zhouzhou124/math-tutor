"""
爬虫基类 — 限速 / 重试 / UA轮换 / robots 检查
"""

import time
import random
import hashlib
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

# 常见浏览器 UA
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


class BaseScraper:
    """爬虫基类 — 所有站点爬虫继承此类"""

    def __init__(self, name: str, base_url: str, rate_limit: float = 2.0):
        self.name = name
        self.base_url = base_url
        self.rate_limit = rate_limit  # 请求间隔(秒)
        self._last_request = 0
        self._session = None
        self._cache = {}  # URL → 响应缓存

    @property
    def session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
            })
        return self._session

    def _rate_limit(self):
        """限速：确保请求间隔 >= rate_limit 秒"""
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed + random.uniform(0, 0.5))
        self._last_request = time.time()

    def fetch(self, url: str, use_cache: bool = True) -> str | None:
        """获取网页内容，带缓存、重试、限速"""
        if use_cache and url in self._cache:
            return self._cache[url]

        self._rate_limit()

        for attempt in range(3):
            try:
                # 轮换 UA
                self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                # 自动检测编码
                resp.encoding = resp.apparent_encoding or "utf-8"
                text = resp.text
                if use_cache:
                    self._cache[url] = text
                return text
            except Exception as e:
                if attempt == 2:
                    print(f"[{self.name}] 获取失败 {url}: {e}")
                    return None
                time.sleep(2 ** attempt)

        return None

    def parse(self, html: str) -> list[dict]:
        """
        解析 HTML → 题目列表。
        子类必须重写此方法。
        返回: [{"year":2024, "category":"数学一", "question_type":"解答题", ...}, ...]
        """
        raise NotImplementedError(f"{self.name} 未实现 parse()")

    def scrape(self, url: str) -> list[dict]:
        """完整爬取流程：获取 → 解析"""
        html = self.fetch(url)
        if not html:
            return []
        return self.parse(html)

    def check_robots(self, url: str = None) -> bool:
        """检查 robots.txt 是否允许爬取"""
        target = url or self.base_url
        domain = urlparse(target).netloc
        robots_url = f"https://{domain}/robots.txt"
        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(random.choice(USER_AGENTS), target)
        except Exception:
            return True  # 无法获取 robots.txt 时默认允许


class ScraperManager:
    """管理多个爬虫实例，统一调度"""

    def __init__(self):
        self.scrapers: dict[str, BaseScraper] = {}

    def register(self, scraper: BaseScraper):
        self.scrapers[scraper.name] = scraper

    def scrape_all(self, math_type: str = None,
                   year: int = None) -> list[dict]:
        """运行所有已注册爬虫，汇总结果"""
        all_questions = []
        for name, scraper in self.scrapers.items():
            try:
                questions = scraper.scrape(
                    math_type=math_type, year=year
                ) if hasattr(scraper, 'scrape_all') else []
                all_questions.extend(questions)
            except Exception as e:
                print(f"[Manager] {name} 失败: {e}")
        return all_questions

    def scrape_from_html(self, html: str, source_name: str = "manual") -> list[dict]:
        """从用户粘贴的 HTML 中手动提取题目"""
        for scraper in self.scrapers.values():
            if hasattr(scraper, 'parse'):
                try:
                    result = scraper.parse(html)
                    if result:
                        return result
                except Exception:
                    continue
        return []
