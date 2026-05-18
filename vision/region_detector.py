"""vision/region_detector.py — Formula Region Detection

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  整图 OCR 是错的。因为：
    空白区域 → 干扰
    阴影     → 干扰
    横线     → 干扰
    页边     → 干扰
    中文说明 → 干扰

  正确方案：
    先检测哪些区域是数学公式
    只对检测到的公式区域做 OCR

  输出：
    FormulaRegion(
        bbox=(x1, y1, x2, y2),
        confidence=0.93,
        region_type="equation"
    )

  实现：
    第一版：OpenCV + 连通域
    - cv2.findContours() 识别高密度笔迹区域
    - 数学符号聚集区域检测
    - 6 层启发式过滤

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Optional

import cv2
import numpy as np
from PIL import Image


class FormulaRegionType(Enum):
    EQUATION = "equation"
    EXPRESSION = "expression"
    INLINE_MATH = "inline_math"
    DISPLAY_MATH = "display_math"
    MATRIX = "matrix"
    FRACTION = "fraction"
    TEXT = "text"
    MIXED = "mixed"
    NOISE = "noise"


@dataclass
class FormulaRegion:
    """数学公式区域 — 核心输出

    替代整图 OCR，只对检测到的公式区域做识别。

    bbox: (x1, y1, x2, y2) — 左上角 + 右下角坐标
    confidence: 检测置信度
    region_type: 区域类型（equation/expression/inline_math 等）
    """
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float = 0.0
    region_type: FormulaRegionType = FormulaRegionType.EQUATION
    density: float = 0.0
    aspect_ratio: float = 0.0
    stroke_density: float = 0.0
    symbol_count: int = 0
    image: Optional[np.ndarray] = None

    @property
    def x1(self) -> int:
        return self.bbox[0]

    @property
    def y1(self) -> int:
        return self.bbox[1]

    @property
    def x2(self) -> int:
        return self.bbox[2]

    @property
    def y2(self) -> int:
        return self.bbox[3]

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> Tuple[int, int]:
        return (self.bbox[0] + self.width // 2, self.bbox[1] + self.height // 2)

    def to_xywh(self) -> Tuple[int, int, int, int]:
        return (self.bbox[0], self.bbox[1], self.width, self.height)

    def crop_from(self, image: np.ndarray, padding: int = 5) -> np.ndarray:
        h, w = image.shape[:2]
        x0 = max(0, self.x1 - padding)
        y0 = max(0, self.y1 - padding)
        x1 = min(w, self.x2 + padding)
        y1 = min(h, self.y2 + padding)
        return image[y0:y1, x0:x1]


@dataclass
class RegionDetectionResult:
    """区域检测结果"""
    formula_regions: List[FormulaRegion] = field(default_factory=list)
    total_regions: int = 0
    filtered_noise: int = 0
    filtered_lines: int = 0
    filtered_shadow: int = 0
    filtered_margin: int = 0
    filtered_text: int = 0
    image_shape: Tuple[int, int] = (0, 0)

    @property
    def regions(self) -> List[FormulaRegion]:
        return self.formula_regions

    def get_by_type(self, region_type: FormulaRegionType) -> List[FormulaRegion]:
        return [r for r in self.formula_regions if r.region_type == region_type]

    def get_equations(self) -> List[FormulaRegion]:
        return [r for r in self.formula_regions
                if r.region_type in (FormulaRegionType.EQUATION,
                                     FormulaRegionType.DISPLAY_MATH,
                                     FormulaRegionType.EXPRESSION)]


class FormulaRegionDetector:
    """数学公式区域检测器

    管线：
      灰度图 → 二值化 → 形态学膨胀 → 连通域检测
      → 启发式过滤（6 层） → 公式分类 → 合并 → 排序

    过滤层：
      1. 面积太小 → 噪点
      2. 面积太大 → 阴影/背景
      3. 宽高比过大 → 横线/竖线
      4. 页边窄条 → 页边距
      5. 密度过低 → 阴影
      6. 密度过高 → 污渍/黑块
    """

    def __init__(self):
        self._min_area = 100
        self._max_area_ratio = 0.8
        self._max_aspect = 20.0
        self._min_density = 0.02
        self._max_density = 0.95
        self._h_merge_gap = 20
        self._v_merge_gap = 15

    def detect(self, image) -> RegionDetectionResult:
        """检测图片中的数学公式区域

        Args:
            image: PIL Image / numpy array / 文件路径

        Returns:
            RegionDetectionResult
        """
        img = self._load_image(image)
        gray = self._to_grayscale(img)
        binary = self._binarize(gray)

        stats = RegionDetectionResult(image_shape=gray.shape[:2])

        # ── Step 1: 形态学膨胀 ──
        # 水平膨胀：连接同行数学符号
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        dilated_h = cv2.dilate(binary, kernel_h, iterations=1)

        # 垂直微膨胀：连接上下标
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        dilated = cv2.dilate(dilated_h, kernel_v, iterations=1)

        # ── Step 2: 连通域检测 ──
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        h, w = gray.shape
        total_area = h * w

        # ── Step 3: 6 层启发式过滤 ──
        candidates = []
        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh

            # Layer 1: 面积太小 → 噪点
            if area < self._min_area:
                stats.filtered_noise += 1
                continue

            # Layer 2: 面积太大 → 阴影/背景
            if area > total_area * self._max_area_ratio:
                stats.filtered_shadow += 1
                continue

            aspect = bw / max(bh, 1)

            # Layer 3: 宽高比过大 → 横线
            if aspect > self._max_aspect:
                stats.filtered_lines += 1
                continue

            # Layer 3b: 高宽比过大 → 竖线
            if bh / max(bw, 1) > self._max_aspect:
                stats.filtered_lines += 1
                continue

            # Layer 4: 页边窄条
            if bw < w * 0.05 and (bx < 10 or bx + bw > w - 10):
                stats.filtered_margin += 1
                continue
            if bh < h * 0.05 and (by < 10 or by + bh > h - 10):
                stats.filtered_margin += 1
                continue

            # 计算密度
            roi = binary[by:by + bh, bx:bx + bw]
            density = np.count_nonzero(roi) / max(area, 1)

            # Layer 5: 密度过低 → 阴影
            if density < self._min_density:
                stats.filtered_shadow += 1
                continue

            # Layer 6: 密度过高 → 污渍/黑块
            if density > self._max_density:
                stats.filtered_noise += 1
                continue

            # ── Step 4: 公式特征分析 ──
            stroke_density = self._compute_stroke_density(roi)
            symbol_count = self._count_symbols(roi)
            region_type = self._classify_formula_region(
                aspect, density, stroke_density, symbol_count, bw, bh, w, h
            )

            # 中文文字区域过滤
            if region_type == FormulaRegionType.TEXT:
                stats.filtered_text += 1
                continue

            confidence = self._compute_confidence(density, stroke_density, symbol_count)

            candidates.append(FormulaRegion(
                bbox=(bx, by, bx + bw, by + bh),
                confidence=confidence,
                region_type=region_type,
                density=density,
                aspect_ratio=aspect,
                stroke_density=stroke_density,
                symbol_count=symbol_count,
            ))

        # ── Step 5: 合并相邻区域 ──
        merged = self._merge_regions(candidates)

        # ── Step 6: 阅读顺序排序 ──
        merged.sort(key=lambda r: (r.y1, r.x1))

        stats.formula_regions = merged
        stats.total_regions = len(merged)
        return stats

    def detect_and_crop(self, image, padding: int = 8) -> List[np.ndarray]:
        """检测公式区域并返回裁剪后的图片列表

        Args:
            image: 输入图片
            padding: 裁剪边距

        Returns:
            List[np.ndarray] — 每个公式区域的灰度图
        """
        img = self._load_image(image)
        gray = self._to_grayscale(img)
        result = self.detect(img)
        return [r.crop_from(gray, padding) for r in result.formula_regions]

    # ════════════════════════════════════════════════════════════
    # 公式特征分析
    # ════════════════════════════════════════════════════════════

    def _compute_stroke_density(self, roi: np.ndarray) -> float:
        """计算笔画密度 — 区分数学符号和中文文字

        数学符号：笔画少、密度低、结构稀疏
        中文文字：笔画多、密度高、结构紧密
        """
        if roi.size == 0:
            return 0.0

        # 距离变换 → 笔画宽度
        dist = cv2.distanceTransform(roi, cv2.DIST_L2, 5)
        stroke_pixels = dist[roi > 0]

        if len(stroke_pixels) == 0:
            return 0.0

        # 平均笔画宽度 / 区域高度 → 笔画密度指标
        avg_width = np.mean(stroke_pixels)
        roi_height = roi.shape[0]

        return avg_width / max(roi_height, 1)

    def _count_symbols(self, roi: np.ndarray) -> int:
        """计算符号数量 — 基于连通域计数

        数学公式：多个小连通域（符号分散）
        中文文字：少量大连通域（笔画连接）
        """
        if roi.size == 0:
            return 0

        # 腐蚀分离粘连符号
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        eroded = cv2.erode(roi, kernel, iterations=1)

        contours, _ = cv2.findContours(eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 过滤极小连通域
        min_cc_area = 4
        return sum(1 for c in contours if cv2.contourArea(c) > min_cc_area)

    def _classify_formula_region(self, aspect: float, density: float,
                                  stroke_density: float, symbol_count: int,
                                  cw: int, ch: int, img_w: int, img_h: int) -> FormulaRegionType:
        """分类公式区域类型

        判断逻辑：
          - 高密度 + 低符号数 + 低笔画密度 → 中文文字
          - 中密度 + 多符号 + 中笔画密度 → 数学公式
          - 宽区域 + 中密度 → 行内公式
          - 居中 + 低密度 → 展示公式
          - 多行 → 矩阵/分段函数
        """
        # 中文文字特征：高密度、少符号、笔画紧密
        if density > 0.35 and symbol_count < 5 and stroke_density < 0.1:
            return FormulaRegionType.TEXT

        # 矩阵/分段函数：高度大、多符号
        if ch > img_h * 0.15 and symbol_count > 8 and aspect < 2:
            return FormulaRegionType.MATRIX

        # 分数线特征：宽区域、中间有水平线
        if aspect > 1.5 and 0.1 < density < 0.3:
            return FormulaRegionType.FRACTION

        # 展示公式：居中、宽度大
        center_x = cw / 2
        if abs(center_x - img_w / 2) < img_w * 0.2 and cw > img_w * 0.3:
            return FormulaRegionType.DISPLAY_MATH

        # 行内公式：窄、与文字同行
        if aspect > 3 and density < 0.2:
            return FormulaRegionType.INLINE_MATH

        # 默认：方程/表达式
        if density > 0.15:
            return FormulaRegionType.EQUATION

        return FormulaRegionType.EXPRESSION

    def _compute_confidence(self, density: float, stroke_density: float,
                            symbol_count: int) -> float:
        """计算检测置信度"""
        # 密度贡献（0.15-0.4 是公式最佳区间）
        density_score = 1.0 - abs(density - 0.25) * 3
        density_score = max(0.0, min(1.0, density_score))

        # 笔画密度贡献
        stroke_score = min(1.0, stroke_density * 5)

        # 符号数量贡献（3-15 个符号最可信）
        if 3 <= symbol_count <= 15:
            symbol_score = 0.9
        elif 1 <= symbol_count <= 25:
            symbol_score = 0.6
        else:
            symbol_score = 0.3

        return min(0.95, density_score * 0.4 + stroke_score * 0.3 + symbol_score * 0.3)

    # ════════════════════════════════════════════════════════════
    # 区域合并
    # ════════════════════════════════════════════════════════════

    def _merge_regions(self, regions: List[FormulaRegion]) -> List[FormulaRegion]:
        """合并相邻或重叠的公式区域"""
        if not regions:
            return []

        boxes = [(r.x1, r.y1, r.x2, r.y2) for r in regions]
        region_data = list(regions)

        merged = True
        while merged:
            merged = False
            new_boxes = []
            new_data = []
            used = [False] * len(boxes)

            for i in range(len(boxes)):
                if used[i]:
                    continue

                for j in range(i + 1, len(boxes)):
                    if used[j]:
                        continue

                    if self._boxes_nearby(boxes[i], boxes[j]):
                        ix1, iy1, ix2, iy2 = boxes[i]
                        jx1, jy1, jx2, jy2 = boxes[j]

                        boxes[i] = (min(ix1, jx1), min(iy1, jy1),
                                    max(ix2, jx2), max(iy2, jy2))

                        # 合并后类型取优先级高的
                        type_priority = {
                            FormulaRegionType.EQUATION: 5,
                            FormulaRegionType.DISPLAY_MATH: 4,
                            FormulaRegionType.EXPRESSION: 3,
                            FormulaRegionType.INLINE_MATH: 2,
                            FormulaRegionType.FRACTION: 4,
                            FormulaRegionType.MATRIX: 4,
                            FormulaRegionType.MIXED: 1,
                        }
                        if type_priority.get(region_data[i].region_type, 0) < \
                           type_priority.get(region_data[j].region_type, 0):
                            region_data[i] = region_data[j]

                        used[j] = True
                        merged = True

                new_boxes.append(boxes[i])
                new_data.append(region_data[i])
                used[i] = True

            boxes = new_boxes
            region_data = new_data

        result = []
        for i, b in enumerate(boxes):
            r = region_data[i]
            result.append(FormulaRegion(
                bbox=b,
                confidence=r.confidence,
                region_type=r.region_type,
                density=r.density,
                aspect_ratio=r.aspect_ratio,
                stroke_density=r.stroke_density,
                symbol_count=r.symbol_count,
            ))

        return result

    def _boxes_nearby(self, box_a, box_b) -> bool:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        # 扩展 box_a 边界
        ea1 = (ax1 - self._h_merge_gap, ay1 - self._v_merge_gap,
               ax2 + self._h_merge_gap, ay2 + self._v_merge_gap)

        return ea1[0] < bx2 and ea1[2] > bx1 and ea1[1] < by2 and ea1[3] > by1

    # ════════════════════════════════════════════════════════════
    # 辅助
    # ════════════════════════════════════════════════════════════

    def _load_image(self, image) -> np.ndarray:
        if isinstance(image, str):
            return cv2.imread(image)
        if isinstance(image, Image.Image):
            return np.array(image)
        if isinstance(image, np.ndarray):
            return image
        raise ValueError(f"Unsupported image type: {type(image)}")

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def _binarize(self, img: np.ndarray) -> np.ndarray:
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary


# ══════════════════════════════════════════════════════════════
# 兼容旧接口
# ══════════════════════════════════════════════════════════════

class RegionType(Enum):
    FORMULA = auto()
    TEXT = auto()
    MIXED = auto()
    TABLE = auto()
    GRAPH = auto()
    NOISE = auto()


@dataclass
class DetectedRegion:
    bbox: Tuple[int, int, int, int]
    region_type: RegionType = RegionType.FORMULA
    confidence: float = 0.0
    density: float = 0.0
    aspect_ratio: float = 0.0
    image: Optional[np.ndarray] = None
    label: str = ""


MathRegionDetector = FormulaRegionDetector
