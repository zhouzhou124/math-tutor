"""题目仓库 - 题库管理"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import BaseRepository
from .models import Question


class QuestionRepository(BaseRepository):
    """题目数据访问层"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir)
        self.questions_dir = self.data_dir.parent / "questions"
        self.simulations_dir = self.questions_dir / "simulations"
        self.exams_dir = self.questions_dir / "exams"
        self.questions_dir.mkdir(parents=True, exist_ok=True)
        self.simulations_dir.mkdir(exist_ok=True)
        self.exams_dir.mkdir(exist_ok=True)
    
    def get_all_questions(self) -> List[Question]:
        """获取所有题目"""
        questions = []
        
        # 遍历模拟题库
        for json_file in self.simulations_dir.glob("*.json"):
            q = self._load_question_from_file(json_file)
            if q:
                questions.append(q)
        
        # 遍历真题库
        for json_file in self.exams_dir.glob("*.json"):
            q = self._load_question_from_file(json_file)
            if q:
                questions.append(q)
        
        return sorted(questions, key=lambda q: (q.category, q.volume, q.question_no))
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """根据ID获取题目"""
        # 尝试从模拟题库查找
        file_path = self.simulations_dir / f"{question_id}.json"
        if file_path.exists():
            return self._load_question_from_file(file_path)
        
        # 尝试从真题库查找
        file_path = self.exams_dir / f"{question_id}.json"
        if file_path.exists():
            return self._load_question_from_file(file_path)
        
        return None
    
    def search_questions(self, 
                        keyword: str = "",
                        year: int = None,
                        question_type: str = "",
                        knowledge_point: str = "",
                        difficulty: str = "") -> List[Question]:
        """搜索题目"""
        all_questions = self.get_all_questions()
        filtered = []
        
        for q in all_questions:
            # 关键词搜索
            if keyword and keyword.lower() not in q.question.lower():
                continue
            
            # 年份筛选
            if year and q.year != year:
                continue
            
            # 题型筛选
            if question_type and q.question_type != question_type:
                continue
            
            # 知识点筛选
            if knowledge_point and knowledge_point not in q.knowledge_points:
                continue
            
            # 难度筛选
            if difficulty and q.difficulty != difficulty:
                continue
            
            filtered.append(q)
        
        return filtered
    
    def update_question(self, question: Question) -> bool:
        """更新题目"""
        file_path = self._get_question_file_path(question.question_id)
        if not file_path:
            return False
        
        question.updated_at = datetime.now()
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(question.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"更新题目失败: {e}")
            return False
    
    def delete_question(self, question_id: str) -> bool:
        """删除题目"""
        file_path = self._get_question_file_path(question_id)
        if not file_path:
            return False
        
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"删除题目失败: {e}")
            return False
    
    def fix_ocr(self, question_id: str, ocr_raw: str, ocr_fixed: str) -> bool:
        """修复OCR错误"""
        question = self.get_question(question_id)
        if not question:
            return False
        
        question.ocr_raw = ocr_raw
        question.ocr_fixed = ocr_fixed
        question.updated_at = datetime.now()
        
        return self.update_question(question)
    
    def create_question(self, question_data: Dict[str, Any]) -> Optional[str]:
        """创建新题目"""
        question_id = question_data.get("question_id", f"q_{int(datetime.now().timestamp())}")
        question_data["question_id"] = question_id
        
        # 确定存储目录
        category = question_data.get("category", "custom")
        if "模拟" in category or "套卷" in category:
            save_dir = self.simulations_dir
        else:
            save_dir = self.exams_dir
        
        file_path = save_dir / f"{question_id}.json"
        
        if file_path.exists():
            return None  # 题目已存在
        
        question = self._dict_to_question(question_data)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(question.to_dict(), f, ensure_ascii=False, indent=2)
            return question_id
        except Exception as e:
            print(f"创建题目失败: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取题库统计"""
        questions = self.get_all_questions()
        
        stats = {
            "total": len(questions),
            "by_type": {},
            "by_difficulty": {},
            "by_year": {},
            "by_category": {},
        }
        
        for q in questions:
            # 按题型统计
            stats["by_type"][q.question_type] = stats["by_type"].get(q.question_type, 0) + 1
            
            # 按难度统计
            stats["by_difficulty"][q.difficulty] = stats["by_difficulty"].get(q.difficulty, 0) + 1
            
            # 按年份统计
            stats["by_year"][q.year] = stats["by_year"].get(q.year, 0) + 1
            
            # 按类别统计
            stats["by_category"][q.category] = stats["by_category"].get(q.category, 0) + 1
        
        return stats
    
    def get_all_knowledge_points(self) -> List[str]:
        """获取所有知识点"""
        points = set()
        for q in self.get_all_questions():
            points.update(q.knowledge_points)
        return sorted(list(points))
    
    def get_all_categories(self) -> List[str]:
        """获取所有类别"""
        categories = set()
        for q in self.get_all_questions():
            categories.add(q.category)
        return sorted(list(categories))
    
    def _load_question_from_file(self, file_path: Path) -> Optional[Question]:
        """从文件加载题目"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._dict_to_question(data)
        except Exception as e:
            print(f"加载题目失败 {file_path}: {e}")
            return None
    
    def _dict_to_question(self, data: Dict[str, Any]) -> Question:
        """将字典转换为Question对象"""
        return Question(
            question_id=data.get("question_id", ""),
            year=data.get("year", 0),
            category=data.get("category", ""),
            volume=data.get("volume"),
            question_type=data.get("question_type", "选择题"),
            question_no=data.get("question_no", 0),
            score=data.get("score", 5),
            difficulty=data.get("difficulty", "中等"),
            knowledge_points=data.get("knowledge_points", []),
            tags=data.get("tags", []),
            question=data.get("question", ""),
            source=data.get("source"),
            options=data.get("options", {}),
            correct_option=data.get("correct_option"),
            answer=data.get("answer"),
            analysis=data.get("analysis"),
            ocr_raw=data.get("ocr_raw"),
            ocr_fixed=data.get("ocr_fixed"),
            is_valid=data.get("is_valid", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )
    
    def _get_question_file_path(self, question_id: str) -> Optional[Path]:
        """获取题目文件路径"""
        # 尝试从模拟题库查找
        file_path = self.simulations_dir / f"{question_id}.json"
        if file_path.exists():
            return file_path
        
        # 尝试从真题库查找
        file_path = self.exams_dir / f"{question_id}.json"
        if file_path.exists():
            return file_path
        
        return None
