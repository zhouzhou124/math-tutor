"""Grading Agent — 按考研标准批改评分"""

from prompts.system_prompts import GRADING_PROMPT
from config import GRADING_RULES


class GradingAgent:
    """对照标准答案批改学生作答，给出分数和扣分点"""

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def grade(self, question: str, standard_answer: str,
              student_answer: str, total_score: int = 10,
              knowledge_points: str = "", difficulty: str = "中等") -> dict:
        """
        输入: 题目、标准答案、学生作答、满分值
        输出: {"success": bool, "total": float, "step_score": float,
                "result_score": float, "step_analysis": [...],
                "deductions": [...], "comment": str}
        """
        if not self.client:
            return {
                "success": False,
                "total": 0,
                "step_score": 0,
                "result_score": 0,
                "step_analysis": [],
                "deductions": [],
                "comment": "LLM 未配置，无法批改。",
            }

        # 按满分值调整评分参数
        step_total = round(total_score * 0.7, 1)
        result_total = round(total_score * 0.3, 1)

        system = GRADING_PROMPT.format(
            question=question,
            standard_answer=standard_answer,
            student_answer=student_answer if student_answer else "（学生未作答）",
            grading_rules=GRADING_RULES,
            knowledge_points=knowledge_points or "未指定",
            difficulty=difficulty,
            step_total=step_total,
            result_total=result_total,
            total=total_score,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": "请批改这位学生的作答。"},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            text = response.choices[0].message.content
            return self._parse_grading_result(text, total_score)
        except UnicodeEncodeError:
            return {
                "success": False, "total": 0, "step_score": 0, "result_score": 0,
                "step_analysis": [], "deductions": [],
                "comment": "系统编码错误，请重试",
                "_error_type": "system_encoding",
            }
        except Exception:
            return {
                "success": False, "total": 0, "step_score": 0, "result_score": 0,
                "step_analysis": [], "deductions": [],
                "comment": "批改服务暂时不可用，请重试",
                "_error_type": "system_internal",
            }

    def _parse_grading_result(self, text: str, total: int) -> dict:
        """解析批改结果文本"""
        import re

        # 提取总分
        total_match = re.search(r"总分.*?(\d+\.?\d*)\s*/\s*(\d+)", text)
        score = float(total_match.group(1)) if total_match else 0

        step_match = re.search(r"步骤分.*?(\d+\.?\d*)\s*/\s*(\d+\.?\d*)", text)
        step_score = float(step_match.group(1)) if step_match else 0

        result_match = re.search(r"结果分.*?(\d+\.?\d*)\s*/\s*(\d+\.?\d*)", text)
        result_score = float(result_match.group(1)) if result_match else 0

        # 提取步骤分析
        steps = []
        step_pattern = r"###\s*步骤(\d+)[：:]\s*(.*?)\n- 判断[：:]\s*(.*?)\n- 得分[：:]\s*(.*?)\n- 评语[：:]\s*(.*?)(?=\n###\s*步骤|\n##|\Z)"
        for m in re.finditer(step_pattern, text, re.DOTALL):
            steps.append({
                "num": m.group(1),
                "content": m.group(2).strip(),
                "judgment": m.group(3).strip(),
                "score": m.group(4).strip(),
                "comment": m.group(5).strip(),
            })

        # 提取扣分汇总
        deductions = []
        ded_pattern = r"扣分项\d+[：:]\s*(.*?)[，,]\s*类型[：:]\s*(.*?)[，,]\s*扣(\d+\.?\d*)分"
        for m in re.finditer(ded_pattern, text):
            deductions.append({
                "item": m.group(1).strip(),
                "type": m.group(2).strip(),
                "points": float(m.group(3)),
            })

        # 提取整体评价
        comment_match = re.search(r"##\s*整体评价\s*\n(.*?)$", text, re.DOTALL)
        comment = comment_match.group(1).strip() if comment_match else ""

        return {
            "success": True,
            "total": score,
            "step_score": step_score,
            "result_score": result_score,
            "step_analysis": steps,
            "deductions": deductions,
            "comment": comment,
            "raw": text,
        }
