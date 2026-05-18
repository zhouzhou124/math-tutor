r"""
LaTeX 保护机制单元测试

测试目标：
1. \sin x 不应该变成 \s ∈ x
2. \sqrt 不应该变成 \d
3. \sqrt{s} 中的 s 不应该被误认为微分符号
"""

import sys
import os
import io

# 设置标准输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rendering.latex_protector import LaTeXProtector, safe_process_latex


def test_latex_protector():
    """测试 LaTeXProtector 类 - 核心保护机制"""
    protector = LaTeXProtector()
    
    test_cases = [
        # (输入, 期望输出)
        (r"\sin x", r"\sin x"),
        (r"\sqrt{x}", r"\sqrt{x}"),
        (r"\cos x + \sin x", r"\cos x + \sin x"),
        (r"\lim_{x\to0}\frac{f(x)}{\sqrt{x}}", r"\lim_{x\to0}\frac{f(x)}{\sqrt{x}}"),
        (r"$\sin x$", r"$\sin x$"),
        (r"$$\sqrt{x} + \sin x$$", r"$$\sqrt{x} + \sin x$$"),
        (r"\s", r"\s"),  # 单字符命令也应该被保护
        (r"\d", r"\d"),  # 单字符命令也应该被保护
        (r"\sqrt{s}", r"\sqrt{s}"),  # \sqrt{s} 不应该被破坏
    ]
    
    print("测试 LaTeXProtector 类...")
    all_passed = True
    for i, (input_text, expected) in enumerate(test_cases):
        protected = protector.protect(input_text)
        restored = protector.restore(protected)
        
        if restored == expected:
            print("测试 {}: 通过".format(i+1))
        else:
            print("测试 {}: 失败".format(i+1))
            print("  输入: {}".format(input_text))
            print("  保护后: {}".format(protected))
            print("  恢复后: {}".format(restored))
            print("  期望: {}".format(expected))
            all_passed = False
    
    return all_passed


def test_safe_process_latex():
    """测试 safe_process_latex 函数 - 模拟破坏性处理"""
    
    def mock_processing(text):
        """模拟可能破坏 LaTeX 的处理过程（如 OCR 后处理）"""
        # 模拟把 "in" 替换为 "∈" 的错误处理
        return text.replace("in", "∈")
    
    test_cases = [
        # \sin 中的 "in" 不应该被替换为 "∈"
        (r"\sin x", r"\sin x"),
        (r"\sqrt{x}", r"\sqrt{x}"),
        (r"$\sin x$", r"$\sin x$"),
        (r"sin x", r"s∈ x"),  # 没有反斜杠的 sin 应该被替换（这是预期行为）
    ]
    
    print("\n测试 safe_process_latex 函数...")
    all_passed = True
    for i, (input_text, expected) in enumerate(test_cases):
        result = safe_process_latex(input_text, mock_processing)
        
        if result == expected:
            print("测试 {}: 通过".format(i+1))
        else:
            print("测试 {}: 失败".format(i+1))
            print("  输入: {}".format(input_text))
            print("  输出: {}".format(result))
            print("  期望: {}".format(expected))
            all_passed = False
    
    return all_passed


def test_differential_normalization_protection():
    """测试微分规范化中的保护机制 - \sqrt 和 \sin 不应该被破坏"""
    from latex_normalizer import _normalize_differential
    
    test_cases = [
        # 关键测试：保护机制应该防止 \sqrt 和 \sin 被破坏
        (r"$\sqrt{x}$", r"$\sqrt{x}$"),          # \sqrt 不应该被破坏
        (r"$\sin x$", r"$\sin x$"),              # \sin 不应该被破坏
        (r"$\sqrt{s}$", r"$\sqrt{s}$"),          # \sqrt{s} 不应该变成 \sqrt{\mathrm{d}s}
        (r"$\sin s$", r"$\sin s$"),              # \sin s 中的 s 不应该被转换
        (r"$\sqrt{x} + \sin x$", r"$\sqrt{x} + \sin x$"),  # 两者共存
    ]
    
    print("\n测试微分规范化保护机制...")
    all_passed = True
    for i, (input_text, expected) in enumerate(test_cases):
        result = _normalize_differential(input_text)
        
        if result == expected:
            print("测试 {}: 通过".format(i+1))
        else:
            print("测试 {}: 失败".format(i+1))
            print("  输入: {}".format(input_text))
            print("  输出: {}".format(result))
            print("  期望: {}".format(expected))
            all_passed = False
    
    return all_passed


def main():
    """运行所有测试"""
    print("=" * 60)
    print("LaTeX 保护机制单元测试")
    print("=" * 60)
    
    results = [
        test_latex_protector(),
        test_safe_process_latex(),
        test_differential_normalization_protection(),
    ]
    
    print("\n" + "=" * 60)
    if all(results):
        print("所有测试通过！")
        return 0
    else:
        print("部分测试失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())