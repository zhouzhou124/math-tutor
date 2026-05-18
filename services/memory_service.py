"""Services Layer - 记忆服务"""

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
    """记忆服务 - 管理学习画像和错题本"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        self.profile_repo = ProfileRepository(db_path, data_dir)
        self.stats_repo = ProfileStatsRepository(db_path, data_dir)
        self.error_repo = ErrorRecordRepository(db_path, data_dir)
        self.error_index_repo = ErrorIndexRepository(db_path, data_dir)
    
    def add_error_record(self, user_id: str, record_data: Dict) -> str:
        """添加错题记录"""
        record_id = self.error_repo.add_record(user_id, record_data)
        
        # 同步更新索引
        error_stats = self.error_repo.get_stats(user_id)
        
        # 更新学习统计
        self._update_learning_stats(user_id, error_stats)
        
        # 更新学习画像
        self._update_profile(user_id)
        
        return record_id
    
    def _update_learning_stats(self, user_id: str, error_stats: ErrorStats):
        """更新学习统计摘要"""
        # 获取当前统计
        stats = self.stats_repo.get_stats(user_id)
        
        # 更新错题数
        stats["total_errors"] = error_stats.total_errors
        
        # 计算正确率（基于错题估计）
        total_errors = error_stats.total_errors
        overall_accuracy = 1.0 - (total_errors / (total_errors + 20))  # 平滑估计
        stats["overall_accuracy"] = overall_accuracy
        
        # 判断阶段
        if total_errors < 15:
            stats["current_level"] = "基础薄弱"
        elif total_errors < 50:
            stats["current_level"] = "强化阶段"
        else:
            stats["current_level"] = "冲刺阶段"
        
        # 更新数据库
        self.stats_repo.update_stats(user_id, stats)
    
    def _update_profile(self, user_id: str):
        """更新学习画像"""
        # 获取错题记录
        records = self.error_repo.get_records(user_id)
        
        if not records:
            return
        
        # 计算各章节错误率
        chapter_errors = {}
        for r in records:
            kp = r.get("knowledge_point", "未知")
            chapter_errors[kp] = chapter_errors.get(kp, 0) + 1
        
        # 计算正确率（平滑估计）
        max_errors = max(chapter_errors.values()) if chapter_errors else 1
        chapter_acc = {}
        for kp, count in chapter_errors.items():
            chapter_acc[kp] = max(0.1, 1.0 - count / (count + 5))
        
        # 薄弱点：正确率最低的 5 个
        weak = sorted(chapter_acc.items(), key=lambda x: x[1])[:5]
        weak_points = [w[0] for w in weak]
        
        # 生成建议
        recommendations = [
            f"重点复习 {w} 相关题型，当前掌握程度较弱"
            for w in weak_points
        ]
        
        # 获取现有画像
        profile = self.profile_repo.get_profile(user_id)
        
        # 更新画像
        profile.total_questions = len(records)
        profile.chapter_accuracy = chapter_acc
        profile.weak_points = weak_points
        profile.recommendations = recommendations[:5]
        
        # 保存画像
        self.profile_repo.save_profile(profile)
    
    def get_profile(self, user_id: str) -> UserProfile:
        """获取学习画像"""
        return self.profile_repo.get_profile(user_id)
    
    def get_errors(self, user_id: str, **filters) -> List[Dict]:
        """获取错题记录"""
        return self.error_repo.get_records(user_id, **filters)
    
    def get_error_stats(self, user_id: str) -> ErrorStats:
        """获取错题统计"""
        return self.error_repo.get_stats(user_id)
    
    def get_recommendations(self, user_id: str) -> List[str]:
        """生成复习建议"""
        profile = self.profile_repo.get_profile(user_id)
        return profile.recommendations
    
    def clear_all_data(self, user_id: str):
        """清除用户所有数据"""
        # 清除错题记录
        all_errors = self.error_repo._load_json(self.error_repo.file_path)
        if user_id in all_errors:
            all_errors[user_id] = {"records": [], "stats": {}}
            self.error_repo._save_json(self.error_repo.file_path, all_errors)
        
        # 清除索引
        self.error_index_repo._execute(
            "DELETE FROM error_index WHERE user_id = ?", (user_id,)
        )
        
        # 重置学习统计
        self.stats_repo.update_stats(user_id, {
            "total_questions": 0,
            "total_errors": 0,
            "overall_accuracy": 0.0,
            "current_level": "强化阶段",
            "streak_days": 0,
            "last_study_date": "",
        })
        
        # 重置学习画像
        profile = UserProfile(user_id=user_id)
        self.profile_repo.save_profile(profile)
