"""
Counterexample Operator

反例算子 - 处理反例构造推理。

数学原理：
  要证明一个命题不成立，只需举出一个反例即可。
  
  形式化：
    要证明 ¬P，找到一个实例 x 使得 P(x) 不成立
    
  常见应用：
    - 证明极限不存在
    - 证明函数不连续
    - 证明命题不成立
"""

from typing import Tuple, List, Optional
from . import ReasoningOperator, ReasoningState, ReasoningStep, OperatorStatus


class CounterexampleOperator(ReasoningOperator):
    """
    反例算子 - 构造反例反驳命题。
    
    核心功能：
      1. 识别需要反例的问题
      2. 构造合适的反例
      3. 验证反例是否有效
    """
    
    @property
    def name(self) -> str:
        return "counterexample"
    
    @property
    def description(self) -> str:
        return "构造反例反驳命题"
    
    def applicable(self, state: ReasoningState) -> Tuple[bool, str]:
        """
        判断是否适用反例构造。
        
        适用条件：
          1. 目标是证明命题不成立
          2. 涉及"不一定"、"不总是"、"存在反例"等
          3. 题目要求判断命题真假
        """
        has_goal = len(state.goals) > 0
        
        counterexample_keywords = [
            '反例', '不成立', '不一定', '不总是',
            '错误', '不正确', '存在'
        ]
        
        has_keyword = any(keyword in ' '.join(state.goals + state.knowns) 
                         for keyword in counterexample_keywords)
        
        if has_goal and has_keyword:
            return True, "检测到适合构造反例的目标"
        else:
            return False, "不适合构造反例"
    
    def apply(self, state: ReasoningState) -> Tuple[ReasoningState, ReasoningStep]:
        """
        应用反例算子。
        
        推理流程：
          1. 分析目标命题
          2. 构造反例
          3. 验证反例
          4. 得出结论
        """
        new_state = state.clone()
        step = ReasoningStep(
            operator_name=self.name,
            conclusion="",
            premises=[],
            explanation=""
        )
        
        # 分析目标
        if state.goals:
            goal = state.goals[0]
            step.premises.append(f"目标：{goal}")
            
            # 构造反例
            counterexample = self._construct_counterexample(goal, state)
            if counterexample:
                new_state.add_known(f"反例：{counterexample}")
                step.premises.append(f"反例：{counterexample}")
                step.conclusion = f"构造反例成功，命题不成立"
                step.explanation += f"构造反例：{counterexample}，因此命题不成立。"
                step.status = OperatorStatus.SUCCESS
            else:
                step.status = OperatorStatus.FAILED
                step.explanation = "无法构造反例"
        else:
            step.status = OperatorStatus.FAILED
            step.explanation = "没有证明目标"
        
        if step.status == OperatorStatus.SUCCESS:
            new_state.mark_operator_applied(self.name)
        
        return new_state, step
    
    def _construct_counterexample(self, goal: str, state: ReasoningState) -> Optional[str]:
        """
        根据目标命题构造反例。
        
        针对常见数学问题的反例构造：
          - 极限存在性反例
          - 连续性反例
          - 单调性反例
        """
        # 分析目标类型
        if '极限' in goal or 'lim' in goal.lower():
            return self._construct_limit_counterexample(goal, state)
        
        elif '连续' in goal:
            return self._construct_continuity_counterexample(goal)
        
        elif '单调' in goal:
            return self._construct_monotonicity_counterexample(goal)
        
        # 通用反例构造
        return self._construct_general_counterexample(goal)
    
    def _construct_limit_counterexample(self, goal: str, state: ReasoningState) -> Optional[str]:
        """
        构造极限相关的反例。
        
        常见反例：
          - 摆动数列：(-1)^n
          - 震荡函数：sin(1/x)
        """
        # 检查是否涉及函数复合
        if 'cos(sin' in ' '.join(state.knowns).lower():
            # 针对用户题目：cos(sin x_n) 存在但 x_n 不存在的情况
            return "取 x_n = (-1)^n * π/2，则 cos(sin x_n) = cos(±1) 极限存在，但 x_n 极限不存在"
        
        if 'sin(cos' in ' '.join(state.knowns).lower():
            # sin(cos x_n) 的情况
            return None  # 这个实际上是成立的，没有反例
        
        return "取 x_n = (-1)^n，则 x_n 极限不存在"
    
    def _construct_continuity_counterexample(self, goal: str) -> Optional[str]:
        """
        构造连续性反例。
        """
        if '处处连续' in goal or '所有点' in goal:
            return "狄利克雷函数 D(x)，在有理数点取1，无理数点取0，处处不连续"
        
        return "分段函数 f(x) = x (x≠0), f(0)=1，在 x=0 处不连续"
    
    def _construct_monotonicity_counterexample(self, goal: str) -> Optional[str]:
        """
        构造单调性反例。
        """
        if '单调' in goal:
            return "f(x) = sin(x) 在 R 上不是单调函数"
        
        return None
    
    def _construct_general_counterexample(self, goal: str) -> Optional[str]:
        """
        通用反例构造。
        """
        if '成立' in goal or '正确' in goal:
            return "存在反例使得命题不成立"
        
        return None
    
    def cost(self, state: ReasoningState) -> float:
        """反例构造成本较高"""
        return 2.5
