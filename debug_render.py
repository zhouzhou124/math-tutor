"""调试LaTeX渲染问题"""
import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("调试LaTeX渲染问题")
print("=" * 80)

# 先检查错误记录数据
print("\n[1] 检查错误记录数据...")
try:
    from repository import ErrorRecordRepository
    
    # 初始化仓库
    db_path = Path(__file__).parent / "storage" / "app.db"
    data_dir = Path(__file__).parent / "storage"
    
    repo = ErrorRecordRepository(db_path, data_dir)
    
    # 获取用户默认记录
    records = repo.get_records("user_default", limit=1)
    
    if records:
        record = records[0]
        print(f"\n找到 {len(records)} 条记录")
        print(f"\n记录内容预览:")
        for key, value in list(record.items())[:10]:  # 只显示前10个字段
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
        
        # 查找包含数学内容的字段
        print("\n[2] 查找数学内容字段...")
        math_fields = ['correct_answer', 'solution', 'analysis']
        for field in math_fields:
            if field in record:
                value = record[field]
                if value and isinstance(value, str) and any(c in value for c in ['\\', '$', '{', '}']):
                    print(f"\n找到字段 {field}，包含数学内容")
                    print(f"内容预览:\n{repr(value[:500])}")
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

# 测试渲染过程
print("\n" + "=" * 80)
print("[3] 测试渲染过程")
print("=" * 80)

# 从截图中提取示例内容
test_content = r"""
原方程为 \(y' + xy = e^{-\frac{x^2}{2}}\)，这是一阶线性非齐次微分方程，其中 \(P(x) = x\)，\(Q(x) = e^{-\frac{x^2}{2}}\)。

【1分】计算积分因子：
\(\mu(x)=e^{\int P(x)\mathrm{d}x}=e^{\int x\mathrm{d}x}=e^{\frac{x^2}{2}}\)

【2.5分】代入通解公式：
\(y=e^{-\int P(x)\mathrm{d}x}\left(\int Q(x)e^{\int P(x)\mathrm{d}x}\mathrm{d}x + C\right)=e^{-\frac{x^2}{2}}\left(\int e^{-\frac{x^2}{2}}\cdot e^{\frac{x^2}{2}}\mathrm{d}x + C\right)=e^{-\frac{x^2}{2}}\left(\int 1\mathrm{d}x + C\right)=e^{-\frac{x^2}{2}}(x + C)\)
"""

try:
    from latex_utils import split_latex_text, render_ast
    
    print(f"\n输入内容: {repr(test_content[:300])}...")
    
    # 测试分割
    print("\n执行 split_latex_text...")
    segments = split_latex_text(test_content)
    print(f"分割结果: {len(segments)} 段")
    for i, seg in enumerate(segments):
        print(f"  [{i}] {seg['type']}: {repr(seg['content'][:80])}")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

# 测试UnifiedRenderer
print("\n" + "=" * 80)
print("[4] 测试 UnifiedRenderer")
print("=" * 80)
try:
    from rendering.unified_renderer import UnifiedRenderer
    renderer = UnifiedRenderer()
    
    print("\n测试 _wrap_bare_math...")
    test_latex = r"\mu(x)=e^{\int P(x)\mathrm{d}x}=e^{\int x\mathrm{d}x}=e^{\frac{x^2}{2}}"
    result = renderer._wrap_bare_math(test_latex)
    print(f"输入: {repr(test_latex)}")
    print(f"输出: {repr(result)}")
    
    # 测试完整的渲染流程
    print("\n测试完整渲染流程...")
    # 创建一个简单的Streamlit测试环境
    import streamlit as st
    with st.container():
        st.header("测试渲染")
        # 使用renderer直接渲染
        renderer.render(test_content)
        print("渲染完成")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("调试完成")
print("=" * 80)
