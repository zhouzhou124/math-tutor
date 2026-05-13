#!/usr/bin/env python3
"""测试概率题渲染问题 - 直接输出到文件"""

import importlib
import latex_normalizer
importlib.reload(latex_normalizer)
from latex_normalizer import normalize_latex_style

# 用户提供的输入
original = "$7.$ 设随机事件 $A$ 与 $B$ 相互独立，且 $P(B) = 0.5$，$P(A - B) = 0.3$，则 $P(B - A) =$ $( )$ \n\n $(A)$ $0.1$ \\qquad $(B)$ $0.2$ \\qquad $(C)$ $0.3$ \\qquad $(D)$ $0.4$"

# 写入原始输入
with open('E:\\math_tutor\\test_probability_output.txt', 'w', encoding='utf-8') as f:
    f.write("=== 原始输入 ===\n")
    f.write(original)
    f.write("\n\n")
    f.write("="*100 + "\n")
    
    # 逐步测试处理流程
    from latex_normalizer import (
        _normalize_choice_options,
    )
    
    f.write("=== 1. _normalize_choice_options 输出 ===\n")
    result1 = _normalize_choice_options(original)
    f.write(result1)
    f.write("\n\n")
    f.write("="*100 + "\n")
    
    f.write("=== 2. 完整 normalize_latex_style 输出 ===\n")
    result2 = normalize_latex_style(original)
    f.write(result2)

print("测试完成，请查看 E:\\math_tutor\\test_probability_output.txt")
