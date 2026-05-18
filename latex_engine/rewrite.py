"""Rewrite Engine - 重写引擎

实现模式匹配和树重写功能，这是数学推理的核心。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple, Union
from copy import deepcopy

from .ast import *
from .types import MathType


# ═══════════════════════════════════════════════
# Pattern AST - 模式抽象语法树
# ═══════════════════════════════════════════════

class PatternNode(ABC):
    """模式节点基类"""
    
    @abstractmethod
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配节点并返回绑定"""
        pass
    
    @abstractmethod
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """使用绑定替换模式变量"""
        pass


class PatternVar(PatternNode):
    """模式变量 - 可以匹配任何节点"""
    
    def __init__(self, name: str, math_type: Optional[MathType] = None):
        self.name = name
        self.math_type = math_type
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配任意节点"""
        # 检查类型约束
        if self.math_type is not None:
            if isinstance(node, TypedNode) and node.math_type != self.math_type:
                return None
        
        # 如果变量已绑定，检查是否匹配
        if self.name in bindings:
            existing = bindings[self.name]
            if not nodes_equal(node, existing):
                return None
            return bindings
        
        # 绑定新变量
        new_bindings = bindings.copy()
        new_bindings[self.name] = deepcopy(node)
        return new_bindings
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """替换为绑定的值"""
        if self.name in bindings:
            return deepcopy(bindings[self.name])
        raise ValueError(f"Pattern variable {self.name} not bound")
    
    def __repr__(self):
        return f"PatternVar({self.name})"


class PatternLiteral(PatternNode):
    """模式字面量 - 匹配特定值"""
    
    def __init__(self, value: Union[int, float, str]):
        self.value = value
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配字面量"""
        if isinstance(node, NumberNode):
            if node.value == self.value:
                return bindings.copy()  # 返回副本，避免修改原字典
        elif isinstance(node, SymbolNode):
            if node.name == self.value:
                return bindings.copy()  # 返回副本，避免修改原字典
        return None
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """返回字面量节点"""
        if isinstance(self.value, (int, float)):
            return NumberNode(self.value)
        else:
            return SymbolNode(self.value)
    
    def __repr__(self):
        return f"PatternLiteral({self.value})"


class PatternAdd(PatternNode):
    """加法模式"""
    
    def __init__(self, left: PatternNode, right: PatternNode):
        self.left = left
        self.right = right
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配加法节点"""
        if isinstance(node, AddNode):
            # 尝试 left + right
            left_bindings = self.left.match(node.left, bindings)
            if left_bindings:
                right_bindings = self.right.match(node.right, left_bindings)
                if right_bindings:
                    return right_bindings
            
            # 尝试交换律：right + left
            left_bindings = self.left.match(node.right, bindings)
            if left_bindings:
                right_bindings = self.right.match(node.left, left_bindings)
                if right_bindings:
                    return right_bindings
        
        return None
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """替换为加法节点"""
        left = self.left.substitute(bindings)
        right = self.right.substitute(bindings)
        return AddNode(left, right)
    
    def __repr__(self):
        return f"PatternAdd({self.left}, {self.right})"


class PatternMultiply(PatternNode):
    """乘法模式"""
    
    def __init__(self, left: PatternNode, right: PatternNode):
        self.left = left
        self.right = right
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配乘法节点"""
        if isinstance(node, MultiplyNode):
            # 尝试 left * right
            left_bindings = self.left.match(node.left, bindings)
            if left_bindings:
                right_bindings = self.right.match(node.right, left_bindings)
                if right_bindings:
                    return right_bindings
            
            # 尝试交换律：right * left
            left_bindings = self.left.match(node.right, bindings)
            if left_bindings:
                right_bindings = self.right.match(node.left, left_bindings)
                if right_bindings:
                    return right_bindings
        
        return None
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """替换为乘法节点"""
        left = self.left.substitute(bindings)
        right = self.right.substitute(bindings)
        return MultiplyNode(left, right)
    
    def __repr__(self):
        return f"PatternMultiply({self.left}, {self.right})"


class PatternPower(PatternNode):
    """幂运算模式"""
    
    def __init__(self, base: PatternNode, exponent: PatternNode):
        self.base = base
        self.exponent = exponent
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配幂运算节点"""
        if isinstance(node, PowerNode):
            base_bindings = self.base.match(node.base, bindings)
            if base_bindings:
                return self.exponent.match(node.exponent, base_bindings)
        return None
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """替换为幂运算节点"""
        base = self.base.substitute(bindings)
        exponent = self.exponent.substitute(bindings)
        return PowerNode(base, exponent)
    
    def __repr__(self):
        return f"PatternPower({self.base}, {self.exponent})"


class PatternNegate(PatternNode):
    """取反模式"""
    
    def __init__(self, operand: PatternNode):
        self.operand = operand
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配取反节点"""
        if isinstance(node, NegateNode):
            return self.operand.match(node.operand, bindings)
        return None
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """替换为取反节点"""
        operand = self.operand.substitute(bindings)
        return NegateNode(operand)
    
    def __repr__(self):
        return f"PatternNegate({self.operand})"


