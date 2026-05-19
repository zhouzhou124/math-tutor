"""
Mathematical Semantic Algebra - Function Object

函数对象 - 表示数学函数及其属性。

核心设计思想：
  将数学函数表示为结构化对象，包含其所有数学属性。
  
  例如：
  FunctionObject(
      name="cos",
      parity="even",
      injective=False,
      monotone_intervals=[("[-π, 0]", "increasing"), ("[0, π]", "decreasing")],
      periodic=True,
      period=2π,
      domain="(-∞, ∞)",
      range="[-1, 1]",
  )

这是真正的"理解数学对象"的架构。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


class Parity(Enum):
    """奇偶性"""
    EVEN = auto()       # 偶函数
    ODD = auto()        # 奇函数
    NEITHER = auto()    # 非奇非偶


class Monotonicity(Enum):
    """单调性"""
    INCREASING = auto()     # 递增
    DECREASING = auto()     # 递减
    CONSTANT = auto()       # 常数
    NON_MONOTONIC = auto()  # 非单调


@dataclass(frozen=True)
class Interval:
    """区间"""
    start: Union[float, str]  # 可以是数字或特殊值如 '-inf', 'inf', '-π/2'
    end: Union[float, str]
    start_open: bool = False  # 是否开区间
    end_open: bool = False
    
    def __repr__(self) -> str:
        start_bracket = '(' if self.start_open else '['
        end_bracket = ')' if self.end_open else ']'
        return f"{start_bracket}{self.start}, {self.end}{end_bracket}"
    
    def contains(self, x: float) -> bool:
        """检查点是否在区间内"""
        start_val = self._to_float(self.start)
        end_val = self._to_float(self.end)
        x_val = x
        
        if self.start_open:
            if x_val <= start_val:
                return False
        else:
            if x_val < start_val:
                return False
        
        if self.end_open:
            if x_val >= end_val:
                return False
        else:
            if x_val > end_val:
                return False
        
        return True
    
    def _to_float(self, value: Union[float, str]) -> float:
        """将值转换为浮点数"""
        if isinstance(value, float):
            return value
        if value == '-inf':
            return float('-inf')
        if value == 'inf':
            return float('inf')
        if value == '-π/2':
            return -3.1415926535 / 2
        if value == 'π/2':
            return 3.1415926535 / 2
        if value == '-π':
            return -3.1415926535
        if value == 'π':
            return 3.1415926535
        if value == '2π':
            return 2 * 3.1415926535
        try:
            return float(value)
        except (ValueError, TypeError):
            return float('-inf')


@dataclass(frozen=True)
class MonotoneInterval:
    """单调区间"""
    interval: Interval
    monotonicity: Monotonicity
    
    def __repr__(self) -> str:
        return f"{self.monotonicity.name}: {self.interval}"


@dataclass(frozen=True)
class FunctionObject:
    """
    函数对象 - 表示数学函数及其属性。
    
    这是语义代数的核心数据结构，用于表示"理解数学对象"。
    """
    
    # 基本信息
    name: str
    latex_name: str
    
    # 定义域和值域
    domain: Interval
    range: Interval
    
    # 奇偶性
    parity: Parity
    
    # 周期性
    is_periodic: bool = False
    period: Optional[float] = None
    
    # 单调性
    monotone_intervals: List[MonotoneInterval] = field(default_factory=list)
    
    # 单射性
    is_injective: bool = False
    injective_intervals: List[Interval] = field(default_factory=list)
    
    # 满射性
    is_surjective: bool = False
    
    # 双射性
    is_bijective: bool = False
    
    # 导数
    derivative: Optional[str] = None
    
    # 特殊点
    zeros: List[float] = field(default_factory=list)
    extrema: List[Tuple[float, str]] = field(default_factory=list)  # (位置, 类型: max/min)
    
    def __repr__(self) -> str:
        return f"<FunctionObject: {self.name}>"
    
    def is_monotone_on(self, interval: Interval) -> Tuple[bool, Optional[Monotonicity]]:
        """
        检查函数在给定区间上是否单调。
        
        Returns:
            (是否单调, 单调性类型)
        """
        for mi in self.monotone_intervals:
            if mi.interval.contains(interval.start) and mi.interval.contains(interval.end):
                return True, mi.monotonicity
        return False, None
    
    def is_injective_on(self, interval: Interval) -> bool:
        """检查函数在给定区间上是否单射"""
        for inj_interval in self.injective_intervals:
            # 简化检查
            if str(inj_interval) in str(interval) or str(interval) in str(inj_interval):
                return True
        # 如果在区间上严格单调，则是单射
        is_mono, _ = self.is_monotone_on(interval)
        return is_mono
    
    def get_inverse_function(self) -> Optional['FunctionObject']:
        """获取反函数"""
        if not self.is_bijective:
            return None
        
        inverse_map = {
            'sin': 'arcsin',
            'cos': 'arccos',
            'tan': 'arctan',
            'exp': 'log',
            'log': 'exp',
            'arcsin': 'sin',
            'arccos': 'cos',
            'arctan': 'tan',
        }
        
        return function_registry.get(inverse_map.get(self.name))
    
    def compose(self, other: 'FunctionObject') -> Optional['FunctionObject']:
        """复合函数"""
        # 检查值域和定义域是否兼容
        if str(self.range) != str(other.domain):
            return None
        
        # 创建复合函数对象（简化版）
        composite_name = f"{self.name}∘{other.name}"
        return FunctionObject(
            name=composite_name,
            latex_name=f"{self.latex_name}({other.latex_name})",
            domain=other.domain,
            range=self.range,
            parity=Parity.NEITHER,
            is_periodic=self.is_periodic or other.is_periodic,
            period=self.period if self.is_periodic else other.period,
            is_injective=self.is_injective and other.is_injective,
        )


# ──────────────────────────────────────────────────────────────
# 函数注册表
# ──────────────────────────────────────────────────────────────

function_registry: Dict[str, FunctionObject] = {}


def register_function(func_obj: FunctionObject) -> None:
    """注册函数对象"""
    function_registry[func_obj.name] = func_obj


def get_function(name: str) -> Optional[FunctionObject]:
    """获取函数对象"""
    return function_registry.get(name.lower())


# ──────────────────────────────────────────────────────────────
# 预定义函数
# ──────────────────────────────────────────────────────────────

# 正弦函数
sin_func = FunctionObject(
    name="sin",
    latex_name=r"\sin",
    domain=Interval('-inf', 'inf'),
    range=Interval(-1, 1),
    parity=Parity.ODD,
    is_periodic=True,
    period=2 * 3.1415926535,
    monotone_intervals=[
        MonotoneInterval(Interval('-π/2', 'π/2'), Monotonicity.INCREASING),
        MonotoneInterval(Interval('π/2', '3π/2'), Monotonicity.DECREASING),
    ],
    injective_intervals=[
        Interval('-π/2', 'π/2'),
        Interval('π/2', '3π/2'),
    ],
    derivative="cos(x)",
    zeros=[0, 3.1415926535, -3.1415926535],
    extrema=[
        (3.1415926535 / 2, 'max'),
        (-3.1415926535 / 2, 'min'),
    ],
)
register_function(sin_func)

# 余弦函数
cos_func = FunctionObject(
    name="cos",
    latex_name=r"\cos",
    domain=Interval('-inf', 'inf'),
    range=Interval(-1, 1),
    parity=Parity.EVEN,
    is_periodic=True,
    period=2 * 3.1415926535,
    monotone_intervals=[
        MonotoneInterval(Interval('0', 'π'), Monotonicity.DECREASING),
        MonotoneInterval(Interval('-π', '0'), Monotonicity.INCREASING),
    ],
    injective_intervals=[
        Interval('0', 'π'),
        Interval('-π', '0'),
    ],
    derivative="-sin(x)",
    zeros=[3.1415926535 / 2, -3.1415926535 / 2],
    extrema=[
        (0, 'max'),
        (3.1415926535, 'min'),
    ],
)
register_function(cos_func)

# 正切函数
tan_func = FunctionObject(
    name="tan",
    latex_name=r"\tan",
    domain=Interval('-π/2', 'π/2', start_open=True, end_open=True),
    range=Interval('-inf', 'inf'),
    parity=Parity.ODD,
    is_periodic=True,
    period=3.1415926535,
    monotone_intervals=[
        MonotoneInterval(Interval('-π/2', 'π/2', start_open=True, end_open=True), Monotonicity.INCREASING),
    ],
    injective_intervals=[
        Interval('-π/2', 'π/2', start_open=True, end_open=True),
    ],
    is_bijective=True,
    derivative="sec^2(x)",
    zeros=[0],
)
register_function(tan_func)

# 反正弦函数
arcsin_func = FunctionObject(
    name="arcsin",
    latex_name=r"\arcsin",
    domain=Interval(-1, 1),
    range=Interval('-π/2', 'π/2'),
    parity=Parity.ODD,
    is_periodic=False,
    monotone_intervals=[
        MonotoneInterval(Interval(-1, 1), Monotonicity.INCREASING),
    ],
    injective_intervals=[Interval(-1, 1)],
    is_injective=True,
    is_surjective=False,
    derivative="1/sqrt(1-x^2)",
)
register_function(arcsin_func)

# 反余弦函数
arccos_func = FunctionObject(
    name="arccos",
    latex_name=r"\arccos",
    domain=Interval(-1, 1),
    range=Interval('0', 'π'),
    parity=Parity.NEITHER,
    is_periodic=False,
    monotone_intervals=[
        MonotoneInterval(Interval(-1, 1), Monotonicity.DECREASING),
    ],
    injective_intervals=[Interval(-1, 1)],
    is_injective=True,
    is_surjective=False,
    derivative="-1/sqrt(1-x^2)",
)
register_function(arccos_func)

# 反正切函数
arctan_func = FunctionObject(
    name="arctan",
    latex_name=r"\arctan",
    domain=Interval('-inf', 'inf'),
    range=Interval('-π/2', 'π/2', start_open=True, end_open=True),
    parity=Parity.ODD,
    is_periodic=False,
    monotone_intervals=[
        MonotoneInterval(Interval('-inf', 'inf'), Monotonicity.INCREASING),
    ],
    injective_intervals=[Interval('-inf', 'inf')],
    is_injective=True,
    is_surjective=False,
    derivative="1/(1+x^2)",
)
register_function(arctan_func)

# 指数函数
exp_func = FunctionObject(
    name="exp",
    latex_name=r"\exp",
    domain=Interval('-inf', 'inf'),
    range=Interval(0, 'inf', start_open=True),
    parity=Parity.NEITHER,
    is_periodic=False,
    monotone_intervals=[
        MonotoneInterval(Interval('-inf', 'inf'), Monotonicity.INCREASING),
    ],
    injective_intervals=[Interval('-inf', 'inf')],
    is_injective=True,
    is_surjective=False,
    derivative="exp(x)",
)
register_function(exp_func)

# 对数函数
log_func = FunctionObject(
    name="log",
    latex_name=r"\log",
    domain=Interval(0, 'inf', start_open=True),
    range=Interval('-inf', 'inf'),
    parity=Parity.NEITHER,
    is_periodic=False,
    monotone_intervals=[
        MonotoneInterval(Interval(0, 'inf', start_open=True), Monotonicity.INCREASING),
    ],
    injective_intervals=[Interval(0, 'inf', start_open=True)],
    is_injective=True,
    is_surjective=False,
    derivative="1/x",
)
register_function(log_func)


# ──────────────────────────────────────────────────────────────
# 可逆性分析器
# ──────────────────────────────────────────────────────────────

class InvertibilityAnalyzer:
    """
    可逆性分析器
    
    判断函数在给定区间上是否可逆，并分析极限存在性的传递关系。
    """
    
    def __init__(self):
        pass
    
    def analyze(self, function_name: str, domain: str) -> Dict[str, Any]:
        """
        分析函数的可逆性。
        
        Args:
            function_name: 函数名
            domain: 定义域区间字符串
        
        Returns:
            Dict: 分析结果
        """
        func = get_function(function_name)
        if not func:
            return {
                'success': False,
                'error': f"未知函数: {function_name}",
            }
        
        # 解析区间
        interval = self._parse_interval(domain)
        
        # 检查单射性
        is_injective = func.is_injective_on(interval)
        
        # 检查单调性
        is_monotone, monotonicity = func.is_monotone_on(interval)
        
        return {
            'success': True,
            'function_name': function_name,
            'domain': domain,
            'is_injective': is_injective,
            'is_monotone': is_monotone,
            'monotonicity': monotonicity.name if monotonicity else None,
            'parity': func.parity.name,
            'is_periodic': func.is_periodic,
            'period': func.period,
            'range': str(func.range),
            'derivative': func.derivative,
            'can_invert': is_injective,
            'reason': self._generate_reason(func, interval, is_injective),
        }
    
    def analyze_composite(self, function_chain: List[str], domain: str) -> Dict[str, Any]:
        """
        分析复合函数的可逆性。
        
        Args:
            function_chain: 函数链（从内到外）
            domain: 最内层函数的定义域
        
        Returns:
            Dict: 分析结果
        """
        if len(function_chain) < 2:
            return {
                'success': False,
                'error': "函数链太短",
            }
        
        results = []
        current_domain = domain
        all_injective = True
        
        for func_name in function_chain[1:]:
            result = self.analyze(func_name, current_domain)
            results.append(result)
            
            if not result.get('can_invert', False):
                all_injective = False
                break
            
            # 更新定义域为当前函数的值域
            current_domain = result.get('range', current_domain)
        
        return {
            'success': True,
            'function_chain': function_chain,
            'domain': domain,
            'steps': results,
            'can_invert': all_injective,
            'reason': self._generate_composite_reason(results, all_injective),
        }
    
    def _parse_interval(self, domain: str) -> Interval:
        """解析区间字符串"""
        # 简化实现
        domain = domain.strip()
        
        start_open = domain.startswith('(') or domain.startswith(']')
        end_open = domain.endswith(')') or domain.endswith('[')
        
        content = domain[1:-1]
        parts = content.split(',')
        start = parts[0].strip()
        end = parts[1].strip()
        
        return Interval(start, end, start_open, end_open)
    
    def _generate_reason(self, func: FunctionObject, interval: Interval, is_injective: bool) -> str:
        """生成推理理由"""
        if is_injective:
            if func.is_monotone_on(interval)[0]:
                return f"{func.name} 在 {interval} 上严格单调，因此可逆"
            else:
                return f"{func.name} 在 {interval} 上是单射，因此可逆"
        else:
            if func.parity == Parity.EVEN:
                return f"{func.name} 是偶函数，f(x) = f(-x)，在对称区间 {interval} 上不是单射，因此不可逆"
            if func.is_periodic:
                return f"{func.name} 是周期函数，在区间 {interval} 上不是单射，因此不可逆"
            return f"{func.name} 在 {interval} 上不是单射，因此不可逆"
    
    def _generate_composite_reason(self, results: List[Dict[str, Any]], all_injective: bool) -> str:
        """生成复合函数推理理由"""
        if all_injective:
            return "所有函数在各自定义域上都是单射，因此复合函数可逆"
        else:
            # 找到第一个不可逆的函数
            for result in results:
                if not result.get('can_invert', False):
                    return f"复合函数中 {result['function_name']} 在 {result['domain']} 上不可逆，因此整个复合函数不可逆"
            return "复合函数不可逆"


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def analyze_invertibility(function_name: str, domain: str) -> Dict[str, Any]:
    """便捷函数：分析可逆性"""
    analyzer = InvertibilityAnalyzer()
    return analyzer.analyze(function_name, domain)


def analyze_composite_invertibility(function_chain: List[str], domain: str) -> Dict[str, Any]:
    """便捷函数：分析复合函数可逆性"""
    analyzer = InvertibilityAnalyzer()
    return analyzer.analyze_composite(function_chain, domain)


# ──────────────────────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 测试函数对象
    print("=== 函数对象测试 ===")
    cos = get_function('cos')
    print(f"函数: {cos.name}")
    print(f"定义域: {cos.domain}")
    print(f"值域: {cos.range}")
    print(f"奇偶性: {cos.parity.name}")
    print(f"周期性: {cos.is_periodic}")
    print(f"单射性: {cos.is_injective}")
    print(f"单调区间: {cos.monotone_intervals}")
    print()
    
    # 测试可逆性分析
    print("=== 可逆性分析测试 ===")
    
    # cos 在 [-1, 1] 的情况
    result = analyze_invertibility('cos', '[-1, 1]')
    print(f"cos 在 [-1, 1]:")
    print(f"  可逆: {result['can_invert']}")
    print(f"  理由: {result['reason']}")
    print()
    
    # sin 在 [-1, 1] 的情况
    result = analyze_invertibility('sin', '[-1, 1]')
    print(f"sin 在 [-1, 1]:")
    print(f"  可逆: {result['can_invert']}")
    print(f"  理由: {result['reason']}")
    print()
    
    # 复合函数测试
    print("=== 复合函数可逆性测试 ===")
    
    # cos(sin(x))
    result = analyze_composite_invertibility(['x_n', 'sin', 'cos'], '[-π/2, π/2]')
    print(f"cos(sin(x_n)) 在 [-π/2, π/2]:")
    print(f"  可逆: {result['can_invert']}")
    print(f"  理由: {result['reason']}")
    print()
    
    # sin(cos(x))
    result = analyze_composite_invertibility(['x_n', 'cos', 'sin'], '[-π/2, π/2]')
    print(f"sin(cos(x_n)) 在 [-π/2, π/2]:")
    print(f"  可逆: {result['can_invert']}")
    print(f"  理由: {result['reason']}")
