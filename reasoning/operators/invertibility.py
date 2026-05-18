"""
Invertibility Operator

可逆性算子 - 处理函数可逆性相关的推理。

数学原理：
  1. 若 f: A → B 是双射，则 f 可逆
  2. 连续且严格单调的函数在其值域上可逆
  3. 若 f 可逆且 lim f(x_n) = L，则 lim x_n = f⁻¹(L)（当 f⁻¹ 在 L 处连续时）
  
  核心应用（针对用户题目）：
    若 lim cos(sin x_n) 存在，能否推出 lim x_n 存在？
    
    分析：
      1. x_n ∈ [-π/2, π/2] ⇒ sin x_n ∈ [-1, 1]
      2. cos 在 [-1, 1] 上不是单调的（在 [-1,0] 增，[0,1] 减）
      3. 因此 cos 在 [-1,1] 上不可逆
      4. 所以 lim cos(sin x_n) 存在不能推出 lim sin x_n 存在
      
      而对于 sin(cos x_n)：
      1. x_n ∈ [-π/2, π/2] ⇒ cos x_n ∈ [0, 1]
      2. sin 在 [0, 1] 上严格单调递增
      3. cos 在 [-π/2, π/2] 上严格单调递减
      4. 复合后 sin(cos x_n) 在 [-π/2, π/2] 上严格单调递减
      5. 因此可逆，极限存在可推出原序列极限存在
"""

from typing import Tuple, List, Optional
from . import ReasoningOperator, ReasoningState, ReasoningStep, OperatorStatus


