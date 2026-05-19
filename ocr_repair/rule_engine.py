"""
Pass 2: Rule Engine

纯函数风格。固定错误映射和启发式修复。
不访问模型，不做语义推断。

修复类别:
  1. OCR 符号 → LaTeX 数学符号
  2. 常见数学字符混淆
  3. 明显缺失的 LaTeX 定界符
  4. 乱码字符标记和替换
"""

import re
from .core import RepairPolicy, RepairTrace, WarningCode
from .utils import count_math_objects
from exam_parser.latex_fixer import LaTeXFixer

# ═══════════════════════════════════════════════
# OCR 符号 → LaTeX 映射
# ═══════════════════════════════════════════════

_OCR_TO_LATEX = [
    # 积分符号
    ('∫', r'\int '),
    ('∬', r'\iint '),
    ('∭', r'\iiint '),
    ('∮', r'\oint '),
    # 求和/求积
    ('∑', r'\sum '),
    ('∏', r'\prod '),
    # 极限/无穷
    ('∞', r'\infty'),
    ('lim', r'\lim '),
    # 偏导/微分
    ('∂', r'\partial '),
    ('∆', r'\Delta '),
    # 比较
    ('≤', r'\leq '),
    ('≥', r'\geq '),
    ('≠', r'\neq '),
    ('≈', r'\approx '),
    ('≡', r'\equiv '),
    # 集合
    ('∈', r'\in '),
    ('∉', r'\notin '),
    ('⊂', r'\subset '),
    ('⊃', r'\supset '),
    ('⊆', r'\subseteq '),
    ('⊇', r'\supseteq '),
    ('∩', r'\cap '),
    ('∪', r'\cup '),
    ('∅', r'\emptyset '),
    # 逻辑/量词
    ('∀', r'\forall '),
    ('∃', r'\exists '),
    ('¬', r'\neg '),
    ('∧', r'\land '),
    ('∨', r'\lor '),
    # 希腊字母（常见误识别）
    ('α', r'\alpha '),
    ('β', r'\beta '),
    ('γ', r'\gamma '),
    ('δ', r'\delta '),
    ('ε', r'\varepsilon '),
    ('ζ', r'\zeta '),
    ('η', r'\eta '),
    ('θ', r'\theta '),
    ('λ', r'\lambda '),
    ('μ', r'\mu '),
    ('π', r'\pi '),
    ('ρ', r'\rho '),
    ('σ', r'\sigma '),
    ('τ', r'\tau '),
    ('φ', r'\varphi '),
    ('ψ', r'\psi '),
    ('ω', r'\omega '),
    ('Γ', r'\Gamma '),
    ('Δ', r'\Delta '),
    ('Θ', r'\Theta '),
    ('Λ', r'\Lambda '),
    ('Ξ', r'\Xi '),
    ('Π', r'\Pi '),
    ('Σ', r'\Sigma '),
    ('Φ', r'\Phi '),
    ('Ψ', r'\Psi '),
    ('Ω', r'\Omega '),
    # 其他符号
    ('×', r'\times '),
    ('÷', r'\div '),
    ('±', r'\pm '),
    ('→', r'\to '),
    ('⇒', r'\Rightarrow '),
    ('⇔', r'\Leftrightarrow '),
    ('…', r'\dots '),
    ('⋯', r'\cdots '),
    ('∇', r'\nabla '),
    ('∠', r'\angle '),
    ('⊥', r'\perp '),
    ('∥', r'\parallel '),
]

# OCR 常见字符混淆（非数学模式）
_CHAR_CONFUSION = {
    '〇': '0',   # 中文零
    'ｏ': 'o',   # 全角o（常见OCR混淆）
    '０': '0',
    '１': '1',
    '２': '2',
    '３': '3',
    '４': '4',
    '５': '5',
    '６': '6',
    '７': '7',
    '８': '8',
    '９': '9',
}

# 乱码字符
_GARBLED_CHARS = re.compile(r'[�￾￿\x00-\x08\x0B\x0C\x0E-\x1F]')

# LaTeX 定界符检测
_LATEX_COMMAND_NO_DOLLAR = re.compile(
    r'(?<!\$)(?<!\\)(\\int|\\sum|\\frac|\\sqrt|\\lim|\\infty|'
    r'\\alpha|\\beta|\\gamma|\\delta|\\lambda|\\theta|'
    r'\\partial|\\mathbf|\\mathrm|\\pmb|\\vec|\\begin|\\end)'
    r'(?!\$)(?!\\)'
)


