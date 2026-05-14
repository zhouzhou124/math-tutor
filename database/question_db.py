"""
考研数学真题数据库 — 核心引擎

三级分类体系:
  一级: 数学一
  二级: 年份 (1987-至今)
  三级: 题型 (选择题/填空题/解答题/证明题)

功能: CRUD / 搜索 / 筛选 / 标签管理 / 质量检查 / 去重
"""

import json
import os
import re
import time
from pathlib import Path
from difflib import SequenceMatcher

from config import STORAGE_DIR, MATH_TYPES, QUESTION_TYPES, DIFFICULTY_LEVELS

# 分离存储结构
EXAM_DIR = Path(STORAGE_DIR) / "questions" / "exams"      # 历年真题
SIMUL_DIR = Path(STORAGE_DIR) / "questions" / "simulations"  # 模拟卷
INDEX_PATH = Path(STORAGE_DIR) / "questions" / "_index.json"
PENDING_PATH = Path(STORAGE_DIR) / "questions" / "_pending_review.json"

def get_question_path(qid: str) -> Path:
    """根据题目ID获取文件路径"""
    if '宇哥八套卷' in qid:
        return SIMUL_DIR / f"{qid}.json"
    return EXAM_DIR / f"{qid}.json"

# 知识点标签全集
KNOWLEDGE_TAGS = [
    # 高等数学
    "极限", "连续", "导数", "微分", "中值定理", "不定积分", "定积分",
    "反常积分", "定积分应用", "微分方程", "多元函数微分", "偏导数",
    "二重积分", "三重积分", "曲线积分", "曲面积分", "重积分",
    "无穷级数", "幂级数", "傅里叶级数", "向量代数", "空间解析几何",
    # 线性代数
    "行列式", "矩阵", "矩阵运算", "逆矩阵", "秩", "线性方程组",
    "向量组", "线性空间", "特征值", "特征向量", "相似对角化",
    "二次型", "合同变换", "正定矩阵", "线性变换",
    # 概率统计
    "随机事件", "概率", "条件概率", "独立性", "全概率公式", "贝叶斯公式",
    "随机变量", "分布函数", "密度函数", "常见分布", "多维随机变量",
    "边缘分布", "条件分布", "协方差", "相关系数", "数字特征",
    "大数定律", "中心极限定理", "数理统计", "参数估计", "假设检验",
]


def _ensure_dirs():
    EXAM_DIR.mkdir(parents=True, exist_ok=True)
    SIMUL_DIR.mkdir(parents=True, exist_ok=True)


def make_question_id(year: int, math_type: str, number: int, volume: str = None) -> str:
    """生成标准题号: 2024-数一-016 或 26宇哥八套卷-卷一-001"""
    if volume:
        # 有卷号的情况（如宇哥八套卷），不包含年份
        return f"{math_type}-{volume}-{number:03d}"
    abbr = {"数学一": "数一"}
    return f"{year}-{abbr.get(math_type, math_type)}-{number:03d}"


def category_group(question: dict) -> str:
    """Return the second-level category key: volume first, then year."""
    if question.get("volume"):
        return str(question["volume"])
    return str(question.get("year", ""))


