"""
语义增强器 — 补充AST的操作语义和验证能力

功能：
1. 操作语义推断：从步骤文本自动识别操作类型
2. 语义验证：检测结构错误和逻辑问题
3. 解析增强：处理更多复杂格式
"""

import re
from typing import List, Dict, Optional, Any
from operations import Op, infer_op_from_text, normalize_op


class SemanticEnhancer:
    """语义增强器"""
    
    def __init__(self):
        # 操作类型模式匹配规则（按优先级）
        self._op_patterns = [
            # 微积分
            (r'(?:求导|导数|微分|f\'|y\'|\'\'|dy/dx|df/dx|\\frac{d}{dx})', Op.DIFFERENTIATE),
            (r'(?:积分|∫|\\int|不定积分|定积分)', Op.INTEGRATE),
            (r'(?:极限|lim|\\lim|x→|趋近于)', Op.COMPUTE_LIMIT),
            (r'(?:偏导|偏导数|∂/∂x|\\partial)', Op.PARTIAL_DIFF),
            
            # 代数变换
            (r'(?:展开|泰勒展开|麦克劳林)', Op.EXPAND_SERIES),
            (r'(?:因式分解|分解因式)', Op.FACTOR),
            (r'(?:化简|整理|合并同类项)', Op.SIMPLIFY),
            (r'(?:代入|替换)', Op.SUBSTITUTE),
            
            # 方程求解
            (r'(?:解方程|求解|求根)', Op.SOLVE_EQUATION),
            (r'(?:解方程组|线性方程组)', Op.SOLVE_SYSTEM),
            (r'(?:解不等式)', Op.SOLVE_INEQUALITY),
            
            # 线性代数
            (r'(?:矩阵|矩阵运算)', Op.MATRIX_OP),
            (r'(?:行列式|det|\\det)', Op.DETERMINANT),
            (r'(?:行变换|初等变换|行阶梯)', Op.ROW_REDUCE),
            (r'(?:特征值|特征向量|λ|\\lambda)', Op.EIGEN_SOLVE),
            (r'(?:正交化|施密特)', Op.ORTHOGONALIZE),
            (r'(?:二次型|标准形|规范形)', Op.QUADRATIC_FORM),
            
            # 级数
            (r'(?:级数|收敛|发散)', Op.CONVERGENCE_TEST),
            (r'(?:求和|级数和)', Op.SUM_SERIES),
            
            # 概率统计
            (r'(?:概率|P\(|条件概率)', Op.PROBABILITY_CALC),
            (r'(?:期望|方差|E\[|D\[)', Op.EXPECTATION),
            (r'(?:极大似然|MLE|似然)', Op.MLE_DERIVE),
            (r'(?:矩估计)', Op.MOMENT_ESTIMATE),
            (r'(?:假设检验)', Op.HYPOTHESIS_TEST),
            
            # 证明
            (r'(?:定理|根据.*定理|应用.*定理)', Op.APPLY_THEOREM),
            (r'(?:数学归纳法)', Op.INDUCTION_STEP),
            (r'(?:反证法)', Op.CONTRADICTION),
            (r'(?:分类讨论|分.*情况)', Op.CLASSIFY),
            
            # 最终答案
            (r'(?:答案|最终答案|所以|故|因此)', Op.FINAL_ANSWER),
        ]
    
    def infer_operation(self, text: str) -> Op:
        """从文本推断操作类型"""
        # 使用 operations.py 中的通用推断
        op = infer_op_from_text(text)
        if op != Op.COMPUTE:
            return op
        
        # 额外的模式匹配
        for pattern, operation in self._op_patterns:
            if re.search(pattern, text):
                return operation
        
        return Op.COMPUTE
    
    def enhance_solution_steps(self, steps: List[dict]) -> List[dict]:
        """为解答步骤补充操作语义"""
        enhanced = []
        
        for i, step in enumerate(steps):
            content = step.get("content", "")
            label = step.get("label", f"步骤{i+1}")
            operation = step.get("operation", "")
            
            # 推断操作类型
            if not operation or operation == "":
                op = self.infer_operation(content)
                operation = op.value
            
            enhanced.append({
                "label": label,
                "content": content,
                "operation": operation,
                "operation_display": self._get_operation_display(operation),
                "step_number": i + 1,
            })
        
        return enhanced
    
    def _get_operation_display(self, operation: str) -> str:
        """获取操作类型的中文显示名称"""
        display_map = {
            Op.DIFFERENTIATE.value: "求导",
            Op.INTEGRATE.value: "积分",
            Op.COMPUTE_LIMIT.value: "极限",
            Op.PARTIAL_DIFF.value: "偏导",
            Op.EXPAND.value: "展开",
            Op.EXPAND_SERIES.value: "级数展开",
            Op.FACTOR.value: "因式分解",
            Op.SIMPLIFY.value: "化简",
            Op.SUBSTITUTE.value: "代入",
            Op.COLLECT.value: "合并同类项",
            Op.SOLVE_EQUATION.value: "解方程",
            Op.SOLVE_SYSTEM.value: "解方程组",
            Op.SOLVE_INEQUALITY.value: "解不等式",
            Op.MATRIX_OP.value: "矩阵运算",
            Op.DETERMINANT.value: "行列式",
            Op.ROW_REDUCE.value: "行变换",
            Op.EIGEN_SOLVE.value: "特征值求解",
            Op.ORTHOGONALIZE.value: "正交化",
            Op.QUADRATIC_FORM.value: "二次型",
            Op.CONVERGENCE_TEST.value: "级数收敛",
            Op.SUM_SERIES.value: "级数求和",
            Op.PROBABILITY_CALC.value: "概率计算",
            Op.EXPECTATION.value: "期望方差",
            Op.MLE_DERIVE.value: "极大似然估计",
            Op.MOMENT_ESTIMATE.value: "矩估计",
            Op.HYPOTHESIS_TEST.value: "假设检验",
            Op.APPLY_THEOREM.value: "应用定理",
            Op.INDUCTION_STEP.value: "数学归纳",
            Op.CONTRADICTION.value: "反证法",
            Op.CLASSIFY.value: "分类讨论",
            Op.FINAL_ANSWER.value: "最终答案",
            Op.COMPUTE.value: "计算",
        }
        return display_map.get(operation, operation)
    
    def validate_structure(self, ast: Any) -> dict:
        """验证AST结构完整性"""
        errors = []
        warnings = []
        
        # 检查必需字段
        required_fields = ["question_id", "question_type", "stem"]
        for field in required_fields:
            if not getattr(ast, field, None):
                errors.append(f"缺少必需字段: {field}")
        
        # 验证选择题结构
        if ast.question_type == "选择题":
            if not ast.options or len(ast.options) < 2:
                errors.append("选择题至少需要2个选项")
            if not ast.answer:
                errors.append("选择题缺少正确答案")
        
        # 验证解答题结构
        if ast.question_type in ("解答题", "证明题"):
            if not ast.answer:
                warnings.append("解答题缺少标准答案")
        
        # 验证步骤结构
        if ast.steps:
            for i, step in enumerate(ast.steps):
                if not step.get("content"):
                    warnings.append(f"步骤 {i+1} 内容为空")
                if not step.get("operation"):
                    warnings.append(f"步骤 {i+1} 缺少操作类型")
        
        # 验证知识点
        if not ast.knowledge_points:
            warnings.append("缺少知识点标记")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_errors": len(errors),
            "total_warnings": len(warnings),
        }
    
    def validate_reasoning(self, ast: Any) -> dict:
        """验证推理逻辑"""
        if not hasattr(ast, 'reasoning_dag') or ast.reasoning_dag is None:
            return {
                "valid": False,
                "errors": ["推理图未构建"],
                "warnings": [],
            }
        
        dag = ast.reasoning_dag
        
        # 检查循环依赖
        cycles = dag.find_cycles()
        if cycles:
            return {
                "valid": False,
                "errors": [f"发现 {len(cycles)} 个循环依赖"],
                "warnings": [],
            }
        
        # 检查孤立节点
        isolated_nodes = []
        for node_id, node in dag.nodes.items():
            in_edges = dag.get_edges_to(node_id)
            out_edges = dag.get_edges_from(node_id)
            if not in_edges and not out_edges:
                isolated_nodes.append(node.label)
        
        return {
            "valid": True,
            "errors": [],
            "warnings": [f"孤立节点: {', '.join(isolated_nodes)}"] if isolated_nodes else [],
            "node_count": len(dag.nodes),
            "edge_count": len(dag.edges),
        }
    
    def validate_knowledge_consistency(self, ast: Any) -> dict:
        """验证知识点一致性"""
        issues = []
        
        # 检查知识点与操作的匹配
        if ast.steps and ast.knowledge_points:
            knowledge_set = set(ast.knowledge_points)
            
            for step in ast.steps:
                op = normalize_op(step.get("operation", ""))
                
                # 操作类型与知识点的映射
                op_knowledge_map = {
                    Op.DIFFERENTIATE: {"导数", "微分", "求导"},
                    Op.INTEGRATE: {"积分", "不定积分", "定积分"},
                    Op.COMPUTE_LIMIT: {"极限", "连续"},
                    Op.EIGEN_SOLVE: {"特征值", "特征向量"},
                    Op.MATRIX_OP: {"矩阵", "线性代数"},
                    Op.QUADRATIC_FORM: {"二次型", "标准形"},
                }
                
                expected_knowledge = op_knowledge_map.get(op, set())
                if expected_knowledge and not expected_knowledge.intersection(knowledge_set):
                    issues.append(f"操作 '{op.value}' 与知识点不匹配")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "knowledge_points": ast.knowledge_points,
        }
    
    def full_validation(self, ast: Any) -> dict:
        """完整验证（结构 + 推理 + 知识点）"""
        structure = self.validate_structure(ast)
        reasoning = self.validate_reasoning(ast)
        knowledge = self.validate_knowledge_consistency(ast)
        
        all_errors = structure["errors"] + reasoning["errors"] + (knowledge["issues"] if not knowledge["valid"] else [])
        all_warnings = structure["warnings"] + reasoning["warnings"]
        
        return {
            "overall_valid": len(all_errors) == 0,
            "structure": structure,
            "reasoning": reasoning,
            "knowledge": knowledge,
            "all_errors": all_errors,
            "all_warnings": all_warnings,
            "summary": {
                "errors": len(all_errors),
                "warnings": len(all_warnings),
                "nodes": reasoning.get("node_count", 0),
                "edges": reasoning.get("edge_count", 0),
            },
        }


