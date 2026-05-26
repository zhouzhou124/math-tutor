"""simple_question_parser.py — 简单题目解析器"""
import re

from latex_utils import repair_math_delimiters_for_render

def parse_latex_question(text: str) -> dict:
    """
    解析用户输入的LaTeX题目文本，提取题目内容和选项。
    
    输入格式示例：
    $1.$ 当 $x \to 0$ 时，以下无穷小量阶数最高的是
    $(A)$ $\int_0^{\sin x} [(1+t)^t - 1] dt$
    $(B)$ $\int_0^{\sin^2 x} (1+t)^t dt$
    $(C)$ $\int_0^{\sin x} [e^{-(1+t)^t}] dt$
    $(D)$ $\int_0^{\sin^2 x} (te^t - t) dt$
    
    返回：{"question": "...", "options": {"A": "...", "B": "...", ...}}
    """
    raw_text = text
    text = repair_math_delimiters_for_render(text)
    result = {"question": "", "options": {}}
    
    lines = text.split('\n')
    question_lines = []
    options = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配选项格式：$(A)$ xxx 或 $(A) xxx 或 (A) xxx 或 A. xxx 或 $A$ xxx
        option_match = re.match(r'^\$?\(?([A-D])\)?\$?\s*(.+)$', line)
        # 如果上面的匹配失败，尝试匹配 $A$ 格式（不带括号）
        if not option_match:
            option_match = re.match(r'^\$([A-D])\$\s*(.+)$', line)
        if option_match:
            letter = option_match.group(1).upper()
            text_content = option_match.group(2).strip()
            # 清理选项中的编号（如 $1.$）
            text_content = re.sub(r'^\$\d+\.\$\s*', '', text_content)
            if letter not in options:
                options[letter] = text_content
        else:
            # 题目内容（去掉编号如 $1.$）
            clean_line = re.sub(r'^\$\d+\.\$\s*', '', line)
            question_lines.append(clean_line)
    
    result["question"] = '\n'.join(question_lines).strip()
    result["options"] = options
    # 保留原始文本，Parser 输出不覆盖 Raw
    result["raw_question_text"] = raw_text

    return result
