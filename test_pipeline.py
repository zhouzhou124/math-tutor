#!/usr/bin/env python3
"""测试完整公式渲染管道"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from latex_utils import split_latex_text, render_segments, clean_markdown

# 测试包含被分割命令的文本
test_text = """
标准解法：

步骤1：计算极限
$\\lim_{x\\to0} \\frac{\\s in x}{x}$

步骤2：由于 \\s in x ∈ [-1,1]，当x→0时，\\s in x ≈ x

步骤3：因此 $\\lim_{x\\to0} \\frac{\\s in x}{x} = 1$
"""

print("=== 原始文本 ===")
print(test_text)
print()

print("=== 清理后 ===")
cleaned = clean_markdown(test_text)
print(cleaned)
print()

print("=== 分割结果 ===")
segments = split_latex_text(cleaned)
for i, seg in enumerate(segments):
    print(f"片段{i+1}: type={seg['type']}, content={repr(seg['content'])}")
print()

print("=== 渲染结果 ===")
rendered = render_segments(segments)
print(rendered)
print()

# 验证关键修复
print("=== 验证修复效果 ===")
if '\\sin' in rendered and '\\frac' in rendered and '\\lim' in rendered:
    print("[PASS] 被分割命令修复成功")
else:
    print("[FAIL] 被分割命令修复失败")

if '\\in' in rendered:
    print("[PASS] Unicode符号转换成功")
else:
    print("[FAIL] Unicode符号转换失败")
