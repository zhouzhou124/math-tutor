"""
Proof Planner

证明规划器 - 基于问题语义结构和推理算子生成证明计划。

核心设计：
  1. 接收 ProblemSchema 作为输入
  2. 搜索适用的推理算子
  3. 构建证明树
  4. 生成推理路径

搜索策略：
  - 正向推理：从已知条件出发，应用算子推导新结论
  - 反向推理：从目标出发，分解为子目标
  - 启发式搜索：根据算子成本和相关性排序
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union
from queue import PriorityQueue

# 导入推理算子
from .operators import (
    ReasoningOperator, ReasoningState, ReasoningStep, OperatorStatus,
    parse_problem_to_state
)
from .operators.monotonicity import MonotonicityOperator
from .operators.invertibility import InvertibilityOperator
from .operators.continuity import ContinuityOperator
from .operators.contradiction import ContradictionOperator
from .operators.counterexample import CounterexampleOperator


class SearchStrategy(Enum):
    """搜索策略"""
    FORWARD = auto()     # 正向推理
    BACKWARD = auto()    # 反向推理
    HYBRID = auto()      # 混合策略


class ProofNode:
    """
    证明树节点 - 表示证明过程中的一个状态。
    """
    
    def __init__(self, state: ReasoningState, step: Optional[ReasoningStep] = None, 
                 parent: Optional['ProofNode'] = None, cost: float = 0.0):
        self.state = state
        self.step = step
        self.parent = parent
        self.children: List['ProofNode'] = []
        self.cost = cost
        self.depth = parent.depth + 1 if parent else 0
    
    def add_child(self, child: 'ProofNode'):
        """添加子节点"""
        self.children.append(child)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'state': self.state.to_dict(),
            'step': self.step.to_dict() if self.step else None,
            'cost': self.cost,
            'depth': self.depth,
            'children': [child.to_dict() for child in self.children],
        }


@dataclass(frozen=True)
class ProofPlan:
    """
    证明计划 - 包含完整的证明路径和推理步骤。
    """
    root: ProofNode
    operators: List[ReasoningOperator]
    steps: List[ReasoningStep]
    success: bool
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'root': self.root.to_dict(),
            'steps': [step.to_dict() for step in self.steps],
            'success': self.success,
            'confidence': self.confidence,
        }


class ProofPlanner:
    """
    证明规划器 - 核心推理引擎。
    
    主要功能：
      1. 初始化推理状态
      2. 搜索适用算子
      3. 构建证明树
      4. 提取证明路径
    """
    
    def __init__(self):
        # 注册所有算子
        self.operators: List[ReasoningOperator] = [
            MonotonicityOperator(),
            InvertibilityOperator(),
            ContinuityOperator(),
            ContradictionOperator(),
            CounterexampleOperator(),
        ]
    
    def plan(self, problem_text: str, 
             strategy: SearchStrategy = SearchStrategy.FORWARD,
             max_depth: int = 5,
             timeout: int = 30) -> ProofPlan:
        """
        生成证明计划。
        
        Args:
            problem_text: 题目文本
            strategy: 搜索策略
            max_depth: 最大搜索深度
            timeout: 超时时间（秒）
        
        Returns:
            ProofPlan: 证明计划
        """
        # 初始化状态
        initial_state = parse_problem_to_state(problem_text)
        
        # 设置目标（如果题目包含"证明"、"判断"等）
        if '证明' in problem_text or '判断' in problem_text:
            initial_state.add_goal(problem_text)
        
        # 根据策略执行搜索
        if strategy == SearchStrategy.FORWARD:
            root = self._forward_search(initial_state, max_depth)
        elif strategy == SearchStrategy.BACKWARD:
            root = self._backward_search(initial_state, max_depth)
        else:
            root = self._hybrid_search(initial_state, max_depth)
        
        # 提取证明步骤
        steps = self._extract_steps(root)
        
        # 判断是否成功
        success = self._is_proof_complete(root.state)
        
        # 计算置信度
        confidence = self._calculate_confidence(root, steps)
        
        return ProofPlan(
            root=root,
            operators=self.operators,
            steps=steps,
            success=success,
            confidence=confidence,
        )
    
    def _forward_search(self, initial_state: ReasoningState, max_depth: int) -> ProofNode:
        """
        正向搜索 - 从已知条件出发推导结论。
        
        使用优先队列进行启发式搜索。
        """
        root = ProofNode(initial_state)
        queue = PriorityQueue()
        queue.put((0.0, root))
        
        visited = set()
        
        while not queue.empty():
            current_cost, node = queue.get()
            
            # 检查深度限制
            if node.depth >= max_depth:
                continue
            
            # 检查是否已访问
            state_key = tuple(sorted(node.state.knowns))
            if state_key in visited:
                continue
            visited.add(state_key)
            
            # 应用所有适用的算子
            for operator in self.operators:
                applicable, reason = operator.applicable(node.state)
                if applicable:
                    new_state, step = operator.apply(node.state)
                    
                    if step.status == OperatorStatus.SUCCESS:
                        child_cost = current_cost + operator.cost(node.state)
                        child = ProofNode(new_state, step, node, child_cost)
                        node.add_child(child)
                        
                        # 检查是否达到目标
                        if self._is_proof_complete(new_state):
                            return child
                        
                        queue.put((child_cost, child))
        
        return root
    
    def _backward_search(self, initial_state: ReasoningState, max_depth: int) -> ProofNode:
        """
        反向搜索 - 从目标出发分解为子目标。
        """
        root = ProofNode(initial_state)
        return self._backward_search_recursive(root, max_depth)
    
    def _backward_search_recursive(self, node: ProofNode, max_depth: int) -> ProofNode:
        """反向搜索递归实现"""
        if node.depth >= max_depth:
            return node
        
        # 如果有目标，尝试分解
        if node.state.goals:
            goal = node.state.goals[0]
            
            for operator in self.operators:
                # 检查算子是否有助于实现目标
                applicable, reason = operator.applicable(node.state)
                if applicable:
                    new_state, step = operator.apply(node.state)
                    
                    if step.status == OperatorStatus.SUCCESS:
                        child = ProofNode(new_state, step, node)
                        node.add_child(child)
                        
                        # 递归搜索
                        result = self._backward_search_recursive(child, max_depth)
                        if self._is_proof_complete(result.state):
                            return result
        
        return node
    
    def _hybrid_search(self, initial_state: ReasoningState, max_depth: int) -> ProofNode:
        """
        混合搜索 - 结合正向和反向推理。
        """
        # 先进行正向推理
        forward_root = self._forward_search(initial_state, max_depth // 2)
        
        # 如果还没完成，进行反向推理
        if not self._is_proof_complete(forward_root.state):
            return self._backward_search_recursive(forward_root, max_depth // 2)
        
        return forward_root
    
    def _is_proof_complete(self, state: ReasoningState) -> bool:
        """
        判断证明是否完成。
        
        完成条件：
          1. 所有目标都已证明
          2. 推导得出了关键结论
        """
        # 检查目标是否为空或已满足
        if not state.goals:
            return True
        
        # 检查是否有"矛盾"、"反例"等结论（对于反证法或反例题）
        has_contradiction = any('矛盾' in known for known in state.knowns)
        has_counterexample = any('反例' in known for known in state.knowns)
        has_conclusion = any('因此' in known or '综上' in known for known in state.knowns)
        
        return has_contradiction or has_counterexample or has_conclusion
    
    def _extract_steps(self, root: ProofNode) -> List[ReasoningStep]:
        """
        从证明树中提取推理步骤。
        """
        steps = []
        
        def collect_steps(node: ProofNode):
            if node.step:
                steps.append(node.step)
            for child in node.children:
                collect_steps(child)
        
        collect_steps(root)
        return steps
    
    def _calculate_confidence(self, root: ProofNode, steps: List[ReasoningStep]) -> float:
        """
        计算证明置信度。
        """
        if not steps:
            return 0.0
        
        # 基础置信度
        confidence = 0.5
        
        # 根据成功步骤数量增加
        success_steps = sum(1 for step in steps if step.status == OperatorStatus.SUCCESS)
        confidence += success_steps * 0.1
        
        # 根据深度调整
        if root.depth <= 2:
            confidence += 0.1
        elif root.depth >= 4:
            confidence -= 0.1
        
        # 根据算子应用情况调整
        applied_ops = set(root.state.applied_operators)
        if 'invertibility' in applied_ops:
            confidence += 0.1
        if 'monotonicity' in applied_ops:
            confidence += 0.1
        
        return min(1.0, max(0.0, confidence))
    
    def get_operator_by_name(self, name: str) -> Optional[ReasoningOperator]:
        """根据名称获取算子"""
        for op in self.operators:
            if op.name == name:
                return op
        return None


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def plan_proof(problem_text: str) -> ProofPlan:
    """便捷函数：生成证明计划"""
    planner = ProofPlanner()
    return planner.plan(problem_text)


def execute_proof(problem_text: str) -> Dict[str, Any]:
    """执行证明并返回结果"""
    plan = plan_proof(problem_text)
    
    result = {
        'success': plan.success,
        'confidence': plan.confidence,
        'steps': [],
        'knowns': [],
    }
    
    for step in plan.steps:
        result['steps'].append({
            'operator': step.operator_name,
            'conclusion': step.conclusion,
            'explanation': step.explanation,
            'status': step.status.name,
        })
    
    result['knowns'] = plan.root.state.knowns
    
    return result


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        """设数列{x_n}满足 -\\frac{\\pi}{2}\\le x_n\\le \\frac{\\pi}{2}，
        判断：若 lim cos(sin x_n) 存在，则 lim x_n 是否存在？""",
        
        """设数列{x_n}满足 -\\frac{\\pi}{2}\\le x_n\\le \\frac{\\pi}{2}，
        判断：若 lim sin(cos x_n) 存在，则 lim x_n 是否存在？""",
    ]
    
    for i, problem in enumerate(test_cases):
        print(f"=== Test Case {i+1} ===")
        print(f"题目：{problem[:50]}...")
        result = execute_proof(problem)
        
        print(f"成功: {result['success']}")
        print(f"置信度: {result['confidence']:.2f}")
        print("推理步骤:")
        for j, step in enumerate(result['steps']):
            print(f"  {j+1}. [{step['operator']}] {step['explanation']}")
        
        print("已知结论:")
        for known in result['knowns'][-3:]:  # 只显示最后3个
            print(f"  - {known}")
        
        print()
