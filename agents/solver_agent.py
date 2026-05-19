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
        from config import USE_STRUCTURED_OUTPUT

        if USE_STRUCTURED_OUTPUT:
            result = self._solve_structured(question, math_type, question_type, knowledge_point)
            if result.get("success"):
                return result

        return self._solve_legacy(question, math_type, question_type, knowledge_point)

    def _solve_structured(self, question: str, math_type: str,
                          question_type: str, knowledge_point: str) -> dict:
        """结构化求解：优先 CanonicalIR → 回退 StructuredSolution → 最终回退 legacy"""
        if not self.client:
            return {"success": False}

        # ── 尝试 CanonicalIR（统一语义输出层）──
        result = self._solve_canonical(question, math_type, question_type, knowledge_point)
        if result.get("success"):
            return result

        # CanonicalIR 失败，直接回退 legacy（跳过 _solve_structured_v1 节省 1 次 LLM 调用）
        return {"success": False}

    def _solve_canonical(self, question: str, math_type: str,
                         question_type: str, knowledge_point: str) -> dict:
        """CanonicalIR 路径：LLM → CanonicalIR JSON → ProofTrace → StructuredSolution"""
        from prompts.structured_prompts import _CANONICAL_SOLVER_PROMPT
        from semantic_output import validate_canonical_ir, proof_trace_to_structured
        from latex_utils import normalize_latex_style

        system = _CANONICAL_SOLVER_PROMPT.format(
            math_type=math_type, question_type=question_type,
            knowledge_point=knowledge_point, question=question,
        )

        user_msg = f"请生成这道{math_type}{question_type}的规范解答。只输出 JSON。"
        invalid_json = None
        validation_errors = None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",
                     "content": f"请生成这道{math_type}{question_type}的规范解答。只输出 JSON。"},
                ],
                temperature=0.2,
                max_tokens=8192,
            )
            text = response.choices[0].message.content
            json_text = _extract_json(text)
            if not json_text:
                return {"success": False}

            data = _json.loads(json_text)

            # Validate: reject if LaTeX content has control chars (sign of corrupted escapes)
            if _has_corrupted_latex(data):
                return {"success": False}

            model, errors, repairs = validate_canonical_ir(data)
            if errors:
                return {"success": False}

            if repairs:
                import logging
                logging.getLogger(__name__).info("SolverAgent repairs: %s", repairs)

            structured = proof_trace_to_structured(model.proof_trace)

            for step in structured.get("steps", []):
                for block in step.get("blocks", []):
                    if block.get("type") == "latex":
                        block["content"] = normalize_latex_style(block.get("content", ""))

            fa = structured.get("final_answer") or {}
            standard_answer = fa.get("content", "") or model.proof_trace.final_answer
            knowledge_pts = model.question.knowledge_points
            common_mistakes = model.metadata.get("common_mistakes", [])
            total_score = model.question.total_score

            legacy_steps = []
            for ps in model.proof_trace.steps:
                legacy_steps.append({
                    "score": int(ps.max_score or 1),
                    "content": f"{ps.label}: {ps.justification}\n\n${ps.input_state} \\Rightarrow {ps.output_state}$"
                })

            return {
                "success": True,
                "standard_answer": standard_answer,
                "total_score": int(total_score),
                "steps": legacy_steps,
                "knowledge_points": knowledge_pts,
                "common_mistakes": common_mistakes,
                "_structured": structured,
                "_canonical_ir": model.model_dump(),
            }
        except Exception:
            return {"success": False}

    def _solve_structured_v1(self, question: str, math_type: str,
                             question_type: str, knowledge_point: str) -> dict:
        """StructuredSolution 路径（回退用）"""
        from prompts.structured_prompts import _STRUCTURED_SOLVER_PROMPT

        system = _STRUCTURED_SOLVER_PROMPT.format(
            math_type=math_type, question_type=question_type,
            knowledge_point=knowledge_point, question=question,
        )

        from latex_utils import normalize_latex_style

        user_msg = f"请生成这道{math_type}{question_type}的标准解答。只输出 JSON。"
        invalid_json = None
        validation_errors = None

        for attempt in range(2):
            try:
                # 第 2 次尝试：发送具体错误反馈
                if attempt == 1 and (invalid_json or validation_errors):
                    feedback_parts = ["你的上一次输出有格式问题。"]
                    if validation_errors:
                        feedback_parts.append(
                            f"验证失败: {'; '.join(validation_errors[:5])}")
                        feedback_parts.append(
                            "请确保: steps 是非空数组、每个 step 有 label 和 blocks、"
                            "每个 block 的 type 必须是 text 或 latex、"
                            "latex 块不含中文、text 块不含 LaTeX 命令。")
                    if invalid_json:
                        feedback_parts.append(
                            f"上次输出的 JSON 片段（已截断）: {invalid_json[:300]}")
                    feedback_parts.append("请修正后重新输出纯 JSON，不要加任何解释文字。")
                    user_msg = "\n".join(feedback_parts)

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.2 if attempt == 0 else 0.1,
                    max_tokens=8192,
                )
                text = response.choices[0].message.content
                json_text = _extract_json(text)
                if not json_text:
                    invalid_json = text[:500]
                    continue

                data = _json.loads(json_text)

                # Pydantic schema validation + auto-repair
                from latex_utils import validate_and_repair
                model, errors, repairs = validate_and_repair(data)
                if errors:
                    validation_errors = errors
                    invalid_json = json_text[:500]
                    continue

                # Log repairs for debugging
                if repairs:
                    import logging
                    logging.getLogger(__name__).info(
                        "SolverAgent auto-repairs: %s", repairs)

                # Extract from validated Pydantic model
                meta = model.metadata
                total_score = int(meta.total_score)
                steps_pydantic = model.steps

                # Normalize LaTeX in latex-type blocks
                from latex_utils import normalize_latex_style
                for s in steps_pydantic:
                    for b in s.blocks:
                        if b.type == "latex":
                            b.content = normalize_latex_style(b.content)

                # Convert Pydantic models back to dict for _structured storage
                steps = []
                for s in steps_pydantic:
                    blocks = []
                    for b in s.blocks:
                        blocks.append({
                            "type": b.type, "content": b.content,
                            "display": b.display, "operation": b.operation,
                        })
                    steps.append({
                        "label": s.label, "blocks": blocks,
                        "operation": s.operation,
                    })

                # Normalize LaTeX in steps
                for step in steps:
                    for block in step.get("blocks", []):
                        if block.get("type") == "latex":
                            block["content"] = normalize_latex_style(block.get("content", ""))

                fa_model = model.final_answer
                standard_answer = fa_model.content if fa_model else ""
                if fa_model:
                    standard_answer = fa_model.content
                knowledge_pts = meta.knowledge_points
                common_mistakes = meta.common_mistakes

                # Build _structured dict from validated model
                _structured = {
                    "steps": [],
                    "final_answer": (
                        {"type": fa_model.type, "content": fa_model.content}
                        if fa_model else None
                    ),
                    "metadata": {
                        "knowledge_points": knowledge_pts,
                        "difficulty": meta.difficulty,
                        "total_score": total_score,
                        "common_mistakes": common_mistakes,
                    },
                }
                for s in steps_pydantic:
                    _structured["steps"].append({
                        "label": s.label,
                        "blocks": [
                            {"type": b.type, "content": b.content,
                             "display": b.display, "operation": b.operation}
                            for b in s.blocks
                        ],
                        "operation": s.operation,
                    })

                return {
                    "success": True,
                    "standard_answer": standard_answer,
                    "total_score": total_score,
                    "steps": steps,
                    "knowledge_points": knowledge_pts,
                    "common_mistakes": common_mistakes,
                    "_structured": _structured,
                }
            except Exception:
                if attempt == 1:
                    return {"success": False}

        return {"success": False}

    def _solve_legacy(self, question: str, math_type: str,
                      question_type: str, knowledge_point: str) -> dict:
        """最终回退路径：用 JSON prompt，解析 JSON 或转为结构化"""
        if not self.client:
            return {"success": False, "standard_answer": "LLM 未配置", "total_score": 10, "steps": []}

        from prompts.system_prompts import SOLVER_PROMPT

        system = SOLVER_PROMPT.format(
            math_type=math_type, question_type=question_type,
            knowledge_point=knowledge_point, question=question,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",
                     "content": f"请生成这道{math_type}{question_type}的标准解答。只输出 JSON。"},
                ],
                temperature=0.2,
                max_tokens=8192,
            )
            text = response.choices[0].message.content

            # Try to parse as JSON (SOLVER_PROMPT now demands JSON)
            json_text = _extract_json(text)
            if json_text:
                try:
                    data = _json.loads(json_text)
                    from latex_utils import validate_and_repair, normalize_latex_style
                    model, errors, repairs = validate_and_repair(data)
                    if model and not errors:
                        _structured = model.model_dump()
                        for step in _structured.get("steps", []):
                            for block in step.get("blocks", []):
                                if block.get("type") == "latex":
                                    block["content"] = normalize_latex_style(block.get("content", ""))
                        fa = _structured.get("final_answer", {}) or {}
                        meta = _structured.get("metadata", {}) or {}
                        return {
                            "success": True,
                            "standard_answer": fa.get("content", ""),
                            "total_score": int(meta.get("total_score", 10)),
                            "steps": _structured.get("steps", []),
                            "knowledge_points": meta.get("knowledge_points", []),
                            "common_mistakes": meta.get("common_mistakes", []),
                            "_structured": _structured,
                        }
                    # JSON parsed but validation failed → extract plain text from blocks
                    if repairs:
                        text = _extract_plain_text(data)
                except Exception:
                    pass

            # JSON failed or validation failed → convert to structured
            try:
                from latex_utils import from_legacy_text, normalize_latex_style
                text = normalize_latex_style(text)
                _structured = from_legacy_text(text)
            except Exception:
                _structured = None

            return {
                "success": True,
                "standard_answer": text,
                "total_score": 10,
                "steps": [],
                "knowledge_points": [],
                "common_mistakes": [],
                "_structured": _structured,
            }
        except UnicodeEncodeError:
            return {"success": False, "standard_answer": "系统编码错误", "total_score": 10,
                    "steps": [], "_error_type": "system_encoding"}
        except Exception as e:
            return {"success": False,
                    "standard_answer": f"解答生成失败: {type(e).__name__}: {e}",
                    "total_score": 10, "steps": [], "_error_type": "system_internal"}

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
                    max_tokens=8192,
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


