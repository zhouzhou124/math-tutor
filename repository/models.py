"""Repository Layer - 数据模型定义

所有数据模型使用 dataclass，确保类型安全和数据一致性。
添加 schema_version 字段支持数据结构升级。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Union
from datetime import datetime


# ──────────────────────────────────────────────────────────
# 基础模型
# ──────────────────────────────────────────────────────────

@dataclass(kw_only=True)
class BaseModel:
    """所有模型的基类"""
    schema_version: str = "0.2"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in vars(self).items() if not k.startswith('_')}


# ──────────────────────────────────────────────────────────
# 用户模型
# ──────────────────────────────────────────────────────────

@dataclass
class User(BaseModel):
    """用户模型"""
    user_id: str
    username: str
    email: Optional[str] = None
    hashed_password: str = ""
    role: str = "student"  # student, admin
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "hashed_password": self.hashed_password,
            "role": self.role,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "schema_version": self.schema_version,
        }


# ──────────────────────────────────────────────────────────
# 学习画像模型
# ──────────────────────────────────────────────────────────

@dataclass
class UserProfile(BaseModel):
    """用户学习画像模型"""
    user_id: str
    level: str = "强化阶段"
    total_questions: int = 0
    overall_accuracy: float = 0.0
    chapter_accuracy: Dict[str, float] = field(default_factory=dict)
    weak_points: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "level": self.level,
            "total_questions": self.total_questions,
            "overall_accuracy": self.overall_accuracy,
            "chapter_accuracy": self.chapter_accuracy,
            "weak_points": self.weak_points,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "schema_version": self.schema_version,
        }


# ──────────────────────────────────────────────────────────
# 错题记录模型
# ──────────────────────────────────────────────────────────

@dataclass
class ErrorRecord(BaseModel):
    """错题记录模型"""
    record_id: str
    user_id: str
    question_id: str
    question_type: str
    knowledge_point: str
    error_type: str
    difficulty: str = "中等"
    student_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    score: int = 0
    max_score: int = 10
    is_repeat: bool = False
    repeat_count: int = 1
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M"))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "question_type": self.question_type,
            "knowledge_point": self.knowledge_point,
            "error_type": self.error_type,
            "difficulty": self.difficulty,
            "student_answer": self.student_answer,
            "correct_answer": self.correct_answer,
            "score": self.score,
            "max_score": self.max_score,
            "is_repeat": self.is_repeat,
            "repeat_count": self.repeat_count,
            "date": self.date,
            "time": self.time,
            "schema_version": self.schema_version,
        }


@dataclass
class ErrorStats(BaseModel):
    """错题统计模型"""
    user_id: str
    total_errors: int = 0
    by_chapter: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    by_difficulty: Dict[str, int] = field(default_factory=dict)
    repeat_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "total_errors": self.total_errors,
            "by_chapter": self.by_chapter,
            "by_type": self.by_type,
            "by_difficulty": self.by_difficulty,
            "repeat_rate": self.repeat_rate,
            "schema_version": self.schema_version,
        }


# ──────────────────────────────────────────────────────────
# AI 推理相关模型（带 Schema）
# ──────────────────────────────────────────────────────────

@dataclass
class ReasoningStep(BaseModel):
    """推理步骤模型"""
    step_id: str
    operation: str
    input_state: Optional[str] = None
    output: Optional[str] = None
    goal: Optional[str] = None
    strategy: Optional[str] = None
    reasoning: Optional[str] = None
    weight: float = 1.0
    is_critical: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "operation": self.operation,
            "input_state": self.input_state,
            "output": self.output,
            "goal": self.goal,
            "strategy": self.strategy,
            "reasoning": self.reasoning,
            "weight": self.weight,
            "is_critical": self.is_critical,
            "schema_version": self.schema_version,
        }


@dataclass
class ReasoningChain(BaseModel):
    """推理链模型"""
    chain_id: str
    user_id: str
    question_id: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "steps": [s.to_dict() for s in self.steps],
            "final_answer": self.final_answer,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }


@dataclass
class GradingResult(BaseModel):
    """批改结果模型"""
    grading_id: str
    user_id: str
    question_id: str
    student_answer: str
    score: int
    max_score: int
    is_correct: bool = False
    method_matched: Optional[str] = None
    step_analysis: List[Dict[str, Any]] = field(default_factory=list)
    error_propagation: List[str] = field(default_factory=list)
    confidence: float = 0.0
    engine: str = "unknown"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "grading_id": self.grading_id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "student_answer": self.student_answer,
            "score": self.score,
            "max_score": self.max_score,
            "is_correct": self.is_correct,
            "method_matched": self.method_matched,
            "step_analysis": self.step_analysis,
            "error_propagation": self.error_propagation,
            "confidence": self.confidence,
            "engine": self.engine,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }


@dataclass
class DiagnosisResult(BaseModel):
    """诊断结果模型"""
    diagnosis_id: str
    user_id: str
    question_id: str
    error_type: str
    root_cause: Optional[str] = None
    knowledge_points: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    is_repeat: bool = False
    repeat_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "error_type": self.error_type,
            "root_cause": self.root_cause,
            "knowledge_points": self.knowledge_points,
            "common_mistakes": self.common_mistakes,
            "recommendations": self.recommendations,
            "is_repeat": self.is_repeat,
            "repeat_count": self.repeat_count,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }


@dataclass
class ASTNode(BaseModel):
    """AST 节点模型"""
    node_id: str
    node_type: str
    value: Optional[str] = None
    children: List["ASTNode"] = field(default_factory=list)
    position: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "value": self.value,
            "children": [c.to_dict() for c in self.children],
            "position": self.position,
            "schema_version": self.schema_version,
        }


@dataclass
class MathAST(BaseModel):
    """数学 AST 模型"""
    ast_id: str
    user_id: str
    expression: str
    root: Optional[ASTNode] = None
    normalized_form: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ast_id": self.ast_id,
            "user_id": self.user_id,
            "expression": self.expression,
            "root": self.root.to_dict() if self.root else None,
            "normalized_form": self.normalized_form,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }


# ──────────────────────────────────────────────────────────
# 仪表盘数据模型
# ──────────────────────────────────────────────────────────

@dataclass
class DashboardData(BaseModel):
    """仪表盘数据模型"""
    user_id: str
    total_questions: int = 0
    total_errors: int = 0
    overall_accuracy: float = 0.0
    current_level: str = "强化阶段"
    streak_days: int = 0
    last_study_date: Optional[str] = None
    weak_points: List[str] = field(default_factory=list)
    recent_errors: List[ErrorRecord] = field(default_factory=list)
    chapter_stats: Dict[str, float] = field(default_factory=dict)
    error_type_dist: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "total_questions": self.total_questions,
            "total_errors": self.total_errors,
            "overall_accuracy": self.overall_accuracy,
            "current_level": self.current_level,
            "streak_days": self.streak_days,
            "last_study_date": self.last_study_date,
            "weak_points": self.weak_points,
            "recent_errors": [e.to_dict() for e in self.recent_errors],
            "chapter_stats": self.chapter_stats,
            "error_type_dist": self.error_type_dist,
            "schema_version": self.schema_version,
        }


# ──────────────────────────────────────────────────────────
# 知识图谱模型
# ──────────────────────────────────────────────────────────

@dataclass
class KnowledgeNode(BaseModel):
    """知识点节点模型"""
    node_id: str
    name: str
    subject: str
    chapter: str
    description: Optional[str] = None
    difficulty: float = 0.0
    mastered: bool = False
    mastery_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "subject": self.subject,
            "chapter": self.chapter,
            "description": self.description,
            "difficulty": self.difficulty,
            "mastered": self.mastered,
            "mastery_score": self.mastery_score,
            "schema_version": self.schema_version,
        }


@dataclass
class KnowledgeEdge(BaseModel):
    """知识点关联模型"""
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation_type: str  # "prerequisite", "related", "subtopic"
    weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "schema_version": self.schema_version,
        }


@dataclass
class KnowledgeGraph(BaseModel):
    """知识图谱模型"""
    graph_id: str
    user_id: str
    nodes: List[KnowledgeNode] = field(default_factory=list)
    edges: List[KnowledgeEdge] = field(default_factory=list)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "user_id": self.user_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "updated_at": self.updated_at.isoformat(),
            "schema_version": self.schema_version,
        }


# ──────────────────────────────────────────────────────────
# 数据回放模型（用于AI调试）
# ──────────────────────────────────────────────────────────

@dataclass
class OCRResult(BaseModel):
    """OCR识别结果模型"""
    ocr_id: str
    image_path: Optional[str] = None
    raw_text: Optional[str] = None
    latex_text: Optional[str] = None
    confidence: float = 0.0
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ocr_id": self.ocr_id,
            "image_path": self.image_path,
            "raw_text": self.raw_text,
            "latex_text": self.latex_text,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }


@dataclass
class ASTNode(BaseModel):
    """AST节点模型"""
    node_id: str
    node_type: str
    value: Optional[str] = None
    children: List[str] = field(default_factory=list)
    position: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "value": self.value,
            "children": self.children,
            "position": self.position,
            "schema_version": self.schema_version,
        }


@dataclass
class MathAST(BaseModel):
    """数学AST模型"""
    ast_id: str
    latex_source: str
    nodes: List[ASTNode] = field(default_factory=list)
    root_node_id: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ast_id": self.ast_id,
            "latex_source": self.latex_source,
            "nodes": [n.to_dict() for n in self.nodes],
            "root_node_id": self.root_node_id,
            "validation_errors": self.validation_errors,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }


# ──────────────────────────────────────────────────────────
# 题库模型
# ──────────────────────────────────────────────────────────

@dataclass
class Question(BaseModel):
    """题目模型"""
    question_id: str
    year: int
    category: str
    volume: Optional[str] = None
    question_type: str = "选择题"  # 选择题、填空题、解答题
    question_no: int = 0
    score: int = 5
    difficulty: str = "中等"  # 简单、中等、困难
    knowledge_points: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    question: str = ""
    source: Optional[str] = None
    options: Dict[str, str] = field(default_factory=dict)  # {"A": "...", "B": "..."}
    correct_option: Optional[str] = None
    answer: Optional[str] = None  # 解答题答案
    analysis: Optional[str] = None  # 解析
    ocr_raw: Optional[str] = None  # OCR原始文本
    ocr_fixed: Optional[str] = None  # 修复后文本
    is_valid: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "year": self.year,
            "category": self.category,
            "volume": self.volume,
            "question_type": self.question_type,
            "question_no": self.question_no,
            "score": self.score,
            "difficulty": self.difficulty,
            "knowledge_points": self.knowledge_points,
            "tags": self.tags,
            "question": self.question,
            "source": self.source,
            "options": self.options,
            "correct_option": self.correct_option,
            "answer": self.answer,
            "analysis": self.analysis,
            "ocr_raw": self.ocr_raw,
            "ocr_fixed": self.ocr_fixed,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "schema_version": self.schema_version,
        }


@dataclass
class GradingSession(BaseModel):
    """批改会话模型 - 用于数据回放"""
    session_id: str
    user_id: str
    question_id: str
    original_image_path: Optional[str] = None
    
    # OCR阶段
    ocr_result: Optional[OCRResult] = None
    
    # AST阶段
    student_ast: Optional[MathAST] = None
    correct_ast: Optional[MathAST] = None
    
    # 推理链
    reasoning_chain: Optional[ReasoningChain] = None
    
    # 批改结果
    grading_result: Optional[GradingResult] = None
    
    # 诊断结果
    diagnosis_result: Optional[DiagnosisResult] = None
    
    # 元数据
    status: str = "pending"  # pending, processing, completed, error
    total_time: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "original_image_path": self.original_image_path,
            "ocr_result": self.ocr_result.to_dict() if self.ocr_result else None,
            "student_ast": self.student_ast.to_dict() if self.student_ast else None,
            "correct_ast": self.correct_ast.to_dict() if self.correct_ast else None,
            "reasoning_chain": self.reasoning_chain.to_dict() if self.reasoning_chain else None,
            "grading_result": self.grading_result.to_dict() if self.grading_result else None,
            "diagnosis_result": self.diagnosis_result.to_dict() if self.diagnosis_result else None,
            "status": self.status,
            "total_time": self.total_time,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "schema_version": self.schema_version,
        }
