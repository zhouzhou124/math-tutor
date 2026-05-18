"""
Continuity Operator

连续性算子 - 处理函数连续性相关的推理。

数学原理：
  1. 若 f 在 x0 处连续，则 lim_{x→x0} f(x) = f(x0)
  2. 连续函数的复合函数仍连续
  3. 若 f 连续且 lim x_n = L，则 lim f(x_n) = f(L)
  4. 闭区间上的连续函数有最大值和最小值（极值定理）
  5. 连续函数将连通集映射为连通集（中间值定理）
"""

from typing import Tuple, List, Optional
from . import ReasoningOperator, ReasoningState, ReasoningStep, OperatorStatus


class ContinuityOperator(ReasoningOperator):
    """
    连续性算子 - 分析函数连续性及其推论。
    
    核心功能：
      1. 判断函数连续性
      2. 应用连续函数性质
      3. 推导极限与连续性的关系
    """
    
    @property
    def name(self) -> str:
        return "continuity"
    
    @property
    def description(self) -> str:
        return "分析函数连续性，应用连续函数性质"
    
    def applicable(self, state: ReasoningState) -> Tuple[bool, str]:
        """
        判断是否适用连续性分析。
        
        适用条件：
          1. 状态中包含连续相关关键词
          2. 状态中包含极限表达式
          3. 状态中包含函数表达式
        """
        has_continuity = any(keyword in ' '.join(state.knowns).lower() 
                           for keyword in ['连续', 'continuity', '连续函数'])
        has_limit = any('lim' in known.lower() for known in state.knowns)
        has_function = any(keyword in ' '.join(state.knowns).lower() 
                          for keyword in ['sin', 'cos', 'tan', 'f(', 'g('])
        
        if has_continuity or (has_limit and has_function):
            return True, "检测到连续性相关内容或极限与函数"
        else:
            return False, "缺少连续性相关信息"
    
    def apply(self, state: ReasoningState) -> Tuple[ReasoningState, ReasoningStep]:
        """
        应用连续性算子。
        
        推理流程：
          1. 识别连续函数
          2. 应用连续函数性质
          3. 推导极限与函数值的关系
        """
        new_state = state.clone()
        step = ReasoningStep(
            operator_name=self.name,
            conclusion="",
            premises=[],
            explanation=""
        )
        
        all_text = ' '.join(state.knowns + state.constraints)
        
        # 识别基本连续函数
        basic_functions = self._identify_continuous_functions(all_text)
        if basic_functions:
            for func_name in basic_functions:
                conclusion = f"{func_name} 是基本初等函数，在其定义域内连续"
                new_state.add_known(conclusion)
                step.premises.append(conclusion)
                step.explanation += conclusion + "。"
        
        # 分析复合函数连续性
        composite_conclusion = self._analyze_composite_continuity(all_text)
        if composite_conclusion:
            new_state.add_known(composite_conclusion)
            step.premises.append("复合函数连续性")
            step.conclusion += composite_conclusion + "; "
            step.explanation += composite_conclusion + "。"
        
        # 应用极限与连续性的关系
        limit_conclusion = self._apply_limit_continuity(state)
        if limit_conclusion:
            new_state.add_known(limit_conclusion)
            step.conclusion += limit_conclusion
            step.explanation += limit_conclusion + "。"
        
        if step.conclusion or step.explanation:
            step.status = OperatorStatus.SUCCESS
            new_state.mark_operator_applied(self.name)
        else:
            step.status = OperatorStatus.FAILED
            step.explanation = "未能应用连续性分析"
        
        return new_state, step
    
    def _identify_continuous_functions(self, text: str) -> List[str]:
        """
        识别基本连续函数。
        """
        continuous_funcs = []
        
        if 'sin' in text.lower():
            continuous_funcs.append('sin(x)')
        if 'cos' in text.lower():
            continuous_funcs.append('cos(x)')
        if 'tan' in text.lower():
            continuous_funcs.append('tan(x)')
        if 'exp' in text.lower() or 'e^' in text:
            continuous_funcs.append('e^x')
        if 'log' in text.lower():
            continuous_funcs.append('log(x)')
        if 'sqrt' in text.lower():
            continuous_funcs.append('sqrt(x)')
        
        return continuous_funcs
    
    def _analyze_composite_continuity(self, text: str) -> Optional[str]:
        """
        分析复合函数的连续性。
        
        规则：连续函数的复合函数仍连续。
        """
        patterns = [
            (r'cos\(sin', "cos(sin(x))"),
            (r'sin\(cos', "sin(cos(x))"),
            (r'f\(g\(', "f(g(x))"),
            (r'g\(f\(', "g(f(x))"),
        ]
        
        for pattern, func_name in patterns:
            if pattern in text.lower():
                return f"复合函数 {func_name} 由连续函数复合而成，因此连续"
        
        return None
    
    def _apply_limit_continuity(self, state: ReasoningState) -> Optional[str]:
        """
        应用极限与连续性的关系。
        
        规则：若 f 连续且 lim x_n = L，则 lim f(x_n) = f(L)
        """
        has_limit = any('lim' in known.lower() for known in state.knowns)
        has_continuous = any('连续' in known for known in state.knowns)
        
        if has_limit and has_continuous:
            return "若 f 连续且 lim x_n = L，则 lim f(x_n) = f(L)"
        
        return None
    
    def cost(self, state: ReasoningState) -> float:
        """连续性分析成本较低"""
        return 0.4
