"""HTML Exporter — Document → HTML 页面"""

from __future__ import annotations

from rendering.document_ast import Document, DocumentNode
from rendering.layout_engine import LayoutEngine


_HTML_WRAPPER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body, {{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}]}});"></script>
<style>
body {{ font-family: "Noto Serif SC", serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; }}
.alert {{ padding: 12px 16px; border-radius: 8px; margin: 8px 0; }}
.alert-info {{ background: #e0f2fe; border-left: 4px solid #0ea5e9; }}
.alert-warning {{ background: #fef3c7; border-left: 4px solid #f59e0b; }}
.alert-error {{ background: #fee2e2; border-left: 4px solid #ef4444; }}
.alert-critical {{ background: #fecaca; border-left: 4px solid #b91c1c; }}
.alert-success {{ background: #d1fae5; border-left: 4px solid #10b981; }}
.obligation {{ padding: 12px 16px; border-radius: 8px; margin: 8px 0; background: #f3f4f6; }}
.obligation-header {{ font-weight: bold; margin-bottom: 8px; }}
.obligation-summary {{ font-style: italic; color: #6b7280; margin-top: 8px; }}
</style>
</head>
<body>
{content}
</body>
</html>"""


class HTMLExporter:
    """Document → HTML 页面导出器."""

    def __init__(self, standalone: bool = True):
        self._engine = LayoutEngine()
        self._standalone = standalone

    def export(self, document: Document) -> str:
        """导出 Document 为 HTML."""
        result = self._engine.layout(document, "html")
        if self._standalone:
            return _HTML_WRAPPER.format(title=document.title, content=result.content)
        return result.content

    def export_nodes(self, nodes: list[DocumentNode], title: str = "") -> str:
        """导出 DocumentNode 列表为 HTML."""
        doc = Document(title=title, nodes=tuple(nodes))
        return self.export(doc)

    def export_to_file(self, document: Document, path: str) -> None:
        """导出 Document 到 HTML 文件."""
        content = self.export(document)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
