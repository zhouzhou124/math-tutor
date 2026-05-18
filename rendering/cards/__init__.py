"""卡片组件 - 消费 ViewModel，返回 HTML String

Renderer 只负责构建 HTML，不调用任何 UI 框架。
"""

from typing import List
from ..components import KnowledgeTag
from ..tokens import (
    StepStatus,
    FormulaStatus,
    DiffStatus,
    ErrorCategory,
    TagType,
    STATUS_CSS_CLASS,
    STEP_STATUS_ICON,
    ERROR_CATEGORY_ICON,
    DIFF_STATUS_ICON,
)
from presentation.viewmodels import (
    StepCardViewModel,
    ErrorViewModel,
    DiagnosisViewModel,
    ScoreViewModel,
)


class ReasoningStepCard:
    """推理步骤卡片 - 返回 HTML"""
    
    @staticmethod
    def render(vm: StepCardViewModel) -> str:
        css_class = STATUS_CSS_CLASS.get(vm.status, "")
        status_class = f" {css_class}" if css_class else ""
        
        title_html = f'<span class="step-title">{vm.display_title or vm.title}</span>'
        
        expression_html = ""
        if vm.expression:
            expression_html = f'<div class="step-expression">$${vm.expression}$$</div>'
        
        reasoning_html = ""
        if vm.reasoning:
            reasoning_html = f'<div class="step-reasoning">{vm.reasoning}</div>'
        
        tags_html = ""
        if vm.knowledge_tags:
            tag_spans = " ".join(
                f'<span class="mt-tag {TagType.KNOWLEDGE.value}">{kp}</span>' for kp in vm.knowledge_tags
            )
            tags_html = f'<div class="step-tags">{tag_spans}</div>'
        
        if vm.theorem_tag:
            tags_html += f' <span class="mt-tag {TagType.THEOREM.value}">{vm.theorem_tag}</span>'
        
        return f"""
        <div class="mt-step-card{status_class}">
            <div class="step-header">
                <div style="display:flex;align-items:center;">
                    <span class="step-number">{vm.step_number}</span>
                    {title_html}
                </div>
            </div>
            <div class="step-body">
                {expression_html}
                {reasoning_html}
                {tags_html}
            </div>
        </div>
        """


class ErrorHighlight:
    """错误定位 - 返回 HTML"""
    
    @staticmethod
    def render(vm: ErrorViewModel) -> str:
        cause_html = ""
        if vm.cause:
            cause_html = f"""
            <div class="error-cause">
                <strong>原因：</strong>{vm.cause}
            </div>
            """
        
        fix_html = ""
        if vm.fix:
            fix_html = f"""
            <div class="error-fix">
                <strong>修正：</strong>{vm.fix}
            </div>
            """
        
        diff_html = ""
        if vm.has_diff and vm.student_expr and vm.correct_expr:
            diff_html = f"""
            <div class="mt-diff-container">
                <div class="mt-diff-side student">
                    <div class="diff-label">❌ 学生答案</div>
                    $${vm.student_expr}$$
                </div>
                <div class="mt-diff-side correct">
                    <div class="diff-label">✅ 正确答案</div>
                    $${vm.correct_expr}$$
                </div>
            </div>
            """
        
        kp_html = ""
        if vm.knowledge_point:
            kp_html = f'<span class="mt-tag {TagType.KNOWLEDGE.value}">{vm.knowledge_point}</span>'
        
        return f"""
        <div class="mt-error-highlight">
            <div class="error-header">
                <span class="error-icon">{vm.error_type_icon}</span>
                <span class="error-type">{vm.error_type_display}</span>
                {kp_html}
            </div>
            {diff_html}
            {cause_html}
            {fix_html}
        </div>
        """


class DiagnosisPanel:
    """诊断面板 - 返回 HTML"""
    
    @staticmethod
    def render(vm: DiagnosisViewModel) -> str:
        kp_tags = " ".join(
            f'<span class="mt-tag {TagType.KNOWLEDGE.value}">{kp}</span>' for kp in vm.knowledge_tags
        )
        
        recs_html = ""
        for rec in vm.recommendations:
            recs_html += f'<div class="recommendation">💡 {rec}</div>'
        
        confidence_html = ""
        if vm.confidence > 0:
            confidence_html = f"""
            <div class="panel-section">
                <div class="panel-section-title">诊断置信度</div>
                <div style="background:var(--mt-gray-200);border-radius:9999px;height:8px;overflow:hidden;">
                    <div style="background:var(--mt-primary);height:100%;width:{vm.confidence_pct};border-radius:9999px;"></div>
                </div>
                <div style="font-size:0.8rem;color:var(--mt-gray-500);margin-top:4px;">{vm.confidence_pct}</div>
            </div>
            """
        
        return f"""
        <div class="mt-diagnosis-panel">
            <div class="panel-header">🔍 错误诊断 - {vm.error_type_display}</div>
            <div class="panel-body">
                <div class="panel-section">
                    <div class="panel-section-title">根本原因</div>
                    <div>{vm.root_cause}</div>
                </div>
                
                <div class="panel-section">
                    <div class="panel-section-title">相关知识点</div>
                    <div>{kp_tags}</div>
                </div>
                
                {confidence_html}
                
                <div class="panel-section">
                    <div class="panel-section-title">改进建议</div>
                    {recs_html}
                </div>
            </div>
        </div>
        """


class ScorePanel:
    """评分面板 - 返回 HTML"""
    
    @staticmethod
    def render(vm: ScoreViewModel) -> str:
        deductions_html = ""
        if vm.deductions:
            rows = ""
            for d in vm.deductions:
                rows += f"""
                <tr>
                    <td style="padding:4px 8px;border-bottom:1px solid var(--mt-gray-200);">{d.get('reason', '')}</td>
                    <td style="padding:4px 8px;border-bottom:1px solid var(--mt-gray-200);text-align:center;color:var(--mt-error);">-{d.get('points', 0)}</td>
                </tr>
                """
            deductions_html = f"""
            <div style="margin-top:12px;">
                <div style="font-size:0.85rem;font-weight:600;color:var(--mt-gray-500);margin-bottom:6px;">扣分明细</div>
                <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                    <thead>
                        <tr style="border-bottom:2px solid var(--mt-gray-200);">
                            <th style="padding:4px 8px;text-align:left;">原因</th>
                            <th style="padding:4px 8px;text-align:center;">扣分</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
            """
        
        return f"""
        <div>
            <div class="mt-score-panel">
                <div class="mt-score-card total">
                    <div class="score-value">{vm.total_display}</div>
                    <div class="score-label">总分</div>
                </div>
                <div class="mt-score-card process">
                    <div class="score-value">{vm.process_display}</div>
                    <div class="score-label">过程分</div>
                </div>
                <div class="mt-score-card deduction">
                    <div class="score-value">{vm.deduction_display}</div>
                    <div class="score-label">扣分</div>
                </div>
            </div>
            {deductions_html}
        </div>
        """
