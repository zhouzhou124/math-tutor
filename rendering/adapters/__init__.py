"""Streamlit Adapter - Renderer 与 Streamlit 的桥梁

Renderer 返回 HTML String，Adapter 负责：
1. 注入 CSS (inject_css)
2. 调用 st.markdown(html, unsafe_allow_html=True)

未来迁移 Web 时，只需替换此 Adapter，Renderer 层零改动。
"""

from rendering.themes import inject_css


def render_html(html: str):
    """将 Renderer 输出的 HTML 渲染到 Streamlit"""
    inject_css()
    import streamlit as st
    st.markdown(html, unsafe_allow_html=True)


def render_markdown(md: str):
    """将 Markdown 文本渲染到 Streamlit"""
    import streamlit as st
    st.markdown(md)


def render_component(render_func, *args, **kwargs):
    """调用 Renderer 方法并渲染结果到 Streamlit
    
    用法：
        render_component(FormulaBlock.render, vm)
        render_component(ScorePanel.render, score_vm)
    """
    html = render_func(*args, **kwargs)
    render_html(html)


def render_components(*render_calls):
    """批量渲染多个 Renderer 调用结果
    
    用法：
        render_components(
            (FormulaBlock.render, [vm1], {}),
            (ScorePanel.render, [score_vm], {}),
        )
    """
    parts = []
    for func, args, kwargs in render_calls:
        html = func(*args, **kwargs)
        parts.append(html)
    
    render_html("\n".join(parts))
