from typing import Optional
from .document_ast import Document, DocumentNode, BlockType
from .render_ir import (
    RenderNode, RenderType, RenderTree,
    TextNode, InlineMathNode, BlockMathNode, AlignNode,
    MatrixNode, CasesNode, StepNode, ProofNode, WarningNode,
    ObligationNode, FinalAnswerNode, ListNode, TableNode,
    DividerNode, CodeNode, ExpanderNode
)


class DocumentToIRConverter:
    """
    将 Document AST 转换为 Render IR。

    这是关键的语义保留环节：
      Document AST (结构化语义)
        → Render IR (可渲染语义)
        → StreamlitRenderer / HTMLRenderer / etc.

    重要：所有语义 metadata 都原样传递到 Render IR，
    不再做字符串化处理。
    """

    def convert(self, doc: Document) -> RenderNode:
        """主入口：将 Document 转换为 RenderTree"""
        if not doc or not doc.nodes:
            return RenderNode(type=RenderType.TEXT, content="")

        children = []
        for node in doc.nodes:
            ir_node = self._convert_node(node)
            if ir_node:
                children.append(ir_node)

        if len(children) == 1:
            return children[0]

        return RenderNode(type=RenderType.CONTAINER, children=tuple(children))

    def _convert_node(self, node: DocumentNode) -> Optional[RenderNode]:
        if not node:
            return None

        converters = {
            BlockType.PARAGRAPH: self._convert_paragraph,
            BlockType.INLINE_MATH: self._convert_inline_math,
            BlockType.DISPLAY_MATH: self._convert_display_math,
            BlockType.STEP: self._convert_step,
            BlockType.PROOF: self._convert_proof,
            BlockType.MATRIX: self._convert_matrix,
            BlockType.CASE_BRANCH: self._convert_cases,
            BlockType.EQUATION: self._convert_equation,
            BlockType.WARNING: self._convert_warning,
            BlockType.OBLIGATION: self._convert_obligation,
            BlockType.FINAL_ANSWER: self._convert_final_answer,
            BlockType.LIST: self._convert_list,
            BlockType.TABLE: self._convert_table,
            BlockType.DIVIDER: self._convert_divider,
            BlockType.CODE: self._convert_code,
            BlockType.TITLE: self._convert_title,
        }

        converter = converters.get(node.type)
        if converter:
            return converter(node)
        return TextNode(text=str(node.content) if node.content else "")

    def _convert_paragraph(self, node: DocumentNode) -> RenderNode:
        content = node.content
        if isinstance(content, str):
            prefix = node.metadata.get("prefix", "")
            suffix = node.metadata.get("suffix", "")
            text = prefix + content + suffix
            return TextNode(text=text, metadata=node.metadata)
        return TextNode(text=str(content), metadata=node.metadata)

    def _convert_inline_math(self, node: DocumentNode) -> InlineMathNode:
        return InlineMathNode(latex=str(node.content), metadata=node.metadata)

    def _convert_display_math(self, node: DocumentNode) -> BlockMathNode:
        env = node.metadata.get("environment", "")
        if env in ("aligned", "align", "eqnarray", "gather"):
            return AlignNode(latex=str(node.content), metadata=node.metadata)
        return BlockMathNode(latex=str(node.content), environment=env, metadata=node.metadata)

    def _convert_step(self, node: DocumentNode) -> StepNode:
        content = node.content
        if hasattr(content, "__dataclass_fields__"):
            content_dict = {f: getattr(content, f) for f in content.__dataclass_fields__ if not f.startswith("_")}
        else:
            content_dict = {"title": str(content)}

        role = node.metadata.get("role", "")
        step_id = node.metadata.get("source_step_id", "") or content_dict.get("step_id", "")

        children = []
        for child_node in node.children:
            child_ir = self._convert_node(child_node)
            if child_ir:
                children.append(child_ir)

        return StepNode(
            step_id=step_id,
            title=content_dict.get("title", ""),
            operation=content_dict.get("operation", ""),
            legality=content_dict.get("legality", "unknown"),
            input_expr=content_dict.get("input_expr", ""),
            output_expr=content_dict.get("output_expr", ""),
            explanation=content_dict.get("explanation", ""),
            theorem_used=content_dict.get("theorem_used", ""),
            children=tuple(children),
            metadata=node.metadata
        )

    def _convert_proof(self, node: DocumentNode) -> ProofNode:
        content = node.content
        if hasattr(content, "__dataclass_fields__"):
            content_dict = {f: getattr(content, f) for f in content.__dataclass_fields__ if not f.startswith("_")}
        else:
            content_dict = {}

        children = []
        for child_node in node.children:
            child_ir = self._convert_node(child_node)
            if child_ir:
                children.append(child_ir)

        return ProofNode(
            strategy=content_dict.get("strategy", "direct"),
            goal=content_dict.get("goal", ""),
            assumptions=content_dict.get("assumptions", ()),
            pending_obligations=content_dict.get("pending_obligations", ()),
            discharged=content_dict.get("discharged", ()),
            children=tuple(children),
            metadata=node.metadata
        )

    def _convert_matrix(self, node: DocumentNode) -> MatrixNode:
        content = node.content
        if hasattr(content, "__dataclass_fields__"):
            rows = list(content.rows) if hasattr(content, "rows") else []
            env = content.environment if hasattr(content, "environment") else "pmatrix"
            label = content.label if hasattr(content, "label") else ""
        elif isinstance(content, list):
            rows = content
            env = "pmatrix"
            label = ""
        else:
            rows = []
            env = "pmatrix"
            label = ""

        return MatrixNode(
            rows=rows,
            environment=env,
            label=label,
            metadata=node.metadata
        )

    def _convert_cases(self, node: DocumentNode) -> CasesNode:
        return CasesNode(latex=str(node.content), metadata=node.metadata)

    def _convert_equation(self, node: DocumentNode) -> BlockMathNode:
        content = node.content
        if hasattr(content, "__dataclass_fields__"):
            lhs = content.lhs if hasattr(content, "lhs") else ""
            rhs = content.rhs if hasattr(content, "rhs") else str(content)
            label = content.label if hasattr(content, "label") else ""
            latex = f"{lhs} = {rhs}"
            if label:
                latex += f"\\tag{{{label}}}"
        else:
            latex = str(content)

        metadata = dict(node.metadata)
        metadata["role"] = node.metadata.get("role", "equation")
        return BlockMathNode(latex=latex, environment="equation", metadata=metadata)

    def _convert_warning(self, node: DocumentNode) -> WarningNode:
        content = node.content
        if hasattr(content, "__dataclass_fields__"):
            message = content.message if hasattr(content, "message") else str(content)
            severity = content.severity if hasattr(content, "severity") else "warning"
            suggestion = content.suggestion if hasattr(content, "suggestion") else ""
        else:
            message = str(content)
            severity = "warning"
            suggestion = ""

        return WarningNode(
            message=message,
            severity=severity,
            suggestion=suggestion,
            metadata=node.metadata
        )

    def _convert_obligation(self, node: DocumentNode) -> ObligationNode:
        content = str(node.content)
        obligation_id = node.metadata.get("obligation_id", "")
        discharged = node.metadata.get("discharged", False)

        return ObligationNode(
            text=content,
            obligation_id=obligation_id,
            discharged=discharged,
            metadata=node.metadata
        )

    def _convert_final_answer(self, node: DocumentNode) -> FinalAnswerNode:
        content = node.content
        if hasattr(content, "__dataclass_fields__"):
            answer = content.answer if hasattr(content, "answer") else str(content)
            answer_expr = content.answer_expr if hasattr(content, "answer_expr") else ""
            is_boxed = content.is_boxed if hasattr(content, "is_boxed") else True
        else:
            answer = str(content)
            answer_expr = ""
            is_boxed = True

        return FinalAnswerNode(
            answer=answer,
            answer_expr=answer_expr,
            is_boxed=is_boxed,
            metadata=node.metadata
        )

    def _convert_list(self, node: DocumentNode) -> ListNode:
        content = node.content
        if isinstance(content, (list, tuple)):
            items = tuple(str(item) for item in content)
        elif isinstance(content, str):
            items = (content,)
        else:
            items = ()

        return ListNode(items=items, metadata=node.metadata)

    def _convert_table(self, node: DocumentNode) -> TableNode:
        content = node.content
        if hasattr(content, "__dataclass_fields__"):
            headers = tuple(content.headers) if hasattr(content, "headers") else ()
            rows = tuple(tuple(r) for r in content.rows) if hasattr(content, "rows") else ()
            caption = content.caption if hasattr(content, "caption") else ""
        elif isinstance(content, dict):
            headers = tuple(content.get("headers", ()))
            rows = tuple(tuple(r) for r in content.get("rows", []))
            caption = content.get("caption", "")
        else:
            headers = ()
            rows = ()
            caption = ""

        return TableNode(
            headers=headers,
            rows=rows,
            caption=caption,
            metadata=node.metadata
        )

    def _convert_divider(self, node: DocumentNode) -> DividerNode:
        return DividerNode(metadata=node.metadata)

    def _convert_code(self, node: DocumentNode) -> CodeNode:
        language = node.metadata.get("language", "")
        code = str(node.content)
        return CodeNode(code=code, language=language, metadata=node.metadata)

    def _convert_title(self, node: DocumentNode) -> TextNode:
        text = f"## {node.content}" if node.content else ""
        return TextNode(text=text, metadata=node.metadata)
