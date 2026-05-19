"""
考研数学真题解析与LaTeX结构化引擎
====================================

端到端管道:
  Raw text → LaTeX修复 → 格式检测 → (OCR清理) → 题目分割 → 答案提取 → 解答匹配 → 验证 → JSON

用法:
  from exam_parser import ExamParserPipeline
  pipeline = ExamParserPipeline()
  result = pipeline.process_file("papers/2024年数学(一)真题.md")
  importer.import_dict(result.questions)
"""

from .latex_fixer import LaTeXFixer, LaTeXReport
from .format_detector import FormatDetector, FormatInfo, PaperFormat
from .question_splitter import QuestionSplitter, QuestionBlock, SplitResult
from .answer_extractor import AnswerExtractor, ExtractedAnswer
from .solution_matcher import SolutionMatcher, SolutionMatch
from .ocr_cleaner import OCRCleaner, OCRReport
from .pipeline import ExamParserPipeline, PipelineResult, StageResult
from .latex_exam_parser import LatexExamParser, LatexNormalizeReport
