"""ocr_repair 共享工具函数"""

import re


def count_math_objects(text: str) -> int:
    """统计文本中的数学对象数量（LaTeX命令+数学符号）。
    这是权威实现，validator.py 和 benchmark runner 共用。
    """
    patterns = [
        r'\\int\b', r'\\iint\b', r'\\iiint\b', r'\\oint\b',
        r'\\sum\b', r'\\prod\b', r'\\lim\b', r'\\infty\b',
        r'\\frac\{', r'\\sqrt\{',
        r'\\begin\{', r'\\end\{',
        r'\\left', r'\\right',
        r'\$\$',
        r'\\alpha\b', r'\\beta\b', r'\\gamma\b',
        r'\\lambda\b', r'\\theta\b', r'\\pi\b',
        r'\\sigma\b', r'\\omega\b',
        r'\\mathbf\b', r'\\mathrm\b', r'\\vec\b',
        r'\\det\b', r'\\operatorname',
        r'\\times\b', r'\\div\b', r'\\pm\b',
        r'\\cdot\b', r'\\cdots\b',
        r'\\to\b', r'\\rightarrow\b', r'\\Rightarrow\b',
        r'\\partial\b', r'\\nabla\b',
        r'\\text\{', r'\\boxed\{',
        r'\\mathrm\{d\}', r'\\mathrm\{e\}',
        r'\\Delta\b', r'\\Gamma\b', r'\\Lambda\b',
        r'\\Sigma\b', r'\\Phi\b', r'\\Psi\b', r'\\Omega\b',
    ]
    count = 0
    for pat in patterns:
        count += len(re.findall(pat, text))
    return count
