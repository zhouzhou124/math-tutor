"""
OCR Repair — 确定性真题文本修复引擎

设计原则:
  - 所有 pass 纯函数: after, trace = pass_fn(before, policy)
  - 默认禁用 LLM
  - 完全可复现（相同输入 → 相同输出）
  - 所有修改可追踪（RepairTrace）

管道:
  Safe Normalize → Layout Recovery → Rule Engine → Validator

用法:
  from ocr_repair import OCRRepair, RepairPolicy
  engine = OCRRepair()
  report = engine.repair(raw_ocr_text)
  # report.repaired → 修复后文本
  # report.needs_manual_review → 是否需要人工复核
  # report.traces → 每个pass的修复追踪
"""

from .core import (
    RepairPolicy,
    WarningCode,
    ValidationResult,
    RepairTrace,
    FidelityScore,
    RepairReport,
)
from .safe_normalize import apply as safe_normalize
from .layout_recovery import apply as layout_recovery
from .rule_engine import apply as rule_engine
from .validator import (
    validate,
    compute_fidelity,
    classify_warnings,
)


class OCRRepair:
    """OCR 修复引擎（确定性优先，可选 LLM）"""

    def __init__(self, policy: RepairPolicy | None = None, llm_client=None):
        self.policy = policy or RepairPolicy()
        self.llm_client = llm_client

    def repair(self, text: str) -> RepairReport:
        """
        执行完整确定性修复管道。

        返回 RepairReport，包含:
          - repaired: 修复后文本
          - pre_validation: 修复前验证结果
          - post_validation: 修复后验证结果
          - fidelity: 保真度评分
          - traces: 每个pass的追踪记录
          - resolved_warnings / introduced_warnings
          - needs_manual_review
        """
        report = RepairReport(original=text)
        pre_warnings: list[WarningCode] = []

        # ── Pre-validation ──
        pre_val, pre_trace = validate(text, policy=self.policy)
        report.pre_validation = pre_val
        pre_warnings = pre_val.warnings
        report.traces.append(pre_trace)

        # ── Pass 0: Safe Normalize ──
        after, trace = safe_normalize(text, self.policy)
        report.traces.append(trace)
        report.passes_executed.append("safe_normalize")
        text = after

        # ── Pass 1: Layout Recovery ──
        after, trace = layout_recovery(text, self.policy)
        report.traces.append(trace)
        report.passes_executed.append("layout_recovery")
        text = after

        # ── Pass 2: Rule Engine ──
        after, trace = rule_engine(text, self.policy)
        report.traces.append(trace)
        report.passes_executed.append("rule_engine")
        text = after

        # ── Post-validation (after deterministic passes) ──
        post_val, post_trace = validate(text, pre_warnings, self.policy)
        report.post_validation = post_val
        report.traces.append(post_trace)

        # ── Optional LLM Repair (gated: quality < threshold + LLM enabled + client available) ──
        if (self.policy.enable_llm and self.llm_client is not None and
            post_val.quality_score < self.policy.llm_trigger_quality and
            not self.policy.strict_fidelity):
            after, llm_trace = self._llm_pass(text)
            if after != text:
                report.traces.append(llm_trace)
                report.passes_executed.append("llm_repair")
                text = after
                # Re-validate after LLM
                post_val, post_trace = validate(text, pre_warnings, self.policy)
                report.post_validation = post_val
                report.traces.append(post_trace)

        # ── Fidelity ──
        report.fidelity = compute_fidelity(report.original, text)

        # ── Warning classification ──
        resolved, introduced = classify_warnings(pre_warnings, post_val.warnings)
        report.resolved_warnings = resolved
        report.introduced_warnings = introduced

        # ── Manual review decision ──
        report.needs_manual_review = (
            post_val.needs_manual_review or
            (report.fidelity and report.fidelity.status == "manual_review") or
            len(introduced) > 2
        )

        if not report.needs_manual_review and report.fidelity:
            if report.fidelity.status == "warning":
                report.needs_manual_review = True
                report.failure_mode = "fidelity_warning"

        if report.needs_manual_review and not report.failure_mode:
            if post_val.failure_mode:
                report.failure_mode = post_val.failure_mode
            elif report.fidelity and report.fidelity.status == "manual_review":
                report.failure_mode = "fidelity_failure: 信息量变化过大"
            else:
                report.failure_mode = "validation_failed"

        report.repaired = text
        return report

    def _llm_pass(self, text: str) -> tuple[str, 'RepairTrace']:
        """LLM辅助修复（仅当质量过低时触发）"""
        from .core import RepairTrace, WarningCode
        trace = RepairTrace(
            pass_name="llm_repair",
            input_snippet=text[:200],
            char_count_before=len(text),
        )
        try:
            # 复用 exam_parser 的 OCR cleaner LLM 路径
            from exam_parser.ocr_cleaner import OCRCleaner
            cleaner = OCRCleaner(self.llm_client)
            report = cleaner.clean(text, use_llm=True)
            trace.output_snippet = report.cleaned[:200]
            trace.char_count_after = len(report.cleaned)
            trace.modifications.append(f"LLM修复: quality {report.quality_before:.2f}→{report.quality_after:.2f}")
            return report.cleaned, trace
        except Exception as e:
            trace.warnings.append(WarningCode.ocr_unrecoverable)
            trace.modifications.append(f"LLM修复失败: {e}")
            return text, trace
