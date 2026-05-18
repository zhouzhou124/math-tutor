# ═══════════════════════════════════════════════════════════════════════════
# Equational Kernel - 等价核心
# 
# 这是形式化重写语义的核心，将 rewrite 从过程式变换转变为逻辑等价关系。
# ═══════════════════════════════════════════════════════════════════════════

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set, Tuple, Union, List
from enum import Enum, auto
from .canonical_ir import Expr, Op, ExprCache
from .strategy import DefaultCostModel

# ═══════════════════════════════════════════════════════════════════════════
# Substitution - 形式化替换
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Substitution:
    """
    形式化替换 - 将变量映射到表达式
    
    核心操作：
    - 应用替换：subst(expr, σ)
    - 组合替换：σ₁ ◦ σ₂
    - 限制替换到变量集
    """
    mapping: Dict[str, Expr] = field(default_factory=dict)
    
    def apply(self, expr: Expr) -> Expr:
        """将替换应用到表达式"""
        return self._apply_recursive(expr)
    
    def _apply_recursive(self, expr: Expr) -> Expr:
        """递归应用替换"""
        # 检查是否是符号变量且在替换映射中
        if expr.op == Op.SYMBOL:
            var_name = str(expr.args[0])
            if var_name in self.mapping:
                return self.mapping[var_name]
            return expr
        
        # 递归应用到子表达式
        new_args = []
        changed = False
        for arg in expr.args:
            if isinstance(arg, Expr):
                new_arg = self._apply_recursive(arg)
                new_args.append(new_arg)
                if new_arg != arg:
                    changed = True
            else:
                new_args.append(arg)
        
        if not changed:
            return expr
        
        # 重建表达式
        if expr.op == Op.ADD:
            return ExprCache.add(new_args)
        elif expr.op == Op.MUL:
            return ExprCache.mul(new_args)
        elif expr.op == Op.SUB:
            return ExprCache.sub(new_args[0], new_args[1])
        elif expr.op == Op.DIV:
            return ExprCache.div(new_args[0], new_args[1])
        elif expr.op == Op.POW:
            return ExprCache.pow(new_args[0], new_args[1])
        elif expr.op == Op.NEG:
            return ExprCache.neg(new_args[0])
        elif expr.op == Op.GROUP:
            return ExprCache.group(new_args[0])
        return Expr(expr.op, tuple(new_args))
    
    def compose(self, other: 'Substitution') -> 'Substitution':
        """
        组合替换：(σ ◦ τ)(x) = σ(τ(x))
        
        先应用 other，再应用 self
        """
        result = dict(other.mapping)
        for key, value in self.mapping.items():
            result[key] = other.apply(value)
        return Substitution(result)
    
    def restrict(self, variables: Set[str]) -> 'Substitution':
        """限制替换到指定变量集"""
        return Substitution({k: v for k, v in self.mapping.items() if k in variables})
    
    def __contains__(self, var: str) -> bool:
        return var in self.mapping
    
    def __repr__(self) -> str:
        pairs = [f"{k} -> {v}" for k, v in self.mapping.items()]
        return f"Substitution({', '.join(pairs)})"
    
    def __bool__(self) -> bool:
        return bool(self.mapping)


# ═══════════════════════════════════════════════════════════════════════════
# Justification - 证明依据
# ═══════════════════════════════════════════════════════════════════════════

class JustificationType(Enum):
    """证明依据类型"""
    AXIOM = auto()           # 公理
    DEFINITION = auto()      # 定义
    THEOREM = auto()         # 定理
    HYPOTHESIS = auto()      # 假设
    PROOF = auto()           # 证明
    COMPUTATION = auto()     # 计算结果
    INDUCTION = auto()       # 归纳证明
    BY_CASES = auto()        # 分情况证明
    TRANSITIVITY = auto()    # 传递性
    REFLEXIVITY = auto()     # 自反性
    SYMMETRY = auto()        # 对称性
    CONGRUENCE = auto()      # 同余
    SUBSTITUTION = auto()    # 代入


