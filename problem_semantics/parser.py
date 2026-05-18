from __future__ import annotations
import re
from typing import Optional, Tuple, List, Dict


# 从 semantic_types 导入类型，避免循环导入
from .semantic_types import (
    QuestionIntent, TopicTag, ObjectType, ReasoningMode,
    ProblemSchema, Constraint, Proposition
)


class ProblemSemanticParser:
    """
    问题语义解析器 — 将题目文本转换为 ProblemSchema。
    
    核心功能：
      1. 识别数学对象（数列、函数、矩阵等）
      2. 提取约束条件
      3. 确定问题意图（命题判断、极限计算、证明等）
      4. 推荐推理模式
    
    解析流程：
      Raw Text → Object Detection → Constraint Extraction → Intent Classification → ProblemSchema
    """
    
    def __init__(self):
        # 使用简单的关键词匹配而非正则表达式，避免转义问题
        self._object_keywords = {
            ObjectType.SEQUENCE: [
                'x_n', 'a_n', 'b_n', '数列',
                '{x_n}', '{a_n}', '{b_n}',
                'x_{n}', 'a_{n}', 'b_{n}',
            ],
            ObjectType.FUNCTION: [
                'f(', 'g(', 'h(', 'f (', 'g (', 'h (',
                'sin(', 'cos(', 'tan(',
                'sin (', 'cos (', 'tan (',
                'lim ', 'lim_',
            ],
            ObjectType.MATRIX: [
                'A=', 'B=', '矩阵',
                '\\begin{matrix}', '\\begin{pmatrix}',
                '\\begin{bmatrix}', '\\begin{vmatrix}',
                '\\begin{array}',
            ],
            ObjectType.EQUATION: [
                '方程',
            ],
            ObjectType.INEQUALITY: [
                '\\geq', '\\le', '\\leq', '\\neq',
                '≥', '≤', '≠',
            ],
            ObjectType.PROPOSITION: [
                '命题', '正确', '错误',
                '成立', '不成立',
                '可推出', '不能推出',
            ],
        }
        
        self._intent_keywords = {
            QuestionIntent.PROPOSITION_JUDGEMENT: [
                '命题', '正确', '错误', '成立', '不成立',
                '可推出', '不能推出', '等价', '充要',
                '必要', '充分', '条件',
            ],
            QuestionIntent.LIMIT_COMPUTATION: [
                '求极限', '计算极限', '极限值',
                '求极限值',
            ],
            QuestionIntent.LIMIT_EXISTENCE: [
                '极限存在', '极限不存在',
                '是否收敛', '收敛性',
            ],
            QuestionIntent.SEQUENCE_LIMIT: [
                '数列极限', '求数列', '递推',
                '通项', '单调有界',
            ],
            QuestionIntent.SEQUENCE_MONOTONICITY: [
                '单调', '递增', '递减',
                '单调性',
            ],
            QuestionIntent.FUNCTION_CONTINUITY: [
                '连续', '连续性', '间断点',
            ],
            QuestionIntent.PROOF_DIRECT: [
                '证明', '求证', '证明题',
                '证明成立', '证明结论',
            ],
            QuestionIntent.COUNTEREXAMPLE: [
                '反例', '构造反例', '举出反例',
            ],
            QuestionIntent.INEQUALITY_PROOF: [
                '证明不等式', '不等式证明',
            ],
        }
        
        self._topic_keywords = {
            TopicTag.LIMIT: ['极限', '\\lim', '收敛', '趋于'],
            TopicTag.CONTINUITY: ['连续', '连续性', '间断'],
            TopicTag.MONOTONICITY: ['单调', '递增', '递减'],
            TopicTag.SEQUENCE: ['数列', 'x_n', 'a_n'],
            TopicTag.FUNCTION: ['函数', 'f(', 'g('],
            TopicTag.COMPOSITE_FUNCTION: ['复合函数', 'f(g(', 'g(f('],
            TopicTag.INVERSE_FUNCTION: ['反函数', '逆函数'],
            TopicTag.TRIGONOMETRIC: ['sin', 'cos', 'tan'],
            TopicTag.PROPOSITION: ['命题', '逻辑', '蕴含'],
            TopicTag.MATRIX: ['矩阵', '行列式', '秩'],
        }
    
    def parse(self, text: str) -> ProblemSchema:
        """
        主入口：将题目文本解析为 ProblemSchema。
        
        Args:
            text: 题目文本（包含 LaTeX）
        
        Returns:
            ProblemSchema: 问题语义结构
        """
        if not text or not isinstance(text, str):
            return ProblemSchema(confidence=0.0)
        
        text = self._normalize_text(text)
        
        objects = self._detect_objects(text)
        constraints = self._extract_constraints(text)
        intent = self._classify_intent(text, objects, constraints)
        topics = self._detect_topics(text)
        reasoning_mode = self._determine_reasoning_mode(intent, topics)
        
        confidence = self._calculate_confidence(intent, objects, constraints)
        
        return ProblemSchema(
            question_type=intent,
            objects=tuple(objects),
            constraints=tuple(constraints),
            topics=tuple(topics),
            reasoning_mode=reasoning_mode,
            confidence=confidence,
        )
    
    def _normalize_text(self, text: str) -> str:
        """标准化文本格式"""
        text = text.replace('≤', '\\le').replace('≥', '\\ge')
        text = text.replace('π', '\\pi').replace('∈', '\\in')
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _detect_objects(self, text: str) -> List[Tuple[str, ObjectType]]:
        """识别文本中的数学对象"""
        objects = []
        seen = set()
        
        for obj_type, keywords in self._object_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    if keyword not in seen:
                        seen.add(keyword)
                        objects.append((keyword, obj_type))
        
        return objects
    
    def _extract_constraints(self, text: str) -> List[str]:
        """提取约束条件"""
        constraints = []
        
        # 提取区间约束
        interval_patterns = [
            r'([a-zA-Z_]+)\s*∈\s*\[([^\]]+)\]',
            r'([a-zA-Z_]+)\s*∈\s*\(([^)]+)\)',
        ]
        
        for pattern in interval_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    var, bound = match
                    constraints.append(f"{var} ∈ [{bound}]")
                else:
                    constraints.append(match)
        
        # 提取不等式约束
        inequality_keywords = ['≥', '≤', '>', '<', '\\ge', '\\le', '\\geq', '\\leq']
        for keyword in inequality_keywords:
            if keyword in text:
                # 简单提取包含不等式的片段
                parts = text.split(keyword)
                if len(parts) >= 2:
                    left = parts[0][-20:].strip() if len(parts[0]) > 20 else parts[0].strip()
                    right = parts[1][:20].strip() if len(parts[1]) > 20 else parts[1].strip()
                    constraints.append(f"{left} {keyword} {right}")
        
        return list(set(constraints))  # 去重
    
    def _classify_intent(self, text: str, objects: List, constraints: List) -> QuestionIntent:
        """
        分类题目意图。
        
        优先级：命题判断 > 证明 > 极限存在性 > 极限计算 > 数列极限
        """
        intent_scores = {}
        
        for intent, keywords in self._intent_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return self._infer_intent_from_context(text, objects, constraints)
        
        max_score = max(intent_scores.values())
        top_intents = [intent for intent, score in intent_scores.items() if score == max_score]
        
        return self._resolve_intent_conflict(top_intents, text, objects)
    
    def _infer_intent_from_context(self, text: str, objects: List, constraints: List) -> QuestionIntent:
        """从上下文推断意图"""
        has_proposition = any(obj_type == ObjectType.PROPOSITION for _, obj_type in objects)
        has_sequence = any(obj_type == ObjectType.SEQUENCE for _, obj_type in objects)
        has_limit = '\\lim' in text or '极限' in text
        
        if has_proposition or '命题' in text:
            return QuestionIntent.PROPOSITION_JUDGEMENT
        
        if has_limit:
            if '是否' in text or '存在' in text:
                return QuestionIntent.LIMIT_EXISTENCE
            elif has_sequence:
                return QuestionIntent.SEQUENCE_LIMIT
            else:
                return QuestionIntent.LIMIT_COMPUTATION
        
        if '证明' in text:
            return QuestionIntent.PROOF_DIRECT
        
        return QuestionIntent.UNKNOWN
    
    def _resolve_intent_conflict(self, intents: List[QuestionIntent], text: str, objects: List) -> QuestionIntent:
        """解决意图冲突"""
        has_proposition = QuestionIntent.PROPOSITION_JUDGEMENT in intents
        has_proof = QuestionIntent.PROOF_DIRECT in intents
        has_limit = any(i in [QuestionIntent.LIMIT_COMPUTATION, QuestionIntent.SEQUENCE_LIMIT] for i in intents)
        
        if has_proposition:
            if '证明' in text or has_proof:
                return QuestionIntent.PROOF_DIRECT
            return QuestionIntent.PROPOSITION_JUDGEMENT
        
        if has_proof:
            return QuestionIntent.PROOF_DIRECT
        
        return intents[0]
    
    def _detect_topics(self, text: str) -> List[TopicTag]:
        """识别知识点"""
        topics = []
        seen = set()
        
        for topic, keywords in self._topic_keywords.items():
            if any(kw in text for kw in keywords):
                if topic not in seen:
                    seen.add(topic)
                    topics.append(topic)
        
        return topics
    
    def _determine_reasoning_mode(self, intent: QuestionIntent, topics: List[TopicTag]) -> ReasoningMode:
        """确定推荐的推理模式"""
        if intent.requires_proof:
            if TopicTag.MONOTONICITY in topics:
                return ReasoningMode.MONOTONICITY_ANALYSIS
            if TopicTag.CONTINUITY in topics:
                return ReasoningMode.CONTINUITY_ANALYSIS
            if TopicTag.INVERSE_FUNCTION in topics:
                return ReasoningMode.INVERTIBILITY_ANALYSIS
            if any('反证' in t.name for t in topics):
                return ReasoningMode.REDUCTIO_AD_ABSURDUM
            return ReasoningMode.DEFINITION_APPLICATION
        
        if intent.requires_computation:
            return ReasoningMode.DIRECT_CALCULATION
        
        return ReasoningMode.DIRECT_CALCULATION
    
    def _calculate_confidence(self, intent: QuestionIntent, objects: List, constraints: List) -> float:
        """计算解析置信度"""
        score = 0.0
        
        if intent != QuestionIntent.UNKNOWN:
            score += 0.3
        
        if objects:
            score += min(0.3, len(objects) * 0.1)
        
        if constraints:
            score += min(0.2, len(constraints) * 0.1)
        
        if intent.requires_proof and any(obj_type == ObjectType.PROPOSITION for _, obj_type in objects):
            score += 0.2
        
        return min(1.0, score)


