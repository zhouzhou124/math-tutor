"""CSS 主题系统 - 数学 IDE 设计系统"""

MATH_TUTOR_CSS = """
<style>
/* ══════════════════════════════════════════════════════════
   Math Tutor Design System - CSS 变量与基础样式
   ══════════════════════════════════════════════════════════ */
:root {
    /* 主色调 */
    --mt-primary: #667eea;
    --mt-primary-light: #8fa4f0;
    --mt-primary-dark: #4a5fc7;
    
    /* 语义色 */
    --mt-success: #10b981;
    --mt-success-bg: #ecfdf5;
    --mt-warning: #f59e0b;
    --mt-warning-bg: #fffbeb;
    --mt-error: #ef4444;
    --mt-error-bg: #fef2f2;
    --mt-info: #3b82f6;
    --mt-info-bg: #eff6ff;
    
    /* 中性色 */
    --mt-gray-50: #f9fafb;
    --mt-gray-100: #f3f4f6;
    --mt-gray-200: #e5e7eb;
    --mt-gray-300: #d1d5db;
    --mt-gray-500: #6b7280;
    --mt-gray-700: #374151;
    --mt-gray-900: #111827;
    
    /* 圆角 */
    --mt-radius-sm: 6px;
    --mt-radius-md: 10px;
    --mt-radius-lg: 14px;
    
    /* 阴影 */
    --mt-shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --mt-shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
    --mt-shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1);
    
    /* 字体 */
    --mt-font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    --mt-font-math: 'STIX Two Math', 'Latin Modern Math', 'Cambria Math', serif;
}

/* ══════════════════════════════════════════════════════════
   FormulaBlock - 公式显示组件
   ══════════════════════════════════════════════════════════ */
.mt-formula-block {
    background: var(--mt-gray-50);
    border: 1px solid var(--mt-gray-200);
    border-radius: var(--mt-radius-md);
    padding: 16px 20px;
    margin: 12px 0;
    font-family: var(--mt-font-math);
    font-size: 1.1rem;
    text-align: center;
    overflow-x: auto;
}

.mt-formula-block.inline {
    display: inline;
    padding: 4px 8px;
    margin: 0 2px;
    font-size: 1rem;
}

.mt-formula-block.correct {
    border-left: 4px solid var(--mt-success);
    background: var(--mt-success-bg);
}

.mt-formula-block.wrong {
    border-left: 4px solid var(--mt-error);
    background: var(--mt-error-bg);
}

.mt-formula-block.partial {
    border-left: 4px solid var(--mt-warning);
    background: var(--mt-warning-bg);
}

.mt-formula-label {
    font-size: 0.8rem;
    color: var(--mt-gray-500);
    margin-bottom: 6px;
    font-family: sans-serif;
}

/* ══════════════════════════════════════════════════════════
   KnowledgeTag - 知识点标签
   ══════════════════════════════════════════════════════════ */
.mt-tag {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 2px 4px;
    line-height: 1.4;
}

.mt-tag.knowledge {
    background: #e0e7ff;
    color: #3730a3;
}

.mt-tag.error-type {
    background: #fce7f3;
    color: #9d174d;
}

.mt-tag.difficulty-easy {
    background: #d1fae5;
    color: #065f46;
}

.mt-tag.difficulty-medium {
    background: #fef3c7;
    color: #92400e;
}

.mt-tag.difficulty-hard {
    background: #fee2e2;
    color: #991b1b;
}

.mt-tag.theorem {
    background: #ede9fe;
    color: #5b21b6;
}

/* ══════════════════════════════════════════════════════════
   StepCard - 推理步骤卡片
   ══════════════════════════════════════════════════════════ */
.mt-step-card {
    border: 1px solid var(--mt-gray-200);
    border-radius: var(--mt-radius-md);
    padding: 16px;
    margin: 10px 0;
    background: white;
    box-shadow: var(--mt-shadow-sm);
    position: relative;
}

.mt-step-card .step-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}

.mt-step-card .step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--mt-primary);
    color: white;
    font-size: 0.85rem;
    font-weight: 600;
    margin-right: 10px;
}

.mt-step-card .step-title {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--mt-gray-900);
}

.mt-step-card .step-body {
    padding-left: 38px;
}

.mt-step-card.correct {
    border-left: 4px solid var(--mt-success);
}

.mt-step-card.correct .step-number {
    background: var(--mt-success);
}

.mt-step-card.error {
    border-left: 4px solid var(--mt-error);
}

.mt-step-card.error .step-number {
    background: var(--mt-error);
}

.mt-step-card.warning {
    border-left: 4px solid var(--mt-warning);
}

.mt-step-card.warning .step-number {
    background: var(--mt-warning);
}

.mt-step-card .step-expression {
    background: var(--mt-gray-50);
    border-radius: var(--mt-radius-sm);
    padding: 10px 14px;
    margin: 8px 0;
    font-family: var(--mt-font-math);
    font-size: 1.05rem;
}

.mt-step-card .step-reasoning {
    color: var(--mt-gray-700);
    font-size: 0.9rem;
    line-height: 1.5;
    margin-top: 6px;
}

.mt-step-card .step-tags {
    margin-top: 8px;
}

/* ══════════════════════════════════════════════════════════
   ErrorHighlight - 错误定位
   ══════════════════════════════════════════════════════════ */
.mt-error-highlight {
    border: 1px solid var(--mt-error);
    border-radius: var(--mt-radius-md);
    padding: 16px;
    margin: 10px 0;
    background: var(--mt-error-bg);
}

.mt-error-highlight .error-header {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
}

.mt-error-highlight .error-icon {
    font-size: 1.3rem;
    margin-right: 8px;
}

.mt-error-highlight .error-type {
    font-weight: 700;
    color: var(--mt-error);
    font-size: 1rem;
}

.mt-error-highlight .error-cause {
    background: white;
    border-radius: var(--mt-radius-sm);
    padding: 10px 14px;
    margin: 8px 0;
    border-left: 3px solid var(--mt-error);
}

.mt-error-highlight .error-fix {
    background: var(--mt-success-bg);
    border-radius: var(--mt-radius-sm);
    padding: 10px 14px;
    margin: 8px 0;
    border-left: 3px solid var(--mt-success);
}

/* ══════════════════════════════════════════════════════════
   DiagnosisPanel - 诊断面板
   ══════════════════════════════════════════════════════════ */
.mt-diagnosis-panel {
    border: 1px solid var(--mt-gray-200);
    border-radius: var(--mt-radius-lg);
    overflow: hidden;
    margin: 12px 0;
    box-shadow: var(--mt-shadow-md);
}

.mt-diagnosis-panel .panel-header {
    background: linear-gradient(135deg, var(--mt-primary) 0%, var(--mt-primary-dark) 100%);
    color: white;
    padding: 14px 18px;
    font-weight: 600;
    font-size: 1rem;
}

.mt-diagnosis-panel .panel-body {
    padding: 16px 18px;
    background: white;
}

.mt-diagnosis-panel .panel-section {
    margin-bottom: 14px;
}

.mt-diagnosis-panel .panel-section-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--mt-gray-500);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}

.mt-diagnosis-panel .recommendation {
    background: var(--mt-success-bg);
    border-radius: var(--mt-radius-sm);
    padding: 8px 12px;
    margin: 4px 0;
    border-left: 3px solid var(--mt-success);
    font-size: 0.9rem;
}

/* ══════════════════════════════════════════════════════════
   ScorePanel - 评分面板
   ══════════════════════════════════════════════════════════ */
.mt-score-panel {
    display: flex;
    gap: 16px;
    margin: 12px 0;
}

.mt-score-card {
    flex: 1;
    border-radius: var(--mt-radius-md);
    padding: 16px;
    text-align: center;
    box-shadow: var(--mt-shadow-sm);
}

.mt-score-card .score-value {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
}

.mt-score-card .score-label {
    font-size: 0.8rem;
    color: var(--mt-gray-500);
    margin-top: 4px;
}

.mt-score-card.total {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.mt-score-card.process {
    background: var(--mt-info-bg);
    color: var(--mt-info);
}

.mt-score-card.deduction {
    background: var(--mt-error-bg);
    color: var(--mt-error);
}

/* ══════════════════════════════════════════════════════════
   Diff Rendering - 差异高亮
   ══════════════════════════════════════════════════════════ */
.mt-diff-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin: 12px 0;
}

.mt-diff-side {
    border-radius: var(--mt-radius-md);
    padding: 14px;
    font-family: var(--mt-font-math);
    font-size: 1rem;
}

.mt-diff-side.student {
    background: var(--mt-error-bg);
    border: 1px solid #fca5a5;
}

.mt-diff-side.correct {
    background: var(--mt-success-bg);
    border: 1px solid #6ee7b7;
}

.mt-diff-side .diff-label {
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 8px;
    font-family: sans-serif;
}

.mt-diff-side.student .diff-label {
    color: var(--mt-error);
}

.mt-diff-side.correct .diff-label {
    color: var(--mt-success);
}

.mt-diff-highlight {
    background: #fde68a;
    padding: 1px 3px;
    border-radius: 3px;
}

.mt-diff-wrong {
    background: #fca5a5;
    text-decoration: line-through;
    padding: 1px 3px;
    border-radius: 3px;
}

/* ══════════════════════════════════════════════════════════
   ReasoningChain - 推理链可视化
   ══════════════════════════════════════════════════════════ */
.mt-chain-container {
    margin: 12px 0;
}

.mt-chain-connector {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px 0;
    color: var(--mt-gray-300);
    font-size: 1.2rem;
}

.mt-chain-connector.error {
    color: var(--mt-error);
}

/* ══════════════════════════════════════════════════════════
   DAG 可视化
   ══════════════════════════════════════════════════════════ */
.mt-dag-container {
    background: var(--mt-gray-50);
    border: 1px solid var(--mt-gray-200);
    border-radius: var(--mt-radius-lg);
    padding: 20px;
    margin: 12px 0;
    overflow-x: auto;
}

.mt-dag-node {
    display: inline-block;
    border: 2px solid var(--mt-primary);
    border-radius: var(--mt-radius-md);
    padding: 8px 14px;
    margin: 6px;
    background: white;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: default;
}

.mt-dag-node.root {
    background: var(--mt-primary);
    color: white;
}

.mt-dag-node.error {
    border-color: var(--mt-error);
    background: var(--mt-error-bg);
}

.mt-dag-edge {
    color: var(--mt-gray-300);
    font-size: 1.2rem;
}
</style>
"""


def inject_css():
    """注入 CSS 到 Streamlit 页面"""
    import streamlit as st
    st.markdown(MATH_TUTOR_CSS, unsafe_allow_html=True)