@dataclass(frozen=True)
class Justification:
    """证明依据 - 说明等式成立的原因"""
    type: JustificationType
    name: str
    references: Tuple['Theorem', ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"Justification({self.type.name}, {self.name})"


# ═══════════════════════════════════════════════════════════════════════════
# Equality - 等式
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Equality:
    """
    等式 - 表示两个表达式的等价关系
    
    核心设计：
    - lhs ≡ rhs（双向等价，非单向变换）
    - 携带证明依据
    - 支持模式变量（用于通用定理）
    """
    lhs: Expr
    rhs: Expr
    justification: Justification
    variables: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        """提取等式中的模式变量"""
        if not self.variables:
            vars = set()
            for expr in [self.lhs, self.rhs]:
                vars.update(self._extract_vars(expr))
            object.__setattr__(self, 'variables', vars)
    
    def _extract_vars(self, expr: Expr) -> Set[str]:
        """提取表达式中的符号变量"""
        vars = set()
        if expr.op == Op.SYMBOL:
            name = str(expr.args[0])
            if name.islower() and len(name) == 1:
                vars.add(name)
        for arg in expr.args:
            if isinstance(arg, Expr):
                vars.update(self._extract_vars(arg))
        return vars
    
    @property
    def is_trivial(self) -> bool:
        """是否是平凡等式（lhs == rhs）"""
        return self.lhs == self.rhs
    
    def substitute(self, bindings: Dict[str, Expr]) -> 'Equality':
        """代入变量绑定，得到具体等式"""
        return Equality(
            lhs=self._substitute_expr(self.lhs, bindings),
            rhs=self._substitute_expr(self.rhs, bindings),
            justification=self.justification,
        )
    
    def _substitute_expr(self, expr: Expr, bindings: Dict[str, Expr]) -> Expr:
        """代入表达式中的变量"""
        if expr.op == Op.SYMBOL:
            name = str(expr.args[0])
            if name in bindings:
                return bindings[name]
            return expr
        
        new_args = []
        for arg in expr.args:
            if isinstance(arg, Expr):
                new_args.append(self._substitute_expr(arg, bindings))
            else:
                new_args.append(arg)
        
        if expr.op == Op.ADD:
            return ExprCache.add(new_args)
        elif expr.op == Op.MUL:
            return ExprCache.mul(new_args)
        elif expr.op == Op.SUB:
            return ExprCache.sub(new_args[0], new_args[1])
        elif expr.op == Op.DIV:
            return ExprCache.div(new_args[0], new_args[1])
        elif expr.op == Op.POW:
            return ExprCache.pow(new_args[0], new_args[1])
        elif expr.op == Op.NEG:
            return ExprCache.neg(new_args[0])
        elif expr.op == Op.GROUP:
            return ExprCache.group(new_args[0])
        return Expr(expr.op, tuple(new_args))
    
    def flip(self) -> 'Equality':
        """翻转等式方向（lhs <-> rhs）"""
        return Equality(
            lhs=self.rhs,
            rhs=self.lhs,
            justification=self.justification,
            variables=self.variables,
        )
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Equality):
            return False
        return (self.lhs == other.lhs and self.rhs == other.rhs) or \
               (self.lhs == other.rhs and self.rhs == other.lhs)
    
    def __hash__(self) -> int:
        # 等式是对称的，所以哈希应该相同
        return hash((frozenset([self.lhs.hash, self.rhs.hash]),))
    
    def __repr__(self) -> str:
        return f"Equality({self.lhs} ≡ {self.rhs})"
    
    def to_latex(self) -> str:
        """转换为 LaTeX 格式"""
        return f"{self.lhs.to_latex()} \\equiv {self.rhs.to_latex()}"


# ═══════════════════════════════════════════════════════════════════════════
# Theorem - 定理
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Theorem:
    """
    定理 - 可复用的数学事实
    
    包含：
    - 等式内容
    - 证明（可选）
    - 适用条件
    """
    name: str
    equality: Equality
    proof: Optional['Proof'] = None
    conditions: List['Equality'] = field(default_factory=list)
    description: str = ""
    
    def __repr__(self) -> str:
        return f"Theorem({self.name}, {self.equality})"
    
    def apply(self, bindings: Dict[str, Expr]) -> Equality:
        """应用定理，代入变量"""
        return self.equality.substitute(bindings)
    
    def apply_with_proof(self, bindings: Dict[str, Expr]) -> Tuple[Equality, 'Proof']:
        """应用定理并返回证明对象"""
        eq = self.equality.substitute(bindings)
        proof = Proof(
            self,
            Substitution(bindings),
            []
        )
        return eq, proof


