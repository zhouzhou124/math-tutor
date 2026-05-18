"""Repository Layer - 核心数据访问类

采用 JSON + SQLite 混合存储方案：
- SQLite: 存储用户、索引、统计等结构化数据
- JSON: 存储学习画像、错题记录等复杂结构数据
"""

import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from .models import User, UserProfile, ErrorRecord, ErrorStats, DashboardData


class Repository:
    """统一数据访问层"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # SQLite 数据库路径
        self.db_path = self.storage_dir / "app.db"
        
        # JSON 数据目录
        self.users_data_dir = self.storage_dir / "users_data"
        self.users_data_dir.mkdir(exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        # 初始化默认用户（用于向后兼容）
        self._init_default_user()
    
    def _init_database(self):
        """初始化 SQLite 数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # 错题索引表（用于快速查询）
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
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # 创建索引（SQLite 需要单独创建）
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_user ON error_index(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_date ON error_index(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_error_kp ON error_index(knowledge_point)")
        
        # 学习统计摘要表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_stats (
                user_id TEXT PRIMARY KEY,
                total_questions INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                overall_accuracy REAL DEFAULT 0.0,
                current_level TEXT DEFAULT '强化阶段',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _init_default_user(self):
        """初始化默认用户（向后兼容）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id FROM users WHERE username = 'default'")
        if cursor.fetchone() is None:
            # 创建默认用户
            user_id = "user_default"
            hashed_pwd = self._hash_password("123456")
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO users (user_id, username, email, hashed_password, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, "default", "", hashed_pwd, now, now))
            
            # 创建学习统计记录
            cursor.execute("""
                INSERT INTO learning_stats (user_id, updated_at)
                VALUES (?, ?)
            """, (user_id, now))
            
            conn.commit()
            
            # 初始化用户数据目录
            self._init_user_data(user_id)
        
        conn.close()
    
    def _hash_password(self, password: str) -> str:
        """密码哈希（使用 SHA-256）"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _init_user_data(self, user_id: str):
        """初始化用户数据目录"""
        user_dir = self.users_data_dir / user_id
        user_dir.mkdir(exist_ok=True)
        
        # 初始化学习画像
        profile = UserProfile(user_id=user_id)
        self._save_user_profile_json(user_id, profile)
        
        # 初始化错题记录
        self._save_error_records_json(user_id, {"records": [], "stats": {}})
    
    def _save_user_profile_json(self, user_id: str, profile: UserProfile):
        """保存用户画像到 JSON 文件"""
        user_dir = self.users_data_dir / user_id
        profile_path = user_dir / "profile.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _load_user_profile_json(self, user_id: str) -> UserProfile:
        """从 JSON 文件加载用户画像"""
        user_dir = self.users_data_dir / user_id
        profile_path = user_dir / "profile.json"
        
        if not profile_path.exists():
            return UserProfile(user_id=user_id)
        
        with open(profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return UserProfile(
            user_id=data["user_id"],
            level=data.get("level", "强化阶段"),
            total_questions=data.get("total_questions", 0),
            overall_accuracy=data.get("overall_accuracy", 0.0),
            chapter_accuracy=data.get("chapter_accuracy", {}),
            weak_points=data.get("weak_points", []),
            recommendations=data.get("recommendations", []),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat())),
        )
    
    def _save_error_records_json(self, user_id: str, data: Dict):
        """保存错题记录到 JSON 文件"""
        user_dir = self.users_data_dir / user_id
        error_path = user_dir / "errors.json"
        with open(error_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_error_records_json(self, user_id: str) -> Dict:
        """从 JSON 文件加载错题记录"""
        user_dir = self.users_data_dir / user_id
        error_path = user_dir / "errors.json"
        
        if not error_path.exists():
            return {"records": [], "stats": {}}
        
        with open(error_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # ──────────────────────────────────────────────────────────
    # 用户操作
    # ──────────────────────────────────────────────────────────
    
    def create_user(self, username: str, password: str, email: str = "") -> Optional[str]:
        """创建用户，返回 user_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            user_id = f"user_{int(time.time())}"
            hashed_pwd = self._hash_password(password)
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO users (user_id, username, email, hashed_password, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, email, hashed_pwd, now, now))
            
            # 创建学习统计记录
            cursor.execute("""
                INSERT INTO learning_stats (user_id, updated_at)
                VALUES (?, ?)
            """, (user_id, now))
            
            conn.commit()
            
            # 初始化用户数据目录
            self._init_user_data(user_id)
            
            return user_id
        except sqlite3.IntegrityError:
            return None  # 用户名已存在
        finally:
            conn.close()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, hashed_password, created_at, updated_at, is_active
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5]),
                is_active=bool(row[6]),
            )
        return None
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证，返回 user_id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        hashed_pwd = self._hash_password(password)
        
        cursor.execute("""
            SELECT user_id FROM users
            WHERE username = ? AND hashed_password = ? AND is_active = 1
        """, (username, hashed_pwd))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    # ──────────────────────────────────────────────────────────
    # 用户画像操作
    # ──────────────────────────────────────────────────────────
    
    def get_user_profile(self, user_id: str) -> UserProfile:
        """获取用户学习画像"""
        return self._load_user_profile_json(user_id)
    
    def save_user_profile(self, user_id: str, profile: UserProfile):
        """保存用户学习画像"""
        profile.user_id = user_id
        profile.updated_at = datetime.now()
        self._save_user_profile_json(user_id, profile)
        
        # 更新统计摘要
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE learning_stats
            SET total_questions = ?, overall_accuracy = ?, current_level = ?, updated_at = ?
            WHERE user_id = ?
        """, (profile.total_questions, profile.overall_accuracy, profile.level, 
              profile.updated_at.isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    # ──────────────────────────────────────────────────────────
    # 错题记录操作
    # ──────────────────────────────────────────────────────────
    
    def add_error_record(self, user_id: str, record: Dict[str, Any]) -> str:
        """添加错题记录，返回 record_id"""
        # 生成记录ID
        record_id = f"err_{int(time.time())}_{int(time.time() * 1000) % 1000}"
        
        # 构建完整记录
        full_record = {
            "record_id": record_id,
            "user_id": user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            **record,
        }
        
        # 检查重复
        errors_data = self._load_error_records_json(user_id)
        same_kp = [r for r in errors_data["records"] 
                   if r.get("knowledge_point") == record.get("knowledge_point")]
        full_record["is_repeat"] = len(same_kp) > 0
        full_record["repeat_count"] = len(same_kp) + 1
        
        # 保存到 JSON
        errors_data["records"].append(full_record)
        self._update_error_stats(errors_data)
        self._save_error_records_json(user_id, errors_data)
        
        # 同时保存到 SQLite 索引
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO error_index (
                record_id, user_id, question_id, question_type, 
                knowledge_point, error_type, difficulty, date, time, is_repeat
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id, user_id,
            record.get("question_id", ""),
            record.get("question_type", ""),
            record.get("knowledge_point", ""),
            record.get("error_type", ""),
            record.get("difficulty", "中等"),
            full_record["date"],
            full_record["time"],
            1 if full_record["is_repeat"] else 0
        ))
        
        conn.commit()
        conn.close()
        
        # 更新学习统计
        self._update_learning_stats(user_id)
        
        return record_id
    
    def _update_error_stats(self, errors_data: Dict):
        """更新错题统计"""
        records = errors_data["records"]
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
        
        errors_data["stats"] = stats
    
    def _update_learning_stats(self, user_id: str):
        """更新学习统计摘要"""
        errors_data = self._load_error_records_json(user_id)
        records = errors_data["records"]
        
        if not records:
            return
        
        total_errors = len(records)
        
        # 计算正确率（基于错题估计）
        chapter_errors = {}
        for r in records:
            kp = r.get("knowledge_point", "未知")
            chapter_errors[kp] = chapter_errors.get(kp, 0) + 1
        
        max_errors = max(chapter_errors.values()) if chapter_errors else 1
        overall_accuracy = 1.0 - (total_errors / (total_errors + 20))  # 平滑估计
        
        # 判断阶段
        if total_errors < 15:
            level = "基础薄弱"
        elif total_errors < 50:
            level = "强化阶段"
        else:
            level = "冲刺阶段"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE learning_stats
            SET total_errors = ?, overall_accuracy = ?, current_level = ?, updated_at = ?
            WHERE user_id = ?
        """, (total_errors, overall_accuracy, level, datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
    
    def get_error_records(self, user_id: str, **filters) -> List[Dict]:
        """获取错题记录，支持筛选"""
        errors_data = self._load_error_records_json(user_id)
        records = errors_data["records"]
        
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
    
    def get_error_stats(self, user_id: str) -> ErrorStats:
        """获取错题统计"""
        errors_data = self._load_error_records_json(user_id)
        stats = errors_data.get("stats", {})
        
        return ErrorStats(
            user_id=user_id,
            total_errors=stats.get("total_errors", 0),
            by_chapter=stats.get("by_chapter", {}),
            by_type=stats.get("by_type", {}),
            by_difficulty=stats.get("by_difficulty", {}),
            repeat_rate=stats.get("repeat_rate", 0.0),
        )
    
    # ──────────────────────────────────────────────────────────
    # 仪表盘数据
    # ──────────────────────────────────────────────────────────
    
    def get_dashboard_data(self, user_id: str) -> DashboardData:
        """获取仪表盘数据"""
        # 从 SQLite 获取统计摘要
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_questions, total_errors, overall_accuracy, current_level
            FROM learning_stats WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        total_questions, total_errors, overall_accuracy, current_level = (
            row if row else (0, 0, 0.0, "强化阶段")
        )
        
        # 从 JSON 获取详细数据
        profile = self._load_user_profile_json(user_id)
        errors_data = self._load_error_records_json(user_id)
        
        # 转换错题记录为 ErrorRecord 对象（过滤未知字段）
        recent_errors = []
        for record_data in errors_data["records"][:10]:
            # 只保留 ErrorRecord 能接受的字段
            filtered_data = {k: v for k, v in record_data.items() 
                           if k in ["record_id", "user_id", "question_id", "question_type",
                                    "knowledge_point", "error_type", "difficulty",
                                    "student_answer", "correct_answer", "score", "max_score",
                                    "is_repeat", "repeat_count", "date", "time"]}
            recent_errors.append(ErrorRecord(**filtered_data))
        
        return DashboardData(
            user_id=user_id,
            total_questions=total_questions,
            total_errors=total_errors,
            overall_accuracy=overall_accuracy,
            current_level=current_level,
            weak_points=profile.weak_points,
            recent_errors=recent_errors,
            chapter_stats=profile.chapter_accuracy,
        )
    
    # ──────────────────────────────────────────────────────────
    # 数据迁移（从旧格式迁移）
    # ──────────────────────────────────────────────────────────
    
    def migrate_from_legacy(self, legacy_notebook_path: str, legacy_profile_path: str):
        """从旧版 JSON 格式迁移数据到默认用户"""
        user_id = "user_default"
        
        # 迁移错题记录
        if os.path.exists(legacy_notebook_path):
            with open(legacy_notebook_path, "r", encoding="utf-8") as f:
                legacy_data = json.load(f)
            
            # 清空现有记录
            errors_data = {"records": [], "stats": {}}
            
            # 迁移记录（添加 user_id 和 record_id）
            for i, record in enumerate(legacy_data.get("records", [])):
                record["user_id"] = user_id
                # 处理旧数据中的 id 字段（统一为 record_id）
                if "id" in record and "record_id" not in record:
                    record["record_id"] = record.pop("id")
                # 如果没有 record_id，生成一个
                if "record_id" not in record:
                    record["record_id"] = f"err_migrated_{i}"
                errors_data["records"].append(record)
            
            self._update_error_stats(errors_data)
            self._save_error_records_json(user_id, errors_data)
            
            # 更新 SQLite 索引
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 先清空现有索引
            cursor.execute("DELETE FROM error_index WHERE user_id = ?", (user_id,))
            
            # 重新插入
            for record in errors_data["records"]:
                cursor.execute("""
                    INSERT INTO error_index (
                        record_id, user_id, question_id, question_type, 
                        knowledge_point, error_type, difficulty, date, time, is_repeat
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record["record_id"], record["user_id"],
                    record.get("question_id", ""),
                    record.get("question_type", ""),
                    record.get("knowledge_point", ""),
                    record.get("error_type", ""),
                    record.get("difficulty", "中等"),
                    record.get("date", ""),
                    record.get("time", ""),
                    1 if record.get("is_repeat") else 0
                ))
            
            conn.commit()
            conn.close()
        
        # 迁移学习画像
        if os.path.exists(legacy_profile_path):
            with open(legacy_profile_path, "r", encoding="utf-8") as f:
                legacy_profile = json.load(f)
            
            profile = UserProfile(
                user_id=user_id,
                level=legacy_profile.get("level", "强化阶段"),
                total_questions=legacy_profile.get("total_questions", 0),
                overall_accuracy=legacy_profile.get("overall_accuracy", 0.0),
                chapter_accuracy=legacy_profile.get("chapter_accuracy", {}),
                weak_points=legacy_profile.get("weak_points", []),
                recommendations=legacy_profile.get("recommendations", []),
            )
            self.save_user_profile(user_id, profile)
        
        # 更新学习统计
        self._update_learning_stats(user_id)
