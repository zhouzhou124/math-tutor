"""LaTeX 渲染器 - 数学公式渲染，返回 HTML String

Renderer 只负责构建 HTML，不调用任何 UI 框架。
"""

from typing import List, Optional


class LatexRenderer:
    """LaTeX 渲染器 - 返回 HTML"""
    
    @staticmethod
    def render_block(latex: str, label: str = "") -> str:
        label_html = f'<div class="mt-formula-label">{label}</div>' if label else ""
        return f"""
        {label_html}
        <div class="mt-formula-block">
            $${latex}$$
        </div>
        """
    
    @staticmethod
    def render_inline(latex: str) -> str:
        return f"${latex}$"
    
    @staticmethod
    def render_comparison(left: str, right: str, left_label: str = "左", right_label: str = "右") -> str:
        return f"""
        <div class="mt-diff-container">
            <div class="mt-diff-side student">
                <div class="diff-label">{left_label}</div>
                $${left}$$
            </div>
            <div class="mt-diff-side correct">
                <div class="diff-label">{right_label}</div>
                $${right}$$
            </div>
        </div>
        """
    
    @staticmethod
    def render_aligned(equations: List[str], label: str = "") -> str:
        label_html = f'<div class="mt-formula-label">{label}</div>' if label else ""
        aligned = " \\\\ ".join(equations)
        return f"""
        {label_html}
        <div class="mt-formula-block">
            $$\\begin{{aligned}} {aligned} \\end{{aligned}}$$
        </div>
        """
    
    @staticmethod
    def render_cases(cases: List[dict], label: str = "") -> str:
        label_html = f'<div class="mt-formula-label">{label}</div>' if label else ""
        
        case_strs = []
        for c in cases:
            expr = c.get("expression", "")
            condition = c.get("condition", "")
            if condition:
                case_strs.append(f"{expr}, & \\text{{if }} {condition}")
            else:
                case_strs.append(expr)
        
        cases_body = " \\\\ ".join(case_strs)
        return f"""
        {label_html}
        <div class="mt-formula-block">
            $$\\begin{{cases}} {cases_body} \\end{{cases}}$$
        </div>
        """