# ═══════════════════════════════════════════════════════════════════════════
# Proof - 证明对象
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Proof:
    """
    证明对象 - 形式化的数学证明表示
    
    核心结构：
    - rule：应用的定理/规则
    - substitution：使用的替换
    - premises：前提证明（子证明）
    
    这是 machine-checkable proof 的基础
    """
    rule: Union[Theorem, str]  # 应用的定理或推理规则名称
    substitution: Substitution
    premises: List['Proof'] = field(default_factory=list)
    
    @classmethod
    def reflexivity(cls, expr: Expr) -> 'Proof':
        """自反性证明：a = a"""
        return cls(
            rule="Reflexivity",
            substitution=Substitution()
        )
    
    @classmethod
    def symmetry(cls, premise: 'Proof') -> 'Proof':
        """对称性证明：a = b ⇒ b = a"""
        return cls(
            rule="Symmetry",
            substitution=Substitution(),
            premises=[premise]
        )
    
    @classmethod
    def transitivity(cls, premise1: 'Proof', premise2: 'Proof') -> 'Proof':
        """传递性证明：a = b, b = c ⇒ a = c"""
        return cls(
            rule="Transitivity",
            substitution=Substitution(),
            premises=[premise1, premise2]
        )
    
    @classmethod
    def congruence(cls, premise: 'Proof', func_name: str, arg_index: int) -> 'Proof':
        """同余证明：a = b ⇒ f(..., a, ...) = f(..., b, ...)"""
        return cls(
            rule=f"Congruence({func_name}, arg={arg_index})",
            substitution=Substitution(),
            premises=[premise]
        )
    
    def __repr__(self) -> str:
        if isinstance(self.rule, Theorem):
            rule_str = f"Theorem({self.rule.name})"
        else:
            rule_str = self.rule
        
        if self.substitution:
            sub_str = f", σ={self.substitution}"
        else:
            sub_str = ""
        
        if self.premises:
            prem_str = f", premises={len(self.premises)}"
        else:
            prem_str = ""
        
        return f"Proof({rule_str}{sub_str}{prem_str})"


# ═══════════════════════════════════════════════════════════════════════════
# EqualityReasoningRule - 等式推理规则
# ═══════════════════════════════════════════════════════════════════════════

class EqualityReasoningRule(Enum):
    """
    等式推理规则 - Equational Logic 的核心规则
    
    这四个规则构成了完整的等式推理系统：
    - REFLEXIVITY: a = a
    - SYMMETRY: a = b ⇒ b = a
    - TRANSITIVITY: a = b, b = c ⇒ a = c
    - CONGRUENCE: a = b ⇒ f(a) = f(b)
    """
    REFLEXIVITY = auto()
    SYMMETRY = auto()
    TRANSITIVITY = auto()
    CONGRUENCE = auto()


# ═══════════════════════════════════════════════════════════════════════════
# EquivalenceClass - 等价类
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EquivalenceClass:
    """
    等价类 - 表示一组互相等价的表达式
    
    核心操作：
    - union：合并两个等价类
    - find：查找表达式所在的代表元
    - add：添加新表达式到等价类
    
    代表元选择策略：
    - 优先选择"更简单"的表达式（代价更小）
    - 如果代价相同，选择哈希最小的
    """
    id: int
    members: Set[int] = field(default_factory=set)  # 表达式哈希集合
    representative: Optional[int] = None  # 代表元哈希
    _expr_cache: Dict[int, Expr] = field(default_factory=dict)  # 用于代价计算
    
    @classmethod
    def singleton(cls, expr: Expr) -> 'EquivalenceClass':
        """从单个表达式创建等价类"""
        h = hash(expr)
        return cls(id=h, members={h}, representative=h, _expr_cache={h: expr})
    
    def contains(self, expr: Expr) -> bool:
        """检查表达式是否在等价类中"""
        return hash(expr) in self.members
    
    def union(self, other: 'EquivalenceClass') -> 'EquivalenceClass':
        """合并两个等价类"""
        new_members = self.members.union(other.members)
        # 合并表达式缓存
        new_cache = {**self._expr_cache, **other._expr_cache}
        
        # 选择"最简单"的表达式作为代表元（代价最小）
        cost_model = DefaultCostModel()
        new_rep = None
        min_cost = float('inf')
        
        for member_hash in new_members:
            expr = new_cache.get(member_hash)
            if expr is None:
                continue
            
            cost = cost_model.cost(expr)
            if cost < min_cost or (cost == min_cost and member_hash < (new_rep or float('inf'))):
                min_cost = cost
                new_rep = member_hash
        
        # 如果找不到合适的代表元，使用哈希最小的
        if new_rep is None:
            new_rep = min(new_members)
        
        return EquivalenceClass(
            id=min(self.id, other.id),
            members=new_members,
            representative=new_rep,
            _expr_cache=new_cache,
        )
    
    def __repr__(self) -> str:
        return f"EquivalenceClass(id={self.id}, size={len(self.members)})"


