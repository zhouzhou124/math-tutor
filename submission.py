"""submission.py — 统一输入层 (Input Layer)

所有题型共用的基础层，负责将不同格式的输入统一转换为结构化的 StudentSubmission。

支持的输入格式：
  - 图片 (PNG, JPG, JPEG)
  - 手写 (通过 OCR 识别)
  - LaTeX (数学公式文本)
  - 纯文本 (普通文本)

统一转换为：
  StudentSubmission(
      raw_text,      # 原始文本
      latex,         # 标准化 LaTeX
      images,        # 原始图片列表
      metadata,      # 元信息
  )

架构：
  ┌─────────────────────────────────────────────┐
  │              Input Layer                     │
  │  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
  │  │  Image  │  │  LaTeX │  │  Text   │      │
  │  │ Handler │  │ Parser │  │ Parser  │      │
  │  └────┬────┘  └────┬────┘  └────┬────┘      │
  │       │             │            │           │
  │       ▼             ▼            ▼           │
  │  ┌─────────────────────────────────────┐    │
  │  │       Submission Normalizer          │    │
  │  │   (LaTeX 标准化 + 文本归一化)        │    │
  │  └─────────────────┬───────────────────┘    │
  │                    ▼                         │
  │  ┌─────────────────────────────────────┐    │
  │  │       StudentSubmission              │    │
  │  └─────────────────────────────────────┘    │
  └─────────────────────────────────────────────┘
"""

from __future__ import annotations

import base64
import re
import json
from dataclasses import dataclass, field
from typing import Optional, Union, List
from enum import Enum
from pathlib import Path


# ═══════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════

class InputSource(Enum):
    """输入来源类型"""
    IMAGE_OCR = "image_ocr"           # 图片 OCR 识别
    HANDWRITING = "handwriting"         # 手写输入（通过 OCR）
    LATEX_TEXT = "latex_text"           # LaTeX 公式文本
    PLAIN_TEXT = "plain_text"           # 纯文本
    MIXED = "mixed"                     # 混合输入


@dataclass
class SubmissionMetadata:
    """提交的元信息"""
    source: InputSource = InputSource.PLAIN_TEXT
    confidence: float = 1.0             # 识别置信度
    language: str = "zh"                 # 语言
    ocr_engine: str = ""                 # OCR 引擎
    timestamp: str = ""                  # 时间戳
    raw_ext: dict = field(default_factory=dict)  # 原始扩展数据


@dataclass
class StudentSubmission:
    """
    统一的学生作答结构

    Attributes:
        raw_text: 原始文本（未处理的原始输入）
        latex: 标准化 LaTeX 文本
        images: 原始图片列表（base64 编码或文件路径）
        metadata: 元信息
        question_id: 关联的题目 ID（可选）
    """
    raw_text: str = ""
    latex: str = ""
    images: List[str] = field(default_factory=list)
    metadata: SubmissionMetadata = field(default_factory=SubmissionMetadata)
    question_id: str = ""

    def is_empty(self) -> bool:
        """检查是否为空提交"""
        return not (self.raw_text.strip() or self.latex.strip() or self.images)

    def get_primary_text(self) -> str:
        """获取主要文本（优先返回 LaTeX）"""
        return self.latex.strip() if self.latex.strip() else self.raw_text.strip()

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "raw_text": self.raw_text,
            "latex": self.latex,
            "images": self.images,
            "metadata": {
                "source": self.metadata.source.value,
                "confidence": self.metadata.confidence,
                "language": self.metadata.language,
                "ocr_engine": self.metadata.ocr_engine,
                "timestamp": self.metadata.timestamp,
            },
            "question_id": self.question_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StudentSubmission":
        """从字典反序列化"""
        metadata = SubmissionMetadata()
        if "metadata" in data:
            m = data["metadata"]
            metadata.source = InputSource(m.get("source", "plain_text"))
            metadata.confidence = m.get("confidence", 1.0)
            metadata.language = m.get("language", "zh")
            metadata.ocr_engine = m.get("ocr_engine", "")
            metadata.timestamp = m.get("timestamp", "")

        return cls(
            raw_text=data.get("raw_text", ""),
            latex=data.get("latex", ""),
            images=data.get("images", []),
            metadata=metadata,
            question_id=data.get("question_id", ""),
        )


