"""
Rendering Pipeline — 渲染流水线

═══════════════════════════════════════════════════════════════
架构
═══════════════════════════════════════════════════════════════

  输入 (ReasoningTrace / WorldState / dict)
      ↓
  Semantic Renderer  →  Document AST
      ↓
  Layout Engine      →  Markdown / LaTeX / HTML
      ↓
  RenderOutput

  一键入口:
    pipeline = RenderingPipeline()
    output = pipeline.render(trace, format="markdown")
    print(output.content)

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from rendering.document_ast import Document
from rendering.semantic_renderer import SemanticRenderer, RenderConfig
from rendering.layout_engine import LayoutEngine, LayoutResult


class RenderFormat(str, Enum):
    MARKDOWN = "markdown"
    LATEX = "latex"
    HTML = "html"


@dataclass(frozen=True)
class RenderOutput:
    content: str = ""
    format: str = "markdown"
    document: Document = field(default_factory=Document.empty)
    metadata: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.content.strip()

    @property
    def markdown(self) -> str:
        if self.format == "markdown":
            return self.content
        return ""

    @property
    def latex(self) -> str:
        if self.format == "latex":
            return self.content
        return ""

    @property
    def html(self) -> str:
        if self.format == "html":
            return self.content
        return ""

    def __str__(self) -> str:
        return self.content


class RenderingPipeline:
    """
    渲染流水线 — 顶层编排。

    用法:
      pipeline = RenderingPipeline()

      # 从 ReasoningTrace
      output = pipeline.render(trace, format="markdown")

      # 从 WorldState
      output = pipeline.render_world_state(ws, format="html")

      # 从 dict
      output = pipeline.render_dict(data, format="latex")

      # 多格式
      outputs = pipeline.render_all(trace)
    """

    def __init__(
        self,
        renderer: SemanticRenderer = None,
        layout_engine: LayoutEngine = None,
        config: RenderConfig = None,
    ):
        self.config = config or RenderConfig()
        self.renderer = renderer or SemanticRenderer(self.config)
        self.layout_engine = layout_engine or LayoutEngine()

    def render(
        self,
        source: Any,
        format: str = "markdown",
        config: RenderConfig = None,
    ) -> RenderOutput:
        cfg = config or self.config
        doc = self.renderer.render_trace(source, cfg)
        result = self.layout_engine.layout(doc, format)
        return RenderOutput(
            content=result.content,
            format=format,
            document=doc,
            metadata={"source_type": type(source).__name__},
        )

    def render_world_state(
        self,
        ws: Any,
        format: str = "markdown",
        config: RenderConfig = None,
    ) -> RenderOutput:
        cfg = config or self.config
        doc = self.renderer.render_world_state(ws, cfg)
        result = self.layout_engine.layout(doc, format)
        return RenderOutput(
            content=result.content,
            format=format,
            document=doc,
            metadata={"source_type": "WorldState"},
        )

    def render_dict(
        self,
        data: dict,
        format: str = "markdown",
        config: RenderConfig = None,
    ) -> RenderOutput:
        cfg = config or self.config
        doc = self.renderer.render_dict(data, cfg)
        result = self.layout_engine.layout(doc, format)
        return RenderOutput(
            content=result.content,
            format=format,
            document=doc,
            metadata={"source_type": "dict"},
        )

    def render_all(
        self,
        source: Any,
        config: RenderConfig = None,
    ) -> dict[str, RenderOutput]:
        cfg = config or self.config
        doc = self.renderer.render_trace(source, cfg)
        results = self.layout_engine.layout_all(doc)
        return {
            fmt: RenderOutput(
                content=r.content,
                format=fmt,
                document=doc,
                metadata={"source_type": type(source).__name__},
            )
            for fmt, r in results.items()
        }

    def render_to_markdown(self, source: Any, config: RenderConfig = None) -> str:
        return self.render(source, "markdown", config).content

    def render_to_latex(self, source: Any, config: RenderConfig = None) -> str:
        return self.render(source, "latex", config).content

    def render_to_html(self, source: Any, config: RenderConfig = None) -> str:
        return self.render(source, "html", config).content
