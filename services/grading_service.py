"""Services Layer - 批改服务"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from repository import (
    ProfileStatsRepository,
    ErrorRecordRepository,
    ErrorIndexRepository,
)
from repository.models import GradingResult, DiagnosisResult


def _get_question_type_for_record(question: dict | None = None, grading_result: dict | None = None) -> str:
    """P39: Extract real question_type from question/result/payload. Never hardcode."""
    for source in (question, grading_result):
        if isinstance(source, dict):
            for key in ("question_type", "type"):
                val = source.get(key)
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
    return "未知题型"


class GradingService:
    """批改服务 - 处理作业批改和错误诊断"""

    def __init__(self, db_path: Path, data_dir: Path, grading_agent=None):
        self.stats_repo = ProfileStatsRepository(db_path, data_dir)
        self.error_repo = ErrorRecordRepository(db_path, data_dir)
        self.error_index_repo = ErrorIndexRepository(db_path, data_dir)
        self.grading_agent = grading_agent

    def grade_answer(self, user_id: str, question_id: str,
                     student_answer: str, max_score: int = 10) -> GradingResult:
        """批改学生答案。需要注入 grading_agent，不再使用随机模拟。"""
        if self.grading_agent is None:
            raise NotImplementedError(
                "GradingService requires a real grading_agent. "
                "Random simulated grading has been removed."
            )
        grading_id = f"grad_{int(time.time())}"
        raw = self.grading_agent.grade(question_id, student_answer, max_score)
        score = int(raw.get("total", raw.get("score", 0)))
        is_correct = score >= max_score * 0.9

        result = GradingResult(
            grading_id=grading_id,
            user_id=user_id,
            question_id=question_id,
            student_answer=student_answer,
            score=score,
            max_score=max_score,
            is_correct=is_correct,
            confidence=float(raw.get("confidence", 0.85)),
            engine=raw.get("engine", "agent"),
        )

        if not is_correct:
            self._record_error(user_id, question_id, student_answer, score, max_score)

        return result
    
    def _record_error(self, user_id: str, question_id: str,
                      student_answer: str, score: int, max_score: int,
                      question: dict | None = None, grading_result: dict | None = None):
        """记录错题"""
        record_data = {
            "question_id": question_id,
            "question_type": _get_question_type_for_record(question, grading_result),
            "knowledge_point": "未知知识点",  # 应该从题库获取
            "error_type": "计算错误",  # 应该由诊断服务确定
            "difficulty": "中等",
            "student_answer": student_answer,
            "score": score,
            "max_score": max_score,
        }
        
        self.error_repo.add_record(user_id, record_data)
    
    def diagnose_error(self, user_id: str, question_id: str, 
                       student_answer: str) -> DiagnosisResult:
        """诊断错误原因"""
        diagnosis_id = f"diag_{int(time.time())}"
        
        # 这里应该调用 DiagnosisAgent 进行实际诊断
        # 简化实现：返回预设诊断结果
        result = DiagnosisResult(
            diagnosis_id=diagnosis_id,
            user_id=user_id,
            question_id=question_id,
            error_type="计算错误",
            root_cause="计算过程中出现错误",
            knowledge_points=["高等数学 - 微积分"],
            common_mistakes=["符号错误", "计算粗心"],
            recommendations=[
                "建议重新计算关键步骤",
                "注意符号和系数的正确性",
            ],
        )
        
        return result
    
    def get_grading_history(self, user_id: str, limit: int = 20) -> list[GradingResult]:
        """获取批改历史"""
        # 简化实现：从错题记录中获取
        records = self.error_repo.get_records(user_id, limit=limit)
        
        results = []
        for record in records:
            result = GradingResult(
                grading_id=record.get("record_id", ""),
                user_id=record.get("user_id", ""),
                question_id=record.get("question_id", ""),
                student_answer=record.get("student_answer", ""),
                score=record.get("score", 0),
                max_score=record.get("max_score", 10),
                is_correct=False,
                created_at=datetime.now(),
            )
            results.append(result)
        
        return results
