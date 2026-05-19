"""
真题导入器 — 支持 JSON 批量导入 / OCR 文档导入 / 单题手动录入

流程: 原始数据 → 解析 → 自动分类 → 质量检查 → 去重 → 入库 → 报告
"""

import json
import time
from pathlib import Path
from difflib import SequenceMatcher

from config import MATH_TYPES, QUESTION_TYPES, DIFFICULTY_LEVELS, STORAGE_DIR
from .question_db import QuestionDB, make_question_id

IMPORT_LOG_PATH = Path(STORAGE_DIR) / "questions" / "_import_log.json"


class QuestionImporter:
    """题目批量导入器"""

    def __init__(self, db: QuestionDB = None):
        self.db = db or QuestionDB()
        self.log = {"imports": [], "stats": {"success": 0, "skipped_dup": 0, "failed": 0, "warnings": []}}

    # ==================== JSON 批量导入 ====================

    def import_json(self, json_path: str) -> dict:
        """
        从 JSON 文件批量导入题目。
        支持格式: {"questions": [...]}  或  [{...}, {...}]
        """
        self._reset_log()
        data = self._load_json(json_path)

        questions = data if isinstance(data, list) else data.get("questions", [data])
        if not isinstance(questions, list):
            questions = [questions]

        for item in questions:
            self._import_one(item)

        return self._generate_report()

    def import_dict(self, questions: list[dict]) -> dict:
        """从 dict 列表导入（供界面调用）"""
        self._reset_log()
        for item in questions:
            self._import_one(item)
        return self._generate_report()

    # ==================== OCR 文档导入 ====================

    def import_from_ocr(self, ocr_text: str, math_type: str = "数学一",
                        year: int = None) -> dict:
        """
        从 OCR 识别文本中提取题目并导入。
        ocr_text: 整份试卷的 OCR 文本
        会自动尝试分割题目、推断题号、提取题干。
        """
        self._reset_log()

        # 按题号模式分割
        blocks = self._split_by_question_number(ocr_text)

        for i, block in enumerate(blocks):
            question = self._parse_ocr_block(block, math_type, year)
            if question:
                self._import_one(question)

        return self._generate_report()

    def import_from_file(self, file_path: str, math_type: str = "数学一",
                         year: int = None) -> dict:
        """
        从上传文件导入（TEX/MD/TXT/JSON；PDF/图片需 OCR）
        返回导入报告。
        """
        self._reset_log()
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in [".json"]:
            return self.import_json(file_path)

        elif suffix in [".tex"]:
            try:
                from exam_parser import LatexExamParser
                result = LatexExamParser().parse_file(
                    file_path, year=year, math_type=math_type,
                )
                if result.errors:
                    self.log["stats"]["warnings"].extend(result.errors[:10])
                for q in result.questions:
                    self._import_one(q)
                return self._generate_report()
            except Exception as e:
                self.log["stats"]["failed"] += 1
                self.log["stats"]["warnings"].append(f"LaTeX 解析失败: {e}")
                return self._generate_report()

        elif suffix in [".txt", ".md"]:
            try:
                from exam_parser import ExamParserPipeline
                pipeline = ExamParserPipeline(db=self.db)
                result = pipeline.process_file(file_path, math_type=math_type, year=year)
                for q in result.questions:
                    self._import_one(q)
                if result.warnings:
                    self.log["stats"]["warnings"].extend(result.warnings[:10])
                return self._generate_report()
            except Exception:
                text = path.read_text(encoding="utf-8")
                return self.import_from_ocr(text, math_type, year)

        elif suffix in [".pdf", ".png", ".jpg", ".jpeg"]:
            # 尝试 OCR
            try:
                import pytesseract
                from PIL import Image

                if suffix == ".pdf":
                    # PDF 需要额外处理，这里提示用户
                    self.log["stats"]["warnings"].append(
                        "PDF 导入需要先转为图片。请使用截图工具逐页导入。"
                    )
                    return self._generate_report()
                else:
                    img = Image.open(file_path)
                    img = img.convert("L")
                    text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                    return self.import_from_ocr(text, math_type, year)
            except ImportError:
                self.log["stats"]["warnings"].append("OCR 模块未安装(pytesseract)，无法处理图片")
                return self._generate_report()

        self.log["stats"]["warnings"].append(f"不支持的文件格式: {suffix}")
        return self._generate_report()

    # ==================== 批量生成示例数据 ====================

    def seed_examples(self) -> dict:
        """插入示例题目（标记为非真实真题，用于演示系统功能）"""
        from database.seed_data import SEED_QUESTIONS
        return self.import_dict(SEED_QUESTIONS)

    # ==================== 内部方法 ====================

    def _import_one(self, item: dict):
        """导入单道题"""
        # 自动补全缺失字段
        enriched = self._enrich(item)

        # LaTeX 格式校验 + 自动修复
        try:
            from validators import validate_and_repair
            enriched, latex_result = validate_and_repair(enriched)
            if not latex_result.valid:
                for err in latex_result.errors[:5]:
                    self.log.setdefault("latex_errors", []).append(err)
            if latex_result.warnings:
                self.log.setdefault("latex_warnings", []).extend(latex_result.warnings[:5])
        except ImportError:
            pass

        # 质量检查
        qc = self.db.validate(enriched)
        if not qc["valid"]:
            self.log["stats"]["failed"] += 1
            self.log["imports"].append({
                "status": "failed",
                "question": enriched.get("question", "")[:80],
                "issues": qc["issues"],
            })
            return

        # 去重
        dup = self.db._check_duplicate(enriched)
        if dup["is_duplicate"]:
            self.log["stats"]["skipped_dup"] += 1
            self.log["imports"].append({
                "status": "skipped_duplicate",
                "question": enriched.get("question", "")[:80],
                "duplicate_of": dup["existing_id"],
            })
            return

        # 入库
        result = self.db.insert(enriched)
        if result["success"]:
            self.log["stats"]["success"] += 1
            self.log["imports"].append({
                "status": "success",
                "question_id": result["question_id"],
                "question": enriched.get("question", "")[:80],
                "warnings": result.get("warnings", []),
            })
            self.log["stats"]["warnings"].extend(result.get("warnings", []))
        else:
            self.log["stats"]["failed"] += 1
            self.log["imports"].append({
                "status": "failed",
                "question": enriched.get("question", "")[:80],
                "issues": result.get("warnings", []),
            })

    def _enrich(self, item: dict) -> dict:
        """自动补全缺失的字段"""
        q = dict(item)

        # 自动推断数学类别
        if not q.get("category"):
            q["category"] = self._infer_math_type(q.get("question", ""))

        # 自动推断题型
        if not q.get("question_type"):
            q["question_type"] = self._infer_question_type(q.get("question", ""))

        # 自动推断年份
        if not q.get("year"):
            q["year"] = self._infer_year(q.get("question", ""))

        # 自动打标签
        if not q.get("knowledge_points"):
            q["knowledge_points"] = self.db.auto_tag(q.get("question", ""))

        # 补充默认难度
        if not q.get("difficulty"):
            q["difficulty"] = "中等"

        # 补充默认分值和答案
        q.setdefault("score", 10)
        q.setdefault("standard_answer", "")
        q.setdefault("solution_steps", [])
        q.setdefault("common_mistakes", [])
        q.setdefault("tags", [])

        return q

    def _split_by_question_number(self, text: str) -> list[str]:
        """按题号模式（如 '1.' '（1）' '一、'）分割 OCR 文本"""
        import re
        # 匹配各种题号格式
        patterns = [
            r'(?:^|\n)\s*(\d{1,2})[\.\、\)）]\s*',      # "1." "12."
            r'(?:^|\n)\s*[（(](\d{1,2})[）)]\s*',       # "（1）"
        ]
        blocks = [text]  # 如果无法分割，整段作为一个块
        for pat in patterns:
            splits = re.split(pat, text)
            if len(splits) > 1:
                # 提取奇数索引的匹配 + 偶数索引的内容
                result = []
                for i in range(1, len(splits), 2):
                    num = splits[i]
                    content = splits[i + 1] if i + 1 < len(splits) else ""
                    result.append(f"{num}. {content.strip()}")
                if len(result) > 1:
                    blocks = result
                    break
        return blocks

    def _parse_ocr_block(self, block: str, math_type: str,
                         year: int = None) -> dict | None:
        """将 OCR 文本块解析为题目 dict"""
        block = block.strip()
        if len(block) < 10:
            return None

        qtype = self._infer_question_type(block)
        kps = self.db.auto_tag(block)

        return {
            "year": year or self._infer_year(block),
            "category": math_type,
            "question_type": qtype,
            "knowledge_points": kps,
            "difficulty": self._infer_difficulty(block),
            "score": self._infer_score(qtype),
            "question": block[:2000],
            "standard_answer": "",
            "solution_steps": [],
            "common_mistakes": [],
            "tags": kps,
        }

    def _infer_math_type(self, text: str) -> str:
        """从文本推断数学类别"""
        return "数学一"

    def _infer_question_type(self, text: str) -> str:
        """推断题型"""
        if any(w in text[:50] for w in ["选择", "下列选", "正确的一项是", "A.", "B."]):
            return "选择题"
        if any(w in text[:50] for w in ["填空", "______"]):
            return "填空题"
        if any(w in text[:50] for w in ["证明", "求证"]):
            return "证明题"
        return "解答题"

    def _infer_year(self, text: str) -> int:
        """从文本推断年份"""
        import re
        match = re.search(r"(19[8-9]\d|20[0-2]\d)\s*年", text)
        if match:
            return int(match.group(1))
        # 尝试从上下文推断
        match = re.search(r"^\s*(\d{4})", text)
        if match and 1987 <= int(match.group(1)) <= 2026:
            return int(match.group(1))
        return 2024  # 无法推断时用当前年份

    def _infer_difficulty(self, text: str) -> str:
        """推断难度"""
        # 基于题型和关键词的简单推断
        if "证明" in text[:50]:
            return "较难"
        if any(w in text for w in ["求极限", "计算不定积分", "求导数"]):
            return "基础"
        if any(w in text for w in ["二重积分", "微分方程", "级数"]):
            return "中等"
        return "中等"

    def _infer_score(self, qtype: str) -> int:
        """基于题型推断分值"""
        return {"选择题": 4, "填空题": 4, "解答题": 10, "证明题": 12}.get(qtype, 10)

    def _reset_log(self):
        self.log = {
            "imports": [],
            "stats": {"success": 0, "skipped_dup": 0, "failed": 0, "warnings": []},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def _generate_report(self) -> dict:
        """生成导入报告"""
        stats = self.log["stats"]
        total = stats["success"] + stats["skipped_dup"] + stats["failed"]

        # 按类别统计
        by_category = {}
        for item in self.log["imports"]:
            if item["status"] == "success":
                qid = item.get("question_id", "")
                mt = qid.split("-")[1] if "-" in qid else "未知"
                mt_full = {"数一": "数学一"}.get(mt, mt)
                by_category[mt_full] = by_category.get(mt_full, 0) + 1

        # 检测缺失年份
        existing_years = set()
        for item in self.log["imports"]:
            if item["status"] == "success":
                qid = item.get("question_id", "")
                parts = qid.split("-")
                if len(parts) >= 1:
                    try:
                        existing_years.add(int(parts[0]))
                    except ValueError:
                        pass

        # 记录导入日志
        report = {
            "total_processed": total,
            "success": stats["success"],
            "skipped_duplicates": stats["skipped_dup"],
            "failed": stats["failed"],
            "by_category": by_category,
            "warnings": stats["warnings"][:20],
            "timestamp": self.log["timestamp"],
        }

        self._save_json(IMPORT_LOG_PATH, {
            "last_import": report,
            "history": [],
        })

        return report

    def _save_json(self, path, data):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # 保留历史记录
        if path == IMPORT_LOG_PATH and path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            old["history"].insert(0, data["last_import"])
            old["history"] = old["history"][:20]  # 保留最近20次
            old["last_import"] = data["last_import"]
            data = old
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _load_json(path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
