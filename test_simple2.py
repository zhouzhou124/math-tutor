#!/usr/bin/env python3
"""简化测试 - 使用lambda函数"""
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
    # 使用lambda函数避免替换字符串被解析
    result = re.sub(pattern, lambda m, t=target: t, result)
    print(f"结果: {repr(result)}")
