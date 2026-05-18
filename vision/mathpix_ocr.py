"""Mathpix OCR Integration — Mathpix API 集成模块

Mathpix 是目前最先进的数学公式识别服务，支持：
  - 印刷体数学公式
  - 手写数学公式  
  - 复杂数学结构（积分、极限、矩阵等）
  - LaTeX/MathML 输出

配置方式：
  1. 在 config.py 中设置 MATHPIX_APP_ID 和 MATHPIX_APP_KEY
  2. 或通过环境变量设置：MATHPIX_APP_ID, MATHPIX_APP_KEY

使用方式：
  from vision.mathpix_ocr import MathpixOCR
  ocr = MathpixOCR()
  result = ocr.recognize(image_path)
  if result.success:
      print(result.latex)
"""

import os
import requests
import base64
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class MathpixResult:
    """Mathpix识别结果"""
    success: bool = False
    latex: str = ""
    confidence: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


class MathpixOCR:
    """Mathpix OCR 客户端"""
    
    # API 端点
    API_URL = "https://api.mathpix.com/v3/text"
    
    def __init__(self, app_id: str = None, app_key: str = None):
        """
        初始化 Mathpix OCR 客户端
        
        Args:
            app_id: Mathpix App ID（可选，默认从配置或环境变量读取）
            app_key: Mathpix App Key（可选，默认从配置或环境变量读取）
        """
        self.app_id = app_id or self._get_config("MATHPIX_APP_ID")
        self.app_key = app_key or self._get_config("MATHPIX_APP_KEY")
        
    def _get_config(self, key: str) -> str:
        """从配置文件或环境变量获取值"""
        # 优先从环境变量获取
        env_value = os.environ.get(key, "")
        if env_value:
            return env_value
        
        # 尝试从 config.py 获取
        try:
            from config import MATHPIX_APP_ID, MATHPIX_APP_KEY
            if key == "MATHPIX_APP_ID":
                return MATHPIX_APP_ID
            elif key == "MATHPIX_APP_KEY":
                return MATHPIX_APP_KEY
        except ImportError:
            pass
        
        # 尝试从 CONFIG 字典获取
        try:
            from config import CONFIG
            if key in CONFIG:
                return CONFIG[key]
        except ImportError:
            pass
        
        return ""
    
    def is_configured(self) -> bool:
        """检查是否已配置 API 密钥"""
        return bool(self.app_id) and bool(self.app_key)
    
    def recognize(self, image_path: str, timeout: int = 10) -> MathpixResult:
        """
        识别图片中的数学公式
        
        Args:
            image_path: 图片路径
            timeout: 请求超时时间（秒）
            
        Returns:
            MathpixResult 对象
        """
        if not self.is_configured():
            return MathpixResult(
                success=False,
                error="Mathpix 未配置：请设置 MATHPIX_APP_ID 和 MATHPIX_APP_KEY"
            )
        
        if not os.path.exists(image_path):
            return MathpixResult(
                success=False,
                error=f"图片文件不存在: {image_path}"
            )
        
        try:
            # 读取并编码图片
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # 构建请求参数
            params = {
                "src": f"data:image/png;base64,{image_data}",
                "formats": ["latex_styled"],
                "math_inline_delimiters": ["$", "$"],
                "rm_spaces": True,
            }
            
            # 发送请求
            headers = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "Content-Type": "application/json",
            }
            
            response = requests.post(
                self.API_URL,
                json=params,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # 解析结果
            return self._parse_response(data)
            
        except requests.exceptions.Timeout:
            return MathpixResult(
                success=False,
                error="请求超时"
            )
        except requests.exceptions.RequestException as e:
            return MathpixResult(
                success=False,
                error=f"请求失败: {str(e)}"
            )
        except Exception as e:
            return MathpixResult(
                success=False,
                error=f"识别失败: {str(e)}"
            )
    
    def _parse_response(self, data: Dict[str, Any]) -> MathpixResult:
        """解析 Mathpix API 响应"""
        try:
            # 检查是否有错误
            if "error" in data:
                return MathpixResult(
                    success=False,
                    error=data["error"],
                    raw_response=data
                )
            
            # 提取 LaTeX 结果
            latex = ""
            if "latex_styled" in data:
                latex = data["latex_styled"]
            elif "latex" in data:
                latex = data["latex"]
            
            # 计算置信度
            confidence = 0.0
            if "confidence" in data:
                confidence = float(data["confidence"])
            
            return MathpixResult(
                success=True,
                latex=latex.strip(),
                confidence=confidence,
                raw_response=data
            )
        
        except Exception as e:
            return MathpixResult(
                success=False,
                error=f"解析响应失败: {str(e)}",
                raw_response=data
            )


# ──────────────────────────────────────────────────────────────
# 便捷函数
# ──────────────────────────────────────────────────────────────

def try_mathpix(image_path: str) -> Optional[str]:
    """
    尝试使用 Mathpix 识别图片，返回 LaTeX 字符串（失败返回 None）
    """
    try:
        ocr = MathpixOCR()
        if not ocr.is_configured():
            return None
        
        result = ocr.recognize(image_path)
        if result.success and result.latex:
            return result.latex
        return None
    except Exception:
        return None