# ═══════════════════════════════════════════════════════════════════════════
# EqualitySystem - 等式系统
# ═══════════════════════════════════════════════════════════════════════════

class EqualitySystem:
    """
    等式系统 - 管理一组等式和等价关系
    
    核心能力：
    - 添加等式
    - 查询等价关系
    - 执行同余闭包（Congruence Closure）
    - 生成证明
    """
    
    def __init__(self):
        self.equations: Set[Equality] = set()
        self.theorems: Dict[str, Theorem] = {}
        self._eq_classes: Dict[int, EquivalenceClass] = {}  # hash -> class
        self._expr_cache: Dict[int, Expr] = {}  # hash -> expr
        self._pending_updates: Set[int] = set()  # 需要重新检查的表达式
    
    def add_equality(self, eq: Equality):
        """添加等式到系统"""
        self.equations.add(eq)
        self._update_eq_classes(eq)
        # 触发同余闭包传播
        self._propagate_congruence()
    
    def add_theorem(self, theorem: Theorem):
        """添加定理到系统"""
        self.theorems[theorem.name] = theorem
        self.add_equality(theorem.equality)
    
    def _update_eq_classes(self, eq: Equality):
        """根据等式更新等价类"""
        lhs_hash = hash(eq.lhs)
        rhs_hash = hash(eq.rhs)
        
        # 缓存表达式
        self._expr_cache[lhs_hash] = eq.lhs
        self._expr_cache[rhs_hash] = eq.rhs
        
        # 获取或创建等价类
        lhs_class = self._eq_classes.get(lhs_hash)
        rhs_class = self._eq_classes.get(rhs_hash)
        
        if lhs_class is None and rhs_class is None:
            # 两者都不在任何等价类中，创建新类
            # 创建两个单元素类然后合并，这样可以正确选择代表元
            lhs_singleton = EquivalenceClass.singleton(eq.lhs)
            rhs_singleton = EquivalenceClass.singleton(eq.rhs)
            new_class = lhs_singleton.union(rhs_singleton)
            self._eq_classes[lhs_hash] = new_class
            self._eq_classes[rhs_hash] = new_class
            # 添加到待处理队列
            self._pending_updates.add(lhs_hash)
            self._pending_updates.add(rhs_hash)
        elif lhs_class is not None and rhs_class is None:
            # rhs 加入 lhs 的等价类
            rhs_singleton = EquivalenceClass.singleton(eq.rhs)
            new_class = lhs_class.union(rhs_singleton)
            for member in new_class.members:
                self._eq_classes[member] = new_class
            self._pending_updates.add(rhs_hash)
        elif rhs_class is not None and lhs_class is None:
            # lhs 加入 rhs 的等价类
            lhs_singleton = EquivalenceClass.singleton(eq.lhs)
            new_class = rhs_class.union(lhs_singleton)
            for member in new_class.members:
                self._eq_classes[member] = new_class
            self._pending_updates.add(lhs_hash)
        elif lhs_class != rhs_class:
            # 合并两个等价类
            new_class = lhs_class.union(rhs_class)
            for member in new_class.members:
                self._eq_classes[member] = new_class
            self._pending_updates.update(new_class.members)
    
    def _propagate_congruence(self):
        """
        同余闭包传播：
        如果 a ≡ b，那么 f(a) ≡ f(b) 对任何函数 f 成立
        
        注意：这里不自动应用定理，只处理已有的等价关系的同余传播。
        定理应用在 are_equivalent 中按需进行。
        """
        processed = set()
        
        while self._pending_updates:
            updated_hash = self._pending_updates.pop()
            
            if updated_hash in processed:
                continue
            processed.add(updated_hash)
            
            updated_expr = self._expr_cache.get(updated_hash)
            if updated_expr is None:
                continue
            
            # 查找所有包含此表达式作为子表达式的表达式
            for expr_hash, expr in list(self._expr_cache.items()):
                if expr_hash == updated_hash:
                    continue
                
                # 检查是否包含更新的表达式作为子表达式
                if self._contains_subexpr(expr, updated_expr):
                    # 尝试构建等价表达式
                    equivalent_expr = self._replace_subexpr(expr, updated_expr)
                    if equivalent_expr is not None and equivalent_expr != expr:
                        eq_hash = hash(equivalent_expr)
                        if eq_hash not in self._eq_classes:
                            # 创建新等式
                            new_eq = Equality(
                                lhs=expr,
                                rhs=equivalent_expr,
                                justification=Justification(
                                    type=JustificationType.CONGRUENCE,
                                    name="Congruence"
                                )
                            )
                            self.equations.add(new_eq)
                            self._update_eq_classes(new_eq)
    
    def _contains_subexpr(self, expr: Expr, subexpr: Expr) -> bool:
        """检查表达式是否包含子表达式"""
        if expr == subexpr:
            return True
        for arg in expr.args:
            if isinstance(arg, Expr) and self._contains_subexpr(arg, subexpr):
                return True
        return False
    
    def _replace_subexpr(self, expr: Expr, old_subexpr: Expr) -> Optional[Expr]:
        """用等价表达式替换子表达式"""
        if expr == old_subexpr:
            # 找到匹配，返回代表元
            rep = self.get_representative(old_subexpr)
            return rep if rep is not None else None
        
        # 递归替换子表达式
        new_args = []
        changed = False
        for arg in expr.args:
            if isinstance(arg, Expr):
                replaced = self._replace_subexpr(arg, old_subexpr)
                if replaced is not None:
                    new_args.append(replaced)
                    changed = True
                else:
                    new_args.append(arg)
            else:
                new_args.append(arg)
        
        if not changed:
            return None
        
        # 重建表达式
        if expr.op == Op.ADD:
            return ExprCache.add(new_args)
        elif expr.op == Op.MUL:
            return ExprCache.mul(new_args)
        elif expr.op == Op.SUB:
            return ExprCache.sub(new_args[0], new_args[1])
        elif expr.op == Op.DIV:
            return ExprCache.div(new_args[0], new_args[1])
        elif expr.op == Op.POW:
            return ExprCache.pow(new_args[0], new_args[1])
        elif expr.op == Op.NEG:
            return ExprCache.neg(new_args[0])
        elif expr.op == Op.GROUP:
            return ExprCache.group(new_args[0])
        return Expr(expr.op, tuple(new_args))
    
    def are_equivalent(self, expr1: Expr, expr2: Expr) -> bool:
        """检查两个表达式是否等价"""
        # 如果完全相同，直接返回 True
        if expr1 == expr2:
            return True
        
        # 首先缓存表达式
        h1 = hash(expr1)
        h2 = hash(expr2)
        
        if h1 not in self._expr_cache:
            self._expr_cache[h1] = expr1
            self._eq_classes[h1] = EquivalenceClass.singleton(expr1)
        
        if h2 not in self._expr_cache:
            self._expr_cache[h2] = expr2
            self._eq_classes[h2] = EquivalenceClass.singleton(expr2)
        
        # 触发同余闭包检查
        self._pending_updates.add(h1)
        self._pending_updates.add(h2)
        self._propagate_congruence()
        
        # 检查直接等价性
        class1 = self._eq_classes.get(h1)
        class2 = self._eq_classes.get(h2)
        
        if class1 is None or class2 is None:
            return h1 == h2
        
        if class1.representative == class2.representative:
            return True
        
        # 如果直接不等价，尝试应用定理进行扩展
        return self._try_theorem_equivalence(expr1, expr2)
    
    def _try_theorem_equivalence(self, expr1: Expr, expr2: Expr) -> bool:
        """
        尝试通过应用定理来证明两个表达式等价
        
        策略：
        1. 将定理应用到 expr1，看是否能得到与 expr2 等价的表达式
        2. 将定理应用到 expr2，看是否能得到与 expr1 等价的表达式
        """
        # 应用定理到 expr1
        result1 = self._apply_all_theorems(expr1)
        for e1 in result1:
            # 将应用结果添加到系统
            self._add_expr_to_system(e1)
            if self.are_equivalent_direct(e1, expr2):
                return True
        
        # 应用定理到 expr2
        result2 = self._apply_all_theorems(expr2)
        for e2 in result2:
            # 将应用结果添加到系统
            self._add_expr_to_system(e2)
            if self.are_equivalent_direct(expr1, e2):
                return True
        
        # 双向应用
        for e1 in result1:
            for e2 in result2:
                if self.are_equivalent_direct(e1, e2):
                    return True
        
        return False
    
    def _add_expr_to_system(self, expr: Expr):
        """将表达式添加到系统中"""
        h = hash(expr)
        if h not in self._expr_cache:
            self._expr_cache[h] = expr
            self._eq_classes[h] = EquivalenceClass.singleton(expr)
            self._pending_updates.add(h)
            self._propagate_congruence()
    
    def are_equivalent_direct(self, expr1: Expr, expr2: Expr) -> bool:
        """直接检查等价性（不应用定理）"""
        h1 = hash(expr1)
        h2 = hash(expr2)
        
        class1 = self._eq_classes.get(h1)
        class2 = self._eq_classes.get(h2)
        
        if class1 is None or class2 is None:
            return h1 == h2
        
        return class1.representative == class2.representative
    
    def _apply_all_theorems(self, expr: Expr) -> List[Expr]:
        """
        将所有定理应用到表达式，返回所有可能的结果
        包括递归应用到子表达式的结果
        """
        results = []
        
        # 首先递归应用到子表达式
        if expr.op in (Op.ADD, Op.MUL, Op.SUB, Op.DIV, Op.POW):
            for i, arg in enumerate(expr.args):
                if isinstance(arg, Expr):
                    sub_results = self._apply_all_theorems(arg)
                    for sub_result in sub_results:
                        # 用子结果替换原参数
                        new_args = list(expr.args)
                        new_args[i] = sub_result
                        if expr.op == Op.ADD:
                            new_expr = ExprCache.add(new_args)
                        elif expr.op == Op.MUL:
                            new_expr = ExprCache.mul(new_args)
                        elif expr.op == Op.SUB:
                            new_expr = ExprCache.sub(new_args[0], new_args[1])
                        elif expr.op == Op.DIV:
                            new_expr = ExprCache.div(new_args[0], new_args[1])
                        elif expr.op == Op.POW:
                            new_expr = ExprCache.pow(new_args[0], new_args[1])
                        else:
                            new_expr = Expr(expr.op, tuple(new_args))
                        if new_expr != expr:
                            results.append(new_expr)
        
        # 然后应用到顶层表达式
        for theorem in self.theorems.values():
            eq = theorem.equality
            
            # 检查表达式是否匹配定理的 LHS
            bindings = self._match_pattern(eq.lhs, expr)
            if bindings is not None:
                rhs = eq.substitute(bindings).rhs
                if rhs != expr:
                    results.append(rhs)
            
            # 检查表达式是否匹配定理的 RHS（双向匹配）
            bindings = self._match_pattern(eq.rhs, expr)
            if bindings is not None:
                lhs = eq.substitute(bindings).lhs
                if lhs != expr:
                    results.append(lhs)
        
        return results
    
    def _match_pattern(self, pattern: Expr, expr: Expr) -> Optional[Dict[str, Expr]]:
        """
        简单的模式匹配：检查表达式是否匹配模式（支持符号变量）
        """
        bindings = {}
        if not self._match_pattern_recursive(pattern, expr, bindings):
            return None
        return bindings
    
    def _match_pattern_recursive(self, pattern: Expr, expr: Expr, bindings: Dict[str, Expr]) -> bool:
        """递归模式匹配"""
        # 模式变量匹配（单字符小写符号）
        if pattern.op == Op.SYMBOL:
            name = str(pattern.args[0])
            if name.islower() and len(name) == 1:
                if name in bindings:
                    return bindings[name] == expr
                bindings[name] = expr
                return True
        
        # 操作符必须匹配
        if pattern.op != expr.op:
            return False
        
        # 参数数量必须匹配
        if len(pattern.args) != len(expr.args):
            return False
        
        # 递归匹配参数
        for p_arg, e_arg in zip(pattern.args, expr.args):
            if isinstance(p_arg, Expr) and isinstance(e_arg, Expr):
                if not self._match_pattern_recursive(p_arg, e_arg, bindings):
                    return False
            elif p_arg != e_arg:
                return False
        
        return True
    
    def get_equivalence_class(self, expr: Expr) -> Optional[EquivalenceClass]:
        """获取表达式所在的等价类"""
        h = hash(expr)
        return self._eq_classes.get(h)
    
    def get_representative(self, expr: Expr) -> Optional[Expr]:
        """获取表达式的代表元"""
        eq_class = self.get_equivalence_class(expr)
        if eq_class and eq_class.representative:
            return self._expr_cache.get(eq_class.representative)
        return None
    
    def __repr__(self) -> str:
        return f"EqualitySystem(equations={len(self.equations)}, theorems={len(self.theorems)}, eq_classes={len(self._eq_classes)})"


