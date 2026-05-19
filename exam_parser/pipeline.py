"""
端到端管道 — 串联所有处理阶段

用法:
  pipeline = ExamParserPipeline()
  result = pipeline.process_file("papers/2024年数学(一)真题.md")
  # result.questions 可直接传给 QuestionImporter.import_dict()

CLI:
  python -m exam_parser.pipeline process <file>
  python -m exam_parser.pipeline batch <dir>
"""

import sys
import time
import json
from pathlib import Path
from dataclasses import dataclass, field

from .latex_fixer import LaTeXFixer
from .format_detector import FormatDetector, PaperFormat
from .question_splitter import QuestionSplitter, QuestionBlock
from .state_machine_splitter import StateMachineSplitter
from .answer_extractor import AnswerExtractor
from .solution_matcher import SolutionMatcher
from .ocr_cleaner import OCRCleaner

from config import MATH_TYPES, QUESTION_TYPES, DIFFICULTY_LEVELS, STORAGE_DIR
from database.question_db import KNOWLEDGE_TAGS


@dataclass
class StageResult:
    stage: str
    success: bool
    input_size: int
    output_size: int
    duration_ms: float
    details: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    year: int
    math_type: str
    format: str
    total_questions: int
    questions: list[dict]
    stats: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report_path: str | None = None


