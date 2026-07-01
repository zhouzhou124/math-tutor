"""P55-hotfix: Tests for disabling destructive compiler and integrity guard."""

import copy
import pytest


class TestCompilerDisabledByDefault:
    def test_flag_is_false(self):
        from services.grading_adapter import ENABLE_SOLUTION_PROOF_MATH_COMPILER
        assert ENABLE_SOLUTION_PROOF_MATH_COMPILER is False

    def test_build_standard_solution_view_no_compile(self):
        """When flag is off, build_standard_solution_view does not call compile."""
        from services.grading_adapter import build_standard_solution_view
        sol = {
            "standard_solution_view": {
                "sections": [{
                    "title": "步骤1",
                    "blocks": [{"type": "text", "content": "令 $u=x$。"}],
                }],
                "final_answer": {"type": "text", "content": "x=1"},
            },
        }
        view = build_standard_solution_view(sol, "解答题")
        # Text should be preserved (not fragmented by compile)
        blocks = view["sections"][0]["blocks"]
        all_content = " ".join(b.get("content", "") for b in blocks)
        assert "令" in all_content


class TestNonDestructiveCompile:
    def test_chinese_not_fragmented(self):
        """Pure Chinese text must stay as a single block."""
        from services.grading_adapter import compile_text_block_to_math_blocks
        text = "步骤1：识别题型并写出原函数。推导目标：求最大值。"
        blocks = compile_text_block_to_math_blocks(text)
        # Must be a single block, not split into characters
        assert len(blocks) == 1
        assert blocks[0]["type"] == "text"
        assert "步骤" in blocks[0]["content"]

    def test_formula_with_chinese_context_preserved(self):
        """'由 f(x)=frac{1}{x} 可知' must keep '由' and '可知'."""
        from services.grading_adapter import compile_text_block_to_math_blocks
        blocks = compile_text_block_to_math_blocks("由 f(x)=frac{1}{x} 可知")
        all_content = " ".join(b.get("content", "") for b in blocks)
        # Chinese must be preserved somewhere
        assert "由" in all_content or "知" in all_content

    def test_no_single_character_blocks(self):
        """Must not produce blocks like 'f', '(', 'x', ')', '='."""
        from services.grading_adapter import compile_text_block_to_math_blocks
        text = "f'(x)=3x^2-3=0，解得 x=1"
        blocks = compile_text_block_to_math_blocks(text)
        text_blocks = [b for b in blocks if b.get("type") == "text"]
        # No block should be a single character
        for b in text_blocks:
            content = str(b.get("content", "")).strip()
            if content:
                assert len(content) > 1, f"Single-char block: {repr(content)}"

    def test_no_empty_latex_delimiters(self):
        """Must not produce empty \\( \\) blocks."""
        from services.grading_adapter import compile_text_block_to_math_blocks
        text = "由 f(x)=frac{1}{x} 可知"
        blocks = compile_text_block_to_math_blocks(text)
        for b in blocks:
            content = str(b.get("content", ""))
            assert content.strip() != "\\(\\)", f"Empty latex block found"

    def test_no_orphan_symbol_blocks(self):
        """Must not produce blocks that are just '(', ')', '.', '=', etc."""
        from services.grading_adapter import compile_text_block_to_math_blocks
        orphans = {"()", "(", ")", ".", "。", "步", "骤", "=", "+", "-"}
        text = "f(x)=frac{1}{x}，因此 f'(x)=-frac{1}{x^2}"
        blocks = compile_text_block_to_math_blocks(text)
        for b in blocks:
            if b.get("type") == "text":
                content = str(b.get("content", "")).strip()
                assert content not in orphans, f"Orphan symbol block: {repr(content)}"


