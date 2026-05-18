"""Diff 渲染器 - 消费 DiffViewModel，返回 HTML String

Renderer 只负责构建 HTML，不调用任何 UI 框架。
"""

from typing import List
from ..tokens import (
    DiffStatus,
    DIFF_STATUS_ICON,
)
from presentation.viewmodels import DiffViewModel


_DIFF_BG_TOKEN = {
    DiffStatus.CORRECT: "success",
    DiffStatus.ERROR: "error",
    DiffStatus.PARTIAL: "warning",
}


class DiffRenderer:
    """差异渲染器 - 返回 HTML"""
    
    @staticmethod
    def render_side_by_side(vm: DiffViewModel) -> str:
        return f"""
        <div class="mt-diff-container">
            <div class="mt-diff-side student">
                <div class="diff-label">❌ {vm.student_label}</div>
                $${vm.student_expr}$$
            </div>
            <div class="mt-diff-side correct">
                <div class="diff-label">✅ {vm.correct_label}</div>
                $${vm.correct_expr}$$
            </div>
        </div>
        """
    
    @staticmethod
    def render_inline_diff(wrong_text: str, correct_text: str, context: str = "") -> str:
        context_html = f'<span style="color:var(--mt-gray-500);font-size:0.85rem;"> ({context})</span>' if context else ""
        return f"""
        <div style="margin:8px 0;">
            <span class="mt-diff-wrong">{wrong_text}</span>
            →
            <span class="mt-diff-highlight">{correct_text}</span>
            {context_html}
        </div>
        """
    
    @staticmethod
    def render_step_diffs(vms: List[DiffViewModel]) -> str:
        parts = []
        for vm in vms:
            icon = DIFF_STATUS_ICON.get(vm.status, "•")
            bg = _DIFF_BG_TOKEN.get(vm.status, "warning")
            
            parts.append(f"""
            <div style="margin:10px 0;padding:10px;border-radius:8px;
                background:var(--mt-{bg}-bg);
                border-left:3px solid var(--mt-{bg});">
                <div style="font-weight:600;margin-bottom:6px;">
                    {icon} {vm.student_label.replace(' - 学生', '')}
                </div>
                <div class="mt-diff-container">
                    <div class="mt-diff-side student">
                        <div class="diff-label">学生</div>
                        $${vm.student_expr}$$
                    </div>
                    <div class="mt-diff-side correct">
                        <div class="diff-label">正确</div>
                        $${vm.correct_expr}$$
                    </div>
                </div>
            </div>
            """)
        
        return "\n".join(parts)
