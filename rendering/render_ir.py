from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence
from enum import Enum, auto


class RenderType(Enum):
    TEXT = auto()
    INLINE_MATH = auto()
    BLOCK_MATH = auto()
    ALIGN = auto()
    MATRIX = auto()
    CASES = auto()
    STEP = auto()
    PROOF = auto()
    WARNING = auto()
    OBLIGATION = auto()
    FINAL_ANSWER = auto()
    LIST = auto()
    TABLE = auto()
    DIVIDER = auto()
    CODE = auto()
    EXPANDER = auto()
    COLUMNS = auto()
    CONTAINER = auto()


@dataclass
class RenderNode:
    type: RenderType
    content: Any = None
    children: tuple[RenderNode, ...] = field(default_factory=tuple)
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.metadata.get("id", "")

    @property
    def role(self) -> str:
        return self.metadata.get("role", "")

    @property
    def confidence(self) -> float:
        return self.metadata.get("confidence", 1.0)


@dataclass
class TextNode(RenderNode):
    text: str = ""

    def __init__(self, text: str, metadata: dict = None):
        super().__init__(type=RenderType.TEXT, content=text, metadata=metadata or {})


@dataclass
class InlineMathNode(RenderNode):
    latex: str = ""

    def __init__(self, latex: str, metadata: dict = None):
        super().__init__(type=RenderType.INLINE_MATH, content=latex, metadata=metadata or {})


@dataclass
class BlockMathNode(RenderNode):
    latex: str = ""
    environment: str = ""

    def __init__(self, latex: str, environment: str = "", metadata: dict = None):
        super().__init__(
            type=RenderType.BLOCK_MATH,
            content=latex,
            metadata={**(metadata or {}), "environment": environment}
        )


@dataclass
class AlignNode(RenderNode):
    latex: str = ""
    equations: list[tuple[str, str]] = field(default_factory=list)

    def __init__(self, latex: str = "", equations: list = None, metadata: dict = None):
        super().__init__(
            type=RenderType.ALIGN,
            content=latex,
            metadata=metadata or {}
        )
        self.equations = equations or []


@dataclass
class MatrixNode(RenderNode):
    rows: list[list[str]] = field(default_factory=list)
    environment: str = "pmatrix"
    label: str = ""

    def __init__(self, rows: list = None, environment: str = "pmatrix", label: str = "", metadata: dict = None):
        super().__init__(
            type=RenderType.MATRIX,
            content=rows or [],
            metadata={**(metadata or {}), "label": label}
        )
        self.rows = rows or []
        self.environment = environment


@dataclass
class CasesNode(RenderNode):
    latex: str = ""

    def __init__(self, latex: str, metadata: dict = None):
        super().__init__(type=RenderType.CASES, content=latex, metadata=metadata or {})


@dataclass
class StepNode(RenderNode):
    step_id: str = ""
    title: str = ""
    operation: str = ""
    legality: str = "unknown"
    input_expr: str = ""
    output_expr: str = ""
    explanation: str = ""
    theorem_used: str = ""
    children: tuple[RenderNode, ...] = field(default_factory=tuple)

    def __init__(self, step_id: str = "", title: str = "", children: tuple = None, metadata: dict = None, **kwargs):
        super().__init__(
            type=RenderType.STEP,
            content=title,
            children=children or (),
            metadata={
                **(metadata or {}),
                "step_id": step_id,
                "operation": kwargs.get("operation", ""),
                "legality": kwargs.get("legality", "unknown"),
                "input_expr": kwargs.get("input_expr", ""),
                "output_expr": kwargs.get("output_expr", ""),
                "explanation": kwargs.get("explanation", ""),
                "theorem_used": kwargs.get("theorem_used", ""),
            }
        )
        self.step_id = step_id
        self.title = title


@dataclass
class ProofNode(RenderNode):
    strategy: str = "direct"
    goal: str = ""
    assumptions: tuple[str, ...] = ()
    pending_obligations: tuple[str, ...] = ()
    discharged: tuple[str, ...] = ()
    children: tuple[RenderNode, ...] = field(default_factory=tuple)

    def __init__(self, strategy: str = "direct", goal: str = "", children: tuple = None, metadata: dict = None, **kwargs):
        super().__init__(
            type=RenderType.PROOF,
            content=goal,
            children=children or (),
            metadata={
                **(metadata or {}),
                "strategy": strategy,
                "goal": goal,
                "assumptions": kwargs.get("assumptions", ()),
                "pending_obligations": kwargs.get("pending_obligations", ()),
                "discharged": kwargs.get("discharged", ()),
            }
        )
        self.strategy = strategy
        self.goal = goal


@dataclass
class WarningNode(RenderNode):
    severity: str = "warning"
    message: str = ""
    suggestion: str = ""

    def __init__(self, message: str, severity: str = "warning", suggestion: str = "", metadata: dict = None):
        super().__init__(
            type=RenderType.WARNING,
            content=message,
            metadata={**(metadata or {}), "severity": severity, "suggestion": suggestion}
        )
        self.severity = severity
        self.message = message
        self.suggestion = suggestion