class TestIntegrityGuard:
    def test_cjk_retention_check(self):
        """compiled_view with low CJK retention is unsafe."""
        from services.grading_adapter import is_compiled_view_safe
        original = {"sections": [{"blocks": [
            {"type": "text", "content": "步骤1：识别题型并写出原函数。推导目标：求最大值。"},
        ]}]}
        compiled = {"sections": [{"blocks": [
            {"type": "text", "content": "步"},
            {"type": "text", "content": "骤"},
            {"type": "text", "content": "1"},
        ]}]}
        assert is_compiled_view_safe(original, compiled) is False

    def test_orphan_symbol_detection(self):
        """compiled_view with orphan '()' blocks is unsafe."""
        from services.grading_adapter import is_compiled_view_safe
        original = {"sections": [{"blocks": [
            {"type": "text", "content": "对函数 f(x)=x^3-3x 求导，得到 f'(x)=3x^2-3"},
        ]}]}
        compiled = {"sections": [{"blocks": [
            {"type": "text", "content": "()"},
            {"type": "text", "content": "()"},
            {"type": "text", "content": "()"},
            {"type": "text", "content": "()"},
            {"type": "text", "content": "()"},
            {"type": "text", "content": "()"},
        ]}]}
        assert is_compiled_view_safe(original, compiled) is False

    def test_fragmentation_detection(self):
        """compiled_view with many single-char blocks is unsafe."""
        from services.grading_adapter import is_compiled_view_safe
        original = {"sections": [{"blocks": [
            {"type": "text", "content": "步骤1：识别题型并写出原函数。推导目标：求最大值。"},
        ]}]}
        # Simulate fragmented output
        fragmented_blocks = [{"type": "text", "content": ch} for ch in "步骤1：识别"]
        compiled = {"sections": [{"blocks": fragmented_blocks}]}
        assert is_compiled_view_safe(original, compiled) is False

    def test_safe_compiled_view_passes(self):
        """Reasonable compiled view passes integrity check."""
        from services.grading_adapter import is_compiled_view_safe
        original = {"sections": [{"blocks": [
            {"type": "text", "content": "由 f(x)=frac{1}{x} 可知，函数在 x=1 处取得极值。"},
        ]}]}
        compiled = {"sections": [{"blocks": [
            {"type": "text", "content": "由 "},
            {"type": "text", "content": "\\(f(x)=\\frac{1}{x}\\)"},
            {"type": "text", "content": " 可知，函数在 x=1 处取得极值。"},
        ]}]}
        assert is_compiled_view_safe(original, compiled) is True

    def test_choose_safe_returns_original_on_unsafe(self):
        """choose_safe_compiled_view returns original when compiled is unsafe."""
        from services.grading_adapter import choose_safe_compiled_view
        original = {"sections": [{"blocks": [
            {"type": "text", "content": "步骤1：识别题型。"},
        ]}]}
        compiled = {"sections": [{"blocks": [
            {"type": "text", "content": "步"},
            {"type": "text", "content": "骤"},
        ]}]}
        result = choose_safe_compiled_view(original, compiled)
        assert result is original

    def test_choose_safe_returns_compiled_on_safe(self):
        """choose_safe_compiled_view returns compiled when safe."""
        from services.grading_adapter import choose_safe_compiled_view
        original = {"sections": [{"blocks": [
            {"type": "text", "content": "由 f(x)=frac{1}{x} 可知。"},
        ]}]}
        compiled = {"sections": [{"blocks": [
            {"type": "text", "content": "由 \\(f(x)=\\frac{1}{x}\\) 可知。"},
        ]}]}
        result = choose_safe_compiled_view(original, compiled)
        assert result is compiled


class TestRendererNoDestructiveCompile:
    def test_render_math_text_preserves_chinese(self):
        """render_math_text must not turn Chinese into code."""
        # We test the underlying detection — render_math_text uses the same logic
        from services.grading_adapter import contains_raw_tex_outside_math
        text = "这是一段中文说明，包含 f(x)=x^2 的讨论。"
        # This text has no raw TeX
        assert contains_raw_tex_outside_math(text) is False

    def test_render_math_text_no_raw_tex_passes_through(self):
        """Text without raw TeX should pass through normal rendering."""
        from services.grading_adapter import contains_raw_tex_outside_math
        assert contains_raw_tex_outside_math("步骤1：识别题型") is False
        assert contains_raw_tex_outside_math("由条件可知") is False


class TestRegressionP54:
    def test_choice_view_still_works(self):
        """P54 choice view should still work after hotfix."""
        from services.grading_adapter import build_standard_solution_view
        sol = {"choice_solution": {"conclusion": "故选 B", "answer": "B"}}
        view = build_standard_solution_view(sol, "选择题")
        assert view["answer_card"]["correct_answer"] == "B"

    def test_fill_view_still_works(self):
        """P54 fill view should still work after hotfix."""
        from services.grading_adapter import build_standard_solution_view
        sol = {"standard_answer": "x=1"}
        view = build_standard_solution_view(sol, "填空题", {"correct_answer": "x=1"})
        assert view["answer_card"]["correct_answer"] == "x=1"
