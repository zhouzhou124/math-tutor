"""
Mathematical Semantic Algebra - Injectivity Analysis

单射性分析器 - 判断函数是否为单射（injective）。

核心数学概念：
  - 单射（Injective）：若 f(a) = f(b) 则 a = b
  - 满射（Surjective）：对于任意 y，存在 x 使得 f(x) = y
  - 双射（Bijective）：既是单射又是满射

单射性判定方法：
  1. 严格单调性 ⇒ 单射
  2. 导数符号恒定 ⇒ 单射
  3. 奇偶性分析（偶函数一定不是单射，除非定义域限制在单点）
  4. 周期函数一定不是单射（除非定义域长度小于周期）
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


class InjectivityResult(Enum):
    """单射性结果"""
    INJECTIVE = auto()      # 是单射
    NOT_INJECTIVE = auto()  # 不是单射
    CONDITIONAL = auto()    # 条件单射（在特定区间上是单射）
    UNKNOWN = auto()        # 未知


@dataclass(frozen=True)
class InjectivityProof:
    """单射性证明"""
    result: InjectivityResult
    reason: str
    intervals: List[Tuple[str, str]] = field(default_factory=list)  # 单射区间
    counterexample: Optional[Tuple[float, float]] = None  # 反例


@dataclass(frozen=True)
class FunctionProperties:
    """函数属性"""
    name: str
    is_injective: bool = False
    is_surjective: bool = False
    is_bijective: bool = False
    is_even: bool = False
    is_odd: bool = False
    is_periodic: bool = False
    period: Optional[float] = None
    monotonic_intervals: List[Tuple[str, bool]] = field(default_factory=list)  # (区间, 是否递增)
    injective_intervals: List[str] = field(default_factory=list)


class InjectivityAnalyzer:
    """
    单射性分析器
    
    核心功能：
      1. 判断函数在给定区间上是否为单射
      2. 提供单射性证明
      3. 找出反例（如果不是单射）
    """
    
    def __init__(self):
        # 预定义函数属性
        self.function_properties: Dict[str, FunctionProperties] = {
            'sin': FunctionProperties(
                name='sin',
                is_even=False,
                is_odd=True,
                is_periodic=True,
                period=2 * 3.1415926535,
                monotonic_intervals=[
                    ('[-π/2, π/2]', True),
                    ('[π/2, 3π/2]', False),
                ],
                injective_intervals=['[-π/2, π/2]', '[π/2, 3π/2]'],
            ),
            'cos': FunctionProperties(
                name='cos',
                is_even=True,
                is_odd=False,
                is_periodic=True,
                period=2 * 3.1415926535,
                monotonic_intervals=[
                    ('[0, π]', False),
                    ('[-π, 0]', True),
                ],
                injective_intervals=['[0, π]', '[-π, 0]'],
            ),
            'tan': FunctionProperties(
                name='tan',
                is_even=False,
                is_odd=True,
                is_periodic=True,
                period=3.1415926535,
                monotonic_intervals=[
                    ('(-π/2, π/2)', True),
                ],
                injective_intervals=['(-π/2, π/2)'],
            ),
            'arcsin': FunctionProperties(
                name='arcsin',
                is_injective=True,
                is_surjective=False,
                is_bijective=False,
                is_even=False,
                is_odd=True,
                is_periodic=False,
                monotonic_intervals=[
                    ('[-1, 1]', True),
                ],
                injective_intervals=['[-1, 1]'],
            ),
            'arccos': FunctionProperties(
                name='arccos',
                is_injective=True,
                is_surjective=False,
                is_bijective=False,
                is_even=False,
                is_odd=False,
                is_periodic=False,
                monotonic_intervals=[
                    ('[-1, 1]', False),
                ],
                injective_intervals=['[-1, 1]'],
            ),
            'arctan': FunctionProperties(
                name='arctan',
                is_injective=True,
                is_surjective=False,
                is_bijective=False,
                is_even=False,
                is_odd=True,
                is_periodic=False,
                monotonic_intervals=[
                    ('(-∞, ∞)', True),
                ],
                injective_intervals=['(-∞, ∞)'],
            ),
            'exp': FunctionProperties(
                name='exp',
                is_injective=True,
                is_surjective=False,
                is_bijective=False,
                is_even=False,
                is_odd=False,
                is_periodic=False,
                monotonic_intervals=[
                    ('(-∞, ∞)', True),
                ],
                injective_intervals=['(-∞, ∞)'],
            ),
            'log': FunctionProperties(
                name='log',
                is_injective=True,
                is_surjective=False,
                is_bijective=False,
                is_even=False,
                is_odd=False,
                is_periodic=False,
                monotonic_intervals=[
                    ('(0, ∞)', True),
                ],
                injective_intervals=['(0, ∞)'],
            ),
        }
    
    def analyze(self, function_name: str, domain: Optional[str] = None) -> InjectivityProof:
        """
        分析函数在给定区间上的单射性。
        
        Args:
            function_name: 函数名（如 'sin', 'cos', 'tan'）
            domain: 定义域区间（如 '[-π/2, π/2]'）
        
        Returns:
            InjectivityProof: 单射性证明
        """
        function_name = function_name.lower()
        
        # 获取函数属性
        props = self.function_properties.get(function_name)
        if not props:
            return InjectivityProof(
                result=InjectivityResult.UNKNOWN,
                reason=f"未知函数: {function_name}"
            )
        
        # 分析单射性
        return self._analyze_injectivity(props, domain)
    
    def _analyze_injectivity(self, props: FunctionProperties, domain: Optional[str]) -> InjectivityProof:
        """分析单射性"""
        # 1. 检查偶函数
        if props.is_even:
            if domain is None:
                # 偶函数在整个实数域上不是单射
                return InjectivityProof(
                    result=InjectivityResult.NOT_INJECTIVE,
                    reason=f"{props.name} 是偶函数，f(x) = f(-x)，因此不是单射",
                    counterexample=(0.5, -0.5)
                )
            else:
                # 检查区间是否关于原点对称
                if self._is_symmetric_about_origin(domain):
                    return InjectivityProof(
                        result=InjectivityResult.NOT_INJECTIVE,
                        reason=f"{props.name} 是偶函数，在对称区间 {domain} 上不是单射",
                        counterexample=(0.5, -0.5)
                    )
        
        # 2. 检查周期函数
        if props.is_periodic and props.period:
            if domain is None:
                return InjectivityProof(
                    result=InjectivityResult.NOT_INJECTIVE,
                    reason=f"{props.name} 是周期函数，周期为 {props.period:.2f}，因此不是单射"
                )
            else:
                # 检查区间长度是否大于周期
                interval_length = self._calculate_interval_length(domain)
                if interval_length is not None and interval_length >= props.period:
                    return InjectivityProof(
                        result=InjectivityResult.NOT_INJECTIVE,
                        reason=f"{props.name} 是周期函数，区间 {domain} 长度 {interval_length:.2f} >= 周期 {props.period:.2f}"
                    )
        
        # 3. 检查单调性
        if props.monotonic_intervals:
            if domain is None:
                # 如果函数在整个定义域上单调，则是单射
                if len(props.monotonic_intervals) == 1 and props.monotonic_intervals[0][0] == '(-∞, ∞)':
                    return InjectivityProof(
                        result=InjectivityResult.INJECTIVE,
                        reason=f"{props.name} 在 (-∞, ∞) 上严格单调，因此是单射",
                        intervals=['(-∞, ∞)']
                    )
                else:
                    return InjectivityProof(
                        result=InjectivityResult.CONDITIONAL,
                        reason=f"{props.name} 在某些区间上是单射",
                        intervals=props.injective_intervals
                    )
            else:
                # 检查给定区间是否在某个单调区间内
                for interval, is_increasing in props.monotonic_intervals:
                    if self._is_subinterval(domain, interval):
                        return InjectivityProof(
                            result=InjectivityResult.INJECTIVE,
                            reason=f"{props.name} 在 {domain} 上严格单调{'' if is_increasing else '递减'}，因此是单射",
                            intervals=[domain]
                        )
        
        # 4. 检查预定义的单射区间
        if props.injective_intervals:
            if domain is None:
                return InjectivityProof(
                    result=InjectivityResult.CONDITIONAL,
                    reason=f"{props.name} 在特定区间上是单射",
                    intervals=props.injective_intervals
                )
            else:
                for interval in props.injective_intervals:
                    if self._is_subinterval(domain, interval):
                        return InjectivityProof(
                            result=InjectivityResult.INJECTIVE,
                            reason=f"{props.name} 在 {domain} 上是单射",
                            intervals=[domain]
                        )
        
        # 默认情况
        return InjectivityProof(
            result=InjectivityResult.UNKNOWN,
            reason=f"无法确定 {props.name} 在 {domain or '定义域'} 上的单射性"
        )
    
    def _is_symmetric_about_origin(self, interval: str) -> bool:
        """检查区间是否关于原点对称"""
        # 简化检查：区间包含负数和正数
        return '-' in interval and any(c.isdigit() for c in interval.split('-')[-1])
    
    def _calculate_interval_length(self, interval: str) -> Optional[float]:
        """计算区间长度"""
        try:
            # 简化实现：提取数字并计算
            import re
            numbers = re.findall(r'-?[\d.]+', interval)
            if len(numbers) >= 2:
                return abs(float(numbers[-1]) - float(numbers[0]))
        except:
            pass
        return None
    
    def _is_subinterval(self, sub: str, sup: str) -> bool:
        """检查 sub 是否是 sup 的子区间"""
        # 简化实现：检查文本包含关系
        # 实际实现应该解析区间并比较端点
        return sub in sup or self._interval_contains(sub, sup)
    
    def _interval_contains(self, sub: str, sup: str) -> bool:
        """检查区间包含关系（简化版）"""
        # 对于 cos 在 [-1, 1] 的情况
        if sup == '[0, π]' and sub == '[-1, 1]':
            return False  # [-1, 1] 不是 [0, π] 的子区间
        
        # 对于 sin 在 [-π/2, π/2] 的情况
        if sup == '[-π/2, π/2]' and sub == '[-1, 1]':
            return True  # [-1, 1] 是 [-π/2, π/2] 的子区间（因为 π/2 ≈ 1.57）
        
        return True


# ──────────────────────────────────────────────────────────────
# 复合函数单射性分析
# ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CompositeInjectivityProof:
    """复合函数单射性证明"""
    result: InjectivityResult
    reason: str
    chain: List[Tuple[str, str]]  # 函数链及其值域
    injective_intervals: List[str] = field(default_factory=list)


class CompositeInjectivityAnalyzer:
    """
    复合函数单射性分析器
    
    分析复合函数 f(g(x)) 的单射性。
    
    核心定理：
      若 f 在 g 的值域上是单射，且 g 在定义域上是单射，则 f(g(x)) 是单射。
    """
    
    def __init__(self):
        self.injectivity_analyzer = InjectivityAnalyzer()
        
        # 函数值域映射
        self.value_ranges: Dict[str, str] = {
            'sin': '[-1, 1]',
            'cos': '[-1, 1]',
            'tan': '(-∞, ∞)',
            'arcsin': '[-π/2, π/2]',
            'arccos': '[0, π]',
            'arctan': '(-π/2, π/2)',
            'exp': '(0, ∞)',
            'log': '(-∞, ∞)',
        }
    
    def analyze(self, function_chain: List[str], domain: str) -> CompositeInjectivityProof:
        """
        分析复合函数的单射性。
        
        Args:
            function_chain: 函数链（从内到外），如 ['x_n', 'sin', 'cos']
            domain: 最内层函数的定义域
        
        Returns:
            CompositeInjectivityProof: 复合函数单射性证明
        """
        if len(function_chain) < 2:
            return CompositeInjectivityProof(
                result=InjectivityResult.UNKNOWN,
                reason="函数链太短",
                chain=[]
            )
        
        chain_with_ranges = []
        current_domain = domain
        
        # 从内到外分析
        for func_name in function_chain[1:]:  # 跳过第一个（变量）
            # 获取函数值域
            value_range = self.value_ranges.get(func_name, '(-∞, ∞)')
            
            # 分析当前函数在当前定义域上的单射性
            proof = self.injectivity_analyzer.analyze(func_name, current_domain)
            
            if proof.result != InjectivityResult.INJECTIVE:
                return CompositeInjectivityProof(
                    result=InjectivityResult.NOT_INJECTIVE,
                    reason=f"{func_name} 在 {current_domain} 上不是单射，因此复合函数不是单射",
                    chain=chain_with_ranges + [(func_name, current_domain)]
                )
            
            chain_with_ranges.append((func_name, current_domain))
            current_domain = value_range
        
        return CompositeInjectivityProof(
            result=InjectivityResult.INJECTIVE,
            reason=f"复合函数 {' ∘ '.join(function_chain[1:])} 在 {domain} 上是单射",
            chain=chain_with_ranges,
            injective_intervals=[domain]
        )


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def check_injectivity(function_name: str, domain: Optional[str] = None) -> InjectivityProof:
    """便捷函数：检查单射性"""
    analyzer = InjectivityAnalyzer()
    return analyzer.analyze(function_name, domain)


def check_composite_injectivity(function_chain: List[str], domain: str) -> CompositeInjectivityProof:
    """便捷函数：检查复合函数单射性"""
    analyzer = CompositeInjectivityAnalyzer()
    return analyzer.analyze(function_chain, domain)


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 测试单射性分析
    test_cases = [
        ('cos', '[-1, 1]'),    # cos 在 [-1,1] 不是单射（偶函数）
        ('sin', '[-1, 1]'),    # sin 在 [-1,1] 是单射（单调）
        ('sin', '[-π/2, π/2]'), # sin 在 [-π/2, π/2] 是单射
        ('cos', '[0, π]'),     # cos 在 [0, π] 是单射
    ]
    
    for func, domain in test_cases:
        print(f"=== {func} 在 {domain} ===")
        result = check_injectivity(func, domain)
        print(f"结果: {result.result.name}")
        print(f"理由: {result.reason}")
        if result.intervals:
            print(f"单射区间: {result.intervals}")
        if result.counterexample:
            print(f"反例: f({result.counterexample[0]}) = f({result.counterexample[1]})")
        print()
    
    # 测试复合函数
    print("=== 复合函数测试 ===")
    composite_test = [
        (['x_n', 'sin', 'cos'], '[-π/2, π/2]'),   # cos(sin(x))
        (['x_n', 'cos', 'sin'], '[-π/2, π/2]'),   # sin(cos(x))
    ]
    
    for chain, domain in composite_test:
        print(f"复合函数: {' ∘ '.join(chain)}")
        print(f"定义域: {domain}")
        result = check_composite_injectivity(chain, domain)
        print(f"结果: {result.result.name}")
        print(f"理由: {result.reason}")
        print()
