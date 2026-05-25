from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def make_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr("[Content_Types].xml", "<Types></Types>")
        docx.writestr("word/document.xml", document)


class WordGuardTests(unittest.TestCase):
    def test_valid_docx_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx = Path(tmp) / "paper.docx"
            make_docx(docx, ["This is a generated paragraph. " * 20])
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/word_guard.py",
                    str(docx),
                    "--markdown",
                    "--min-chars",
                    "100",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("Status: PASS", result.stdout)

    def test_placeholder_docx_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docx = Path(tmp) / "paper.docx"
            make_docx(docx, ["TODO replace this section with real content. " * 10])
            result = subprocess.run(
                [
                    sys.executable,
                    "src/scripts/word_guard.py",
                    str(docx),
                    "--markdown",
                    "--min-chars",
                    "50",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("placeholder", result.stdout)


if __name__ == "__main__":
    unittest.main()
