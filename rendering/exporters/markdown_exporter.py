"""Markdown Exporter — Document → Markdown 文本

═══════════════════════════════════════════════════════════════
核心 API
═══════════════════════════════════════════════════════════════

  MarkdownExporter.export(document) → str

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from typing import Optional

from rendering.document_ast import Document, DocumentNode
from rendering.layout_engine import LayoutEngine


class MarkdownExporter:
    """Document → Markdown 文本导出器."""

    def __init__(self):
        self._engine = LayoutEngine()

    def export(self, document: Document) -> str:
        """导出 Document 为 Markdown 文本."""
        result = self._engine.layout(document, "markdown")
        return result.content

    def export_nodes(self, nodes: list[DocumentNode], title: str = "") -> str:
        """导出 DocumentNode 列表为 Markdown 文本."""
        doc = Document(title=title, nodes=tuple(nodes))
        return self.export(doc)

    def export_to_file(self, document: Document, path: str) -> None:
        """导出 Document 到 Markdown 文件."""
        content = self.export(document)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
