"""Math Solver Agent — 生成标准解答"""

from prompts.system_prompts import SOLVER_PROMPT


class SolverAgent:
    """根据题目生成标准解答过程"""

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def solve(self, question: str, math_type: str = "数学一",
              question_type: str = "解答题",
              knowledge_point: str = "未指定") -> dict:
        """
        输入: 题目文本、类别、题型、知识点
        输出: {"success": bool, "standard_answer": str, "total_score": int, "steps": [...]}
        """
        if not self.client:
            return {
                "success": False,
                "standard_answer": "LLM 未配置，无法生成解答。请配置 API Key。",
                "total_score": 10,
                "steps": [],
            }

        system = SOLVER_PROMPT.format(
            math_type=math_type,
            question_type=question_type,
            knowledge_point=knowledge_point,
            question=question,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"请生成这道{math_type}{question_type}的标准解答。"},
                ],
                temperature=0.2,
                max_tokens=4096,
            )
            text = response.choices[0].message.content

            # 简单解析：提取总分
            total_score = 10  # 默认
            import re
            score_matches = re.findall(r"【(\d+)分】", text)
            if score_matches:
                total_score = sum(int(s) for s in score_matches)

            return {
                "success": True,
                "standard_answer": text,
                "total_score": total_score,
                "steps": self._parse_steps(text),
            }
        except UnicodeEncodeError:
            return {
                "success": False,
                "standard_answer": "系统编码错误，请重试",
                "total_score": 10, "steps": [],
                "_error_type": "system_encoding",
            }
        except Exception:
            return {
                "success": False,
                "standard_answer": "解答生成暂不可用，请使用题库缓存答案",
                "total_score": 10, "steps": [],
                "_error_type": "system_internal",
            }

    def _parse_steps(self, text: str) -> list:
        """从解答中解析步骤列表"""
        import re
        steps = []
        pattern = r"###\s*步骤[一二三四五六七八九十\d]+(?:【(\d+)分】)?\s*\n(.*?)(?=###\s*步骤|###\s*最终答案|\Z)"
        for match in re.finditer(pattern, text, re.DOTALL):
            score = int(match.group(1)) if match.group(1) else 0
            content = match.group(2).strip()
            steps.append({"score": score, "content": content[:200]})
        return steps
