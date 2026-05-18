"""vision/handwritten_formula.py — 手写公式检测与识别

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  pytesseract 对印刷体还行，对手写数学公式基本废了。

  正确方向：
    1. 检测手写区域（笔画特征：粗细不均、弯曲、连接）
    2. 提取笔画特征（密度、曲率、交叉点）
    3. 三级识别管线：
       - 本地 pytesseract（印刷体）
       - LLM Vision API（手写体 fallback）
       - 结构化公式解析（最高优先级，如果可用）

  输出不是字符串，而是 FormulaHypothesis：
    - latex: LaTeX 表示
    - confidence: 置信度
    - source: 来源（ocr / vision / parsed）
    - bounding_box: 位置

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Optional

import cv2
import numpy as np
from PIL import Image


class FormulaSource(Enum):
    LOCAL_OCR = auto()
    VISION_API = auto()
    PARSED = auto()
    HYBRID = auto()


@dataclass
class FormulaHypothesis:
    """公式假设 — 一个公式的多种识别结果"""
    latex: str = ""
    raw_text: str = ""
    confidence: float = 0.0
    source: FormulaSource = FormulaSource.LOCAL_OCR
    bounding_box: Tuple[int, int, int, int] = (0, 0, 0, 0)
    is_handwritten: bool = False
    stroke_count: int = 0
    alternatives: List[str] = field(default_factory=list)


@dataclass
class FormulaDetectionResult:
    """公式检测结果"""
    formulas: List[FormulaHypothesis] = field(default_factory=list)
    total_detected: int = 0
    handwritten_count: int = 0
    printed_count: int = 0
    avg_confidence: float = 0.0


class HandwrittenFormulaDetector:
    """手写公式检测器

    检测图片中的手写公式区域，区分手写/印刷，
    提供多级识别管线。
    """

    def __init__(self, llm_client=None, model: str = ""):
        self._llm_client = llm_client
        self._model = model

    def detect_formulas(self, image) -> FormulaDetectionResult:
        """检测图片中的公式

        Args:
            image: PIL Image 或 numpy array

        Returns:
            FormulaDetectionResult
        """
        img = self._to_numpy(image)
        gray = self._to_grayscale(img)

        from vision.region_detector import MathRegionDetector
        detector = MathRegionDetector()
        region_result = detector.detect(gray)

        formulas = []
        for region in region_result.regions:
            x, y, w, h = region.bbox
            padding = 5
            x0 = max(0, x - padding)
            y0 = max(0, y - padding)
            x1 = min(gray.shape[1], x + w + padding)
            y1 = min(gray.shape[0], y + h + padding)
            roi = gray[y0:y1, x0:x1]

            is_hw = self._is_handwritten(roi)
            stroke_count = self._estimate_stroke_count(roi)

            formula = FormulaHypothesis(
                bounding_box=(x, y, w, h),
                is_handwritten=is_hw,
                stroke_count=stroke_count,
                confidence=region.confidence,
            )
            formulas.append(formula)

        handwritten = sum(1 for f in formulas if f.is_handwritten)
        printed = len(formulas) - handwritten
        avg_conf = sum(f.confidence for f in formulas) / max(len(formulas), 1)

        return FormulaDetectionResult(
            formulas=formulas,
            total_detected=len(formulas),
            handwritten_count=handwritten,
            printed_count=printed,
            avg_confidence=avg_conf,
        )

    def recognize_formula(self, image, prefer_vision: bool = False) -> FormulaHypothesis:
        """识别单个公式区域

        三级管线：
          1. 本地 OCR（印刷体优先）
          2. Vision API（手写体 fallback）
          3. 合并结果

        Args:
            image: 公式区域图片
            prefer_vision: 是否优先使用 Vision API

        Returns:
            FormulaHypothesis
        """
        img = self._to_numpy(image)
        gray = self._to_grayscale(img)
        is_hw = self._is_handwritten(gray)

        if prefer_vision or is_hw:
            result = self._recognize_via_vision(gray)
            if result.confidence > 0.3:
                return result

        result_ocr = self._recognize_via_ocr(gray)
        if not is_hw and result_ocr.confidence > 0.3:
            return result_ocr

        result_vision = self._recognize_via_vision(gray)
        if result_vision.confidence > result_ocr.confidence:
            return result_vision

        return result_ocr

    def _is_handwritten(self, region: np.ndarray) -> bool:
        """判断区域是否为手写

        手写特征：
          - 笔画粗细不均（方差大）
          - 边缘弯曲度高
          - 连接点不规则
          - 密度分布不均匀
        """
        if region.size == 0:
            return False

        _, binary = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 特征 1: 笔画粗细方差
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        stroke_widths = dist[binary > 0]
        if len(stroke_widths) > 0:
            width_var = np.var(stroke_widths) / max(np.mean(stroke_widths) ** 2, 1)
        else:
            width_var = 0

        # 特征 2: 边缘弯曲度
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if contours:
            total_perimeter = sum(cv2.arcLength(c, True) for c in contours)
            total_area = sum(cv2.contourArea(c) for c in contours)
            curvature = total_perimeter / max(np.sqrt(total_area), 1)
        else:
            curvature = 0

        # 特征 3: 密度分布均匀性
        h, w = binary.shape
        if w > 4 and h > 4:
            quadrants = [
                binary[:h // 2, :w // 2],
                binary[:h // 2, w // 2:],
                binary[h // 2:, :w // 2],
                binary[h // 2:, w // 2:],
            ]
            densities = [np.count_nonzero(q) / max(q.size, 1) for q in quadrants]
            density_var = np.var(densities)
        else:
            density_var = 0

        # 综合判断
        score = width_var * 2 + curvature * 0.1 + density_var * 5
        return score > 1.5

    def _estimate_stroke_count(self, region: np.ndarray) -> int:
        """估算笔画数量（基于连通域）"""
        if region.size == 0:
            return 0
        _, binary = cv2.threshold(region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return len(contours)

    def _recognize_via_ocr(self, region: np.ndarray) -> FormulaHypothesis:
        """本地 OCR 识别"""
        try:
            import pytesseract
            pil_img = Image.fromarray(region)
            text = pytesseract.image_to_string(pil_img, lang="chi_sim+eng")
            text = text.strip()

            conf = min(0.8, len(text) / 50) if text else 0.0

            return FormulaHypothesis(
                raw_text=text,
                latex=text,
                confidence=conf,
                source=FormulaSource.LOCAL_OCR,
                is_handwritten=False,
            )
        except Exception:
            return FormulaHypothesis(
                confidence=0.0,
                source=FormulaSource.LOCAL_OCR,
            )

    def _recognize_via_vision(self, region: np.ndarray) -> FormulaHypothesis:
        """Vision API 识别手写公式"""
        if self._llm_client is None:
            return FormulaHypothesis(
                confidence=0.0,
                source=FormulaSource.VISION_API,
            )

        try:
            import base64
            from io import BytesIO

            _, buffer = cv2.imencode(".png", region)
            b64 = base64.b64encode(buffer).decode("utf-8")

            response = self._llm_client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是数学公式识别专家。识别图片中的数学公式，"
                            "输出 LaTeX 格式。只输出 LaTeX，不要其他内容。"
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
                                "text": "请识别这个数学公式，输出 LaTeX。",
                            },
                        ],
                    },
                ],
                temperature=0.0,
                max_tokens=512,
            )

            latex = response.choices[0].message.content.strip()
            latex = latex.strip("$").strip("`").strip()

            return FormulaHypothesis(
                latex=latex,
                raw_text=latex,
                confidence=0.7,
                source=FormulaSource.VISION_API,
                is_handwritten=True,
            )
        except Exception:
            return FormulaHypothesis(
                confidence=0.0,
                source=FormulaSource.VISION_API,
            )

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
