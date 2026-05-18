"""
Operation Template System — 操作语义模板系统

═══════════════════════════════════════════════════════════════
核心问题
═══════════════════════════════════════════════════════════════

  系统内部: Op.CANCEL
  学生看到: "约去公因子 x-1（需满足 x ≠ 1）"

  缺失的正是: 操作 → 人类可读语义 的映射。

═══════════════════════════════════════════════════════════════
设计
═══════════════════════════════════════════════════════════════

  每个 Op 对应一个 OpTemplate，包含:

    (1) 标题模板  title         — "约分"
    (2) 解释模板  explanation   — "约去分子分母公共因子"
    (3) 约束模板  constraints   — ["需满足 {constraint}"]
    (4) 错误模板  error_hints   — ["约分时遗漏非零条件"]
    (5) LaTeX 片段 latex_hint   — 操作的 LaTeX 表示模板

  模板支持变量插值:
    {input}       — 输入表达式
    {output}      — 输出表达式
    {variable}    — 操作变量 (如求导变量 x)
    {constraint}  — 约束条件
    {theorem}     — 使用的定理
    {factor}      — 公因子

═══════════════════════════════════════════════════════════════
"""

from rendering.templates.op_templates import (
    OpTemplate,
    TemplateRegistry,
    template_registry,
    get_template,
    render_title,
    render_explanation,
    render_constraints,
    render_error_hints,
    render_full_description,
)
from rendering.templates.expr_formatter import (
    ExprFormatter,
    format_expr,
    format_constraint,
    format_equation,
)
from rendering.templates.builtin_templates import register_all_builtins

from rendering.templates.algebra import algebra_templates
from rendering.templates.calculus import calculus_templates
from rendering.templates.linear_algebra import linear_algebra_templates
from rendering.templates.logic import logic_templates

register_all_builtins()

__all__ = [
    "OpTemplate",
    "TemplateRegistry",
    "template_registry",
    "get_template",
    "render_title",
    "render_explanation",
    "render_constraints",
    "render_error_hints",
    "render_full_description",
    "ExprFormatter",
    "format_expr",
    "format_constraint",
    "format_equation",
    "register_all_builtins",
    "algebra_templates",
    "calculus_templates",
    "linear_algebra_templates",
    "logic_templates",
]
