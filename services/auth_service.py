"""Services Layer - 认证服务"""

from typing import Optional
from pathlib import Path

from repository import UserRepository
from repository.models import User


class AuthService:
    """认证服务 - 处理用户登录、注册等业务逻辑"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        self.user_repo = UserRepository(db_path, data_dir)
    
    def register(self, username: str, password: str, email: str = "") -> Optional[str]:
        """用户注册"""
        # 验证输入
        if not username or not password:
            return None
        
        # 创建用户
        user_id = self.user_repo.create_user(username, password, email)
        
        # 如果创建成功，初始化用户数据
        if user_id:
            # 用户数据会在 Repository 层自动初始化
            pass
        
        return user_id
    
    def login(self, username: str, password: str) -> Optional[str]:
        """用户登录"""
        return self.user_repo.authenticate(username, password)
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        return self.user_repo.get_user(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户信息"""
        return self.user_repo.get_user_by_username(username)
    
    def logout(self, user_id: str):
        """用户登出（在 Session 层处理）"""
        pass
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        # 验证旧密码
        user = self.user_repo.get_user(user_id)
        if not user:
            return False
        
        # 检查旧密码（这里需要比对哈希）
        import hashlib
        hashed_old = hashlib.sha256(old_password.encode()).hexdigest()
        if hashed_old != user.hashed_password:
            return False
        
        # 更新密码
        user.hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        self.user_repo.update_user(user)
        return True
