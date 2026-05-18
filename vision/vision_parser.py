"""vision/vision_parser.py — 数学视觉解析器（新主入口）

═══════════════════════════════════════════════════════════════
核心升级 — 不再输出 OCR 文本，而是输出 VisualReasoningStep
═══════════════════════════════════════════════════════════════

  之前：
    image → pytesseract → "f(x) = x^2 + 1"  (字符串，丢失结构)

  现在：
    image → VisionParser → VisualReasoningStep(
                                image_region=...,
                                latex="f(x) = x^2 + 1",
                                confidence=0.85,
                                spatial_relation="below_step_1"
                            )

  识别引擎优先级：
    1. pix2tex   — 印刷数学公式（LaTeX 输出，专为数学设计）
    2. Vision API — 手写公式（多模态 VLM，支持任意手写）
    3. pytesseract — 纯文本 fallback（仅用于非数学文本）

  输出流向：
    VisualReasoningStep → ReasoningTraceBuilder → MathIR

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Optional, Dict

import cv2
import numpy as np
from PIL import Image


class ParseStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    FALLBACK = "fallback"


class EngineType(Enum):
    PIX2TEX = "pix2tex"
    VISION_API = "vision_api"
    PYTESSERACT = "pytesseract"
    HYBRID = "hybrid"


@dataclass
class VisualReasoningStep:
    """视觉推理步骤 — 替代 OCR 文本字符串

    这是视觉推理的核心输出单元。
    不是字符串，而是结构化的数学推理步骤。
    """
    step_id: str = ""
    image_region: Optional[np.ndarray] = None
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    latex: str = ""
    raw_text: str = ""
    confidence: float = 0.0
    engine: EngineType = EngineType.PIX2TEX
    is_handwritten: bool = False
    spatial_relation: str = ""
    step_number: int = 0
    has_equation: bool = False
    has_numbering: bool = False
    alternatives: List[str] = field(default_factory=list)

    def to_latex(self) -> str:
        return self.latex or self.raw_text

    def has_content(self) -> bool:
        return bool(self.latex.strip() or self.raw_text.strip())


@dataclass
class VisionParseResult:
    """视觉解析结果 — 替代 OCR 字典"""
    status: ParseStatus = ParseStatus.FAILED
    steps: List[VisualReasoningStep] = field(default_factory=list)
    total_steps: int = 0
    avg_confidence: float = 0.0
    dominant_engine: EngineType = EngineType.PIX2TEX
    handwritten_ratio: float = 0.0
    warnings: List[str] = field(default_factory=list)
    raw_ocr_text: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_latex(self) -> str:
        parts = []
        for step in self.steps:
            if step.has_content():
                parts.append(step.to_latex())
        return "\n\n".join(parts)

    def has_content(self) -> bool:
        return any(s.has_content() for s in self.steps)

    def to_ocr_dict(self) -> dict:
        """兼容旧接口 — 转换为 OCR_Agent.recognize() 的输出格式"""
        latex_text = self.to_latex()
        return {
            "success": self.status != ParseStatus.FAILED,
            "question": "",
            "student_answer": latex_text,
            "math_type": "数学一",
            "question_type": "解答题",
            "knowledge_point": "未识别",
            "confidence": self.avg_confidence,
            "warnings": self.warnings,
        }


class VisionParser:
    """数学视觉解析器 — 替代 OCR 文本输出的新主入口

    识别引擎优先级：
      1. pix2tex   — 印刷数学公式
      2. Vision API — 手写公式
      3. pytesseract — 纯文本 fallback

    用法：
        parser = VisionParser(llm_client=client, model="gpt-4o")
        result = parser.parse(image)

        if result.has_content():
            for step in result.steps:
                print(step.latex, step.confidence, step.engine)
        else:
            print("视觉解析失败")
    """

    def __init__(self, llm_client=None, model: str = ""):
        self._llm_client = llm_client
        self._model = model
        self._pix2tex_model = None

    def parse(self, image) -> VisionParseResult:
        """解析图片中的数学内容

        完整管线：
          1. 预处理 → 区域检测 → 步骤分割
          2. 每个步骤：pix2tex → Vision API → pytesseract fallback
          3. 组装 VisualReasoningStep

        Args:
            image: PIL Image 或 numpy array 或文件路径

        Returns:
            VisionParseResult
        """
        img = self._load_image(image)
        if img is None:
            return VisionParseResult(
                status=ParseStatus.FAILED,
                warnings=["无法加载图片"],
            )

        # ── 1. 预处理 + 区域检测 + 步骤分割 ──
        from vision.preprocess import MathImagePreprocessor
        from vision.region_detector import MathRegionDetector
        from vision.step_segmenter import StepSegmenter

        preprocessor = MathImagePreprocessor()
        region_detector = MathRegionDetector()
        step_segmenter = StepSegmenter()

        # 预处理
        preprocess_result = preprocessor.process(img, auto_crop=False)
        processed_img = preprocess_result.image

        # 区域检测
        region_result = region_detector.detect(img)

        # 步骤分割
        step_result = step_segmenter.segment(img)

        # ── 2. 逐步骤识别 ──
        steps = []
        engine_counts: Dict[EngineType, int] = {}
        handwritten_count = 0

        for i, visual_step in enumerate(step_result.steps):
            if visual_step.image is None or visual_step.image.size == 0:
                continue

            # 判断是否手写
            is_hw = self._is_handwritten(visual_step.image)

            # 三级识别管线
            vr_step = self._recognize_step(
                visual_step.image,
                step_number=i + 1,
                is_handwritten=is_hw,
                bbox=visual_step.bbox,
                has_equation=visual_step.has_equation_sign,
                has_numbering=visual_step.has_numbering,
            )

            # 空间关系
            if i > 0 and steps:
                vr_step.spatial_relation = f"below_step_{steps[-1].step_id}"

            steps.append(vr_step)

            engine_counts[vr_step.engine] = engine_counts.get(vr_step.engine, 0) + 1
            if is_hw:
                handwritten_count += 1

        # ── 3. 组装结果 ──
        total = len(steps)
        hw_ratio = handwritten_count / max(total, 1)
        avg_conf = sum(s.confidence for s in steps) / max(total, 1)

        dominant = EngineType.PIX2TEX
        if engine_counts:
            dominant = max(engine_counts, key=engine_counts.get)

        status = ParseStatus.FAILED
        if total > 0 and avg_conf > 0.5:
            status = ParseStatus.SUCCESS
        elif total > 0:
            status = ParseStatus.PARTIAL

        warnings = []
        if hw_ratio > 0.5:
            warnings.append("检测到手写内容较多，建议配置 Vision API 提高识别率")
        if avg_conf < 0.3:
            warnings.append("整体置信度较低，结果可能不准确")

        return VisionParseResult(
            status=status,
            steps=steps,
            total_steps=total,
            avg_confidence=avg_conf,
            dominant_engine=dominant,
            handwritten_ratio=hw_ratio,
            warnings=warnings,
        )

    def _recognize_step(self, region: np.ndarray,
                        step_number: int = 0,
                        is_handwritten: bool = False,
                        bbox: Tuple[int, int, int, int] = (0, 0, 0, 0),
                        has_equation: bool = False,
                        has_numbering: bool = False) -> VisualReasoningStep:
        """三级识别管线

        优先级：
          印刷体: pix2tex → pytesseract → Vision API
          手写体: Vision API → pix2tex → pytesseract
        """
        step_id = f"vstep_{step_number:03d}"

        if is_handwritten:
            # 手写体：Vision API 优先
            result = self._recognize_via_vision_api(region)
            if result.confidence > 0.3:
                result.step_id = step_id
                result.step_number = step_number
                result.is_handwritten = True
                result.bbox = bbox
                result.has_equation = has_equation
                result.has_numbering = has_numbering
                return result

            result = self._recognize_via_pix2tex(region)
            if result.confidence > 0.3:
                result.step_id = step_id
                result.step_number = step_number
                result.is_handwritten = True
                result.bbox = bbox
                result.has_equation = has_equation
                result.has_numbering = has_numbering
                return result

        else:
            # 印刷体：pix2tex 优先
            result = self._recognize_via_pix2tex(region)
            if result.confidence > 0.3:
                result.step_id = step_id
                result.step_number = step_number
                result.bbox = bbox
                result.has_equation = has_equation
                result.has_numbering = has_numbering
                return result

        # Fallback: pytesseract
        result = self._recognize_via_pytesseract(region)
        result.step_id = step_id
        result.step_number = step_number
        result.is_handwritten = is_handwritten
        result.bbox = bbox
        result.has_equation = has_equation
        result.has_numbering = has_numbering
        return result

    def _recognize_via_pix2tex(self, region: np.ndarray) -> VisualReasoningStep:
        """pix2tex 识别 — 印刷数学公式专用

        pix2tex 专为数学公式设计，输出 LaTeX。
        比 pytesseract 适合数学 100 倍。
        """
        try:
            from pix2tex.cli import LatexOCR

            if self._pix2tex_model is None:
                self._pix2tex_model = LatexOCR()

            pil_img = Image.fromarray(region) if isinstance(region, np.ndarray) else region
            latex = self._pix2tex_model(pil_img)

            if latex and latex.strip():
                return VisualReasoningStep(
                    latex=latex.strip(),
                    confidence=0.75,
                    engine=EngineType.PIX2TEX,
                )
        except ImportError:
            pass
        except Exception:
            pass

        return VisualReasoningStep(
            confidence=0.0,
            engine=EngineType.PIX2TEX,
        )

    def _recognize_via_vision_api(self, region: np.ndarray) -> VisualReasoningStep:
        """Vision API 识别 — 手写公式专用

        使用多模态 VLM（如 Qwen2.5-VL, GPT-4o）识别手写公式。
        """
        if self._llm_client is None:
            return VisualReasoningStep(
                confidence=0.0,
                engine=EngineType.VISION_API,
            )

        try:
            import base64

            _, buffer = cv2.imencode(".png", region)
            b64 = base64.b64encode(buffer).decode("utf-8")

            response = self._llm_client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是数学公式识别专家。识别图片中的数学内容，输出 LaTeX 格式。"
                            "规则：\n"
                            "1. 只输出 LaTeX，不要其他内容\n"
                            "2. 不要用 $ 包裹\n"
                            "3. 多行公式用 \\\\ 分隔\n"
                            "4. 如果有文字说明，用 \\text{} 包裹"
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64}"},
                            },
                            {
                                "type": "text",
                                "text": "请识别这个数学内容，输出 LaTeX。",
                            },
                        ],
                    },
                ],
                temperature=0.0,
                max_tokens=1024,
            )

            latex = response.choices[0].message.content.strip()
            latex = latex.strip("$").strip("`").strip()

            if latex:
                return VisualReasoningStep(
                    latex=latex,
                    confidence=0.7,
                    engine=EngineType.VISION_API,
                    is_handwritten=True,
                )
        except Exception:
            pass

        return VisualReasoningStep(
            confidence=0.0,
            engine=EngineType.VISION_API,
        )

    def _recognize_via_pytesseract(self, region: np.ndarray) -> VisualReasoningStep:
        """pytesseract 识别 — 纯文本 fallback

        仅作为最后手段，不适合数学公式和手写。
        """
        try:
            import pytesseract

            pil_img = Image.fromarray(region)
            text = pytesseract.image_to_string(pil_img, lang="chi_sim+eng")
            text = text.strip()

            if text:
                return VisualReasoningStep(
                    raw_text=text,
                    latex=text,
                    confidence=0.3,
                    engine=EngineType.PYTESSERACT,
                )
        except Exception:
            pass

        return VisualReasoningStep(
            confidence=0.0,
            engine=EngineType.PYTESSERACT,
        )

    def _is_handwritten(self, region: np.ndarray) -> bool:
        """判断区域是否为手写"""
        if region.size == 0:
            return False

        if len(region.shape) == 3:
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        else:
            gray = region

        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        stroke_widths = dist[binary > 0]

        if len(stroke_widths) == 0:
            return False

        width_var = np.var(stroke_widths) / max(np.mean(stroke_widths) ** 2, 1)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            total_perimeter = sum(cv2.arcLength(c, True) for c in contours)
            total_area = sum(cv2.contourArea(c) for c in contours)
            curvature = total_perimeter / max(np.sqrt(total_area), 1)
        else:
            curvature = 0

        score = width_var * 2 + curvature * 0.1
        return score > 1.5

    def _load_image(self, image):
        """加载图片"""
        if isinstance(image, str):
            try:
                return Image.open(image)
            except Exception:
                return None
        if isinstance(image, Image.Image):
            return image
        if isinstance(image, np.ndarray):
            return Image.fromarray(image)
        return None