class ParserEnhancer:
    """解析器增强器 — 处理复杂格式"""
    
    def __init__(self):
        # 题号模式
        self._number_patterns = [
            r'^\s*\d+\.\s*',          # 1.
            r'^\s*\(\d+\)\s*',        # (1)
            r'^\s*\[\d+\]\s*',        # [1]
            r'^\s*\$\d+\$\s*',        # $1$
            r'^\s*\$\(\d+\)\$\s*',    # $(1)$
        ]
        
        # 分隔符模式
        self._separator_patterns = [
            (r'\\qquad', '\n'),
            (r'\\quad', '\n'),
            (r'\\hspace\{[^}]+\}', '\n'),
            (r'\\ ', '\n'),
        ]
    
    def clean_stem(self, text: str) -> str:
        """清理题干文本"""
        cleaned = text.strip()
        
        # 移除题号前缀
        for pattern in self._number_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # 移除分数标记
        cleaned = re.sub(r'\(本题满分\d+分\)', '', cleaned)
        cleaned = re.sub(r'\(本题满\d+分\)', '', cleaned)
        
        # 处理分隔符
        for pattern, replacement in self._separator_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        return cleaned.strip()
    
    def extract_options_enhanced(self, text: str) -> List[Dict[str, str]]:
        """增强版选项提取"""
        options = []
        
        # 预处理：替换分隔符
        processed = text
        for pattern, replacement in self._separator_patterns:
            processed = re.sub(pattern, '\n', processed)
        
        # 匹配选项的模式
        patterns = [
            # $(A)$ content
            r'(?m)^\s*\$\(\s*([A-D])\s*\)\$\s*(.+?)(?=\n\s*\$\(\s*[A-D]\s*\)\$|\Z)',
            # $(A)$ content (带空格)
            r'(?m)\$\(\s*([A-D])\s*\)\$\s*(.+?)(?=\$\(\s*[A-D]\s*\)\$|\Z)',
            # (A) content
            r'(?m)^\s*[\(（]\s*([A-D])\s*[\)）]\s*(.+?)(?=\n\s*[\(（]\s*[A-D]\s*[\)）]|\Z)',
            # A. content
            r'(?m)^\s*([A-D])\.\s*(.+?)(?=\n\s*[A-D]\.|\Z)',
            # $A$ content
            r'(?m)\$([A-D])\$\s*(.+?)(?=\$[A-D]\$|\Z)',
            # \left(A\right) content
            r'(?m)\$\\left\(\s*\\mathrm\{([A-D])\}\s*\\right\)\$\s*(.+?)(?=\$\\left\(\s*\\mathrm\{[A-D]\}\s*\\right\)\$|\Z)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, processed, re.DOTALL)
            for m in matches:
                label = m.group(1)
                content = m.group(2).strip()
                # 清理内容中的多余空格和换行
                content = re.sub(r'\s+', ' ', content).strip()
                # 移除内容开头的 $（如果是格式问题）
                if content.startswith('$') and len(content) > 1 and not content.startswith('$$'):
                    content = content[1:].strip()
                options.append({"label": label, "content": content})
        
        # 去重
        seen = set()
        deduped = []
        for opt in options:
            if opt["label"] not in seen:
                seen.add(opt["label"])
                deduped.append(opt)
        
        return deduped
    
    def parse_mixed_format(self, text: str) -> Dict[str, Any]:
        """解析混合格式的题目文本"""
        result = {
            "stem": "",
            "options": [],
            "answer": "",
            "analysis": "",
        }
        
        # 尝试提取选项
        options = self.extract_options_enhanced(text)
        
        if options:
            # 找到第一个选项的位置，之前的是题干
            first_opt_pos = text.find(f"({options[0]['label']})")
            if first_opt_pos == -1:
                first_opt_pos = text.find(f"${options[0]['label']}$")
            if first_opt_pos == -1:
                first_opt_pos = text.find(f"(${options[0]['label']})")
            
            if first_opt_pos != -1:
                result["stem"] = self.clean_stem(text[:first_opt_pos])
            else:
                result["stem"] = self.clean_stem(text)
            
            result["options"] = options
        else:
            result["stem"] = self.clean_stem(text)
        
        # 尝试提取答案
        answer_patterns = [
            r'(?:答案|正确答案|正确选项|选)\s*[：:]\s*([A-D])',
            r'(?:答案|答)\s*[：:]\s*([^\n]+)',
        ]
        
        for pattern in answer_patterns:
            m = re.search(pattern, text)
            if m:
                result["answer"] = m.group(1).strip()
                break
        
        return result
    
    def normalize_latex_enhanced(self, text: str) -> str:
        """增强版 LaTeX 规范化"""
        normalized = text
        
        # 修复破损的数学环境
        normalized = re.sub(r'\$\$', '$$', normalized)
        normalized = re.sub(r'\$\s*\$', '$$', normalized)
        
        # 修复单独的 $
        lines = normalized.split('\n')
        new_lines = []
        for line in lines:
            # 统计 $ 的数量，如果是奇数，尝试修复
            count = line.count('$')
            if count % 2 != 0:
                # 尝试在末尾添加 $
                if not line.strip().endswith('$'):
                    line += '$'
            new_lines.append(line)
        
        normalized = '\n'.join(new_lines)
        
        # 移除多余的空白
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized


# 全局实例
_semantic_enhancer = None
_parser_enhancer = None


def get_semantic_enhancer() -> SemanticEnhancer:
    """获取语义增强器实例"""
    global _semantic_enhancer
    if _semantic_enhancer is None:
        _semantic_enhancer = SemanticEnhancer()
    return _semantic_enhancer


def get_parser_enhancer() -> ParserEnhancer:
    """获取解析增强器实例"""
    global _parser_enhancer
    if _parser_enhancer is None:
        _parser_enhancer = ParserEnhancer()
    return _parser_enhancer


# 示例用法
if __name__ == "__main__":
    # 测试语义增强器
    enhancer = SemanticEnhancer()
    
    # 测试操作推断
    test_steps = [
        {"content": "对 f(x) = x^2 求导"},
        {"content": "代入 x = 2"},
        {"content": "因此，答案是 4"},
    ]
    enhanced = enhancer.enhance_solution_steps(test_steps)
    print("操作推断测试:")
    for step in enhanced:
        print(f"  {step['content']} → {step['operation']} ({step['operation_display']})")
    
    # 测试解析增强器
    parser = ParserEnhancer()
    test_text = "1. 设函数 f(x) = x^2，求 f'(2)。$(A)$ 2 $(B)$ 4 $(C)$ 6 $(D)$ 8\n答案：B"
    parsed = parser.parse_mixed_format(test_text)
    print("\n解析测试:")
    print(f"  题干: {parsed['stem']}")
    print(f"  选项: {parsed['options']}")
    print(f"  答案: {parsed['answer']}")
