#!/usr/bin/env python3
"""简化测试"""
import re

# 测试修复被分割的命令
split_cmds = [
    (r'\sin', r'\\s\s*in'),
    (r'\cos', r'\\c\s*os'),
    (r'\tan', r'\\t\s*an'),
]

test_input = r'\s in x'
print(f"输入: {repr(test_input)}")

result = test_input
for target, pattern in split_cmds:
    print(f"尝试模式: {pattern}, 替换为: {target}")
    result = re.sub(pattern, target, result)
    print(f"结果: {repr(result)}")
