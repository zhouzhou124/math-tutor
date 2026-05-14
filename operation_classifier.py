"""operation_classifier.py — Operation Classifier (Phase 1)

LLM + 规则混合分类器，用于识别解题步骤的操作类型。
"""
import re
from typing import Optional
from operations import Op, KEYWORD_PATTERNS, normalize_op


class OperationClassifier:
    """操作类型分类器：规则 + LLM 混合策略"""
    
    def __init__(self, llm_client=None):
        """
        初始化分类器
        
        Args:
            llm_client: LLM客户端（可选），如果未提供则只使用规则
        """
        self.llm_client = llm_client
        self._build_pattern_cache()
    
    def _build_pattern_cache(self):
        """构建正则表达式缓存，提升性能"""
        self.compiled_patterns = []
        for pattern, op in KEYWORD_PATTERNS:
            try:
                compiled = re.compile(pattern)
                self.compiled_patterns.append((compiled, op))
            except re.error:
                pass
    
    def classify(self, step_content: str, use_llm: bool = True) -> Op:
        """
        分类步骤内容的操作类型
        
        Args:
            step_content: 步骤文本内容
            use_llm: 是否使用LLM（规则未命中时）
        
        Returns:
            操作类型枚举
        """
        if not step_content:
            return Op.COMPUTE
        
        # 第一阶段：规则匹配（快速）
        rule_result = self._classify_by_rules(step_content)
        if rule_result != Op.COMPUTE:
            return rule_result
        
        # 第二阶段：LLM分类（规则未命中）
        if use_llm and self.llm_client:
            return self._classify_by_llm(step_content)
        
        # 降级：返回通用计算
        return Op.COMPUTE
    
    def _classify_by_rules(self, text: str) -> Op:
        """
        基于规则的操作分类
        
        策略：
        1. 特殊上下文判断（优先级最高）
        2. 关键词匹配
        3. 符号模式匹配
        4. 上下文推断
        """
        # 0. 特殊上下文判断（优先级最高）
        # "求解：f'(x) = 0" 应该是 solve_equation 而不是 differentiate
        if re.search(r'求解.*[:：=].*=', text) or re.search(r'求.*[:：=].*=', text):
            # 检查是否是求解方程
            if '=' in text and ('f\'' in text or 'y\'' in text or 'dy/dx' in text):
                return Op.SOLVE_EQUATION
        
        # 1. 关键词匹配
        for pattern, op in self.compiled_patterns:
            if pattern.search(text):
                return op
        
        # 2. 特殊符号模式
        if "∫" in text or "\\int" in text:
            return Op.INTEGRATE
        if "lim" in text or "\\lim" in text:
            return Op.COMPUTE_LIMIT
        if "∑" in text or "\\sum" in text:
            return Op.SUM_SERIES
        if "∏" in text or "\\prod" in text:
            return Op.SUM_SERIES
        
        # 3. 数学表达式模式
        if self._has_derivative_pattern(text):
            return Op.DIFFERENTIATE
        if self._has_integral_pattern(text):
            return Op.INTEGRATE
        if self._has_limit_pattern(text):
            return Op.COMPUTE_LIMIT
        
        return Op.COMPUTE
    
    def _has_derivative_pattern(self, text: str) -> bool:
        """检测求导模式"""
        patterns = [
            r"f'\(|f''\(|y'\(|y''\(",
            r"\\frac{d}{dx}",
            r"\\frac{\\partial}{\\partial}",
            r"求导|导数|微分|偏导",
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _has_integral_pattern(self, text: str) -> bool:
        """检测积分模式"""
        patterns = [
            r"\\int_?\^?\{.*?\}",
            r"不定积分|定积分|反常积分",
            r"分部积分|换元积分",
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _has_limit_pattern(self, text: str) -> bool:
        """检测极限模式"""
        patterns = [
            r"\\lim_?\{.*?\\to.*?\}",
            r"极限|趋近|收敛",
        ]
        return any(re.search(p, text) for p in patterns)
    
    def _classify_by_llm(self, text: str) -> Op:
        """
        基于LLM的操作分类
        
        当规则无法确定时，使用LLM进行语义理解
        """
        if not self.llm_client:
            return Op.COMPUTE
        
        # 构建提示词
        prompt = self._build_llm_prompt(text)
        
        try:
            response = self.llm_client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个数学解题步骤分析专家。你的任务是识别解题步骤的操作类型。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=50,
            )
            
            result = response.choices[0].message.content.strip()
            # 规范化结果
            return normalize_op(result)
        except Exception as e:
            # LLM失败，降级到规则
            return self._classify_by_rules(text)
    
    def _build_llm_prompt(self, text: str) -> str:
        """构建LLM分类提示词"""
        # 获取所有可用的操作类型
        available_ops = [op.value for op in Op]
        
        prompt = f"""请判断以下解题步骤的操作类型：

步骤内容：{text}

可选操作类型：
{', '.join(available_ops[:20])}  # 只显示前20个，避免过长

请只返回操作类型的英文名称（如 differentiate, integrate, simplify 等）。
"""
        return prompt
    
    def classify_batch(self, steps: list[str], use_llm: bool = True) -> list[Op]:
        """
        批量分类多个步骤
        
        Args:
            steps: 步骤内容列表
            use_llm: 是否使用LLM
        
        Returns:
            操作类型列表
        """
        return [self.classify(step, use_llm) for step in steps]
    
    def get_operation_description(self, op: Op) -> str:
        """获取操作类型的中文描述"""
        descriptions = {
            Op.DIFFERENTIATE: "求导",
            Op.PARTIAL_DIFF: "偏导数",
            Op.INTEGRATE: "积分",
            Op.COMPUTE_LIMIT: "求极限",
            Op.EXPAND: "展开",
            Op.FACTOR: "因式分解",
            Op.SIMPLIFY: "化简",
            Op.SUBSTITUTE: "代入",
            Op.COLLECT: "合并同类项",
            Op.CANCEL: "约分",
            Op.SOLVE_EQUATION: "解方程",
            Op.SOLVE_SYSTEM: "解方程组",
            Op.SOLVE_INEQUALITY: "解不等式",
            Op.MATRIX_OP: "矩阵运算",
            Op.ROW_REDUCE: "行变换",
            Op.EIGEN_SOLVE: "特征值求解",
            Op.DETERMINANT: "行列式",
            Op.ORTHOGONALIZE: "正交化",
            Op.QUADRATIC_FORM: "二次型",
            Op.EXPAND_SERIES: "级数展开",
            Op.SUM_SERIES: "级数求和",
            Op.CONVERGENCE_TEST: "收敛性判断",
            Op.PROBABILITY_CALC: "概率计算",
            Op.EXPECTATION: "期望/方差计算",
            Op.MLE_DERIVE: "极大似然估计",
            Op.MOMENT_ESTIMATE: "矩估计",
            Op.HYPOTHESIS_TEST: "假设检验",
            Op.APPLY_THEOREM: "应用定理",
            Op.CLASSIFY: "分类讨论",
            Op.INDUCTION_STEP: "数学归纳法",
            Op.CONTRADICTION: "反证法",
            Op.COMPUTE: "计算",
            Op.DEFINE: "定义",
            Op.FINAL_ANSWER: "最终答案",
            Op.CROSS_PRODUCT: "叉积",
            Op.DOT_PRODUCT: "点积",
            Op.NORM: "范数",
        }
        return descriptions.get(op, op.value)


# 单例模式，避免重复初始化
_classifier_instance: Optional[OperationClassifier] = None


def get_classifier(llm_client=None) -> OperationClassifier:
    """获取分类器单例"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = OperationClassifier(llm_client)
    return _classifier_instance


def classify_step(step_content: str, use_llm: bool = True) -> Op:
    """便捷函数：分类单个步骤"""
    classifier = get_classifier()
    return classifier.classify(step_content, use_llm)