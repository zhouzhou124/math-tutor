"""vision/preprocess.py — Math Image Preprocessor

═══════════════════════════════════════════════════════════════
两阶段流水线
═══════════════════════════════════════════════════════════════

  阶段 1: 图片增强
    gray → CLAHE → adaptive_threshold → morphology_close → sharpen → deskew

  阶段 2: 区域检测（关键）
    先检测数学公式区域，排除空白/横线/阴影/页边干扰
    只对检测到的区域做 OCR

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, List

import cv2
import numpy as np
from PIL import Image


@dataclass
class MathRegion:
    """数学公式区域"""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    image: np.ndarray = None
    label: str = "formula"
    confidence: float = 0.0


@dataclass
class PreprocessResult:
    image: np.ndarray
    rotation_angle: float = 0.0
    formula_regions: List[Tuple[int, int, int, int]] = field(default_factory=list)
    math_regions: List[MathRegion] = field(default_factory=list)
    confidence: float = 0.0


class MathImagePreprocessor:
    """数学公式图片预处理器

    阶段 1: gray → CLAHE → adaptive_threshold → morphology_close → sharpen → deskew
    阶段 2: detect_math_regions → 逐区域提取
    """

    def __init__(self):
        self._debug_mode = False

    def set_debug(self, enabled: bool = True):
        self._debug_mode = enabled
        return self

    # ════════════════════════════════════════════════════════════
    # 主入口
    # ════════════════════════════════════════════════════════════

    def process(self, image, auto_crop: bool = True) -> PreprocessResult:
        """完整预处理流水线

        阶段 1: gray → CLAHE → adaptive_threshold → morphology_close → sharpen → deskew
        阶段 2: detect_math_regions → 逐区域提取

        Args:
            image: PIL Image 或 numpy array
            auto_crop: 是否裁剪到最大公式区域

        Returns:
            PreprocessResult (含 math_regions)
        """
        img = self._to_numpy(image)

        # Step 1: gray
        img = self._to_grayscale(img)

        # Step 2: CLAHE 增强
        img = self.enhance_formula_contrast(img)

        # Step 3: 自适应阈值
        img = self.adaptive_threshold(img)

        # Step 4: morphology close
        img = self.morphology_close(img)

        # Step 5: sharpen
        img = self.sharpen(img)

        # Step 6: deskew
        img, angle = self.deskew(img)

        # 阶段 2: 区域检测
        math_regions = self.detect_math_regions(img)

        # 兼容旧接口
        formula_regions = [r.bbox for r in math_regions]

        if auto_crop and math_regions:
            img = self._crop_to_region(img, math_regions[0].bbox)

        return PreprocessResult(
            image=img,
            rotation_angle=angle,
            formula_regions=formula_regions,
            math_regions=math_regions,
            confidence=self._estimate_confidence(img, formula_regions),
        )

    def process_for_ocr(self, image) -> List[np.ndarray]:
        """专为 OCR 准备：返回逐区域裁剪后的图片列表

        用法:
            regions = preprocessor.process_for_ocr(img)
            for region_img in regions:
                text = pytesseract.image_to_string(region_img)

        Args:
            image: PIL Image 或 numpy array

        Returns:
            List[np.ndarray] — 每个数学区域的灰度图
        """
        img = self._to_numpy(image)
        original = self._to_grayscale(img)

        # 阶段 1: 增强（在原图上操作，保留灰度信息给 OCR）
        enhanced = self.enhance_formula_contrast(original)

        # 阶段 2: 在增强图上检测区域
        binary = self.adaptive_threshold(enhanced)
        binary = self.morphology_close(binary)
        binary = self.sharpen(binary)
        binary, _ = self.deskew(binary)

        # 同步旋转原图
        enhanced, _ = self.deskew(enhanced)

        # 检测区域
        math_regions = self._detect_regions_from_binary(binary)

        # 从增强后的灰度图（非二值图）中裁剪各区域
        region_images = []
        for mr in math_regions:
            x, y, w, h = mr.bbox
            padding = 8
            x0 = max(0, x - padding)
            y0 = max(0, y - padding)
            x1 = min(enhanced.shape[1], x + w + padding)
            y1 = min(enhanced.shape[0], y + h + padding)
            crop = enhanced[y0:y1, x0:x1]
            region_images.append(crop)

        return region_images

    # ════════════════════════════════════════════════════════════
    # 区域检测（关键）
    # ════════════════════════════════════════════════════════════

    def detect_math_regions(self, image: np.ndarray) -> List[MathRegion]:
        """检测图片中的数学公式区域

        使用 MSER + 轮廓检测 + 启发式过滤：
        - 排除大面积空白
        - 排除横线（宽高比过大）
        - 排除阴影（面积过大但密度低）
        - 排除页边（靠近边缘的窄条）
        - 合并相邻区域

        Args:
            image: 二值化或灰度图

        Returns:
            List[MathRegion] — 按从上到下、从左到右排序
        """
        img = self._ensure_grayscale(image)

        if len(np.unique(img)) > 2:
            binary = self._binarize(img)
        else:
            binary = img.copy()

        return self._detect_regions_from_binary(binary)

    def _detect_regions_from_binary(self, binary: np.ndarray) -> List[MathRegion]:
        """从二值图检测数学区域（核心算法）"""
        h, w = binary.shape
        total_area = h * w

        # ── 1. 形态学操作：水平膨胀连接同行字符 ──
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        dilated_h = cv2.dilate(binary, kernel_h, iterations=1)

        # 垂直微膨胀连接上下标
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        dilated = cv2.dilate(dilated_h, kernel_v, iterations=1)

        # ── 2. 查找轮廓 ──
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # ── 3. 启发式过滤 ──
        candidates = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch

            # 过滤：面积太小（噪点）
            if area < 100:
                continue

            # 过滤：面积太大（整页阴影/背景）— 超过图片 80%
            if area > total_area * 0.8:
                continue

            # 过滤：横线（宽高比 > 20:1）
            aspect = cw / max(ch, 1)
            if aspect > 20:
                continue

            # 过滤：竖线（高宽比 > 20:1）
            if ch / max(cw, 1) > 20:
                continue

            # 过滤：页边窄条（宽度 < 图片 5% 且靠近边缘）
            if cw < w * 0.05 and (x < 10 or x + cw > w - 10):
                continue

            # 过滤：页边窄条（高度 < 图片 5% 且靠近边缘）
            if ch < h * 0.05 and (y < 10 or y + ch > h - 10):
                continue

            # 计算区域密度（前景像素占比）
            roi = binary[y:y + ch, x:x + cw]
            density = np.count_nonzero(roi) / max(area, 1)

            # 过滤：密度过低（大面积阴影）
            if density < 0.02:
                continue

            # 过滤：密度过高（纯黑块/污渍）
            if density > 0.95:
                continue

            candidates.append(MathRegion(
                bbox=(x, y, cw, ch),
                confidence=min(0.9, density * 3 + 0.2),
                label="formula",
            ))

        # ── 4. 合并重叠/相邻区域 ──
        merged = self._merge_regions(candidates, h_gap=20, v_gap=15)

        # ── 5. 按阅读顺序排序（从上到下，从左到右）──
        merged.sort(key=lambda r: (r.bbox[1], r.bbox[0]))

        return merged

    def _merge_regions(self, regions: List[MathRegion],
                       h_gap: int = 20, v_gap: int = 15) -> List[MathRegion]:
        """合并相邻或重叠的区域"""
        if not regions:
            return []

        # 转为 (x, y, w, h) 列表
        boxes = [list(r.bbox) for r in regions]

        merged = True
        while merged:
            merged = False
            new_boxes = []
            used = [False] * len(boxes)

            for i in range(len(boxes)):
                if used[i]:
                    continue
                xi, yi, wi, hi = boxes[i]

                for j in range(i + 1, len(boxes)):
                    if used[j]:
                        continue
                    xj, yj, wj, hj = boxes[j]

                    if self._boxes_nearby(
                        (xi, yi, wi, hi), (xj, yj, wj, hj), h_gap, v_gap
                    ):
                        # 合并
                        x_merge = min(xi, xj)
                        y_merge = min(yi, yj)
                        x_end = max(xi + wi, xj + wj)
                        y_end = max(yi + hi, yj + hj)
                        boxes[i] = [x_merge, y_merge, x_end - x_merge, y_end - y_merge]
                        xi, yi, wi, hi = boxes[i]
                        used[j] = True
                        merged = True

                new_boxes.append(boxes[i])
                used[i] = True

            boxes = new_boxes

        return [
            MathRegion(bbox=(b[0], b[1], b[2], b[3]), confidence=0.7)
            for b in boxes
        ]

    @staticmethod
    def _boxes_nearby(box_a, box_b, h_gap, v_gap):
        """判断两个框是否相邻（考虑间距容差）"""
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b

        # 扩展 box_a 的边界
        ax1, ay1 = ax - h_gap, ay - v_gap
        ax2, ay2 = ax + aw + h_gap, ay + ah + v_gap
        bx1, by1 = bx, by
        bx2, by2 = bx + bw, by + bh

        # 检查是否重叠
        if ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1:
            return True
        return False

    def _binarize(self, img: np.ndarray) -> np.ndarray:
        """Otsu 二值化"""
        _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary

    # ════════════════════════════════════════════════════════════
    # 图片增强步骤
    # ════════════════════════════════════════════════════════════

    def enhance_formula_contrast(self, image: np.ndarray) -> np.ndarray:
        """CLAHE 对比度增强 — 解决光照不均"""
        img = self._ensure_grayscale(image)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(img)
        p2, p98 = np.percentile(enhanced, (2, 98))
        stretched = cv2.normalize(enhanced, None, int(p2), int(p98), cv2.NORM_MINMAX)
        return stretched.astype(np.uint8)

    def adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """自适应二值化 — 局部阈值处理光照不均"""
        img = self._ensure_grayscale(image)
        thresh = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=15,
            C=2,
        )
        return thresh

    def morphology_close(self, image: np.ndarray) -> np.ndarray:
        """形态学闭运算 — 填充字符内部断裂"""
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=1)
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open, iterations=1)
        return opened

    def sharpen(self, image: np.ndarray) -> np.ndarray:
        """Unsharp Mask 锐化 — 增强边缘清晰度"""
        blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=3)
        alpha = 1.5
        sharpened = cv2.addWeighted(image, 1 + alpha, blurred, -alpha, 0)
        return sharpened

    def deskew(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """倾斜校正 — Hough 直线检测 + 旋转"""
        img = self._ensure_grayscale(image)
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
        if lines is None:
            return img, 0.0
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = (theta * 180 / np.pi) - 90
            if abs(angle) < 45:
                angles.append(angle)
        if not angles:
            return img, 0.0
        median_angle = float(np.median(angles))
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated, median_angle

    def denoise(self, image: np.ndarray) -> np.ndarray:
        """去噪 — 中值 + 高斯 + 双边滤波"""
        img = self._ensure_grayscale(image)
        img = cv2.medianBlur(img, 3)
        img = cv2.GaussianBlur(img, (5, 5), 0)
        img = cv2.bilateralFilter(img, 9, 75, 75)
        return img

    # ════════════════════════════════════════════════════════════
    # 辅助
    # ════════════════════════════════════════════════════════════

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

    def _ensure_grayscale(self, image: np.ndarray) -> np.ndarray:
        return self._to_grayscale(image)

    def _crop_to_region(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = bbox
        return image[y:y + h, x:x + w]

    def _estimate_confidence(self, image: np.ndarray, regions: List[Tuple[int, int, int, int]]) -> float:
        if not regions:
            return 0.3
        h, w = image.shape[:2]
        total_area = h * w
        region_area = sum(r[2] * r[3] for r in regions)
        coverage_ratio = min(region_area / total_area, 0.5)
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        sharpness = np.var(laplacian) / 10000
        return min(0.95, 0.3 + coverage_ratio * 2 + min(sharpness, 0.4))

    def to_pil(self, image: np.ndarray) -> Image.Image:
        return Image.fromarray(image)


def preprocess_image(image, auto_crop: bool = True) -> PreprocessResult:
    processor = MathImagePreprocessor()
    return processor.process(image, auto_crop)


def enhance_for_ocr(image) -> np.ndarray:
    processor = MathImagePreprocessor()
    result = processor.process(image, auto_crop=True)
    return result.image
