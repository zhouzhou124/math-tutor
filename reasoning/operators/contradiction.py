"""
Contradiction Operator

反证法算子 - 处理反证法推理。

数学原理：
  反证法（归谬法）是一种间接证明方法：
  1. 假设命题的否定成立
  2. 从这个假设出发，推导出矛盾
  3. 因此原命题成立
  
  形式化：
    要证明 P，假设 ¬P
    若 ¬P ⇒ Q 且 ¬Q（矛盾）
    则 P 成立
"""

from typing import Tuple, List, Optional
from . import ReasoningOperator, ReasoningState, ReasoningStep, OperatorStatus


class ContradictionOperator(ReasoningOperator):
    """
    反证法算子 - 应用反证法进行推理。
    
    核心功能：
      1. 识别适合反证法的问题
      2. 构造假设
      3. 推导矛盾
      4. 得出结论
    """
    
    @property
    def name(self) -> str:
        return "contradiction"
    
    @property
    def description(self) -> str:
        return "应用反证法，通过推导矛盾证明命题"
    
    def applicable(self, state: ReasoningState) -> Tuple[bool, str]:
        """
        判断是否适用反证法。
        
        适用条件：
          1. 目标是证明某个命题成立
          2. 命题涉及"不存在"、"不可能"、"唯一"等
          3. 直接证明困难
        """
        has_goal = len(state.goals) > 0
        
        # 检测反证法适用的关键词
        contradiction_keywords = [
            '不存在', '不可能', '唯一', '至多', '至少',
            '不能', '无法', '不可能', '必定', '一定'
        ]
        
        has_keyword = any(keyword in ' '.join(state.goals + state.knowns) 
                         for keyword in contradiction_keywords)
        
        if has_goal and has_keyword:
            return True, "检测到适合反证法的目标"
        elif has_goal:
            return True, "有证明目标，可尝试反证法"
        else:
            return False, "没有证明目标"
    
    def apply(self, state: ReasoningState) -> Tuple[ReasoningState, ReasoningStep]:
        """
        应用反证法算子。
        
        推理流程：
          1. 提取目标命题
          2. 构造否定假设
          3. 推导矛盾
          4. 得出结论
        """
        new_state = state.clone()
        step = ReasoningStep(
            operator_name=self.name,
            conclusion="",
            premises=[],
            explanation=""
        )
        
        # 提取目标
        if state.goals:
            goal = state.goals[0]
            step.premises.append(f"目标：{goal}")
            
            # 构造否定假设
            negation = self._construct_negation(goal)
            if negation:
                new_state.add_assumption(negation)
                step.premises.append(f"假设：{negation}")
                step.explanation += f"采用反证法，假设 {negation}。"
                
                # 推导矛盾
                contradiction = self._derive_contradiction(new_state)
                if contradiction:
                    new_state.add_known(f"矛盾：{contradiction}")
                    step.conclusion = f"推出矛盾，因此原命题成立：{goal}"
                    step.explanation += f"从假设出发，推出矛盾：{contradiction}。因此原命题成立。"
                else:
                    step.status = OperatorStatus.PARTIAL
                    step.explanation += "需进一步推导矛盾。"
            else:
                step.status = OperatorStatus.FAILED
                step.explanation = "无法构造否定假设"
        else:
            step.status = OperatorStatus.FAILED
            step.explanation = "没有证明目标"
        
        if step.status == OperatorStatus.FAILED:
            pass
        else:
            new_state.mark_operator_applied(self.name)
        
        return new_state, step
    
    def _construct_negation(self, proposition: str) -> Optional[str]:
        """
        构造命题的否定。
        
        简单规则：
          - "存在" → "不存在"
          - "成立" → "不成立"
          - "有" → "没有"
          - "能" → "不能"
        """
        negation_map = {
            '存在': '不存在',
            '成立': '不成立',
            '有': '没有',
            '能': '不能',
            '是': '不是',
            '可以': '不可以',
            '一定': '不一定',
            '必定': '不必定',
        }
        
        for keyword, negation in negation_map.items():
            if keyword in proposition:
                return proposition.replace(keyword, negation, 1)
        
        # 默认在前面加"并非"
        return f"并非 {proposition}"
    
    def _derive_contradiction(self, state: ReasoningState) -> Optional[str]:
        """
        从当前状态推导矛盾。
        
        检查已知条件和假设是否矛盾。
        """
        # 简单检查：假设与已知条件是否冲突
        for assumption in state.assumptions:
            for known in state.knowns:
                # 检查直接矛盾
                if self._is_contradiction(assumption, known):
                    return f"{assumption} 与 {known} 矛盾"
        
        return None
    
    def _is_contradiction(self, statement1: str, statement2: str) -> bool:
        """
        判断两个陈述是否矛盾。
        
        简单规则：检查是否有直接对立的关键词。
        """
        contradiction_pairs = [
            ('存在', '不存在'),
            ('成立', '不成立'),
            ('有', '没有'),
            ('能', '不能'),
            ('>', '<='),
            ('<', '>='),
            ('=', '≠'),
        ]
        
        for pos, neg in contradiction_pairs:
            has_pos = pos in statement1 and neg in statement2
            has_neg = neg in statement1 and pos in statement2
            if has_pos or has_neg:
                return True
        
        return False
    
    def cost(self, state: ReasoningState) -> float:
        """反证法成本较高，优先级较低"""
        return 2.0