def _extract_plain_text(data: dict) -> str:
    """Extract plain text from a partially-valid StructuredSolution dict.

    Used when validate_and_repair finds errors but we can still salvage content.
    """
    parts = []
    for step in data.get("steps", []):
        if isinstance(step, dict):
            label = step.get("label", "")
            if label:
                parts.append(f"### {label}")
            for b in step.get("blocks", []):
                if isinstance(b, dict):
                    c = b.get("content", "")
                    if c and isinstance(c, str):
                        if b.get("type") == "latex":
                            parts.append(f"${c}$")
                        else:
                            parts.append(c)
    fa = data.get("final_answer", {})
    if isinstance(fa, dict) and fa.get("content"):
        parts.append(f"最终答案：{fa['content']}")
    return "\n\n".join(parts)


def _has_corrupted_latex(data: dict) -> bool:
    """Check if parsed JSON data has corrupted LaTeX (form feeds, bare \n, etc.)"""
    import json
    raw = json.dumps(data, ensure_ascii=False)
    # Form feed = \frac became corrupted by JSON parser
    if '\x0c' in raw:
        return True
    # Check string values for suspicious patterns
    def _check(obj, depth=0):
        if depth > 10:
            return False
        if isinstance(obj, str):
            # \n\n (double JSON newline) in LaTeX context = corrupted
            if '\n\n' in obj and ('\\' in obj or 'frac' in obj or 'sum' in obj or 'int' in obj):
                return True
            # Stray form feed
            if '\x0c' in obj:
                return True
        elif isinstance(obj, dict):
            for v in obj.values():
                if _check(v, depth+1):
                    return True
        elif isinstance(obj, list):
            for v in obj:
                if _check(v, depth+1):
                    return True
        return False
    return _check(data)


