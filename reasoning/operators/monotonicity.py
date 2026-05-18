"""
Monotonicity Operator

单调性算子 - 处理函数单调性相关的推理。

数学原理：
  1. 若 f 在区间 I 上严格单调递增，则 f(x1) < f(x2) 当且仅当 x1 < x2
  2. 若 f 在区间 I 上严格单调递减，则 f(x1) < f(x2) 当且仅当 x1 > x2
  3. 严格单调函数是单射（injective）
  4. 连续且严格单调的函数在其值域上可逆
"""

from typing import Tuple, List, Optional
from . import ReasoningOperator, ReasoningState, ReasoningStep, OperatorStatus


class MonotonicityOperator(ReasoningOperator):
    """
    单调性算子 - 检测和应用函数单调性。
    
    支持：
      - 三角函数单调性（sin, cos, tan 在特定区间）
      - 复合函数单调性
      - 单调性与极限存在性的关系
    """
    
    @property
    def name(self) -> str:
        return "monotonicity"
    
    @property
    def description(self) -> str:
        return "分析函数单调性，用于判断极限存在性和可逆性"
    
    def applicable(self, state: ReasoningState) -> Tuple[bool, str]:
        """
        判断是否适用单调性分析。
        
        适用条件：
          1. 状态中包含函数表达式（如 sin, cos, tan）
          2. 状态中包含区间约束
          3. 目标涉及极限存在性或函数可逆性
        """
        has_function = any(keyword in ' '.join(state.knowns + state.goals).lower() 
                          for keyword in ['sin', 'cos', 'tan', '函数', '单调'])
        has_interval = any(keyword in ' '.join(state.constraints) 
                          for keyword in ['∈', '[', ']', '(', ')', '≤', '≥'])
        
        if has_function and has_interval:
            return True, "检测到函数表达式和区间约束"
        elif has_function:
            return True, "检测到函数表达式"
        else:
            return False, "缺少函数表达式或区间约束"
    
    def apply(self, state: ReasoningState) -> Tuple[ReasoningState, ReasoningStep]:
        """
        应用单调性算子。
        
        主要推理：
          1. 识别函数类型（sin, cos, tan）
          2. 确定定义域区间
          3. 判断单调性
          4. 推导结论（可逆性、极限存在性）
        """
        new_state = state.clone()
        step = ReasoningStep(
            operator_name=self.name,
            conclusion="",
            premises=[],
            explanation=""
        )
        
        # 分析已知条件
        all_text = ' '.join(state.knowns + state.constraints)
        
        # 识别三角函数及其单调性
        trig_monotonicity = self._analyze_trig_monotonicity(all_text)
        
        if trig_monotonicity:
            for func_name, interval, is_increasing, conclusion in trig_monotonicity:
                new_state.add_known(conclusion)
                step.premises.append(f"{func_name} 在 {interval} 上的单调性")
                step.conclusion += conclusion + "; "
                step.explanation += f"根据 {func_name} 的单调性性质，{conclusion}。"
        
        # 分析复合函数单调性
        composite_conclusion = self._analyze_composite_monotonicity(all_text)
        if composite_conclusion:
            new_state.add_known(composite_conclusion)
            step.premises.append("复合函数单调性")
            step.conclusion += composite_conclusion + "; "
            step.explanation += f"复合函数单调性分析：{composite_conclusion}。"
        
        # 分析单调性与极限的关系
        limit_conclusion = self._analyze_limit_monotonicity(state)
        if limit_conclusion:
            new_state.add_known(limit_conclusion)
            step.premises.append("单调性与极限")
            step.conclusion += limit_conclusion + "; "
            step.explanation += f"单调性蕴含极限性质：{limit_conclusion}。"
        
        if step.conclusion:
            step.status = OperatorStatus.SUCCESS
            new_state.mark_operator_applied(self.name)
        else:
            step.status = OperatorStatus.FAILED
            step.explanation = "未能应用单调性分析"
        
        return new_state, step
    
    def _analyze_trig_monotonicity(self, text: str) -> List[Tuple[str, str, bool, str]]:
        """
        分析三角函数的单调性。
        
        Returns:
            [(函数名, 区间, 是否递增, 结论), ...]
        """
        results = []
        
        # sin 函数分析
        if 'sin' in text.lower():
            # sin 在 [-π/2, π/2] 上严格递增
            if any(s in text for s in ['-π/2', '-\\pi/2', '[-π/2', '[-\\pi/2']):
                results.append(('sin', '[-π/2, π/2]', True, 
                              'sin(x) 在 [-π/2, π/2] 上严格单调递增'))
            
        # cos 函数分析
        if 'cos' in text.lower():
            # cos 在 [0, π] 上严格递减
            if any(s in text for s in ['[0,', '[0,1]', '∈[0']):
                results.append(('cos', '[0, π]', False, 
                              'cos(x) 在 [0, π] 上严格单调递减'))
            # cos 在 [-π, 0] 上严格递增  
            if any(s in text for s in ['[-π,', '[-1,', '∈[-']):
                results.append(('cos', '[-π, 0]', True, 
                              'cos(x) 在 [-π, 0] 上严格单调递增'))
        
        # tan 函数分析
        if 'tan' in text.lower():
            if any(s in text for s in ['(-π/2', '(-\\pi/2']):
                results.append(('tan', '(-π/2, π/2)', True, 
                              'tan(x) 在 (-π/2, π/2) 上严格单调递增'))
        
        return results
    
    def _analyze_composite_monotonicity(self, text: str) -> Optional[str]:
        """
        分析复合函数的单调性。
        
        规则：
          - 增函数 ∘ 增函数 = 增函数
          - 增函数 ∘ 减函数 = 减函数
          - 减函数 ∘ 增函数 = 减函数
          - 减函数 ∘ 减函数 = 增函数
        """
        # 检测复合函数模式
        patterns = [
            (r'cos\(sin', "cos(sin(x))"),
            (r'sin\(cos', "sin(cos(x))"),
            (r'cos\(cos', "cos(cos(x))"),
            (r'sin\(sin', "sin(sin(x))"),
        ]
        
        for pattern, func_name in patterns:
            if pattern in text.lower():
                return f"复合函数 {func_name} 的单调性需根据内层和外层函数的单调性综合判断"
        
        return None
    
    def _analyze_limit_monotonicity(self, state: ReasoningState) -> Optional[str]:
        """
        分析单调性与极限存在性的关系。
        
        核心原理：
          若 f 严格单调且 lim f(x_n) 存在，
          且 f 的定义域包含所有 x_n，
          则 lim x_n 存在（当 f 可逆时）。
        """
        has_limit = any('lim' in known.lower() for known in state.knowns)
        has_monotonic = any('单调' in known for known in state.knowns)
        
        if has_limit and has_monotonic:
            return "严格单调函数的极限存在性蕴含原序列的极限存在性（可逆情况下）"
        
        return None
    
    def cost(self, state: ReasoningState) -> float:
        """单调性分析成本较低，优先级较高"""
        return 0.5
