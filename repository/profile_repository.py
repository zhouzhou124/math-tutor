"""Repository Layer - 学习画像数据访问"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .base import JSONRepository, SQLiteRepository
from .models import UserProfile


class ProfileRepository(JSONRepository):
    """学习画像数据访问层（JSON 存储复杂结构）"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir, "profiles.json")
    
    def get_profile(self, user_id: str) -> UserProfile:
        """获取用户学习画像"""
        all_profiles = self._load_json(self.file_path)
        profile_data = all_profiles.get(user_id, {})
        
        if not profile_data:
            return UserProfile(user_id=user_id)
        
        return UserProfile(
            user_id=profile_data["user_id"],
            level=profile_data.get("level", "强化阶段"),
            total_questions=profile_data.get("total_questions", 0),
            overall_accuracy=profile_data.get("overall_accuracy", 0.0),
            chapter_accuracy=profile_data.get("chapter_accuracy", {}),
            weak_points=profile_data.get("weak_points", []),
            recommendations=profile_data.get("recommendations", []),
            created_at=datetime.fromisoformat(profile_data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(profile_data.get("updated_at", datetime.now().isoformat())),
        )
    
    def save_profile(self, profile: UserProfile):
        """保存用户学习画像"""
        all_profiles = self._load_json(self.file_path)
        profile.updated_at = datetime.now()
        all_profiles[profile.user_id] = profile.to_dict()
        self._save_json(self.file_path, all_profiles)


class ProfileStatsRepository(SQLiteRepository):
    """学习统计摘要（SQLite 存储快速查询数据）"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir)
        self.initialize()
    
    def initialize(self):
        """初始化统计摘要表"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_stats (
                user_id TEXT PRIMARY KEY,
                total_questions INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                overall_accuracy REAL DEFAULT 0.0,
                current_level TEXT DEFAULT '强化阶段',
                streak_days INTEGER DEFAULT 0,
                last_study_date TEXT,
                updated_at TEXT NOT NULL,
                schema_version TEXT DEFAULT '0.2'
            )
        """)
        
        conn.commit()
        conn.close()
    
    def update_stats(self, user_id: str, stats: Dict):
        """更新学习统计"""
        cursor = self._query("SELECT user_id FROM learning_stats WHERE user_id = ?", (user_id,))
        
        if cursor.fetchone():
            # 更新现有记录
            self._execute("""
                UPDATE learning_stats
                SET total_questions = ?, total_errors = ?, overall_accuracy = ?, 
                    current_level = ?, streak_days = ?, last_study_date = ?, updated_at = ?
                WHERE user_id = ?
            """, (
                stats.get("total_questions", 0),
                stats.get("total_errors", 0),
                stats.get("overall_accuracy", 0.0),
                stats.get("current_level", "强化阶段"),
                stats.get("streak_days", 0),
                stats.get("last_study_date", ""),
                datetime.now().isoformat(),
                user_id,
            ))
        else:
            # 创建新记录
            self._execute("""
                INSERT INTO learning_stats (
                    user_id, total_questions, total_errors, overall_accuracy, 
                    current_level, streak_days, last_study_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                stats.get("total_questions", 0),
                stats.get("total_errors", 0),
                stats.get("overall_accuracy", 0.0),
                stats.get("current_level", "强化阶段"),
                stats.get("streak_days", 0),
                stats.get("last_study_date", ""),
                datetime.now().isoformat(),
            ))
    
    def get_stats(self, user_id: str) -> Dict:
        """获取学习统计"""
        cursor = self._query("""
            SELECT total_questions, total_errors, overall_accuracy, current_level, 
                   streak_days, last_study_date
            FROM learning_stats WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "total_questions": row[0],
                "total_errors": row[1],
                "overall_accuracy": row[2],
                "current_level": row[3],
                "streak_days": row[4],
                "last_study_date": row[5],
            }
        return {}
