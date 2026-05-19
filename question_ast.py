"""question_ast.py — Question Abstract Syntax Tree

Structured question data — NOT a flat markdown blob.

Each question type has its own AST node.
Renderers consume the AST, not raw text.
"""
import re
import json as _json
from latex_utils import normalize_latex_style
from dataclasses import dataclass, field
from typing import Optional as _Optional, List as _List, Dict as _Dict

# 语义增强器
from semantic_enhancer import get_semantic_enhancer, get_parser_enhancer


# ============================================================
# AST Nodes
# ============================================================

@dataclass
class ChoiceOption:
    label: str            # "A", "B", "C", "D"
    content: str          # LaTeX, e.g. "k=2, c=-\\frac12"


@dataclass
class QuestionStem:
    """Parsed question stem — text + optional inline math."""
    text: str             # Clean text with inline math markers preserved


@dataclass
class SolutionStep:
    label: str = ""       # "步骤1"
    content: str = ""     # LaTeX / text
    operation: str = ""   # "differentiate", "solve", etc.
    input_expr: _Optional['ExprNode'] = None    # 输入表达式 AST
    output_expr: _Optional['ExprNode'] = None   # 输出表达式 AST
    
    def get_operation(self):
        """获取规范化的操作类型"""
        from operations import normalize_op
        return normalize_op(self.operation)
    
    def set_operation(self, op):
        """设置操作类型（支持 Op 枚举或字符串）"""
        from operations import normalize_op
        normalized = normalize_op(op)
        self.operation = normalized.value
    
    def parse_input_expr(self, latex: str):
        """解析输入表达式 LaTeX 为 AST"""
        from expression_parser import parse_latex
        try:
            self.input_expr = parse_latex(latex)
        except Exception:
            self.input_expr = None

    def parse_output_expr(self, latex: str):
        """解析输出表达式 LaTeX 为 AST"""
        from expression_parser import parse_latex
        try:
            self.output_expr = parse_latex(latex)
        except Exception:
            self.output_expr = None

    def evaluate_input(self, variables: dict = None) -> _Optional[float]:
        """计算输入表达式的值"""
        if self.input_expr:
            try:
                return self.input_expr.evaluate(variables or {})
            except Exception:
                return None
        return None

    def evaluate_output(self, variables: dict = None) -> _Optional[float]:
        """计算输出表达式的值"""
        if self.output_expr:
            try:
                return self.output_expr.evaluate(variables or {})
            except Exception:
                return None
        return None
    
    def get_input_latex(self) -> str:
        """获取输入表达式的 LaTeX 表示"""
        if self.input_expr:
            return self.input_expr.to_latex()
        return ""
    
    def get_output_latex(self) -> str:
        """获取输出表达式的 LaTeX 表示"""
        if self.output_expr:
            return self.output_expr.to_latex()
        return ""


