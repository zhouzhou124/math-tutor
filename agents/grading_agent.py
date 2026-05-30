"""Grading Agent — 按考研标准批改评分"""

import json as _json
import logging

from prompts.system_prompts import GRADING_PROMPT
from config import GRADING_RULES, get_scoring_weights
from .solver_agent import _extract_json

logger = logging.getLogger(__name__)


class GradingAgent:
    """对照标准答案批改学生作答，给出分数和扣分点"""

    def __init__(self, client, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def grade(self, question: str, standard_answer: str,
              student_answer: str, total_score: int = 10,
              knowledge_points: str = "", difficulty: str = "中等",
              canonical_trace=None, question_type: str = "") -> dict:
        """标准批改入口（Engine B 主路径）。双栈：先试结构化，失败回退 Markdown。"""
        from config import USE_STRUCTURED_OUTPUT

        if USE_STRUCTURED_OUTPUT:
            result = self._grade_structured(
                question, standard_answer, student_answer,
                total_score, knowledge_points, difficulty, canonical_trace,
                question_type=question_type,
            )
            if result.get("success"):
                return result

        return self._do_grade(question, standard_answer, student_answer,
                              total_score, knowledge_points, difficulty,
                              canonical_trace, question_type=question_type)

    def grade_with_evidence(self, question: str, standard_answer: str,
                            student_answer: str, total_score: int = 10,
                            knowledge_points: str = "", difficulty: str = "中等",
                            canonical_trace=None,
                            engine_c_evidence: dict = None,
                            question_type: str = "") -> dict:
        """
        基于 Engine C 结构化证据的语义裁决（Engine B 作为 fallback 时使用）。
        不再从头理解题目，只对 Engine C 无法判断的部分做最终裁决。
        """
        if not self.client:
            return {"success": False, "total": 0, "comment": "LLM 未配置"}

        # 构建精简的 evidence 描述
        evidence_text = ""
        if engine_c_evidence:
            matched = engine_c_evidence.get("matched_steps", [])
            coverage = engine_c_evidence.get("coverage", 0)
            correctness = engine_c_evidence.get("correctness", 0)
            evidence_text = "Engine C 分析结果：\n"
            evidence_text += f"- 步骤覆盖度: {coverage:.0%}\n"
            evidence_text += f"- 数学正确度: {correctness:.0%}\n"
            if matched:
                evidence_text += "- 已匹配步骤:\n"
                for ms in matched[:10]:
                    evidence_text += (
                        f"  · {ms.get('label', '?')}: "
                        f"match={ms.get('match_method', '?')}\n"
                    )

        return self._do_grade(
            question, standard_answer, student_answer,
            total_score, knowledge_points, difficulty,
            canonical_trace,
            extra_context=evidence_text,
            question_type=question_type,
        )

    def _grade_structured(self, question: str, standard_answer: str,
                           student_answer: str, total_score: int,
                           knowledge_points: str, difficulty: str,
                           canonical_trace=None, question_type: str = "") -> dict:
        """结构化批改：LLM 输出 JSON，直接映射到结果字典"""
        if not self.client:
            return {"success": False}

        from prompts.structured_prompts import _STRUCTURED_GRADING_PROMPT

        # P39: 使用 config 中的题型权重，不再硬编码 50/50
        weights = get_scoring_weights(question_type)
        step_total = round(total_score * (weights["correctness"] + weights["process"]) / 100, 1)
        result_total = round(total_score * weights["format"] / 100, 1)

        system = _STRUCTURED_GRADING_PROMPT.format(
            question=question, standard_answer=standard_answer,
            student_answer=student_answer if student_answer else "（学生未作答）",
            grading_rules=GRADING_RULES,
            knowledge_points=knowledge_points or "未指定",
            difficulty=difficulty,
            step_total=step_total, result_total=result_total, total=total_score,
        )

        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": "请批改这位学生的作答。只输出 JSON。"},
                    ],
                    temperature=0.1,
                    max_tokens=4096,
                    timeout=60,
                )
                text = response.choices[0].message.content
                json_text = _extract_json(text)
                if not json_text:
                    continue

                data = _json.loads(json_text)
                score_data = data.get("score", {})
                return {
                    "success": True,
                    "total": float(score_data.get("total", 0)),
                    "step_score": float(score_data.get("step_score", 0)),
                    "result_score": float(score_data.get("result_score", 0)),
                    "step_analysis": data.get("step_analysis", []),
                    "deductions": data.get("deductions", []),
                    "comment": data.get("comment", ""),
                    "method_matched": data.get("method_matched", ""),
                    "confidence": float(data.get("confidence", 0.85)),
                    "_engine": "B_structured",
                }
            except Exception:
                if attempt == 1:
                    return {"success": False}

        return {"success": False}

    def _do_grade(self, question: str, standard_answer: str,
                  student_answer: str, total_score: int,
                  knowledge_points: str, difficulty: str,
                  canonical_trace=None, extra_context: str = "",
                  question_type: str = "") -> dict:
        """内部统一批改实现。"""

        if not self.client:
            return {"success": False, "total": 0, "comment": "LLM 未配置，无法批改。"}

        # P39: 使用 config 中的题型权重，不再硬编码 50/50
        weights = get_scoring_weights(question_type)
        step_total = round(total_score * (weights["correctness"] + weights["process"]) / 100, 1)
        result_total = round(total_score * weights["format"] / 100, 1)

        # 格式化 canonical trace
        enriched_answer = standard_answer
        if canonical_trace and hasattr(canonical_trace, 'best_method'):
            best = canonical_trace.best_method(student_answer=student_answer)
            if best and best.graph and best.graph.nodes:
                trace_lines = [f"标准解法: {best.method_name}", ""]
                for node in best.graph.nodes:
                    op = node.operation or node.type
                    out = node.output or ""
                    label = node.label or ""
                    if out:
                        trace_lines.append(f"步骤({op}): {label} → {out}")
                    elif label:
                        trace_lines.append(f"步骤({op}): {label}")
                if best.final_answer:
                    trace_lines.append(f"\n最终答案: {best.final_answer}")
                enriched_answer = "\n".join(trace_lines)

        system = GRADING_PROMPT.format(
            question=question,
            standard_answer=enriched_answer,
            student_answer=student_answer if student_answer else "（学生未作答）",
            grading_rules=GRADING_RULES,
            knowledge_points=knowledge_points or "未指定",
            difficulty=difficulty,
            step_total=step_total,
            result_total=result_total,
            total=total_score,
        )

        # 如果有 Engine C 证据，追加到 prompt 末尾
        if extra_context:
            system += f"\n\n[系统提示] 以下为自动分析结果，仅供参考。" \
                      f"你只需要对不确定的部分做最终语义判断：\n{extra_context}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": "请批改这位学生的作答。"},
                ],
                temperature=0.1,
                max_tokens=4096,
                timeout=60,
            )
            text = response.choices[0].message.content
            return self._parse_grading_result(text, total_score)
        except UnicodeEncodeError:
            return {"success": False, "total": 0, "comment": "系统编码错误", "_error_type": "system_encoding"}
        except Exception:
            return {"success": False, "total": 0, "comment": "批改服务暂不可用", "_error_type": "system_internal"}

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