class PatternSymbol(PatternNode):
    """符号模式 - 匹配特定符号"""
    
    def __init__(self, name: str):
        self.name = name
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配符号节点"""
        if isinstance(node, SymbolNode) and node.name == self.name:
            return bindings
        return None
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """返回符号节点"""
        return SymbolNode(self.name)
    
    def __repr__(self):
        return f"PatternSymbol({self.name})"


class PatternFunction(PatternNode):
    """函数调用模式"""
    
    def __init__(self, name: str, args: List[PatternNode]):
        self.name = name
        self.args = args
    
    def match(self, node: ASTNode, bindings: Dict[str, ASTNode]) -> Optional[Dict[str, ASTNode]]:
        """匹配函数调用节点"""
        if isinstance(node, FunctionNode) and node.name.lower() == self.name.lower():
            if len(node.arguments) != len(self.args):
                return None
            
            current_bindings = bindings
            for i, (pattern_arg, node_arg) in enumerate(zip(self.args, node.arguments)):
                current_bindings = pattern_arg.match(node_arg, current_bindings)
                if current_bindings is None:
                    return None
            
            return current_bindings
        return None
    
    def substitute(self, bindings: Dict[str, ASTNode]) -> ASTNode:
        """替换为函数调用节点"""
        args = [arg.substitute(bindings) for arg in self.args]
        return FunctionNode(self.name, args)
    
    def __repr__(self):
        return f"PatternFunction({self.name}, {self.args})"


# ═══════════════════════════════════════════════
# Rewrite Rule - 重写规则
# ═══════════════════════════════════════════════

class RewriteRule:
    """重写规则"""
    
    def __init__(self, pattern: PatternNode, replacement: PatternNode, 
                 condition=None, name: str = ""):
        self.pattern = pattern
        self.replacement = replacement
        self.condition = condition  # 可选的条件函数
        self.name = name
    
    def apply(self, node: ASTNode) -> Optional[ASTNode]:
        """尝试应用规则"""
        bindings = self.pattern.match(node, {})
        if bindings is None:
            return None
        
        # 检查条件
        if self.condition is not None:
            if not self.condition(bindings):
                return None
        
        # 应用替换
        result = self.replacement.substitute(bindings)
        # 确保返回的是干净的AST节点，不包含规则名称
        return result
    
    def match(self, node: ASTNode) -> Optional[Dict[str, ASTNode]]:
        """检查是否匹配"""
        return self.pattern.match(node, {})
    
    def __repr__(self):
        return f"RewriteRule({self.name})"


# ═══════════════════════════════════════════════
# Rewrite Engine - 重写引擎
# ═══════════════════════════════════════════════

class RewriteEngine:
    """重写引擎"""
    
    def __init__(self):
        self.rules: List[RewriteRule] = []
    
    def add_rule(self, rule: RewriteRule):
        """添加规则"""
        self.rules.append(rule)
    
    def add_rules(self, rules: List[RewriteRule]):
        """添加多个规则"""
        self.rules.extend(rules)
    
    def rewrite(self, node: ASTNode, max_iterations: int = 100) -> Tuple[ASTNode, List[str]]:
        """重写表达式，返回最终结果和重写步骤"""
        current = node  # 不使用 deepcopy，直接引用
        steps = []
        changed = True
        iterations = 0
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            # 对当前节点尝试所有规则
            rule_applied = False
            for rule in self.rules:
                result = rule.apply(current)
                if result is not None:
                    # 记录步骤前先获取字符串表示
                    before_str = current.to_latex()
                    after_str = result.to_latex()
                    steps.append(f"{before_str} → {after_str} [{rule.name}]")
                    current = result
                    changed = True
                    rule_applied = True
                    break  # 每次迭代只应用一个规则
            
            # 无论是否应用规则，都尝试递归重写子节点
            # 这样可以处理 GroupNode 内部的表达式
            current, sub_steps = self._rewrite_recursive(current)
            steps.extend(sub_steps)
            if sub_steps:
                changed = True
        
        return current, steps
    
    def _rewrite_recursive(self, node: ASTNode) -> Tuple[ASTNode, List[str]]:
        """递归重写子节点"""
        steps = []
        
        if isinstance(node, AddNode):
            node.left, left_steps = self.rewrite(node.left)
            node.right, right_steps = self.rewrite(node.right)
            steps.extend(left_steps)
            steps.extend(right_steps)
        elif isinstance(node, SubtractNode):
            node.left, left_steps = self.rewrite(node.left)
            node.right, right_steps = self.rewrite(node.right)
            steps.extend(left_steps)
            steps.extend(right_steps)
        elif isinstance(node, MultiplyNode):
            node.left, left_steps = self.rewrite(node.left)
            node.right, right_steps = self.rewrite(node.right)
            steps.extend(left_steps)
            steps.extend(right_steps)
        elif isinstance(node, DivideNode):
            node.numerator, num_steps = self.rewrite(node.numerator)
            node.denominator, den_steps = self.rewrite(node.denominator)
            steps.extend(num_steps)
            steps.extend(den_steps)
        elif isinstance(node, PowerNode):
            node.base, base_steps = self.rewrite(node.base)
            node.exponent, exp_steps = self.rewrite(node.exponent)
            steps.extend(base_steps)
            steps.extend(exp_steps)
        elif isinstance(node, NegateNode):
            node.operand, op_steps = self.rewrite(node.operand)
            steps.extend(op_steps)
        elif isinstance(node, FunctionNode):
            new_args = []
            for arg in node.arguments:
                arg, arg_steps = self.rewrite(arg)
                new_args.append(arg)
                steps.extend(arg_steps)
            node.arguments = new_args
        elif isinstance(node, GroupNode):
            new_content = []
            for item in node.content:
                item, item_steps = self.rewrite(item)
                new_content.append(item)
                steps.extend(item_steps)
            node.content = new_content
            # 如果 GroupNode 只包含一个表达式，返回该表达式（展开括号）
            if len(node.content) == 1:
                return node.content[0], steps
        
        return node, steps
    
    def match(self, node: ASTNode) -> List[Tuple[RewriteRule, Dict[str, ASTNode]]]:
        """找到所有匹配的规则"""
        matches = []
        for rule in self.rules:
            bindings = rule.match(node)
            if bindings is not None:
                matches.append((rule, bindings))
        return matches


# ═══════════════════════════════════════════════
# Rule DSL - 规则领域专用语言
# ═══════════════════════════════════════════════

class RuleParser:
    """规则 DSL 解析器"""
    
    def __init__(self):
        pass
    
    def parse(self, rule_str: str) -> RewriteRule:
        """解析规则字符串，如 "x + 0 -> x" """
        # 分割左右两边
        parts = rule_str.split('->')
        if len(parts) != 2:
            raise ValueError("Invalid rule format. Use 'pattern -> replacement'")
        
        pattern_str = parts[0].strip()
        replacement_str = parts[1].strip()
        
        # 移除替换表达式中的注释（/* ... */）
        if '/*' in replacement_str:
            replacement_str = replacement_str[:replacement_str.find('/*')].strip()
        
        # 解析模式和替换
        pattern = self._parse_expression(pattern_str)
        replacement = self._parse_expression(replacement_str)
        
        # 提取规则名称
        name = self._extract_name(rule_str)
        
        return RewriteRule(pattern, replacement, name=name)
    
    def _extract_name(self, rule_str: str) -> str:
        """从注释中提取规则名称"""
        if '/*' in rule_str and '*/' in rule_str:
            start = rule_str.find('/*') + 2
            end = rule_str.find('*/')
            return rule_str[start:end].strip()
        return ""
    
    def _parse_expression(self, expr_str: str) -> PatternNode:
        """解析表达式字符串为模式节点"""
        expr_str = expr_str.strip()
        
        # 检查是否为模式变量（以大写字母开头）
        if expr_str.isidentifier() and expr_str[0].isupper():
            return PatternVar(expr_str)
        
        # 检查是否为数字
        try:
            if '.' in expr_str:
                return PatternLiteral(float(expr_str))
            else:
                return PatternLiteral(int(expr_str))
        except ValueError:
            pass
        
        # 检查是否为符号（小写字母）
        if expr_str.isidentifier() and expr_str[0].islower():
            return PatternSymbol(expr_str)
        
        # 处理二元运算
        # 找最低优先级的运算符
        operators = [('+', PatternAdd), ('-', PatternAdd), 
                     ('*', PatternMultiply), ('/', PatternMultiply),
                     ('^', PatternPower)]
        
        for op, pattern_class in operators:
            # 不在括号内的运算符
            depth = 0
            for i, char in enumerate(expr_str):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                elif char == op and depth == 0:
                    left = self._parse_expression(expr_str[:i])
                    right = self._parse_expression(expr_str[i+1:])
                    return pattern_class(left, right)
        
        # 处理函数调用
        if '(' in expr_str and ')' in expr_str:
            paren_start = expr_str.find('(')
            paren_end = expr_str.rfind(')')
            
            func_name = expr_str[:paren_start].strip()
            args_str = expr_str[paren_start+1:paren_end]
            
            args = []
            depth = 0
            current_arg = ""
            for char in args_str:
                if char == '(':
                    depth += 1
                    current_arg += char
                elif char == ')':
                    depth -= 1
                    current_arg += char
                elif char == ',' and depth == 0:
                    if current_arg.strip():
                        args.append(self._parse_expression(current_arg))
                    current_arg = ""
                else:
                    current_arg += char
            if current_arg.strip():
                args.append(self._parse_expression(current_arg))
            
            return PatternFunction(func_name, args)
        
        # 处理括号
        if expr_str.startswith('(') and expr_str.endswith(')'):
            return self._parse_expression(expr_str[1:-1])
        
        # 处理负号
        if expr_str.startswith('-'):
            operand = self._parse_expression(expr_str[1:])
            return PatternNegate(operand)
        
        # 默认视为符号
        return PatternSymbol(expr_str)


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════

def nodes_equal(node1: ASTNode, node2: ASTNode) -> bool:
    """检查两个节点是否相等"""
    if type(node1) != type(node2):
        return False
    
    if isinstance(node1, NumberNode):
        return node1.value == node2.value
    elif isinstance(node1, SymbolNode):
        return node1.name == node2.name
    elif isinstance(node1, AddNode):
        return nodes_equal(node1.left, node2.left) and nodes_equal(node1.right, node2.right)
    elif isinstance(node1, MultiplyNode):
        return nodes_equal(node1.left, node2.left) and nodes_equal(node1.right, node2.right)
    elif isinstance(node1, PowerNode):
        return nodes_equal(node1.base, node2.base) and nodes_equal(node1.exponent, node2.exponent)
    elif isinstance(node1, NegateNode):
        return nodes_equal(node1.operand, node2.operand)
    elif isinstance(node1, FunctionNode):
        if node1.name != node2.name:
            return False
        if len(node1.arguments) != len(node2.arguments):
            return False
        return all(nodes_equal(a, b) for a, b in zip(node1.arguments, node2.arguments))
    
    return True


# ═══════════════════════════════════════════════
# 预定义规则库
# ═══════════════════════════════════════════════

def create_default_rules() -> List[RewriteRule]:
    """创建默认的数学重写规则"""
    parser = RuleParser()
    rules = []
    
    # 恒等元规则
    rules.append(parser.parse("X + 0 -> X /* Additive Identity */"))
    rules.append(parser.parse("0 + X -> X /* Additive Identity (commuted) */"))
    rules.append(parser.parse("X * 1 -> X /* Multiplicative Identity */"))
    rules.append(parser.parse("1 * X -> X /* Multiplicative Identity (commuted) */"))
    rules.append(parser.parse("X * 0 -> 0 /* Multiplication by zero */"))
    rules.append(parser.parse("0 * X -> 0 /* Multiplication by zero (commuted) */"))
    
    # 逆元规则
    rules.append(parser.parse("X + (-X) -> 0 /* Additive Inverse */"))
    rules.append(parser.parse("(-X) + X -> 0 /* Additive Inverse (commuted) */"))
    
    # 合并同类项
    rules.append(parser.parse("X + X -> 2 * X /* Combine like terms */"))
    
    # 幂运算规则
    rules.append(parser.parse("X^0 -> 1 /* Zero exponent */"))
    rules.append(parser.parse("X^1 -> X /* Exponent of one */"))
    
    # 三角函数恒等式
    rules.append(parser.parse("sin(X)^2 + cos(X)^2 -> 1 /* Pythagorean identity */"))
    
    # 分配律
    rules.append(parser.parse("A * (B + C) -> A * B + A * C /* Distributive */"))
    rules.append(parser.parse("(A + B) * C -> A * C + B * C /* Distributive (commuted) */"))
    
    return rules


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def rewrite(expr: ASTNode, rules: Optional[List[RewriteRule]] = None) -> Tuple[ASTNode, List[str]]:
    """重写表达式"""
    engine = RewriteEngine()
    if rules is None:
        rules = create_default_rules()
    engine.add_rules(rules)
    return engine.rewrite(expr)


def parse_rule(rule_str: str) -> RewriteRule:
    """解析规则字符串"""
    parser = RuleParser()
    return parser.parse(rule_str)