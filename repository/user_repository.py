"""Repository Layer - 用户数据访问"""

import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import SQLiteRepository
from .models import User


class UserRepository(SQLiteRepository):
    """用户数据访问层"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir)
        self.initialize()
    
    def initialize(self):
        """初始化用户表"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                hashed_password TEXT NOT NULL,
                role TEXT DEFAULT 'student',
                is_admin INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                schema_version TEXT DEFAULT '0.2'
            )
        """)
        
        # 初始化管理员账号（如果不存在）
        self._init_admin_account()
        
        conn.commit()
        conn.close()
    
    def _init_admin_account(self):
        """初始化管理员账号"""
        cursor = self._query("SELECT user_id FROM users WHERE username = ?", ("admin",))
        if not cursor.fetchone():
            # 创建默认管理员账号
            admin_id = f"user_{int(time.time())}"
            hashed_pwd = self._hash_password("admin123")
            now = datetime.now().isoformat()
            
            self._execute("""
                INSERT INTO users (user_id, username, email, hashed_password, role, is_admin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (admin_id, "admin", "admin@example.com", hashed_pwd, "admin", 1, now, now))
    
    def _hash_password(self, password: str) -> str:
        """密码哈希（SHA-256）"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str, email: str = "", role: str = "student") -> Optional[str]:
        """创建用户，返回 user_id"""
        try:
            user_id = f"user_{int(time.time())}"
            hashed_pwd = self._hash_password(password)
            now = datetime.now().isoformat()
            is_admin = 1 if role == "admin" else 0
            
            cursor = self._execute("""
                INSERT INTO users (user_id, username, email, hashed_password, role, is_admin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, email, hashed_pwd, role, is_admin, now, now))
            
            return user_id
        except Exception:
            return None  # 用户名已存在
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        cursor = self._query("""
            SELECT user_id, username, email, hashed_password, role, is_admin, is_active, created_at, updated_at
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                role=row[4],
                is_admin=bool(row[5]),
                is_active=bool(row[6]),
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
            )
        return None
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """用户认证，返回 user_id"""
        hashed_pwd = self._hash_password(password)
        
        cursor = self._query("""
            SELECT user_id FROM users
            WHERE username = ? AND hashed_password = ? AND is_active = 1
        """, (username, hashed_pwd))
        
        row = cursor.fetchone()
        return row[0] if row else None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户信息"""
        cursor = self._query("""
            SELECT user_id, username, email, hashed_password, role, is_admin, is_active, created_at, updated_at
            FROM users WHERE username = ?
        """, (username,))
        
        row = cursor.fetchone()
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                role=row[4],
                is_admin=bool(row[5]),
                is_active=bool(row[6]),
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8]),
            )
        return None
    
    def update_user(self, user: User):
        """更新用户信息"""
        user.updated_at = datetime.now()
        self._execute("""
            UPDATE users
            SET username = ?, email = ?, updated_at = ?, is_active = ?
            WHERE user_id = ?
        """, (user.username, user.email, user.updated_at.isoformat(), 
              1 if user.is_active else 0, user.user_id))
    
    def delete_user(self, user_id: str):
        """删除用户"""
        self._execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    
    def get_all_users(self) -> list[User]:
        """获取所有用户"""
        cursor = self._query("""
            SELECT user_id, username, email, hashed_password, created_at, updated_at, is_active
            FROM users
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append(User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5]),
                is_active=bool(row[6]),
            ))
        return users
