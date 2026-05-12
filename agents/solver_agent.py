"""Math Solver Agent — 生成标准解答"""

import json as _json
import re as _re

from prompts.system_prompts import SOLVER_PROMPT, CANONICAL_SOLVE_PROMPT


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

            # 规范化 LaTeX（修复 $$$ 等破损分隔符，再解析步骤）
            try:
                from latex_normalizer import normalize_latex_style
                text = normalize_latex_style(text)
            except Exception:
                pass

            # 简单解析：提取总分
            total_score = 10  # 默认
            score_matches = _re.findall(r"【(\d+)分】", text)
            if score_matches:
                total_score = sum(int(s) for s in score_matches)

            steps, knowledge_points, common_mistakes = self._parse_steps(text)
            return {
                "success": True,
                "standard_answer": text,
                "total_score": total_score,
                "steps": steps,
                "knowledge_points": knowledge_points,
                "common_mistakes": common_mistakes,
            }
        except UnicodeEncodeError:
            return {
                "success": False,
                "standard_answer": "系统编码错误，请重试",
                "total_score": 10, "steps": [],
                "_error_type": "system_encoding",
            }
        except Exception as e:
            return {
                "success": False,
                "standard_answer": f"解答生成失败: {type(e).__name__}: {e}",
                "total_score": 10, "steps": [],
                "_error_type": "system_internal",
            }

    def _parse_steps(self, text: str) -> tuple:
        """从解答中解析步骤列表、知识点、常见错误"""
        steps = []
        pattern = r"###\s*步骤[一二三四五六七八九十\d]+(?:【(\d+)分】)?\s*\n(.*?)(?=###\s*步骤|###\s*最终答案|##\s*涉及知识|##\s*常见错误|\Z)"
        for match in _re.finditer(pattern, text, _re.DOTALL):
            score = int(match.group(1)) if match.group(1) else 0
            content = match.group(2).strip()
            steps.append({"score": score, "content": content})
        knowledge_points = self._extract_list(text, r"##\s*涉及知识点\s*\n(.*?)(?=##\s*常见错误|\Z)")
        common_mistakes = self._extract_list(text, r"##\s*常见错误提醒\s*\n(.*?)(?=##|\Z)")
        return steps, knowledge_points, common_mistakes

    @staticmethod
    def _extract_list(text: str, pattern: str) -> list:
        """从正则匹配的区块中提取列表项"""
        m = _re.search(pattern, text, _re.DOTALL)
        if not m:
            return []
        block = m.group(1).strip()
        items = []
        for line in block.split('\n'):
            line = line.strip()
            line = _re.sub(r'^[-•*]\s*', '', line)
            line = _re.sub(r'^\d+[\.、]\s*', '', line)
            if line:
                items.append(line)
        return items

    def solve_trace(self, question: str, math_type: str = "数学一",
                    question_type: str = "解答题", knowledge_point: str = "未指定",
                    total_score: float = 10, n_methods: int = 1):
        """
        生成规范解题轨迹（CanonicalSolutionTrace）。

        调用 CANONICAL_SOLVE_PROMPT 让 LLM 输出结构化 JSON，
        然后构建 SolutionGraph DAG。
        """
        from solution_graph import (
            CanonicalSolutionTrace, SolutionMethod, SolutionGraph,
            GraphNode, GraphEdge,
        )

        if not self.client:
            return None

        system = CANONICAL_SOLVE_PROMPT.format(
            math_type=math_type,
            question_type=question_type,
            knowledge_point=knowledge_point,
            question=question,
        )

        # 构建多方法请求
        if n_methods > 1:
            method_instruction = (
                f"请给出这道题的 {n_methods} 种不同解法。"
                "每种解法必须是本质上不同的方法（如分部积分 vs 三角代换），"
                "不是同一种方法的微小变形。每种解法都要有完整的步骤。"
            )
        else:
            method_instruction = "请生成这道题的规范解题轨迹 JSON。"

        # 第一次尝试
        json_text = None
        for attempt in range(2):
            try:
                user_msg = (
                    method_instruction
                    if attempt == 0
                    else "你的上一次输出 JSON 格式有误，请严格按要求输出纯 JSON，不要添加任何解释文字。"
                )
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1 if attempt > 0 else 0.2,
                    max_tokens=4096,
                )
                text = response.choices[0].message.content
                json_text = _extract_json(text)
                if json_text:
                    break
            except Exception:
                if attempt == 1:
                    return None

        if not json_text:
            return None

        try:
            data = _json.loads(json_text)
        except Exception:
            return None

        methods = []
        for method_data in data.get("methods", []):
            nodes = []
            edges = []
            prev_id = None

            for step in method_data.get("steps", []):
                step_id = step.get("id", f"s{len(nodes)+1}")
                node = GraphNode(
                    id=step_id,
                    type=step.get("operation", "compute"),
                    label=step.get("label", ""),
                    output=step.get("output_state", ""),
                    input_state=step.get("input_state", ""),
                    operation=step.get("operation", "compute"),
                    input_refs=[prev_id] if prev_id else [],
                    weight=float(step.get("score_weight", 1)),
                    goal=step.get("goal", ""),
                    strategy=step.get("strategy", ""),
                    reasoning=step.get("reasoning", ""),
                )
                nodes.append(node)
                if prev_id:
                    edges.append(GraphEdge(source=prev_id, target=step_id))
                prev_id = step_id

            final_answer = method_data.get("final_answer", "")
            if nodes and nodes[-1].type != "final_answer":
                fa_node = GraphNode(
                    id=f"s{len(nodes)+1}",
                    type="final_answer",
                    label="最终答案",
                    output=final_answer,
                    input_state=nodes[-1].output if nodes else "",
                    operation="final_answer",
                    input_refs=[nodes[-1].id] if nodes else [],
                    weight=3,
                )
                nodes.append(fa_node)
                edges.append(GraphEdge(source=nodes[-2].id, target=fa_node.id))

            graph = SolutionGraph(
                question_id="",
                final_answer=final_answer,
                nodes=nodes,
                edges=edges,
                total_score=total_score,
                grading_mode="hybrid",
            )

            method = SolutionMethod(
                method_name=method_data.get("method_name", "标准解法"),
                graph=graph,
                final_answer=final_answer,
                knowledge_points=method_data.get("knowledge_points", []),
                common_mistakes=method_data.get("common_mistakes", []),
            )
            methods.append(method)

        if not methods:
            return None

        return CanonicalSolutionTrace(
            question_id="",
            methods=methods,
            verified=False,
        )


