#!/usr/bin/env python3
"""测试概率题渲染问题"""

import importlib
import latex_normalizer
importlib.reload(latex_normalizer)
from latex_normalizer import normalize_latex_style

# 用户提供的输入
original = "$7.$ 设随机事件 $A$ 与 $B$ 相互独立，且 $P(B) = 0.5$，$P(A - B) = 0.3$，则 $P(B - A) =$ $( )$ \n\n $(A)$ $0.1$ \\qquad $(B)$ $0.2$ \\qquad $(C)$ $0.3$ \\qquad $(D)$ $0.4$"

print("=== 原始输入 ===")
print(original)
print("\n" + "="*100 + "\n")

# 逐步测试处理流程
from latex_normalizer import (
    _remove_escaped_newlines,
    _fix_triple_dollars,
    _convert_latex_delimiters,
    _fix_nested_math,
    _normalize_choice_options,
    _wrap_bare_math_expressions,
    _normalize_summation,
    _normalize_integral,
    _normalize_differential,
    _normalize_limit,
    _fix_subscript_spacing,
    _normalize_trig_functions,
    _normalize_delimiters,
    _fix_chinese_in_math,
    _normalize_katex_compat,
    _normalize_operators,
    _dedup_commands,
    _normalize_whitespace
)

print("=== 逐步测试处理流程 ===")
step = original
print(f"输入长度: {len(step)}")
print(f"输入: {step[:100]}...")
print()

step1 = _remove_escaped_newlines(step)
print("1. _remove_escaped_newlines")
print(f"   输出: {step1[:100]}...")
print()

step2 = _fix_triple_dollars(step1)
print("2. _fix_triple_dollars")
print(f"   输出: {step2[:100]}...")
print()

step3 = _convert_latex_delimiters(step2)
print("3. _convert_latex_delimiters")
print(f"   输出: {step3[:100]}...")
print()

step4 = _fix_nested_math(step3)
print("4. _fix_nested_math")
print(f"   输出: {step4[:100]}...")
print()

step5 = _normalize_choice_options(step4)
print("5. _normalize_choice_options")
print(f"   输出: {step5[:100]}...")
print()

step6 = _wrap_bare_math_expressions(step5)
print("6. _wrap_bare_math_expressions")
print(f"   输出: {step6[:100]}...")
print()

step7 = _normalize_summation(step6)
print("7. _normalize_summation")
print(f"   输出: {step7[:100]}...")
print()

step8 = _normalize_integral(step7)
print("8. _normalize_integral")
print(f"   输出: {step8[:100]}...")
print()

step9 = _normalize_differential(step8)
print("9. _normalize_differential")
print(f"   输出: {step9[:100]}...")
print()

step10 = _normalize_limit(step9)
print("10. _normalize_limit")
print(f"    输出: {step10[:100]}...")
print()

step11 = _fix_subscript_spacing(step10)
print("11. _fix_subscript_spacing")
print(f"    输出: {step11[:100]}...")
print()

step12 = _normalize_trig_functions(step11)
print("12. _normalize_trig_functions")
print(f"    输出: {step12[:100]}...")
print()

step13 = _normalize_delimiters(step12)
print("13. _normalize_delimiters")
print(f"    输出: {step13[:100]}...")
print()

step14 = _fix_chinese_in_math(step13)
print("14. _fix_chinese_in_math")
print(f"    输出: {step14[:100]}...")
print()

step15 = _normalize_katex_compat(step14)
print("15. _normalize_katex_compat")
print(f"    输出: {step15[:100]}...")
print()

step16 = _normalize_operators(step15)
print("16. _normalize_operators")
print(f"    输出: {step16[:100]}...")
print()

step17 = _dedup_commands(step16)
print("17. _dedup_commands")
print(f"    输出: {step17[:100]}...")
print()

step18 = _normalize_whitespace(step17)
print("18. _normalize_whitespace")
print(f"    输出: {step18[:100]}...")
print()

print("="*100)
print("=== 最终结果 ===")
result = normalize_latex_style(original)
print(result)
