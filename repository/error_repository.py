"""Repository Layer - 错题记录数据访问

优化策略:
  - 每人独立 JSON 文件 (errors/{user_id}.json)，不再全量加载
  - 记录只存 question_id，不存 question/answer/solution_steps 全文
  - 增量更新统计，不重算全部记录
  - 每人最多 200 条，超出删最旧
  - 状态化生命周期: ACTIVE → MASTERED / ARCHIVED / HIDDEN → DELETED
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .base import JSONRepository, SQLiteRepository
from .models import ErrorRecord, ErrorStats

MAX_RECORDS_PER_USER = 200

# Fields that can be looked up from QuestionDB — don't store in error record
_LOOKUP_FIELDS = {"question", "standard_answer", "solution_steps"}

# 错题生命周期状态机: ACTIVE → MASTERED | ARCHIVED | HIDDEN → DELETED
RECORD_STATUSES = {
    "ACTIVE": "当前错题",
    "MASTERED": "已掌握",
    "ARCHIVED": "已归档",
    "HIDDEN": "已隐藏",
    "DELETED": "已删除",
}


class ErrorRecordRepository(JSONRepository):
    """错题记录数据访问层 — 每人独立 JSON 文件"""

    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir, "errors.json")  # kept for migration
        self._errors_dir = data_dir / "errors"
        self._errors_dir.mkdir(parents=True, exist_ok=True)

    def _user_file(self, user_id: str) -> Path:
        return self._errors_dir / f"{user_id}.json"

    def _load_user(self, user_id: str) -> dict:
        """Load a single user's error data. Returns {'records': [], 'stats': {}}."""
        fp = self._user_file(user_id)
        if not fp.exists():
            return {"records": [], "stats": {}}
        raw = self._load_json(fp)
        # Handle old format wrapped in {"schema_version": ..., "data": ...}
        if isinstance(raw, dict) and "data" in raw and "schema_version" in raw:
            return raw["data"]
        # Handle legacy format directly on disk
        if isinstance(raw, dict) and "records" in raw:
            return raw
        return {"records": [], "stats": {}}

    def _save_user(self, user_id: str, data: dict):
        self._save_json(self._user_file(user_id), data)

    def _strip_redundant(self, record: dict) -> dict:
        """Remove fields that can be looked up from QuestionDB."""
        return {k: v for k, v in record.items() if k not in _LOOKUP_FIELDS}

    def _increment_stats(self, stats: dict, record: dict):
        """Incrementally update stats for one new record."""
        stats["total_errors"] = stats.get("total_errors", 0) + 1

        chapter = record.get("knowledge_point", "未知").split(" - ")[0]
        by_chapter = stats.setdefault("by_chapter", {})
        by_chapter[chapter] = by_chapter.get(chapter, 0) + 1

        etype = record.get("error_type", "未分类")
        by_type = stats.setdefault("by_type", {})
        by_type[etype] = by_type.get(etype, 0) + 1

        diff = record.get("difficulty", "中等")
        by_difficulty = stats.setdefault("by_difficulty", {})
        by_difficulty[diff] = by_difficulty.get(diff, 0) + 1

    def _decrement_stats(self, stats: dict, record: dict):
        """Decrement stats when removing a record."""
        stats["total_errors"] = max(0, stats.get("total_errors", 0) - 1)

        chapter = record.get("knowledge_point", "未知").split(" - ")[0]
        by_chapter = stats.get("by_chapter", {})
        if chapter in by_chapter:
            by_chapter[chapter] = max(0, by_chapter[chapter] - 1)
            if by_chapter[chapter] == 0:
                del by_chapter[chapter]

        etype = record.get("error_type", "未分类")
        by_type = stats.get("by_type", {})
        if etype in by_type:
            by_type[etype] = max(0, by_type[etype] - 1)
            if by_type[etype] == 0:
                del by_type[etype]

        diff = record.get("difficulty", "中等")
        by_difficulty = stats.get("by_difficulty", {})
        if diff in by_difficulty:
            by_difficulty[diff] = max(0, by_difficulty[diff] - 1)
            if by_difficulty[diff] == 0:
                del by_difficulty[diff]

        total = stats.get("total_errors", 0)
        # Note: records list not available here; repeat_rate is recalculated
        # by the caller (add_record / delete_record) with the actual list

    def add_record(self, user_id: str, record_data: Dict) -> str:
        """Add error record. Strips redundant fields, caps at MAX_RECORDS_PER_USER."""
        data = self._load_user(user_id)
        records = data.get("records", [])
        stats = data.get("stats", {})

        record_id = f"err_{int(time.time())}_{int(time.time() * 1000) % 1000}"

        full_record = {
            "record_id": record_id,
            "user_id": user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "status": "ACTIVE",  # 生命周期初始状态
            **self._strip_redundant(record_data),
        }

        # Check repeat
        same_kp = [r for r in records
                   if r.get("knowledge_point") == record_data.get("knowledge_point")]
        full_record["is_repeat"] = len(same_kp) > 0
        full_record["repeat_count"] = len(same_kp) + 1

        records.append(full_record)

        # Cap at MAX_RECORDS_PER_USER — remove oldest
        while len(records) > MAX_RECORDS_PER_USER:
            removed = records.pop(0)
            self._decrement_stats(stats, removed)

        # Incremental stats
        self._increment_stats(stats, full_record)
        # Recalc repeat_rate
        repeats = sum(1 for r in records if r.get("is_repeat"))
        stats["repeat_rate"] = repeats / len(records) if records else 0.0

        data["records"] = records
        data["stats"] = stats
        self._save_user(user_id, data)

        return record_id

    def get_records(self, user_id: str, **filters) -> List[Dict]:
        """Get error records with optional filters. Default: ACTIVE only."""
        data = self._load_user(user_id)
        records = data.get("records", [])

        # Filter by status: default ACTIVE, pass status="ALL" for all
        status_filter = filters.pop("status", "ACTIVE")
        if status_filter != "ALL":
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            records = [r for r in records if r.get("status", "ACTIVE") in status_filter]

        if "subject" in filters and filters["subject"]:
            records = [r for r in records
                       if filters["subject"] in r.get("knowledge_point", "")]
        if "knowledge_point" in filters and filters["knowledge_point"]:
            records = [r for r in records
                       if filters["knowledge_point"] in r.get("knowledge_point", "")]
        if "error_type" in filters and filters["error_type"]:
            records = [r for r in records
                       if filters["error_type"] in r.get("error_type", "")]
        if "limit" in filters:
            records = records[:filters["limit"]]

        return sorted(records, key=lambda r: r.get("date", ""), reverse=True)

    def get_records_with_stats(self, user_id: str, **filters) -> tuple:
        """Get records + stats in one read. Default: ACTIVE only."""
        data = self._load_user(user_id)
        records = data.get("records", [])

        # Filter by status: default ACTIVE
        status_filter = filters.pop("status", "ACTIVE")
        if status_filter != "ALL":
            if isinstance(status_filter, str):
                status_filter = [status_filter]
            records = [r for r in records if r.get("status", "ACTIVE") in status_filter]

        if "subject" in filters and filters.get("subject"):
            records = [r for r in records
                       if filters["subject"] in r.get("knowledge_point", "")]
        if "knowledge_point" in filters and filters.get("knowledge_point"):
            records = [r for r in records
                       if filters["knowledge_point"] in r.get("knowledge_point", "")]
        if "error_type" in filters and filters.get("error_type"):
            records = [r for r in records
                       if filters["error_type"] in r.get("error_type", "")]

        records = sorted(records, key=lambda r: r.get("date", ""), reverse=True)
        if "limit" in filters:
            records = records[:filters["limit"]]

        raw_stats = data.get("stats", {})
        stats = ErrorStats(
            user_id=user_id,
            total_errors=raw_stats.get("total_errors", 0),
            by_chapter=raw_stats.get("by_chapter", {}),
            by_type=raw_stats.get("by_type", {}),
            by_difficulty=raw_stats.get("by_difficulty", {}),
            repeat_rate=raw_stats.get("repeat_rate", 0.0),
        )
        return records, stats

    def update_status(self, user_id: str, record_id: str, new_status: str) -> bool:
        """Transition a record to a new lifecycle status."""
        if new_status not in RECORD_STATUSES:
            return False
        data = self._load_user(user_id)
        records = data.get("records", [])
        for r in records:
            if r.get("record_id") == record_id:
                r["status"] = new_status
                self._save_user(user_id, data)
                return True
        return False

    def delete_record(self, user_id: str, record_id: str) -> bool:
        """Soft-delete: mark as ARCHIVED instead of removing."""
        return self.update_status(user_id, record_id, "ARCHIVED")

    def hard_delete_record(self, user_id: str, record_id: str) -> bool:
        """Permanently remove a record from disk. Use sparingly."""
        data = self._load_user(user_id)
        records = data.get("records", [])
        stats = data.get("stats", {})

        deleted = None
        new_records = []
        for r in records:
            if r.get("record_id") == record_id:
                deleted = r
            else:
                new_records.append(r)

        if deleted is None:
            return False

        self._decrement_stats(stats, deleted)
        repeats = sum(1 for r in new_records if r.get("is_repeat"))
        total = stats.get("total_errors", 0)
        stats["repeat_rate"] = repeats / total if total else 0.0

        data["records"] = new_records
        data["stats"] = stats
        self._save_user(user_id, data)
        return True

    def get_stats(self, user_id: str) -> ErrorStats:
        """Get error stats for all records (full history, for analytics)."""
        data = self._load_user(user_id)
        stats = data.get("stats", {})
        return ErrorStats(
            user_id=user_id,
            total_errors=stats.get("total_errors", 0),
            by_chapter=stats.get("by_chapter", {}),
            by_type=stats.get("by_type", {}),
            by_difficulty=stats.get("by_difficulty", {}),
            repeat_rate=stats.get("repeat_rate", 0.0),
        )


