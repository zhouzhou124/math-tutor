"""Type Environment - 类型环境管理

管理变量、函数和符号的类型绑定。
"""

from typing import Dict, Optional, Any
from .types import MathType


class TypeEnvironment:
    """类型环境 - 维护符号到类型的映射"""
    
    def __init__(self, parent: Optional['TypeEnvironment'] = None):
        self.parent = parent
        self.bindings: Dict[str, MathType] = {}
        
        # 内置符号类型
        self._init_builtins()
    
    def _init_builtins(self):
        """初始化内置符号类型"""
        # 数学常数
        self.bindings['pi'] = MathType.REAL
        self.bindings['e'] = MathType.REAL
        self.bindings['i'] = MathType.COMPLEX
        
        # 数学函数
        self.bindings['sin'] = MathType.TRIGONOMETRIC
        self.bindings['cos'] = MathType.TRIGONOMETRIC
        self.bindings['tan'] = MathType.TRIGONOMETRIC
        self.bindings['asin'] = MathType.TRIGONOMETRIC
        self.bindings['acos'] = MathType.TRIGONOMETRIC
        self.bindings['atan'] = MathType.TRIGONOMETRIC
        
        self.bindings['exp'] = MathType.EXPONENTIAL
        self.bindings['log'] = MathType.LOGARITHMIC
        self.bindings['ln'] = MathType.LOGARITHMIC
        
        # 对数函数
        self.bindings['sqrt'] = MathType.FUNCTION
        
        # 三角函数别名
        self.bindings['sinh'] = MathType.TRIGONOMETRIC
        self.bindings['cosh'] = MathType.TRIGONOMETRIC
        self.bindings['tanh'] = MathType.TRIGONOMETRIC
    
    def get(self, name: str) -> Optional[MathType]:
        """获取符号的类型"""
        # 先在当前作用域查找
        if name in self.bindings:
            return self.bindings[name]
        
        # 如果有父作用域，向上查找
        if self.parent:
            return self.parent.get(name)
        
        # 默认返回未知类型
        return MathType.UNKNOWN
    
    def set(self, name: str, math_type: MathType):
        """设置符号的类型"""
        self.bindings[name] = math_type
    
    def update(self, bindings: Dict[str, MathType]):
        """批量更新类型绑定"""
        self.bindings.update(bindings)
    
    def extend(self) -> 'TypeEnvironment':
        """创建一个新的子作用域"""
        return TypeEnvironment(parent=self)
    
    def get_all_bindings(self) -> Dict[str, MathType]:
        """获取所有绑定（包括父作用域）"""
        if self.parent:
            parent_bindings = self.parent.get_all_bindings()
            parent_bindings.update(self.bindings)
            return parent_bindings
        return dict(self.bindings)
    
    def __contains__(self, name: str) -> bool:
        """检查符号是否在环境中"""
        if name in self.bindings:
            return True
        if self.parent:
            return name in self.parent
        return False
    
    def __getitem__(self, name: str) -> MathType:
        """使用索引访问类型"""
        result = self.get(name)
        if result is None:
            raise KeyError(f"Symbol '{name}' not found in type environment")
        return result
    
    def __setitem__(self, name: str, math_type: MathType):
        """使用索引设置类型"""
        self.set(name, math_type)
    
    def __repr__(self) -> str:
        """返回环境的字符串表示"""
        return f"TypeEnvironment({self.bindings})"


# ═══════════════════════════════════════════════
# 上下文管理器
# ═══════════════════════════════════════════════

class TypeContext:
    """类型上下文 - 用于临时类型绑定"""
    
    def __init__(self, env: TypeEnvironment, **kwargs):
        self.env = env
        self.bindings = kwargs
        self.old_bindings: Dict[str, Optional[MathType]] = {}
    
    def __enter__(self):
        """进入上下文，保存旧绑定并应用新绑定"""
        for name, math_type in self.bindings.items():
            self.old_bindings[name] = self.env.get(name)
            self.env.set(name, math_type)
        return self.env
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，恢复旧绑定"""
        for name, old_type in self.old_bindings.items():
            if old_type is not None:
                self.env.set(name, old_type)
            else:
                if name in self.env.bindings:
                    del self.env.bindings[name]


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def create_default_environment() -> TypeEnvironment:
    """创建默认类型环境"""
    return TypeEnvironment()


def create_empty_environment() -> TypeEnvironment:
    """创建空类型环境（不包含内置符号）"""
    env = TypeEnvironment(parent=None)
    env.bindings = {}
    return env