def parse_problem(text: str) -> ProblemSchema:
    """便捷函数：解析题目文本"""
    parser = ProblemSemanticParser()
    return parser.parse(text)


if __name__ == "__main__":
    test_cases = [
        """设数列{x_n}满足 -\\frac{\\pi}{2}\\le x_n\\le \\frac{\\pi}{2}，
        则下列命题正确的是：
        A. 若 lim cos(sin x_n) 存在，则 lim x_n 存在
        B. 若 lim sin(cos x_n) 存在，则 lim x_n 存在""",
        
        """求极限：lim_{n→∞} \\frac{n^2 + 1}{2n^2 - n}""",
        
        """证明：若函数 f(x) 在 x=0 处连续，且 f(x+y) = f(x) + f(y)，则 f(x) = kx""",
    ]
    
    for i, case in enumerate(test_cases):
        schema = parse_problem(case)
        print(f"=== Test Case {i+1} ===")
        print(f"Question Type: {schema.question_type.name}")
        print(f"Objects: {[(name, obj_type.name) for name, obj_type in schema.objects]}")
        print(f"Constraints: {schema.constraints}")
        print(f"Topics: {[t.name for t in schema.topics]}")
        print(f"Reasoning Mode: {schema.reasoning_mode.name}")
        print(f"Confidence: {schema.confidence:.2f}")
        print()