# ═══════════════════════════════════════════════════════════════════════════
# Proof - 证明
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# Standard Axioms - 标准公理库
# ═══════════════════════════════════════════════════════════════════════════

def create_additive_identity() -> Theorem:
    """加法单位元公理: x + 0 = x"""
    x = ExprCache.symbol("x")
    zero = ExprCache.number(0)
    eq = Equality(
        lhs=ExprCache.add([x, zero]),
        rhs=x,
        justification=Justification(
            type=JustificationType.AXIOM,
            name="Additive Identity"
        ),
        variables={"x"}
    )
    return Theorem(name="additive_identity", equality=eq, description="加法单位元")


def create_multiplicative_identity() -> Theorem:
    """乘法单位元公理: x * 1 = x"""
    x = ExprCache.symbol("x")
    one = ExprCache.number(1)
    eq = Equality(
        lhs=ExprCache.mul([x, one]),
        rhs=x,
        justification=Justification(
            type=JustificationType.AXIOM,
            name="Multiplicative Identity"
        ),
        variables={"x"}
    )
    return Theorem(name="multiplicative_identity", equality=eq, description="乘法单位元")


def create_multiplication_by_zero() -> Theorem:
    """乘法零元公理: x * 0 = 0"""
    x = ExprCache.symbol("x")
    zero = ExprCache.number(0)
    eq = Equality(
        lhs=ExprCache.mul([x, zero]),
        rhs=zero,
        justification=Justification(
            type=JustificationType.AXIOM,
            name="Multiplication by Zero"
        ),
        variables={"x"}
    )
    return Theorem(name="multiplication_by_zero", equality=eq, description="乘法零元")