def _extract_json(text: str) -> str | None:
    """从 LLM 输出中提取 JSON（可能被 ```json ``` 包裹），并尝试修复常见格式问题。"""
    # 优先从 ```json ``` 代码块中提取
    m = _re.search(r'```json\s*(.*?)\s*```', text, _re.DOTALL)
    if m:
        raw = m.group(1).strip()
    else:
        m = _re.search(r'```\s*(.*?)\s*```', text, _re.DOTALL)
        if m:
            raw = m.group(1).strip()
        else:
            # 贪婪匹配最外层 { ... }
            m = _re.search(r'\{.*\}', text, _re.DOTALL)
            if m:
                raw = m.group(0).strip()
            else:
                return None

    # 尝试直接解析
    import json
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass

    # 修复常见问题
    repaired = raw
    # 1. 去掉尾部逗号: ,] → ] , ,} → }
    repaired = _re.sub(r',\s*([}\]])', r'\1', repaired)
    # 2. 修复单引号 → 双引号（简单场景）
    repaired = repaired.replace("'", '"')
    # 3. 去掉注释
    repaired = _re.sub(r'//.*?$', '', repaired, flags=_re.MULTILINE)

    try:
        json.loads(repaired)
        return repaired
    except json.JSONDecodeError:
        pass

    # 最后尝试：截取第一个 { 到最后一个 }
    first = raw.find('{')
    last = raw.rfind('}')
    if first != -1 and last > first:
        candidate = raw[first:last + 1]
        candidate = _re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    return None
