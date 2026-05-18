"""Streamlit专用LaTeX渲染器 - 直接调用st.latex()

解决HTML + LaTeX混合渲染链断裂问题。
"""

import streamlit as st
import re


class STLatexRenderer:
    """Streamlit专用LaTeX渲染器 - 直接调用st.latex()"""
    
    BLOCK_ENVIRONMENTS = {
        'cases', 'align', 'align*', 'gather', 'gather*',
        'equation', 'equation*', 'matrix', 'pmatrix',
        'bmatrix', 'vmatrix', 'Vmatrix', 'array'
    }
    
    @staticmethod
    def detect_mode(latex: str) -> str:
        """检测LaTeX环境类型"""
        for env in STLatexRenderer.BLOCK_ENVIRONMENTS:
            if f'\\begin{{{env}}}' in latex:
                return 'block'
        if latex.count('\n') > 2 or len(latex) > 100:
            return 'block'
        return 'inline'
    
    @staticmethod
    def render(latex: str, mode: str = None):
        """渲染LaTeX，自动判断模式"""
        if not latex:
            return
        
        # 清理输入：去除引号、多余空白
        latex = latex.strip().strip('"').strip("'").strip()
        
        # 检测模式并渲染
        detected_mode = mode or STLatexRenderer.detect_mode(latex)
        
        if detected_mode == 'block':
            st.latex(latex)
        else:
            st.markdown(f"${latex}$")
    
    @staticmethod
    def render_card(title: str, latex: str):
        """渲染带标题的公式卡片"""
        st.markdown(f"**{title}**")
        STLatexRenderer.render(latex)
    
    @staticmethod
    def render_comparison(left: str, right: str, left_label: str = "学生", right_label: str = "标准答案"):
        """渲染对比公式"""
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**{left_label}**")
            STLatexRenderer.render(left)
        with col2:
            st.markdown(f"**{right_label}**")
            STLatexRenderer.render(right)