def create_additive_commutativity() -> Theorem:
    """加法交换律: x + y = y + x"""
    x = ExprCache.symbol("x")
    y = ExprCache.symbol("y")
    eq = Equality(
        lhs=ExprCache.add([x, y]),
        rhs=ExprCache.add([y, x]),
        justification=Justification(
            type=JustificationType.AXIOM,
            name="Additive Commutativity"
        ),
        variables={"x", "y"}
    )
    return Theorem(name="additive_commutativity", equality=eq, description="加法交换律")


def create_multiplicative_commutativity() -> Theorem:
    """乘法交换律: x * y = y * x"""
    x = ExprCache.symbol("x")
    y = ExprCache.symbol("y")
    eq = Equality(
        lhs=ExprCache.mul([x, y]),
        rhs=ExprCache.mul([y, x]),
        justification=Justification(
            type=JustificationType.AXIOM,
            name="Multiplicative Commutativity"
        ),
        variables={"x", "y"}
    )
    return Theorem(name="multiplicative_commutativity", equality=eq, description="乘法交换律")


# ═══════════════════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════════════════

def create_std_axioms() -> List[Theorem]:
    """创建标准公理集合"""
    return [
        create_additive_identity(),
        create_multiplicative_identity(),
        create_multiplication_by_zero(),
        create_additive_commutativity(),
        create_multiplicative_commutativity(),
    ]


def create_std_equality_system() -> EqualitySystem:
    """创建包含标准公理的等式系统"""
    system = EqualitySystem()
    for axiom in create_std_axioms():
        system.add_theorem(axiom)
    return system
