"""
Student Trace Extractor — 从学生原始解题文本提取结构化推导轨迹

核心职责：
  - 将学生自由文本 → 结构化步骤（operation, input_state, output_state）
  - 优先用 LLM 提取（精度高），失败时回退到启发式提取
  - 输出与 CanonicalSolutionTrace 格式对齐，供 graph_matching 使用
"""

import re
import json as _json

from operations import Op, infer_op_from_text, normalize_op


# ═══════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════

def extract_student_trace(student_text: str, question: str = "",
                          client=None, model: str = "deepseek-chat") -> dict:
    """
    从学生文本提取结构化轨迹。

    Args:
        student_text: 学生原始解题文本
        question: 题目文本（辅助 LLM 理解上下文）
        client: OpenAI-compatible LLM 客户端
        model: LLM 模型名

    Returns:
        {
            "steps": [{"id", "operation", "input_state", "output_state", "label", "has_error", "error_description", "confidence"}],
            "final_answer": str,
            "method_name": str,
            "extraction_method": "llm" | "heuristic",
        }
    """
    if not student_text or not student_text.strip():
        return _empty_result("heuristic")

    # 优先 LLM 提取
    if client:
        try:
            result = _llm_extract(student_text, question, client, model)
            if result and result.get("steps"):
                result["extraction_method"] = "llm"
                return result
        except Exception:
            pass

    # 启发式兜底
    result = _heuristic_extract(student_text)
    result["extraction_method"] = "heuristic"
    return result


# ═══════════════════════════════════════════════
# LLM 提取
# ═══════════════════════════════════════════════

def _llm_extract(student_text: str, question: str,
                 client, model: str) -> dict | None:
    """用 LLM 提取学生轨迹"""
    from prompts.system_prompts import STUDENT_TRACE_PROMPT

    system = STUDENT_TRACE_PROMPT.format(
        student_answer=student_text,
        question=question or "（无题目信息）",
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": "请解析这段学生解题文本的推导轨迹。"},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    text = response.choices[0].message.content

    json_text = _extract_json(text)
    if not json_text:
        return None

    data = _json.loads(json_text)

    steps = data.get("steps", [])
    if not isinstance(steps, list):
        return None

    # 规范化每个步骤
    normalized_steps = []
    for i, step in enumerate(steps):
        op = normalize_op(step.get("operation", "compute"))
        normalized_steps.append({
            "id": step.get("id", f"s{i+1}"),
            "operation": op.value,
            "input_state": step.get("input_state", ""),
            "output_state": step.get("output_state", ""),
            "label": step.get("label", ""),
            "has_error": bool(step.get("has_error", False)),
            "error_description": step.get("error_description", ""),
            "confidence": float(step.get("confidence", 0.8)),
        })

    # 推断 input_state（LLM 可能漏填）
    _infer_input_states(normalized_steps)

    return {
        "steps": normalized_steps,
        "final_answer": data.get("final_answer", ""),
        "method_name": data.get("method_name", "学生解法"),
    }


# ═══════════════════════════════════════════════
# 启发式提取（无 LLM 兜底）
# ═══════════════════════════════════════════════

# 步骤切分模式
_STEP_PATTERNS = [
    r'(?:^|\n)\s*(?:\d+[\s\.、．]+)',
    r'(?:^|\n)\s*[（(]\s*[IVXivx1-9]+\s*[）)]',
    r'(?:^|\n)\s*[一二三四五六七八九十]+[、．\s]',
]


def _heuristic_extract(student_text: str) -> dict:
    """启发式提取：步骤切分 + 关键词推断 operation + input_state 链式推断"""
    steps = []
    lines = student_text.strip().split('\n')
    current_label = ""
    current_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_new_step = any(re.match(p, line) for p in _STEP_PATTERNS)

        if is_new_step and current_lines:
            steps.append(_build_heuristic_step(
                len(steps) + 1, current_label, '\n'.join(current_lines)
            ))
            current_lines = [line]
            current_label = line[:80]
        else:
            if not current_label:
                current_label = line[:80]
            current_lines.append(line)

    if current_lines:
        steps.append(_build_heuristic_step(
            len(steps) + 1, current_label, '\n'.join(current_lines)
        ))

    # 关键改进：链式推断 input_state
    _infer_input_states(steps)

    # 推断最终答案
    final_answer = ""
    if steps:
        last_output = steps[-1].get("output_state", "")
        if last_output:
            final_answer = last_output

    return {
        "steps": steps,
        "final_answer": final_answer,
        "method_name": "学生解法",
    }


def _build_heuristic_step(idx: int, label: str, raw_text: str) -> dict:
    """构建单个启发式步骤"""
    op = infer_op_from_text(raw_text)

    # 尝试提取数学表达式（多种模式）
    math_exprs = re.findall(r'\$([^$]+)\$', raw_text)
    if not math_exprs:
        math_exprs = re.findall(r'\\[a-zA-Z]+[^\n]*', raw_text)
    if not math_exprs:
        # 尝试提取含等号的表达式
        eq_match = re.findall(r'([^=\n]+=\s*[^\n]+)', raw_text)
        if eq_match:
            math_exprs = eq_match

    output_state = math_exprs[-1].strip() if math_exprs else ""

    return {
        "id": f"s{idx}",
        "operation": op.value,
        "input_state": "",  # 后续由 _infer_input_states 填充
        "output_state": output_state,
        "label": label,
        "has_error": False,
        "error_description": "",
        "confidence": 0.6,  # 启发式提取置信度较低
    }


def _infer_input_states(steps: list[dict]):
    """
    链式推断 input_state：步骤 N 的 input_state = 步骤 N-1 的 output_state。

    这是启发式提取的关键改进——没有这一步，verify_step_transition 无法验证步骤间转换。
    """
    for i, step in enumerate(steps):
        if not step.get("input_state") and i > 0:
            prev_output = steps[i - 1].get("output_state", "")
            if prev_output:
                step["input_state"] = prev_output


# ═══════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════

def _extract_json(text: str) -> str | None:
    """从 LLM 输出中提取 JSON"""
    m = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        return m.group(0).strip()
    return None


def _empty_result(method: str) -> dict:
    """空结果"""
    return {
        "steps": [],
        "final_answer": "",
        "method_name": "",
        "extraction_method": method,
    }