@dataclass
class QuestionAST:
    """Base AST node — common fields for all question types."""
    question_id: str
    question_type: str              # "选择题" | "填空题" | "解答题" | "证明题"
    stem: str = ""                  # Pure question text (no options mixed in)
    answer: str = ""                # Correct answer
    analysis: str = ""              # Solution / explanation
    year: str = ""
    category: str = ""
    score: str = ""
    difficulty: str = "中等"
    knowledge_points: list = field(default_factory=list)
    # Type-specific fields
    options: list = field(default_factory=list)    # list[ChoiceOption] for choice
    steps: list = field(default_factory=list)      # list[SolutionStep] for solution/proof
    # Reasoning DAG for tracking logical flow
    reasoning_dag: _Optional['ReasoningDAG'] = None
    
    def build_reasoning_dag(self) -> 'ReasoningDAG':
        """从解答步骤构建推理图"""
        from reasoning_dag import DagBuilder, NodeType
        
        builder = DagBuilder()
        
        # 添加前提节点（题目描述）
        premise_id = builder.add_premise(self.stem)
        
        # 添加目标节点
        goal_id = builder.add_goal(f"求答案: {self.answer}")
        
        # 跟踪上一步的输出节点ID
        prev_output_id = premise_id
        
        # 遍历步骤构建推理链
        for i, step in enumerate(self.steps):
            # 添加操作节点
            op_type = step.get_operation()
            op_id = builder.add_operation(op_type, step.content)
            
            # 如果有输入表达式，添加表达式节点
            if step.input_expr:
                input_expr_id = builder.add_expression(
                    step.get_input_latex(), 
                    step.input_expr
                )
                builder.connect_input(input_expr_id, op_id, "输入")
                # 连接上一步的输出到当前输入
                if prev_output_id:
                    builder.connect_depends(prev_output_id, input_expr_id, "前置")
            
            # 如果有输出表达式，添加表达式节点
            if step.output_expr:
                output_expr_id = builder.add_expression(
                    step.get_output_latex(), 
                    step.output_expr
                )
                builder.connect_output(op_id, output_expr_id, "输出")
                prev_output_id = output_expr_id
        
        # 添加结论节点
        conclusion_id = builder.add_conclusion(self.answer)
        if prev_output_id:
            builder.connect_derives(prev_output_id, conclusion_id, "推导")
        builder.connect_depends(goal_id, conclusion_id, "达成")
        
        self.reasoning_dag = builder.build()
        return self.reasoning_dag
    
    def get_reasoning_mermaid(self) -> str:
        """获取推理图的 Mermaid 表示"""
        if self.reasoning_dag is None:
            self.build_reasoning_dag()
        return self.reasoning_dag.to_mermaid()
    
    def validate_reasoning(self) -> dict:
        """验证推理链的正确性"""
        if self.reasoning_dag is None:
            self.build_reasoning_dag()
        
        result = {
            'valid': True,
            'has_cycles': False,
            'errors': [],
            'warnings': []
        }
        
        # 检查是否有环
        cycles = self.reasoning_dag.find_cycles()
        if cycles:
            result['has_cycles'] = True
            result['valid'] = False
            result['errors'].append(f"发现 {len(cycles)} 个循环依赖")
        
        # 检查是否有孤立节点
        for node_id, node in self.reasoning_dag.nodes.items():
            in_edges = self.reasoning_dag.get_edges_to(node_id)
            out_edges = self.reasoning_dag.get_edges_from(node_id)
            if not in_edges and not out_edges and node.type != NodeType.PREMISE:
                result['warnings'].append(f"孤立节点: {node.label}")
        
        return result
    
    def enhance_semantics(self) -> 'QuestionAST':
        """增强AST的语义信息"""
        enhancer = get_semantic_enhancer()
        
        # 为步骤补充操作语义
        enhanced_steps = []
        for i, step in enumerate(self.steps):
            if isinstance(step, SolutionStep):
                content = step.content
                operation = step.operation
            elif isinstance(step, dict):
                content = step.get("content", "")
                operation = step.get("operation", "")
            else:
                content = str(step)
                operation = ""
            
            # 如果没有操作类型，自动推断
            if not operation:
                op = enhancer.infer_operation(content)
                operation = op.value
            
            enhanced_steps.append(SolutionStep(
                label=f"步骤{i+1}",
                content=content,
                operation=operation,
            ))
        
        self.steps = enhanced_steps
        
        return self
    
    def validate_semantics(self) -> dict:
        """完整语义验证"""
        enhancer = get_semantic_enhancer()
        return enhancer.full_validation(self)
    
    def validate_structure(self) -> dict:
        """验证结构完整性"""
        enhancer = get_semantic_enhancer()
        return enhancer.validate_structure(self)
    
    def validate_knowledge_consistency(self) -> dict:
        """验证知识点一致性"""
        enhancer = get_semantic_enhancer()
        return enhancer.validate_knowledge_consistency(self)


# ============================================================
# Parser: legacy flat text → AST
# ============================================================

