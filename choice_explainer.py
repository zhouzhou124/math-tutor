"""选择题解析生成器 — AI-powered choice question explanation"""

import re


def detect_question_type(question_text: str, existing_type: str = "") -> str:
    """自动检测题型。当 existing_type 可靠时直接返回，否则从题目文本推断。"""
    if existing_type in ("选择题", "填空题", "解答题", "证明题"):
        return existing_type

    text = (question_text or "").strip()
    if not text:
        return existing_type or "解答题"

    # 检测选择题特征: $(A)$ (A) A. A、 等
    choice_markers = [
        r'[\$\(]\s*A\s*[\)\$]', r'[\$\(]\s*B\s*[\)\$]',
        r'[\$\(]\s*C\s*[\)\$]', r'[\$\(]\s*D\s*[\)\$]',
        r'^\s*A\s*[.．、]', r'^\s*B\s*[.．、]',
        r'^\s*C\s*[.．、]', r'^\s*D\s*[.．、]',
    ]
    choice_hits = sum(1 for p in choice_markers if re.search(p, text, re.MULTILINE))
    if choice_hits >= 3:
        return "选择题"

    # 检测填空题特征: 下划线、空格留白
    if re.search(r'_{2,}|\\underline\s*\{', text):
        return "填空题"

    return existing_type or "解答题"


def _parse_options_from_question(question_text: str) -> dict:
    """从题目文本中离线解析选项内容。

    支持格式:
      - $(A)$ content $(B)$ content ...
      - (A) content (B) content ...
    返回 {"A": "content", "B": "content", ...}
    """
    options = {"A": "", "B": "", "C": "", "D": ""}
    text = (question_text or "").strip()
    if not text:
        return options

    # 策略: 找选项标记位置，然后按标记切分
    # 匹配 $(A)$ 或 (A) 或 A. 或 A、
    markers = []
    for letter in ["A", "B", "C", "D"]:
        for m in re.finditer(
            rf'(?:\$\s*\(\s*{letter}\s*\)\s*\$|\(\s*{letter}\s*\)|{letter}\s*[.．、])',
            text,
        ):
            markers.append((m.start(), m.end(), letter))

    markers.sort()

    if len(markers) < 3:
        return options  # 不足3个选项标记，不解析

    # 按标记位置切分
    for i, (start, end, letter) in enumerate(markers):
        if i + 1 < len(markers):
            next_start = markers[i + 1][0]
            content = text[end:next_start].strip()
        else:
            content = text[end:].strip()
        # 清理行尾的 \qquad, \quad, 多余空格
        content = re.sub(r'\s*\\qquad\s*$', '', content)
        content = re.sub(r'\s*\\quad\s*$', '', content)
        options[letter] = content.strip()

    return options


CHOICE_EXPLANATION_PROMPT = """你是一位考研数学辅导老师。学生做了一道选择题，请给出详细解析。

## 题目
{question}

## 学生答案
{student_answer}

## 正确答案
{correct_answer}

## 学生是否答对
{correct_status}

请按以下格式输出解析。

【重要】所有数学公式必须用 $...$ 包裹（行内）或 $$...$$ 包裹（独立行）。
例如：$\\frac{{1}}{{2}}$，$\\sum_{{n=1}}^{{\\infty}} a_n$，$$\\int_0^1 x\\,dx = \\frac{{1}}{{2}}$$
绝对不要裸写 LaTeX 命令，如 (\\frac12) 是错误的，必须写成 $\\frac{{1}}{{2}}$。

## 解题思路
（用简洁的数学推理过程说明如何得到正确答案，公式必须用 $...$ 包裹）

## 选项分析
A: （该选项为什么对/错，公式必须用 $...$ 包裹）
B: （该选项为什么对/错）
C: （该选项为什么对/错）
D: （该选项为什么对/错）

## 知识点
- 知识点1
- 知识点2

## 常见误区
- 误区1
- 误区2

## 秒杀技巧
（如果有快速解法或排除法，请说明，公式用 $...$ 包裹；没有则写"无"）
"""


