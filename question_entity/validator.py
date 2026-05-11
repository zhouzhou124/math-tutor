"""
Entity Validator — 实体级合法性检查

检查项:
  - question_id 唯一性
  - content_hash 一致性
  - 答案合法性
  - math syntax 完整性
"""

import re
from .schema import (
    QuestionEntity, EntityValidationResult, EntityStatus,
    FailureMode, AlignmentResult,
)


class EntityValidator:
    """实体级验证器"""

    def validate(self, entity: QuestionEntity,
                 alignment: AlignmentResult | None = None) -> EntityValidationResult:
        """验证单个实体的合法性"""
        result = EntityValidationResult(valid=True)

        # 1. question_id 检查
        if not entity.question_id or len(entity.question_id) < 10:
            result.valid = False
            result.failure_mode = FailureMode.QUESTION_ID_CONFLICT
            result.warnings.append("question_id 无效或过短")
            result.manual_review = True

        # 2. content_hash 检查
        if not entity.content_hash:
            result.warnings.append("缺少 content_hash")
        elif entity.previous_hash and entity.previous_hash != entity.content_hash:
            result.failure_mode = FailureMode.CONTENT_DRIFT_DETECTED
            result.warnings.append(
                f"内容漂移: previous={entity.previous_hash[:12]} current={entity.content_hash[:12]}"
            )

        # 3. 题目文本检查
        if entity.stem is None or not entity.stem.clean_text:
            result.valid = False
            result.warnings.append("题目文本为空")
            result.manual_review = True
        elif len(entity.stem.clean_text) < 10:
            result.warnings.append("题目文本过短（<10字符）")
            result.manual_review = True

        # 4. 答案检查
        if entity.official_answer is None:
            result.failure_mode = FailureMode.MISSING_OFFICIAL_ANSWER
            result.warnings.append("缺少官方答案")
            # 不标记 invalid — 无答案是可接受的
        elif entity.official_answer.confidence < 0.40:
            result.failure_mode = FailureMode.LOW_ALIGNMENT_CONFIDENCE
            result.warnings.append(
                f"答案匹配置信度过低 ({entity.official_answer.confidence:.2f})"
            )
            result.manual_review = True

        # 5. 解析检查
        if entity.official_solution is None:
            result.failure_mode = FailureMode.MISSING_SOLUTION
            result.warnings.append("缺少官方解析")
            # 不标记 invalid

        # 6. 数学语法检查
        if entity.stem and entity.stem.clean_text:
            math_ok = _check_math_syntax(entity.stem.clean_text)
            if not math_ok:
                result.failure_mode = FailureMode.MATH_SYNTAX_BROKEN
                result.warnings.append("数学语法损坏（括号不配对）")
                result.manual_review = True

        # 7. 选择题选项-答案一致性
        if entity.stem and entity.stem.question_type == "选择题":
            ans = entity.official_answer.value if entity.official_answer else ""
            ans_letter = _extract_choice_letter(ans)
            option_keys = {o.key for o in entity.stem.options}
            if ans_letter and option_keys and ans_letter not in option_keys:
                result.failure_mode = FailureMode.OPTION_ANSWER_INVALID
                result.warnings.append(f"答案 {ans_letter} 不在选项 {option_keys} 中")
                result.valid = False
                result.manual_review = True

        # 8. 对齐分数
        if alignment:
            result.answer_alignment_score = alignment.overall_score
            result.solution_alignment_score = alignment.overall_score
            if alignment.overall_score < 0.50:
                result.manual_review = True

        # 9. 状态判定
        if result.manual_review:
            result.status = EntityStatus.MANUAL_REVIEW
        elif entity.status == EntityStatus.UNRESOLVED:
            result.status = EntityStatus.AUTO_MATCHED
        else:
            result.status = entity.status

        return result


def _check_math_syntax(text: str) -> bool:
    """检查数学语法（括号配对）"""
    # 花括号
    if text.count("{") != text.count("}"):
        return False
    # $ 配对
    dollars = re.findall(r'(?<!\$)\$(?!\$)', text)
    if len(dollars) % 2 != 0:
        return False
    # $$ 配对
    if text.count("$$") % 2 != 0:
        return False
    return True


def _extract_choice_letter(text: str) -> str | None:
    """从文本中提取选择题答案字母"""
    m = re.search(r'\b([A-D])\b', text.strip())
    if m:
        return m.group(1)
    m = re.search(r'[（(]([A-D])[）)]', text)
    if m:
        return m.group(1)
    return None


