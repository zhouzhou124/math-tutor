"""Repository Layer - 基础类"""

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class BaseRepository(ABC):
    """所有 Repository 的基类"""
    
    SCHEMA_VERSION = "0.2"
    
    def __init__(self, db_path: Path, data_dir: Path):
        self.db_path = db_path
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _save_json(self, path: Path, data: Dict[str, Any]):
        """保存数据到 JSON 文件（添加版本字段）"""
        data_with_version = {
            "schema_version": self.SCHEMA_VERSION,
            "data": data,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data_with_version, f, ensure_ascii=False, indent=2)
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """从 JSON 文件加载数据"""
        if not path.exists():
            return {}
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 处理版本兼容
        if "schema_version" in data:
            return data.get("data", {})
        else:
            # 旧格式，直接返回
            return data
    
    @abstractmethod
    def initialize(self):
        """初始化资源（表、文件等）"""
        pass


class JSONRepository(BaseRepository):
    """基于 JSON 的 Repository 基类"""
    
    def __init__(self, db_path: Path, data_dir: Path, file_name: str):
        super().__init__(db_path, data_dir)
        self.file_path = data_dir / file_name
    
    def initialize(self):
        """确保文件存在"""
        if not self.file_path.exists():
            self._save_json(self.file_path, {})


class SQLiteRepository(BaseRepository):
    """基于 SQLite 的 Repository 基类"""
    
    def initialize(self):
        """初始化数据库表"""
        pass
    
    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行 SQL 语句"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor
    
    def _query(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行查询语句"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor
