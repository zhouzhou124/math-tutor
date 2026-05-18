"""OCR Pipeline Controller — 数学视觉识别管道控制器

核心改进：
  1. Timeout System - 每层都有超时限制
  2. Progressive OCR - 渐进式识别（普通OCR → 公式检测 → 数学OCR）
  3. Fast-Fail Strategy - 快速失败策略
  4. Progress Tracking - 进度追踪
  5. Image Quality Pre-check - 图片质量预检测

Pipeline 架构：
┌─────────────────────────────────────────────────────────────┐
│  Stage 0: Image Quality Check                              │
│  ├─ blur_score, contrast_score, tilt_score, shadow_score   │
│  └─ 低于阈值直接拒绝                                       │
├─────────────────────────────────────────────────────────────┤
│  Stage 1: Fast OCR (200ms timeout)                         │
│  └─ 只检测是否有文字，不做数学结构分析                      │
├─────────────────────────────────────────────────────────────┤
│  Stage 2: Math Region Detection (1s timeout)               │
│  └─ 检测是否存在数学结构（∫, lim, Σ, √等）                 │
├─────────────────────────────────────────────────────────────┤
│  Stage 3: Math OCR (5s timeout)                            │
│  └─ 完整数学公式识别                                       │
├─────────────────────────────────────────────────────────────┤
│  Stage 4: LaTeX Repair (2s timeout, max 2 retries)         │
│  └─ LLM修复无效LaTeX                                       │
├─────────────────────────────────────────────────────────────┤
│  Stage 5: SymPy Verification (2s timeout)                  │
│  └─ 验证数学正确性                                         │
└─────────────────────────────────────────────────────────────┘

安全阈值：
  MAX_OCR_TIME = 8    # 总OCR超时（秒）
  MAX_PARSE_TIME = 2   # 单个解析步骤超时（秒）
  MAX_LLM_RETRY = 2    # LLM修复最大重试次数
"""

import time
import signal
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any, Dict, List


class PipelineStage(Enum):
    """管道阶段枚举"""
    IMAGE_CHECK = "image_check"
    FAST_OCR = "fast_ocr"
    MATH_REGION_DETECT = "math_region_detect"
    MATH_OCR = "math_ocr"
    LATEX_REPAIR = "latex_repair"
    SYMPY_VERIFY = "sympy_verify"