@dataclass
class ObligationNode(RenderNode):
    obligation_id: str = ""
    text: str = ""
    discharged: bool = False

    def __init__(self, text: str, obligation_id: str = "", discharged: bool = False, metadata: dict = None):
        super().__init__(
            type=RenderType.OBLIGATION,
            content=text,
            metadata={**(metadata or {}), "obligation_id": obligation_id, "discharged": discharged}
        )
        self.obligation_id = obligation_id
        self.text = text
        self.discharged = discharged


@dataclass
class FinalAnswerNode(RenderNode):
    answer: str = ""
    answer_expr: str = ""
    is_boxed: bool = True

    def __init__(self, answer: str = "", answer_expr: str = "", is_boxed: bool = True, metadata: dict = None):
        super().__init__(
            type=RenderType.FINAL_ANSWER,
            content=answer,
            metadata={**(metadata or {}), "is_boxed": is_boxed, "answer_expr": answer_expr}
        )
        self.answer = answer
        self.answer_expr = answer_expr
        self.is_boxed = is_boxed


@dataclass
class ListNode(RenderNode):
    items: tuple[str, ...] = ()

    def __init__(self, items: tuple = None, metadata: dict = None):
        super().__init__(
            type=RenderType.LIST,
            content=items or (),
            metadata=metadata or {}
        )
        self.items = items or ()


@dataclass
class TableNode(RenderNode):
    headers: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    caption: str = ""

    def __init__(self, headers: tuple = None, rows: tuple = None, caption: str = "", metadata: dict = None):
        super().__init__(
            type=RenderType.TABLE,
            content={"headers": headers or (), "rows": rows or (), "caption": caption},
            metadata=metadata or {}
        )
        self.headers = headers or ()
        self.rows = rows or ()
        self.caption = caption


@dataclass
class DividerNode(RenderNode):
    def __init__(self, metadata: dict = None):
        super().__init__(type=RenderType.DIVIDER, content="---", metadata=metadata or {})


@dataclass
class CodeNode(RenderNode):
    language: str = ""
    code: str = ""

    def __init__(self, code: str, language: str = "", metadata: dict = None):
        super().__init__(
            type=RenderType.CODE,
            content=code,
            metadata={**(metadata or {}), "language": language}
        )
        self.language = language
        self.code = code


@dataclass
class ExpanderNode(RenderNode):
    label: str = ""
    expanded: bool = False
    child: Optional[RenderNode] = None

    def __init__(self, label: str = "", child: RenderNode = None, expanded: bool = False, metadata: dict = None):
        super().__init__(
            type=RenderType.EXPANDER,
            content=label,
            children=(child,) if child else (),
            metadata={**(metadata or {}), "expanded": expanded}
        )
        self.label = label
        self.expanded = expanded
        self.child = child


@dataclass
class ColumnsNode(RenderNode):
    column_count: int = 2
    columns: tuple[RenderNode, ...] = field(default_factory=tuple)

    def __init__(self, columns: tuple = None, column_count: int = 2, metadata: dict = None):
        super().__init__(
            type=RenderType.COLUMNS,
            content=column_count,
            children=columns or (),
            metadata={**(metadata or {}), "column_count": column_count}
        )
        self.column_count = column_count
        self.columns = columns or ()


@dataclass
class ContainerNode(RenderNode):
    border: bool = False
    child: Optional[RenderNode] = None

    def __init__(self, child: RenderNode = None, border: bool = False, metadata: dict = None):
        super().__init__(
            type=RenderType.CONTAINER,
            content=None,
            children=(child,) if child else (),
            metadata={**(metadata or {}), "border": border}
        )
        self.border = border
        self.child = child


class RenderTree:
    root: RenderNode

    def __init__(self, root: RenderNode = None):
        self.root = root or RenderNode(type=RenderType.TEXT, content="")

    def walk(self) -> list[RenderNode]:
        result = []
        self._walk_node(self.root, result)
        return result

    def _walk_node(self, node: RenderNode, result: list):
        result.append(node)
        for child in node.children:
            self._walk_node(child, result)

    def find_by_id(self, node_id: str) -> Optional[RenderNode]:
        for node in self.walk():
            if node.id == node_id:
                return node
        return None

    def find_by_type(self, render_type: RenderType) -> list[RenderNode]:
        return [node for node in self.walk() if node.type == render_type]

    def find_by_role(self, role: str) -> list[RenderNode]:
        return [node for node in self.walk() if node.role == role]

    def to_dict(self) -> dict:
        return self._node_to_dict(self.root)

    def _node_to_dict(self, node: RenderNode) -> dict:
        d = {
            "type": node.type.name,
            "content": self._serialize_content(node.content),
            "metadata": node.metadata,
        }
        if node.children:
            d["children"] = [self._node_to_dict(c) for c in node.children]
        return d

    def _serialize_content(self, content: Any) -> Any:
        if isinstance(content, (str, int, float, bool, type(None))):
            return content
        if isinstance(content, (list, tuple)):
            return [self._serialize_content(c) for c in content]
        if hasattr(content, "__dataclass_fields__"):
            return {k: self._serialize_content(v) for k, v in content.__dict__.items() if not k.startswith("_")}
        return str(content)

    @classmethod
    def from_document(cls, doc) -> RenderTree:
        from .document_to_ir import DocumentToIRConverter
        converter = DocumentToIRConverter()
        root = converter.convert(doc)
        return cls(root=root)
