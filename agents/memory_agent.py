"""Memory Agent — 错题本存储 + 学习画像 + 复习建议"""

import json
import os
import time
from pathlib import Path
from config import STORAGE_DIR, ERROR_NOTEBOOK_PATH, STUDENT_PROFILE_PATH, STAGES


class MemoryAgent:
    """管理错题本和学习画像的持久化存储"""

    def __init__(self):
        Path(STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        self._init_files()

    def _init_files(self):
        if not os.path.exists(ERROR_NOTEBOOK_PATH):
            self._save_json(ERROR_NOTEBOOK_PATH, {"records": [], "stats": {}})
        if not os.path.exists(STUDENT_PROFILE_PATH):
            self._save_json(STUDENT_PROFILE_PATH, {
                "level": "强化阶段",
                "total_questions": 0,
                "overall_accuracy": 0.0,
                "chapter_accuracy": {},
                "weak_points": [],
                "recommendations": [],
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })

    def _load_json(self, path: str) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_json(self, path: str, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ────────── 错题本操作 ──────────

    def add_error(self, error_record: dict) -> str:
        """添加一条错题记录。返回 record_id"""
        notebook = self._load_json(ERROR_NOTEBOOK_PATH)

        record_id = f"err_{int(time.time())}_{len(notebook['records']) + 1}"
        record = {
            "id": record_id,
            "date": time.strftime("%Y-%m-%d"),
            "time": time.strftime("%H:%M"),
            **error_record,
        }

        # 检查是否重复出错（同一知识点近30天内有记录）
        same_kp = [
            r for r in notebook["records"]
            if r.get("knowledge_point") == error_record.get("knowledge_point")
        ]
        record["is_repeat"] = len(same_kp) > 0
        record["repeat_count"] = len(same_kp) + 1

        notebook["records"].append(record)
        self._update_stats(notebook)
        self._save_json(ERROR_NOTEBOOK_PATH, notebook)
        self._update_profile()
        return record_id

    def get_errors(self, subject: str = None, knowledge_point: str = None,
                   error_type: str = None, limit: int = 50) -> list:
        """查询错题，支持筛选"""
        notebook = self._load_json(ERROR_NOTEBOOK_PATH)
        records = notebook["records"]

        if subject:
            records = [r for r in records if subject in r.get("knowledge_point", "")]
        if knowledge_point:
            records = [r for r in records if knowledge_point in r.get("knowledge_point", "")]
        if error_type:
            records = [r for r in records if error_type in r.get("error_type", "")]

        return sorted(records, key=lambda r: r.get("date", ""), reverse=True)[:limit]

    def get_error_stats(self) -> dict:
        """错题统计"""
        notebook = self._load_json(ERROR_NOTEBOOK_PATH)
        return notebook.get("stats", {})

    def _update_stats(self, notebook: dict):
        """更新错题统计"""
        records = notebook["records"]
        stats = {
            "total_errors": len(records),
            "by_chapter": {},
            "by_type": {},
            "by_difficulty": {},
            "repeat_rate": 0.0,
        }

        for r in records:
            chapter = r.get("knowledge_point", "未知").split(" - ")[0]
            stats["by_chapter"][chapter] = stats["by_chapter"].get(chapter, 0) + 1

            etype = r.get("error_type", "未分类")
            stats["by_type"][etype] = stats["by_type"].get(etype, 0) + 1

            diff = r.get("difficulty", "中等")
            stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1

        repeats = sum(1 for r in records if r.get("is_repeat"))
        stats["repeat_rate"] = repeats / len(records) if records else 0

        notebook["stats"] = stats

    # ────────── 学习画像操作 ──────────

    def _update_profile(self):
        """更新学习画像"""
        notebook = self._load_json(ERROR_NOTEBOOK_PATH)
        profile = self._load_json(STUDENT_PROFILE_PATH)
        records = notebook["records"]

        if not records:
            return

        # 计算各章节正确率（基于错题中知识点的出现频率）
        chapter_errors = {}
        for r in records:
            kp = r.get("knowledge_point", "未知")
            chapter_errors[kp] = chapter_errors.get(kp, 0) + 1

        # 正确率 = 1 - 该知识点错题占比（近似）
        max_errors = max(chapter_errors.values()) if chapter_errors else 1
        chapter_acc = {}
        for kp, count in chapter_errors.items():
            chapter_acc[kp] = max(0.1, 1.0 - count / (count + 5))  # 平滑估计

        # 薄弱点：正确率最低的 5 个
        weak = sorted(chapter_acc.items(), key=lambda x: x[1])[:5]
        weak_points = [w[0] for w in weak]

        # 阶段判断
        total = len(records)
        if total < 15:
            level = "基础薄弱"
        elif total < 50:
            level = "强化阶段"
        else:
            level = "冲刺阶段"

        profile.update({
            "total_questions": total,
            "chapter_accuracy": chapter_acc,
            "weak_points": weak_points,
            "level": level,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        self._save_json(STUDENT_PROFILE_PATH, profile)

    def get_profile(self) -> dict:
        """获取当前学习画像"""
        return self._load_json(STUDENT_PROFILE_PATH)

    def get_recommendations(self) -> list[str]:
        """生成复习建议"""
        profile = self._load_json(STUDENT_PROFILE_PATH)
        weak = profile.get("weak_points", [])
        recs = []
        for i, w in enumerate(weak, 1):
            recs.append(f"重点复习 {w} 相关题型，当前掌握程度较弱")
        return recs[:5]

    def clear_all(self):
        """重置所有数据"""
        self._save_json(ERROR_NOTEBOOK_PATH, {"records": [], "stats": {}})
        self._save_json(STUDENT_PROFILE_PATH, {
            "level": "强化阶段",
            "total_questions": 0,
            "overall_accuracy": 0.0,
            "chapter_accuracy": {},
            "weak_points": [],
            "recommendations": [],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
