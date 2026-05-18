"""详细测试LaTeX渲染问题"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# 测试样例LaTeX内容（从截图中提取）
test_content = """原方程为

y' + xy = e^{-\\frac{x^2}{2}}

这是一阶线性微分方程，$P(x) = x$，$Q(x) = e^{-x^2/2}$。

识别方程类型，写出积分因子

计算积分因子

\\mu(x)=e^{\\int P(x)\\mathrm{d}x}=e^{\\int x\\mathrm{d}x}=e^{\\frac{x^2}{2}}

正确计算积分因子通解公式 $y=e^{-\\int P(x)\\mathrm{d}x}\\left(\\int Q(x)e^{\\int P(x)\\mathrm{d}x}\\mathrm{d}x + C\\right)$

代入得 $y=e^{-\\frac{x^2}{2}}\\left(\\int e^{\\frac{x^2}{2}}\\cdot e^{-\\frac{x^2}{2}}\\mathrm{d}x + C\\right)=e^{-\\frac{x^2}{2}}\\left(\\int 1\\mathrm{d}x + C\\right)=e^{-\\frac{x^2}{2}}(x + C)$

利用初始条件定常数 $x=0,y=0\\implies C=0$

得出特解表达式第一步最终答案

\\boxed{y(x)=xe^{-\\frac{x^2}{2}}}
"""

print("="*80)
print("测试内容：")
print("="*80)
print(test_content)
print("\n" + "="*80)

# 测试1：测试split_latex_text
print("\n[1] 测试 split_latex_text...")
try:
    from latex_utils import split_latex_text
    segments = split_latex_text(test_content)
    print(f"分割结果 ({len(segments)} 段):")
    for i, seg in enumerate(segments):
        seg_type = seg.get('type', 'text')
        content = seg.get('content', '')[:100]
        print(f"  [{i}] {seg_type}: {repr(content)}...")
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 测试2：测试safe_latex
print("\n[2] 测试 safe_latex...")
try:
    from latex_utils import safe_latex
    result = safe_latex(test_content)
    print(f"safe_latex 结果 (前500字符):\n{result[:500]}...")
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 测试3：测试UnifiedRenderer
print("\n[3] 测试 UnifiedRenderer...")
try:
    from rendering.unified_renderer import UnifiedRenderer
    renderer = UnifiedRenderer()
    
    # 分步测试
    print("\n  3.1 测试 _clean_markdown...")
    cleaned = renderer._clean_markdown(test_content)
    print(f"  _clean_markdown 结果 (前300字符):\n  {repr(cleaned[:300])}...")
    
    print("\n  3.2 测试 _wrap_bare_math...")
    wrapped = renderer._wrap_bare_math(cleaned)
    print(f"  _wrap_bare_math 结果:\n{repr(wrapped)}")
    
    print("\n  3.3 测试完整渲染...")
    result = renderer.render(test_content)
    print(f"  完整渲染结果类型: {type(result)}")
    if hasattr(result, '__len__'):
        print(f"  完整渲染结果长度: {len(result)}")
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()

# 测试4：测试具体的LaTeX片段
print("\n[4] 测试具体的LaTeX片段...")
test_latex_1 = r"\mu(x)=e^{\int P(x)\mathrm{d}x}"
test_latex_2 = r"e^{\frac{x^2}{2}}"
test_latex_3 = r"\boxed{y(x)=xe^{-\frac{x^2}{2}}}"

print(f"\n  测试1: {repr(test_latex_1)}")
print(f"  测试2: {repr(test_latex_2)}")
print(f"  测试3: {repr(test_latex_3)}")

try:
    from rendering.unified_renderer import UnifiedRenderer
    renderer = UnifiedRenderer()
    
    print("\n  应用 _wrap_bare_math:")
    for i, latex in enumerate([test_latex_1, test_latex_2, test_latex_3], 1):
        result = renderer._wrap_bare_math(latex)
        print(f"  [{i}] 输入: {repr(latex)}")
        print(f"      输出: {repr(result)}")
except Exception as e:
    print(f"✗ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("测试完成")
print("="*80)
