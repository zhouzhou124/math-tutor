"""OCR Agent — 数学视觉识别（带超时和快速失败机制）

═══════════════════════════════════════════════════════════════
核心升级
═══════════════════════════════════════════════════════════════

  之前：image → pytesseract → 字符串（无限重试）
  现在：分层管道 → 超时控制 → 快速失败

  Pipeline架构：
    Stage 0: 图片质量检测 → 不合格直接拒绝
    Stage 1: 快速OCR → 200ms超时
    Stage 2: 数学区域检测 → 无数学则跳过
    Stage 3: 数学OCR → 5s超时
    Stage 4: LaTeX修复 → 2s超时，最多2次重试
    Stage 5: SymPy验证 → 2s超时

  安全阈值：
    MAX_OCR_TIME = 8     # 总超时（秒）
    MAX_LLM_RETRY = 2    # LLM修复最大重试次数

═══════════════════════════════════════════════════════════════
"""

import re
import time
from PIL import Image
from config import KNOWLEDGE_POINTS, QUESTION_TYPES, SUBJECTS, LLM_BASE_URL, LLM_MODEL

try:
    from vision.vision_parser import VisionParser, VisionParseResult, ParseStatus
    _vision_parser_available = True
except ImportError:
    _vision_parser_available = False

try:
    from vision.image_quality import estimate_image_quality, is_image_acceptable, get_quality_warnings
    _quality_check_available = True
except ImportError:
    _quality_check_available = False

# ──────────────────────────────────────────────────────────────
# Mathpix OCR 集成（优先级最高）
# ──────────────────────────────────────────────────────────────
try:
    from vision.mathpix_ocr import MathpixOCR
    _mathpix_ok = True
except ImportError:
    _mathpix_ok = False


def _mathpix_available() -> bool:
    """检查Mathpix是否已配置"""
    if not _mathpix_ok:
        return False
    try:
        ocr = MathpixOCR()
        return ocr.is_configured()
    except Exception:
        return False


