#!/usr/bin/env python3
"""测试公式渲染修复效果"""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from latex_utils import split_latex_text, render_segments
from renderers.components.grading_result import _restore_backslashes

# 测试用例 - 包含图片中的错误模式
test_cases = [
    # 被分割的命令
    (r'\s in x', r'\sin x', "sin被分割"),
    (r'\c os x', r'\cos x', "cos被分割"),
    (r'\t an x', r'\tan x', "tan被分割"),
    (r'\l og x', r'\log x', "log被分割"),
    (r'\l n x', r'\ln x', "ln被分割"),
    
    # Unicode符号转换
    ("x ∈ R", r"x \in R", "Unicode∈转换"),
    ("a ≤ b", r"a \leq b", "Unicode≤转换"),
    ("a ≥ b", r"a \geq b", "Unicode≥转换"),
    ("∞", r"\infty", "Unicode∞转换"),
    ("α + β", r"\alpha + \beta", "希腊字母转换"),
    
    # 组合测试
    (r'\s in(x) + \c os(x) = 1', r'\sin(x) + \cos(x) = 1', "三角函数组合"),
    ("x ∈ [-∞, +∞]", r"x \in [-\infty, +\infty]", "区间表示"),
    (r'\lim_{x→0} \frac{\s in x}{x}', r'\lim_{x\rightarrow0} \frac{\sin x}{x}', "极限公式"),
]

print("=" * 60)
print("测试公式渲染修复效果")
print("=" * 60)

all_passed = True

for input_text, expected, desc in test_cases:
    print(f"\n【测试】{desc}")
    print(f"输入: {repr(input_text)}")
    
    # 测试 _restore_backslashes
    result = _restore_backslashes(input_text)
    print(f"修复后: {repr(result)}")
    
    # 检查是否修复成功
    if result == expected:
        print("[PASS] 通过")
    else:
        print(f"[FAIL] 失败 (期望: {repr(expected)})")
        all_passed = False

print("\n" + "=" * 60)
if all_passed:
    print("所有测试通过!")
else:
    print("部分测试失败")

# 测试完整管道
print("\n" + "=" * 60)
print("测试完整渲染管道")
print("=" * 60)

test_text = """
标准解法：

步骤1：计算极限
$\\lim_{x\\to0} \\frac{\\s in x}{x}$

步骤2：由于 \\s in x ∈ [-1,1]，当x→0时，\\s in x ≈ x

步骤3：因此 $\\lim_{x\\to0} \\frac{\\s in x}{x} = 1$
"""

print("原始文本:")
print(test_text)
print("\n--- 分割结果 ---")
segments = split_latex_text(test_text)
for i, seg in enumerate(segments):
    print(f"片段{i+1}: type={seg['type']}, content={repr(seg['content'])}")

print("\n--- 渲染结果 ---")
rendered = render_segments(segments)
print(rendered)
