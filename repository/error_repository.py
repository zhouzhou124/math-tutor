"""Repository Layer - 错题记录数据访问"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .base import JSONRepository, SQLiteRepository
from .models import ErrorRecord, ErrorStats


class ErrorRecordRepository(JSONRepository):
    """错题记录数据访问层（JSON 存储详细记录）"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir, "errors.json")
    
    def add_record(self, user_id: str, record_data: Dict) -> str:
        """添加错题记录，返回 record_id"""
        all_errors = self._load_json(self.file_path)
        
        if user_id not in all_errors:
            all_errors[user_id] = {"records": [], "stats": {}}
        
        # 生成记录ID
        record_id = f"err_{int(time.time())}_{int(time.time() * 1000) % 1000}"
        
        # 构建完整记录
        full_record = {
            "record_id": record_id,
            "user_id": user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            **record_data,
        }
        
        # 检查重复
        same_kp = [r for r in all_errors[user_id]["records"] 
                   if r.get("knowledge_point") == record_data.get("knowledge_point")]
        full_record["is_repeat"] = len(same_kp) > 0
        full_record["repeat_count"] = len(same_kp) + 1
        
        all_errors[user_id]["records"].append(full_record)
        self._update_stats(all_errors[user_id])
        self._save_json(self.file_path, all_errors)
        
        return record_id
    
    def _update_stats(self, user_data: Dict):
        """更新错题统计"""
        records = user_data["records"]
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
        
        user_data["stats"] = stats
    
    def get_records(self, user_id: str, **filters) -> List[Dict]:
        """获取错题记录，支持筛选"""
        all_errors = self._load_json(self.file_path)
        user_data = all_errors.get(user_id, {"records": []})
        records = user_data["records"]

        # 应用筛选条件
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
        """一次读取同时返回记录和统计，避免重复 JSON 解析"""
        all_errors = self._load_json(self.file_path)
        user_data = all_errors.get(user_id, {"records": [], "stats": {}})
        records = user_data.get("records", [])

        # 应用筛选条件
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

        # 从已加载的 user_data 构建 stats，无需再次读文件
        raw_stats = user_data.get("stats", {})
        stats = ErrorStats(
            user_id=user_id,
            total_errors=raw_stats.get("total_errors", 0),
            by_chapter=raw_stats.get("by_chapter", {}),
            by_type=raw_stats.get("by_type", {}),
            by_difficulty=raw_stats.get("by_difficulty", {}),
            repeat_rate=raw_stats.get("repeat_rate", 0.0),
        )
        return records, stats

    def delete_record(self, user_id: str, record_id: str) -> bool:
        """删除指定错题记录，返回是否成功"""
        all_errors = self._load_json(self.file_path)
        user_data = all_errors.get(user_id)
        if not user_data:
            return False

        records = user_data.get("records", [])
        new_records = [r for r in records if r.get("record_id") != record_id]

        if len(new_records) == len(records):
            return False  # 未找到匹配记录

        # Incremental stats update: just decrement counters
        deleted = next((r for r in records if r.get("record_id") == record_id), None)
        if deleted:
            stats = user_data.get("stats", {})
            stats["total_errors"] = max(0, stats.get("total_errors", 0) - 1)
            chapter = deleted.get("knowledge_point", "未知").split(" - ")[0]
            if chapter in stats.get("by_chapter", {}):
                stats["by_chapter"][chapter] = max(0, stats["by_chapter"][chapter] - 1)
                if stats["by_chapter"][chapter] == 0:
                    del stats["by_chapter"][chapter]
            etype = deleted.get("error_type", "未分类")
            if etype in stats.get("by_type", {}):
                stats["by_type"][etype] = max(0, stats["by_type"][etype] - 1)
                if stats["by_type"][etype] == 0:
                    del stats["by_type"][etype]
            diff = deleted.get("difficulty", "中等")
            if diff in stats.get("by_difficulty", {}):
                stats["by_difficulty"][diff] = max(0, stats["by_difficulty"][diff] - 1)
                if stats["by_difficulty"][diff] == 0:
                    del stats["by_difficulty"][diff]
            total = stats.get("total_errors", 0)
            repeats = sum(1 for r in new_records if r.get("is_repeat"))
            stats["repeat_rate"] = repeats / total if total else 0
            user_data["stats"] = stats

        user_data["records"] = new_records
        self._save_json(self.file_path, all_errors)
        return True

    def get_stats(self, user_id: str) -> ErrorStats:
        """获取错题统计"""
        all_errors = self._load_json(self.file_path)
        user_data = all_errors.get(user_id, {})
        stats = user_data.get("stats", {})
        
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
        
        # 创建索引
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