def _extract_stem_and_options(text: str) -> tuple[str, list[ChoiceOption]]:
    """Extract stem text and choice options from legacy question text.

    Handles formats:
      $(A)$ content \\qquad $(B)$ content
      (A) content (B) content
      A. content  B. content
      $(A)$ $y=x+e$ $(B)$ $y=x+1$ (无 \qquad 分隔)
    """
    options = []
    stem = text

    # 预处理：先把 \qquad 和 \quad 替换为换行，这样选项就会出现在单独的行
    processed_text = text.replace('\\qquad', '\n').replace('\\quad', '\n')

    # Pattern: 匹配选项标签
    # 支持以下位置的选项标签：
    # 1. 行首或换行后
    # 2. 数学表达式后（$ 符号后）
    # 3. 右括号后（\) 或 \right\) 或普通 )）
    # 4. 中文括号后（））
    opt_pattern = re.compile(
        r'(?:^|\n)(?:\s*\$\\left\(\\mathrm\{([A-D])\}\\right\))'
        r'|'
        r'(?:^|\n)(?:\s*\$\(([A-D])\))'
        r'|'
        r'(?:^|\n)(?:\s*[（(]\s*([A-D])\s*[）)])'
        r'|'
        # 新增：匹配 $ 符号后的选项标签（如 $(A)$ $y=x+e$ $(B)$ ...）
        r'(?<=\$)(?:\s*\$\(([A-D])\))'
        r'|'
        r'(?<=\$)(?:\s*\$\\left\(\\mathrm\{([A-D])\}\\right\))'
        r'|'
        # 新增：匹配右括号后的选项标签（如 ...\) $(A)$）
        r'(?<=\\\))(?:\s*\$\(([A-D])\))'
        r'|'
        r'(?<=\\right\))(?:\s*\$\(([A-D])\))'
        r'|'
        # 新增：匹配普通右括号后的选项标签（如 ...) $(A)$）
        r'(?<=\))(?:\s*\$\(([A-D])\))'
        r'|'
        # 新增：匹配中文右括号后的选项标签（如 ...） $(A)$）
        r'(?<=）)(?:\s*\$\(([A-D])\))'
    )

    # Find all option markers with positions
    markers = []
    for m in opt_pattern.finditer(processed_text):
        # 支持9个捕获组
        label = m.group(1) or m.group(2) or m.group(3) or \
                m.group(4) or m.group(5) or m.group(6) or \
                m.group(7) or m.group(8) or m.group(9)
        if label and label not in [x[0] for x in markers]:
            markers.append((label, m.start(), m.end()))

    if len(markers) >= 2:
        # First marker position = end of stem
        stem_end = markers[0][1]
        stem = processed_text[:stem_end].strip()
        # Remove trailing number prefix like "1. " or "$1.$"
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', stem)

        # Extract option content between markers
        for i, (label, start, end) in enumerate(markers):
            next_start = markers[i + 1][1] if i + 1 < len(markers) else len(processed_text)
            content = processed_text[end:next_start].strip()
            # Clean up separators
            content = re.sub(r'\\qquad|\\quad', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()
            # Handle the case where label is formatted as $\left(\mathrm{A}\right)$
            # and is directly followed by $$ content (no space)
            # This causes the two $ signs to merge, leaving an extra $ at the start
            # e.g., $\left(\mathrm{A}\right)$$$content$$ -> match gives $content$$
            # If content starts with $$, it's correct. If it starts with $ but not $$,
            # it means there's an extra $ that should be removed
            if content.startswith('$') and len(content) > 1 and not content.startswith('$$'):
                content = content[1:].strip()
            # LaTeX post-processing: normalize + preserve $ delimiters
            content = normalize_latex_style(content)
            # Preserve all $ delimiters - the renderer will handle them appropriately
            options.append(ChoiceOption(label=label, content=content))

    # Deduplicate by label (keep first occurrence)
    seen = set()
    deduped = []
    for o in options:
        if o.label not in seen:
            seen.add(o.label)
            deduped.append(o)

    return stem, deduped


def _extract_answer(text: str, qtype: str) -> str:
    """Extract answer from text based on question type."""
    # Choice: look for "正确选项" or check the correct_option field
    m = re.search(r'(?:正确选项|答案|选)\s*[：:]\s*([A-D])', text)
    if m:
        return m.group(1)
    # Fill/Solution: look for answer markers
    m = re.search(r'(?:答案|答|解)\s*[：:]\s*(.+?)(?:\n|$)', text)
    if m:
        return m.group(1).strip()
    return ""


def parse_legacy(q: dict) -> QuestionAST:
    """Convert a legacy QuestionDB dict into a QuestionAST.

    The legacy format stores the entire question as a single LaTeX string
    in q['question'], with options/answers embedded inline.
    This parser decomposes it into structured fields.
    """
    qid = q.get("question_id", "?")
    qtype = q.get("question_type", "")
    raw_text = q.get("question", "")
    raw_answer = q.get("standard_answer", "")
    correct = q.get("correct_option", "")
    options_raw = q.get("options") or {}
    steps_raw = q.get("solution_steps") or []

    # Parse stem + options from raw text
    stem = raw_text
    options = []

    if qtype == "选择题":
        stem, options = _extract_stem_and_options(raw_text)
        # Use existing options dict if the parser didn't find inline options
        if options_raw and len(options_raw) >= len(options):
            # Replace parsed options with explicit dict (more reliable)
            options = []
            for label in "ABCDEFGH":
                if label in options_raw:
                    c = options_raw[label].strip()
                    options.append(ChoiceOption(label=label, content=normalize_latex_style(c)))
        answer = correct or raw_answer

    elif qtype == "填空题":
        answer = raw_answer
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', raw_text)

    elif qtype in ("解答题", "证明题"):
        answer = raw_answer
        # 移除题号前缀
        stem = re.sub(r'^\s*\$?\d+\.?\$?\s*', '', raw_text)
        # 移除"(本题满分XX分)"标记，因为界面已经显示分数
        stem = re.sub(r'\(本题满分\d+分\)', '', stem)
        stem = re.sub(r'\(本题满\d+分\)', '', stem)
        stem = stem.strip()
        if not answer and raw_text:
            answer = _extract_answer(raw_text, qtype)

    else:
        answer = raw_answer

    # Parse solution steps
    steps = []
    for s in steps_raw:
        if isinstance(s, dict):
            steps.append(SolutionStep(
                label=s.get("label", ""),
                content=s.get("content", ""),
                operation=s.get("operation", ""),
            ))
        elif isinstance(s, str):
            steps.append(SolutionStep(content=s))

    # Normalize LaTeX: wrap bare math, fix stray $, unify delimiters
    stem = normalize_latex_style(stem.strip()) if stem else ""
    answer = normalize_latex_style(answer.strip()) if answer else ""

    return QuestionAST(
        question_id=qid,
        question_type=qtype,
        stem=stem,
        answer=answer.strip() if answer else "",
        analysis=raw_answer.strip() if raw_answer else "",
        year=str(q.get("year", "")),
        category=q.get("category", ""),
        score=str(q.get("score", "")),
        difficulty=q.get("difficulty", "中等"),
        knowledge_points=q.get("knowledge_points") or q.get("tags") or [],
        options=options,
        steps=steps,
    )


# ============================================================
# Serialization
# ============================================================

def ast_to_dict(ast: QuestionAST) -> dict:
    """Convert QuestionAST back to a plain dict (for JSON storage)."""
    return {
        "question_id": ast.question_id,
        "question_type": ast.question_type,
        "stem": ast.stem,
        "options": [{"label": o.label, "content": o.content} for o in ast.options],
        "answer": ast.answer,
        "analysis": ast.analysis,
        "steps": [
            {"label": s.label, "content": s.content, "operation": s.operation}
            for s in ast.steps
        ],
        "year": ast.year,
        "category": ast.category,
        "score": ast.score,
        "difficulty": ast.difficulty,
        "knowledge_points": ast.knowledge_points,
    }


def ast_to_json(ast: QuestionAST) -> str:
    """Serialize QuestionAST to JSON string."""
    return _json.dumps(ast_to_dict(ast), ensure_ascii=False, indent=2)


# ============================================================
# Legacy dict adapter (for backward compatibility)
# ============================================================

def ast_to_legacy_dict(ast: QuestionAST) -> dict:
    """Convert AST back to a dict compatible with legacy renderers.

    This allows gradual migration — renderers that expect q['question']
    will still work while we transition to AST-native rendering.
    """
    # Rebuild the full question text
    parts = [ast.stem]
    if ast.options:
        opt_parts = []
        for i, opt in enumerate(ast.options):
            opt_parts.append(
                f"$(\\left(\\mathrm{{{opt.label}}}\\right))$ {opt.content}"
            )
        parts.append("  ".join(opt_parts))

    full_text = "\n\n".join(parts)

    return {
        "question_id": ast.question_id,
        "question_type": ast.question_type,
        "question": full_text,
        "standard_answer": ast.answer,
        "correct_option": ast.answer if ast.question_type == "选择题" else "",
        "options": {o.label: o.content for o in ast.options} if ast.options else {},
        "solution_steps": [
            {"label": s.label, "content": s.content, "operation": s.operation}
            for s in ast.steps
        ],
        "year": ast.year,
        "category": ast.category,
        "score": ast.score,
        "difficulty": ast.difficulty,
        "knowledge_points": ast.knowledge_points,
        "tags": ast.knowledge_points,
    }
