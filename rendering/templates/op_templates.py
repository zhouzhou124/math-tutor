"""
OpTemplate — 操作语义模板 + 注册表

═══════════════════════════════════════════════════════════════
核心数据结构
═══════════════════════════════════════════════════════════════

  OpTemplate:
    op_key          — 操作键 (Op 枚举值字符串)
    title           — 标题模板: "约分"
    explanation     — 解释模板: "约去分子分母公共因子"
    constraints     — 约束模板列表: ["需满足 {constraint} ≠ 0"]
    error_hints     — 常见错误提示: ["约分时遗漏非零条件"]
    latex_hint      — LaTeX 表示模板
    category        — 操作分类: "calculus" / "algebra" / "linalg" / ...
    color           — 显示颜色 (用于前端渲染)

  模板变量:
    {input}       — 输入表达式
    {output}      — 输出表达式
    {variable}    — 操作变量 (如求导变量 x)
    {constraint}  — 约束条件
    {theorem}     — 使用的定理
    {factor}      — 公因子
    {point}       — 代入点
    {order}       — 阶数

═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class OpTemplate:
    """
    操作语义模板 — 将 Op 枚举映射为人类可读的语义描述。

    示例:
      Op.CANCEL → OpTemplate(
          op_key="cancel",
          title="约分",
          explanation="约去分子分母公共因子 {factor}",
          constraints=["需满足 {factor} ≠ 0"],
          error_hints=["约分时遗漏非零条件: {factor} ≠ 0"],
      )

    用法:
      tpl = get_template("cancel")
      tpl.render_title()                          → "约分"
      tpl.render_explanation(factor="x-1")        → "约去分子分母公共因子 x-1"
      tpl.render_constraints(factor="x-1")        → ["需满足 x-1 ≠ 0"]
      tpl.render_error_hints(factor="x-1")        → ["约分时遗漏非零条件: x-1 ≠ 0"]
    """

    op_key: str = ""
    title: str = ""
    explanation: str = ""
    constraints: tuple[str, ...] = ()
    error_hints: tuple[str, ...] = ()
    latex_hint: str = ""
    category: str = "general"
    color: str = "#6b7280"

    def render_title(self, **kwargs) -> str:
        return self.title.format(**kwargs) if kwargs else self.title

    def render_explanation(self, **kwargs) -> str:
        return self.explanation.format(**kwargs) if kwargs else self.explanation

    def render_constraints(self, **kwargs) -> list[str]:
        if not kwargs:
            return list(self.constraints)
        return [c.format(**kwargs) for c in self.constraints]

    def render_error_hints(self, **kwargs) -> list[str]:
        if not kwargs:
            return list(self.error_hints)
        return [e.format(**kwargs) for e in self.error_hints]

    def render_latex_hint(self, **kwargs) -> str:
        if not kwargs:
            return self.latex_hint
        return self.latex_hint.format(**kwargs)

    def render_full(self, **kwargs) -> dict:
        return {
            "op_key": self.op_key,
            "title": self.render_title(**kwargs),
            "explanation": self.render_explanation(**kwargs),
            "constraints": self.render_constraints(**kwargs),
            "error_hints": self.render_error_hints(**kwargs),
            "latex_hint": self.render_latex_hint(**kwargs),
            "category": self.category,
            "color": self.color,
        }

    def to_dict(self) -> dict:
        return {
            "op_key": self.op_key,
            "title": self.title,
            "explanation": self.explanation,
            "constraints": list(self.constraints),
            "error_hints": list(self.error_hints),
            "latex_hint": self.latex_hint,
            "category": self.category,
            "color": self.color,
        }

    @classmethod
    def from_dict(cls, d: dict) -> OpTemplate:
        return cls(
            op_key=d.get("op_key", ""),
            title=d.get("title", ""),
            explanation=d.get("explanation", ""),
            constraints=tuple(d.get("constraints", ())),
            error_hints=tuple(d.get("error_hints", ())),
            latex_hint=d.get("latex_hint", ""),
            category=d.get("category", "general"),
            color=d.get("color", "#6b7280"),
        )


class TemplateRegistry:
    """
    模板注册表 — 管理所有 OpTemplate。

    用法:
      registry = TemplateRegistry()
      registry.register(OpTemplate(op_key="cancel", title="约分", ...))
      tpl = registry.get("cancel")
      tpl.render_explanation(factor="x-1")
    """

    def __init__(self):
        self._templates: dict[str, OpTemplate] = {}

    def register(self, template: OpTemplate) -> None:
        self._templates[template.op_key] = template

    def register_many(self, templates: list[OpTemplate]) -> None:
        for t in templates:
            self.register(t)

    def get(self, op_key: str) -> Optional[OpTemplate]:
        return self._templates.get(op_key)

    def get_or_default(self, op_key: str) -> OpTemplate:
        tpl = self._templates.get(op_key)
        if tpl:
            return tpl
        return OpTemplate(
            op_key=op_key,
            title=op_key,
            explanation=f"执行 {op_key} 操作",
            category="general",
        )

    def has(self, op_key: str) -> bool:
        return op_key in self._templates

    def all_keys(self) -> list[str]:
        return sorted(self._templates.keys())

    def all_templates(self) -> list[OpTemplate]:
        return list(self._templates.values())

    def by_category(self, category: str) -> list[OpTemplate]:
        return [t for t in self._templates.values() if t.category == category]

    def categories(self) -> dict[str, list[OpTemplate]]:
        result: dict[str, list[OpTemplate]] = {}
        for t in self._templates.values():
            if t.category not in result:
                result[t.category] = []
            result[t.category].append(t)
        return result

    def merge(self, other: TemplateRegistry) -> None:
        for key, tpl in other._templates.items():
            self._templates[key] = tpl

    def __len__(self) -> int:
        return len(self._templates)

    def __contains__(self, op_key: str) -> bool:
        return op_key in self._templates

    def __getitem__(self, op_key: str) -> OpTemplate:
        return self.get_or_default(op_key)


template_registry = TemplateRegistry()


def get_template(op_key: str) -> OpTemplate:
    return template_registry.get_or_default(op_key)


def render_title(op_key: str, **kwargs) -> str:
    return get_template(op_key).render_title(**kwargs)


def render_explanation(op_key: str, **kwargs) -> str:
    return get_template(op_key).render_explanation(**kwargs)


def render_constraints(op_key: str, **kwargs) -> list[str]:
    return get_template(op_key).render_constraints(**kwargs)


def render_error_hints(op_key: str, **kwargs) -> list[str]:
    return get_template(op_key).render_error_hints(**kwargs)


def render_full_description(op_key: str, **kwargs) -> dict:
    return get_template(op_key).render_full(**kwargs)
