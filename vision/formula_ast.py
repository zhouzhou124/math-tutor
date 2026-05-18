"""vision/formula_ast.py — Formula AST（数学公式抽象语法树）

═══════════════════════════════════════════════════════════════
核心思想 — 从 SpatialGraph 到 FormulaAST
═══════════════════════════════════════════════════════════════

  你已经有：
    MathExpression  (math_ir.py)
    ExprCategory    (math_ir.py)
    ExprNode        (expression_ast.py)

  但缺少：视觉层面的公式结构 AST。

  区别：
    expression_ast.py — 计算层 AST（求值、简化、符号计算）
    formula_ast.py    — 视觉层 AST（从图像空间关系恢复公式结构）

  数据流：
    SpatialGraph → FormulaAST → MathExpression/ExprNode

  例如 ∫₀¹ x² dx：

    SpatialGraph:
      0 --limit_lower--> ∫
      1 --limit_upper--> ∫
      x --argument--> ∫
      ² --superscript--> x

    FormulaAST:
      IntegralNode(
          lower=NumberNode(0),
          upper=NumberNode(1),
          body=SuperscriptNode(
              base=VariableNode("x"),
              exponent=NumberNode(2)
          ),
          var=VariableNode("x")
      )

═══════════════════════════════════════════════════════════════
AST 类型层次
═══════════════════════════════════════════════════════════════

  ExprNode (基类)
  ├── NumberNode
  ├── VariableNode
  ├── OperatorNode
  ├── FractionNode
  ├── SuperscriptNode
  ├── SubscriptNode
  ├── IntegralNode
  ├── SumNode
  ├── ProductNode
  ├── LimitNode
  ├── MatrixNode
  ├── FunctionNode
  ├── RadicalNode
  ├── BracketNode
  └── SequenceNode

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Optional, Dict, Any


class FormulaNodeType(Enum):
    NUMBER = "number"
    VARIABLE = "variable"
    OPERATOR = "operator"
    FRACTION = "fraction"
    SUPERSCRIPT = "superscript"
    SUBSCRIPT = "subscript"
    INTEGRAL = "integral"
    SUM = "sum"
    PRODUCT = "product"
    LIMIT = "limit"
    MATRIX = "matrix"
    FUNCTION = "function"
    RADICAL = "radical"
    BRACKET = "bracket"
    SEQUENCE = "sequence"
    DERIVATIVE = "derivative"
    PARTIAL_DERIVATIVE = "partial_derivative"
    BIG_OPERATOR = "big_operator"
    ROOT = "root"


@dataclass
class FormulaAST:
    """数学公式 AST — 视觉层面的公式结构表示

    与 expression_ast.ExprNode 的区别：
      - FormulaAST 从图像空间关系恢复
      - ExprNode 从 LaTeX 文本解析
      - FormulaAST 可以转换为 ExprNode

    用法：
        ast = FormulaAST(root=IntegralNode(...))
        latex = ast.to_latex()
        expr = ast.to_expr_node()  # 转换为 expression_ast.ExprNode
    """
    root: Optional[ExprNode] = None
    source: str = ""
    confidence: float = 0.0
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_latex(self) -> str:
        if self.root is None:
            return ""
        return self.root.to_latex()

    def to_dict(self) -> dict:
        return {
            "root": self.root.to_dict() if self.root else None,
            "source": self.source,
            "confidence": self.confidence,
            "bbox": list(self.bbox),
        }

    @classmethod
    def from_dict(cls, d: dict) -> FormulaAST:
        root = ExprNode.from_dict(d["root"]) if d.get("root") else None
        return cls(
            root=root,
            source=d.get("source", ""),
            confidence=d.get("confidence", 0.0),
            bbox=tuple(d.get("bbox", (0, 0, 0, 0))),
        )


@dataclass
class ExprNode:
    """公式 AST 节点基类

    所有公式节点共享的接口：
      - to_latex() → LaTeX 字符串
      - to_dict() / from_dict() → 序列化
      - children → 子节点列表
      - node_type → 节点类型
    """
    node_type: FormulaNodeType = FormulaNodeType.NUMBER
    confidence: float = 0.0

    @property
    def children(self) -> List[ExprNode]:
        return []

    def to_latex(self) -> str:
        return ""

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type.value,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ExprNode:
        nt = FormulaNodeType(d.get("node_type", "number"))
        dispatch = {
            FormulaNodeType.NUMBER: NumberNode,
            FormulaNodeType.VARIABLE: VariableNode,
            FormulaNodeType.OPERATOR: OperatorNode,
            FormulaNodeType.FRACTION: FractionNode,
            FormulaNodeType.SUPERSCRIPT: SuperscriptNode,
            FormulaNodeType.SUBSCRIPT: SubscriptNode,
            FormulaNodeType.INTEGRAL: IntegralNode,
            FormulaNodeType.SUM: SumNode,
            FormulaNodeType.PRODUCT: ProductNode,
            FormulaNodeType.LIMIT: LimitNode,
            FormulaNodeType.MATRIX: MatrixNode,
            FormulaNodeType.FUNCTION: FunctionNode,
            FormulaNodeType.RADICAL: RadicalNode,
            FormulaNodeType.BRACKET: BracketNode,
            FormulaNodeType.SEQUENCE: SequenceNode,
            FormulaNodeType.DERIVATIVE: DerivativeNode,
        }
        target_cls = dispatch.get(nt, cls)
        if hasattr(target_cls, "_from_dict_impl"):
            return target_cls._from_dict_impl(d)
        return target_cls(
            node_type=nt,
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class NumberNode(ExprNode):
    """数值节点 — 0, 1, 3.14, ..."""
    value: str = ""
    node_type: FormulaNodeType = field(default=FormulaNodeType.NUMBER, init=False)

    @property
    def children(self) -> List[ExprNode]:
        return []

    def to_latex(self) -> str:
        return self.value

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["value"] = self.value
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> NumberNode:
        return cls(value=d.get("value", ""), confidence=d.get("confidence", 0.0))


@dataclass
class VariableNode(ExprNode):
    """变量节点 — x, y, a, b, ..."""
    name: str = ""
    subscript: Optional[str] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.VARIABLE, init=False)

    @property
    def children(self) -> List[ExprNode]:
        return []

    def to_latex(self) -> str:
        if self.subscript:
            return f"{self.name}_{{{self.subscript}}}"
        return self.name

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["name"] = self.name
        if self.subscript:
            d["subscript"] = self.subscript
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> VariableNode:
        return cls(
            name=d.get("name", ""),
            subscript=d.get("subscript"),
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class OperatorNode(ExprNode):
    """运算符节点 — +, -, ×, ÷, =, ≠, ≤, ≥, ∈"""
    symbol: str = ""
    left: Optional[ExprNode] = None
    right: Optional[ExprNode] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.OPERATOR, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.left:
            result.append(self.left)
        if self.right:
            result.append(self.right)
        return result

    def to_latex(self) -> str:
        left_l = self.left.to_latex() if self.left else ""
        right_l = self.right.to_latex() if self.right else ""

        symbol_map = {
            "+": "+", "-": "-", "×": "\\times", "÷": "\\div",
            "=": "=", "≠": "\\neq", "≤": "\\leq", "≥": "\\geq",
            "∈": "\\in", "∉": "\\notin", "⊂": "\\subset",
            "→": "\\to", "⇒": "\\Rightarrow", "⟹": "\\implies",
            "±": "\\pm", "∓": "\\mp", "≈": "\\approx",
            "<": "<", ">": ">",
        }
        sym = symbol_map.get(self.symbol, self.symbol)

        if self.symbol in {"+", "-"} and right_l and right_l.startswith("-"):
            return f"{left_l} {sym} {right_l[1:]}"
        return f"{left_l} {sym} {right_l}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["symbol"] = self.symbol
        if self.left:
            d["left"] = self.left.to_dict()
        if self.right:
            d["right"] = self.right.to_dict()
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> OperatorNode:
        left = ExprNode.from_dict(d["left"]) if d.get("left") else None
        right = ExprNode.from_dict(d["right"]) if d.get("right") else None
        return cls(
            symbol=d.get("symbol", ""),
            left=left,
            right=right,
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class FractionNode(ExprNode):
    """分数节点 — \\frac{numerator}{denominator}

    从 SpatialGraph 的分数线检测恢复：
      分数线上方 → numerator
      分数线下方 → denominator
    """
    numerator: Optional[ExprNode] = None
    denominator: Optional[ExprNode] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.FRACTION, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.numerator:
            result.append(self.numerator)
        if self.denominator:
            result.append(self.denominator)
        return result

    def to_latex(self) -> str:
        num = self.numerator.to_latex() if self.numerator else ""
        den = self.denominator.to_latex() if self.denominator else ""
        return f"\\frac{{{num}}}{{{den}}}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.numerator:
            d["numerator"] = self.numerator.to_dict()
        if self.denominator:
            d["denominator"] = self.denominator.to_dict()
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> FractionNode:
        num = ExprNode.from_dict(d["numerator"]) if d.get("numerator") else None
        den = ExprNode.from_dict(d["denominator"]) if d.get("denominator") else None
        return cls(numerator=num, denominator=den, confidence=d.get("confidence", 0.0))


@dataclass
class SuperscriptNode(ExprNode):
    """上标节点 — base^{exponent}

    从 SpatialGraph 的 superscript 关系恢复：
      主体上方偏右的小符号 → exponent
    """
    base: Optional[ExprNode] = None
    exponent: Optional[ExprNode] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.SUPERSCRIPT, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.base:
            result.append(self.base)
        if self.exponent:
            result.append(self.exponent)
        return result

    def to_latex(self) -> str:
        base_l = self.base.to_latex() if self.base else ""
        exp_l = self.exponent.to_latex() if self.exponent else ""
        if len(exp_l) == 1:
            return f"{base_l}^{exp_l}"
        return f"{base_l}^{{{exp_l}}}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.base:
            d["base"] = self.base.to_dict()
        if self.exponent:
            d["exponent"] = self.exponent.to_dict()
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> SuperscriptNode:
        base = ExprNode.from_dict(d["base"]) if d.get("base") else None
        exp = ExprNode.from_dict(d["exponent"]) if d.get("exponent") else None
        return cls(base=base, exponent=exp, confidence=d.get("confidence", 0.0))


@dataclass
class SubscriptNode(ExprNode):
    """下标节点 — base_{subscript}

    从 SpatialGraph 的 subscript 关系恢复：
      主体下方偏右的小符号 → subscript
    """
    base: Optional[ExprNode] = None
    subscript: Optional[ExprNode] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.SUBSCRIPT, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.base:
            result.append(self.base)
        if self.subscript:
            result.append(self.subscript)
        return result

    def to_latex(self) -> str:
        base_l = self.base.to_latex() if self.base else ""
        sub_l = self.subscript.to_latex() if self.subscript else ""
        if len(sub_l) == 1:
            return f"{base_l}_{sub_l}"
        return f"{base_l}_{{{sub_l}}}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.base:
            d["base"] = self.base.to_dict()
        if self.subscript:
            d["subscript"] = self.subscript.to_dict()
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> SubscriptNode:
        base = ExprNode.from_dict(d["base"]) if d.get("base") else None
        sub = ExprNode.from_dict(d["subscript"]) if d.get("subscript") else None
        return cls(base=base, subscript=sub, confidence=d.get("confidence", 0.0))


@dataclass
class IntegralNode(ExprNode):
    """积分节点 — \\int_{lower}^{upper} body d(var)

    从 SpatialGraph 的大操作符检测恢复：
      ∫ 上方 → upper (limit_upper)
      ∫ 下方 → lower (limit_lower)
      ∫ 右侧 → body (argument)
    """
    lower: Optional[ExprNode] = None
    upper: Optional[ExprNode] = None
    body: Optional[ExprNode] = None
    var: Optional[ExprNode] = None
    is_double: bool = False
    is_triple: bool = False
    is_contour: bool = False
    node_type: FormulaNodeType = field(default=FormulaNodeType.INTEGRAL, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.lower:
            result.append(self.lower)
        if self.upper:
            result.append(self.upper)
        if self.body:
            result.append(self.body)
        if self.var:
            result.append(self.var)
        return result

    def to_latex(self) -> str:
        if self.is_contour:
            sym = "\\oint"
        elif self.is_triple:
            sym = "\\iiint"
        elif self.is_double:
            sym = "\\iint"
        else:
            sym = "\\int"

        lower_l = f"_{{{self.lower.to_latex()}}}" if self.lower else ""
        upper_l = f"^{{{self.upper.to_latex()}}}" if self.upper else ""
        body_l = self.body.to_latex() if self.body else ""
        var_l = f"\\,d{self.var.to_latex()}" if self.var else ""

        return f"{sym}{lower_l}{upper_l} {body_l}{var_l}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.lower:
            d["lower"] = self.lower.to_dict()
        if self.upper:
            d["upper"] = self.upper.to_dict()
        if self.body:
            d["body"] = self.body.to_dict()
        if self.var:
            d["var"] = self.var.to_dict()
        d["is_double"] = self.is_double
        d["is_triple"] = self.is_triple
        d["is_contour"] = self.is_contour
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> IntegralNode:
        return cls(
            lower=ExprNode.from_dict(d["lower"]) if d.get("lower") else None,
            upper=ExprNode.from_dict(d["upper"]) if d.get("upper") else None,
            body=ExprNode.from_dict(d["body"]) if d.get("body") else None,
            var=ExprNode.from_dict(d["var"]) if d.get("var") else None,
            is_double=d.get("is_double", False),
            is_triple=d.get("is_triple", False),
            is_contour=d.get("is_contour", False),
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class SumNode(ExprNode):
    """求和节点 — \\sum_{lower}^{upper} body"""
    lower: Optional[ExprNode] = None
    upper: Optional[ExprNode] = None
    body: Optional[ExprNode] = None
    var: Optional[ExprNode] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.SUM, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.lower:
            result.append(self.lower)
        if self.upper:
            result.append(self.upper)
        if self.body:
            result.append(self.body)
        if self.var:
            result.append(self.var)
        return result

    def to_latex(self) -> str:
        lower_l = f"_{{{self.lower.to_latex()}}}" if self.lower else ""
        upper_l = f"^{{{self.upper.to_latex()}}}" if self.upper else ""
        body_l = self.body.to_latex() if self.body else ""
        return f"\\sum{lower_l}{upper_l} {body_l}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.lower:
            d["lower"] = self.lower.to_dict()
        if self.upper:
            d["upper"] = self.upper.to_dict()
        if self.body:
            d["body"] = self.body.to_dict()
        if self.var:
            d["var"] = self.var.to_dict()
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> SumNode:
        return cls(
            lower=ExprNode.from_dict(d["lower"]) if d.get("lower") else None,
            upper=ExprNode.from_dict(d["upper"]) if d.get("upper") else None,
            body=ExprNode.from_dict(d["body"]) if d.get("body") else None,
            var=ExprNode.from_dict(d["var"]) if d.get("var") else None,
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class ProductNode(ExprNode):
    """求积节点 — \\prod_{lower}^{upper} body"""
    lower: Optional[ExprNode] = None
    upper: Optional[ExprNode] = None
    body: Optional[ExprNode] = None
    var: Optional[ExprNode] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.PRODUCT, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.lower:
            result.append(self.lower)
        if self.upper:
            result.append(self.upper)
        if self.body:
            result.append(self.body)
        if self.var:
            result.append(self.var)
        return result

    def to_latex(self) -> str:
        lower_l = f"_{{{self.lower.to_latex()}}}" if self.lower else ""
        upper_l = f"^{{{self.upper.to_latex()}}}" if self.upper else ""
        body_l = self.body.to_latex() if self.body else ""
        return f"\\prod{lower_l}{upper_l} {body_l}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.lower:
            d["lower"] = self.lower.to_dict()
        if self.upper:
            d["upper"] = self.upper.to_dict()
        if self.body:
            d["body"] = self.body.to_dict()
        if self.var:
            d["var"] = self.var.to_dict()
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> ProductNode:
        return cls(
            lower=ExprNode.from_dict(d["lower"]) if d.get("lower") else None,
            upper=ExprNode.from_dict(d["upper"]) if d.get("upper") else None,
            body=ExprNode.from_dict(d["body"]) if d.get("body") else None,
            var=ExprNode.from_dict(d["var"]) if d.get("var") else None,
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class LimitNode(ExprNode):
    """极限节点 — \\lim_{var → approach} body"""
    var: Optional[ExprNode] = None
    approach: Optional[ExprNode] = None
    body: Optional[ExprNode] = None
    direction: Optional[str] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.LIMIT, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.var:
            result.append(self.var)
        if self.approach:
            result.append(self.approach)
        if self.body:
            result.append(self.body)
        return result

    def to_latex(self) -> str:
        var_l = self.var.to_latex() if self.var else ""
        approach_l = self.approach.to_latex() if self.approach else ""
        body_l = self.body.to_latex() if self.body else ""

        dir_str = ""
        if self.direction == "right":
            dir_str = "^+"
        elif self.direction == "left":
            dir_str = "^-"

        return f"\\lim_{{{var_l} \\to {approach_l}{dir_str}}} {body_l}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.var:
            d["var"] = self.var.to_dict()
        if self.approach:
            d["approach"] = self.approach.to_dict()
        if self.body:
            d["body"] = self.body.to_dict()
        if self.direction:
            d["direction"] = self.direction
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> LimitNode:
        return cls(
            var=ExprNode.from_dict(d["var"]) if d.get("var") else None,
            approach=ExprNode.from_dict(d["approach"]) if d.get("approach") else None,
            body=ExprNode.from_dict(d["body"]) if d.get("body") else None,
            direction=d.get("direction"),
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class MatrixNode(ExprNode):
    """矩阵节点 — \\begin{pmatrix} ... \\end{pmatrix}"""
    rows: List[List[ExprNode]] = field(default_factory=list)
    delimiter: str = "pmatrix"
    node_type: FormulaNodeType = field(default=FormulaNodeType.MATRIX, init=False)

    @property
    def children(self) -> List[ExprNode]:
        return [cell for row in self.rows for cell in row]

    def to_latex(self) -> str:
        row_strs = []
        for row in self.rows:
            cells = " & ".join(cell.to_latex() for cell in row)
            row_strs.append(cells)
        body = " \\\\ ".join(row_strs)
        return f"\\begin{{{self.delimiter}}} {body} \\end{{{self.delimiter}}}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["rows"] = [[cell.to_dict() for cell in row] for row in self.rows]
        d["delimiter"] = self.delimiter
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> MatrixNode:
        rows = []
        for row_d in d.get("rows", []):
            row = [ExprNode.from_dict(cell) for cell in row_d]
            rows.append(row)
        return cls(
            rows=rows,
            delimiter=d.get("delimiter", "pmatrix"),
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class FunctionNode(ExprNode):
    """函数节点 — \\sin, \\cos, \\ln, f(x), ..."""
    name: str = ""
    arguments: List[ExprNode] = field(default_factory=list)
    node_type: FormulaNodeType = field(default=FormulaNodeType.FUNCTION, init=False)

    @property
    def children(self) -> List[ExprNode]:
        return self.arguments

    def to_latex(self) -> str:
        args = ", ".join(arg.to_latex() for arg in self.arguments)
        built_in = {"sin", "cos", "tan", "ln", "log", "exp", "sqrt",
                     "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh",
                     "sec", "csc", "cot", "max", "min", "det", "tr"}
        if self.name in built_in:
            return f"\\{self.name}{{{args}}}"
        return f"{self.name}({args})"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["name"] = self.name
        d["arguments"] = [arg.to_dict() for arg in self.arguments]
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> FunctionNode:
        args = [ExprNode.from_dict(a) for a in d.get("arguments", [])]
        return cls(name=d.get("name", ""), arguments=args, confidence=d.get("confidence", 0.0))


@dataclass
class RadicalNode(ExprNode):
    """根号节点 — \\sqrt[n]{radicand}"""
    radicand: Optional[ExprNode] = None
    index: Optional[ExprNode] = None
    node_type: FormulaNodeType = field(default=FormulaNodeType.RADICAL, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.radicand:
            result.append(self.radicand)
        if self.index:
            result.append(self.index)
        return result

    def to_latex(self) -> str:
        rad_l = self.radicand.to_latex() if self.radicand else ""
        if self.index:
            idx_l = self.index.to_latex()
            return f"\\sqrt[{idx_l}]{{{rad_l}}}"
        return f"\\sqrt{{{rad_l}}}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.radicand:
            d["radicand"] = self.radicand.to_dict()
        if self.index:
            d["index"] = self.index.to_dict()
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> RadicalNode:
        return cls(
            radicand=ExprNode.from_dict(d["radicand"]) if d.get("radicand") else None,
            index=ExprNode.from_dict(d["index"]) if d.get("index") else None,
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class BracketNode(ExprNode):
    """括号节点 — (expr), [expr], {expr}"""
    content: Optional[ExprNode] = None
    left_delim: str = "("
    right_delim: str = ")"
    node_type: FormulaNodeType = field(default=FormulaNodeType.BRACKET, init=False)

    @property
    def children(self) -> List[ExprNode]:
        if self.content:
            return [self.content]
        return []

    def to_latex(self) -> str:
        content_l = self.content.to_latex() if self.content else ""
        delim_map = {
            "(": ("\\left(", "\\right)"),
            "[": ("\\left[", "\\right]"),
            "{": ("\\left\\{", "\\right\\}"),
            "⟨": ("\\left\\langle", "\\right\\rangle"),
            "|": ("\\left|", "\\right|"),
            "‖": ("\\left\\|", "\\right\\|"),
        }
        pair = delim_map.get(self.left_delim, (self.left_delim, self.right_delim))
        return f"{pair[0]}{content_l}{pair[1]}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.content:
            d["content"] = self.content.to_dict()
        d["left_delim"] = self.left_delim
        d["right_delim"] = self.right_delim
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> BracketNode:
        return cls(
            content=ExprNode.from_dict(d["content"]) if d.get("content") else None,
            left_delim=d.get("left_delim", "("),
            right_delim=d.get("right_delim", ")"),
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class SequenceNode(ExprNode):
    """序列节点 — 多个表达式的水平排列"""
    elements: List[ExprNode] = field(default_factory=list)
    node_type: FormulaNodeType = field(default=FormulaNodeType.SEQUENCE, init=False)

    @property
    def children(self) -> List[ExprNode]:
        return self.elements

    def to_latex(self) -> str:
        return " ".join(e.to_latex() for e in self.elements)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["elements"] = [e.to_dict() for e in self.elements]
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> SequenceNode:
        elements = [ExprNode.from_dict(e) for e in d.get("elements", [])]
        return cls(elements=elements, confidence=d.get("confidence", 0.0))


@dataclass
class DerivativeNode(ExprNode):
    """导数节点 — \\frac{d}{dx} f(x)"""
    body: Optional[ExprNode] = None
    var: Optional[ExprNode] = None
    order: int = 1
    is_partial: bool = False
    node_type: FormulaNodeType = field(default=FormulaNodeType.DERIVATIVE, init=False)

    @property
    def children(self) -> List[ExprNode]:
        result = []
        if self.body:
            result.append(self.body)
        if self.var:
            result.append(self.var)
        return result

    def to_latex(self) -> str:
        var_l = self.var.to_latex() if self.var else "x"
        body_l = self.body.to_latex() if self.body else ""

        if self.is_partial:
            if self.order == 1:
                return f"\\frac{{\\partial}}{{\\partial {var_l}}} {body_l}"
            return f"\\frac{{\\partial^{self.order}}}{{\\partial {var_l}^{self.order}}} {body_l}"

        if self.order == 1:
            return f"\\frac{{d}}{{d{var_l}}} {body_l}"
        return f"\\frac{{d^{self.order}}}{{d{var_l}^{self.order}}} {body_l}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.body:
            d["body"] = self.body.to_dict()
        if self.var:
            d["var"] = self.var.to_dict()
        d["order"] = self.order
        d["is_partial"] = self.is_partial
        return d

    @classmethod
    def _from_dict_impl(cls, d: dict) -> DerivativeNode:
        return cls(
            body=ExprNode.from_dict(d["body"]) if d.get("body") else None,
            var=ExprNode.from_dict(d["var"]) if d.get("var") else None,
            order=d.get("order", 1),
            is_partial=d.get("is_partial", False),
            confidence=d.get("confidence", 0.0),
        )


# ══════════════════════════════════════════════════════════════
# SpatialGraph → FormulaAST 转换器
# ══════════════════════════════════════════════════════════════

class SpatialGraphToFormulaAST:
    """从 SpatialGraph 构建 FormulaAST

    核心转换逻辑：
      SpatialEdge(relation=NUMERATOR)  → FractionNode
      SpatialEdge(relation=SUPERSCRIPT) → SuperscriptNode
      SpatialEdge(relation=SUBSCRIPT)   → SubscriptNode
      SpatialEdge(relation=LIMIT_UPPER/LOWER) + ∫ → IntegralNode
      SpatialEdge(relation=LIMIT_UPPER/LOWER) + Σ → SumNode
      SpatialEdge(relation=RADICAND)    → RadicalNode

    用法：
        converter = SpatialGraphToFormulaAST()
        ast = converter.convert(spatial_graph)
        latex = ast.to_latex()
    """

    _BIG_OP_MAP = {
        "∫": IntegralNode,
        "∬": lambda: IntegralNode(is_double=True),
        "∭": lambda: IntegralNode(is_triple=True),
        "∮": lambda: IntegralNode(is_contour=True),
        "Σ": SumNode,
        "∑": SumNode,
        "∏": ProductNode,
        "∏": ProductNode,
    }

    def convert(self, graph) -> FormulaAST:
        from vision.layout_graph import SpatialGraph, MathSpatialRelation

        if not graph.nodes:
            return FormulaAST(confidence=0.0)

        roots = graph.get_root_nodes()
        if not roots:
            roots = list(graph.nodes.keys())[:1]

        root_nodes = []
        for root_id in roots:
            node = self._build_node(graph, root_id)
            if node:
                root_nodes.append(node)

        if not root_nodes:
            return FormulaAST(confidence=0.0)

        if len(root_nodes) == 1:
            root = root_nodes[0]
        else:
            root = SequenceNode(elements=root_nodes)

        avg_conf = sum(n.confidence for n in graph.nodes.values()) / max(len(graph.nodes), 1)

        return FormulaAST(
            root=root,
            source="spatial_graph",
            confidence=avg_conf,
            bbox=graph.formula_bbox,
        )

    def _build_node(self, graph, node_id: str) -> Optional[ExprNode]:
        node = graph.nodes.get(node_id)
        if node is None:
            return None

        children = graph.get_children(node_id)

        if not children:
            return self._make_leaf(node)

        from vision.layout_graph import MathSpatialRelation

        subscripts = graph.get_children(node_id, MathSpatialRelation.SUBSCRIPT)
        superscripts = graph.get_children(node_id, MathSpatialRelation.SUPERSCRIPT)
        numerators = graph.get_children(node_id, MathSpatialRelation.NUMERATOR)
        denominators = graph.get_children(node_id, MathSpatialRelation.DENOMINATOR)
        limit_lower = graph.get_children(node_id, MathSpatialRelation.LIMIT_LOWER)
        limit_upper = graph.get_children(node_id, MathSpatialRelation.LIMIT_UPPER)
        arguments = graph.get_children(node_id, MathSpatialRelation.ARGUMENT)
        right_args = graph.get_children(node_id, MathSpatialRelation.RIGHT_ARG)
        radicands = graph.get_children(node_id, MathSpatialRelation.RADICAND)
        indices = graph.get_children(node_id, MathSpatialRelation.INDEX)
        exponents = graph.get_children(node_id, MathSpatialRelation.EXPONENT)
        horizontals = graph.get_children(node_id, MathSpatialRelation.HORIZONTAL)

        # ── 分数 ──
        if numerators or denominators:
            num = self._build_node(graph, numerators[0]) if numerators else None
            den = self._build_node(graph, denominators[0]) if denominators else None
            return FractionNode(numerator=num, denominator=den, confidence=node.confidence)

        # ── 根号 ──
        if radicands:
            rad = self._build_node(graph, radicands[0])
            idx = self._build_node(graph, indices[0]) if indices else None
            return RadicalNode(radicand=rad, index=idx, confidence=node.confidence)

        # ── 大操作符 ──
        symbol = node.symbol
        if symbol in self._BIG_OP_MAP:
            return self._build_big_op(graph, node, symbol, limit_lower, limit_upper,
                                       arguments, right_args)

        # ── 上标 ──
        if superscripts:
            base = self._make_leaf(node)
            exp = self._build_node(graph, superscripts[0])
            result = SuperscriptNode(base=base, exponent=exp, confidence=node.confidence)

            if subscripts:
                sub = self._build_node(graph, subscripts[0])
                result = SubscriptNode(base=result, subscript=sub, confidence=node.confidence)

            return result

        # ── 下标 ──
        if subscripts:
            base = self._make_leaf(node)
            sub = self._build_node(graph, subscripts[0])
            return SubscriptNode(base=base, subscript=sub, confidence=node.confidence)

        # ── 水平序列 ──
        if horizontals:
            elements = [self._make_leaf(node)]
            for h_id in horizontals:
                h_node = self._build_node(graph, h_id)
                if h_node:
                    elements.append(h_node)
            if len(elements) > 1:
                return SequenceNode(elements=elements, confidence=node.confidence)

        # ── 有参数的函数 ──
        if arguments:
            args = [self._build_node(graph, a) for a in arguments]
            return FunctionNode(name=symbol, arguments=args, confidence=node.confidence)

        return self._make_leaf(node)

    def _build_big_op(self, graph, node, symbol: str,
                      limit_lower: list, limit_upper: list,
                      arguments: list, right_args: list) -> ExprNode:
        lower = self._build_node(graph, limit_lower[0]) if limit_lower else None
        upper = self._build_node(graph, limit_upper[0]) if limit_upper else None

        all_args = arguments + right_args
        body_parts = [self._build_node(graph, a) for a in all_args]
        body_parts = [b for b in body_parts if b is not None]

        body = None
        if len(body_parts) == 1:
            body = body_parts[0]
        elif len(body_parts) > 1:
            body = SequenceNode(elements=body_parts)

        factory = self._BIG_OP_MAP[symbol]
        if callable(factory):
            op_node = factory()
        else:
            op_node = factory

        if isinstance(op_node, IntegralNode):
            op_node.lower = lower
            op_node.upper = upper
            op_node.body = body
            op_node.confidence = node.confidence
        elif isinstance(op_node, SumNode):
            op_node.lower = lower
            op_node.upper = upper
            op_node.body = body
            op_node.confidence = node.confidence
        elif isinstance(op_node, ProductNode):
            op_node.lower = lower
            op_node.upper = upper
            op_node.body = body
            op_node.confidence = node.confidence

        return op_node

    def _make_leaf(self, node) -> ExprNode:
        symbol = node.symbol

        if not symbol:
            return VariableNode(name="?", confidence=node.confidence * 0.5)

        if symbol and symbol.replace(".", "").replace("-", "").isdigit():
            return NumberNode(value=symbol, confidence=node.confidence)

        if len(symbol) == 1 and symbol.isalpha():
            return VariableNode(name=symbol, confidence=node.confidence)

        operators = {"+", "-", "×", "÷", "=", "≠", "≤", "≥", "∈", "∉",
                     "<", ">", "→", "⇒", "±", "≈", "⊂"}
        if symbol in operators:
            return OperatorNode(symbol=symbol, confidence=node.confidence)

        if symbol.startswith("\\") or symbol in {"sin", "cos", "tan", "ln", "log",
                                                   "exp", "sqrt", "arcsin", "arccos"}:
            return FunctionNode(name=symbol, confidence=node.confidence)

        return VariableNode(name=symbol, confidence=node.confidence * 0.7)
