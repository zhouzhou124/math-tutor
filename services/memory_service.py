"""Services Layer - 记忆服务（Supabase + 本地JSON双栈）"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from repository import (
    ProfileRepository,
    ProfileStatsRepository,
    ErrorRecordRepository,
    ErrorIndexRepository,
)
from repository.models import UserProfile, ErrorRecord, ErrorStats


class MemoryService:
    """记忆服务 - 管理学习画像和错题本。

    优先 Supabase（云端持久），不可用时回退本地 JSON。
    """

    def __init__(self, db_path: Path, data_dir: Path):
        self.db_path = db_path
        self.data_dir = data_dir
        self._supabase = None
        self._supabase_error_repo = None
        self._local_initialized = False
        self._profile_repo = None
        self._stats_repo = None
        self._error_repo = None
        self._error_index_repo = None

    # ── Supabase 初始化 ──

    @classmethod
    def with_supabase(cls, db_path: Path, data_dir: Path,
                      supabase_url: str, supabase_key: str):
        """创建 Supabase 优先的 MemoryService，本地 JSON 为 fallback。"""
        svc = cls(db_path, data_dir)
        try:
            from repository.supabase_client import SupabaseClient
            from repository.supabase_error_repo import SupabaseErrorRepository
            client = SupabaseClient(supabase_url, supabase_key)
            svc._supabase = client
            svc._supabase_error_repo = SupabaseErrorRepository(client)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Supabase init failed, using local JSON: %s", e)
        return svc

    def _ensure_local(self):
        if self._local_initialized:
            return
        self._profile_repo = ProfileRepository(self.db_path, self.data_dir)
        self._stats_repo = ProfileStatsRepository(self.db_path, self.data_dir)
        self._error_repo = ErrorRecordRepository(self.db_path, self.data_dir)
        self._error_index_repo = ErrorIndexRepository(self.db_path, self.data_dir)
        self._local_initialized = True

    # ── 错题记录 ──

    def add_error_record(self, user_id: str, record_data: Dict) -> str:
        if self._supabase_error_repo:
            try:
                return self._supabase_error_repo.add_record(user_id, record_data)
            except Exception:
                pass  # fall through to local
        self._ensure_local()
        record_id = self._error_repo.add_record(user_id, record_data)
        self._update_learning_stats(user_id, self._error_repo.get_stats(user_id))
        self._update_profile(user_id)
        return record_id

    def get_errors(self, user_id: str, **filters) -> List[Dict]:
        if self._supabase_error_repo:
            try:
                return self._supabase_error_repo.get_records(user_id, **filters)
            except Exception:
                pass
        self._ensure_local()
        return self._error_repo.get_records(user_id, **filters)

    def get_error_stats(self, user_id: str) -> ErrorStats:
        if self._supabase_error_repo:
            try:
                _, stats = self._supabase_error_repo.get_records_with_stats(user_id)
                return stats
            except Exception:
                pass
        self._ensure_local()
        return self._error_repo.get_stats(user_id)

    def get_errors_with_stats(self, user_id: str, **filters) -> tuple:
        if self._supabase_error_repo:
            try:
                return self._supabase_error_repo.get_records_with_stats(user_id, **filters)
            except Exception:
                pass
        self._ensure_local()
        records = self._error_repo.get_records(user_id, **filters)
        stats = self._error_repo.get_stats(user_id)
        return records, stats

    def delete_error_record(self, user_id: str, record_id: str) -> bool:
        """Soft-delete: archive the record (status=ARCHIVED)."""
        if self._supabase_error_repo:
            try:
                if self._supabase_error_repo.delete_record(user_id, record_id):
                    return True
            except Exception:
                pass
        self._ensure_local()
        return self._error_repo.delete_record(user_id, record_id)

    def update_error_status(self, user_id: str, record_id: str, status: str) -> bool:
        """Transition a record through the lifecycle: ACTIVE → MASTERED/ARCHIVED/HIDDEN."""
        self._ensure_local()
        return self._error_repo.update_status(user_id, record_id, status)

    def hard_delete_error_record(self, user_id: str, record_id: str) -> bool:
        """Permanently delete a record. Use only with confirmation."""
        self._ensure_local()
        success = self._error_repo.hard_delete_record(user_id, record_id)
        if success:
            try:
                self._error_index_repo.delete_index(record_id)
            except Exception:
                pass
            try:
                error_stats = self._error_repo.get_stats(user_id)
                self._update_learning_stats(user_id, error_stats)
                self._update_profile(user_id)
            except Exception:
                pass
        return success

    # ── 学习统计 ──

    def _update_learning_stats(self, user_id: str, error_stats: ErrorStats):
        self._ensure_local()
        stats = self._stats_repo.get_stats(user_id)
        stats["total_errors"] = error_stats.total_errors
        total_errors = error_stats.total_errors
        stats["overall_accuracy"] = 1.0 - (total_errors / (total_errors + 20))
        if total_errors < 15: stats["current_level"] = "基础薄弱"
        elif total_errors < 50: stats["current_level"] = "强化阶段"
        else: stats["current_level"] = "冲刺阶段"
        self._stats_repo.update_stats(user_id, stats)

    def _update_profile(self, user_id: str):
        """从 stats 增量更新画像，不再全量扫描 records。"""
        self._ensure_local()
        error_stats = self._error_repo.get_stats(user_id)
        by_chapter = error_stats.by_chapter
        if not by_chapter:
            return
        total = error_stats.total_errors
        chapter_acc = {kp: max(0.1, 1.0 - count / (count + 5))
                       for kp, count in by_chapter.items()}
        weak = sorted(chapter_acc.items(), key=lambda x: x[1])[:5]
        weak_points = [w[0] for w in weak]
        profile = self._profile_repo.get_profile(user_id)
        profile.total_questions = total
        profile.chapter_accuracy = chapter_acc
        profile.weak_points = weak_points
        profile.recommendations = [f"重点复习 {w} 相关题型" for w in weak_points]
        self._profile_repo.save_profile(profile)

    def get_profile(self, user_id: str) -> UserProfile:
        self._ensure_local()
        return self._profile_repo.get_profile(user_id)

    def get_recommendations(self, user_id: str) -> List[str]:
        return self.get_profile(user_id).recommendations

    def clear_all_data(self, user_id: str):
        if self._supabase_error_repo:
            try:
                records, _ = self._supabase_error_repo.get_records_with_stats(user_id)
                for r in records:
                    self._supabase_error_repo.delete_record(user_id, r.get("record_id", ""))
            except Exception:
                pass
        self._ensure_local()
        all_errors = self._error_repo._load_json(self._error_repo.file_path)
        if user_id in all_errors:
            del all_errors[user_id]
            self._error_repo._save_json(self._error_repo.file_path, all_errors)
        try:
            self._error_index_repo._execute("DELETE FROM error_index WHERE user_id = ?", (user_id,))
        except Exception: pass
        self._stats_repo.update_stats(user_id, {
            "total_questions": 0, "total_errors": 0, "overall_accuracy": 0.0,
            "current_level": "强化阶段", "streak_days": 0, "last_study_date": "",
        })
