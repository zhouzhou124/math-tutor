r"""
LaTeX 命令保护机制 — 防止反斜杠命令被错误处理

问题根源分析：
1. \\sin x → \\s ∈ x：\\sin 中的 "in" 被误认为是集合符号 ∈
2. \\sqrt → \\d：\\sqrt 中的 "s" 后跟空格被误认为微分 ds

解决方案：
- 在任何处理之前，先保护所有已存在的 \\命令形式
- 使用唯一占位符替换，处理完成后再恢复
- 确保不会误处理单字符反斜杠（如 \\s, \\d 等）
"""

import re
from typing import Dict, Tuple


class LaTeXProtector:
    """
    LaTeX 命令保护类
    
    使用方式：
        protector = LaTeXProtector()
        protected_text = protector.protect(text)
        # ... 进行各种处理 ...
        restored_text = protector.restore(protected_text)
    """
    
    def __init__(self):
        self._placeholders: Dict[str, str] = {}
        self._counter = 0
    
    def protect(self, text: str) -> str:
        """保护所有 LaTeX 命令"""
        if not text:
            return text
        
        self._placeholders = {}
        self._counter = 0
        temp_text = text
        
        # 模式1：保护所有 \命令 形式（\后面跟字母）
        # 匹配 \[a-zA-Z]+，包括单字符命令如 \s, \d
        cmd_pattern = re.compile(r'\\[a-zA-Z]+')
        matches = list(cmd_pattern.finditer(temp_text))
        
        # 从后往前处理，避免位置偏移
        for match in reversed(matches):
            full_cmd = match.group(0)  # 如 \sin, \sqrt, \s, \d 等
            placeholder = self._generate_placeholder()
            temp_text = temp_text[:match.start()] + placeholder + temp_text[match.end():]
            self._placeholders[placeholder] = full_cmd
        
        # 模式2：保护可能被误认为微分的模式（如 \s x）
        # 这会在后续处理中被错误转换为 \,\mathrm{d} x
        # 保护形式：\字母 后跟空格和变量
        single_char_pattern = re.compile(r'(\\[a-zA-Z])\s+([a-zA-Z])')
        matches = list(single_char_pattern.finditer(temp_text))
        for match in reversed(matches):
            full_pattern = match.group(0)  # 如 "\s x"
            placeholder = self._generate_placeholder()
            temp_text = temp_text[:match.start()] + placeholder + temp_text[match.end():]
            self._placeholders[placeholder] = full_pattern
        
        return temp_text
    
    def restore(self, text: str) -> str:
        """恢复被保护的 LaTeX 命令"""
        if not text:
            return text
        
        restored = text
        for placeholder, original in self._placeholders.items():
            restored = restored.replace(placeholder, original)
        
        return restored
    
    def _generate_placeholder(self) -> str:
        """生成唯一的占位符"""
        placeholder = f'\x00LATEX{self._counter}\x00'
        self._counter += 1
        return placeholder


def safe_process_latex(text: str, processing_func) -> str:
    """
    安全处理 LaTeX 文本的包装函数
    
    Args:
        text: 原始 LaTeX 文本
        processing_func: 处理函数，接收字符串并返回处理后的字符串
    
    Returns:
        安全处理后的 LaTeX 文本
    """
    protector = LaTeXProtector()
    protected = protector.protect(text)
    processed = processing_func(protected)
    restored = protector.restore(processed)
    return restored


# ═══════════════════════════════════════════════
# 全局便捷函数
# ═══════════════════════════════════════════════

_latex_protector = None


def protect_latex(text: str) -> Tuple[str, int]:
    """
    保护 LaTeX 命令并返回保护后的文本和占位符数量
    
    Returns:
        (protected_text, placeholder_count)
    """
    global _latex_protector
    if _latex_protector is None:
        _latex_protector = LaTeXProtector()
    
    protected = _latex_protector.protect(text)
    count = len(_latex_protector._placeholders)
    return protected, count


def restore_latex(text: str) -> str:
    """恢复被保护的 LaTeX 命令"""
    global _latex_protector
    if _latex_protector is None:
        return text
    return _latex_protector.restore(text)