class InvertibilityOperator(ReasoningOperator):
    """
    可逆性算子 - 分析函数可逆性及其对极限存在性的影响。
    
    核心功能：
      1. 判断函数在给定区间上是否可逆
      2. 推导极限存在性的传递关系
      3. 处理复合函数的可逆性
    """
    
    @property
    def name(self) -> str:
        return "invertibility"
    
    @property
    def description(self) -> str:
        return "分析函数可逆性，推导极限存在性的传递关系"
    
    def applicable(self, state: ReasoningState) -> Tuple[bool, str]:
        """
        判断是否适用可逆性分析。
        
        适用条件：
          1. 状态中包含极限表达式（lim）
          2. 状态中包含函数表达式（sin, cos, tan 等）
          3. 状态中包含区间约束
        """
        has_limit = any('lim' in known.lower() for known in state.knowns)
        has_function = any(keyword in ' '.join(state.knowns).lower() 
                          for keyword in ['sin', 'cos', 'tan', 'lim'])
        has_interval = any(keyword in ' '.join(state.constraints + state.knowns) 
                          for keyword in ['∈', '[', ']', '(', ')', '≤', '≥'])
        
        if has_limit and has_function:
            return True, "检测到极限表达式和函数"
        elif has_function and has_interval:
            return True, "检测到函数表达式和区间约束"
        else:
            return False, "缺少极限表达式或函数信息"
    
    def apply(self, state: ReasoningState) -> Tuple[ReasoningState, ReasoningStep]:
        """
        应用可逆性算子。
        
        推理流程：
          1. 提取函数链（复合函数结构）
          2. 分析每个函数在其定义域上的单调性
          3. 判断复合函数是否可逆
          4. 推导极限存在性的传递关系
        """
        new_state = state.clone()
        step = ReasoningStep(
            operator_name=self.name,
            conclusion="",
            premises=[],
            explanation=""
        )
        
        all_text = ' '.join(state.knowns + state.constraints)
        
        # 分析复合函数结构
        function_chain = self._extract_function_chain(all_text)
        if function_chain:
            step.premises.append(f"函数链: {' → '.join(function_chain)}")
            
            # 分析每个函数的可逆性
            invertibility_results = self._analyze_chain_invertibility(function_chain, all_text)
            
            if invertibility_results:
                for result in invertibility_results:
                    new_state.add_known(result)
                    step.conclusion += result + "; "
                    step.explanation += result + "。"
            
            # 推导极限传递关系
            limit_conclusion = self._derive_limit_transfer(function_chain, all_text)
            if limit_conclusion:
                new_state.add_known(limit_conclusion)
                step.conclusion += limit_conclusion
                step.explanation += limit_conclusion + "。"
        
        if step.conclusion:
            step.status = OperatorStatus.SUCCESS
            new_state.mark_operator_applied(self.name)
        else:
            step.status = OperatorStatus.FAILED
            step.explanation = "未能应用可逆性分析"
        
        return new_state, step
    
    def _extract_function_chain(self, text: str) -> List[str]:
        """
        从文本中提取复合函数链。
        
        例如：cos(sin x_n) → ['x_n', 'sin', 'cos']
        """
        chain = []
        
        # 检测复合函数模式
        patterns = [
            (r'cos\(sin', ['x', 'sin', 'cos']),
            (r'sin\(cos', ['x', 'cos', 'sin']),
            (r'cos\(cos', ['x', 'cos', 'cos']),
            (r'sin\(sin', ['x', 'sin', 'sin']),
        ]
        
        for pattern, func_chain in patterns:
            if pattern in text.lower():
                chain = func_chain
                break
        
        # 添加下标信息
        if chain and 'x_n' in text:
            chain[0] = 'x_n'
        
        return chain
    
    def _analyze_chain_invertibility(self, function_chain: List[str], text: str) -> List[str]:
        """
        分析复合函数链中每个函数的可逆性。
        
        Returns:
            分析结论列表
        """
        results = []
        
        if len(function_chain) < 2:
            return results
        
        # 分析内层函数
        inner_func = function_chain[1]
        domain_info = self._get_domain_info(text)
        
        if inner_func == 'sin':
            if domain_info in ['[-π/2, π/2]', '[-π/2, π/2]'] or ('-π/2' in text and 'π/2' in text):
                results.append(f"sin 在 [-π/2, π/2] 上严格单调递增，因此可逆")
                results.append(f"sin(x_n) 的值域为 [-1, 1]")
        
        elif inner_func == 'cos':
            if domain_info in ['[-π/2, π/2]'] or ('-π/2' in text and 'π/2' in text):
                results.append(f"cos 在 [-π/2, π/2] 上严格单调递减，因此可逆")
                results.append(f"cos(x_n) 的值域为 [0, 1]")
        
        # 分析外层函数
        if len(function_chain) > 2:
            outer_func = function_chain[2]
            
            if outer_func == 'cos':
                # cos 的输入来自内层函数的值域
                if inner_func == 'sin':
                    # sin 的值域是 [-1, 1]
                    results.append(f"cos 在 [-1, 1] 上不是单调函数（在 [-1,0] 增，[0,1] 减）")
                    results.append(f"因此 cos 在 [-1, 1] 上不可逆")
                
                elif inner_func == 'cos':
                    # cos 的值域是 [0, 1]
                    results.append(f"cos 在 [0, 1] 上严格单调递减，因此可逆")
            
            elif outer_func == 'sin':
                if inner_func == 'cos':
                    # cos 的值域是 [0, 1]
                    results.append(f"sin 在 [0, 1] 上严格单调递增，因此可逆")
                
                elif inner_func == 'sin':
                    # sin 的值域是 [-1, 1]
                    results.append(f"sin 在 [-1, 1] 上严格单调递增，因此可逆")
        
        return results
    
    def _get_domain_info(self, text: str) -> str:
        """从文本中提取定义域信息"""
        if '-π/2' in text and 'π/2' in text:
            return '[-π/2, π/2]'
        elif '-\\pi/2' in text and '\\pi/2' in text:
            return '[-π/2, π/2]'
        return ""
    
    def _derive_limit_transfer(self, function_chain: List[str], text: str) -> Optional[str]:
        """
        推导极限存在性的传递关系。
        
        核心规则：
          若 f 可逆且 lim f(x_n) 存在，则 lim x_n 存在
        """
        conclusions = []
        
        if len(function_chain) >= 3:
            outer_func = function_chain[2]
            inner_func = function_chain[1]
            
            # 判断外层函数是否可逆
            if outer_func == 'cos':
                if inner_func == 'sin':
                    # cos 在 [-1,1] 上不可逆
                    conclusions.append(f"由于 cos 在 [-1, 1] 上不可逆，lim cos(sin x_n) 存在不能推出 lim sin x_n 存在")
                    conclusions.append(f"因此 lim cos(sin x_n) 存在不能推出 lim x_n 存在")
                
                elif inner_func == 'cos':
                    # cos 在 [0,1] 上可逆
                    conclusions.append(f"由于 cos 在 [0, 1] 上可逆，lim cos(cos x_n) 存在可推出 lim cos x_n 存在")
            
            elif outer_func == 'sin':
                if inner_func == 'cos':
                    # sin 在 [0,1] 上可逆
                    conclusions.append(f"由于 sin 在 [0, 1] 上可逆，lim sin(cos x_n) 存在可推出 lim cos x_n 存在")
                    conclusions.append(f"又 cos 在 [-π/2, π/2] 上可逆，因此 lim cos x_n 存在可推出 lim x_n 存在")
                    conclusions.append(f"综上：lim sin(cos x_n) 存在可推出 lim x_n 存在")
                
                elif inner_func == 'sin':
                    # sin 在 [-1,1] 上可逆
                    conclusions.append(f"由于 sin 在 [-1, 1] 上可逆，lim sin(sin x_n) 存在可推出 lim sin x_n 存在")
        
        if conclusions:
            return '；'.join(conclusions)
        
        return None
    
    def cost(self, state: ReasoningState) -> float:
        """可逆性分析成本中等"""
        return 0.8
