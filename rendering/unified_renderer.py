from typing import Optional, Union
from rendering.document_parser import DocumentParser
from rendering.document_to_ir import DocumentToIRConverter
from rendering.reasoning_trace_to_ir import ReasoningTraceToIRConverter
from rendering.proof_replay_renderer import ProofReplayRenderer
from rendering.streamlit_renderer import StreamlitRenderer
from rendering.render_ir import RenderTree, RenderNode, RenderType
from rendering.latex_validator import LaTeXValidator


class UnifiedRenderer:
    """
    统一渲染入口 — 数学语义驱动的渲染管道 (Phase 3)。

    支持三种输入模式：

    1. 文本模式 (Text Mode):
      Raw Content
        → LaTeXFixer          # OCR/输入修复
        → LaTeXValidator      # 结构合法性验证 + 自动修复
        → clean_markdown       # Markdown 污染清理
        → wrap_bare_math       # 裸数学表达式包裹
        → DocumentParser       # 文本 → Document AST (语义分类)
        → DocumentToIRConverter # Document AST → Render IR (语义保留)
        → StreamlitRenderer    # Render IR → Streamlit UI (直接渲染)

    2. 图模式 (Graph Mode):
      ReasoningTrace (Semantic Graph)
        → StructuredLatexRenderer  # 结构化 LaTeX 渲染（不再字符串拼接）
        → StreamlitRenderer        # Render IR → Streamlit UI

    3. Proof/Trace 模式:
      RewriteTrace / EqualityProof / RewriteResult
        → StructuredLatexRenderer  # 结构化构建（AlignedBlock + 验证）
        → StreamlitRenderer        # Render IR → Streamlit UI

    关键特点:
      - LaTeXValidator 在渲染前验证所有 LaTeX
      - StructuredLatexRenderer 禁止字符串拼接
      - Render IR 保留所有语义
      - StreamlitRenderer 直接调用 st.*，不经过 Markdown 字符串
    """

    def __init__(self):
        self._parser = DocumentParser()
        self._doc_converter = DocumentToIRConverter()
        self._trace_converter = ReasoningTraceToIRConverter()
        self._renderer = StreamlitRenderer()
        self._proof_replay = ProofReplayRenderer()
        self._validator = LaTeXValidator()
        self._latex_renderer = None

    @property
    def latex_renderer(self):
        if self._latex_renderer is None:
            from rendering.structured_latex_renderer import LatexRenderer
            self._latex_renderer = LatexRenderer()
        return self._latex_renderer

    def render(self, content: Union[str, object], role: str = "", view_mode: str = "linear") -> Union[str, RenderTree]:
        if self._is_rewrite_trace(content):
            return self._render_rewrite_trace(content)
        elif self._is_equality_proof(content):
            return self._render_equality_proof(content)
        elif self._is_rewrite_result(content):
            return self._render_rewrite_result(content)
        elif self._is_reasoning_trace(content):
            return self._render_trace(content, view_mode=view_mode)
        else:
            return self._render_text(content, role=role)

    def _is_reasoning_trace(self, content) -> bool:
        if content is None:
            return False
        return (
            hasattr(content, 'steps') and
            hasattr(content, 'edges') and
            hasattr(content, 'topological_order')
        )

    def _is_rewrite_trace(self, content) -> bool:
        if content is None:
            return False
        type_name = type(content).__name__
        return type_name == 'RewriteTrace'

    def _is_equality_proof(self, content) -> bool:
        if content is None:
            return False
        type_name = type(content).__name__
        return type_name == 'EqualityProof'

    def _is_rewrite_result(self, content) -> bool:
        if content is None:
            return False
        type_name = type(content).__name__
        return type_name == 'RewriteResult'

    def _render_text(self, text: str, role: str = "") -> str:
        if not text:
            return ""

        if not isinstance(text, str):
            text = str(text)

        fixed = self._fix_latex(text)
        validated = self._validate_and_fix(fixed)
        cleaned = self._clean_markdown(validated)
        cleaned = self._wrap_bare_math(cleaned)

        doc = self._parser.parse(cleaned, default_role=role)
        tree = RenderTree.from_document(doc)
        return tree

    def _render_trace(self, trace, view_mode: str = "linear") -> RenderTree:
        tree = self._trace_converter.convert(trace, view_mode=view_mode)
        return tree

    def _render_rewrite_trace(self, trace) -> RenderTree:
        nodes = self.latex_renderer.render_proof_trace(trace)
        if not nodes:
            return RenderTree(root=RenderNode(type=RenderType.TEXT, content=""))
        if len(nodes) == 1:
            return RenderTree(root=nodes[0])
        return RenderTree(root=RenderNode(type=RenderType.CONTAINER, children=tuple(nodes)))

    def _render_equality_proof(self, proof) -> RenderTree:
        nodes = self.latex_renderer.render_equality_proof(proof)
        if not nodes:
            return RenderTree(root=RenderNode(type=RenderType.TEXT, content=""))
        if len(nodes) == 1:
            return RenderTree(root=nodes[0])
        return RenderTree(root=RenderNode(type=RenderType.CONTAINER, children=tuple(nodes)))

    def _render_rewrite_result(self, result) -> RenderTree:
        nodes = self.latex_renderer.render_rewrite_result(result)
        if not nodes:
            return RenderTree(root=RenderNode(type=RenderType.TEXT, content=""))
        if len(nodes) == 1:
            return RenderTree(root=nodes[0])
        return RenderTree(root=RenderNode(type=RenderType.CONTAINER, children=tuple(nodes)))

    def render_to_streamlit(self, content: Union[str, object], role: str = "", view_mode: str = "linear") -> None:
        if not content:
            return

        if self._is_rewrite_trace(content):
            self._render_rewrite_trace_to_streamlit(content)
        elif self._is_equality_proof(content):
            self._render_equality_proof_to_streamlit(content)
        elif self._is_rewrite_result(content):
            self._render_rewrite_result_to_streamlit(content)
        elif self._is_reasoning_trace(content):
            self._render_trace_to_streamlit(content, view_mode=view_mode)
        else:
            self._render_text_to_streamlit(content, role=role)

    def _render_text_to_streamlit(self, text: str, role: str = "") -> None:
        if not text:
            return

        try:
            fixed = self._fix_latex(text)
            validated = self._validate_and_fix(fixed)
            cleaned = self._clean_markdown(validated)
            wrapped = self._wrap_bare_math(cleaned)
            doc = self._parser.parse(wrapped, default_role=role)
            tree = RenderTree.from_document(doc)
            self._renderer.render(tree)
        except Exception:
            import streamlit as st
            import re as _re
            fallback = text
            if not _re.search(r'\$', text) and _re.search(r'\\[a-zA-Z]', text):
                fallback = f"$$\n{text}\n$$"
            fallback = self._validate_and_fix(fallback)
            st.markdown(fallback, unsafe_allow_html=True)

    def _render_trace_to_streamlit(self, trace, view_mode: str = "linear") -> None:
        self._proof_replay.render(trace, expanded=False)

    def _render_rewrite_trace_to_streamlit(self, trace) -> None:
        tree = self._render_rewrite_trace(trace)
        self._renderer.render(tree)

    def _render_equality_proof_to_streamlit(self, proof) -> None:
        tree = self._render_equality_proof(proof)
        self._renderer.render(tree)

    def _render_rewrite_result_to_streamlit(self, result) -> None:
        tree = self._render_rewrite_result(result)
        self._renderer.render(tree)

    def _validate_and_fix(self, text: str) -> str:
        if not text or not text.strip():
            return text

        has_latex_commands = False
        import re
        if re.search(r'\\[a-zA-Z]', text):
            has_latex_commands = True
        if '$' in text or '\\begin{' in text or '\\left' in text:
            has_latex_commands = True

        if not has_latex_commands:
            return text

        result = self._validator.validate_and_fix(text)
        return result.fixed_latex

    def _fix_latex(self, text: str) -> str:
        try:
            from exam_parser.latex_fixer import LaTeXFixer
            fixer = LaTeXFixer()
            report = fixer.fix(text)
            return report.fixed
        except Exception:
            return text

    def _clean_markdown(self, text: str) -> str:
        import re

        protected = {}
        cmd_count = 0
        temp_text = text

        cmd_pattern = re.compile(r'\\[a-zA-Z]+')
        matches = list(cmd_pattern.finditer(temp_text))

        for match in reversed(matches):
            full_cmd = match.group(0)
            placeholder = f'\x00CMD{cmd_count}\x00'
            temp_text = temp_text[:match.start()] + placeholder + temp_text[match.end():]
            protected[placeholder] = full_cmd
            cmd_count += 1

        temp_text = re.sub(r'\*\*(.+?)\*\*', r'\1', temp_text)
        temp_text = re.sub(r'__(.+?)__', r'\1', temp_text)
        temp_text = re.sub(r'\*(.+?)\*', r'\1', temp_text)
        temp_text = re.sub(r'_(.+?)_', r'\1', temp_text)

        code_pattern = re.compile(r'`([^`]+)`')
        temp_text = code_pattern.sub(r'\1', temp_text)

        temp_text = re.sub(r'[ \t]+', ' ', temp_text)

        for placeholder, original in protected.items():
            temp_text = temp_text.replace(placeholder, original)

        return temp_text

    def _wrap_bare_math(self, text: str) -> str:
        import re

        if not text:
            return text

        in_math_region = [False] * len(text)

        double_dollar_pattern = r'\$\$.*?\$\$'
        for m in re.finditer(double_dollar_pattern, text, re.DOTALL):
            for i in range(m.start(), min(m.end(), len(in_math_region))):
                in_math_region[i] = True

        single_dollar_pattern = r'(?<!\$)\$[^$\n]+?\$(?!\$)'
        for m in re.finditer(single_dollar_pattern, text):
            is_in_double = False
            for i in range(m.start(), min(m.end(), len(in_math_region))):
                if in_math_region[i]:
                    is_in_double = True
                    break
            if not is_in_double:
                for i in range(m.start(), min(m.end(), len(in_math_region))):
                    in_math_region[i] = True

        bare_matches = []
        n = len(text)
        i = 0

        while i < n:
            if i < n and in_math_region[i]:
                while i < n and in_math_region[i]:
                    i += 1
                continue

            if i < n and text[i] == '\\' and i + 1 < n and text[i + 1].isalpha():
                cmd_end = i + 1
                while cmd_end < n and text[cmd_end].isalpha():
                    cmd_end += 1

                cmd = text[i:cmd_end]

                if cmd in {'\\quad', '\\qquad', '\\hspace', '\\vspace', '\\hfill', '\\vfill'}:
                    i = cmd_end
                    continue

                start = i
                brace_stack = []
                j = cmd_end
                in_expression = True

                while j < n and in_expression:
                    if in_math_region[j]:
                        break

                    c = text[j]

                    if c == '{':
                        brace_stack.append('{')
                    elif c == '}':
                        if brace_stack:
                            brace_stack.pop()
                    elif c == '\\':
                        pass

                    if not brace_stack:
                        next_pos = j + 1
                        while next_pos < n and text[next_pos] in ' \t':
                            next_pos += 1

                        if next_pos >= n:
                            in_expression = False
                        else:
                            next_char = text[next_pos]
                            if '\u4e00' <= next_char <= '\u9fff' or next_char in '，。！？；：""''（）【】《》、·…\n\r':
                                in_expression = False

                    j += 1

                matched_text = text[start:j].strip()
                if len(matched_text) > 1:
                    bare_matches.append((start, j))

                i = j
            else:
                i += 1

        if bare_matches:
            new_text = text
            for start, end in reversed(bare_matches):
                new_text = new_text[:start] + '$' + new_text[start:end] + '$' + new_text[end:]
            return new_text

        return text


_unified_renderer: Optional[UnifiedRenderer] = None


def get_unified_renderer() -> UnifiedRenderer:
    global _unified_renderer
    if _unified_renderer is None:
        _unified_renderer = UnifiedRenderer()
    return _unified_renderer


def unified_render(text: str, role: str = "") -> str:
    return get_unified_renderer().render(text, role)


def unified_render_st(text: str, role: str = "") -> None:
    get_unified_renderer().render_to_streamlit(text, role)
