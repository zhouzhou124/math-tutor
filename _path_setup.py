"""
路径初始化 — 必须在所有 import 之前运行
Streamlit / PyCharm / 命令行 全兼容
"""
import sys
import os

# 方案1: 从 __file__ 推断项目根目录
try:
    _THIS_FILE = os.path.realpath(__file__)
    _ROOT = os.path.dirname(_THIS_FILE)
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
except NameError:
    pass

# 方案2: 从当前工作目录推断
_CWD = os.path.realpath(os.getcwd())
if _CWD not in sys.path:
    sys.path.insert(0, _CWD)

# 方案3: 硬编码兜底
_HARDCODED = r"E:\math_tutor"
if os.path.isdir(_HARDCODED) and _HARDCODED not in sys.path:
    sys.path.insert(0, _HARDCODED)
