"""canonicalization/ir.py — 规范推理中间表示层（Canonical Reasoning IR）

提供数学推理的统一中间表示，支持：
- 步骤级推理表示
- 公式规范化
- 约束系统
- 错误传播追踪

架构设计：
┌─────────────────────────────────────────────────────────┐
│           Canonical Reasoning IR                        │
├─────────────────────────────────────────────────────────┤
│  ReasoningStep — 推理步骤                               │
│  FormulaNode — 公式节点                                 │
│  Constraint — 约束                                      │
│  ErrorTrace — 错误追踪                                  │
│  ProofTree — 证明树                                     │
└─────────────────────────────────────────────────────────┘

未来数据流：
    LLM → Math AST → Canonical IR → Constraint Engine → Diagnosis → ViewModel → Renderer → UI
"""
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum
from dataclasses import dataclass, field
from sympy import Expr, simplify, expand, factor


class StepStatus(Enum):
    """步骤状态"""
    CORRECT = "correct"           # 正确
    PARTIALLY_CORRECT = "partially_correct"  # 部分正确
    INCORRECT = "incorrect"       # 错误
    UNVERIFIED = "unverified"     # 未验证
    ASSUMPTION = "assumption"     # 假设


class StepType(Enum):
    """步骤类型"""
    ASSUMPTION = "assumption"     # 假设
    DEFINITION = "definition"     # 定义
    THEOREM = "theorem"           # 定理
    AXIOM = "axiom"               # 公理
    DERIVATION = "derivation"     # 推导
    SUBSTITUTION = "substitution" # 代入
    SIMPLIFICATION = "simplification" # 化简
    TRANSFORMATION = "transformation" # 变换
    CONCLUSION = "conclusion"     # 结论
    CHECK = "check"               # 验证
    ERROR = "error"               # 错误


class ErrorCategory(Enum):
    """错误类别"""
    CALCULATION = "calculation"           # 计算错误
    LOGIC = "logic"                       # 逻辑错误
    CONCEPT = "concept"                   # 概念错误
    APPLICATION = "application"           # 应用错误
    MISAPPLICATION = "misapplication"     # 误用
    OMISSION = "omission"                 # 遗漏
    REDUNDANCY = "redundancy"             # 冗余
    FORMATTING = "formatting"             # 格式错误


@dataclass
class FormulaNode:
    """公式节点 — 规范化的数学表达式"""
    expression: Expr              # SymPy 表达式
    latex: str                   # LaTeX 字符串
    canonical_form: Optional[str] = None  # 规范化形式
    variables: Set[str] = field(default_factory=set)  # 变量集合
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """后初始化 — 计算规范化形式"""
        if self.expression is not None:
            self.canonical_form = self._compute_canonical()
    
    def _compute_canonical(self) -> str:
        """计算规范化形式"""
        try:
            # 多种规范化形式
            simplified = simplify(self.expression)
            expanded = expand(self.expression)
            factored = factor(self.expression)
            
            # 返回最简洁的形式
            forms = [str(simplified), str(expanded), str(factored)]
            return min(forms, key=len)
        except Exception:
            return str(self.expression)
    
    def is_equivalent(self, other: 'FormulaNode') -> bool:
        """判断是否等价"""
        if self.expression is None or other.expression is None:
            return False
        try:
            return simplify(self.expression - other.expression) == 0
        except Exception:
            return False
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "latex": self.latex,
            "canonical_form": self.canonical_form,
            "variables": list(self.variables),
            **self.properties
        }


@dataclass
class Constraint:
    """约束 — 推理过程中的约束条件"""
    id: str
    type: str                     # 约束类型：equality, inequality, domain, etc.
    left: FormulaNode             # 左表达式
    right: FormulaNode            # 右表达式
    operator: str                 # 操作符：=, <, >, <=, >=, !=
    is_active: bool = True        # 是否激活
    source_step: Optional[str] = None  # 来源步骤ID
    
    def is_satisfied(self) -> bool:
        """检查约束是否满足"""
        if not self.is_active:
            return True
        
        try:
            diff = self.left.expression - self.right.expression
            simplified = simplify(diff)
            
            if self.operator == "=":
                return simplified == 0
            elif self.operator == "!=":
                return simplified != 0
            elif self.operator == "<":
                return simplified < 0
            elif self.operator == ">":
                return simplified > 0
            elif self.operator == "<=":
                return simplified <= 0
            elif self.operator == ">=":
                return simplified >= 0
        except Exception:
            return False
        
        return False
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "operator": self.operator,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "is_active": self.is_active,
            "source_step": self.source_step
        }


