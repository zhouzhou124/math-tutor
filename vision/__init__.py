"""vision — 视觉推理模块

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  图像 → Step Detection → Formula Detection → Spatial Graph → MathIR

  不是：图像 → 字符串
  而是：图像 → 视觉理解 → 数学推理结构

═══════════════════════════════════════════════════════════════
模块
═══════════════════════════════════════════════════════════════

  preprocess.py          — 图片预处理（gray→CLAHE→阈值→close→sharpen→deskew）
  region_detector.py     — 数学区域检测（排除空白/横线/阴影/页边）
  handwritten_formula.py — 手写公式检测与识别（OCR + Vision API）
  step_segmenter.py      — 解题步骤分割（行间距→步骤边界）
  layout_graph.py        — 空间布局图（节点=区域，边=空间关系）
  visual_trace_builder.py— 视觉推理轨迹构建器
  confidence_fusion.py   — 置信度融合（加权+一致性奖励）
  vision_parser.py       — 数学视觉解析器（新主入口，输出 VisualReasoningStep）
  formula_ast.py         — Formula AST（视觉层公式结构，SpatialGraph → FormulaAST）
  operation_recovery.py  — 操作类型恢复（视觉步骤 → Op，三级策略）

═══════════════════════════════════════════════════════════════
"""

try:
    from vision.preprocess import MathImagePreprocessor, PreprocessResult
except ImportError:
    MathImagePreprocessor = None
    PreprocessResult = None
try:
    from vision.region_detector import (
        MathRegionDetector, DetectedRegion, RegionType, RegionDetectionResult,
        FormulaRegionDetector, FormulaRegion, FormulaRegionType,
    )
    from vision.handwritten_formula import (
        HandwrittenFormulaDetector, FormulaHypothesis, FormulaSource, FormulaDetectionResult,
    )
    from vision.step_segmenter import (
        StepSegmenter, VisualStep, StepLevel, StepSegmentationResult,
        StepMarkerType, StepMarker, DerivationRole,
    )
    from vision.layout_graph import (
        LayoutGraphBuilder, LayoutGraph, LayoutNode, LayoutEdge, LayoutNodeType,
        SpatialRelation, SpatialGraphBuilder, SpatialGraph, SpatialNode, SpatialEdge,
        MathSpatialRelation, SymbolRole,
    )
    from vision.visual_trace_builder import (
        VisualTraceBuilder, VisualReasoningTrace, VisualTransition, TraceStatus,
    )
    from vision.confidence_fusion import (
        ConfidenceFusion, ConfidenceEntry, ConfidenceSource, FusionResult, fuse_confidences,
    )
    from vision.vision_parser import (
        VisionParser, VisualReasoningStep, VisionParseResult, ParseStatus, EngineType,
    )
    from vision.formula_ast import (
        FormulaAST, FormulaNodeType, FormulaExprNode, NumberNode, VariableNode,
        OperatorNode, FractionNode, SuperscriptNode, SubscriptNode, IntegralNode,
        SumNode, ProductNode, LimitNode, MatrixNode, FormulaFunctionNode,
        RadicalNode, BracketNode, SequenceNode, DerivativeNode, SpatialGraphToFormulaAST,
    )
    from vision.operation_recovery import (
        OperationRecovery, OperationRecoveryResult, RecoveredOperation, RecoveryLevel,
        StructuralAnalyzer, StructuralDiff, StructuralFeature,
    )
except ImportError:
    pass

__all__ = [
    "MathImagePreprocessor",
    "PreprocessResult",
    "MathRegionDetector",
    "DetectedRegion",
    "RegionType",
    "RegionDetectionResult",
    "FormulaRegionDetector",
    "FormulaRegion",
    "FormulaRegionType",
    "HandwrittenFormulaDetector",
    "FormulaHypothesis",
    "FormulaSource",
    "FormulaDetectionResult",
    "StepSegmenter",
    "VisualStep",
    "StepLevel",
    "StepSegmentationResult",
    "StepMarkerType",
    "StepMarker",
    "DerivationRole",
    "LayoutGraphBuilder",
    "LayoutGraph",
    "LayoutNode",
    "LayoutEdge",
    "LayoutNodeType",
    "SpatialRelation",
    "SpatialGraphBuilder",
    "SpatialGraph",
    "SpatialNode",
    "SpatialEdge",
    "MathSpatialRelation",
    "SymbolRole",
    "VisualTraceBuilder",
    "VisualReasoningTrace",
    "VisualTransition",
    "TraceStatus",
    "ConfidenceFusion",
    "ConfidenceEntry",
    "ConfidenceSource",
    "FusionResult",
    "fuse_confidences",
    "VisionParser",
    "VisualReasoningStep",
    "VisionParseResult",
    "ParseStatus",
    "EngineType",
    "FormulaAST",
    "FormulaNodeType",
    "FormulaExprNode",
    "NumberNode",
    "VariableNode",
    "OperatorNode",
    "FractionNode",
    "SuperscriptNode",
    "SubscriptNode",
    "IntegralNode",
    "SumNode",
    "ProductNode",
    "LimitNode",
    "MatrixNode",
    "FormulaFunctionNode",
    "RadicalNode",
    "BracketNode",
    "SequenceNode",
    "DerivativeNode",
    "SpatialGraphToFormulaAST",
    "OperationRecovery",
    "OperationRecoveryResult",
    "RecoveredOperation",
    "RecoveryLevel",
    "StructuralAnalyzer",
    "StructuralDiff",
    "StructuralFeature",
]
