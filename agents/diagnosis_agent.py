"""Diagnosis Agent — 错因分析和薄弱点诊断"""

from prompts.system_prompts import DIAGNOSIS_PROMPT


class DiagnosisAgent:
    """分析学生错误类型、根本原因、与历史的关联"""

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def diagnose(self, question: str, student_answer: str,
                 standard_answer: str, grading_result: dict,
                 error_history: list = None) -> dict:
        """
        输入: 题目、学生作答、标准答案、评分结果、该知识点历史错题
        输出: {"error_type": str, "root_cause": str, "is_repeat": bool,
                "affects_future": bool, "weak_points": [...]}
        """
        if error_history is None:
            error_history = []

        history_text = "无历史记录"
        if error_history:
            history_items = []
            for h in error_history[-5:]:  # 最近5条
                history_items.append(
                    f"- {h.get('date', '?')} | 得分{h.get('score', '?')}/{h.get('total', '?')} "
                    f"| 错误类型: {h.get('error_type', '?')}"
                )
            history_text = "\n".join(history_items)

        if not self.client:
            return self._local_diagnose(grading_result, error_history)

        system = DIAGNOSIS_PROMPT.format(
            question=question,
            student_answer=student_answer,
            standard_answer=standard_answer,
            grading_result=str(grading_result),
            error_history=history_text,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": "请分析这位学生的错误原因。"},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            text = response.choices[0].message.content
            return self._parse_diagnosis(text, error_history)
        except Exception:
            return self._local_diagnose(grading_result, error_history)

    def _parse_diagnosis(self, text: str, history: list) -> dict:
        import re

        type_match = re.search(r"##\s*错误类型\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
        error_type = type_match.group(1).strip() if type_match else "未识别"

        cause_match = re.search(r"##\s*根本原因\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
        root_cause = cause_match.group(1).strip() if cause_match else ""

        repeat_match = re.search(r"##\s*是否高频错误\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
        repeat_text = repeat_match.group(1).strip() if repeat_match else ""
        is_repeat = "是" in repeat_text or "高频" in repeat_text or len(history) >= 2

        weak_match = re.search(r"##\s*薄弱知识点\s*\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
        weak_text = weak_match.group(1).strip() if weak_match else ""
        weak_points = [w.strip("- ") for w in weak_text.split("\n") if w.strip()]

        return {
            "error_type": error_type,
            "root_cause": root_cause,
            "is_repeat": is_repeat,
            "repeat_count": len(history),
            "affects_future": "影响" in text and "后续" in text,
            "weak_points": weak_points,
            "raw": text,
        }

    def _local_diagnose(self, grading_result: dict, history: list) -> dict:
        """无 LLM 时的本地诊断"""
        deductions = grading_result.get("deductions", [])
        if not deductions:
            return {
                "error_type": "无明显错误",
                "root_cause": "",
                "is_repeat": False,
                "repeat_count": len(history),
                "affects_future": False,
                "weak_points": [],
                "raw": "",
            }

        # 汇总扣分类型（兼容 dict 和 str 两种格式）
        types = []
        for d in deductions:
            if isinstance(d, dict):
                types.append(d.get("type", "未分类"))
            elif isinstance(d, str):
                types.append(d[:20])  # 截取前20字符作为类型摘要
        main_type = max(set(types), key=types.count) if types else "未分类"

        return {
            "error_type": main_type,
            "root_cause": f"该题扣{grading_result.get('total', 0)}分，主要扣分类型：{main_type}",
            "is_repeat": len(history) >= 2,
            "repeat_count": len(history),
            "affects_future": False,
            "weak_points": types,
            "raw": "",
        }
