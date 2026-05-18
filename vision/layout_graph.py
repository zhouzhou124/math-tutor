"""vision/layout_graph.py — Spatial Graph（数学空间关系图）

═══════════════════════════════════════════════════════════════
核心思想 — 数学不是线性的
═══════════════════════════════════════════════════════════════

  例如：∫₀¹ x² dx

  需要知道：
    "0" 是积分下限（subscript）
    "1" 是积分上限（superscript）
    "x²" 是积分主体（argument）

  这不是"字符识别"，而是"数学结构理解"。

  输出：
    SpatialNode(symbol="∫", bbox=...)
    SpatialEdge(source="0", target="∫", relation="subscript")
    SpatialEdge(source="1", target="∫", relation="superscript")

  这是革命性的：
    从"字符识别" → 进入"数学结构理解"

═══════════════════════════════════════════════════════════════
两层图结构
═══════════════════════════════════════════════════════════════

  1. LayoutGraph — 区域级空间关系（步骤之间）
     节点 = 检测到的区域（公式/文字/步骤）
     边   = ABOVE/BELOW/LEFT_OF/ALIGNED

  2. SpatialGraph — 符号级数学关系（公式内部）
     节点 = 单个符号（∫, x, ², 0, 1, dx）
     边   = subscript/superscript/numerator/denominator/under/over

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Dict, Optional, Set

import cv2
import numpy as np
from PIL import Image


# ══════════════════════════════════════════════════════════════
# 第一层：区域级空间关系（LayoutGraph）
# ══════════════════════════════════════════════════════════════

class SpatialRelation(Enum):
    ABOVE = auto()
    BELOW = auto()
    LEFT_OF = auto()
    RIGHT_OF = auto()
    ALIGNED_H = auto()
    ALIGNED_V = auto()
    CONTAINS = auto()
    CONTAINED_BY = auto()
    ADJACENT = auto()
    OVERLAPS = auto()


class LayoutNodeType(Enum):
    FORMULA = "formula"
    TEXT = "text"
    STEP = "step"
    ARROW = "arrow"
    EQUALS_SIGN = "equals"
    NUMBERING = "numbering"
    FRACTION_LINE = "fraction_line"
    BRACKET = "bracket"


@dataclass
class LayoutNode:
    node_id: str = ""
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    node_type: LayoutNodeType = LayoutNodeType.FORMULA
    center: Tuple[int, int] = (0, 0)
    area: int = 0
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        x, y, w, h = self.bbox
        self.center = (x + w // 2, y + h // 2)
        self.area = w * h


@dataclass
class LayoutEdge:
    source_id: str = ""
    target_id: str = ""
    relation: SpatialRelation = SpatialRelation.ABOVE
    weight: float = 1.0
    confidence: float = 0.0


@dataclass
class LayoutGraph:
    nodes: Dict[str, LayoutNode] = field(default_factory=dict)
    edges: List[LayoutEdge] = field(default_factory=list)
    image_shape: Tuple[int, int] = (0, 0)

    def add_node(self, node: LayoutNode):
        self.nodes[node.node_id] = node

    def add_edge(self, edge: LayoutEdge):
        self.edges.append(edge)

    def get_neighbors(self, node_id: str,
                      relation: Optional[SpatialRelation] = None) -> List[str]:
        neighbors = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if relation is None or edge.relation == relation:
                    neighbors.append(edge.target_id)
            elif edge.target_id == node_id:
                if relation is None or edge.relation == relation:
                    neighbors.append(edge.source_id)
        return neighbors

    def get_edges_from(self, node_id: str) -> List[LayoutEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> List[LayoutEdge]:
        return [e for e in self.edges if e.target_id == node_id]

    def topological_order(self) -> List[str]:
        sorted_nodes = sorted(
            self.nodes.values(),
            key=lambda n: (n.center[1], n.center[0])
        )
        return [n.node_id for n in sorted_nodes]

    def find_aligned_groups(self, axis: str = "vertical",
                            tolerance: int = 15) -> List[List[str]]:
        groups: Dict[int, List[str]] = {}
        for node in self.nodes.values():
            if axis == "vertical":
                key = node.center[0] // tolerance
            else:
                key = node.center[1] // tolerance
            if key not in groups:
                groups[key] = []
            groups[key].append(node.node_id)
        return [g for g in groups.values() if len(g) > 1]

    def to_dict(self) -> dict:
        return {
            "nodes": {
                nid: {
                    "node_id": n.node_id,
                    "bbox": list(n.bbox),
                    "node_type": n.node_type.value,
                    "center": list(n.center),
                    "area": n.area,
                    "confidence": n.confidence,
                }
                for nid, n in self.nodes.items()
            },
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation": e.relation.name,
                    "weight": e.weight,
                    "confidence": e.confidence,
                }
                for e in self.edges
            ],
            "image_shape": list(self.image_shape),
        }


# ══════════════════════════════════════════════════════════════
# 第二层：符号级数学关系（SpatialGraph）— 革命性
# ══════════════════════════════════════════════════════════════

class MathSpatialRelation(Enum):
    """数学空间关系 — 理解公式的二维结构"""
    SUBSCRIPT = "subscript"
    SUPERSCRIPT = "superscript"
    NUMERATOR = "numerator"
    DENOMINATOR = "denominator"
    UNDER = "under"
    OVER = "over"
    LEFT_ARG = "left_arg"
    RIGHT_ARG = "right_arg"
    RADICAND = "radicand"
    INDEX = "index"
    BASE = "base"
    EXPONENT = "exponent"
    LIMIT_LOWER = "limit_lower"
    LIMIT_UPPER = "limit_upper"
    ARGUMENT = "argument"
    HORIZONTAL = "horizontal"
    INSIDE = "inside"


class SymbolRole(Enum):
    """符号在数学结构中的角色"""
    OPERATOR = "operator"
    OPERAND = "operand"
    BOUNDARY = "boundary"
    MODIFIER = "modifier"
    VARIABLE = "variable"
    CONSTANT = "constant"
    FUNCTION = "function"
    ACCENT = "accent"
    DELIMITER = "delimiter"
    UNKNOWN = "unknown"


@dataclass
class SpatialNode:
    """空间图节点 — 公式中的单个符号

    例如：
      SpatialNode(symbol="∫", bbox=..., role=OPERATOR)
      SpatialNode(symbol="0", bbox=..., role=BOUNDARY)
      SpatialNode(symbol="x", bbox=..., role=VARIABLE)
    """
    node_id: str = ""
    symbol: str = ""
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (x1, y1, x2, y2)
    center: Tuple[float, float] = (0.0, 0.0)
    size: Tuple[int, int] = (0, 0)
    role: SymbolRole = SymbolRole.UNKNOWN
    confidence: float = 0.0
    parent_id: Optional[str] = None
    image: Optional[np.ndarray] = None

    def __post_init__(self):
        x1, y1, x2, y2 = self.bbox
        self.center = ((x1 + x2) / 2, (y1 + y2) / 2)
        self.size = (x2 - x1, y2 - y1)

    @property
    def width(self) -> int:
        return self.size[0]

    @property
    def height(self) -> int:
        return self.size[1]

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        return self.width / max(self.height, 1)


@dataclass
class SpatialEdge:
    """空间图边 — 符号间的数学关系

    例如：
      SpatialEdge(source="0", target="∫", relation=SUBSCRIPT)
      SpatialEdge(source="1", target="∫", relation=SUPERSCRIPT)
      SpatialEdge(source="x²", target="∫", relation=ARGUMENT)
    """
    source_id: str = ""
    target_id: str = ""
    relation: MathSpatialRelation = MathSpatialRelation.HORIZONTAL
    confidence: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class SpatialGraph:
    """数学空间关系图 — 公式内部的二维结构

    这是"数学结构理解"的核心：
      不只是识别字符，而是理解字符间的数学关系。

    例如 ∫₀¹ x² dx 的空间图：
      Nodes: ∫, 0, 1, x, ², dx
      Edges:
        0 --subscript--> ∫
        1 --superscript--> ∫
        x --argument--> ∫
        ² --superscript--> x
        dx --right_arg--> ∫
    """
    nodes: Dict[str, SpatialNode] = field(default_factory=dict)
    edges: List[SpatialEdge] = field(default_factory=list)
    formula_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    formula_type: str = ""
    latex: str = ""

    def add_node(self, node: SpatialNode):
        self.nodes[node.node_id] = node

    def add_edge(self, edge: SpatialEdge):
        self.edges.append(edge)

    def get_children(self, node_id: str,
                     relation: Optional[MathSpatialRelation] = None) -> List[str]:
        children = []
        for edge in self.edges:
            if edge.target_id == node_id:
                if relation is None or edge.relation == relation:
                    children.append(edge.source_id)
        return children

    def get_parent(self, node_id: str) -> Optional[str]:
        for edge in self.edges:
            if edge.source_id == node_id:
                return edge.target_id
        return None

    def get_subscripts(self, node_id: str) -> List[str]:
        return self.get_children(node_id, MathSpatialRelation.SUBSCRIPT)

    def get_superscripts(self, node_id: str) -> List[str]:
        return self.get_children(node_id, MathSpatialRelation.SUPERSCRIPT)

    def get_numerator(self, node_id: str) -> Optional[str]:
        children = self.get_children(node_id, MathSpatialRelation.NUMERATOR)
        return children[0] if children else None

    def get_denominator(self, node_id: str) -> Optional[str]:
        children = self.get_children(node_id, MathSpatialRelation.DENOMINATOR)
        return children[0] if children else None

    def get_root_nodes(self) -> List[str]:
        targets = {e.target_id for e in self.edges}
        return [nid for nid in self.nodes if nid not in targets]

    def to_latex(self) -> str:
        if self.latex:
            return self.latex
        roots = self.get_root_nodes()
        if not roots:
            return ""
        parts = []
        for root_id in roots:
            parts.append(self._node_to_latex(root_id))
        return " ".join(parts)

    def _node_to_latex(self, node_id: str) -> str:
        node = self.nodes.get(node_id)
        if node is None:
            return ""

        symbol = node.symbol
        children = self.get_children(node_id)

        if not children:
            return symbol

        subscripts = self.get_subscripts(node_id)
        superscripts = self.get_superscripts(node_id)
        numerators = self.get_children(node_id, MathSpatialRelation.NUMERATOR)
        denominators = self.get_children(node_id, MathSpatialRelation.DENOMINATOR)
        under = self.get_children(node_id, MathSpatialRelation.UNDER)
        over = self.get_children(node_id, MathSpatialRelation.OVER)
        arguments = self.get_children(node_id, MathSpatialRelation.ARGUMENT)
        right_args = self.get_children(node_id, MathSpatialRelation.RIGHT_ARG)
        radicands = self.get_children(node_id, MathSpatialRelation.RADICAND)
        exponents = self.get_children(node_id, MathSpatialRelation.EXPONENT)

        result = symbol

        if numerators and denominators:
            num_latex = self._node_to_latex(numerators[0])
            den_latex = self._node_to_latex(denominators[0])
            result = f"\\frac{{{num_latex}}}{{{den_latex}}}"
        elif numerators:
            result = f"\\frac{{{self._node_to_latex(numerators[0])}}}{{}}"

        if radicands:
            rad_latex = self._node_to_latex(radicands[0])
            index_latex = ""
            indices = self.get_children(node_id, MathSpatialRelation.INDEX)
            if indices:
                index_latex = f"[{self._node_to_latex(indices[0])}]"
            result = f"\\sqrt{index_latex}{{{rad_latex}}}"

        if subscripts:
            sub_latex = "".join(self._node_to_latex(s) for s in subscripts)
            result = f"{result}_{{{sub_latex}}}"

        if superscripts:
            sup_latex = "".join(self._node_to_latex(s) for s in superscripts)
            result = f"{result}^{{{sup_latex}}}"

        if exponents:
            exp_latex = self._node_to_latex(exponents[0])
            result = f"{result}^{{{exp_latex}}}"

        if under:
            under_latex = "".join(self._node_to_latex(s) for s in under)
            result = f"{result}_{{{under_latex}}}"

        if over:
            over_latex = "".join(self._node_to_latex(s) for s in over)
            result = f"{result}^{{{over_latex}}}"

        if arguments:
            arg_latex = " ".join(self._node_to_latex(a) for a in arguments)
            result = f"{result} {arg_latex}"

        if right_args:
            ra_latex = " ".join(self._node_to_latex(r) for r in right_args)
            result = f"{result} {ra_latex}"

        return result

    def to_dict(self) -> dict:
        return {
            "nodes": {
                nid: {
                    "node_id": n.node_id,
                    "symbol": n.symbol,
                    "bbox": list(n.bbox),
                    "center": list(n.center),
                    "size": list(n.size),
                    "role": n.role.value,
                    "confidence": n.confidence,
                }
                for nid, n in self.nodes.items()
            },
            "edges": [
                {
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation": e.relation.value,
                    "confidence": e.confidence,
                }
                for e in self.edges
            ],
            "formula_bbox": list(self.formula_bbox),
            "formula_type": self.formula_type,
            "latex": self.latex,
        }


# ══════════════════════════════════════════════════════════════
# SpatialGraphBuilder — 从公式区域构建空间图
# ══════════════════════════════════════════════════════════════

class SpatialGraphBuilder:
    """数学空间关系图构建器

    从公式区域图片中：
      1. 检测单个符号（连通域）
      2. 识别符号角色（操作符/变量/边界）
      3. 判断符号间数学关系（subscript/superscript/numerator/denominator）
      4. 构建空间图

    核心算法：
      - 基线检测：同行符号共享基线
      - 相对位置：上方=superscript，下方=subscript
      - 分数线检测：上方=numerator，下方=denominator
      - 大操作符检测：∫, Σ, ∏ → 上下限
    """

    _BIG_OPERATORS = {"∫", "∬", "∭", "∮", "Σ", "∏", "⋃", "⋂", "∮", "∑", "∏"}
    _FRACTION_CHARS = {"—", "-", "/", "⁄"}
    _ROOT_CHARS = {"√", "∛", "∜"}
    _DELIMITER_OPEN = {"(", "[", "{", "⟨", "|"}
    _DELIMITER_CLOSE = {")", "]", "}", "⟩", "|"}
    _ACCENT_CHARS = {"̂", "̃", "̄", "̇", "̈", "⃗", "→"}

    def __init__(self):
        self._baseline_tolerance = 0.3
        self._size_ratio_threshold = 0.65
        self._min_cc_area = 6

    def build(self, formula_image: np.ndarray,
              formula_bbox: Tuple[int, int, int, int] = (0, 0, 0, 0),
              ocr_text: str = "") -> SpatialGraph:
        """从公式区域图片构建空间图

        Args:
            formula_image: 公式区域的灰度/二值图
            formula_bbox: 公式在原图中的位置
            ocr_text: OCR 识别的文本（辅助符号识别）

        Returns:
            SpatialGraph
        """
        if len(formula_image.shape) == 3:
            gray = cv2.cvtColor(formula_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = formula_image

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Step 1: 检测连通域 → 符号
        symbols = self._detect_symbols(binary, formula_bbox, ocr_text)

        if not symbols:
            return SpatialGraph(formula_bbox=formula_bbox)

        # Step 2: 检测基线
        baselines = self._detect_baselines(symbols)

        # Step 3: 检测分数线
        fraction_lines = self._detect_fraction_lines(binary, symbols)

        # Step 4: 构建空间关系
        graph = SpatialGraph(formula_bbox=formula_bbox)
        for sym in symbols:
            graph.add_node(sym)

        self._build_relations(graph, symbols, baselines, fraction_lines)

        return graph

    def _detect_symbols(self, binary: np.ndarray,
                        offset: Tuple[int, int, int, int],
                        ocr_text: str) -> List[SpatialNode]:
        """检测单个符号 — 基于连通域"""
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        symbols = []
        ocr_chars = list(ocr_text) if ocr_text else []

        for i, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)

            if area < self._min_cc_area:
                continue

            ox, oy = offset[0], offset[1]

            symbol_char = ocr_chars[i] if i < len(ocr_chars) else ""
            role = self._classify_symbol_role(symbol_char, w, h, area)

            symbols.append(SpatialNode(
                node_id=f"sym_{i:03d}",
                symbol=symbol_char,
                bbox=(ox + x, oy + y, ox + x + w, oy + y + h),
                role=role,
                confidence=0.5 if symbol_char else 0.2,
            ))

        symbols.sort(key=lambda s: (s.center[1], s.center[0]))
        return symbols

    def _classify_symbol_role(self, char: str, w: int, h: int, area: int) -> SymbolRole:
        if char in self._BIG_OPERATORS:
            return SymbolRole.OPERATOR
        if char in self._DELIMITER_OPEN or char in self._DELIMITER_CLOSE:
            return SymbolRole.DELIMITER
        if char in self._FRACTION_CHARS:
            return SymbolRole.OPERATOR
        if char in self._ROOT_CHARS:
            return SymbolRole.OPERATOR
        if char in self._ACCENT_CHARS:
            return SymbolRole.ACCENT
        if char and char.isdigit():
            return SymbolRole.CONSTANT
        if char and char.isalpha():
            return SymbolRole.VARIABLE
        if char in {"+", "-", "×", "÷", "=", "≠", "<", ">", "≤", "≥", "∈", "∉"}:
            return SymbolRole.OPERATOR
        return SymbolRole.UNKNOWN

    def _detect_baselines(self, symbols: List[SpatialNode]) -> List[List[str]]:
        """检测基线 — 同行符号共享基线

        基线是符号底部的水平线。同行符号的基线大致相同。
        """
        if not symbols:
            return []

        # 按中心 y 排序
        sorted_syms = sorted(symbols, key=lambda s: s.center[1])

        baselines = []
        current_line = [sorted_syms[0].node_id]

        for i in range(1, len(sorted_syms)):
            prev = self._find_node(symbols, current_line[-1])
            curr = sorted_syms[i]

            # 判断是否在同一基线
            prev_bottom = prev.bbox[3]
            curr_bottom = curr.bbox[3]
            avg_height = (prev.height + curr.height) / 2

            if abs(prev_bottom - curr_bottom) < avg_height * self._baseline_tolerance:
                current_line.append(curr.node_id)
            else:
                baselines.append(current_line)
                current_line = [curr.node_id]

        baselines.append(current_line)
        return baselines

    def _detect_fraction_lines(self, binary: np.ndarray,
                                symbols: List[SpatialNode]) -> List[Dict]:
        """检测分数线 — 水平长线段

        分数线特征：
          - 宽度远大于高度
          - 水平方向
          - 位于分子和分母之间
        """
        h, w = binary.shape
        fraction_lines = []

        # 水平线检测
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            aspect = cw / max(ch, 1)

            if aspect > 5 and cw > w * 0.1:
                fraction_lines.append({
                    "x": x, "y": y, "w": cw, "h": ch,
                    "center_y": y + ch / 2,
                    "x_start": x, "x_end": x + cw,
                })

        return fraction_lines

    def _build_relations(self, graph: SpatialGraph,
                         symbols: List[SpatialNode],
                         baselines: List[List[str]],
                         fraction_lines: List[Dict]):
        """构建符号间的数学空间关系"""
        if not symbols:
            return

        # 计算平均符号高度（用于判断上下标）
        avg_height = np.mean([s.height for s in symbols])
        avg_width = np.mean([s.width for s in symbols])

        # ── 1. 分数关系 ──
        for fl in fraction_lines:
            fl_y = fl["center_y"]
            fl_x_start = fl["x_start"]
            fl_x_end = fl["x_end"]

            numerator_id = None
            denominator_id = None

            for sym in symbols:
                sym_cx, sym_cy = sym.center

                if sym_cx < fl_x_start or sym_cx > fl_x_end:
                    continue

                if sym_cy < fl_y - sym.height * 0.3:
                    if numerator_id is None or sym_cy > self._find_node(symbols, numerator_id).center[1]:
                        numerator_id = sym.node_id
                elif sym_cy > fl_y + sym.height * 0.3:
                    if denominator_id is None or sym_cy < self._find_node(symbols, denominator_id).center[1]:
                        denominator_id = sym.node_id

            # 创建分数线节点
            fl_node_id = f"frac_{len(graph.edges)}"
            fl_node = SpatialNode(
                node_id=fl_node_id,
                symbol="/",
                bbox=(fl["x"], fl["y"], fl["x"] + fl["w"], fl["y"] + fl["h"]),
                role=SymbolRole.OPERATOR,
                confidence=0.8,
            )
            graph.add_node(fl_node)

            if numerator_id:
                graph.add_edge(SpatialEdge(
                    source_id=numerator_id,
                    target_id=fl_node_id,
                    relation=MathSpatialRelation.NUMERATOR,
                    confidence=0.8,
                ))
            if denominator_id:
                graph.add_edge(SpatialEdge(
                    source_id=denominator_id,
                    target_id=fl_node_id,
                    relation=MathSpatialRelation.DENOMINATOR,
                    confidence=0.8,
                ))

        # ── 2. 同基线水平关系 ──
        for baseline in baselines:
            line_syms = [self._find_node(symbols, nid) for nid in baseline]
            line_syms = [s for s in line_syms if s is not None]
            line_syms.sort(key=lambda s: s.center[0])

            for i in range(len(line_syms) - 1):
                graph.add_edge(SpatialEdge(
                    source_id=line_syms[i].node_id,
                    target_id=line_syms[i + 1].node_id,
                    relation=MathSpatialRelation.HORIZONTAL,
                    confidence=0.7,
                ))

        # ── 3. 上下标/上下限关系 ──
        for sym in symbols:
            # 大操作符 → 检测上下限
            if sym.role == SymbolRole.OPERATOR and sym.symbol in self._BIG_OPERATORS:
                self._detect_limits(graph, symbols, sym, avg_height)
                continue

            # 普通符号 → 检测上下标
            self._detect_scripts(graph, symbols, sym, avg_height)

    def _detect_limits(self, graph: SpatialGraph, symbols: List[SpatialNode],
                       operator: SpatialNode, avg_height: float):
        """检测大操作符的上下限

        例如 ∫₀¹：
          "0" 在 ∫ 下方偏右 → limit_lower (subscript)
          "1" 在 ∫ 上方偏右 → limit_upper (superscript)
        """
        op_cx, op_cy = operator.center
        op_h = operator.height

        for sym in symbols:
            if sym.node_id == operator.node_id:
                continue

            sx, sy = sym.center

            # 水平范围：操作符中心附近
            if abs(sx - op_cx) > op_h * 1.5:
                continue

            # 在操作符上方 → 上限
            if sy < op_cy - op_h * 0.2:
                if sym.height < avg_height * 0.8:
                    graph.add_edge(SpatialEdge(
                        source_id=sym.node_id,
                        target_id=operator.node_id,
                        relation=MathSpatialRelation.LIMIT_UPPER,
                        confidence=0.8,
                    ))
                    sym.parent_id = operator.node_id

            # 在操作符下方 → 下限
            elif sy > op_cy + op_h * 0.2:
                if sym.height < avg_height * 0.8:
                    graph.add_edge(SpatialEdge(
                        source_id=sym.node_id,
                        target_id=operator.node_id,
                        relation=MathSpatialRelation.LIMIT_LOWER,
                        confidence=0.8,
                    ))
                    sym.parent_id = operator.node_id

    def _detect_scripts(self, graph: SpatialGraph, symbols: List[SpatialNode],
                        base: SpatialNode, avg_height: float):
        """检测上下标

        判断逻辑：
          - 符号比基线符号小 → 可能是上下标
          - 在基线上方 → superscript
          - 在基线下方 → subscript
          - 水平位置在基线符号右侧附近
        """
        base_cx, base_cy = base.center
        base_bottom = base.bbox[3]
        base_right = base.bbox[2]

        for sym in symbols:
            if sym.node_id == base.node_id:
                continue
            if sym.parent_id is not None:
                continue

            sx, sy = sym.center

            # 水平位置：在基线符号右侧附近
            if sx < base_cx - base.width * 0.5:
                continue
            if sx > base_right + avg_height * 2:
                continue

            # 大小判断：上下标通常比主体小
            is_smaller = sym.height < base.height * self._size_ratio_threshold

            # 垂直位置判断
            if sy < base_cy - base.height * 0.2 and is_smaller:
                graph.add_edge(SpatialEdge(
                    source_id=sym.node_id,
                    target_id=base.node_id,
                    relation=MathSpatialRelation.SUPERSCRIPT,
                    confidence=0.7,
                ))
                sym.parent_id = base.node_id

            elif sy > base_bottom - base.height * 0.2 and is_smaller:
                graph.add_edge(SpatialEdge(
                    source_id=sym.node_id,
                    target_id=base.node_id,
                    relation=MathSpatialRelation.SUBSCRIPT,
                    confidence=0.7,
                ))
                sym.parent_id = base.node_id

    @staticmethod
    def _find_node(symbols: List[SpatialNode], node_id: str) -> Optional[SpatialNode]:
        for s in symbols:
            if s.node_id == node_id:
                return s
        return None


# ══════════════════════════════════════════════════════════════
# LayoutGraphBuilder — 区域级空间图构建器
# ══════════════════════════════════════════════════════════════

class LayoutGraphBuilder:
    """区域级空间布局图构建器

    从图片中检测区域，构建区域间的空间关系图。
    """

    def __init__(self):
        self._alignment_tolerance = 15
        self._adjacency_threshold = 30

    def build(self, image) -> LayoutGraph:
        img = self._to_numpy(image)
        gray = self._to_grayscale(img)

        from vision.region_detector import FormulaRegionDetector
        detector = FormulaRegionDetector()
        region_result = detector.detect(gray)

        graph = LayoutGraph(image_shape=gray.shape[:2])

        for i, region in enumerate(region_result.formula_regions):
            node = LayoutNode(
                node_id=f"region_{i:03d}",
                bbox=region.to_xywh(),
                node_type=self._map_region_type(region.region_type),
                confidence=region.confidence,
            )
            graph.add_node(node)

        node_list = list(graph.nodes.values())
        for i, node_a in enumerate(node_list):
            for j, node_b in enumerate(node_list):
                if i >= j:
                    continue
                edges = self._compute_relations(node_a, node_b)
                for edge in edges:
                    graph.add_edge(edge)

        self._detect_alignments(graph)
        return graph

    def _compute_relations(self, a: LayoutNode, b: LayoutNode) -> List[LayoutEdge]:
        edges = []
        ax, ay, aw, ah = a.bbox
        bx, by, bw, bh = b.bbox

        if ay + ah < by:
            dist = by - (ay + ah)
            edges.append(LayoutEdge(
                source_id=a.node_id, target_id=b.node_id,
                relation=SpatialRelation.ABOVE,
                weight=1.0 / max(dist, 1),
                confidence=max(0.0, 1.0 - dist / 200),
            ))
        elif by + bh < ay:
            dist = ay - (by + bh)
            edges.append(LayoutEdge(
                source_id=b.node_id, target_id=a.node_id,
                relation=SpatialRelation.ABOVE,
                weight=1.0 / max(dist, 1),
                confidence=max(0.0, 1.0 - dist / 200),
            ))

        if ax + aw < bx:
            dist = bx - (ax + aw)
            edges.append(LayoutEdge(
                source_id=a.node_id, target_id=b.node_id,
                relation=SpatialRelation.LEFT_OF,
                weight=1.0 / max(dist, 1),
                confidence=max(0.0, 1.0 - dist / 200),
            ))
        elif bx + bw < ax:
            dist = ax - (bx + bw)
            edges.append(LayoutEdge(
                source_id=b.node_id, target_id=a.node_id,
                relation=SpatialRelation.LEFT_OF,
                weight=1.0 / max(dist, 1),
                confidence=max(0.0, 1.0 - dist / 200),
            ))

        if self._contains(a.bbox, b.bbox):
            edges.append(LayoutEdge(
                source_id=a.node_id, target_id=b.node_id,
                relation=SpatialRelation.CONTAINS, weight=1.0, confidence=0.8,
            ))
        elif self._contains(b.bbox, a.bbox):
            edges.append(LayoutEdge(
                source_id=b.node_id, target_id=a.node_id,
                relation=SpatialRelation.CONTAINS, weight=1.0, confidence=0.8,
            ))

        if self._overlaps(a.bbox, b.bbox):
            edges.append(LayoutEdge(
                source_id=a.node_id, target_id=b.node_id,
                relation=SpatialRelation.OVERLAPS, weight=0.5, confidence=0.5,
            ))

        if self._is_adjacent(a.bbox, b.bbox):
            edges.append(LayoutEdge(
                source_id=a.node_id, target_id=b.node_id,
                relation=SpatialRelation.ADJACENT, weight=0.8, confidence=0.7,
            ))

        return edges

    def _detect_alignments(self, graph: LayoutGraph):
        v_groups = graph.find_aligned_groups("vertical", self._alignment_tolerance)
        for group in v_groups:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    graph.add_edge(LayoutEdge(
                        source_id=group[i], target_id=group[j],
                        relation=SpatialRelation.ALIGNED_V, weight=0.9, confidence=0.7,
                    ))

        h_groups = graph.find_aligned_groups("horizontal", self._alignment_tolerance)
        for group in h_groups:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    graph.add_edge(LayoutEdge(
                        source_id=group[i], target_id=group[j],
                        relation=SpatialRelation.ALIGNED_H, weight=0.9, confidence=0.7,
                    ))

    @staticmethod
    def _contains(outer, inner) -> bool:
        ox, oy, ow, oh = outer
        ix, iy, iw, ih = inner
        return ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh

    @staticmethod
    def _overlaps(a, b) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by

    def _is_adjacent(self, a, b) -> bool:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        h_gap = max(bx - (ax + aw), ax - (bx + bw), 0)
        v_gap = max(by - (ay + ah), ay - (by + bh), 0)
        return h_gap < self._adjacency_threshold and v_gap < self._adjacency_threshold

    @staticmethod
    def _map_region_type(region_type) -> LayoutNodeType:
        from vision.region_detector import FormulaRegionType
        mapping = {
            FormulaRegionType.EQUATION: LayoutNodeType.FORMULA,
            FormulaRegionType.EXPRESSION: LayoutNodeType.FORMULA,
            FormulaRegionType.INLINE_MATH: LayoutNodeType.FORMULA,
            FormulaRegionType.DISPLAY_MATH: LayoutNodeType.FORMULA,
            FormulaRegionType.FRACTION: LayoutNodeType.FORMULA,
            FormulaRegionType.MATRIX: LayoutNodeType.FORMULA,
            FormulaRegionType.TEXT: LayoutNodeType.TEXT,
            FormulaRegionType.MIXED: LayoutNodeType.STEP,
        }
        return mapping.get(region_type, LayoutNodeType.FORMULA)

    def _to_numpy(self, image) -> np.ndarray:
        if isinstance(image, Image.Image):
            return np.array(image)
        if isinstance(image, np.ndarray):
            return image
        raise ValueError(f"Unsupported image type: {type(image)}")

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