class ExamParserPipeline:
    """端到端考研数学真题解析管道"""

    SOLUTIONS_BASE = "E:/math_tutor/storage/math1_source/Kaoyan-Math1-Papers-main/solutions"

    def __init__(self, db=None, llm_client=None):
        self.db = db
        self.llm_client = llm_client
        self.latex_fixer = LaTeXFixer()
        self.format_detector = FormatDetector()
        self.legacy_splitter = QuestionSplitter()
        self.state_splitter = StateMachineSplitter()
        self.answer_extractor = AnswerExtractor()
        self.solution_matcher = SolutionMatcher(self.SOLUTIONS_BASE)
        self.ocr_cleaner = OCRCleaner(llm_client)

    def process_file(self, file_path: str, math_type: str = None,
                     year: int = None) -> PipelineResult:
        """处理单份试卷文件（MD / TXT / TEX）"""
        path = Path(file_path)
        if not path.exists():
            return PipelineResult(
                year=year or 0, math_type=math_type or "", format="unknown",
                total_questions=0, questions=[],
                errors=[f"文件不存在: {file_path}"],
            )

        if path.suffix.lower() == ".tex":
            from .latex_exam_parser import LatexExamParser
            return LatexExamParser().parse_file(
                str(path), year=year, math_type=math_type or "数学一", pipeline=self,
            )

        text = path.read_text(encoding="utf-8")
        return self.process_text(text, year=year, math_type=math_type,
                                 filename=path.name)

    def process_text(self, text: str, year: int = None,
                     math_type: str = "数学一",
                     filename: str = "") -> PipelineResult:
        """处理原始文本（主流程）"""
        stages = []
        errors = []
        warnings = []
        t_start = time.time()

        # ---- Stage 1: LaTeX修复 ----
        t0 = time.time()
        latex_report = self.latex_fixer.fix(text, ocr_mode=True)
        cleaned_text = latex_report.fixed
        stages.append(StageResult(
            stage="latex_fix", success=True,
            input_size=len(text), output_size=len(cleaned_text),
            duration_ms=(time.time() - t0) * 1000,
            details={"fixes": latex_report.fixes_applied,
                     "unresolved": latex_report.unresolved},
        ))
        if latex_report.unresolved:
            warnings.extend(latex_report.unresolved)

        # ---- Stage 2: 格式检测 ----
        t0 = time.time()
        format_info = self.format_detector.detect(cleaned_text, filename)
        stages.append(StageResult(
            stage="format_detect", success=True,
            input_size=len(cleaned_text), output_size=0,
            duration_ms=(time.time() - t0) * 1000,
            details={"format": format_info.format.name,
                     "year": format_info.year,
                     "math_type": format_info.math_type,
                     "confidence": format_info.confidence},
        ))

        actual_year = year or format_info.year or 0
        actual_type = math_type if math_type != "数学一" else format_info.math_type

        # ---- Stage 3: OCR清理（如需要） ----
        if format_info.format == PaperFormat.OCR_DEGRADED:
            t0 = time.time()
            ocr_report = self.ocr_cleaner.clean(cleaned_text, use_llm=(self.llm_client is not None))
            cleaned_text = ocr_report.cleaned
            stages.append(StageResult(
                stage="ocr_clean", success=True,
                input_size=len(text), output_size=len(cleaned_text),
                duration_ms=(time.time() - t0) * 1000,
                details={
                    "quality_before": ocr_report.quality_before,
                    "quality_after": ocr_report.quality_after,
                    "needs_manual_review": ocr_report.needs_manual_review,
                },
            ))
            if ocr_report.needs_manual_review:
                warnings.append("OCR文本质量仍然较低，建议人工审核")
            # 重新检测格式
            format_info = self.format_detector.detect(cleaned_text, filename)
        else:
            stages.append(StageResult(
                stage="ocr_clean", success=True, input_size=0, output_size=0,
                duration_ms=0, details={"skipped": "not OCR degraded"},
            ))

        # ---- Stage 4: 题目分割 (Shadow Mode: legacy + state machine) ----
        t0 = time.time()
        legacy_result = self.legacy_splitter.split(cleaned_text, format_info)
        state_result = self.state_splitter.split(cleaned_text, format_info)

        # Shadow mode: prefer state machine if it produces more questions within expected range
        legacy_q = len(legacy_result.questions)
        state_q = len(state_result.questions)
        expected_min = 10
        expected_max = 30

        if state_q >= expected_min and state_q <= expected_max:
            split_result = state_result
            splitter_used = "state_machine"
        else:
            split_result = legacy_result
            splitter_used = "legacy"

        # If legacy produces more valid questions, prefer it
        if legacy_q >= expected_min and legacy_q > state_q:
            split_result = legacy_result
            splitter_used = "legacy"

        stages.append(StageResult(
            stage="split", success=True,
            input_size=len(cleaned_text),
            output_size=len(split_result.questions),
            duration_ms=(time.time() - t0) * 1000,
            details={
                "sections": len(split_result.sections),
                "questions": len(split_result.questions),
                "splitter": splitter_used,
                "legacy_questions": legacy_q,
                "state_questions": state_q,
            },
        ))
        if split_result.warnings:
            warnings.extend(split_result.warnings)

        if not split_result.questions:
            return PipelineResult(
                year=actual_year, math_type=actual_type,
                format=format_info.format.name,
                total_questions=0, questions=[],
                errors=["未能从文本中分割出任何题目"],
                warnings=warnings,
            )

        # ---- Stage 5: 答案提取 ----
        t0 = time.time()
        raw_questions = []
        for block in split_result.questions:
            extracted = self.answer_extractor.extract_from_block(block)
            q = self._block_to_dict(block, extracted, actual_year, actual_type)
            raw_questions.append(q)
        stages.append(StageResult(
            stage="answer_extract", success=True,
            input_size=len(split_result.questions),
            output_size=len(raw_questions),
            duration_ms=(time.time() - t0) * 1000,
            details={"with_answer": sum(1 for q in raw_questions if q.get("standard_answer")),
                     "with_solution": sum(1 for q in raw_questions if q.get("solution_steps"))},
        ))

        # ---- Stage 6: 解答匹配 ----
        t0 = time.time()
        if actual_year and self.solution_matcher.solutions_base:
            matches = self.solution_matcher.match_year(
                split_result.questions, actual_year, actual_type
            )
            matched_count = 0
            for q, match in zip(raw_questions, matches):
                if match.matched:
                    # 优先用solution文件的内容，但如果题目已有内联答案则保留
                    if not q.get("standard_answer") and match.answer:
                        q["standard_answer"] = match.answer
                    if match.solution_text:
                        if not q.get("solution_steps"):
                            q["solution_steps"] = match.solution_steps
                        # 将解答文本附加到答案后
                        if q.get("standard_answer") and len(q["standard_answer"]) < 30:
                            q["standard_answer"] += f"\n\n{match.solution_text[:500]}"
                    matched_count += 1
            stages.append(StageResult(
                stage="solution_match", success=True,
                input_size=len(raw_questions),
                output_size=sum(1 for m in matches if m.matched),
                duration_ms=(time.time() - t0) * 1000,
                details={"matched": matched_count,
                         "total": len(raw_questions)},
            ))
        else:
            stages.append(StageResult(
                stage="solution_match", success=True, input_size=0, output_size=0,
                duration_ms=0, details={"skipped": "no year or solution base"},
            ))

        # ---- Stage 7: 验证 ----
        t0 = time.time()
        if self.db:
            valid_count = 0
            issue_count = 0
            for q in raw_questions:
                qc = self.db.validate(q)
                if qc["valid"]:
                    valid_count += 1
                if qc.get("issues"):
                    issue_count += len(qc["issues"])
            stages.append(StageResult(
                stage="validate", success=True,
                input_size=len(raw_questions), output_size=valid_count,
                duration_ms=(time.time() - t0) * 1000,
                details={"valid": valid_count, "issues": issue_count},
            ))
        else:
            stages.append(StageResult(
                stage="validate", success=True, input_size=0, output_size=0,
                duration_ms=0, details={"skipped": "no DB instance"},
            ))

        # ---- 组装结果 ----
        stats = {
            "total_duration_ms": (time.time() - t_start) * 1000,
            "stages": [
                {"stage": s.stage, "success": s.success,
                 "duration_ms": round(s.duration_ms, 1),
                 **s.details}
                for s in stages
            ],
            "answers_found": sum(1 for q in raw_questions if q.get("standard_answer")),
            "solutions_found": sum(1 for q in raw_questions if q.get("solution_steps")),
            "knowledge_points_found": sum(1 for q in raw_questions if q.get("knowledge_points")),
        }

        return PipelineResult(
            year=actual_year, math_type=actual_type,
            format=format_info.format.name,
            total_questions=len(raw_questions),
            questions=raw_questions,
            stats=stats, errors=errors, warnings=warnings,
        )

    def process_directory(self, dir_path: str) -> list[PipelineResult]:
        """批量处理目录下所有MD文件"""
        path = Path(dir_path)
        results = []
        md_files = sorted(path.rglob("*.md"))

        for md_file in md_files:
            if "README" in md_file.name:
                continue
            print(f"处理: {md_file.name}")
            result = self.process_file(str(md_file))
            results.append(result)
            print(f"  解析出 {result.total_questions} 题, "
                  f"有答案 {result.stats.get('answers_found', 0)} 题")

        return results

    def _block_to_dict(self, block: QuestionBlock,
                       extracted, year: int,
                       math_type: str) -> dict:
        """将QuestionBlock转为数据库dict格式"""
        # 清理题目文本（移除答案标注）
        q_text = self._clean_question_text(block.raw_text)

        # 知识标签
        from database.md_parser import MarkdownExamParser
        kp = MarkdownExamParser._detect_knowledge_points(
            MarkdownExamParser(), q_text
        )

        # 难度推断
        from database.md_parser import MarkdownExamParser
        difficulty = MarkdownExamParser._infer_difficulty(
            MarkdownExamParser(), q_text, block.question_type, ""
        )

        # 分值默认
        score = {"选择题": 5, "填空题": 5, "解答题": 10, "证明题": 12}.get(
            block.question_type, 10
        )

        return {
            "year": year,
            "category": math_type,
            "question_type": block.question_type,
            "knowledge_points": kp,
            "difficulty": difficulty,
            "score": score,
            "question": q_text.strip()[:3000],
            "standard_answer": extracted.short_answer,
            "solution_steps": extracted.solution_steps,
            "common_mistakes": [],
            "tags": kp,
            "source": "exam_parser_pipeline",
            "options": extracted.options,
            "correct_option": extracted.correct_option,
        }

    def _clean_question_text(self, raw_text: str) -> str:
        """清理题目文本：移除答案/解析标注，保留题目和选项"""
        # 在【答案】或【解】或【解析】处截断
        for marker in ["【答案】", "【解】", "【解析】", "【分析】"]:
            idx = raw_text.find(marker)
            if idx > 0:
                raw_text = raw_text[:idx]
        return raw_text.strip()


