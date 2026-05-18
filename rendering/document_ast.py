"""
Document AST — 数学文档结构树

═══════════════════════════════════════════════════════════════
设计原则
═══════════════════════════════════════════════════════════════

  不直接渲染字符串。先建"数学文档结构树"。

  DocumentNode 是树节点:
    type     — BlockType (TITLE, STEP, DISPLAY_MATH, ...)
    content  — 具体数据 (str / StepBlock / MatrixBlock / ...)
    children — 子节点列表
    metadata — 附加信息 (source_step_id, confidence, ...)

  核心子类型:
    StepBlock    — 推理步骤 (input_expr, output_expr, operation, legality, ...)
    ProofBlock   — 证明块 (strategy, phase, obligations)
    MatrixBlock  — 矩阵 (rows, environment)
    EquationBlock — 方程/等式 (lhs, rhs, alignment)
    WarningBlock — 警告 (severity, message)
    TableBlock   — 表格 (headers, rows)

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class BlockType(Enum):
    TITLE = "title"
    PARAGRAPH = "paragraph"
    INLINE_MATH = "inline_math"
    DISPLAY_MATH = "display_math"
    STEP = "step"
    WARNING = "warning"
    PROOF = "proof"
    MATRIX = "matrix"
    EQUATION = "equation"
    LIST = "list"
    TABLE = "table"
    DIVIDER = "divider"
    CODE = "code"
    CASE_BRANCH = "case_branch"
    FINAL_ANSWER = "final_answer"
    OBLIGATION = "obligation"


class MathDisplayStyle(Enum):
    INLINE = "inline"
    DISPLAY = "display"
    ALIGNED = "aligned"


@dataclass(frozen=True)
class StepBlock:
    step_id: str = ""
    title: str = ""
    explanation: str = ""
    input_expr: str = ""
    output_expr: str = ""
    operation: str = ""
    legality: str = "unknown"
    warnings: tuple[str, ...] = ()
    proof_obligations: tuple[str, ...] = ()
    theorem_used: str = ""
    confidence: float = 1.0
    source_step_id: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.legality in ("valid", "unknown")

    @property
    def is_suspect(self) -> bool:
        return self.legality == "suspect"

    @property
    def is_invalid(self) -> bool:
        return self.legality == "invalid"

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def has_obligations(self) -> bool:
        return len(self.proof_obligations) > 0

    @property
    def fingerprint(self) -> str:
        raw = f"{self.step_id}::{self.operation}::{self.input_expr}::{self.output_expr}"
        return hashlib.md5(raw.encode()).hexdigest()[:10]

    def to_dict(self) -> dict:
        d = {
            "step_id": self.step_id,
            "title": self.title,
            "explanation": self.explanation,
            "input_expr": self.input_expr,
            "output_expr": self.output_expr,
            "operation": self.operation,
            "legality": self.legality,
        }
        if self.warnings:
            d["warnings"] = list(self.warnings)
        if self.proof_obligations:
            d["proof_obligations"] = list(self.proof_obligations)
        if self.theorem_used:
            d["theorem_used"] = self.theorem_used
        if self.confidence != 1.0:
            d["confidence"] = self.confidence
        if self.source_step_id:
            d["source_step_id"] = self.source_step_id
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> StepBlock:
        return cls(
            step_id=d.get("step_id", ""),
            title=d.get("title", ""),
            explanation=d.get("explanation", ""),
            input_expr=d.get("input_expr", ""),
            output_expr=d.get("output_expr", ""),
            operation=d.get("operation", ""),
            legality=d.get("legality", "unknown"),
            warnings=tuple(d.get("warnings", ())),
            proof_obligations=tuple(d.get("proof_obligations", ())),
            theorem_used=d.get("theorem_used", ""),
            confidence=d.get("confidence", 1.0),
            source_step_id=d.get("source_step_id", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass(frozen=True)
class ProofBlock:
    strategy: str = "direct"
    phase: str = "not_started"
    goal: str = ""
    obligations: tuple[str, ...] = ()
    discharged: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    contradiction_target: str = ""

    @property
    def is_complete(self) -> bool:
        return self.phase == "complete"

    @property
    def pending_obligations(self) -> tuple[str, ...]:
        return tuple(o for o in self.obligations if o not in self.discharged)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "phase": self.phase,
            "goal": self.goal,
            "obligations": list(self.obligations),
            "discharged": list(self.discharged),
            "assumptions": list(self.assumptions),
            "contradiction_target": self.contradiction_target,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ProofBlock:
        return cls(
            strategy=d.get("strategy", "direct"),
            phase=d.get("phase", "not_started"),
            goal=d.get("goal", ""),
            obligations=tuple(d.get("obligations", ())),
            discharged=tuple(d.get("discharged", ())),
            assumptions=tuple(d.get("assumptions", ())),
            contradiction_target=d.get("contradiction_target", ""),
        )


@dataclass(frozen=True)
class MatrixBlock:
    rows: tuple[tuple[str, ...], ...] = ()
    environment: str = "pmatrix"
    label: str = ""
    display: MathDisplayStyle = MathDisplayStyle.DISPLAY

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    def to_dict(self) -> dict:
        return {
            "rows": [list(r) for r in self.rows],
            "environment": self.environment,
            "label": self.label,
            "display": self.display.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MatrixBlock:
        return cls(
            rows=tuple(tuple(r) for r in d.get("rows", ())),
            environment=d.get("environment", "pmatrix"),
            label=d.get("label", ""),
            display=MathDisplayStyle(d.get("display", "display")),
        )


@dataclass(frozen=True)
class EquationBlock:
    lhs: str = ""
    rhs: str = ""
    alignment: str = "center"
    label: str = ""
    numbered: bool = False
    display: MathDisplayStyle = MathDisplayStyle.DISPLAY

    @property
    def full_latex(self) -> str:
        return f"{self.lhs} = {self.rhs}"

    def to_dict(self) -> dict:
        return {
            "lhs": self.lhs,
            "rhs": self.rhs,
            "alignment": self.alignment,
            "label": self.label,
            "numbered": self.numbered,
            "display": self.display.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EquationBlock:
        return cls(
            lhs=d.get("lhs", ""),
            rhs=d.get("rhs", ""),
            alignment=d.get("alignment", "center"),
            label=d.get("label", ""),
            numbered=d.get("numbered", False),
            display=MathDisplayStyle(d.get("display", "display")),
        )


@dataclass(frozen=True)
class WarningBlock:
    severity: str = "warning"
    message: str = ""
    location: str = ""
    suggestion: str = ""

    @property
    def is_error(self) -> bool:
        return self.severity in ("error", "critical")

    @property
    def is_warning(self) -> bool:
        return self.severity == "warning"

    @property
    def is_info(self) -> bool:
        return self.severity in ("info", "minor")

    @property
    def is_critical(self) -> bool:
        return self.severity == "critical"

    def to_dict(self) -> dict:
        d = {
            "severity": self.severity,
            "message": self.message,
        }
        if self.location:
            d["location"] = self.location
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d

    @classmethod
    def from_dict(cls, d: dict) -> WarningBlock:
        return cls(
            severity=d.get("severity", "warning"),
            message=d.get("message", ""),
            location=d.get("location", ""),
            suggestion=d.get("suggestion", ""),
        )


@dataclass(frozen=True)
class TableBlock:
    headers: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    caption: str = ""
    alignment: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "headers": list(self.headers),
            "rows": [list(r) for r in self.rows],
            "caption": self.caption,
            "alignment": list(self.alignment),
        }

    @classmethod
    def from_dict(cls, d: dict) -> TableBlock:
        return cls(
            headers=tuple(d.get("headers", ())),
            rows=tuple(tuple(r) for r in d.get("rows", ())),
            caption=d.get("caption", ""),
            alignment=tuple(d.get("alignment", ())),
        )


@dataclass(frozen=True)
class DocumentNode:
    type: BlockType = BlockType.PARAGRAPH
    content: Any = None
    children: tuple[DocumentNode, ...] = ()
    metadata: dict = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        raw = f"{self.type.value}::{str(self.content)[:100]}::{len(self.children)}"
        return hashlib.md5(raw.encode()).hexdigest()[:10]

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def source_step_id(self) -> str:
        return self.metadata.get("source_step_id", "")

    @property
    def confidence(self) -> float:
        return self.metadata.get("confidence", 1.0)

    def with_child(self, child: DocumentNode) -> DocumentNode:
        return DocumentNode(
            type=self.type,
            content=self.content,
            children=self.children + (child,),
            metadata=self.metadata,
        )

    def with_metadata(self, **kwargs) -> DocumentNode:
        new_meta = dict(self.metadata)
        new_meta.update(kwargs)
        return DocumentNode(
            type=self.type,
            content=self.content,
            children=self.children,
            metadata=new_meta,
        )

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def find_by_type(self, block_type: BlockType) -> list[DocumentNode]:
        return [n for n in self.walk() if n.type == block_type]

    def find_by_step_id(self, step_id: str) -> Optional[DocumentNode]:
        for n in self.walk():
            if n.source_step_id == step_id:
                return n
        return None

    def to_dict(self) -> dict:
        d = {
            "type": self.type.value,
        }
        if self.content is not None:
            if hasattr(self.content, "to_dict"):
                d["content"] = self.content.to_dict()
                d["content_type"] = type(self.content).__name__
            else:
                d["content"] = self.content
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> DocumentNode:
        block_type = BlockType(d.get("type", "paragraph"))
        content = d.get("content")
        content_type = d.get("content_type", "")

        if content is not None and isinstance(content, dict) and content_type:
            _CTORS = {
                "StepBlock": StepBlock.from_dict,
                "ProofBlock": ProofBlock.from_dict,
                "MatrixBlock": MatrixBlock.from_dict,
                "EquationBlock": EquationBlock.from_dict,
                "WarningBlock": WarningBlock.from_dict,
                "TableBlock": TableBlock.from_dict,
            }
            ctor = _CTORS.get(content_type)
            if ctor:
                content = ctor(content)

        children = tuple(
            DocumentNode.from_dict(c) for c in d.get("children", [])
        )
        metadata = d.get("metadata", {})

        return cls(
            type=block_type,
            content=content,
            children=children,
            metadata=metadata,
        )


@dataclass(frozen=True)
class Document:
    title: str = ""
    nodes: tuple[DocumentNode, ...] = ()
    metadata: dict = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        raw = f"{self.title}::{'::'.join(n.fingerprint for n in self.nodes)}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    @property
    def step_blocks(self) -> list[StepBlock]:
        result = []
        for node in self.nodes:
            for n in node.walk():
                if n.type == BlockType.STEP and isinstance(n.content, StepBlock):
                    result.append(n.content)
        return result

    @property
    def warning_blocks(self) -> list[WarningBlock]:
        result = []
        for node in self.nodes:
            for n in node.walk():
                if n.type == BlockType.WARNING and isinstance(n.content, WarningBlock):
                    result.append(n.content)
        return result

    @property
    def has_warnings(self) -> bool:
        return len(self.warning_blocks) > 0

    @property
    def has_invalid_steps(self) -> bool:
        return any(s.is_invalid for s in self.step_blocks)

    @property
    def node_count(self) -> int:
        count = 0
        for node in self.nodes:
            count += sum(1 for _ in node.walk())
        return count

    def with_node(self, node: DocumentNode) -> Document:
        return Document(
            title=self.title,
            nodes=self.nodes + (node,),
            metadata=self.metadata,
        )

    def with_title(self, title: str) -> Document:
        return Document(
            title=title,
            nodes=self.nodes,
            metadata=self.metadata,
        )

    def find_by_type(self, block_type: BlockType) -> list[DocumentNode]:
        result = []
        for node in self.nodes:
            result.extend(node.find_by_type(block_type))
        return result

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "nodes": [n.to_dict() for n in self.nodes],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict) -> Document:
        return cls(
            title=d.get("title", ""),
            nodes=tuple(DocumentNode.from_dict(n) for n in d.get("nodes", [])),
            metadata=d.get("metadata", {}),
        )

    @classmethod
    def empty(cls) -> Document:
        return cls()
