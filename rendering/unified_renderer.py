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

        # Replace KaTeX-unsupported commands before the pipeline
        from latex_utils import _preprocess_latex
        text = _preprocess_latex(text)

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
            # 首先将 HTML 实体直接替换为 LaTeX 命令（在 unescape 之前）
            html_to_latex = {
                '&times;': r'\times',
                '&times': r'\times',
                '&RightArrow;': r'\Rightarrow',
                '&RightArrow': r'\Rightarrow',
                '&rightarrow;': r'\rightarrow',
                '&rightarrow': r'\rightarrow',
                '&le;': r'\le',
                '&le': r'\le',
                '&ge;': r'\ge',
                '&ge': r'\ge',
                '&lt;': r'\lt',
                '&lt': r'\lt',
                '&gt;': r'\gt',
                '&gt': r'\gt',
                '&ne;': r'\ne',
                '&ne': r'\ne',
                '&equiv;': r'\equiv',
                '&equiv': r'\equiv',
                '&approx;': r'\approx',
                '&approx': r'\approx',
                '&sum;': r'\sum',
                '&sum': r'\sum',
                '&int;': r'\int',
                '&int': r'\int',
                '&infty;': r'\infty',
                '&infty': r'\infty',
                '&partial;': r'\partial',
                '&partial': r'\partial',
                '&cdot;': r'\cdot',
                '&cdot': r'\cdot',
                '&alpha;': r'\alpha',
                '&alpha': r'\alpha',
                '&beta;': r'\beta',
                '&beta': r'\beta',
                '&gamma;': r'\gamma',
                '&gamma': r'\gamma',
                '&delta;': r'\delta',
                '&delta': r'\delta',
                '&epsilon;': r'\varepsilon',
                '&epsilon': r'\varepsilon',
                '&zeta;': r'\zeta',
                '&zeta': r'\zeta',
                '&eta;': r'\eta',
                '&eta': r'\eta',
                '&theta;': r'\theta',
                '&theta': r'\theta',
                '&iota;': r'\iota',
                '&iota': r'\iota',
                '&kappa;': r'\kappa',
                '&kappa': r'\kappa',
                '&lambda;': r'\lambda',
                '&lambda': r'\lambda',
                '&mu;': r'\mu',
                '&mu': r'\mu',
                '&nu;': r'\nu',
                '&nu': r'\nu',
                '&xi;': r'\xi',
                '&xi': r'\xi',
                '&pi;': r'\pi',
                '&pi': r'\pi',
                '&rho;': r'\rho',
                '&rho': r'\rho',
                '&sigma;': r'\sigma',
                '&sigma': r'\sigma',
                '&tau;': r'\tau',
                '&tau': r'\tau',
                '&upsilon;': r'\upsilon',
                '&upsilon': r'\upsilon',
                '&phi;': r'\phi',
                '&phi': r'\phi',
                '&chi;': r'\chi',
                '&chi': r'\chi',
                '&psi;': r'\psi',
                '&psi': r'\psi',
                '&omega;': r'\omega',
                '&omega': r'\omega',
            }
            
            for html_entity, latex_cmd in html_to_latex.items():
                text = text.replace(html_entity, latex_cmd)
            
            # 然后解码剩余的 HTML 实体
            from html import unescape
            text = unescape(text)
            
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

        n = len(text)
        in_math_region = [False] * n

        double_dollar_pattern = r'\$\$.*?\$\$'
        for m in re.finditer(double_dollar_pattern, text, re.DOTALL):
            for i in range(m.start(), min(m.end(), n)):
                in_math_region[i] = True

        single_dollar_pattern = r'(?<!\$)\$[^$\n]+?\$(?!\$)'
        for m in re.finditer(single_dollar_pattern, text):
            is_in_double = False
            for i in range(m.start(), min(m.end(), n)):
                if in_math_region[i]:
                    is_in_double = True
                    break
            if not is_in_double:
                for i in range(m.start(), min(m.end(), n)):
                    in_math_region[i] = True

        # 定义中文标点符号
        chinese_punctuation = set('，。！？；：""''（）【】《》、·…\n\r')

        def is_chinese_char(c):
            return '\u4e00' <= c <= '\u9fff'

        def find_closing_paren(start_pos, open_char, close_char):
            """查找匹配的闭合括号"""
            count = 1
            pos = start_pos + 1
            while pos < n and count > 0:
                if text[pos] == open_char:
                    count += 1
                elif text[pos] == close_char:
                    count -= 1
                pos += 1
            if count == 0:
                return pos - 1
            return -1

        bare_matches = []
        pos = 0

        while pos < n:
            # 跳过空白和已标记区域
            while pos < n and (text[pos] in ' \t\n\r' or in_math_region[pos]):
                pos += 1
            
            if pos >= n:
                break

            # 模式1: 查找以 \命令 开头的数学表达式
            if text[pos] == '\\' and pos + 1 < n and text[pos + 1].isalpha():
                cmd_pattern = re.compile(r'\\[a-zA-Z]+')
                cmd_match = cmd_pattern.match(text, pos)
                if cmd_match:
                    cmd = cmd_match.group(0)
                    
                    # 跳过纯间距命令
                    skip_commands = {'\\quad', '\\qquad', '\\hspace', '\\vspace', '\\hfill', '\\vfill'}
                    if cmd in skip_commands:
                        pos = cmd_match.end()
                        continue
                    
                    # 找到命令后的花括号内容
                    brace_count = 0
                    paren_count = 0
                    end_pos = cmd_match.end()
                    while end_pos < n:
                        c = text[end_pos]
                        if c == '{':
                            brace_count += 1
                        elif c == '}':
                            brace_count -= 1
                        elif c == '(':
                            paren_count += 1
                        elif c == ')':
                            paren_count -= 1
                        elif c == '\\' and end_pos + 1 < n and text[end_pos + 1].isalpha():
                            pass
                        
                        end_pos += 1
                        
                        # 当所有括号都匹配完毕时检查是否应该结束
                        if brace_count == 0 and paren_count == 0:
                            temp_pos = end_pos
                            while temp_pos < n and text[temp_pos] in ' \t':
                                temp_pos += 1
                            
                            if temp_pos >= n:
                                break
                            
                            next_char = text[temp_pos]
                            if is_chinese_char(next_char) or next_char in chinese_punctuation:
                                break
                    
                    # 检查是否找到有效区域
                    is_valid = True
                    for i in range(pos, min(end_pos, n)):
                        if in_math_region[i]:
                            is_valid = False
                            break
                    
                    if is_valid:
                        content = text[pos:end_pos].strip()
                        if content and len(content) > 1:
                            bare_matches.append((pos, end_pos))
                    
                    pos = end_pos
                    continue
            
            # 模式2: 查找以字母开头后面跟着 ( 的函数调用
            if text[pos].isalpha() and pos + 1 < n and text[pos + 1] == '(':
                # 找到函数名
                func_end = pos + 1
                while func_end < n and text[func_end - 1].isalpha():
                    func_end += 1
                
                # 找到匹配的闭合括号
                close_paren = find_closing_paren(pos + 1, '(', ')')
                if close_paren >= 0:
                    # 这是一个函数调用，继续查找后面的数学内容
                    end_pos = close_paren + 1
                    
                    # 继续查找后面的数学表达式（如 =, +, -, \命令等）
                    while end_pos < n:
                        # 检查是否应该结束
                        temp_pos = end_pos
                        while temp_pos < n and text[temp_pos] in ' \t':
                            temp_pos += 1
                        
                        if temp_pos >= n:
                            break
                        
                        next_char = text[temp_pos]
                        if is_chinese_char(next_char) or next_char in chinese_punctuation:
                            break
                        
                        # 检查是否是数学相关字符
                        if next_char == '\\' and temp_pos + 1 < n and text[temp_pos + 1].isalpha():
                            # 遇到 \命令，继续扩展
                            cmd_pattern = re.compile(r'\\[a-zA-Z]+')
                            cmd_match = cmd_pattern.match(text, temp_pos)
                            if cmd_match:
                                brace_count = 0
                                paren_count = 0
                                cmd_end = cmd_match.end()
                                while cmd_end < n:
                                    c = text[cmd_end]
                                    if c == '{':
                                        brace_count += 1
                                    elif c == '}':
                                        brace_count -= 1
                                    elif c == '(':
                                        paren_count += 1
                                    elif c == ')':
                                        paren_count -= 1
                                    cmd_end += 1
                                    if brace_count == 0 and paren_count == 0:
                                        temp_pos_check = cmd_end
                                        while temp_pos_check < n and text[temp_pos_check] in ' \t':
                                            temp_pos_check += 1
                                        if temp_pos_check >= n or is_chinese_char(text[temp_pos_check]) or text[temp_pos_check] in chinese_punctuation:
                                            break
                                end_pos = cmd_end
                            else:
                                end_pos += 1
                        elif next_char.isalpha() or next_char.isdigit() or next_char in '+-*/=<>^_()[]{}':
                            end_pos += 1
                        else:
                            break
                    
                    # 检查是否与已有数学区域重叠
                    is_valid = True
                    for i in range(pos, min(end_pos, n)):
                        if in_math_region[i]:
                            is_valid = False
                            break
                    
                    if is_valid:
                        content = text[pos:end_pos].strip()
                        if content and len(content) > 1:
                            bare_matches.append((pos, end_pos))
                    
                    pos = end_pos
                    continue
            
            # 模式3: 查找以字母开头后面跟着 = 的变量赋值
            if text[pos].isalpha():
                # 找到变量名（包括下标如 F_x）
                var_end = pos + 1
                while var_end < n:
                    c = text[var_end]
                    if c.isalpha() or c.isdigit() or c == '_':
                        var_end += 1
                    else:
                        break
                
                # 检查后面是否是 =
                temp_pos = var_end
                while temp_pos < n and text[temp_pos] in ' \t':
                    temp_pos += 1
                
                if temp_pos < n and text[temp_pos] == '=':
                    # 这是一个变量赋值，继续查找后面的数学内容
                    end_pos = temp_pos + 1
                    
                    # 继续查找后面的数学表达式
                    while end_pos < n:
                        temp_pos_check = end_pos
                        while temp_pos_check < n and text[temp_pos_check] in ' \t':
                            temp_pos_check += 1
                        
                        if temp_pos_check >= n:
                            break
                        
                        next_char = text[temp_pos_check]
                        if is_chinese_char(next_char) or next_char in chinese_punctuation:
                            break
                        
                        # 检查是否是数学相关字符
                        if next_char == '\\' and temp_pos_check + 1 < n and text[temp_pos_check + 1].isalpha():
                            # 遇到 \命令，继续扩展
                            cmd_pattern = re.compile(r'\\[a-zA-Z]+')
                            cmd_match = cmd_pattern.match(text, temp_pos_check)
                            if cmd_match:
                                brace_count = 0
                                paren_count = 0
                                cmd_end = cmd_match.end()
                                while cmd_end < n:
                                    c = text[cmd_end]
                                    if c == '{':
                                        brace_count += 1
                                    elif c == '}':
                                        brace_count -= 1
                                    elif c == '(':
                                        paren_count += 1
                                    elif c == ')':
                                        paren_count -= 1
                                    cmd_end += 1
                                    if brace_count == 0 and paren_count == 0:
                                        temp_pos_check2 = cmd_end
                                        while temp_pos_check2 < n and text[temp_pos_check2] in ' \t':
                                            temp_pos_check2 += 1
                                        if temp_pos_check2 >= n or is_chinese_char(text[temp_pos_check2]) or text[temp_pos_check2] in chinese_punctuation:
                                            break
                                end_pos = cmd_end
                            else:
                                end_pos += 1
                        elif next_char.isalpha() or next_char.isdigit() or next_char in '+-*/=<>^_()[]{}':
                            end_pos += 1
                        else:
                            break
                    
                    # 检查是否与已有数学区域重叠
                    is_valid = True
                    for i in range(pos, min(end_pos, n)):
                        if in_math_region[i]:
                            is_valid = False
                            break
                    
                    if is_valid:
                        content = text[pos:end_pos].strip()
                        if content and len(content) > 1:
                            bare_matches.append((pos, end_pos))
                    
                    pos = end_pos
                    continue
            
            pos += 1

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
