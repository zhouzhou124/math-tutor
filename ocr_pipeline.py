"""
OCR Pipeline — 增强 OCR 管线（三级 fallback）

Layer 1: pytesseract 本地 OCR（快，免费）
Layer 2: LLM text cleanup（用 LLM 清洗 OCR 噪声）
Layer 3: Vision API（base64 传图给多模态模型）

仅在 pytesseract 置信度过低或用户显式请求时触发高层 fallback。
"""

import base64
import re

from config import (
    VISION_API_KEY,
    VISION_BASE_URL,
    VISION_MODEL,
)


def ocr_with_fallback(
    image_paths: list[str],
    client=None,
    model: str = "deepseek-chat",
    force_vision: bool = False,
) -> dict:
    """
    OCR 管线：pytesseract → LLM cleanup → Vision API fallback。

    Args:
        image_paths: [question_image_path, answer_image_path]
                     其中任一可为 None（表示没有该图片）
        client: OpenAI-compatible LLM client
        model: LLM 模型名
        force_vision: 是否强制使用 Vision API（跳过 pytesseract）

    Returns:
        {
            "success": bool,
            "question": str,
            "student_answer": str,
            "confidence": float,
            "source": "pytesseract" | "llm_cleanup" | "vision_api" | "manual",
            "warnings": [str],
        }
    """
    warnings: list[str] = []
    q_path = image_paths[0] if len(image_paths) > 0 else None
    a_path = image_paths[1] if len(image_paths) > 1 else None

    # ── Layer 1: pytesseract ──
    question_text = ""
    student_text = ""

    if q_path:
        question_text = _pytesseract_ocr(q_path)
    if a_path:
        student_text = _pytesseract_ocr(a_path)

    source = "pytesseract"
    total_len = len(question_text) + len(student_text)

    # 置信度估计
    if total_len == 0:
        confidence = 0.0
        warnings.append("OCR 未识别到任何文本")
    elif total_len < 20:
        confidence = 0.3
        warnings.append("OCR 结果过短，可能识别不完整")
    elif total_len < 60:
        confidence = 0.6
    else:
        confidence = 0.85

    # ── Layer 2: LLM cleanup（可选）──
    if client and total_len > 0:
        try:
            cleaned = _llm_cleanup(client, model, question_text, student_text)
            if cleaned:
                question_text = cleaned.get("question", question_text)
                student_text = cleaned.get("student_answer", student_text)
                source = "llm_cleanup"
                confidence = min(1.0, confidence + 0.15)
        except Exception as e:
            warnings.append(f"LLM cleanup 失败: {e}")

    # ── Layer 3: Vision API fallback ──
    if confidence < 0.4 or force_vision:
        # 尝试 Vision API 处理作答图片（手写体最需要）
        if a_path and _can_use_vision():
            try:
                vision_text = _vision_api_ocr(a_path)
                if vision_text and len(vision_text) > len(student_text) * 1.5:
                    student_text = vision_text
                    source = "vision_api"
                    confidence = 0.85
                    # 清理掉旧的短结果警告
                    warnings = [w for w in warnings if "过短" not in w]
            except Exception as e:
                warnings.append(f"Vision API 失败: {e}")

        if q_path and _can_use_vision() and not question_text:
            try:
                vision_text = _vision_api_ocr(q_path)
                if vision_text:
                    question_text = vision_text
                    source = "vision_api"
                    confidence = 0.85
            except Exception as e:
                warnings.append(f"Vision API 题目识别失败: {e}")

    # ── 推断题型和知识点 ──
    question_type = _infer_question_type(question_text)

    return {
        "success": confidence >= 0.3 or force_vision,
        "question": question_text,
        "student_answer": student_text,
        "confidence": confidence,
        "source": source,
        "warnings": warnings,
        "question_type": question_type,
        "math_type": "数学一",
    }


# ═══════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════

def _can_use_vision() -> bool:
    return bool(VISION_API_KEY and VISION_API_KEY.strip())


def _pytesseract_ocr(image_path: str) -> str:
    """本地 pytesseract OCR。"""
    if not image_path:
        return ""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        img = img.convert("L")  # 灰度
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text.strip()
    except ImportError:
        return ""
    except Exception:
        return ""


def _llm_cleanup(client, model: str, question_text: str, student_text: str) -> dict | None:
    """LLM 清洗 OCR 输出，分离题干和作答。"""
    from prompts.system_prompts import OCR_CLEANUP_PROMPT

    combined = f"题干:\n{question_text}\n\n学生作答:\n{student_text}"
    try:
        prompt = OCR_CLEANUP_PROMPT.format(ocr_raw=combined)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 OCR 校对助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        result = response.choices[0].message.content
        q_match = re.search(r"##\s*题干\s*\n(.*?)(?=##\s*学生作答|\Z)", result, re.DOTALL)
        a_match = re.search(r"##\s*学生作答\s*\n(.*?)$", result, re.DOTALL)
        return {
            "question": q_match.group(1).strip() if q_match else question_text,
            "student_answer": a_match.group(1).strip() if a_match else student_text,
        }
    except Exception:
        return None


def _vision_api_ocr(image_path: str) -> str:
    """
    使用 OpenAI-compatible Vision API 识别图片中的数学内容。
    以 base64 编码图片发送。
    """
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # 推断 MIME 类型
    ext = image_path.lower().rsplit(".", 1)[-1] if "." in image_path else "png"
    mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "gif", "webp") else "image/png"

    from openai import OpenAI

    vision_client = OpenAI(
        api_key=VISION_API_KEY,
        base_url=VISION_BASE_URL,
    )

    response = vision_client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract ALL mathematical content from this image as LaTeX. "
                            "Preserve all formulas, symbols, and notation exactly as written. "
                            "For handwritten answers, transcribe step by step. "
                            "Return ONLY the LaTeX content, no commentary."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_data}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        temperature=0.1,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def _infer_question_type(text: str) -> str:
    """从文本推断题型。"""
    if not text:
        return "解答题"
    if any(w in text for w in ["选择", "下列选项中", "正确的一项是", "A.", "B.", "C.", "D."]):
        return "选择题"
    if any(w in text for w in ["填空", "______"]):
        return "填空题"
    if any(w in text for w in ["证明", "求证"]):
        return "证明题"
    return "解答题"