def _extract_json(text: str) -> str | None:
    """从 LLM 输出中提取 JSON，处理 LaTeX 转义问题。

    LLM 常见错误及修复策略：
    1. JSON 包裹在 ```json ``` 中 → 提取代码块
    2. LaTeX 反斜杠未正确转义（\\frac 写成 \\frac） → 检测并修复
    3. 尾部多余逗号（,], ,}） → 移除
    4. JSON 外有解释文字 → 用括号匹配定位 JSON 边界
    5. 单引号用于 JSON 键/值 → 仅修复键名/字符串值中的单引号
    """
    raw = text.strip()

    # ── 1. 提取 ```json ``` 或 ``` ``` 代码块 ──
    m = _re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, _re.DOTALL)
    if m:
        raw = m.group(1).strip()

    # ── 2. 用括号匹配找到最外层 JSON ──
    raw = _find_json_boundary(raw)

    # ── 3. 修复 LaTeX 反斜杠 ──
    raw = _fix_latex_escaping(raw)

    # ── 4. 尝试解析 + 修复尾部逗号 ──
    import json
    for candidate in (raw, _re.sub(r',\s*([}\]])', r'\1', raw)):
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue

    # ── 5. 最后的激进修复：去掉注释，清理不可见字符 ──
    raw = _re.sub(r'//[^\n]*', '', raw)
    raw = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        pass

    return None


def _find_json_boundary(text: str) -> str:
    """用括号深度匹配找到第一个 { 到最后一个 } 的 JSON 边界。"""
    start = text.find('{')
    if start == -1:
        return text

    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
        elif ch == '"':
            # 跳过 JSON 字符串（处理转义）
            j = i + 1
            while j < len(text):
                if text[j] == '\\' and j + 1 < len(text):
                    j += 2  # 跳过转义字符
                elif text[j] == '"':
                    i = j
                    break
                j += 1

    # 没找到匹配的 }，回退到第一个 { 到文本末尾
    if depth > 0:
        return text[start:]

    return text


