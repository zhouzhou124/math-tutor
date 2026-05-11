"""
Alignment Validator — 多阶段答案-解析-题目对齐验证

验证维度:
  numbering_score:  题号一致性
  formula_score:    公式一致性
  keyword_score:    关键词一致性
  structure_score:  结构一致性（选项/填空）
  option_score:     选项合法性（选择题专用）
  semantic_score:   语义整体一致性

低于阈值 → MANUAL_REVIEW
"""

import re
from difflib import SequenceMatcher
from .schema import (
    QuestionEntity, AlignmentResult, EntityStatus, FailureMode,
)


class AlignmentValidator:
    """多阶段对齐验证器"""

    # 阈值配置
    MIN_OVERALL_SCORE = 0.50      # 低于此值 → manual_review
    MIN_OPTION_SCORE = 0.60       # 选择题选项合法性
    MIN_FORMULA_OVERLAP = 0.30    # 公式最低重叠率

    def validate(self, entity: QuestionEntity) -> AlignmentResult:
        """对题目实体进行多阶段对齐验证"""
        result = AlignmentResult()
        question_text = entity.stem.clean_text if entity.stem else ""

        if not question_text:
            result.details.append("题目文本为空")
            result.overall_score = 0.0
            return result

        answer_text = entity.official_answer.value if entity.official_answer else ""
        solution_text = entity.official_solution.steps_markdown if entity.official_solution else ""

        # 1. 公式一致性
        result.formula_score = self._formula_consistency(question_text, answer_text, solution_text)

        # 2. 关键词一致性
        result.keyword_score = self._keyword_consistency(question_text, answer_text, solution_text)

        # 3. 结构一致性
        result.structure_score = self._structure_consistency(entity)

        # 4. 选项合法性（选择题）
        if entity.stem and entity.stem.question_type == "选择题":
            result.option_score = self._option_validity(entity)
        else:
            result.option_score = 1.0

        # 5. 语义整体一致性
        result.semantic_score = self._semantic_consistency(question_text, answer_text)

        # 6. 综合分数
        scores = [
            result.formula_score,
            result.keyword_score,
            result.structure_score,
            result.option_score,
            result.semantic_score,
        ]
        result.overall_score = sum(scores) / len(scores)

        # 诊断信息
        if result.overall_score < self.MIN_OVERALL_SCORE:
            result.details.append(
                f"综合分数 {result.overall_score:.2f} < {self.MIN_OVERALL_SCORE}"
            )
        if result.option_score < self.MIN_OPTION_SCORE:
            result.details.append(f"选项合法性低 ({result.option_score:.2f})")
        if result.formula_score < self.MIN_FORMULA_OVERLAP:
            result.details.append(f"公式重叠率低 ({result.formula_score:.2f})")

        return result

    def _formula_consistency(self, question: str, answer: str, solution: str) -> float:
        """检查公式一致性：题目中的公式是否在答案/解析中出现"""
        q_formulas = set(_extract_formulas(question))
        a_formulas = set(_extract_formulas(answer))
        s_formulas = set(_extract_formulas(solution))
        target = a_formulas | s_formulas

        if not q_formulas:
            return 0.8  # 无公式题目（如纯文字题）

        overlap = len(q_formulas & target)
        return min(1.0, overlap / max(len(q_formulas), 1))

    def _keyword_consistency(self, question: str, answer: str, solution: str) -> float:
        """检查关键词一致性"""
        q_keywords = _extract_math_keywords(question)
        target_text = answer + " " + solution
        if not q_keywords:
            return 0.8
        matched = sum(1 for kw in q_keywords if kw in target_text)
        return matched / max(len(q_keywords), 1)

    def _structure_consistency(self, entity: QuestionEntity) -> float:
        """检查结构一致性：题型、选项格式等"""
        score = 1.0
        if entity.stem is None:
            return 0.0

        qtype = entity.stem.question_type

        # 选择题：必须至少有2个选项
        if qtype == "选择题":
            if len(entity.stem.options) < 2:
                score *= 0.5
                return score
            # 答案必须是 A-D
            ans = entity.official_answer.value if entity.official_answer else ""
            ans_letter = _extract_choice_letter(ans)
            if ans_letter and ans_letter not in "ABCD":
                score *= 0.6

        # 填空题：答案不应为空
        if qtype == "填空题":
            ans = entity.official_answer.value if entity.official_answer else ""
            if not ans or len(ans.strip()) < 1:
                score *= 0.7

        return score

    def _option_validity(self, entity: QuestionEntity) -> float:
        """检查选择题选项合法性"""
        if not entity.stem or not entity.stem.options:
            return 0.0

        options = entity.stem.options
        # 检查是否有 A/B/C/D 四个选项
        keys = {o.key for o in options}
        expected = {"A", "B", "C", "D"}
        missing = expected - keys
        if missing:
            return 0.5 - (len(missing) * 0.15)

        # 检查答案是否在选项中
        ans = entity.official_answer.value if entity.official_answer else ""
        ans_letter = _extract_choice_letter(ans)
        if ans_letter and ans_letter not in keys:
            return 0.3  # 答案不在选项中 → 严重问题

        return 1.0

    def _semantic_consistency(self, question: str, answer: str) -> float:
        """语义整体一致性（文本相似度作为最后一道防线）"""
        if not answer or not question:
            return 0.5
        # 简单文本相似度（不作为主力，仅兜底）
        q_short = question[:300]
        a_short = answer[:300]
        return SequenceMatcher(None, q_short, a_short).ratio()

    def get_failure_mode(self, result: AlignmentResult) -> FailureMode | None:
        """根据对齐结果判断失败模式"""
        if result.overall_score < 0.30:
            return FailureMode.ANSWER_QUESTION_MISMATCH
        if result.option_score < 0.50:
            return FailureMode.OPTION_ANSWER_INVALID
        if result.formula_score < 0.20:
            return FailureMode.SOLUTION_QUESTION_MISMATCH
        if result.overall_score < self.MIN_OVERALL_SCORE:
            return FailureMode.LOW_ALIGNMENT_CONFIDENCE
        return None


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════

def _extract_formulas(text: str) -> list[str]:
    """提取 LaTeX 公式"""
    formulas = []
    for m in re.finditer(r'\$\$?(.+?)\$\$?', text, re.DOTALL):
        f = m.group(1).strip()
        # 规范化
        f = re.sub(r'\s+', ' ', f)
        formulas.append(f)
    return formulas


def _extract_math_keywords(text: str) -> list[str]:
    """提取数学关键词"""
    keywords = [
        "极限", "导数", "微分", "积分", "级数", "矩阵", "行列式",
        "概率", "随机变量", "特征值", "二次型", "方程", "函数",
        "收敛", "发散", "连续", "可导", "极值",
    ]
    return [kw for kw in keywords if kw in text]


def _extract_choice_letter(text: str) -> str | None:
    """从文本中提取选择题答案字母"""
    m = re.search(r'\b([A-D])\b', text.strip())
    if m:
        return m.group(1)
    m = re.search(r'[（(]([A-D])[）)]', text)
    if m:
        return m.group(1)
    return None
