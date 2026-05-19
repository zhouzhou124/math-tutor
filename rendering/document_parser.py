from typing import Optional
from rendering.document_ast import (
    Document, DocumentNode, BlockType,
    StepBlock, ProofBlock, MatrixBlock, EquationBlock,
    TableBlock, WarningBlock, FinalAnswerBlock
)
from rendering.content_classifier import ContentClassifier, ContentSegment, ContentType


class DocumentParser:
    """
    将混合文本（中文 + LaTeX + 英文）解析为 Document AST。

    输入:
      "由 Sylvester 不等式：$$r(AB)\\ge r(A)+r(B)-n$$，将(2)代入(1)"
    输出:
      Document(nodes=[
        DocumentNode(BlockType.PARAGRAPH, "由 Sylvester 不等式："),
        DocumentNode(BlockType.DISPLAY_MATH, "r(AB)\\ge r(A)+r(B)-n", metadata={"role": "theorem"}),
        DocumentNode(BlockType.PARAGRAPH, "，将(2)代入(1)"),
      ])
    """

    def __init__(self):
        self._classifier = ContentClassifier()

    def parse(self, text: str, default_role: str = "") -> Document:
        """
        主入口：将混合文本解析为 Document AST。

        Args:
            text: 原始混合文本
            default_role: 默认数学角色 (如 "student_answer", "standard_answer", "question")
        """
        if not text:
            return Document(nodes=[])

        if not isinstance(text, str):
            text = str(text)

        text = self._preprocess(text)

        segments = self._classifier.classify(text)

        nodes = []
        for seg in segments:
            node = self._segment_to_node(seg, default_role)
            if node:
                nodes.append(node)

        return Document(nodes=tuple(nodes))

    def _preprocess(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text

    def _segment_to_node(self, seg: ContentSegment, default_role: str) -> Optional[DocumentNode]:
        content = seg.content
        if not content:
            return None

        role = seg.metadata.get("role", default_role)

        if seg.type == ContentType.INLINE_MATH:
            return DocumentNode(
                type=BlockType.INLINE_MATH,
                content=content,
                metadata={"role": role, "confidence": seg.confidence}
            )

        if seg.type == ContentType.BLOCK_MATH:
            return DocumentNode(
                type=BlockType.DISPLAY_MATH,
                content=content,
                metadata={"role": role, "confidence": seg.confidence}
            )

        if seg.type == ContentType.ALIGNED:
            return DocumentNode(
                type=BlockType.DISPLAY_MATH,
                content=content,
                metadata={"role": "aligned", "environment": "aligned", "confidence": seg.confidence}
            )

        if seg.type == ContentType.MATRIX:
            return DocumentNode(
                type=BlockType.MATRIX,
                content=self._parse_matrix_content(content),
                metadata={"role": "matrix", "confidence": seg.confidence}
            )

        if seg.type == ContentType.CASES:
            return DocumentNode(
                type=BlockType.CASE_BRANCH,
                content=self._parse_cases_content(content),
                metadata={"role": "cases", "confidence": seg.confidence}
            )

        if seg.type == ContentType.EQUALITY_CHAIN:
            return DocumentNode(
                type=BlockType.EQUATION,
                content=content,
                metadata={"role": "derivation", "confidence": seg.confidence}
            )

        if seg.type == ContentType.PROOF_TRANSITION:
            return self._parse_proof_node(content, seg.metadata)

        if seg.type == ContentType.FINAL_ANSWER:
            return self._parse_final_answer_node(content, role)

        if seg.type == ContentType.TABLE:
            return self._parse_table_node(content)

        if seg.type == ContentType.LIST:
            items = [line.strip("- ").strip() for line in content.split("\n") if line.strip()]
            return DocumentNode(
                type=BlockType.LIST,
                content=tuple(items),
                metadata={"role": role}
            )

        if seg.type == ContentType.DIVIDER:
            return DocumentNode(type=BlockType.DIVIDER, content="---")

        if seg.type == ContentType.WARNING:
            return DocumentNode(
                type=BlockType.WARNING,
                content=WarningBlock(message=content, severity="warning"),
                metadata={"role": role}
            )

        if seg.type == ContentType.ERROR:
            return DocumentNode(
                type=BlockType.WARNING,
                content=WarningBlock(message=content, severity="error"),
                metadata={"role": role}
            )

        if seg.type == ContentType.OBLIGATION:
            return DocumentNode(
                type=BlockType.OBLIGATION,
                content=content,
                metadata={"role": "obligation"}
            )

        if seg.type == ContentType.THEOREM:
            return DocumentNode(
                type=BlockType.PARAGRAPH,
                content=content,
                metadata={"role": "theorem", "prefix": "📖 "}
            )

        if seg.type == ContentType.DEFINITION:
            return DocumentNode(
                type=BlockType.PARAGRAPH,
                content=content,
                metadata={"role": "definition", "prefix": "📚 "}
            )

        if seg.type == ContentType.OPTION:
            return DocumentNode(
                type=BlockType.PARAGRAPH,
                content=content,
                metadata={"role": "option"}
            )

        if seg.type == ContentType.DERIVATION_STEP:
            return self._parse_derivation_step(content, role)

        return DocumentNode(
            type=BlockType.PARAGRAPH,
            content=content,
            metadata={"role": role}
        )

    def _parse_proof_node(self, content: str, metadata: dict) -> DocumentNode:
        lines = content.split("\n")
        assumptions = []
        goal = ""
        pending = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if "假设" in line:
                assumptions.append(line.replace("假设", "").strip(":：").strip())
            elif "目标" in line or "求证" in line:
                goal = line.replace("目标", "").replace("求证", "").strip(":：").strip()
            elif "待证" in line:
                pending.append(line.replace("待证", "").strip(":：").strip())

        proof = ProofBlock(
            strategy="direct" if goal else "unknown",
            goal=goal,
            assumptions=tuple(assumptions),
            pending_obligations=tuple(pending)
        )
        return DocumentNode(
            type=BlockType.PROOF,
            content=proof,
            metadata=metadata
        )

    def _parse_final_answer_node(self, content: str, role: str) -> DocumentNode:
        answer_content = content.replace("**答案**", "").replace("📌", "").replace("最终答案", "").strip()
        answer_content = answer_content.lstrip(":： ").strip()

        answer_expr = ""
        if "=" in answer_content:
            idx = answer_content.rfind("=")
            answer_expr = answer_content[idx + 1:].strip()
            answer_content = answer_content[:idx + 1].strip() + " = " + answer_expr

        return DocumentNode(
            type=BlockType.FINAL_ANSWER,
            content=FinalAnswerBlock(
                answer=answer_content,
                answer_expr=answer_expr,
                is_boxed=True
            ),
            metadata={"role": role}
        )

    def _parse_matrix_content(self, content: str) -> MatrixBlock:
        from re import findall
        rows_str = findall(r"\\\\", content)
        if not rows_str:
            rows = [[c.strip() for c in content.split("&")]]
        else:
            row_texts = content.split("\\\\")
            rows = []
            for row_text in row_texts:
                if row_text.strip():
                    cells = [c.strip() for c in row_text.split("&")]
                    rows.append(cells)

        return MatrixBlock(
            rows=tuple(tuple(row) for row in rows),
            environment="pmatrix"
        )

    def _parse_cases_content(self, content: str) -> str:
        return content

    def _parse_table_node(self, content: str) -> DocumentNode:
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if not lines:
            return DocumentNode(type=BlockType.PARAGRAPH, content="")

        headers = []
        rows = []

        if "|" in lines[0]:
            parts = [p.strip() for p in lines[0].split("|")]
            parts = [p for p in parts if p and p != "---"]
            if parts:
                headers = parts
                lines = lines[1:]

        for line in lines:
            if "|" in line:
                cells = [p.strip() for p in line.split("|")]
                cells = [p for p in cells if p and p != "---"]
                if cells:
                    rows.append(cells)

        table = TableBlock(
            headers=tuple(headers),
            rows=tuple(tuple(r) for r in rows)
        )
        return DocumentNode(
            type=BlockType.TABLE,
            content=table
        )

    def _parse_derivation_step(self, content: str, role: str) -> DocumentNode:
        import re

        step = StepBlock(
            title="推导",
            output_expr=content,
            legality="unknown"
        )
        return DocumentNode(
            type=BlockType.STEP,
            content=step,
            metadata={"role": role}
        )
