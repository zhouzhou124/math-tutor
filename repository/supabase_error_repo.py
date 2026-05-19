"""Supabase-backed error record repository. Replaces JSON file storage."""
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .supabase_client import SupabaseClient
from .models import ErrorStats


class SupabaseErrorRepository:
    """错题记录 Supabase 存储（替代 JSON 文件）"""

    def __init__(self, client: SupabaseClient):
        self.client = client

    # ── Schema auto-creation (run once) ──

    def ensure_tables(self):
        """Create tables if they don't exist. Run once on first use.
        Requires supabase SQL editor access, OR we create via REST.
        Since REST can't CREATE TABLE, this is a manual step.
        See supabase_schema.sql for the SQL to run in Supabase SQL Editor.
        """
        pass  # Tables must be created via Supabase SQL Editor (one-time)

    # ── Record CRUD ──

    def add_record(self, user_id: str, record_data: Dict) -> str:
        record_id = f"err_{int(time.time())}_{int(time.time() * 1000) % 1000}"
        row = {
            "record_id": record_id,
            "user_id": user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "question": record_data.get("question", "")[:2000],
            "student_answer": record_data.get("student_answer", "")[:2000],
            "standard_answer": record_data.get("standard_answer", "")[:5000],
            "question_type": record_data.get("question_type", ""),
            "knowledge_point": record_data.get("knowledge_point", ""),
            "difficulty": record_data.get("difficulty", "中等"),
            "score": str(record_data.get("score", 0)),
            "max_score": str(record_data.get("max_score", 10)),
            "error_type": record_data.get("error_type", ""),
            "root_cause": record_data.get("root_cause", "")[:500],
            "engine": record_data.get("engine", ""),
            "comment": record_data.get("comment", "")[:1000],
            "extra_json": self._pack_extra(record_data),
        }
        self.client.insert("error_records", row)
        return record_id

    def _pack_extra(self, data: Dict) -> str:
        import json
        extra = {}
        for k in ("solution_steps", "step_analysis", "weak_points",
                   "recommendations", "common_mistakes", "knowledge_points",
                   "question_id", "confidence", "method_matched"):
            if k in data and data[k]:
                extra[k] = data[k]
        # Store is_repeat info
        extra["is_repeat"] = data.get("is_repeat", False)
        extra["repeat_count"] = data.get("repeat_count", 0)
        return json.dumps(extra, ensure_ascii=False) if extra else "{}"

    def _unpack_extra(self, row: Dict) -> Dict:
        import json
        try:
            extra = json.loads(row.get("extra_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            extra = {}
        extra["record_id"] = row.get("record_id", "")
        extra["date"] = row.get("date", "")
        extra["time"] = row.get("time", "")
        extra["question"] = row.get("question", "")
        extra["student_answer"] = row.get("student_answer", "")
        extra["standard_answer"] = row.get("standard_answer", "")
        extra["question_type"] = row.get("question_type", "")
        extra["knowledge_point"] = row.get("knowledge_point", "")
        extra["difficulty"] = row.get("difficulty", "中等")
        try: extra["score"] = float(row.get("score", 0))
        except: extra["score"] = 0
        try: extra["max_score"] = float(row.get("max_score", 10))
        except: extra["max_score"] = 10
        extra["error_type"] = row.get("error_type", "")
        extra["root_cause"] = row.get("root_cause", "")
        extra["engine"] = row.get("engine", "")
        extra["comment"] = row.get("comment", "")
        extra["is_repeat"] = extra.get("is_repeat", False)
        extra["repeat_count"] = extra.get("repeat_count", 0)
        return extra

    def get_records(self, user_id: str, **filters) -> List[Dict]:
        f = {"user_id": user_id}
        if filters.get("knowledge_point"):
            f["knowledge_point"] = f"like.%{filters['knowledge_point']}%"
        if filters.get("error_type"):
            f["error_type"] = filters["error_type"]
        rows = self.client.select(
            "error_records", "*", filters=f,
            order="date.desc,time.desc",
            limit=filters.get("limit", 100),
        )
        return [self._unpack_extra(r) for r in (rows or [])]

    def get_records_with_stats(self, user_id: str, **filters) -> Tuple[List[Dict], ErrorStats]:
        records = self.get_records(user_id, **filters)
        # Compute stats from records
        stats = ErrorStats(
            user_id=user_id,
            total_errors=len(records),
            by_chapter={},
            by_type={},
            by_difficulty={},
            repeat_rate=0.0,
        )
        for r in records:
            ch = (r.get("knowledge_point") or "未知").split(" - ")[0]
            stats.by_chapter[ch] = stats.by_chapter.get(ch, 0) + 1
            et = r.get("error_type", "未分类")
            stats.by_type[et] = stats.by_type.get(et, 0) + 1
            df = r.get("difficulty", "中等")
            stats.by_difficulty[df] = stats.by_difficulty.get(df, 0) + 1
        reps = sum(1 for r in records if r.get("is_repeat"))
        stats.repeat_rate = reps / len(records) if records else 0
        return records, stats

    def delete_record(self, user_id: str, record_id: str) -> bool:
        rows = self.client.delete("error_records", {
            "user_id": user_id, "record_id": record_id,
        })
        return len(rows) > 0
