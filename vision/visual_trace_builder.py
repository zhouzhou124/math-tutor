"""vision/visual_trace_builder.py — 视觉推理轨迹构建器

═══════════════════════════════════════════════════════════════
核心思想 — 这是整个视觉推理模块的"主入口"
═══════════════════════════════════════════════════════════════

  图像 → Step Detection → Formula Detection → Spatial Graph → MathIR

  不是：图像 → 字符串

  而是：图像 → 视觉理解 → 数学推理结构

  这是整个项目未来最大的升级：
    因为已有 Step语义 / ReasoningTrace / TransformationVerifier
         ConstraintGraph / RuntimeState / Rule DSL
    现在只缺"视觉入口"

  输出：VisualReasoningTrace
    - 与 MathIR 的 MathState / MathOperation 对接
    - 与 RuntimeState 的 WorldState 对接
    - 可直接送入 TransformationVerifier 验证

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Dict, Optional

import cv2
import numpy as np
from PIL import Image

from vision.region_detector import MathRegionDetector, DetectedRegion, RegionType
from vision.handwritten_formula import (
    HandwrittenFormulaDetector,
    FormulaHypothesis,
    FormulaSource,
)
from vision.step_segmenter import StepSegmenter, VisualStep, StepLevel
from vision.layout_graph import (
    LayoutGraphBuilder,
    LayoutGraph,
    LayoutNode,
    LayoutEdge,
    SpatialRelation,
)


class TraceStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class VisualTransition:
    """视觉状态转移 — 对应 MathIR 的 MathOperation"""
    transition_id: str = ""
    step_index: int = 0
    operation_type: str = ""
    input_latex: str = ""
    output_latex: str = ""
    confidence: float = 0.0
    source: FormulaSource = FormulaSource.LOCAL_OCR
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    is_handwritten: bool = False
    spatial_relations: List[str] = field(default_factory=list)


@dataclass
class VisualReasoningTrace:
    """视觉推理轨迹 — 从图片构建的推理结构

    对接已有系统：
      - transitions → MathOperation
      - steps → ReasoningStep
      - layout_graph → 空间依赖
      - confidence → ConfidenceFusion
    """
    trace_id: str = ""
    image_shape: Tuple[int, int] = (0, 0)
    status: TraceStatus = TraceStatus.PARTIAL
    total_steps: int = 0
    transitions: List[VisualTransition] = field(default_factory=list)
    steps: List[VisualStep] = field(default_factory=list)
    formulas: List[FormulaHypothesis] = field(default_factory=list)
    layout_graph: Optional[LayoutGraph] = None
    regions: List[DetectedRegion] = field(default_factory=list)
    avg_confidence: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = f"vtrace_{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_math_ir_dict(self) -> dict:
        """转换为 MathIR 兼容格式

        可直接用于构建 MathState / MathOperation
        """
        return {
            "trace_id": self.trace_id,
            "status": self.status.value,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_number": s.step_number,
                    "level": s.level.name,
                    "has_equation": s.has_equation_sign,
                    "has_numbering": s.has_numbering,
                    "bbox": list(s.bbox),
                }
                for s in self.steps
            ],
            "transitions": [
                {
                    "transition_id": t.transition_id,
                    "operation_type": t.operation_type,
                    "input_latex": t.input_latex,
                    "output_latex": t.output_latex,
                    "confidence": t.confidence,
                    "source": t.source.name,
                    "is_handwritten": t.is_handwritten,
                }
                for t in self.transitions
            ],
            "formulas": [
                {
                    "latex": f.latex,
                    "confidence": f.confidence,
                    "source": f.source.name,
                    "is_handwritten": f.is_handwritten,
                }
                for f in self.formulas
            ],
            "avg_confidence": self.avg_confidence,
            "timestamp": self.timestamp,
        }


class VisualTraceBuilder:
    """视觉推理轨迹构建器

    完整管线：
      Image → Region Detection → Formula Detection → Step Segmentation
            → Layout Graph → Visual Reasoning Trace

    这是视觉推理的"主入口"。
    """

    def __init__(self, llm_client=None, model: str = ""):
        self._llm_client = llm_client
        self._model = model
        self._region_detector = MathRegionDetector()
        self._formula_detector = HandwrittenFormulaDetector(llm_client, model)
        self._step_segmenter = StepSegmenter()
        self._layout_builder = LayoutGraphBuilder()

    def build_trace(self, image) -> VisualReasoningTrace:
        """从图片构建视觉推理轨迹

        完整管线：
          1. Region Detection — 检测数学区域
          2. Formula Detection — 识别公式
          3. Step Segmentation — 分割步骤
          4. Layout Graph — 构建空间关系
          5. Visual Trace — 组装推理轨迹

        Args:
            image: PIL Image 或 numpy array

        Returns:
            VisualReasoningTrace
        """
        img = self._to_numpy(image)
        gray = self._to_grayscale(img)

        trace = VisualReasoningTrace(image_shape=gray.shape[:2])

        # ── 1. Region Detection ──
        region_result = self._region_detector.detect(gray)
        trace.regions = region_result.regions

        # ── 2. Formula Detection ──
        formula_result = self._formula_detector.detect_formulas(gray)
        trace.formulas = formula_result.formulas

        # ── 3. Step Segmentation ──
        step_result = self._step_segmenter.segment(gray)
        trace.steps = step_result.steps
        trace.total_steps = step_result.total_steps

        # ── 4. Layout Graph ──
        layout_graph = self._layout_builder.build(gray)
        trace.layout_graph = layout_graph

        # ── 5. 识别每个步骤的公式 ──
        for step in trace.steps:
            if step.image is not None and step.image.size > 0:
                formula = self._formula_detector.recognize_formula(
                    step.image,
                    prefer_vision=False,
                )
                step.confidence = formula.confidence

        # ── 6. 构建 Visual Transitions ──
        trace.transitions = self._build_transitions(trace)

        # ── 7. 计算总体置信度 ──
        all_conf = [f.confidence for f in trace.formulas if f.confidence > 0]
        all_conf += [s.confidence for s in trace.steps if s.confidence > 0]
        trace.avg_confidence = sum(all_conf) / max(len(all_conf), 1)

        # ── 8. 状态判断 ──
        if trace.total_steps > 0 and trace.avg_confidence > 0.5:
            trace.status = TraceStatus.SUCCESS
        elif trace.total_steps > 0:
            trace.status = TraceStatus.PARTIAL
        else:
            trace.status = TraceStatus.FAILED

        return trace

    def _build_transitions(self, trace: VisualReasoningTrace) -> List[VisualTransition]:
        """从步骤和公式构建状态转移

        每个"步骤"对应一个 VisualTransition：
          input_latex  = 上一步的输出
          output_latex = 当前步骤的公式
          operation_type = 推断的操作类型
        """
        transitions = []

        for i, step in enumerate(trace.steps):
            # 查找与步骤重叠的公式
            step_formulas = self._find_formulas_in_step(step, trace.formulas)

            input_latex = ""
            output_latex = ""

            if i > 0 and transitions:
                input_latex = transitions[-1].output_latex

            if step_formulas:
                best = max(step_formulas, key=lambda f: f.confidence)
                output_latex = best.latex

            op_type = self._infer_operation(input_latex, output_latex, step)

            spatial = []
            if trace.layout_graph:
                for edge in trace.layout_graph.edges:
                    if edge.source_id == f"region_{i:03d}":
                        spatial.append(edge.relation.name)

            transition = VisualTransition(
                transition_id=f"trans_{i:03d}",
                step_index=i,
                operation_type=op_type,
                input_latex=input_latex,
                output_latex=output_latex,
                confidence=step.confidence,
                source=FormulaSource.HYBRID if step_formulas else FormulaSource.LOCAL_OCR,
                bbox=step.bbox,
                is_handwritten=any(f.is_handwritten for f in step_formulas),
                spatial_relations=spatial,
            )
            transitions.append(transition)

        return transitions

    @staticmethod
    def _find_formulas_in_step(step: VisualStep,
                                formulas: List[FormulaHypothesis]) -> List[FormulaHypothesis]:
        """查找与步骤区域重叠的公式"""
        sx, sy, sw, sh = step.bbox
        result = []
        for f in formulas:
            fx, fy, fw, fh = f.bounding_box
            if (sx <= fx + fw and sx + sw >= fx and
                    sy <= fy + fh and sy + sh >= fy):
                result.append(f)
        return result

    @staticmethod
    def _infer_operation(input_latex: str, output_latex: str,
                         step: VisualStep) -> str:
        """推断操作类型"""
        if not output_latex:
            return "unknown"

        text = output_latex.lower()

        if any(kw in text for kw in ["d/dx", "dy/dx", "f'", "f''", "derivative"]):
            return "differentiate"
        if any(kw in text for kw in ["∫", "int", "integral"]):
            return "integrate"
        if any(kw in text for kw in ["lim", "→", "→"]):
            return "compute_limit"
        if any(kw in text for kw in ["=", "equals"]):
            return "transform"
        if any(kw in text for kw in ["∴", "therefore", "所以", "故"]):
            return "conclude"
        if any(kw in text for kw in ["∵", "because", "因为"]):
            return "apply_theorem"
        if step.has_numbering:
            return "classify"

        return "transform"

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