def generate_choice_explanation(
    question: dict,
    student_answer: str,
    is_correct: bool,
    client,
    model: str = "deepseek-chat",
) -> dict:
    """为选择题生成AI解析。

    Args:
        question: 完整题目dict（含question, correct_option等）
        student_answer: 学生原始答案文本
        is_correct: 学生是否答对
        client: OpenAI兼容客户端（可为None）
        model: 模型名称

    Returns:
        解析dict，包含thought_process, option_analysis, knowledge_points等
    """
    correct_option = question.get("correct_option", "")
    question_text = question.get("question", "")
    knowledge_points = question.get("knowledge_points", [])

    # 离线 fallback：从题目文本解析选项内容
    parsed_options = _parse_options_from_question(question_text)
    fallback = {
        "thought_process": "",
        "option_analysis": parsed_options,
        "knowledge_points": knowledge_points,
        "common_traps": [],
        "fast_method": "",
        "correct_answer": correct_option,
        "raw": "",
    }

    if not client:
        return fallback
    correct_status = "答对了" if is_correct else "答错了"

    # 使用 str.replace() 避免 LaTeX { } 与 .format() 冲突
    prompt = (CHOICE_EXPLANATION_PROMPT
        .replace("{question}", question_text)
        .replace("{student_answer}", student_answer or "（未作答）")
        .replace("{correct_answer}", correct_option)
        .replace("{correct_status}", correct_status)
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是考研数学辅导专家，擅长分析选择题的每个选项。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        text = response.choices[0].message.content
        result = _parse_explanation(text, correct_option, question)
        # 合并离线解析结果：LLM 解析失败的字段使用离线解析兜底
        if not any(result.get("option_analysis", {}).values()):
            result["option_analysis"] = parsed_options
        if not result.get("knowledge_points"):
            result["knowledge_points"] = knowledge_points
        # thought_process 解析失败时，直接使用 LLM 原始输出
        if not result.get("thought_process") and text:
            result["thought_process"] = text.strip()
        return result
    except Exception as e:
        import streamlit as st
        st.warning(f"选择题解析生成失败: {e}")
        return fallback


def _parse_explanation(text: str, correct_option: str, question: dict) -> dict:
    """从LLM响应中解析结构化解析内容。"""

    # 解题思路 — 容错匹配：标题后任意空白/冒号后取内容
    thought_match = re.search(
        r"##\s*解题思路\s*[：:\s](.*?)(?=\n##\s*\S|\Z)", text, re.DOTALL
    )
    thought_process = thought_match.group(1).strip() if thought_match else ""

    # 选项分析
    option_analysis = {"A": "", "B": "", "C": "", "D": ""}
    analysis_match = re.search(
        r"##\s*选项分析\s*[：:\s](.*?)(?=\n##\s*\S|\Z)", text, re.DOTALL
    )
    if analysis_match:
        analysis_text = analysis_match.group(1)
        for letter in ["A", "B", "C", "D"]:
            opt_match = re.search(
                rf"{letter}\s*[：:]\s*(.*?)(?=\n[A-D]\s*[：:]|\n##|\Z)",
                analysis_text,
                re.DOTALL,
            )
            if opt_match:
                option_analysis[letter] = opt_match.group(1).strip()

    # 知识点
    kp_match = re.search(
        r"##\s*知识点\s*[：:\s](.*?)(?=\n##\s*\S|\Z)", text, re.DOTALL
    )
    knowledge_points = []
    if kp_match:
        knowledge_points = [
            line.strip("- •· ")
            for line in kp_match.group(1).strip().split("\n")
            if line.strip() and line.strip() not in ("-", "- ", "•", "·")
        ]

    # 常见误区
    trap_match = re.search(
        r"##\s*常见误区\s*[：:\s](.*?)(?=\n##\s*\S|\Z)", text, re.DOTALL
    )
    common_traps = []
    if trap_match:
        common_traps = [
            line.strip("- •· ")
            for line in trap_match.group(1).strip().split("\n")
            if line.strip() and line.strip() not in ("-", "- ", "•", "·")
        ]

    # 秒杀技巧
    fast_match = re.search(
        r"##\s*秒杀技巧\s*[：:\s](.*?)(?=\n##\s*\S|\Z)", text, re.DOTALL
    )
    fast_method = ""
    if fast_match:
        fast_method = fast_match.group(1).strip()
        if fast_method in ("无", "无。", "暂无", "暂无。"):
            fast_method = ""

    return {
        "thought_process": thought_process,
        "option_analysis": option_analysis,
        "knowledge_points": knowledge_points or question.get("knowledge_points", []),
        "common_traps": common_traps,
        "fast_method": fast_method,
        "correct_answer": correct_option,
        "raw": text,
    }


DETAILED_ANSWER_PROMPT = """你是一位考研数学辅导专家。请为以下题目生成一份详细的、分步骤的标准答案。

## 题目
{question}

## 题目类型
{question_type}

## 已知答案
{known_answer}

## 知识点
{knowledge_points}

请严格按照以下格式输出详细解答。每个步骤必须用"步骤N："开头，公式必须用 $...$ 包裹：

## 标准答案
（用一两行给出最终答案）

步骤1：（第一步的标题，如"分析题意"、"确定方法"等）
（这一步的推理过程。所有公式用 $...$ 包裹，如 $f(x)=x^2+1$。）

步骤2：（第二步的标题）
（这一步的推理过程。所有公式用 $...$ 包裹。）

步骤3：（第三步的标题）
（继续推理，直到得出最终答案。每步一个核心操作。）

（根据需要继续步骤4、步骤5...）

## 关键知识点
（本题考察的核心知识点，列出2-4个）

## 易错提示
（学生容易犯的错误，列出2-4个）
"""


def generate_detailed_answer(
    question: dict,
    known_answer: str,
    question_type: str,
    client,
    model: str = "deepseek-chat",
) -> str:
    """为任意题型生成带详细步骤的标准答案。

    Returns:
        格式化的详细答案文本（含步骤、知识点、易错提示）
    """
    question_text = question.get("question", "")
    knowledge_points = ", ".join(question.get("knowledge_points", []))

    if not client:
        return known_answer

    prompt = (DETAILED_ANSWER_PROMPT
        .replace("{question}", question_text)
        .replace("{question_type}", question_type)
        .replace("{known_answer}", known_answer)
        .replace("{knowledge_points}", knowledge_points or "未指定")
    )

    try:
        messages = [
            {"role": "system", "content": "你是考研数学辅导专家，擅长分步骤讲解题目解答过程。"},
            {"role": "user", "content": prompt},
        ]
        text_parts = []

        for round_idx in range(2):  # 最多续写1次
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2 if round_idx == 0 else 0.1,
                max_tokens=4096,
                timeout=45,  # 单次LLM调用最长等45秒
            )
            choice = response.choices[0]
            chunk = choice.message.content or ""
            if chunk:
                text_parts.append(chunk)

            combined = "".join(text_parts).strip()
            finish_reason = getattr(choice, "finish_reason", "")

            # 内容够了就停，不纠结是否"完整"
            if len(combined) > 500 and finish_reason != "length":
                return combined or known_answer
            if _is_answer_good_enough(combined):
                return combined or known_answer

            messages = [
                {"role": "system", "content": "你是考研数学辅导专家。"},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": combined},
                {"role": "user", "content": "请继续写，不要重复已有内容，只输出后续部分。"},
            ]

        return "".join(text_parts).strip() or known_answer
    except Exception as e:
        import streamlit as st
        st.warning(f"详细答案生成失败: {e}")
        return known_answer


def _is_answer_good_enough(text: str) -> bool:
    """Return True when the generated answer is long enough and looks complete."""
    s = (text or "").strip()
    if len(s) < 200:
        return False
    # Has at least one step marker or structured section
    has_steps = bool(re.search(r'(?:步骤\d+|## (?:标准答案|详细步骤|关键知识点|易错提示))', s))
    if not has_steps:
        return False
    # Doesn't end mid-sentence
    if s[-1] in "，、；：,;:（([【":
        return False
    # Math delimiters balanced
    if s.count("$$") % 2 != 0:
        return False
    if (s.replace("$$", "").count("$")) % 2 != 0:
        return False
    return True


def _is_detailed_answer_complete(text: str) -> bool:
    """Heuristic guard against token-limit truncation in detailed answers."""
    return _is_answer_good_enough(text)