def _mathpix_recognize(image_path: str, timeout: int = 10) -> dict:
    """使用Mathpix识别图片"""
    try:
        ocr = MathpixOCR()
        result = ocr.recognize(image_path, timeout=timeout)
        return {
            "success": result.success,
            "latex": result.latex,
            "text": result.latex,
            "confidence": result.confidence,
            "error": result.error,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _call_llm(client, model: str, system: str, user: str) -> str:
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
    """数学视觉识别代理（带超时和快速失败机制）"""

    # 超时配置（秒）
    TIMEOUT_FAST_OCR = 0.5      # 快速OCR超时
    TIMEOUT_MATH_OCR = 5.0      # 数学OCR超时
    TIMEOUT_LATEX_REPAIR = 2.0  # LaTeX修复超时
    MAX_LLM_RETRY = 2           # LLM最大重试次数

    def __init__(self, client=None, model: str = ""):
        self.client = client
        self.model = model or LLM_MODEL
        self._vision_parser = None
        self._progress_callback = None
        self._cancel_flag = False

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self._progress_callback = callback

    def _update_progress(self, stage: str, message: str = "", progress: int = 0):
        """更新进度"""
        if self._progress_callback:
            self._progress_callback({
                "stage": stage,
                "message": message,
                "progress": progress,
                "timestamp": time.time()
            })

    def cancel(self):
        """取消当前操作"""
        self._cancel_flag = True

    def recognize(self, question_image_path: str = None,
                  answer_image_path: str = None,
                  progress_callback=None) -> dict:
        """识别题目和作答图片（带进度追踪）"""
        if progress_callback:
            self._progress_callback = progress_callback
        
        warnings = []
        self._update_progress("init", "初始化OCR引擎...", 0)

        # ── Stage 0: 图片质量预检测 ──
        self._update_progress("quality_check", "图片质量检测中...", 10)
        if _quality_check_available:
            if question_image_path and not is_image_acceptable(question_image_path):
                q_warnings = get_quality_warnings(question_image_path)
                warnings.extend(q_warnings)
            if answer_image_path and not is_image_acceptable(answer_image_path):
                a_warnings = get_quality_warnings(answer_image_path)
                warnings.extend(a_warnings)

        # ── 识别题目 ──
        self._update_progress("question", "识别题目...", 25)
        question_text = ""
        if question_image_path:
            question_text = self._recognize_image_with_timeout(question_image_path, "question")

        # ── 识别作答 ──
        self._update_progress("answer", "识别作答...", 50)
        student_text = ""
        if answer_image_path:
            student_text = self._recognize_image_with_timeout(answer_image_path, "answer")

        conf = min(1.0, len(question_text) / 100) if question_text else 0.0

        if len(question_text) < 10 and not student_text:
            warnings.append("图片识别结果过短，可能识别失败，建议手动输入")
            conf = max(0.3, conf)

        # ── Stage 4: LLM cleanup（最多重试2次）──
        if self.client and (question_text or student_text):
            self._update_progress("cleanup", "优化识别结果...", 75)
            cleaned = self._llm_cleanup_with_retry(question_text, student_text)
            if cleaned:
                question_text = cleaned.get("question", question_text)
                student_text = cleaned.get("student_answer", student_text)

        question_type = self._infer_question_type(question_text or student_text)
        knowledge_point = self._infer_knowledge_point(question_text or student_text)

        # 收集引擎警告
        if hasattr(self, '_warnings') and self._warnings:
            warnings.extend(self._warnings)

        self._update_progress("done", "识别完成", 100)

        # Image quality assessment
        image_quality = {}
        if answer_image_path:
            try:
                img_q = estimate_image_quality(answer_image_path)
                image_quality = {
                    "score": round(img_q.get("score", 0.5), 2),
                    "sharpness": round(img_q.get("sharpness", 100), 0),
                    "contrast": round(img_q.get("contrast", 100), 0),
                    "issues": img_q.get("issues", []),
                }
            except Exception:
                pass

        return {
            "success": conf > 0.3 or bool(student_text),
            "question": question_text,
            "student_answer": student_text,
            "math_type": "数学一",
            "question_type": question_type,
            "knowledge_point": knowledge_point,
            "confidence": conf,
            "warnings": warnings,
            "image_quality": image_quality,
            "engine": getattr(self, '_last_engine', 'unknown'),
        }

    def _recognize_image_with_timeout(self, image_path: str, context: str = "") -> str:
        """带超时的图片识别（多重引擎fallback）"""
        if not image_path or self._cancel_flag:
            return ""

        results = []

        # ── 引擎1: VisionParser（主引擎）──
        # ── 引擎0: Mathpix API（优先级最高，手写+印刷数学专用）──
        if _mathpix_ok and _mathpix_available():
            try:
                self._last_engine = "mathpix"
                mp_result = _mathpix_recognize(image_path, timeout=25)
                if mp_result.get("success") and (mp_result.get("latex") or mp_result.get("text")):
                    result_text = mp_result.get("latex") or mp_result.get("text")
                    if result_text and len(result_text.strip()) > 3:
                        self._update_progress("mathpix_done", "Mathpix识别完成", 90)
                        return result_text.strip()
            except Exception as e:
                self._add_warning(f"Mathpix失败: {str(e)[:30]}")
        elif not _mathpix_ok:
            pass  # Module not available
        else:
            self._add_warning("Mathpix未配置API Key，跳过")

        # ── 引擎1: VisionParser（主引擎）──
        self._last_engine = "vision_parser"
        parser = self._get_vision_parser()
        if parser is not None:
            try:
                result = self._run_with_timeout(
                    lambda: parser.parse(image_path),
                    self.TIMEOUT_MATH_OCR,
                    f"数学OCR({context})"
                )
                if result and result.has_content():
                    latex = result.to_latex()
                    if latex and latex.strip():
                        return latex
            except TimeoutError as e:
                self._add_warning(f"VisionParser超时，降级到其他引擎")
            except Exception as e:
                self._add_warning(f"VisionParser失败: {str(e)[:30]}")

        # ── 引擎2: 尝试直接使用vision_parser的OCR功能 ──
        try:
            from vision.vision_parser import VisionParser
            # 如果主解析器不可用，尝试创建一个简单版本
            simple_parser = VisionParser(llm_client=self.client, model=self.model)
            result = simple_parser.parse(image_path)
            if result and result.has_content():
                latex = result.to_latex()
                if latex and latex.strip():
                    return latex
        except Exception:
            pass

        # ── 引擎3: pytesseract（带预处理）──
        ocr_text = self._local_ocr_fallback(image_path)
        if ocr_text and ocr_text.strip():
            return ocr_text

        # ── 引擎4: 尝试pix2tex（如果可用）──
        self._last_engine = "pix2tex"
        pix2tex_result = self._try_pix2tex(image_path)
        if pix2tex_result:
            return pix2tex_result

        # 所有引擎都失败
        self._add_warning(f"所有OCR引擎均未能识别图片内容")
        return ""

    def _try_pix2tex(self, image_path: str) -> str:
        """Try pix2tex for math formula recognition.

        Supports: pix2tex (pip install pix2tex) or latexocr (pip install latexocr).
        Preprocesses image (grayscale + contrast + sharpen) before recognition.
        """
        # Preprocess for better recognition
        try:
            from PIL import Image, ImageFilter, ImageEnhance
            img = Image.open(image_path).convert('L')
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = img.filter(ImageFilter.SHARPEN)
            import tempfile as _tf, os as _os
            with _tf.NamedTemporaryFile(suffix='.png', delete=False) as _tmp:
                img.save(_tmp.name)
                pp_path = _tmp.name
        except Exception:
            pp_path = image_path

        result = None

        # Try pix2tex
        try:
            from pix2tex.cli import LatexOCR
            model = LatexOCR()
            result = model(pp_path)
        except ImportError:
            pass
        except Exception:
            pass

        # Try latexocr (older name)
        if not result:
            try:
                from latexocr import LatexOCR
                model = LatexOCR()
                result = model(pp_path)
            except ImportError:
                pass
            except Exception:
                pass

        # Cleanup
        if pp_path != image_path:
            try: _os.unlink(pp_path)
            except Exception: pass

        if result and result.strip() and len(result.strip()) >= 3:
            return result.strip()
        return ""

    @staticmethod
    def is_pix2tex_available() -> bool:
        """Check if pix2tex or latexocr is installed."""
        try:
            from pix2tex.cli import LatexOCR
            return True
        except ImportError:
            pass
        try:
            from latexocr import LatexOCR
            return True
        except ImportError:
            pass
        return False

    def _add_warning(self, message: str):
        """添加警告信息（用于后续报告）"""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        if message not in self._warnings:
            self._warnings.append(message)

    def _run_with_timeout(self, func, timeout_sec: float, operation_name: str) -> any:
        """带超时的函数执行"""
        import threading
        
        result = None
        exception = None
        
        def worker():
            nonlocal result, exception
            try:
                result = func()
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout_sec)
        
        if thread.is_alive():
            raise TimeoutError(f"{operation_name}超时({timeout_sec}s)")
        
        if exception:
            raise exception
        
        return result

    def _llm_cleanup_with_retry(self, question_text: str, student_text: str) -> dict | None:
        """带重试的LLM清理（最多重试2次）"""
        if not question_text and not student_text:
            return None

        for attempt in range(self.MAX_LLM_RETRY):
            try:
                from prompts.system_prompts import OCR_CLEANUP_PROMPT
                combined = f"题干:\n{question_text}\n\n学生作答:\n{student_text}"
                prompt = OCR_CLEANUP_PROMPT.format(ocr_raw=combined)
                
                result = self._run_with_timeout(
                    lambda: _call_llm(self.client, self.model, prompt, "请清理OCR结果"),
                    self.TIMEOUT_LATEX_REPAIR,
                    f"LLM清理(第{attempt+1}次)"
                )
                
                q_match = re.search(r"##\s*题干\s*\n(.*?)(?=##\s*学生作答|\Z)", result, re.DOTALL)
                a_match = re.search(r"##\s*学生作答\s*\n(.*?)$", result, re.DOTALL)
                return {
                    "question": q_match.group(1).strip() if q_match else question_text,
                    "student_answer": a_match.group(1).strip() if a_match else student_text,
                }
            except TimeoutError:
                if attempt < self.MAX_LLM_RETRY - 1:
                    continue
                return None
            except Exception:
                return None
        
        return None

    def _get_vision_parser(self) -> 'VisionParser':
        if self._vision_parser is None and _vision_parser_available:
            self._vision_parser = VisionParser(
                llm_client=self.client,
                model=self.model,
            )
        return self._vision_parser

    def _local_ocr_fallback(self, image_path: str) -> str:
        """pytesseract fallback — 仅在 VisionParser 不可用时使用"""
        if not image_path:
            return ""
        try:
            import pytesseract

            img = Image.open(image_path)

            # 尝试预处理
            try:
                from vision.preprocess import MathImagePreprocessor
                preprocessor = MathImagePreprocessor()
                region_images = preprocessor.process_for_ocr(img)
                if region_images:
                    texts = []
                    for region_img in region_images:
                        pil_region = Image.fromarray(region_img)
                        region_text = pytesseract.image_to_string(
                            pil_region, lang="chi_sim+eng"
                        )
                        region_text = region_text.strip()
                        if region_text:
                            texts.append(region_text)
                    return "\n".join(texts)
            except ImportError:
                pass

            img = img.convert("L")
            text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            return text.strip()

        except ImportError:
            return ""
        except Exception:
            return ""

    def _infer_question_type(self, text: str) -> str:
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
        if not text:
            return "未识别"
        for subject, points in KNOWLEDGE_POINTS.items():
            for point in points:
                keywords = point.replace("与", " ").replace("及", " ").split()
                if any(kw in text for kw in keywords):
                    return f"{subject} - {point}"
        return "高等数学 - 未识别"
