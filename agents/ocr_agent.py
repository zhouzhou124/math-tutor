"""OCR Agent — 图片文字识别（本地 pytesseract + 可选 LLM 清理）"""

import re
from PIL import Image
from config import KNOWLEDGE_POINTS, QUESTION_TYPES, SUBJECTS


def _call_llm(client, model: str, system: str, user: str) -> str:
    """通用 LLM 调用"""
    if client is None:
        return ""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content


class OCR_Agent:
    """识别题目图片和作答图片，输出结构化文本"""

    def __init__(self, client=None, model: str = "deepseek-chat"):
        self.client = client
        self.model = model

    def recognize(self, question_image_path: str,
                  answer_image_path: str = None) -> dict:
        """
        输入:
            question_image_path: 题目图片路径
            answer_image_path: 作答图片路径（可选，没有则只识别题目）
        输出:
            {
                "success": bool,
                "question": str,
                "student_answer": str,
                "math_type": str,       # 推断的数学类别
                "question_type": str,   # 推断的题型
                "knowledge_point": str, # 推断的知识点
                "confidence": float,    # 识别置信度 0-1
                "warnings": [str],      # 无法识别的位置/符号
            }
        """
        warnings = []

        # 本地 OCR 提取文本
        question_text = self._local_ocr(question_image_path)
        student_text = self._local_ocr(answer_image_path) if answer_image_path else ""

        # 置信度检查：OCR 结果过短 = 可能失败
        conf = min(1.0, len(question_text) / 100)

        if len(question_text) < 10:
            warnings.append("题目图片 OCR 结果过短，可能识别失败，建议手动输入")
            conf = 0.3

        # 如果 LLM 可用，用 LLM 清理 OCR 结果
        if self.client and question_text:
            cleaned = self._llm_cleanup(question_text, student_text)
            if cleaned:
                question_text = cleaned.get("question", question_text)
                student_text = cleaned.get("student_answer", student_text)

        # 推断题型和知识点
        question_type = self._infer_question_type(question_text)
        knowledge_point = self._infer_knowledge_point(question_text)

        return {
            "success": conf > 0.3,
            "question": question_text,
            "student_answer": student_text,
            "math_type": "数学一",  # OCR 无法自动推断，需用户确认
            "question_type": question_type,
            "knowledge_point": knowledge_point,
            "confidence": conf,
            "warnings": warnings,
        }

    def _local_ocr(self, image_path: str) -> str:
        """使用 pytesseract 进行本地 OCR"""
        if not image_path:
            return ""
        try:
            import pytesseract
            img = Image.open(image_path)
            # 预处理：转灰度 + 二值化提高 OCR 准确率
            img = img.convert("L")
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            return text.strip()
        except ImportError:
            return "[OCR模块未安装] 请安装 pytesseract 和 Tesseract-OCR"
        except Exception:
            return "[OCR 失败] 图片无法识别，请重新拍摄或手动输入"

    def _llm_cleanup(self, question_text: str, student_text: str) -> dict | None:
        """用 LLM 清理 OCR 结果，分离题干和作答"""
        from prompts.system_prompts import OCR_CLEANUP_PROMPT

        combined = f"题干:\n{question_text}\n\n学生作答:\n{student_text}"
        prompt = OCR_CLEANUP_PROMPT.format(ocr_raw=combined)

        try:
            result = _call_llm(self.client, self.model, prompt, "请清理OCR结果")
            # 解析输出
            q_match = re.search(r"##\s*题干\s*\n(.*?)(?=##\s*学生作答|\Z)", result, re.DOTALL)
            a_match = re.search(r"##\s*学生作答\s*\n(.*?)$", result, re.DOTALL)
            return {
                "question": q_match.group(1).strip() if q_match else question_text,
                "student_answer": a_match.group(1).strip() if a_match else student_text,
            }
        except Exception:
            return None

    def _infer_question_type(self, text: str) -> str:
        """从文本推断题型"""
        if not text:
            return "解答题"
        if any(word in text for word in ["选择", "下列选项中", "正确的一项是"]):
            return "选择题"
        if any(word in text for word in ["填空", "______"]):
            return "填空题"
        if any(word in text for word in ["证明", "求证"]):
            return "证明题"
        return "解答题"

    def _infer_knowledge_point(self, text: str) -> str:
        """从文本推断知识点"""
        if not text:
            return "未识别"
        for subject, points in KNOWLEDGE_POINTS.items():
            for point in points:
                # 简单关键词匹配
                keywords = point.replace("与", " ").replace("及", " ").split()
                if any(kw in text for kw in keywords):
                    return f"{subject} - {point}"
        return "高等数学 - 未识别"
