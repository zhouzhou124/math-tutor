"""OCR Progress Component — OCR进度显示组件

显示数学视觉识别的分步进度，包括：
  - 当前阶段
  - 进度条
  - 预计剩余时间
  - 阶段描述

阶段定义：
  0%   - 初始化
  10%  - 图片质量检测
  25%  - 识别题目
  50%  - 识别作答
  75%  - 优化识别结果
  100% - 完成
"""

import streamlit as st
import time


def show_ocr_progress():
    """显示OCR进度区域（需要配合进度回调使用）"""
    # 初始化进度状态
    if "ocr_progress" not in st.session_state:
        st.session_state.ocr_progress = {
            "stage": "init",
            "message": "准备识别...",
            "progress": 0,
            "start_time": time.time(),
        }
    
    progress = st.session_state.ocr_progress
    
    # 计算已耗时和预计剩余时间
    elapsed = time.time() - progress["start_time"]
    if progress["progress"] > 0:
        estimated_total = elapsed / (progress["progress"] / 100)
        remaining = max(0, estimated_total - elapsed)
    else:
        remaining = 10  # 默认预计10秒
    
    # 进度条
    st.progress(progress["progress"], text=f"{progress['progress']}%")
    
    # 阶段信息
    stage_info = get_stage_info(progress["stage"], progress["progress"])
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{stage_info['icon']} {stage_info['name']}**")
        st.markdown(f"<small>{progress['message']}</small>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<small>⏱️ 已耗时: {int(elapsed)}s</small>", unsafe_allow_html=True)
        st.markdown(f"<small>⏳ 预计剩余: {int(remaining)}s</small>", unsafe_allow_html=True)
    
    # 阶段指示器
    show_stage_indicator(progress["progress"])


def get_stage_info(stage: str, progress: int) -> dict:
    """获取阶段信息"""
    stages = {
        "init": {"name": "初始化", "icon": "🔧"},
        "quality_check": {"name": "图片质量检测", "icon": "📸"},
        "fast_ocr": {"name": "快速OCR", "icon": "📝"},
        "question": {"name": "识别题目", "icon": "📋"},
        "answer": {"name": "识别作答", "icon": "✍️"},
        "math_region": {"name": "数学区域检测", "icon": "🔍"},
        "math_ocr": {"name": "数学公式识别", "icon": "∑"},
        "cleanup": {"name": "优化识别结果", "icon": "✨"},
        "done": {"name": "识别完成", "icon": "✅"},
    }
    return stages.get(stage, {"name": "处理中", "icon": "⚙️"})


def show_stage_indicator(progress: int):
    """显示阶段指示器"""
    stages = [
        (0, "初始化"),
        (10, "质量检测"),
        (25, "识别题目"),
        (50, "识别作答"),
        (75, "优化"),
        (100, "完成"),
    ]
    
    st.markdown("<div style='display: flex; justify-content: space-between; font-size: 11px; color: #6b7280;'>", unsafe_allow_html=True)
    for pct, name in stages:
        color = "#22c55e" if progress >= pct else "#d1d5db"
        st.markdown(f"<span style='color: {color};'>{name}</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def update_ocr_progress(stage: str, message: str = "", progress: int = 0):
    """更新OCR进度"""
    if "ocr_progress" not in st.session_state:
        st.session_state.ocr_progress = {}
    
    st.session_state.ocr_progress.update({
        "stage": stage,
        "message": message,
        "progress": progress,
    })


def reset_ocr_progress():
    """重置OCR进度"""
    st.session_state.ocr_progress = {
        "stage": "init",
        "message": "准备识别...",
        "progress": 0,
        "start_time": time.time(),
    }


def progress_callback(progress_info: dict):
    """进度回调函数（供OCR Agent调用）"""
    update_ocr_progress(
        stage=progress_info.get("stage", "init"),
        message=progress_info.get("message", ""),
        progress=progress_info.get("progress", 0),
    )