@dataclass
class ErrorTrace:
    """错误追踪 — 错误的传播路径和原因"""
    error_id: str
    step_id: str                  # 发生错误的步骤ID
    category: ErrorCategory       # 错误类别
    message: str                  # 错误消息
    confidence: float = 0.0       # 置信度
    propagated_to: List[str] = field(default_factory=list)  # 传播到的步骤ID列表
    suggested_fix: Optional[str] = None  # 建议修复
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "error_id": self.error_id,
            "step_id": self.step_id,
            "category": self.category.value,
            "message": self.message,
            "confidence": self.confidence,
            "propagated_to": self.propagated_to,
            "suggested_fix": self.suggested_fix
        }


@dataclass
class ReasoningStep:
    """推理步骤 — 规范化的推理步骤表示"""
    id: str
    content: str                  # 步骤内容（自然语言描述）
    formula: Optional[FormulaNode] = None  # 关联的公式
    step_type: StepType = StepType.DERIVATION
    status: StepStatus = StepStatus.UNVERIFIED
    dependencies: List[str] = field(default_factory=list)  # 依赖的步骤ID列表
    errors: List[ErrorTrace] = field(default_factory=list)  # 错误列表
    constraints: List[Constraint] = field(default_factory=list)  # 约束列表
    score: Optional[float] = None  # 得分（0-1）
    explanation: Optional[str] = None  # 解释说明
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) > 0 or self.status == StepStatus.INCORRECT
    
    @property
    def is_correct(self) -> bool:
        """检查是否正确"""
        return self.status == StepStatus.CORRECT
    
    def add_error(self, error: ErrorTrace):
        """添加错误"""
        self.errors.append(error)
    
    def add_constraint(self, constraint: Constraint):
        """添加约束"""
        self.constraints.append(constraint)
    
    def add_dependency(self, step_id: str):
        """添加依赖"""
        if step_id not in self.dependencies:
            self.dependencies.append(step_id)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "formula": self.formula.to_dict() if self.formula else None,
            "step_type": self.step_type.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "errors": [e.to_dict() for e in self.errors],
            "constraints": [c.to_dict() for c in self.constraints],
            "score": self.score,
            "explanation": self.explanation,
            **self.properties
        }


@dataclass
class ProofTree:
    """证明树 — 完整的推理结构"""
    root_id: str                  # 根步骤ID
    steps: List[ReasoningStep] = field(default_factory=list)
    title: Optional[str] = None
    description: Optional[str] = None
    overall_status: StepStatus = StepStatus.UNVERIFIED
    final_score: Optional[float] = None  # 最终得分
    
    def add_step(self, step: ReasoningStep):
        """添加步骤"""
        # 检查是否已存在
        existing = next((s for s in self.steps if s.id == step.id), None)
        if existing:
            # 更新现有步骤
            idx = self.steps.index(existing)
            self.steps[idx] = step
        else:
            self.steps.append(step)
    
    def get_step(self, step_id: str) -> Optional[ReasoningStep]:
        """获取步骤"""
        return next((s for s in self.steps if s.id == step_id), None)
    
    def get_dependencies(self, step_id: str) -> List[ReasoningStep]:
        """获取步骤的所有依赖"""
        step = self.get_step(step_id)
        if not step:
            return []
        
        dependencies = []
        for dep_id in step.dependencies:
            dep_step = self.get_step(dep_id)
            if dep_step:
                dependencies.append(dep_step)
        return dependencies
    
    def get_dependents(self, step_id: str) -> List[ReasoningStep]:
        """获取依赖于指定步骤的所有步骤"""
        dependents = []
        for step in self.steps:
            if step_id in step.dependencies:
                dependents.append(step)
        return dependents
    
    def get_error_propagation_path(self, error_id: str) -> List[str]:
        """获取错误传播路径"""
        path = []
        # 找到包含该错误的步骤
        for step in self.steps:
            for error in step.errors:
                if error.error_id == error_id:
                    path.append(step.id)
                    # 追踪传播路径
                    for target_id in error.propagated_to:
                        path.extend(self._get_propagation_chain(target_id))
                    return path
        return path
    
    def _get_propagation_chain(self, step_id: str) -> List[str]:
        """递归获取传播链"""
        chain = [step_id]
        step = self.get_step(step_id)
        if step:
            for dependent in self.get_dependents(step_id):
                if dependent.id not in chain:
                    chain.extend(self._get_propagation_chain(dependent.id))
        return chain
    
    def validate_constraints(self) -> List[Constraint]:
        """验证所有约束，返回不满足的约束"""
        violated = []
        for step in self.steps:
            for constraint in step.constraints:
                if not constraint.is_satisfied():
                    violated.append(constraint)
        return violated
    
    def compute_overall_status(self):
        """计算整体状态"""
        statuses = [step.status for step in self.steps]
        
        if StepStatus.INCORRECT in statuses:
            self.overall_status = StepStatus.INCORRECT
        elif StepStatus.PARTIALLY_CORRECT in statuses:
            self.overall_status = StepStatus.PARTIALLY_CORRECT
        elif all(s == StepStatus.CORRECT for s in statuses):
            self.overall_status = StepStatus.CORRECT
        else:
            self.overall_status = StepStatus.UNVERIFIED
        
        # 计算综合得分
        if self.steps:
            valid_scores = [s.score for s in self.steps if s.score is not None]
            if valid_scores:
                self.final_score = sum(valid_scores) / len(valid_scores)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "root_id": self.root_id,
            "steps": [step.to_dict() for step in self.steps],
            "title": self.title,
            "description": self.description,
            "overall_status": self.overall_status.value,
            "final_score": self.final_score
        }