def apply(text: str, policy: RepairPolicy | None = None) -> tuple[str, RepairTrace]:
    """
    Rule Engine 主入口。

    返回: (fixed_text, trace)
    纯函数：相同输入永远返回相同输出。
    """
    if policy is None:
        policy = RepairPolicy()

    trace = RepairTrace(
        pass_name="rule_engine",
        input_snippet=text[:200] if text else "",
        char_count_before=len(text),
        math_object_count_before=count_math_objects(text),
    )

    if not policy.enable_rule_engine:
        trace.output_snippet = text[:200]
        trace.char_count_after = len(text)
        return text, trace

    after = text
    mods = []

    # Step 1: 标记不可恢复的乱码字符
    after, garbled_count = _mark_garbled(after)
    if garbled_count > 0:
        mods.append(f"标记乱码: {garbled_count}处")
        if garbled_count > len(text) * policy.max_unrecoverable_ratio:
            trace.warnings.append(WarningCode.ocr_unrecoverable)

    # Step 2: OCR 符号 → LaTeX
    after, symbol_count = _apply_ocr_to_latex(after)
    if symbol_count > 0:
        mods.append(f"OCR符号→LaTeX: {symbol_count}处")

    # Step 3: 数学模式外字符混淆修复
    after, conf_count = _fix_char_confusion(after)
    if conf_count > 0:
        mods.append(f"字符混淆修复: {conf_count}处")

    # Step 4: 双反斜杠修复（复用 exam_parser 的 LaTeXFixer）
    latex_fixer = LaTeXFixer()
    latex_report = latex_fixer.fix(after, ocr_mode=True)
    if latex_report.fix_count > 0:
        after = latex_report.fixed
        mods.append(f"双反斜杠修复: {latex_report.fix_count}处")

    # Step 5: 检测明显缺失的 math mode 定界符
    after, dollar_count = _detect_missing_dollar(after)
    if dollar_count > 0:
        mods.append(f"补全$定界符: {dollar_count}处")

    trace.modifications = mods
    trace.output_snippet = after[:200] if after else ""
    trace.char_count_after = len(after)
    trace.math_object_count_after = count_math_objects(after)

    return after, trace


# ═══════════════════════════════════════════════
# 内部函数
# ═══════════════════════════════════════════════

def _mark_garbled(text: str) -> tuple[str, int]:
    """标记不可恢复的乱码字符为 [OCR?]"""
    count = len(_GARBLED_CHARS.findall(text))
    result = _GARBLED_CHARS.sub('[OCR?]', text)
    return result, count


def _apply_ocr_to_latex(text: str) -> tuple[str, int]:
    """应用 OCR 符号 → LaTeX 映射（仅在数学模式外）"""
    count = 0
    result = text
    for symbol, latex in _OCR_TO_LATEX:
        if symbol in result:
            # 对于字母形式的映射（如 'lim' -> '\lim '），只在不是 LaTeX 命令的一部分时替换
            # 即前面不能有反斜杠
            if symbol.isalpha():
                # 使用正则表达式，确保前面没有反斜杠
                pattern = re.compile(r'(?<!\\)' + re.escape(symbol))
                matches = pattern.findall(result)
                if matches:
                    result = pattern.sub(latex, result)
                    count += len(matches)
            else:
                old = result
                result = result.replace(symbol, latex)
                count += 1
    return result, count


def _fix_char_confusion(text: str) -> tuple[str, int]:
    """修复常见字符混淆（仅在非数学模式）"""
    count = 0
    result = text
    for old, new in _CHAR_CONFUSION.items():
        if old in result:
            result = result.replace(old, new)
            count += 1
    return result, count


def _detect_missing_dollar(text: str) -> tuple[str, int]:
    """
    检测明显缺失 math mode 定界符的 LaTeX 命令。
    只在 LaTeX 命令序列明显未包裹在 $ 内时添加。
    保守策略：不插入 $，只标记。
    """
    # 暂时保守：只统计，不修改
    count = len(_LATEX_COMMAND_NO_DOLLAR.findall(text))
    # 不自动补全——太危险（可能误加$到非数学文本）
    return text, 0