# ==================== CLI ====================

def create_parser():
    import argparse
    parser = argparse.ArgumentParser(
        description="考研数学真题解析与LaTeX结构化引擎",
    )
    sub = parser.add_subparsers(dest="command")

    # process
    p = sub.add_parser("process", help="处理单份试卷")
    p.add_argument("file", help="试卷文件路径")
    p.add_argument("--math-type", default="数学一", help="数学类别")
    p.add_argument("--year", type=int, help="年份")
    p.add_argument("--output", "-o", help="输出JSON路径")
    p.add_argument("--import-to-db", action="store_true", help="直接导入数据库")

    # batch
    b = sub.add_parser("batch", help="批量处理目录")
    b.add_argument("dir", help="目录路径")
    b.add_argument("--import-to-db", action="store_true", help="直接导入数据库")

    # fix-latex
    fl = sub.add_parser("fix-latex", help="仅修复LaTeX")
    fl.add_argument("file", help="文件路径")
    fl.add_argument("--output", "-o", help="输出路径")

    # stats
    s = sub.add_parser("stats", help="统计试卷信息")
    s.add_argument("dir", help="目录路径")

    return parser


def cmd_process(args):
    pipeline = ExamParserPipeline()
    if args.import_to_db:
        from database import QuestionDB, QuestionImporter
        db = QuestionDB()
        pipeline.db = db

    result = pipeline.process_file(
        args.file, math_type=args.math_type, year=args.year
    )

    print(f"年份: {result.year} | 数学类别: {result.math_type}")
    print(f"格式: {result.format} | 题目数: {result.total_questions}")
    print(f"答案数: {result.stats.get('answers_found', 0)}")
    print(f"解答数: {result.stats.get('solutions_found', 0)}")
    if result.errors:
        print(f"错误: {result.errors}")
    if result.warnings:
        print(f"警告: {result.warnings[:5]}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result.questions, f, ensure_ascii=False, indent=2)
        print(f"已输出到: {args.output}")

    if args.import_to_db and pipeline.db and result.questions:
        from database import QuestionImporter
        importer = QuestionImporter(pipeline.db)
        report = importer.import_dict(result.questions)
        print(f"导入: 成功{report['success']}, 跳过{report['skipped_duplicates']}, "
              f"失败{report['failed']}")


def cmd_batch(args):
    pipeline = ExamParserPipeline()
    if args.import_to_db:
        from database import QuestionDB, QuestionImporter
        db = QuestionDB()
        pipeline.db = db

    results = pipeline.process_directory(args.dir)

    total_q = sum(r.total_questions for r in results)
    total_ans = sum(r.stats.get("answers_found", 0) for r in results)
    print(f"\n总计: {len(results)} 份试卷, {total_q} 题, {total_ans} 有答案")

    if args.import_to_db and pipeline.db:
        all_qs = []
        for r in results:
            all_qs.extend(r.questions)
        from database import QuestionImporter
        importer = QuestionImporter(pipeline.db)
        report = importer.import_dict(all_qs)
        print(f"累计导入: 成功{report['success']}, 跳过{report['skipped_duplicates']}, "
              f"失败{report['failed']}")


def cmd_fix_latex(args):
    fixer = LaTeXFixer()
    text = Path(args.file).read_text(encoding="utf-8")
    report = fixer.fix(text, ocr_mode=True)

    output = report.fixed
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"已输出到: {args.output}")
    else:
        print(output[:2000])

    print(f"\n修复数: {report.fix_count}")
    for fix in report.fixes_applied:
        print(f"  - {fix}")
    if report.unresolved:
        print(f"未解决: {report.unresolved}")


def cmd_stats(args):
    path = Path(args.dir)
    md_files = sorted(path.rglob("*.md"))
    detector = FormatDetector()

    for f in md_files:
        if f.name in ("README.md", "LICENSE.md"):
            continue
        text = f.read_text(encoding="utf-8")
        info = detector.detect(text, f.name)
        print(f"{f.name:40s} | {info.format.name:25s} | "
              f"year={info.year} | {info.math_type} | "
              f"conf={info.confidence:.0%}")


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "process":
        cmd_process(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "fix-latex":
        cmd_fix_latex(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