# ═══════════════════════════════════════════════
# 输入处理器
# ═══════════════════════════════════════════════

class ImageHandler:
    """图片处理器"""

    SUPPORTED_FORMATS = {"png", "jpg", "jpeg", "gif", "webp"}

    @staticmethod
    def is_image(path: str) -> bool:
        """检查是否为支持的图片格式"""
        ext = Path(path).suffix.lower().lstrip(".")
        return ext in ImageHandler.SUPPORTED_FORMATS

    @staticmethod
    def encode_image(image_path: str) -> str:
        """将图片编码为 base64"""
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "gif", "webp") else "image/png"
        return f"data:{mime};base64,{data}"

    @staticmethod
    def decode_base64_image(data_uri: str) -> bytes:
        """从 data URI 解码图片"""
        if ";base64," in data_uri:
            _, encoded = data_uri.split(";base64,", 1)
            return base64.b64decode(encoded)
        return b""

    @staticmethod
    def get_mime_type(image_path: str) -> str:
        """获取图片的 MIME 类型"""
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        return mime_map.get(ext, "image/png")


class LaTeXParser:
    """LaTeX 公式解析器"""

    @staticmethod
    def is_latex(text: str) -> bool:
        """快速判断文本是否包含 LaTeX"""
        if not text:
            return False
        latex_indicators = [
            r"\$",                     # $ 包裹的公式
            r"\\begin\{",              # LaTeX 环境
            r"\\frac", r"\\sqrt",     # 常见命令
            r"\^|_",                   # 上标下标
            r"\\left|\\right",         # 分隔符
            r"\\int|\\sum|\\prod",     # 大运算符
        ]
        return any(re.search(p, text) for p in latex_indicators)

    @staticmethod
    def extract_formulas(text: str) -> List[str]:
        """提取所有 LaTeX 公式"""
        formulas = []

        # 提取 $$...$$  display math
        formulas.extend(re.findall(r'\$\$(.+?)\$\$', text, re.DOTALL))

        # 提取 $...$ inline math
        # 排除已经匹配过的 $$
        single_dollar_pattern = r'(?<!\$)\$(.+?)\$(?!\$)'
        for m in re.finditer(single_dollar_pattern, text, re.DOTALL):
            formulas.append(m.group(1))

        return formulas

    @staticmethod
    def normalize_latex(text: str) -> str:
        """标准化 LaTeX 文本"""
        if not text:
            return text

        # 修复常见的格式问题
        # 1. 修复破损的 $ 配对
        dollar_count = text.count('$') - text.count('$$') * 2
        if dollar_count % 2 != 0:
            text = text.rstrip('$') + '$'

        # 2. 规范化空格
        text = re.sub(r'\\ +', r'\\ ', text)  # 多个空格合并
        text = re.sub(r' {2,}', ' ', text)     # 多个空格合并

        # 3. 规范化换行
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    @staticmethod
    def remove_latex_wrappers(text: str) -> str:
        """移除 LaTeX 包裹符号，保留内容"""
        # 移除 $$...$$
        text = re.sub(r'\$\$(.+?)\$\$', r'\1', text, flags=re.DOTALL)
        # 移除 $...$
        text = re.sub(r'(?<!\$)\$(.+?)\$(?!\$)', r'\1', text, flags=re.DOTALL)
        return text