class IRBuilder:
    """IR构建器 — 从各种来源构建规范推理IR"""
    
    @staticmethod
    def from_latex(latex_str: str) -> FormulaNode:
        """从LaTeX字符串创建公式节点"""
        from sympy import latex as sympy_latex
        from sympy.parsing.latex import parse_latex
        
        try:
            expr = parse_latex(latex_str)
            return FormulaNode(
                expression=expr,
                latex=sympy_latex(expr),
                variables=set(str(v) for v in expr.free_symbols)
            )
        except Exception:
            # 如果解析失败，返回原始LaTeX
            return FormulaNode(
                expression=None,
                latex=latex_str,
                variables=set()
            )
    
    @staticmethod
    def from_dict(data: Dict) -> ReasoningStep:
        """从字典创建推理步骤"""
        formula_data = data.get("formula")
        formula = None
        if formula_data:
            formula = FormulaNode(
                expression=None,  # 需要从latex重新解析
                latex=formula_data.get("latex", ""),
                canonical_form=formula_data.get("canonical_form"),
                variables=set(formula_data.get("variables", [])),
                properties=formula_data
            )
        
        errors = []
        for error_data in data.get("errors", []):
            errors.append(ErrorTrace(
                error_id=error_data.get("error_id", ""),
                step_id=data.get("id", ""),
                category=ErrorCategory(error_data.get("category", "calculation")),
                message=error_data.get("message", ""),
                confidence=error_data.get("confidence", 0.0),
                propagated_to=error_data.get("propagated_to", []),
                suggested_fix=error_data.get("suggested_fix")
            ))
        
        return ReasoningStep(
            id=data.get("id", ""),
            content=data.get("content", ""),
            formula=formula,
            step_type=StepType(data.get("step_type", "derivation")),
            status=StepStatus(data.get("status", "unverified")),
            dependencies=data.get("dependencies", []),
            errors=errors,
            score=data.get("score"),
            explanation=data.get("explanation"),
            properties={k: v for k, v in data.items() if k not in ["id", "content", "formula", "step_type", "status", "dependencies", "errors", "score", "explanation"]}
        )
    
    @staticmethod
    def from_proof_tree_dict(data: Dict) -> ProofTree:
        """从字典创建证明树"""
        proof_tree = ProofTree(
            root_id=data.get("root_id", ""),
            title=data.get("title"),
            description=data.get("description"),
            overall_status=StepStatus(data.get("overall_status", "unverified")),
            final_score=data.get("final_score")
        )
        
        for step_data in data.get("steps", []):
            step = IRBuilder.from_dict(step_data)
            proof_tree.add_step(step)
        
        return proof_tree


# 便捷函数
def create_proof_tree_from_steps(steps: List[Dict]) -> ProofTree:
    """从步骤列表创建证明树"""
    proof_tree = ProofTree(root_id="root")
    
    for i, step_data in enumerate(steps):
        step = IRBuilder.from_dict({
            "id": f"step_{i}",
            **step_data
        })
        
        # 设置依赖关系（默认依赖前一步）
        if i > 0:
            step.add_dependency(f"step_{i-1}")
        
        proof_tree.add_step(step)
    
    proof_tree.compute_overall_status()
    return proof_tree


def compare_proof_trees(tree1: ProofTree, tree2: ProofTree) -> Dict:
    """比较两个证明树"""
    result = {
        "is_equivalent": False,
        "differences": [],
        "similarity_score": 0.0
    }
    
    # 比较步骤数量
    if len(tree1.steps) != len(tree2.steps):
        result["differences"].append(f"步骤数量不同: {len(tree1.steps)} vs {len(tree2.steps)}")
    
    # 比较每个步骤
    for step1, step2 in zip(tree1.steps, tree2.steps):
        if step1.status != step2.status:
            result["differences"].append(f"步骤 {step1.id} 状态不同: {step1.status.value} vs {step2.status.value}")
        
        if step1.formula and step2.formula:
            if not step1.formula.is_equivalent(step2.formula):
                result["differences"].append(f"步骤 {step1.id} 公式不等价")
    
    # 计算相似度
    if tree1.steps and tree2.steps:
        matching_steps = sum(1 for s1, s2 in zip(tree1.steps, tree2.steps) if s1.status == s2.status)
        result["similarity_score"] = matching_steps / max(len(tree1.steps), len(tree2.steps))
    
    result["is_equivalent"] = len(result["differences"]) == 0
    return result