class QuestionDB:
    """真题数据库"""

    def __init__(self):
        _ensure_dirs()
        self._init_index()
        # 索引缓存
        self._index_cache = None
        self._index_cache_time = 0
        # 题目缓存（LRU，最多缓存100题）
        self._question_cache = {}
        self._cache_max_size = 100

    # ==================== 索引管理 ====================

    def _init_index(self):
        if not INDEX_PATH.exists():
            index = {
                "categories": {},     # 三级分类树
                "knowledge_index": {}, # 知识点 → [id列表]
                "difficulty_index": {}, # 难度 → [id列表]
                "metadata": {
                    "total_questions": 0,
                    "last_updated": "",
                    "missing_data": [],
                    "pending_review": [],
                },
            }
            self._save_json(INDEX_PATH, index)

    def _load_index(self, force_reload: bool = False) -> dict:
        """加载索引，支持缓存（5秒内不重新加载）"""
        now = time.time()
        if not force_reload and self._index_cache is not None and (now - self._index_cache_time) < 5:
            return self._index_cache
        
        self._index_cache = self._load_json(INDEX_PATH)
        self._index_cache_time = now
        return self._index_cache

    def _clear_index_cache(self):
        """清除索引缓存（在索引更新后调用）"""
        self._index_cache = None
        self._index_cache_time = 0

    def _cache_question(self, qid: str, question: dict):
        """缓存题目，LRU策略"""
        if len(self._question_cache) >= self._cache_max_size:
            # 移除最旧的缓存（FIFO策略）
            oldest_key = next(iter(self._question_cache))
            del self._question_cache[oldest_key]
        self._question_cache[qid] = question

    def _get_cached_question(self, qid: str) -> dict:
        """从缓存获取题目"""
        return self._question_cache.get(qid)

    def _save_index(self, index: dict):
        index["metadata"]["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save_json(INDEX_PATH, index)

    def _load_json(self, path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_json(self, path, data):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== CRUD ====================

    def insert(self, question: dict) -> dict:
        """
        插入一道题。自动分配ID，更新所有索引。
        返回 {"success": bool, "question_id": str, "warnings": [str]}
        """
        warnings = []

        # 质量检查
        qc = self.validate(question)
        if not qc["valid"]:
            return {"success": False, "question_id": "", "warnings": qc["issues"]}
        warnings.extend(qc.get("warnings", []))

        # 去重检查
        dup = self._check_duplicate(question)
        if dup["is_duplicate"]:
            return {
                "success": False,
                "question_id": "",
                "warnings": [f"疑似重复: 与 {dup['existing_id']} 相似度 {dup['similarity']:.1%}"],
            }

        # 生成ID（考虑卷号，避免卷一和卷二ID碰撞）
        year = question["year"]
        math_type = question["category"]
        volume = question.get("volume", "")
        number = self._next_number(year, math_type, volume)
        qid = make_question_id(year, math_type, number, volume)
        question["question_id"] = qid

        # 写入数据文件
        data_path = get_question_path(qid)
        self._save_json(data_path, question)

        # 更新索引
        index = self._load_index()
        self._update_categories(index, question)
        self._update_knowledge_index(index, question)
        self._update_difficulty_index(index, question)
        index["metadata"]["total_questions"] += 1
        self._save_index(index)

        return {"success": True, "question_id": qid, "warnings": warnings}

    def get(self, question_id: str) -> dict | None:
        # 先从缓存获取
        cached = self._get_cached_question(question_id)
        if cached is not None:
            return cached
        
        data_path = get_question_path(question_id)
        if data_path.exists():
            q = self._load_json(data_path)
            self._cache_question(question_id, q)
            return q
        return None

    def update(self, question_id: str, updates: dict) -> bool:
        existing = self.get(question_id)
        if not existing:
            return False

        # 保护 ID 不被修改
        updates.pop("question_id", None)
        existing.update(updates)
        self._save_json(get_question_path(question_id), existing)
        # 更新后清除缓存
        if question_id in self._question_cache:
            del self._question_cache[question_id]
        self._clear_index_cache()
        self._clear_stats_cache()

        # 重建相关索引
        index = self._load_index()
        # 如果知识点变了
        if "knowledge_points" in updates or "tags" in updates:
            self._rebuild_knowledge_index(index)
        if "difficulty" in updates:
            self._rebuild_difficulty_index(index)
        self._save_index(index)
        return True

    def delete(self, question_id: str) -> bool:
        data_path = get_question_path(question_id)
        if not data_path.exists():
            return False

        question = self._load_json(data_path)
        data_path.unlink()

        # 更新索引
        index = self._load_index()
        self._remove_from_index(index, question)
        index["metadata"]["total_questions"] -= 1
        self._save_index(index)
        
        # 清除缓存
        if question_id in self._question_cache:
            del self._question_cache[question_id]
        self._clear_index_cache()
        self._clear_stats_cache()
        return True

    # ==================== 搜索 ====================

    def search(self, **filters) -> list[dict]:
        """
        搜索题目。支持的过滤条件:
          math_type: 数学类别
          year: 年份
          volume: 卷号（用于非真题类别如宇哥八套卷）
          question_type: 题型
          knowledge_point: 知识点（支持部分匹配）
          difficulty: 难度
          keyword: 题目内容关键词
          limit: 返回数量上限(默认50)
        """
        limit = filters.pop("limit", 50)
        candidate_ids = None

        # 只加载一次索引
        index = self._load_index()

        # 卷号过滤：从 categories 索引获取该卷的题目 ID
        if filters.get("volume"):
            vol = filters.pop("volume")
            mt = filters.get("math_type", "")
            if mt:
                vol_ids = index.get("categories", {}).get(mt, {}).get(vol, {})
                candidate_ids = set()
                for ids in vol_ids.values():
                    candidate_ids.update(ids)

        # 用最精确的索引缩小范围
        if filters.get("knowledge_point"):
            kp = filters["knowledge_point"]
            ki = index.get("knowledge_index", {})
            matches = [ids for key, ids in ki.items() if kp in key]
            if matches:
                if candidate_ids is not None:
                    # 交集优化
                    kp_ids = set()
                    for m in matches:
                        kp_ids.update(m)
                    candidate_ids.intersection_update(kp_ids)
                else:
                    candidate_ids = set()
                    for m in matches:
                        candidate_ids.update(m)
            else:
                return []  # 知识点不匹配

        if candidate_ids is None and filters.get("difficulty"):
            di = index.get("difficulty_index", {})
            candidate_ids = set(di.get(filters["difficulty"], []))

        # 加载候选题
        questions = []
        if candidate_ids is not None:
            # 优先使用索引，只加载需要的题目
            candidate_list = list(candidate_ids)[:limit * 3]
            for qid in candidate_list:
                q = self.get(qid)
                if q:
                    questions.append(q)
        else:
            # 全量扫描（首次或没有精确索引）
            questions = self._load_all(100000)  # 加载全部题目

        # 精确过滤
        results = []
        for q in questions:
            if self._match(q, filters) and len(results) < limit:
                results.append(q)

        # Stable sort by question_no (numeric)
        results.sort(key=lambda q: q.get("question_no", 0))
        return results

    def browse(self, math_type: str = None, year: int = None,
               question_type: str = None, page: int = 1,
               page_size: int = 20) -> dict:
        """分页浏览，返回 {items, total, page, total_pages}"""
        filters = {}
        if math_type:
            filters["math_type"] = math_type
        if year:
            filters["year"] = year
        if question_type:
            filters["question_type"] = question_type
        filters["limit"] = 10000  # large limit, paginate in memory

        all_results = self.search(**filters)
        total = len(all_results)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "items": all_results[start:end],
            "total": total,
            "page": page,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }

    # ==================== 统计 ====================

    def stats(self) -> dict:
        """数据库统计（带缓存）"""
        # 使用缓存，5秒内不重新计算
        now = time.time()
        if hasattr(self, '_stats_cache') and hasattr(self, '_stats_cache_time'):
            if (now - self._stats_cache_time) < 5:
                return self._stats_cache
        
        index = self._load_index()
        cats = index.get("categories", {})

        by_type = {}
        for mt_name, mt_data in cats.items():
            for year_str, year_data in mt_data.items():
                if isinstance(year_data, dict):
                    for qtype, ids in year_data.items():
                        if qtype in QUESTION_TYPES:
                            by_type[qtype] = by_type.get(qtype, 0) + len(ids)

        by_math_type = {}
        for mt_name, mt_data in cats.items():
            count = 0
            for year_str, year_data in mt_data.items():
                if isinstance(year_data, dict):
                    for qtype, ids in year_data.items():
                        if qtype in QUESTION_TYPES:
                            count += len(ids)
            by_math_type[mt_name] = count

        years = set()
        for mt_data in cats.values():
            for y in mt_data.keys():
                if y.isdigit():
                    years.add(int(y))

        result = {
            "total": index["metadata"]["total_questions"],
            "by_math_type": by_math_type,
            "by_question_type": by_type,
            "years_covered": sorted(list(years)),
            "knowledge_points_covered": len(index.get("knowledge_index", {})),
            "missing_data": index["metadata"].get("missing_data", []),
            "pending_review": index["metadata"].get("pending_review", []),
        }

        # 缓存结果
        self._stats_cache = result
        self._stats_cache_time = now
        return result

    def _clear_stats_cache(self):
        """清除统计缓存"""
        if hasattr(self, '_stats_cache'):
            delattr(self, '_stats_cache')
        if hasattr(self, '_stats_cache_time'):
            delattr(self, '_stats_cache_time')

    # ==================== 质量验证 ====================

    def validate(self, question: dict) -> dict:
        """验证题目数据完整性。返回 {valid, issues, warnings}"""
        issues = []
        warnings = []

        required = ["year", "category", "question_type", "question"]
        for field in required:
            if not question.get(field):
                issues.append(f"缺少必填字段: {field}")

        if question.get("category") not in MATH_TYPES:
            issues.append(f"未知数学类别: {question.get('category')}")

        if question.get("question_type") not in QUESTION_TYPES:
            issues.append(f"未知题型: {question.get('question_type')}")

        if not question.get("standard_answer"):
            warnings.append("缺少标准答案，将标记为待生成")

        if not question.get("solution_steps"):
            warnings.append("缺少解答步骤")

        if not question.get("knowledge_points") and not question.get("tags"):
            warnings.append("缺少知识点标签")

        # LaTeX 完整性检查
        text = question.get("question", "") + question.get("standard_answer", "")
        if text:
            latex_issues = self._check_latex(text)
            if latex_issues:
                warnings.append(f"LaTeX 可能异常: {', '.join(latex_issues)}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    # ==================== 知识点标签 ====================

    def auto_tag(self, question_text: str) -> list[str]:
        """从题目文本自动识别知识点标签"""
        tags = []
        text_lower = question_text.lower()
        for tag in KNOWLEDGE_TAGS:
            # 精确匹配或特征词匹配
            if tag in question_text:
                tags.append(tag)
        return tags

    def get_all_tags(self) -> list[str]:
        """获取数据库中所有使用过的标签"""
        index = self._load_index()
        return sorted(index.get("knowledge_index", {}).keys())

    def get_volumes(self, math_type: str) -> list[str]:
        """获取指定数学类别的卷号列表（用于宇哥八套卷等）"""
        index = self._load_index()
        cat_idx = index.get("categories", {}).get(math_type, {})
        if not cat_idx:
            return []
        _cn = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8}
        return sorted(cat_idx.keys(), key=lambda v: next((_cn.get(ch, 99) for ch in v if ch in _cn), 99))

    # ==================== 内部方法 ====================

    def _next_number(self, year: int, math_type: str, volume: str = "") -> int:
        """获取下一个题号（考虑卷号，避免不同卷号的题目ID碰撞）"""
        index = self._load_index()
        # 如果有卷号，使用卷号作为二级分类；否则使用年份
        if volume:
            cat = index["categories"].get(math_type, {}).get(volume, {})
        else:
            cat = index["categories"].get(math_type, {}).get(str(year), {})
        max_num = 0
        for qtype, ids in cat.items():
            if qtype in QUESTION_TYPES:
                for qid in ids:
                    try:
                        num = int(qid.split("-")[-1])
                        max_num = max(max_num, num)
                    except ValueError:
                        pass
        return max_num + 1

    def _check_duplicate(self, question: dict) -> dict:
        """检查是否与已有题目重复"""
        year = question.get("year")
        math_type = question.get("category")
        text = question.get("question", "")
        if not year or not math_type or not text:
            return {"is_duplicate": False, "existing_id": "", "similarity": 0}

        index = self._load_index()
        cat = index["categories"].get(math_type, {}).get(str(year), {})
        candidates = []
        for qtype, ids in cat.items():
            if qtype in QUESTION_TYPES:
                candidates.extend(ids)

        for qid in candidates:
            existing = self.get(qid)
            if existing:
                sim = SequenceMatcher(None, text, existing.get("question", "")).ratio()
                if sim > 0.85:
                    return {"is_duplicate": True, "existing_id": qid, "similarity": sim}

        return {"is_duplicate": False, "existing_id": "", "similarity": 0}

    def _check_latex(self, text: str) -> list[str]:
        """检查 LaTeX 语法问题"""
        issues = []
        # 不配对的 $$
        if text.count("$$") % 2 != 0:
            issues.append("不配对的 $$")
        # 不配对的 $
        single_dollar = len(re.findall(r"(?<!\$)\$(?!\$)", text))
        if single_dollar % 2 != 0:
            issues.append("不配对的 $")
        # 不配对的括号
        if text.count("{") != text.count("}"):
            issues.append("不配对的花括号")
        if text.count("\\[") != text.count("\\]"):
            issues.append("不配对的 \\[ \\]")
        return issues

    def _match(self, question: dict, filters: dict) -> bool:
        """检查题目是否匹配过滤条件"""
        if filters.get("math_type") and question.get("category") != filters["math_type"]:
            return False
        if filters.get("year") and question.get("year") != filters["year"]:
            return False
        if filters.get("question_type") and question.get("question_type") != filters["question_type"]:
            return False
        if filters.get("difficulty") and question.get("difficulty") != filters["difficulty"]:
            return False
        if filters.get("keyword"):
            kw = filters["keyword"]
            searchable = question.get("question", "") + " " + " ".join(question.get("knowledge_points", [])) + " " + " ".join(question.get("tags", []))
            if kw not in searchable:
                return False
        return True

    def _load_all(self, limit: int = 100000) -> list[dict]:
        """加载所有题目（供搜索遍历）"""
        questions = []
        
        # 加载真题
        if EXAM_DIR.exists():
            for f in sorted(EXAM_DIR.glob("*.json"))[:limit]:
                try:
                    questions.append(self._load_json(f))
                except Exception:
                    pass
        
        # 加载模拟卷
        if SIMUL_DIR.exists():
            for f in sorted(SIMUL_DIR.glob("*.json"))[:limit]:
                try:
                    questions.append(self._load_json(f))
                except Exception:
                    pass
        
        return questions

    def _update_categories(self, index: dict, question: dict):
        cats = index.setdefault("categories", {})
        mt = question["category"]
        group_key = category_group(question)
        qtype = question["question_type"]
        qid = question["question_id"]

        mt_data = cats.setdefault(mt, {})
        group_data = mt_data.setdefault(group_key, {})
        type_list = group_data.setdefault(qtype, [])
        if qid not in type_list:
            type_list.append(qid)

    def _update_knowledge_index(self, index: dict, question: dict):
        ki = index.setdefault("knowledge_index", {})
        qid = question["question_id"]
        all_tags = set(question.get("knowledge_points", []) + question.get("tags", []))
        for tag in all_tags:
            if tag not in ki:
                ki[tag] = []
            if qid not in ki[tag]:
                ki[tag].append(qid)

    def _update_difficulty_index(self, index: dict, question: dict):
        di = index.setdefault("difficulty_index", {})
        diff = question.get("difficulty", "中等")
        if diff not in di:
            di[diff] = []
        di[diff].append(question["question_id"])

    def _remove_from_index(self, index: dict, question: dict):
        qid = question["question_id"]
        # 从分类索引中移除
        cats = index.get("categories", {})
        mt = question.get("category", "")
        group_key = category_group(question)
        qtype = question.get("question_type", "")
        try:
            cats[mt][group_key][qtype].remove(qid)
        except (KeyError, ValueError):
            for group_data in cats.get(mt, {}).values():
                try:
                    group_data.get(qtype, []).remove(qid)
                except (AttributeError, ValueError):
                    pass
        # 从知识索引中移除
        for tag_list in index.get("knowledge_index", {}).values():
            try:
                tag_list.remove(qid)
            except ValueError:
                pass
        # 从难度索引中移除
        for diff_list in index.get("difficulty_index", {}).values():
            try:
                diff_list.remove(qid)
            except ValueError:
                pass

    def _rebuild_knowledge_index(self, index: dict):
        """重建知识点索引（用于update操作后）"""
        index["knowledge_index"] = {}
        for q in self._load_all(limit=10000):
            self._update_knowledge_index(index, q)

    def _rebuild_difficulty_index(self, index: dict):
        index["difficulty_index"] = {}
        for q in self._load_all(limit=10000):
            self._update_difficulty_index(index, q)
