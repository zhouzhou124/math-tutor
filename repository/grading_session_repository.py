"""批改会话仓库 - 用于数据回放"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base import JSONRepository
from .models import GradingSession, OCRResult, MathAST, ReasoningChain, GradingResult, DiagnosisResult


class GradingSessionRepository(JSONRepository):
    """批改会话数据访问层"""
    
    def __init__(self, db_path: Path, data_dir: Path):
        super().__init__(db_path, data_dir, "grading_sessions.json")
    
    def create_session(self, user_id: str, question_id: str, image_path: str = None) -> str:
        """创建批改会话"""
        session_id = f"session_{int(time.time())}_{int(time.time() * 1000) % 1000}"
        
        session = GradingSession(
            session_id=session_id,
            user_id=user_id,
            question_id=question_id,
            original_image_path=image_path,
        )
        
        sessions = self._load_json(self.file_path)
        sessions[session_id] = session.to_dict()
        self._save_json(self.file_path, sessions)
        
        return session_id
    
    def update_ocr_result(self, session_id: str, ocr_result: OCRResult):
        """更新OCR结果"""
        sessions = self._load_json(self.file_path)
        if session_id in sessions:
            sessions[session_id]["ocr_result"] = ocr_result.to_dict()
            sessions[session_id]["status"] = "processing"
            self._save_json(self.file_path, sessions)
    
    def update_ast(self, session_id: str, student_ast: MathAST = None, correct_ast: MathAST = None):
        """更新AST"""
        sessions = self._load_json(self.file_path)
        if session_id in sessions:
            if student_ast:
                sessions[session_id]["student_ast"] = student_ast.to_dict()
            if correct_ast:
                sessions[session_id]["correct_ast"] = correct_ast.to_dict()
            self._save_json(self.file_path, sessions)
    
    def update_reasoning_chain(self, session_id: str, reasoning_chain: ReasoningChain):
        """更新推理链"""
        sessions = self._load_json(self.file_path)
        if session_id in sessions:
            sessions[session_id]["reasoning_chain"] = reasoning_chain.to_dict()
            self._save_json(self.file_path, sessions)
    
    def update_grading_result(self, session_id: str, grading_result: GradingResult):
        """更新批改结果"""
        sessions = self._load_json(self.file_path)
        if session_id in sessions:
            sessions[session_id]["grading_result"] = grading_result.to_dict()
            sessions[session_id]["status"] = "completed"
            sessions[session_id]["total_time"] = (datetime.now() - datetime.fromisoformat(
                sessions[session_id]["created_at"])).total_seconds()
            self._save_json(self.file_path, sessions)
    
    def update_diagnosis_result(self, session_id: str, diagnosis_result: DiagnosisResult):
        """更新诊断结果"""
        sessions = self._load_json(self.file_path)
        if session_id in sessions:
            sessions[session_id]["diagnosis_result"] = diagnosis_result.to_dict()
            self._save_json(self.file_path, sessions)
    
    def get_session(self, session_id: str) -> Optional[GradingSession]:
        """获取批改会话"""
        sessions = self._load_json(self.file_path)
        if session_id not in sessions:
            return None
        
        data = sessions[session_id]
        return self._dict_to_session(data)
    
    def get_sessions_by_user(self, user_id: str) -> List[GradingSession]:
        """获取用户的所有批改会话"""
        sessions = self._load_json(self.file_path)
        user_sessions = []
        
        for session_data in sessions.values():
            if session_data.get("user_id") == user_id:
                user_sessions.append(self._dict_to_session(session_data))
        
        return sorted(user_sessions, key=lambda s: s.created_at, reverse=True)
    
    def get_recent_sessions(self, limit: int = 20) -> List[GradingSession]:
        """获取最近的批改会话"""
        sessions = self._load_json(self.file_path)
        all_sessions = []
        
        for session_data in sessions.values():
            all_sessions.append(self._dict_to_session(session_data))
        
        return sorted(all_sessions, key=lambda s: s.created_at, reverse=True)[:limit]
    
    def get_sessions_by_status(self, status: str) -> List[GradingSession]:
        """按状态获取会话"""
        sessions = self._load_json(self.file_path)
        filtered = []
        
        for session_data in sessions.values():
            if session_data.get("status") == status:
                filtered.append(self._dict_to_session(session_data))
        
        return sorted(filtered, key=lambda s: s.created_at, reverse=True)
    
    def _dict_to_session(self, data: Dict[str, Any]) -> GradingSession:
        """将字典转换为GradingSession对象"""
        session = GradingSession(
            session_id=data["session_id"],
            user_id=data["user_id"],
            question_id=data["question_id"],
            original_image_path=data.get("original_image_path"),
            status=data.get("status", "pending"),
            total_time=data.get("total_time", 0.0),
            error_message=data.get("error_message"),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
        
        # OCR结果
        if data.get("ocr_result"):
            ocr_data = data["ocr_result"]
            session.ocr_result = OCRResult(
                ocr_id=ocr_data["ocr_id"],
                image_path=ocr_data.get("image_path"),
                raw_text=ocr_data.get("raw_text"),
                latex_text=ocr_data.get("latex_text"),
                confidence=ocr_data.get("confidence", 0.0),
                processing_time=ocr_data.get("processing_time", 0.0),
                errors=ocr_data.get("errors", []),
                created_at=datetime.fromisoformat(ocr_data["created_at"]),
            )
        
        # 学生AST
        if data.get("student_ast"):
            ast_data = data["student_ast"]
            session.student_ast = MathAST(
                ast_id=ast_data["ast_id"],
                latex_source=ast_data["latex_source"],
                root_node_id=ast_data.get("root_node_id"),
                validation_errors=ast_data.get("validation_errors", []),
                created_at=datetime.fromisoformat(ast_data["created_at"]),
            )
        
        # 正确答案AST
        if data.get("correct_ast"):
            ast_data = data["correct_ast"]
            session.correct_ast = MathAST(
                ast_id=ast_data["ast_id"],
                latex_source=ast_data["latex_source"],
                root_node_id=ast_data.get("root_node_id"),
                validation_errors=ast_data.get("validation_errors", []),
                created_at=datetime.fromisoformat(ast_data["created_at"]),
            )
        
        # 推理链
        if data.get("reasoning_chain"):
            rc_data = data["reasoning_chain"]
            session.reasoning_chain = ReasoningChain(
                chain_id=rc_data["chain_id"],
                question_id=rc_data["question_id"],
                steps=[],  # 简化处理
                final_answer=rc_data.get("final_answer"),
                confidence=rc_data.get("confidence", 0.0),
                created_at=datetime.fromisoformat(rc_data["created_at"]),
            )
        
        # 批改结果
        if data.get("grading_result"):
            gr_data = data["grading_result"]
            session.grading_result = GradingResult(
                grading_id=gr_data["grading_id"],
                user_id=gr_data["user_id"],
                question_id=gr_data["question_id"],
                student_answer=gr_data.get("student_answer"),
                score=gr_data["score"],
                max_score=gr_data["max_score"],
                is_correct=gr_data.get("is_correct", False),
                method_matched=gr_data.get("method_matched"),
                step_analysis=gr_data.get("step_analysis", []),
                error_propagation=gr_data.get("error_propagation", []),
                confidence=gr_data.get("confidence", 0.0),
                engine=gr_data.get("engine", "unknown"),
                created_at=datetime.fromisoformat(gr_data["created_at"]),
            )
        
        # 诊断结果
        if data.get("diagnosis_result"):
            dr_data = data["diagnosis_result"]
            session.diagnosis_result = DiagnosisResult(
                diagnosis_id=dr_data["diagnosis_id"],
                user_id=dr_data["user_id"],
                question_id=dr_data["question_id"],
                error_type=dr_data["error_type"],
                root_cause=dr_data.get("root_cause"),
                knowledge_points=dr_data.get("knowledge_points", []),
                common_mistakes=dr_data.get("common_mistakes", []),
                recommendations=dr_data.get("recommendations", []),
                is_repeat=dr_data.get("is_repeat", False),
                repeat_count=dr_data.get("repeat_count", 0),
                created_at=datetime.fromisoformat(dr_data["created_at"]),
            )
        
        return session