class PipelineStatus(Enum):
    """管道状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class PipelineProgress:
    """管道进度信息"""
    stage: PipelineStage = PipelineStage.IMAGE_CHECK
    stage_index: int = 0
    total_stages: int = 6
    message: str = ""
    elapsed_ms: float = 0.0
    estimated_remaining_ms: float = 0.0


@dataclass
class ImageQuality:
    """图片质量评分（0-100，越高越好）"""
    blur_score: int = 0
    contrast_score: int = 0
    tilt_score: int = 0
    shadow_score: int = 0
    
    @property
    def overall(self) -> int:
        """综合评分"""
        return int((self.blur_score + self.contrast_score + self.tilt_score + self.shadow_score) / 4)
    
    @property
    def is_acceptable(self) -> bool:
        """是否可接受（综合评分 >= 50）"""
        return self.overall >= 50


@dataclass
class OCRResult:
    """OCR结果"""
    success: bool = False
    text: str = ""
    latex: str = ""
    confidence: float = 0.0
    status: PipelineStatus = PipelineStatus.COMPLETED
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    stage_reached: PipelineStage = PipelineStage.IMAGE_CHECK


class TimeoutError(Exception):
    """超时异常"""
    pass


def timeout(seconds: float, error_message: str = "Operation timed out"):
    """超时装饰器"""
    def decorator(func: Callable) -> Callable:
        def handler(signum, frame):
            raise TimeoutError(error_message)
        
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(int(seconds))
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
        return wrapper
    return decorator


class OCRPipeline:
    """OCR管道控制器"""
    
    # 超时配置（秒）
    MAX_STAGE_TIME = {
        PipelineStage.IMAGE_CHECK: 1.0,
        PipelineStage.FAST_OCR: 0.5,
        PipelineStage.MATH_REGION_DETECT: 1.0,
        PipelineStage.MATH_OCR: 5.0,
        PipelineStage.LATEX_REPAIR: 2.0,
        PipelineStage.SYMPY_VERIFY: 2.0,
    }
    
    # 阶段名称映射
    STAGE_NAMES = {
        PipelineStage.IMAGE_CHECK: "图片质量检测",
        PipelineStage.FAST_OCR: "快速OCR",
        PipelineStage.MATH_REGION_DETECT: "数学区域检测",
        PipelineStage.MATH_OCR: "数学公式识别",
        PipelineStage.LATEX_REPAIR: "LaTeX修复",
        PipelineStage.SYMPY_VERIFY: "数学验证",
    }
    
    # 阶段耗时预估（毫秒）
    STAGE_ESTIMATES = {
        PipelineStage.IMAGE_CHECK: 200,
        PipelineStage.FAST_OCR: 300,
        PipelineStage.MATH_REGION_DETECT: 500,
        PipelineStage.MATH_OCR: 3000,
        PipelineStage.LATEX_REPAIR: 1000,
        PipelineStage.SYMPY_VERIFY: 500,
    }
    
    def __init__(self):
        self.progress = PipelineProgress()
        self.start_time = 0.0
        self._cancel_flag = False
        self._progress_callback = None
    
    def set_progress_callback(self, callback: Callable[[PipelineProgress], None]):
        """设置进度回调函数"""
        self._progress_callback = callback
    
    def _update_progress(self, stage: PipelineStage, message: str = ""):
        """更新进度"""
        self.progress.stage = stage
        self.progress.stage_index = list(PipelineStage).index(stage) + 1
        self.progress.message = message
        self.progress.elapsed_ms = (time.time() - self.start_time) * 1000
        
        # 计算预计剩余时间
        remaining_stages = list(PipelineStage)[self.progress.stage_index:]
        self.progress.estimated_remaining_ms = sum(
            self.STAGE_ESTIMATES.get(s, 500) for s in remaining_stages
        )
        
        if self._progress_callback:
            self._progress_callback(self.progress)
    
    def cancel(self):
        """取消管道执行"""
        self._cancel_flag = True
    
    def _check_cancel(self):
        """检查是否已取消"""
        if self._cancel_flag:
            raise RuntimeError("Pipeline cancelled")
    
    def run(self, image_path: str) -> OCRResult:
        """执行完整OCR管道"""
        self.start_time = time.time()
        self._cancel_flag = False
        result = OCRResult()
        
        stages = [
            (PipelineStage.IMAGE_CHECK, self._stage_image_check),
            (PipelineStage.FAST_OCR, self._stage_fast_ocr),
            (PipelineStage.MATH_REGION_DETECT, self._stage_math_region_detect),
            (PipelineStage.MATH_OCR, self._stage_math_ocr),
            (PipelineStage.LATEX_REPAIR, self._stage_latex_repair),
            (PipelineStage.SYMPY_VERIFY, self._stage_sympy_verify),
        ]
        
        for stage, handler in stages:
            if self._cancel_flag:
                result.status = PipelineStatus.ABORTED
                result.error = "用户取消"
                return result
            
            self._update_progress(stage, f"{self.STAGE_NAMES[stage]}中...")
            
            try:
                timeout_sec = self.MAX_STAGE_TIME[stage]
                stage_result = self._run_with_timeout(handler, image_path, timeout_sec)
                
                if stage_result is not None:
                    if isinstance(stage_result, ImageQuality):
                        if not stage_result.is_acceptable:
                            result.success = False
                            result.status = PipelineStatus.FAILED
                            result.error = f"图片质量过低（综合评分: {stage_result.overall}/100）"
                            result.warnings.append(f"模糊度: {stage_result.blur_score}/100")
                            result.warnings.append(f"对比度: {stage_result.contrast_score}/100")
                            result.warnings.append(f"倾斜度: {stage_result.tilt_score}/100")
                            result.warnings.append(f"阴影: {stage_result.shadow_score}/100")
                            return result
                    elif isinstance(stage_result, str):
                        result.text = stage_result
                    elif isinstance(stage_result, dict):
                        result.__dict__.update(stage_result)
                
                result.stage_reached = stage
                
            except TimeoutError:
                result.status = PipelineStatus.TIMEOUT
                result.error = f"{self.STAGE_NAMES[stage]}超时（{timeout_sec}秒）"
                result.warnings.append(result.error)
                return result
            except Exception as e:
                result.status = PipelineStatus.FAILED
                result.error = f"{self.STAGE_NAMES[stage]}失败: {str(e)}"
                result.warnings.append(result.error)
                return result
        
        result.success = True
        result.status = PipelineStatus.COMPLETED
        return result
    
    def _run_with_timeout(self, func: Callable, image_path: str, timeout_sec: float) -> Any:
        """带超时的函数执行"""
        import threading
        
        result = None
        exception = None
        
        def worker():
            nonlocal result, exception
            try:
                result = func(image_path)
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout_sec)
        
        if thread.is_alive():
            raise TimeoutError(f"Operation timed out after {timeout_sec}s")
        
        if exception:
            raise exception
        
        return result
    
    def _stage_image_check(self, image_path: str) -> ImageQuality:
        """Stage 0: 图片质量检测"""
        self._check_cancel()
        return self._estimate_image_quality(image_path)
    
    def _stage_fast_ocr(self, image_path: str) -> str:
        """Stage 1: 快速OCR（只检测是否有文字）"""
        self._check_cancel()
        return self._run_fast_ocr(image_path)
    
    def _stage_math_region_detect(self, image_path: str) -> bool:
        """Stage 2: 数学区域检测"""
        self._check_cancel()
        has_math = self._detect_math_regions(image_path)
        if not has_math:
            # 如果没有检测到数学结构，可以提前返回普通OCR结果
            pass
        return has_math
    
    def _stage_math_ocr(self, image_path: str) -> Dict:
        """Stage 3: 数学公式识别"""
        self._check_cancel()
        return self._run_math_ocr(image_path)
    
    def _stage_latex_repair(self, image_path: str) -> Dict:
        """Stage 4: LaTeX修复（最多重试2次）"""
        self._check_cancel()
        return self._repair_latex(image_path, max_retries=2)
    
    def _stage_sympy_verify(self, image_path: str) -> Dict:
        """Stage 5: SymPy验证"""
        self._check_cancel()
        return self._verify_with_sympy(image_path)
    
    # ──────────────────────────────────────────────────────────────
    # 以下方法需要在子类中实现或通过依赖注入提供
    # ──────────────────────────────────────────────────────────────
    
    def _estimate_image_quality(self, image_path: str) -> ImageQuality:
        """估算图片质量（子类实现）"""
        # 默认实现：返回可接受的质量
        return ImageQuality(blur_score=80, contrast_score=75, tilt_score=90, shadow_score=85)
    
    def _run_fast_ocr(self, image_path: str) -> str:
        """快速OCR（子类实现）"""
        return ""
    
    def _detect_math_regions(self, image_path: str) -> bool:
        """检测数学区域（子类实现）"""
        return True
    
    def _run_math_ocr(self, image_path: str) -> Dict:
        """数学OCR（子类实现）"""
        return {"latex": "", "confidence": 0.0}
    
    def _repair_latex(self, image_path: str, max_retries: int = 2) -> Dict:
        """修复LaTeX（子类实现）"""
        return {}
    
    def _verify_with_sympy(self, image_path: str) -> Dict:
        """SymPy验证（子类实现）"""
        return {}
