"""基础组件 - 消费 ViewModel，返回 HTML String

Renderer 只负责构建 HTML，不调用任何 UI 框架。
Streamlit Adapter 负责 st.markdown() 调用。
"""

from ..tokens import (
    FormulaStatus,
    TagType,
    STATUS_CSS_CLASS,
)
from presentation.viewmodels import FormulaViewModel


class FormulaBlock:
    """公式显示组件 - 返回 HTML"""
    
    @staticmethod
    def render(vm: FormulaViewModel) -> str:
        css_class = STATUS_CSS_CLASS.get(vm.status, "")
        status_class = f" {css_class}" if css_class else ""
        label_html = f'<div class="mt-formula-label">{vm.display_label or vm.label}</div>' if (vm.display_label or vm.label) else ""
        
        return f"""
        <div class="mt-formula-block{status_class}">
            {label_html}
            $${vm.latex}$$
        </div>
        """
    
    @staticmethod
    def render_simple(latex: str, label: str = "", status: FormulaStatus = FormulaStatus.NEUTRAL) -> str:
        vm = FormulaViewModel(latex=latex, label=label, status=status, display_label=label)
        return FormulaBlock.render(vm)
    
    @staticmethod
    def render_inline(latex: str, status: FormulaStatus = FormulaStatus.NEUTRAL) -> str:
        css_class = STATUS_CSS_CLASS.get(status, "")
        status_class = f" {css_class}" if css_class else ""
        return f'<span class="mt-formula-block inline{status_class}">${latex}$</span>'


class KnowledgeTag:
    """知识点标签组件 - 返回 HTML"""
    
    @staticmethod
    def render(text: str, tag_type: TagType = TagType.KNOWLEDGE) -> str:
        return f'<span class="mt-tag {tag_type.value}">{text}</span>'
    
    @staticmethod
    def render_tags(tags: list, tag_type: TagType = TagType.KNOWLEDGE) -> str:
        tags_html = " ".join(f'<span class="mt-tag {tag_type.value}">{tag}</span>' for tag in tags)
        return f'<div>{tags_html}</div>'
