"""
Reasoning Operator Base Class

推理算子是数学语义变换的基本单元，每个算子代表一种数学推理规则或定理应用。

核心设计理念：
  - 算子是纯函数，接受状态并返回新状态
  - 算子可以组合形成证明树
  - 算子有适用条件和前置条件
  - 算子产生可验证的推理步骤
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


class OperatorStatus(Enum):
    """算子应用状态"""
    SUCCESS = auto()
    FAILED = auto()
    PENDING = auto()
    PARTIAL = auto()


class ReasoningState:
    """
    推理状态 — 表示推理过程中的数学知识状态。
    
    包含：
      - 已知条件 (knowns)
      - 待证目标 (goals)
      - 已应用算子 (applied_operators)
      - 假设 (assumptions)
      - 约束 (constraints)
    """
    
    def __init__(self):
        self.knowns: List[str] = []        # 已知事实
        self.goals: List[str] = []          # 待证目标
        self.assumptions: List[str] = []    # 当前假设
        self.constraints: List[str] = []    # 约束条件
        self.applied_operators: List[str] = []  # 已应用的算子
        self.metadata: Dict[str, Any] = {}  # 元数据
    
    def add_known(self, fact: str):
        """添加已知事实"""
        if fact not in self.knowns:
            self.knowns.append(fact)
    
    def add_goal(self, goal: str):
        """添加待证目标"""
        if goal not in self.goals:
            self.goals.append(goal)
    
    def add_assumption(self, assumption: str):
        """添加假设"""
        if assumption not in self.assumptions:
            self.assumptions.append(assumption)
    
    def add_constraint(self, constraint: str):
        """添加约束"""
        if constraint not in self.constraints:
            self.constraints.append(constraint)
    
    def mark_operator_applied(self, operator_name: str):
        """标记算子已应用"""
        if operator_name not in self.applied_operators:
            self.applied_operators.append(operator_name)
    
    def clone(self) -> 'ReasoningState':
        """复制状态"""
        new_state = ReasoningState()
        new_state.knowns = list(self.knowns)
        new_state.goals = list(self.goals)
        new_state.assumptions = list(self.assumptions)
        new_state.constraints = list(self.constraints)
        new_state.applied_operators = list(self.applied_operators)
        new_state.metadata = dict(self.metadata)
        return new_state
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'knowns': self.knowns,
            'goals': self.goals,
            'assumptions': self.assumptions,
            'constraints': self.constraints,
            'applied_operators': self.applied_operators,
            'metadata': self.metadata,
        }


class ReasoningStep:
    """
    推理步骤 — 记录单次算子应用的结果。
    """
    
    def __init__(self, operator_name: str, conclusion: str, 
                 premises: List[str] = None, explanation: str = ""):
        self.operator_name = operator_name
        self.conclusion = conclusion
        self.premises = premises or []
        self.explanation = explanation
        self.status = OperatorStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operator_name': self.operator_name,
            'conclusion': self.conclusion,
            'premises': self.premises,
            'explanation': self.explanation,
            'status': self.status.name,
        }


class ReasoningOperator(ABC):
    """
    推理算子基类 — 所有数学推理算子的抽象基类。
    
    每个算子实现：
      1. applicable() - 判断是否适用于当前状态
      2. apply() - 应用算子，返回新状态和推理步骤
      3. cost() - 估算应用成本
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """算子名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """算子描述"""
        pass
    
    @abstractmethod
    def applicable(self, state: ReasoningState) -> Tuple[bool, str]:
        """
        判断算子是否适用于当前状态。
        
        Returns:
            (是否适用, 理由)
        """
        pass
    
    @abstractmethod
    def apply(self, state: ReasoningState) -> Tuple[ReasoningState, ReasoningStep]:
        """
        应用算子，执行推理变换。
        
        Returns:
            (新状态, 推理步骤)
        """
        pass
    
    def cost(self, state: ReasoningState) -> float:
        """
        估算算子应用成本（用于搜索排序）。
        
        Returns:
            成本值（越小越优先）
        """
        return 1.0
    
    def __repr__(self) -> str:
        return f"<{self.name}: {self.description}>"


@dataclass(frozen=True)
class OperatorResult:
    """算子应用结果"""
    state: ReasoningState
    step: ReasoningStep
    status: OperatorStatus
    cost: float = 0.0


# ──────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────

def create_initial_state(problem_text: str, constraints: List[str] = None) -> ReasoningState:
    """
    从题目文本创建初始推理状态。
    
    Args:
        problem_text: 题目文本
        constraints: 约束条件列表
    
    Returns:
        ReasoningState: 初始状态
    """
    state = ReasoningState()
    state.add_known(problem_text)
    
    if constraints:
        for constraint in constraints:
            state.add_constraint(constraint)
    
    return state


def parse_problem_to_state(problem_text: str) -> ReasoningState:
    """
    将题目文本解析为推理状态（便捷函数）。
    """
    try:
        from problem_semantics import parse_problem
        schema = parse_problem(problem_text)
        
        state = ReasoningState()
        state.add_known(problem_text)
        
        for constraint in schema.constraints:
            state.add_constraint(constraint)
        
        # 设置元数据
        state.metadata['question_type'] = schema.question_type.name
        state.metadata['topics'] = [t.name for t in schema.topics]
        state.metadata['confidence'] = schema.confidence
        
        return state
    except ImportError:
        return create_initial_state(problem_text)