class TextParser:
    """纯文本解析器"""

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本"""
        if not text:
            return text

        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

        # 规范化换行
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 移除首尾空白
        text = text.strip()

        return text

    @staticmethod
    def is_handwriting_candidate(text: str) -> bool:
        """判断是否为手写候选文本（OCR 结果）"""
        if not text:
            return False

        # 手写特征：包含多个错别字标记、奇怪的字符
        handwriting_indicators = [
            r'[■□]',           # OCR 错别字标记
            r'[??]',           # 无法识别的字符
            r'[\x00-\x1f]',    # 控制字符
        ]

        # 如果包含这些特征，可能是 OCR 结果
        for indicator in handwriting_indicators:
            if re.search(indicator, text):
                return True

        # 如果文本很短且包含数字和数学符号，可能是 OCR
        if len(text) < 50 and re.search(r'\d', text):
            return True

        return False


# ═══════════════════════════════════════════════
# 统一入口：SubmissionBuilder
# ═══════════════════════════════════════════════

class SubmissionBuilder:
    """
    学生作答统一构建器

    用法：
        # 从文本构建
        submission = SubmissionBuilder.from_text("我的答案是 $x=2$")

        # 从图片构建
        submission = SubmissionBuilder.from_image("answer.png")

        # 合并多个输入
        submission = SubmissionBuilder.merge([
            SubmissionBuilder.from_text("第一部分..."),
            SubmissionBuilder.from_image("second.png"),
        ])
    """

    @staticmethod
    def from_text(
        text: str,
        source: InputSource = InputSource.PLAIN_TEXT,
        question_id: str = "",
    ) -> StudentSubmission:
        """
        从纯文本构建 Submission

        Args:
            text: 原始文本
            source: 输入来源
            question_id: 关联题目 ID

        Returns:
            StudentSubmission
        """
        text = TextParser.clean_text(text)
        latex = LaTeXParser.normalize_latex(text) if LaTeXParser.is_latex(text) else text

        metadata = SubmissionMetadata(source=source)
        if source == InputSource.LATEX_TEXT:
            metadata.source = InputSource.LATEX_TEXT

        return StudentSubmission(
            raw_text=text,
            latex=latex,
            images=[],
            metadata=metadata,
            question_id=question_id,
        )

    @staticmethod
    def from_latex(
        latex_text: str,
        question_id: str = "",
    ) -> StudentSubmission:
        """
        从 LaTeX 公式构建 Submission

        Args:
            latex_text: LaTeX 公式文本
            question_id: 关联题目 ID

        Returns:
            StudentSubmission
        """
        latex_text = LaTeXParser.normalize_latex(latex_text)

        return StudentSubmission(
            raw_text=latex_text,
            latex=latex_text,
            images=[],
            metadata=SubmissionMetadata(source=InputSource.LATEX_TEXT),
            question_id=question_id,
        )

    @staticmethod
    def from_image(
        image_path: str,
        ocr_result: str = "",
        ocr_engine: str = "pytesseract",
        confidence: float = 0.8,
        question_id: str = "",
    ) -> StudentSubmission:
        """
        从图片构建 Submission

        Args:
            image_path: 图片路径
            ocr_result: OCR 识别结果
            ocr_engine: OCR 引擎名称
            confidence: 识别置信度
            question_id: 关联题目 ID

        Returns:
            StudentSubmission
        """
        # 编码图片
        try:
            encoded_image = ImageHandler.encode_image(image_path)
        except Exception:
            encoded_image = ""

        # 处理 OCR 结果
        text = TextParser.clean_text(ocr_result)
        latex = LaTeXParser.normalize_latex(text) if text else ""

        metadata = SubmissionMetadata(
            source=InputSource.IMAGE_OCR,
            confidence=confidence,
            ocr_engine=ocr_engine,
        )

        return StudentSubmission(
            raw_text=text,
            latex=latex,
            images=[encoded_image] if encoded_image else [],
            metadata=metadata,
            question_id=question_id,
        )

    @staticmethod
    def from_handwriting(
        image_path: str,
        ocr_result: str = "",
        confidence: float = 0.7,
        question_id: str = "",
    ) -> StudentSubmission:
        """
        从手写图片构建 Submission

        Args:
            image_path: 手写图片路径
            ocr_result: OCR 识别结果
            confidence: 识别置信度
            question_id: 关联题目 ID

        Returns:
            StudentSubmission
        """
        submission = SubmissionBuilder.from_image(
            image_path=image_path,
            ocr_result=ocr_result,
            ocr_engine="handwriting_recognizer",
            confidence=confidence,
            question_id=question_id,
        )
        submission.metadata.source = InputSource.HANDWRITING
        return submission

    @staticmethod
    def merge(
        submissions: List[StudentSubmission],
        question_id: str = "",
    ) -> StudentSubmission:
        """
        合并多个 Submission

        Args:
            submissions: Submission 列表
            question_id: 关联题目 ID

        Returns:
            合并后的 StudentSubmission
        """
        if not submissions:
            return StudentSubmission(question_id=question_id)

        if len(submissions) == 1:
            submissions[0].question_id = question_id
            return submissions[0]

        # 合并文本
        raw_texts = []
        latex_texts = []
        all_images = []
        confidences = []

        for sub in submissions:
            if sub.raw_text.strip():
                raw_texts.append(sub.raw_text)
            if sub.latex.strip():
                latex_texts.append(sub.latex)
            all_images.extend(sub.images)
            confidences.append(sub.metadata.confidence)

        # 使用第一个来源作为主要来源
        primary_source = submissions[0].metadata.source

        # 合并文本（用换行分隔）
        raw_text = "\n".join(raw_texts)
        latex = "\n".join(latex_texts)

        # 归一化 LaTeX
        latex = LaTeXParser.normalize_latex(latex)

        # 计算平均置信度
        avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0

        metadata = SubmissionMetadata(
            source=InputSource.MIXED,
            confidence=avg_confidence,
        )

        return StudentSubmission(
            raw_text=raw_text,
            latex=latex,
            images=all_images,
            metadata=metadata,
            question_id=question_id,
        )


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def create_submission(
    text: str = "",
    latex: str = "",
    images: List[str] = None,
    source: str = "plain_text",
    question_id: str = "",
) -> StudentSubmission:
    """
    创建 StudentSubmission 的便捷函数

    Args:
        text: 原始文本
        latex: LaTeX 文本
        images: 图片列表
        source: 来源类型
        question_id: 关联题目 ID

    Returns:
        StudentSubmission
    """
    try:
        input_source = InputSource(source)
    except ValueError:
        input_source = InputSource.PLAIN_TEXT

    metadata = SubmissionMetadata(source=input_source)

    return StudentSubmission(
        raw_text=text or "",
        latex=latex or text or "",  # 如果没有 latex，用 text
        images=images or [],
        metadata=metadata,
        question_id=question_id,
    )


# ═══════════════════════════════════════════════
# 示例用法
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    # 示例 1: 从纯文本创建
    sub1 = SubmissionBuilder.from_text(
        "我的答案是 $x^2 + y^2 = 1$",
        question_id="2013-数一-001"
    )
    print("=== 从文本创建 ===")
    print(f"raw_text: {sub1.raw_text}")
    print(f"latex: {sub1.latex}")
    print(f"is_latex: {LaTeXParser.is_latex(sub1.raw_text)}")

    # 示例 2: 从 LaTeX 创建
    sub2 = SubmissionBuilder.from_latex(
        r"\int_0^1 x^2 dx = \frac{1}{3}",
        question_id="2013-数一-002"
    )
    print("\n=== 从 LaTeX 创建 ===")
    print(f"latex: {sub2.latex}")

    # 示例 3: 合并多个 Submission
    merged = SubmissionBuilder.merge([sub1, sub2], question_id="merged-001")
    print("\n=== 合并 ===")
    print(f"raw_text: {merged.raw_text}")
    print(f"latex: {merged.latex}")
    print(f"images count: {len(merged.images)}")
    print(f"source: {merged.metadata.source.value}")
