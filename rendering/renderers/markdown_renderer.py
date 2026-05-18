"""Markdown 渲染器 - 只负责文本布局，返回 Markdown String

Markdown 只做：
- 标题层级
- 表格布局
- 列表排版
- 时间线排版

语义（状态、颜色、图标）由 ViewModel 通过 Mapper 提供。
"""


class MarkdownRenderer:
    """Markdown 渲染器 - 纯文本布局，返回 Markdown String"""
    
    @staticmethod
    def render_section(title: str, content: str, level: int = 3) -> str:
        headers = {1: "#", 2: "##", 3: "###", 4: "####"}
        h = headers.get(level, "###")
        return f"{h} {title}\n\n{content}"
    
    @staticmethod
    def render_key_value(data: dict, title: str = "") -> str:
        parts = []
        if title:
            parts.append(f"**{title}**")
        
        rows = []
        for key, value in data.items():
            rows.append(f"| {key} | {value} |")
        
        table = "| 属性 | 值 |\n|------|------|\n" + "\n".join(rows)
        parts.append(table)
        return "\n\n".join(parts)
    
    @staticmethod
    def render_timeline(items: list, title: str = "") -> str:
        parts = []
        if title:
            parts.append(f"### {title}")
        
        for item in items:
            time_str = item.get("time", "")
            label = item.get("label", "")
            detail = item.get("detail", "")
            icon = item.get("icon", "•")
            
            parts.append(f"{icon} **{time_str}** - {label}")
            if detail:
                parts.append(f"   {detail}")
        
        return "\n\n".join(parts)
