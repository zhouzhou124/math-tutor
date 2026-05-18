"""
Rich Step Renderer — 富步骤渲染器

═══════════════════════════════════════════════════════════════
核心问题
═══════════════════════════════════════════════════════════════

  现在:
    步骤二:
    P_2A=\\begin{pmatrix}...

  未来:
    步骤二：验证变换组合

    📘 对矩阵 A 先进行：
    R_3 ← R_3 + R_1

    对应初等矩阵：
    P_2 = \\begin{pmatrix} 1 & 0 & 1 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \\end{pmatrix}

    因此：
    P_2 A = \\begin{pmatrix} ... \\end{pmatrix}

    随后交换第一、二行：
    R_1 ↔ R_2

    得到：
    P_1 P_2 A = B

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  StepBlock (普通步骤)
      ↓
  RichStepRenderer
      ↓
  RichStep (富步骤)
    ├── title           — "验证变换组合"
    ├── description     — "对矩阵 A 先进行..."
    ├── row_ops         — [RowOp(...), ...]
    ├── elementary_mats — [P_2, P_1, ...]
    ├── result_expr     — "P_1 P_2 A = B"
    └── result_matrix   — MatrixBlock

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Sequence

from rendering.document_ast import (
    BlockType,
    MathDisplayStyle,
    DocumentNode,
    Document,
    StepBlock,
    MatrixBlock,
    EquationBlock,
)
from rendering.math_formatter import MathFormatter, FormatterConfig


# ═══════════════════════════════════════════════════════════
# Row Operation Types
# ═══════════════════════════════════════════════════════════

class RowOpKind(Enum):
    SWAP = "swap"
    SCALE = "scale"
    ADD = "add"


@dataclass(frozen=True)
class RowOp:
    """
    行操作结构化表示.

    SWAP:   R_i ↔ R_j           → RowOp(kind=SWAP, row_i=1, row_j=2)
    SCALE:  R_i ← k·R_i         → RowOp(kind=SCALE, row_i=3, factor="2")
    ADD:    R_i ← R_i + k·R_j   → RowOp(kind=ADD, row_i=3, row_j=1, factor="1")
    """
    kind: RowOpKind = RowOpKind.ADD
    row_i: int = 1
    row_j: int = 0
    factor: str = "1"

    @property
    def latex(self) -> str:
        if self.kind == RowOpKind.SWAP:
            return f"R_{self.row_i} \\leftrightarrow R_{self.row_j}"
        elif self.kind == RowOpKind.SCALE:
            return f"R_{self.row_i} \\leftarrow {self.factor} \\cdot R_{self.row_i}"
        elif self.kind == RowOpKind.ADD:
            if self.factor == "1":
                return f"R_{self.row_i} \\leftarrow R_{self.row_i} + R_{self.row_j}"
            return f"R_{self.row_i} \\leftarrow R_{self.row_i} + {self.factor} \\cdot R_{self.row_j}"
        return ""

    @property
    def description_cn(self) -> str:
        if self.kind == RowOpKind.SWAP:
            return f"交换第 {self.row_i} 行与第 {self.row_j} 行"
        elif self.kind == RowOpKind.SCALE:
            return f"第 {self.row_i} 行乘以 {self.factor}"
        elif self.kind == RowOpKind.ADD:
            if self.factor == "1":
                return f"第 {self.row_i} 行加上第 {self.row_j} 行"
            return f"第 {self.row_i} 行加上 {self.factor} 倍第 {self.row_j} 行"
        return ""

    def to_dict(self) -> dict:
        d = {"kind": self.kind.value, "row_i": self.row_i}
        if self.kind == RowOpKind.SWAP:
            d["row_j"] = self.row_j
        elif self.kind == RowOpKind.SCALE:
            d["factor"] = self.factor
        elif self.kind == RowOpKind.ADD:
            d["row_j"] = self.row_j
            d["factor"] = self.factor
        return d


# ═══════════════════════════════════════════════════════════
# Rich Step Data Structure
# ═══════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RichStep:
    """
    富步骤 — 包含完整操作语义的步骤结构.

    相比 StepBlock，增加了:
      - row_ops: 行操作序列
      - elementary_mats: 对应初等矩阵
      - composition: 组合表达式 (如 P_1 P_2 A)
      - result_matrix: 结果矩阵
      - description: 自然语言描述
    """
    step_id: str = ""
    title: str = ""
    description: str = ""
    row_ops: tuple[RowOp, ...] = ()
    elementary_mats: tuple[dict, ...] = ()
    composition: str = ""
    result_matrix: tuple[tuple[str, ...], ...] = ()
    result_env: str = "pmatrix"
    result_label: str = ""
    legality: str = "valid"
    warnings: tuple[str, ...] = ()
    source_step: StepBlock = None

    def to_dict(self) -> dict:
        d = {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "row_ops": [op.to_dict() for op in self.row_ops],
            "composition": self.composition,
            "legality": self.legality,
        }
        if self.elementary_mats:
            d["elementary_mats"] = list(self.elementary_mats)
        if self.result_matrix:
            d["result_matrix"] = [list(r) for r in self.result_matrix]
        if self.result_label:
            d["result_label"] = self.result_label
        return d


# ═══════════════════════════════════════════════════════════
# Row Operation Parser
# ═══════════════════════════════════════════════════════════

_SWAP_PATTERN = re.compile(
    r'R[_\s]?(\d+)\s*(?:↔|\\leftrightarrow|<->|<=>)\s*R[_\s]?(\d+)', re.IGNORECASE
)

_SCALE_PATTERN = re.compile(
    r'R[_\s]?(\d+)\s*(?:←|\\leftarrow|<-)\s*([-\d/\\frac{}]+)\s*[·*⋅\\cdot]?\s*R[_\s]?\1', re.IGNORECASE
)

_ADD_PATTERN = re.compile(
    r'R[_\s]?(\d+)\s*(?:←|\\leftarrow|<-)\s*R[_\s]?\1\s*\+\s*([-\d/\\frac{}]+)?\s*[·*⋅\\cdot]?\s*R[_\s]?(\d+)', re.IGNORECASE
)

_ADD_SIMPLE_PATTERN = re.compile(
    r'R[_\s]?(\d+)\s*(?:←|\\leftarrow|<-)\s*R[_\s]?\1\s*\+\s*R[_\s]?(\d+)', re.IGNORECASE
)


def parse_row_op(text: str) -> Optional[RowOp]:
    """
    解析行操作文本 → RowOp.

    支持格式:
      R_3 ← R_3 + R_1           → ADD(3, 1, "1")
      R_3 ← R_3 + 2·R_1         → ADD(3, 1, "2")
      R_1 ↔ R_2                  → SWAP(1, 2)
      R_2 ← 3·R_2               → SCALE(2, "3")
    """
    text = text.strip()

    m = _SWAP_PATTERN.search(text)
    if m:
        return RowOp(kind=RowOpKind.SWAP, row_i=int(m.group(1)), row_j=int(m.group(2)))

    m = _ADD_PATTERN.search(text)
    if m:
        row_i = int(m.group(1))
        factor = m.group(2) or "1"
        factor = factor.strip().rstrip("*·⋅")
        if not factor:
            factor = "1"
        row_j = int(m.group(3))
        return RowOp(kind=RowOpKind.ADD, row_i=row_i, row_j=row_j, factor=factor)

    m = _ADD_SIMPLE_PATTERN.search(text)
    if m:
        return RowOp(kind=RowOpKind.ADD, row_i=int(m.group(1)), row_j=int(m.group(2)))

    m = _SCALE_PATTERN.search(text)
    if m:
        return RowOp(kind=RowOpKind.SCALE, row_i=int(m.group(1)), factor=m.group(2).strip())

    return None


def parse_row_ops(text: str) -> list[RowOp]:
    """
    从文本中提取所有行操作.

    支持多行或分号分隔:
      "R_3 ← R_3 + R_1; R_1 ↔ R_2"
      "R_3 ← R_3 + R_1\\nR_1 ↔ R_2"
    """
    segments = re.split(r'[;；\n]', text)
    ops = []
    for seg in segments:
        op = parse_row_op(seg)
        if op:
            ops.append(op)
    return ops


# ═══════════════════════════════════════════════════════════
# Elementary Matrix Generator
# ═══════════════════════════════════════════════════════════

def elementary_matrix(op: RowOp, n: int) -> list[list[str]]:
    """
    由行操作生成 n×n 初等矩阵.

    SWAP(i,j):  交换单位矩阵的第 i 行与第 j 行
    SCALE(i,k): 单位矩阵第 i 行对角元改为 k
    ADD(i,j,k): 单位矩阵 (i,j) 位置改为 k
    """
    mat = [[str(1 if r == c else 0) for c in range(n)] for r in range(n)]

    if op.kind == RowOpKind.SWAP:
        i, j = op.row_i - 1, op.row_j - 1
        mat[i], mat[j] = mat[j], mat[i]
    elif op.kind == RowOpKind.SCALE:
        i = op.row_i - 1
        mat[i][i] = op.factor
    elif op.kind == RowOpKind.ADD:
        i, j = op.row_i - 1, op.row_j - 1
        mat[i][j] = op.factor

    return mat


# ═══════════════════════════════════════════════════════════
# Rich Step Renderer
# ═══════════════════════════════════════════════════════════

@dataclass
class RichRendererConfig:
    show_elementary_matrix: bool = True
    show_row_op_notation: bool = True
    show_composition: bool = True
    show_result_matrix: bool = True
    show_description: bool = True
    matrix_size: int = 3
    icon_step: str = "📘"
    icon_therefore: str = "∴"
    icon_then: str = "➡️"


class RichStepRenderer:
    """
    富步骤渲染器 — 将普通 StepBlock 增强为 RichStep 并渲染为 DocumentNode.

    核心能力:
      1. 解析行操作文本 → RowOp 结构
      2. 由 RowOp 生成初等矩阵
      3. 构建组合表达式 (P_1 P_2 A = B)
      4. 生成富文本 DocumentNode 序列
    """

    def __init__(
        self,
        config: RichRendererConfig = None,
        math_formatter: MathFormatter = None,
    ):
        self.config = config or RichRendererConfig()
        self._fmt = math_formatter or MathFormatter()

    def enrich_step(self, step: StepBlock, matrix_size: int = 0) -> RichStep:
        """
        StepBlock → RichStep.

        从 step 的 explanation / input_expr / output_expr 中提取行操作信息.
        """
        n = matrix_size or self.config.matrix_size

        row_ops = self._extract_row_ops(step)
        elementary_mats = ()
        if row_ops and self.config.show_elementary_matrix:
            elementary_mats = tuple(
                {"label": f"P_{i+1}", "rows": elementary_matrix(op, n), "op": op}
                for i, op in enumerate(row_ops)
            )

        composition = ""
        if elementary_mats and self.config.show_composition:
            labels = [m["label"] for m in elementary_mats]
            var = self._extract_matrix_var(step)
            if labels and var:
                product = " ".join(labels)
                composition = f"{product} {var}"

        result_matrix = ()
        result_env = "pmatrix"
        result_label = ""
        if step.output_expr and self.config.show_result_matrix:
            parsed = self._try_parse_matrix(step.output_expr)
            if parsed:
                result_matrix = parsed
                result_env = "pmatrix"
            result_label = composition if composition else ""

        description = self._build_description(step, row_ops)

        return RichStep(
            step_id=step.step_id,
            title=step.title,
            description=description,
            row_ops=tuple(row_ops),
            elementary_mats=elementary_mats,
            composition=composition,
            result_matrix=result_matrix,
            result_env=result_env,
            result_label=result_label,
            legality=step.legality,
            warnings=tuple(w[1] if isinstance(w, tuple) else str(w) for w in step.warnings),
            source_step=step,
        )

    def render_rich_step(self, rich: RichStep) -> list[DocumentNode]:
        """
        RichStep → DocumentNode[].

        生成结构:
          1. 步骤标题
          2. 操作描述 (📘 ...)
          3. 行操作记号 (display math)
          4. 初等矩阵 (逐个展示)
          5. 组合表达式
          6. 结果矩阵
        """
        nodes = []

        nodes.append(DocumentNode(
            type=BlockType.PARAGRAPH,
            content=f"**{rich.title}**",
            metadata={"role": "step_title"},
        ))

        if rich.description and self.config.show_description:
            nodes.append(DocumentNode(
                type=BlockType.PARAGRAPH,
                content=f"{self.config.icon_step} {rich.description}",
                metadata={"role": "step_description"},
            ))

        for i, op in enumerate(rich.row_ops):
            if self.config.show_row_op_notation:
                nodes.append(DocumentNode(
                    type=BlockType.DISPLAY_MATH,
                    content=op.latex,
                    metadata={"role": "row_op", "op_index": i},
                ))

        for i, em in enumerate(rich.elementary_mats):
            if self.config.show_elementary_matrix:
                label = em["label"]
                rows = em["rows"]
                op = em["op"]
                desc = op.description_cn
                mat_block = MatrixBlock(
                    rows=tuple(tuple(r) for r in rows),
                    environment="pmatrix",
                    label=label,
                )
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"对应初等矩阵（{desc}）：",
                    metadata={"role": "elem_mat_intro", "op_index": i},
                ))
                nodes.append(DocumentNode(
                    type=BlockType.MATRIX,
                    content=mat_block,
                    metadata={"role": "elementary_matrix", "op_index": i},
                ))

        if rich.composition and self.config.show_composition:
            if rich.result_matrix:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content="因此：",
                    metadata={"role": "therefore"},
                ))
                mat_block = MatrixBlock(
                    rows=rich.result_matrix,
                    environment=rich.result_env,
                    label=rich.composition,
                )
                nodes.append(DocumentNode(
                    type=BlockType.MATRIX,
                    content=mat_block,
                    metadata={"role": "composition_result"},
                ))
            else:
                nodes.append(DocumentNode(
                    type=BlockType.PARAGRAPH,
                    content=f"因此：${rich.composition}$",
                    metadata={"role": "composition"},
                ))

        elif rich.result_matrix and self.config.show_result_matrix:
            mat_block = MatrixBlock(
                rows=rich.result_matrix,
                environment=rich.result_env,
                label=rich.result_label,
            )
            nodes.append(DocumentNode(
                type=BlockType.MATRIX,
                content=mat_block,
                metadata={"role": "result_matrix"},
            ))

        if rich.warnings:
            for w in rich.warnings:
                from rendering.document_ast import WarningBlock
                nodes.append(DocumentNode(
                    type=BlockType.WARNING,
                    content=WarningBlock(severity="warning", message=w),
                ))

        return nodes

    def render_step_rich(self, step: StepBlock, matrix_size: int = 0) -> list[DocumentNode]:
        """一步完成: StepBlock → RichStep → DocumentNode[]"""
        rich = self.enrich_step(step, matrix_size)
        return self.render_rich_step(rich)

    def render_dict_step_rich(self, step: dict, number: int = 1) -> list[DocumentNode]:
        """
        dict step → RichStep → DocumentNode[].

        支持的 dict 格式:
          {
            "step_id": "s1",
            "label": "验证变换组合",
            "operation": "row_reduce",
            "legality": "valid",
            "row_ops": ["R_3 ← R_3 + R_1", "R_1 ↔ R_2"],
            "matrix_size": 3,
            "matrix_var": "A",
            "blocks": [
              {"type": "matrix", "rows": [[...], [...]], "environment": "bmatrix"},
              {"type": "text", "content": "..."},
            ]
          }
        """
        n = step.get("matrix_size", self.config.matrix_size)
        row_op_texts = step.get("row_ops", [])
        matrix_var = step.get("matrix_var", "A")

        row_ops = []
        for text in row_op_texts:
            op = parse_row_op(text)
            if op:
                row_ops.append(op)

        if not row_ops:
            explanation = step.get("explanation", step.get("label", ""))
            row_ops = parse_row_ops(explanation)

        elementary_mats = ()
        if row_ops and self.config.show_elementary_matrix:
            elementary_mats = tuple(
                {"label": f"P_{i+1}", "rows": elementary_matrix(op, n), "op": op}
                for i, op in enumerate(row_ops)
            )

        composition = ""
        if elementary_mats and self.config.show_composition:
            labels = [m["label"] for m in elementary_mats]
            if labels and matrix_var:
                product = " ".join(labels)
                composition = f"{product} {matrix_var}"

        description = step.get("description", "")
        if not description and row_ops:
            if len(row_ops) == 1:
                description = f"对矩阵 {matrix_var} 进行：{row_ops[0].description_cn}"
            else:
                first_desc = row_ops[0].description_cn
                rest_descs = [op.description_cn for op in row_ops[1:]]
                description = f"对矩阵 {matrix_var} 先进行：{first_desc}\n随后" + "，再".join(rest_descs)

        result_matrix = ()
        result_env = "pmatrix"
        result_label = composition

        blocks = step.get("blocks", [])
        for b in blocks:
            if b.get("type") == "matrix":
                rows = b.get("rows", [])
                if rows:
                    result_matrix = tuple(tuple(r) for r in rows)
                    result_env = b.get("environment", "pmatrix")
                break

        label = step.get("label", f"步骤 {number}")
        if step.get("operation") == "row_reduce":
            label = f"{label}" if label else "行变换"

        rich = RichStep(
            step_id=step.get("step_id", f"s{number}"),
            title=label,
            description=description,
            row_ops=tuple(row_ops),
            elementary_mats=elementary_mats,
            composition=composition,
            result_matrix=result_matrix,
            result_env=result_env,
            result_label=result_label,
            legality=step.get("legality", "valid"),
        )

        return self.render_rich_step(rich)

    def _extract_row_ops(self, step: StepBlock) -> list[RowOp]:
        texts = []

        if step.explanation:
            texts.append(step.explanation)
        if step.input_expr:
            texts.append(step.input_expr)
        if step.output_expr:
            texts.append(step.output_expr)

        combined = " ; ".join(texts)
        ops = parse_row_ops(combined)

        if not ops and step.operation in ("row_reduce", "row_swap", "row_scale", "row_add"):
            ops = self._infer_row_ops_from_step(step)

        return ops

    def _infer_row_ops_from_step(self, step: StepBlock) -> list[RowOp]:
        if step.input_expr and step.output_expr:
            return []
        return []

    def _extract_matrix_var(self, step: StepBlock) -> str:
        for candidate in [step.input_expr, step.explanation]:
            if not candidate:
                continue
            m = re.search(r'\\?[A-Z]_?\d*\s*=', candidate)
            if m:
                var = m.group(0).replace("=", "").strip()
                return var
            m = re.search(r'([A-Z])\s*=', candidate)
            if m:
                return m.group(1)
        return "A"

    def _extract_matrix_var_from_rich(self, rich: RichStep) -> str:
        if rich.composition:
            parts = rich.composition.split()
            if parts:
                return parts[-1]
        return "A"

    def _build_description(self, step: StepBlock, row_ops: list[RowOp]) -> str:
        if row_ops:
            var = self._extract_matrix_var(step)
            if len(row_ops) == 1:
                return f"对矩阵 {var} 进行：{row_ops[0].description_cn}"
            parts = [f"对矩阵 {var} 依次进行："]
            for i, op in enumerate(row_ops):
                parts.append(f"({i+1}) {op.description_cn}")
            return "\n".join(parts)

        if step.explanation:
            return step.explanation

        return ""

    def _try_parse_matrix(self, latex: str) -> tuple[tuple[str, ...], ...]:
        """
        尝试从 LaTeX 文本中解析矩阵数据.

        支持:
          \\begin{pmatrix}1 & 2 \\\\ 3 & 4\\end{pmatrix}
          [[1,2],[3,4]]
        """
        for env in ("pmatrix", "bmatrix", "vmatrix", "matrix"):
            begin_tag = f"\\begin{{{env}}}"
            end_tag = f"\\end{{{env}}}"
            begin_idx = latex.find(begin_tag)
            end_idx = latex.find(end_tag)
            if begin_idx != -1 and end_idx != -1:
                content = latex[begin_idx + len(begin_tag):end_idx]
                content = re.sub(r'\s*\\\\\s*', '\n', content)
                content = re.sub(r'\s*&\s*', ', ', content)
                rows = []
                for line in content.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    elements = [e.strip() for e in line.split(",") if e.strip()]
                    if elements:
                        rows.append(tuple(elements))
                if rows:
                    return tuple(rows)

        if latex.startswith("[["):
            from rendering.math_formatter import MathFormatter
            fmt = MathFormatter()
            rows = fmt._parse_nested_list(latex)
            if rows:
                return tuple(tuple(r) for r in rows)

        return ()


# ═══════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════

_default_renderer = RichStepRenderer()


def enrich_step(step: StepBlock, matrix_size: int = 0) -> RichStep:
    return _default_renderer.enrich_step(step, matrix_size)


def render_rich_step(rich: RichStep) -> list[DocumentNode]:
    return _default_renderer.render_rich_step(rich)


def render_step_rich(step: StepBlock, matrix_size: int = 0) -> list[DocumentNode]:
    return _default_renderer.render_step_rich(step, matrix_size)


def render_dict_step_rich(step: dict, number: int = 1) -> list[DocumentNode]:
    return _default_renderer.render_dict_step_rich(step, number)
