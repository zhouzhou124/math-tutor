"""vision/confidence_fusion.py — 置信度融合

═══════════════════════════════════════════════════════════════
核心思想
═══════════════════════════════════════════════════════════════

  视觉识别有多个置信度来源：
    - OCR 置信度（pytesseract）
    - Vision API 置信度
    - 区域检测置信度
    - 步骤分割置信度
    - 空间关系置信度

  不能简单平均。因为：
    - OCR 对印刷体高置信，对手写体低置信
    - Vision API 对手写体高置信，对印刷体可能不如 OCR
    - 空间关系提供结构性置信度

  正确做法：加权融合
    - 根据来源可靠性分配权重
    - 根据手写/印刷动态调整
    - 根据一致性奖励（多个来源一致 → 提升置信度）

  融合策略：
    1. 加权平均（基础）
    2. Dempster-Shafer 证据理论（高级）
    3. 一致性奖励（多个来源一致时提升）

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional


class ConfidenceSource(Enum):
    LOCAL_OCR = auto()
    VISION_API = auto()
    REGION_DETECTION = auto()
    STEP_SEGMENTATION = auto()
    SPATIAL_RELATION = auto()
    STRUCTURAL = auto()


@dataclass
class ConfidenceEntry:
    """单个置信度条目"""
    source: ConfidenceSource = ConfidenceSource.LOCAL_OCR
    value: float = 0.0
    weight: float = 1.0
    is_handwritten: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class FusionResult:
    """融合结果"""
    final_confidence: float = 0.0
    source_count: int = 0
    dominant_source: ConfidenceSource = ConfidenceSource.LOCAL_OCR
    consistency_bonus: float = 0.0
    entries: List[ConfidenceEntry] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ConfidenceFusion:
    """置信度融合器

    融合多个来源的置信度，输出最终置信度。

    策略：
      1. 加权平均（基础）
      2. 一致性奖励（多个来源一致 → 提升）
      3. 冲突惩罚（来源差异大 → 降低）
    """

    _BASE_WEIGHTS: Dict[ConfidenceSource, float] = {
        ConfidenceSource.LOCAL_OCR: 0.3,
        ConfidenceSource.VISION_API: 0.4,
        ConfidenceSource.REGION_DETECTION: 0.1,
        ConfidenceSource.STEP_SEGMENTATION: 0.1,
        ConfidenceSource.SPATIAL_RELATION: 0.05,
        ConfidenceSource.STRUCTURAL: 0.05,
    }

    _HANDWRITTEN_WEIGHTS: Dict[ConfidenceSource, float] = {
        ConfidenceSource.LOCAL_OCR: 0.1,
        ConfidenceSource.VISION_API: 0.6,
        ConfidenceSource.REGION_DETECTION: 0.1,
        ConfidenceSource.STEP_SEGMENTATION: 0.1,
        ConfidenceSource.SPATIAL_RELATION: 0.05,
        ConfidenceSource.STRUCTURAL: 0.05,
    }

    def __init__(self):
        self._consistency_threshold = 0.2
        self._consistency_bonus = 0.1
        self._conflict_penalty = 0.15

    def fuse(self, entries: List[ConfidenceEntry]) -> FusionResult:
        """融合多个置信度

        Args:
            entries: 置信度条目列表

        Returns:
            FusionResult
        """
        if not entries:
            return FusionResult(
                final_confidence=0.0,
                warnings=["无置信度来源"],
            )

        if len(entries) == 1:
            e = entries[0]
            return FusionResult(
                final_confidence=e.value,
                source_count=1,
                dominant_source=e.source,
                entries=entries,
            )

        # 判断是否手写（多数投票）
        is_hw = sum(1 for e in entries if e.is_handwritten) > len(entries) / 2

        # 选择权重表
        weights = self._HANDWRITTEN_WEIGHTS if is_hw else self._BASE_WEIGHTS

        # 加权平均
        total_weight = 0.0
        weighted_sum = 0.0
        for entry in entries:
            w = weights.get(entry.source, 0.1) * entry.weight
            weighted_sum += entry.value * w
            total_weight += w

        avg_confidence = weighted_sum / max(total_weight, 0.001)

        # 一致性奖励
        values = [e.value for e in entries]
        value_range = max(values) - min(values)
        consistency_bonus = 0.0

        if value_range < self._consistency_threshold:
            consistency_bonus = self._consistency_bonus * (1 - value_range / self._consistency_threshold)
        elif value_range > 0.5:
            consistency_bonus = -self._conflict_penalty

        final_confidence = max(0.0, min(1.0, avg_confidence + consistency_bonus))

        # 找主导来源
        dominant = max(entries, key=lambda e: weights.get(e.source, 0.1) * e.value)

        # 警告
        warnings = []
        if value_range > 0.5:
            warnings.append(f"来源置信度差异大 (range={value_range:.2f})，结果可能不可靠")
        if final_confidence < 0.3:
            warnings.append("最终置信度过低，建议人工确认")

        return FusionResult(
            final_confidence=final_confidence,
            source_count=len(entries),
            dominant_source=dominant.source,
            consistency_bonus=consistency_bonus,
            entries=entries,
            warnings=warnings,
        )

    def fuse_trace_confidence(self, trace) -> FusionResult:
        """融合整个 VisualReasoningTrace 的置信度

        Args:
            trace: VisualReasoningTrace

        Returns:
            FusionResult
        """
        entries = []

        for formula in trace.formulas:
            source = self._map_formula_source(formula.source)
            entries.append(ConfidenceEntry(
                source=source,
                value=formula.confidence,
                is_handwritten=formula.is_handwritten,
            ))

        for step in trace.steps:
            entries.append(ConfidenceEntry(
                source=ConfidenceSource.STEP_SEGMENTATION,
                value=step.confidence,
            ))

        if trace.layout_graph and trace.layout_graph.nodes:
            node_confs = [n.confidence for n in trace.layout_graph.nodes.values()]
            avg_node_conf = sum(node_confs) / max(len(node_confs), 1)
            entries.append(ConfidenceEntry(
                source=ConfidenceSource.SPATIAL_RELATION,
                value=avg_node_conf,
            ))

        if trace.regions:
            region_confs = [r.confidence for r in trace.regions]
            avg_region_conf = sum(region_confs) / max(len(region_confs), 1)
            entries.append(ConfidenceEntry(
                source=ConfidenceSource.REGION_DETECTION,
                value=avg_region_conf,
            ))

        return self.fuse(entries)

    @staticmethod
    def _map_formula_source(formula_source) -> ConfidenceSource:
        from vision.handwritten_formula import FormulaSource
        mapping = {
            FormulaSource.LOCAL_OCR: ConfidenceSource.LOCAL_OCR,
            FormulaSource.VISION_API: ConfidenceSource.VISION_API,
            FormulaSource.PARSED: ConfidenceSource.STRUCTURAL,
            FormulaSource.HYBRID: ConfidenceSource.STRUCTURAL,
        }
        return mapping.get(formula_source, ConfidenceSource.LOCAL_OCR)


def fuse_confidences(entries: List[ConfidenceEntry]) -> FusionResult:
    """便捷函数：融合置信度"""
    fusion = ConfidenceFusion()
    return fusion.fuse(entries)
