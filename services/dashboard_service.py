"""Services Layer - 仪表盘服务"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from repository import (
    UserRepository, 
    ProfileRepository, 
    ProfileStatsRepository,
    ErrorRecordRepository,
    ErrorIndexRepository,
)
from repository.models import DashboardData, ErrorRecord


class DashboardService:
    """仪表盘服务 - 聚合多维度数据供仪表盘展示"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        self.user_repo = UserRepository(db_path, data_dir)
        self.profile_repo = ProfileRepository(db_path, data_dir)
        self.stats_repo = ProfileStatsRepository(db_path, data_dir)
        self.error_repo = ErrorRecordRepository(db_path, data_dir)
        self.error_index_repo = ErrorIndexRepository(db_path, data_dir)
    
    def get_dashboard_data(self, user_id: str) -> DashboardData:
        """获取完整的仪表盘数据"""
        # 获取学习统计
        stats = self.stats_repo.get_stats(user_id)
        
        # 获取学习画像
        profile = self.profile_repo.get_profile(user_id)
        
        # 获取错题统计
        error_stats = self.error_repo.get_stats(user_id)
        
        # 获取最近错题
        recent_error_dicts = self.error_repo.get_records(user_id, limit=10)
        
        # 转换为 ErrorRecord 对象
        recent_errors = []
        for record_data in recent_error_dicts:
            # 映射字段名
            mapped_data = {}
            field_mapping = {
                "total_score": "max_score",
                "standard_answer": "correct_answer",
            }
            for original_key, value in record_data.items():
                new_key = field_mapping.get(original_key, original_key)
                mapped_data[new_key] = value
            
            # ErrorRecord 类接受的字段列表
            allowed_fields = ["record_id", "user_id", "question_id", "question_type",
                            "knowledge_point", "error_type", "difficulty",
                            "student_answer", "correct_answer", "score", "max_score",
                            "is_repeat", "repeat_count", "date", "time"]
            
            # 只保留允许的字段
            filtered_data = {k: v for k, v in mapped_data.items() if k in allowed_fields}
            
            # 确保所有必需字段都存在
            required_fields = ["record_id", "user_id", "question_id", "question_type", 
                               "knowledge_point", "error_type"]
            for field in required_fields:
                if field not in filtered_data:
                    if field == "question_id":
                        filtered_data[field] = "unknown_" + filtered_data.get("record_id", "unknown")
                    else:
                        filtered_data[field] = "unknown"
            
            # 设置默认值
            filtered_data.setdefault("difficulty", "中等")
            filtered_data.setdefault("student_answer", None)
            filtered_data.setdefault("correct_answer", None)
            filtered_data.setdefault("score", 0)
            filtered_data.setdefault("max_score", 10)
            filtered_data.setdefault("is_repeat", False)
            filtered_data.setdefault("repeat_count", 1)
            filtered_data.setdefault("date", datetime.now().strftime("%Y-%m-%d"))
            filtered_data.setdefault("time", datetime.now().strftime("%H:%M"))
            
            recent_errors.append(ErrorRecord(**filtered_data))
        
        # 获取错误类型分布
        error_type_dist = self.error_index_repo.get_error_count_by_type(user_id)
        
        return DashboardData(
            user_id=user_id,
            total_questions=stats.get("total_questions", 0),
            total_errors=stats.get("total_errors", 0),
            overall_accuracy=stats.get("overall_accuracy", 0.0),
            current_level=stats.get("current_level", "强化阶段"),
            streak_days=stats.get("streak_days", 0),
            last_study_date=stats.get("last_study_date"),
            weak_points=profile.weak_points,
            recent_errors=recent_errors,
            chapter_stats=profile.chapter_accuracy,
            error_type_dist=error_type_dist,
        )
    
    def update_streak(self, user_id: str):
        """更新连续打卡天数"""
        stats = self.stats_repo.get_stats(user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        last_date = stats.get("last_study_date")
        
        if last_date == today:
            # 今天已经打卡过
            return
        
        # 计算连续天数
        streak_days = stats.get("streak_days", 0)
        
        if last_date:
            # 检查是否连续
            last_dt = datetime.strptime(last_date, "%Y-%m-%d")
            today_dt = datetime.strptime(today, "%Y-%m-%d")
            diff_days = (today_dt - last_dt).days
            
            if diff_days == 1:
                streak_days += 1
            else:
                streak_days = 1
        else:
            streak_days = 1
        
        # 更新统计
        stats.update({
            "streak_days": streak_days,
            "last_study_date": today,
        })
        self.stats_repo.update_stats(user_id, stats)
    
    def calculate_mastery(self, user_id: str) -> Dict[str, float]:
        """计算各知识点掌握度"""
        profile = self.profile_repo.get_profile(user_id)
        chapter_acc = profile.chapter_accuracy
        
        # 掌握度 = 正确率（0-100）
        mastery = {}
        for chapter, accuracy in chapter_acc.items():
            mastery[chapter] = accuracy * 100
        
        return mastery
    
    def get_weekly_progress(self, user_id: str, weeks: int = 4) -> List[Dict]:
        """获取最近几周的学习进度"""
        # 获取错题记录
        records = self.error_repo.get_records(user_id)
        
        # 按周分组
        weekly_data = []
        today = datetime.now()
        
        for week_offset in range(weeks):
            start_of_week = today - datetime.timedelta(days=today.weekday() + week_offset * 7)
            end_of_week = start_of_week + datetime.timedelta(days=6)
            
            week_records = [
                r for r in records
                if start_of_week.strftime("%Y-%m-%d") <= r.get("date", "") <= end_of_week.strftime("%Y-%m-%d")
            ]
            
            weekly_data.append({
                "week_start": start_of_week.strftime("%Y-%m-%d"),
                "week_end": end_of_week.strftime("%Y-%m-%d"),
                "count": len(week_records),
                "accuracy": self._calculate_week_accuracy(week_records),
            })
        
        return weekly_data
    
    def _calculate_week_accuracy(self, records: List[Dict]) -> float:
        """计算一周的正确率"""
        if not records:
            return 0.0
        
        total_score = sum(r.get("score", 0) for r in records)
        total_max = sum(r.get("max_score", 10) for r in records)
        
        return total_score / max(total_max, 1)
