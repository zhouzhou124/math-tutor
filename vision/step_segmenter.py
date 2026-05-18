"""vision/step_segmenter.py — 解题步骤分割（增强版）

═══════════════════════════════════════════════════════════════
核心思想 — 学生不是写公式，而是写推导过程
═══════════════════════════════════════════════════════════════

  真正难点：
    学生写的是推导过程，不是孤立公式。

  例如：
    f(x) = x² + 1
         = (x+1)² - 2x
         = ...

  每一步都必须分离。

  切分依据：
    ┌──────────┬──────────────────────────────┐
    │ 特征     │ 用途                          │
    ├──────────┼──────────────────────────────┤
    │ 等号位置 │ 步骤分界                      │
    │ 行间距   │ 推导段落                      │
    │ 箭头 →   │ 推导关系                      │
    │ ∴        │ 结论                          │
    │ 编号     │ 步骤编号                      │
    │ ∵        │ 因为（前提）                  │
    │ ⟹       │ 蕴含（逻辑推导）              │
    └──────────┴──────────────────────────────┘

  输出：
    [VisualStep(...), VisualStep(...), VisualStep(...)]

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, List, Optional, Dict

import cv2
import numpy as np
from PIL import Image


class StepLevel(Enum):
    MAIN = auto()
    SUB = auto()
    CONTINUATION = auto()


class StepMarkerType(Enum):
    EQUALS = "equals"
    ARROW = "arrow"
    THEREFORE = "therefore"
    BECAUSE = "because"
    IMPLIES = "implies"
    NUMBERING = "numbering"
    NONE = "none"


class DerivationRole(Enum):
    PREMISE = "premise"
    DERIVATION = "derivation"
    CONCLUSION = "conclusion"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


@dataclass
class StepMarker:
    """步骤标记 — 等号/箭头/∴/∵ 等视觉标记"""
    marker_type: StepMarkerType = StepMarkerType.NONE
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    symbol: str = ""
    confidence: float = 0.0
    is_aligned: bool = False
    alignment_x: int = 0


@dataclass
class VisualStep:
    """视觉步骤 — 图片中的一个推理步骤

    每个 VisualStep 包含：
      - 位置 (bbox)
      - 区域图片
      - 步骤编号
      - 层级（主步骤/子步骤/续行）
      - 标记（等号/箭号/∴/∵）
      - 推导角色（前提/推导/结论）
    """
    step_id: str = ""
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    image: Optional[np.ndarray] = None
    level: StepLevel = StepLevel.MAIN
    step_number: int = 0
    indent: int = 0
    confidence: float = 0.0
    has_equation_sign: bool = False
    has_numbering: bool = False
    numbering_text: str = ""
    markers: List[StepMarker] = field(default_factory=list)
    derivation_role: DerivationRole = DerivationRole.UNKNOWN
    equals_alignment_x: int = 0
    is_continuation: bool = False
    continuation_of: Optional[str] = None
    text_content: str = ""


@dataclass
class StepSegmentationResult:
    """步骤分割结果"""
    steps: List[VisualStep] = field(default_factory=list)
    total_steps: int = 0
    main_steps: int = 0
    sub_steps: int = 0
    continuation_steps: int = 0
    avg_gap: float = 0.0
    equals_columns: List[int] = field(default_factory=list)
    derivation_chain: List[List[str]] = field(default_factory=list)


class StepSegmenter:
    """解题步骤分割器（增强版）

    管线：
      1. 预处理 → 二值化
      2. 水平投影 → 检测文本行
      3. 行间距分析 → 检测步骤边界
      4. 等号检测 → 对齐分析 + 续行检测
      5. 箭头检测 → 推导关系
      6. ∴/∵ 检测 → 结论/前提
      7. 编号检测 → 显式步骤标记
      8. 推导链构建 → 步骤间关系
    """

    def __init__(self):
        self._gap_threshold_factor = 1.8
        self._min_step_height = 15
        self._indent_threshold = 30
        self._equals_min_width = 8
        self._equals_max_width = 40
        self._equals_gap = 6
        self._arrow_templates: List[np.ndarray] = []
        self._therefore_templates: List[np.ndarray] = []

    def segment(self, image) -> StepSegmentationResult:
        img = self._to_numpy(image)
        gray = self._to_grayscale(img)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # ── Step 1: 水平投影 → 检测行 ──
        h_projection = np.sum(binary, axis=1)
        rows = self._detect_rows(h_projection, binary.shape[1])

        if not rows:
            return StepSegmentationResult()

        # ── Step 2: 行间距分析 → 步骤边界 ──
        steps = self._detect_steps_from_rows(rows, gray, binary)

        # ── Step 3: 等号检测 → 对齐 + 续行 ──
        steps = self._detect_equals_signs(steps, binary, gray)

        # ── Step 4: 箭头检测 → 推导关系 ──
        steps = self._detect_arrows(steps, binary, gray)

        # ── Step 5: ∴/∵ 检测 → 结论/前提 ──
        steps = self._detect_logical_markers(steps, binary, gray)

        # ── Step 6: 编号检测 ──
        steps = self._detect_numbering(steps, gray)

        # ── Step 7: 续行检测（等号对齐的连续行）──
        steps = self._detect_continuations(steps)

        # ── Step 8: 推导角色标注 ──
        steps = self._assign_derivation_roles(steps)

        # ── Step 9: 推导链构建 ──
        derivation_chains = self._build_derivation_chains(steps)

        # ── Step 10: 分配编号 ──
        step_num = 0
        main_count = 0
        sub_count = 0
        cont_count = 0
        for s in steps:
            step_num += 1
            s.step_id = f"step_{step_num:03d}"
            s.step_number = step_num
            if s.level == StepLevel.MAIN:
                main_count += 1
            elif s.level == StepLevel.SUB:
                sub_count += 1
            else:
                cont_count += 1

        # 计算平均间距
        gaps = []
        for i in range(len(steps) - 1):
            _, y1, _, h1 = steps[i].bbox
            _, y2, _, _ = steps[i + 1].bbox
            gaps.append(y2 - (y1 + h1))
        avg_gap = float(np.mean(gaps)) if gaps else 0.0

        # 等号列
        eq_cols = []
        for s in steps:
            if s.equals_alignment_x > 0:
                eq_cols.append(s.equals_alignment_x)

        return StepSegmentationResult(
            steps=steps,
            total_steps=len(steps),
            main_steps=main_count,
            sub_steps=sub_count,
            continuation_steps=cont_count,
            avg_gap=avg_gap,
            equals_columns=eq_cols,
            derivation_chain=derivation_chains,
        )

    # ════════════════════════════════════════════════════════════
    # Step 1-2: 行检测 + 步骤边界
    # ════════════════════════════════════════════════════════════

    def _detect_rows(self, h_projection: np.ndarray,
                     img_width: int) -> List[Tuple[int, int]]:
        threshold = img_width * 0.005
        rows = []
        in_row = False
        start = 0

        for y, val in enumerate(h_projection):
            if val > threshold and not in_row:
                in_row = True
                start = y
            elif val <= threshold and in_row:
                in_row = False
                rows.append((start, y))

        if in_row:
            rows.append((start, len(h_projection)))

        return rows

    def _detect_steps_from_rows(self, rows: List[Tuple[int, int]],
                                gray: np.ndarray,
                                binary: np.ndarray) -> List[VisualStep]:
        if len(rows) <= 1:
            if rows:
                y0, y1 = rows[0]
                return [VisualStep(
                    bbox=(0, y0, gray.shape[1], y1 - y0),
                    image=gray[y0:y1, :],
                    level=StepLevel.MAIN,
                    confidence=0.5,
                )]
            return []

        gaps = [rows[i + 1][0] - rows[i][1] for i in range(len(rows) - 1)]
        avg_gap = np.mean(gaps) if gaps else 0
        step_gap_threshold = avg_gap * self._gap_threshold_factor

        steps = []
        current_rows = [rows[0]]

        for i in range(1, len(rows)):
            gap = gaps[i - 1]
            if gap > step_gap_threshold and gap > self._min_step_height:
                step = self._rows_to_step(current_rows, gray, binary)
                steps.append(step)
                current_rows = [rows[i]]
            else:
                current_rows.append(rows[i])

        if current_rows:
            step = self._rows_to_step(current_rows, gray, binary)
            steps.append(step)

        return steps

    def _rows_to_step(self, rows: List[Tuple[int, int]],
                      gray: np.ndarray,
                      binary: np.ndarray) -> VisualStep:
        y_start = rows[0][0]
        y_end = rows[-1][1]
        h = y_end - y_start

        roi = binary[y_start:y_end, :]
        col_proj = np.sum(roi, axis=0)
        threshold = roi.shape[0] * 0.05
        nonzero_cols = np.where(col_proj > threshold)[0]

        if len(nonzero_cols) > 0:
            x_start = max(0, int(nonzero_cols[0]) - 5)
            x_end = min(gray.shape[1], int(nonzero_cols[-1]) + 5)
            w = x_end - x_start
            indent = x_start
        else:
            x_start = 0
            w = gray.shape[1]
            indent = 0

        level = StepLevel.MAIN
        if indent > self._indent_threshold:
            level = StepLevel.SUB

        return VisualStep(
            bbox=(x_start, y_start, w, h),
            image=gray[y_start:y_end, x_start:x_start + w],
            level=level,
            indent=indent,
            confidence=0.6,
        )

    # ════════════════════════════════════════════════════════════
    # Step 3: 等号检测 — 步骤分界 + 对齐分析
    # ════════════════════════════════════════════════════════════

    def _detect_equals_signs(self, steps: List[VisualStep],
                             binary: np.ndarray,
                             gray: np.ndarray) -> List[VisualStep]:
        """检测等号 — 核心步骤分界标记

        等号特征：
          - 两条水平短线
          - 上下间距均匀
          - 水平对齐

        等号对齐 = 续行推导：
          f(x) = x² + 1
               = (x+1)² - 2x    ← 等号对齐，是续行
        """
        for step in steps:
            x, y, w, h = step.bbox
            roi = binary[y:y + h, x:x + w]

            if roi.size == 0:
                continue

            # 方法1: 模板匹配检测等号
            equals_positions = self._find_equals_in_roi(roi)

            if equals_positions:
                step.has_equation_sign = True
                for eq_x, eq_y, eq_w, eq_h in equals_positions:
                    marker = StepMarker(
                        marker_type=StepMarkerType.EQUALS,
                        bbox=(x + eq_x, y + eq_y, eq_w, eq_h),
                        symbol="=",
                        confidence=0.8,
                        alignment_x=x + eq_x + eq_w // 2,
                    )
                    marker.is_aligned = True
                    step.markers.append(marker)

                # 记录等号对齐位置
                main_eq = min(equals_positions, key=lambda e: e[0])
                step.equals_alignment_x = x + main_eq[0] + main_eq[2] // 2

        # 分析等号对齐 → 标记续行
        if len(steps) > 1:
            alignment_groups = self._group_by_equals_alignment(steps)
            for group in alignment_groups:
                if len(group) > 1:
                    for i in range(1, len(group)):
                        group[i].is_continuation = True
                        group[i].continuation_of = group[i - 1].step_id or f"step_{group[i-1].step_number:03d}"
                        group[i].level = StepLevel.CONTINUATION

        return steps

    def _find_equals_in_roi(self, roi: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """在 ROI 中检测等号位置

        等号 = 两条水平短线，上下间距均匀
        """
        if roi.shape[0] < 6 or roi.shape[1] < self._equals_min_width:
            return []

        results = []

        # 水平线检测
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 1))
        horizontal = cv2.morphologyEx(roi, cv2.MORPH_OPEN, kernel)

        # 找水平线轮廓
        contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h_lines = []
        for cnt in contours:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            aspect = cw / max(ch, 1)
            if aspect > 3 and cw > self._equals_min_width and cw < self._equals_max_width * 2:
                h_lines.append((cx, cy, cw, ch))

        # 配对：找两条距离相近的水平线 = 等号
        h_lines.sort(key=lambda l: (l[1], l[0]))

        for i in range(len(h_lines) - 1):
            l1 = h_lines[i]
            l2 = h_lines[i + 1]

            # 垂直距离
            v_gap = l2[1] - (l1[1] + l1[3])

            # 水平重叠
            x_overlap = max(0, min(l1[0] + l1[2], l2[0] + l2[2]) - max(l1[0], l2[0]))

            if (self._equals_gap - 2 <= v_gap <= self._equals_gap + 8 and
                    x_overlap > min(l1[2], l2[2]) * 0.5):
                eq_x = min(l1[0], l2[0])
                eq_y = l1[1]
                eq_w = max(l1[0] + l1[2], l2[0] + l2[2]) - eq_x
                eq_h = (l2[1] + l2[3]) - l1[1]
                results.append((eq_x, eq_y, eq_w, eq_h))

        return results

    def _group_by_equals_alignment(self, steps: List[VisualStep]) -> List[List[VisualStep]]:
        """按等号对齐位置分组 → 检测续行推导

        例如：
          f(x) = x² + 1       ← 等号在 x=200
               = (x+1)² - 2x  ← 等号在 x=200 → 续行
        """
        groups = []
        tolerance = 20

        aligned_steps = [s for s in steps if s.equals_alignment_x > 0]

        if not aligned_steps:
            return groups

        current_group = [aligned_steps[0]]

        for i in range(1, len(aligned_steps)):
            prev = current_group[-1]
            curr = aligned_steps[i]

            # 检查是否相邻
            prev_idx = steps.index(prev)
            curr_idx = steps.index(curr)

            if (curr_idx == prev_idx + 1 and
                    abs(curr.equals_alignment_x - prev.equals_alignment_x) < tolerance):
                current_group.append(curr)
            else:
                if len(current_group) > 1:
                    groups.append(current_group)
                current_group = [curr]

        if len(current_group) > 1:
            groups.append(current_group)

        return groups

    # ════════════════════════════════════════════════════════════
    # Step 4: 箭头检测 → 推导关系
    # ════════════════════════════════════════════════════════════

    def _detect_arrows(self, steps: List[VisualStep],
                       binary: np.ndarray,
                       gray: np.ndarray) -> List[VisualStep]:
        """检测箭头 → 推导关系标记

        箭头类型：
          →  : 推导
          ⇒  : 蕴含
          ⟹  : 逻辑推导
          ←  : 反推
          ↔  : 等价
        """
        for step in steps:
            x, y, w, h = step.bbox
            roi = binary[y:y + h, x:x + w]

            if roi.size == 0:
                continue

            arrows = self._find_arrows_in_roi(roi)

            for arrow_x, arrow_y, arrow_w, arrow_h, arrow_type in arrows:
                marker = StepMarker(
                    marker_type=StepMarkerType.ARROW,
                    bbox=(x + arrow_x, y + arrow_y, arrow_w, arrow_h),
                    symbol=arrow_type,
                    confidence=0.7,
                )
                step.markers.append(marker)

        return steps

    def _find_arrows_in_roi(self, roi: np.ndarray) -> List[Tuple[int, int, int, int, str]]:
        """在 ROI 中检测箭头

        箭头特征：
          - 水平线段 + 右端三角形
          - 或 ⇒ 双线箭头
        """
        results = []
        h, w = roi.shape

        if h < 5 or w < 15:
            return results

        # 水平线检测
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
        horizontal = cv2.morphologyEx(roi, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            aspect = cw / max(ch, 1)

            if aspect > 4 and cw > 15:
                # 检查右端是否有三角形（箭头头部）
                right_region = roi[cy:cy + ch, min(cx + cw - 8, w):min(cx + cw + 5, w)]

                if right_region.size > 0 and np.mean(right_region) > 30:
                    # 判断箭头类型
                    arrow_type = "→"
                    if ch > 4:
                        arrow_type = "⇒"

                    results.append((cx, cy, cw, ch, arrow_type))

        return results

    # ════════════════════════════════════════════════════════════
    # Step 5: ∴/∵ 检测 → 结论/前提
    # ════════════════════════════════════════════════════════════

    def _detect_logical_markers(self, steps: List[VisualStep],
                                binary: np.ndarray,
                                gray: np.ndarray) -> List[VisualStep]:
        """检测 ∴ (因此) 和 ∵ (因为) 标记

        ∴ 特征：
          - 三个点呈三角形排列
          - 通常在行首

        ∵ 特征：
          - 三个点呈倒三角形排列
          - 通常在行首
        """
        for step in steps:
            x, y, w, h = step.bbox
            # 只检查行首区域
            left_roi = binary[y:y + h, x:min(x + 50, x + w)]

            if left_roi.size == 0:
                continue

            # 检测点状模式
            dots = self._find_dot_patterns(left_roi)

            for dot_x, dot_y, dot_w, dot_h, pattern_type in dots:
                if pattern_type == "triangle":
                    marker = StepMarker(
                        marker_type=StepMarkerType.THEREFORE,
                        bbox=(x + dot_x, y + dot_y, dot_w, dot_h),
                        symbol="∴",
                        confidence=0.7,
                    )
                    step.markers.append(marker)
                    step.derivation_role = DerivationRole.CONCLUSION

                elif pattern_type == "inverted_triangle":
                    marker = StepMarker(
                        marker_type=StepMarkerType.BECAUSE,
                        bbox=(x + dot_x, y + dot_y, dot_w, dot_h),
                        symbol="∵",
                        confidence=0.7,
                    )
                    step.markers.append(marker)
                    step.derivation_role = DerivationRole.PREMISE

        return steps

    def _find_dot_patterns(self, roi: np.ndarray) -> List[Tuple[int, int, int, int, str]]:
        """检测点状模式 — ∴ 或 ∵

        ∴ = 上方1个点 + 下方2个点（三角形）
        ∵ = 上方2个点 + 下方1个点（倒三角形）
        """
        results = []

        # 检测小圆点（连通域）
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        dots = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            aspect = cw / max(ch, 1)

            # 点的特征：小面积、近似圆形
            if 4 < area < 200 and 0.3 < aspect < 3:
                center_x = cx + cw // 2
                center_y = cy + ch // 2
                dots.append((center_x, center_y, cx, cy, cw, ch))

        if len(dots) < 3:
            return results

        # 尝试找3个点组成 ∴ 或 ∵
        from itertools import combinations

        for combo in combinations(dots, 3):
            xs = [d[0] for d in combo]
            ys = [d[1] for d in combo]

            # 检查3个点是否紧凑
            x_range = max(xs) - min(xs)
            y_range = max(ys) - min(ys)

            if x_range > 30 or y_range > 30:
                continue

            # 按y排序
            sorted_by_y = sorted(combo, key=lambda d: d[1])

            top_dots = [d for d in sorted_by_y if d[1] < sorted_by_y[1][1] + 3]
            bottom_dots = [d for d in sorted_by_y if d[1] > sorted_by_y[1][1] - 3]

            # ∴ : 上方1个点，下方2个点
            if len(top_dots) == 1 and len(bottom_dots) == 2:
                all_x = [d[2] for d in combo]
                all_y = [d[3] for d in combo]
                all_w = [d[4] for d in combo]
                all_h = [d[5] for d in combo]
                results.append((
                    min(all_x), min(all_y),
                    max(x + w for x, w in zip(all_x, all_w)) - min(all_x),
                    max(y + h for y, h in zip(all_y, all_h)) - min(all_y),
                    "triangle",
                ))
                break

            # ∵ : 上方2个点，下方1个点
            if len(top_dots) == 2 and len(bottom_dots) == 1:
                all_x = [d[2] for d in combo]
                all_y = [d[3] for d in combo]
                all_w = [d[4] for d in combo]
                all_h = [d[5] for d in combo]
                results.append((
                    min(all_x), min(all_y),
                    max(x + w for x, w in zip(all_x, all_w)) - min(all_x),
                    max(y + h for y, h in zip(all_y, all_h)) - min(all_y),
                    "inverted_triangle",
                ))
                break

        return results

    # ════════════════════════════════════════════════════════════
    # Step 6: 编号检测
    # ════════════════════════════════════════════════════════════

    def _detect_numbering(self, steps: List[VisualStep],
                          gray: np.ndarray) -> List[VisualStep]:
        """检测步骤编号

        检测模式：
          - ①②③④⑤
          - (1) (2) (3)
          - 1. 2. 3.
          - 第一步 第二步
          - Step 1, Step 2
        """
        for step in steps:
            x, y, w, h = step.bbox
            if w < 30 or h < 10:
                continue

            roi = gray[y:y + h, x:min(x + 80, x + w)]
            if roi.size == 0:
                continue

            try:
                import pytesseract
                pil_roi = Image.fromarray(roi)
                text = pytesseract.image_to_string(pil_roi, lang="chi_sim+eng")
                text = text.strip()

                numbering_patterns = [
                    (r"^[①②③④⑤⑥⑦⑧⑨⑩]", "circled"),
                    (r"^\(\d+\)", "paren"),
                    (r"^\d+[\.、)]", "dot"),
                    (r"^第[一二三四五六七八九十]+步", "chinese"),
                    (r"^Step\s*\d+", "english"),
                    (r"^\d+\s*[,，]", "comma"),
                ]

                for pattern, ptype in numbering_patterns:
                    match = re.search(pattern, text)
                    if match:
                        step.has_numbering = True
                        step.numbering_text = match.group(0)
                        step.markers.append(StepMarker(
                            marker_type=StepMarkerType.NUMBERING,
                            symbol=match.group(0),
                            confidence=0.8,
                        ))
                        break
            except Exception:
                pass

        return steps

    # ════════════════════════════════════════════════════════════
    # Step 7: 续行检测
    # ════════════════════════════════════════════════════════════

    def _detect_continuations(self, steps: List[VisualStep]) -> List[VisualStep]:
        """检测续行 — 等号对齐的连续推导

        例如：
          f(x) = x² + 1           ← 主步骤
               = (x+1)² - 2x      ← 续行（等号对齐）
               = x² + 2x + 1 - 2x ← 续行（等号对齐）
               = x² + 1           ← 续行（等号对齐）

        判断依据：
          1. 等号位置与上一步对齐
          2. 等号左侧为空白（只有等号，没有左操作数）
          3. 行间距较小
        """
        for i in range(1, len(steps)):
            step = steps[i]
            prev = steps[i - 1]

            if step.is_continuation:
                continue

            # 条件1: 等号对齐
            if (step.equals_alignment_x > 0 and
                    prev.equals_alignment_x > 0 and
                    abs(step.equals_alignment_x - prev.equals_alignment_x) < 20):

                # 条件2: 等号左侧内容较少（续行特征）
                eq_x = step.equals_alignment_x - step.bbox[0]
                if eq_x > step.bbox[2] * 0.2:
                    # 等号偏右 → 可能是续行
                    left_roi = step.image[:, :eq_x] if step.image is not None else None
                    if left_roi is not None and left_roi.size > 0:
                        left_density = np.count_nonzero(left_roi > 128) / left_roi.size
                        if left_density < 0.1:
                            step.is_continuation = True
                            step.continuation_of = prev.step_id or f"step_{prev.step_number:03d}"
                            step.level = StepLevel.CONTINUATION

            # 条件3: 行间距小 + 缩进大 → 续行
            if (not step.is_continuation and
                    step.indent > prev.indent + 20 and
                    step.has_equation_sign):
                step.is_continuation = True
                step.continuation_of = prev.step_id or f"step_{prev.step_number:03d}"
                step.level = StepLevel.CONTINUATION

        return steps

    # ════════════════════════════════════════════════════════════
    # Step 8: 推导角色标注
    # ════════════════════════════════════════════════════════════

    def _assign_derivation_roles(self, steps: List[VisualStep]) -> List[VisualStep]:
        """标注每个步骤的推导角色

        规则：
          - 有 ∵ 标记 → PREMISE（前提）
          - 有 ∴ 标记 → CONCLUSION（结论）
          - 有 →/⇒ 标记 → DERIVATION（推导）
          - 续行 → DERIVATION
          - 第一步 + 无标记 → PREMISE
          - 最后一步 + 无标记 → CONCLUSION
          - 其他 → DERIVATION
        """
        for i, step in enumerate(steps):
            if step.derivation_role != DerivationRole.UNKNOWN:
                continue

            marker_types = {m.marker_type for m in step.markers}

            if StepMarkerType.BECAUSE in marker_types:
                step.derivation_role = DerivationRole.PREMISE
            elif StepMarkerType.THEREFORE in marker_types:
                step.derivation_role = DerivationRole.CONCLUSION
            elif StepMarkerType.ARROW in marker_types:
                step.derivation_role = DerivationRole.DERIVATION
            elif step.is_continuation:
                step.derivation_role = DerivationRole.DERIVATION
            elif i == 0:
                step.derivation_role = DerivationRole.PREMISE
            elif i == len(steps) - 1:
                step.derivation_role = DerivationRole.CONCLUSION
            else:
                step.derivation_role = DerivationRole.DERIVATION

        return steps

    # ════════════════════════════════════════════════════════════
    # Step 9: 推导链构建
    # ════════════════════════════════════════════════════════════

    def _build_derivation_chains(self, steps: List[VisualStep]) -> List[List[str]]:
        """构建推导链 — 步骤间的推导关系

        例如：
          Chain 1: [step_001, step_002, step_003]
            step_001 → PREMISE
            step_002 → DERIVATION (continuation of step_001)
            step_003 → CONCLUSION

          Chain 2: [step_004, step_005]
            step_004 → PREMISE
            step_005 → CONCLUSION
        """
        if not steps:
            return []

        chains = []
        current_chain = [steps[0].step_id or f"step_{steps[0].step_number:03d}"]

        for i in range(1, len(steps)):
            step = steps[i]
            prev = steps[i - 1]

            if step.is_continuation and step.continuation_of == (prev.step_id or f"step_{prev.step_number:03d}"):
                current_chain.append(step.step_id or f"step_{step.step_number:03d}")
            else:
                if current_chain:
                    chains.append(current_chain)
                current_chain = [step.step_id or f"step_{step.step_number:03d}"]

        if current_chain:
            chains.append(current_chain)

        return chains

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