_LATEX_CMDS = {
    'frac', 'sqrt', 'int', 'sum', 'prod', 'lim', 'left', 'right',
    'big', 'Big', 'bigg', 'Bigg', 'bigl', 'Bigl', 'biggl', 'Biggl',
    'bigr', 'Bigr', 'biggr', 'Biggr',
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'arcsin', 'arccos', 'arctan',
    'log', 'ln', 'exp', 'partial', 'nabla', 'infty', 'emptyset',
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta', 'lambda', 'mu',
    'pi', 'sigma', 'phi', 'omega', 'Gamma', 'Delta', 'Theta', 'Lambda',
    'Pi', 'Sigma', 'Omega', 'to', 'cdot', 'times', 'div', 'pm', 'mp',
    'leq', 'geq', 'neq', 'equiv', 'approx', 'sim', 'forall', 'exists',
    'in', 'notin', 'subset', 'subseteq', 'cup', 'cap', 'setminus',
    'overline', 'underline', 'hat', 'tilde', 'bar', 'vec',
    'text', 'textbf', 'mathrm', 'mathbf', 'mathcal', 'mathbb',
    'begin', 'end', 'boxed', 'displaystyle', 'limits', 'prime', 'dots',
    'cdots', 'vdots', 'ddots', 'Rightarrow', 'Leftarrow',
    'rightarrow', 'leftarrow', 'mapsto', 'longrightarrow', 'binom',
    'choose', 'dfrac', 'tfrac', 'cfrac',
    'langle', 'rangle', 'lfloor', 'rfloor', 'lceil', 'rceil',
    'angle', 'triangle', 'circ', 'bullet', 'oplus', 'otimes', 'odot',
    'max', 'min', 'sup', 'inf', 'det', 'dim', 'gcd', 'hom',
    'stackrel', 'xrightarrow', 'xleftarrow',
    'displaystyle', 'textstyle', 'scriptstyle',
    'slash', 'backslash', 'parallel', 'perp',
    'cdotp', 'colon', 'ldotp', 'mathellipsis',
}
_LATEX_CMDS_SORTED = sorted(_LATEX_CMDS, key=len, reverse=True)


def _fix_latex_escaping(text: str) -> str:
    r"""修复 JSON 字符串内未正确转义的 LaTeX 反斜杠。

    JSON 合法转义: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    单反斜杠后跟字母（如 \f 在 \frac 中）是非法 JSON，需修复。

    特殊处理: \n 和 \t 既是 JSON 转义（换行/制表）也是 LaTeX 前缀
    (\notin, \times 等）。检测后续字符来判断是 JSON 转义还是 LaTeX。
    """
    # JSON escapes that are ALSO LaTeX command prefixes
    AMBIGUOUS = {'n', 't'}

    result = []
    i = 0
    in_string = False

    while i < len(text):
        ch = text[i]

        if ch == '"' and (i == 0 or text[i - 1] != '\\'):
            in_string = not in_string

        if in_string and ch == '\\' and i + 1 < len(text):
            next_ch = text[i + 1]

            # 已经是 \\ → 跳过
            if i > 0 and text[i - 1] == '\\':
                result.append(ch)
                i += 1
                continue

            if next_ch == '\\' or next_ch == '"' or next_ch == '/' or next_ch == 'r' or next_ch == 'u':
                # Unambiguous JSON escapes: \\, \", \/, \r, \uXXXX
                pass
            elif next_ch == 'f':
                # \f = JSON form feed, but LLM uses it for \frac, \flat
                result.append('\\')
            elif next_ch == 'b':
                # \b = JSON backspace, but LLM uses it for \begin, \binom, \boxed, \bar
                result.append('\\')
            elif next_ch in AMBIGUOUS:
                # \n 可能是 JSON 换行或 \notin / \neq / \nearrow
                # \t 可能是 JSON 制表或 \times / \text / \tan
                peek = text[i + 1:i + 10]  # Long enough for \nearrow, \nsubseteq
                looks_like_latex = any(
                    peek.startswith(p) for p in
                    ('notin', 'neq', 'nearrow', 'nsubseteq', 'ngtr', 'nless',
                     'times', 'text', 'tan', 'tilde', 'tfrac', 'textbf', 'texttt')
                )
                if looks_like_latex:
                    result.append('\\')
            elif next_ch.isalpha() or next_ch == '(':
                # 其他非法转义 → 修复
                result.append('\\')

        result.append(ch)
        i += 1

    return ''.join(result)