class ErrorIndexRepository(SQLiteRepository):
    """错题索引（SQLite 存储快速查询索引）"""

    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir)
        self.initialize()

    def initialize(self):
        """初始化索引表"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_index (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                question_type TEXT,
                knowledge_point TEXT,
                error_type TEXT,
                difficulty TEXT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                is_repeat INTEGER DEFAULT 0,
                schema_version TEXT DEFAULT '0.2',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ei_user ON error_index(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ei_date ON error_index(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ei_kp ON error_index(knowledge_point)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ei_type ON error_index(error_type)")

        conn.commit()
        conn.close()

    def add_index(self, record: ErrorRecord):
        """添加索引记录"""
        self._execute("""
            INSERT OR REPLACE INTO error_index (
                record_id, user_id, question_id, question_type,
                knowledge_point, error_type, difficulty, date, time, is_repeat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.record_id,
            record.user_id,
            record.question_id,
            record.question_type,
            record.knowledge_point,
            record.error_type,
            record.difficulty,
            record.date,
            record.time,
            1 if record.is_repeat else 0,
        ))

    def delete_index(self, record_id: str):
        """删除索引记录"""
        self._execute("DELETE FROM error_index WHERE record_id = ?", (record_id,))

    def search_by_knowledge_point(self, user_id: str, knowledge_point: str, limit: int = 20) -> List[Dict]:
        """按知识点搜索错题"""
        cursor = self._query("""
            SELECT record_id, question_id, question_type, error_type, date
            FROM error_index
            WHERE user_id = ? AND knowledge_point LIKE ?
            ORDER BY date DESC
            LIMIT ?
        """, (user_id, f"%{knowledge_point}%", limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "record_id": row[0],
                "question_id": row[1],
                "question_type": row[2],
                "error_type": row[3],
                "date": row[4],
            })
        return results

    def get_error_count_by_type(self, user_id: str) -> Dict[str, int]:
        """按错误类型统计数量"""
        cursor = self._query("""
            SELECT error_type, COUNT(*) as count
            FROM error_index
            WHERE user_id = ?
            GROUP BY error_type
        """, (user_id,))

        results = {}
        for row in cursor.fetchall():
            results[row[0]] = row[1]
        return results
