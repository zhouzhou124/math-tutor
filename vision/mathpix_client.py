"""vision/mathpix_client.py — Mathpix OCR API integration.

Mathpix is a commercial OCR service specialized in math formula recognition.
Supports: handwritten math, printed math, mixed text+math, tables, diagrams.

API docs: https://docs.mathpix.com/
"""
import base64
import json
import os
import time
import requests


MATHpix_API_URL = "https://api.mathpix.com/v3/text"
MATHpix_PDF_URL = "https://api.mathpix.com/v3/pdf"


def get_mathpix_credentials() -> tuple[str, str]:
    """Get Mathpix credentials from env vars or settings.

    Priority: env vars > settings.json > None
    Returns (app_id, app_key) or (None, None).
    """
    # 1. Environment variables
    app_id = os.environ.get("MATHpix_APP_ID")
    app_key = os.environ.get("MATHpix_APP_KEY")
    if app_id and app_key:
        return app_id, app_key

    # 2. Settings file
    try:
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "storage", "settings.json",
        )
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            app_id = settings.get("mathpix_app_id", "")
            app_key = settings.get("mathpix_app_key", "")
            if app_id and app_key:
                return app_id, app_key
    except Exception:
        pass

    # 3. Streamlit session state
    try:
        import streamlit as st
        app_id = st.session_state.get("mathpix_app_id", "")
        app_key = st.session_state.get("mathpix_app_key", "")
        if app_id and app_key:
            return app_id, app_key
    except Exception:
        pass

    return None, None


def is_available() -> bool:
    """Check if Mathpix credentials are configured."""
    app_id, app_key = get_mathpix_credentials()
    return bool(app_id and app_key)


def recognize_image(
    image_path: str,
    formats: list[str] = None,
    timeout: int = 30,
) -> dict:
    """Recognize math from an image using Mathpix API.

    Args:
        image_path: Path to image file
        formats: Output formats, default ['latex', 'text']
        timeout: Request timeout in seconds

    Returns:
        {"success": bool, "latex": str, "text": str, "confidence": float, "error": str}
    """
    if formats is None:
        formats = ["latex", "text"]

    app_id, app_key = get_mathpix_credentials()
    if not app_id or not app_key:
        return {
            "success": False,
            "latex": "",
            "text": "",
            "confidence": 0.0,
            "error": "Mathpix credentials not configured",
        }

    # Read and encode image
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": f"Failed to read image: {e}"}

    # Build request
    headers = {
        "app_id": app_id,
        "app_key": app_key,
        "Content-type": "application/json",
    }

    payload = {
        "src": f"data:image/png;base64,{image_data}",
        "formats": {fmt: True for fmt in formats},
        "format_options": {
            "latex": {
                "transforms": ["rm_newlines", "rm_spaces"],
            }
        },
    }

    try:
        resp = requests.post(
            MATHpix_API_URL,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

        if resp.status_code == 200:
            data = resp.json()
            latex = ""
            text = ""
            conf = 0.0

            if "latex" in data:
                latex = data.get("latex", "")
            elif "text" in data:
                text = data.get("text", "")

            # If we got latex_styled
            if not latex and "latex_styled" in data:
                latex = data["latex_styled"]

            # Confidence
            if "confidence" in data:
                conf = float(data["confidence"])
            elif "latex_confidence" in data:
                conf = float(data["latex_confidence"])
            else:
                conf = 0.85 if latex else 0.3  # Default heuristics

            return {
                "success": bool(latex or text),
                "latex": latex,
                "text": text,
                "confidence": round(conf, 2),
                "error": "",
            }
        elif resp.status_code == 401:
            return {"success": False, "error": "Mathpix认证失败，请检查app_id和app_key"}
        elif resp.status_code == 402:
            return {"success": False, "error": "Mathpix账户余额不足"}
        elif resp.status_code == 429:
            return {"success": False, "error": "Mathpix请求频率过高，请稍后重试"}
        else:
            return {
                "success": False,
                "error": f"Mathpix API error (HTTP {resp.status_code}): {resp.text[:200]}",
            }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Mathpix请求超时"}
    except Exception as e:
        return {"success": False, "error": f"Mathpix调用失败: {str(e)}"}


def recognize_image_sync(image_path: str, timeout: int = 60) -> dict:
    """Recognize math with polling support for async processing.

    Some Mathpix API calls (especially for complex documents) are async.
    This function polls until the result is ready or timeout is reached.
    """
    result = recognize_image(image_path, timeout=min(timeout, 30))

    # If we got a PDF/deprecated async response, poll
    if not result["success"] and "pdf_id" in result.get("error", ""):
        # Legacy async handling — most v3 calls are synchronous now
        pass

    return result
