"""Image Quality Assessment — 图片质量评估模块

核心功能：
  1. 模糊度检测（拉普拉斯方差法）
  2. 对比度检测（直方图分析）
  3. 倾斜检测（霍夫变换）
  4. 阴影检测（亮度分布分析）

评分标准（0-100，越高越好）：
  - blur_score:  >80 清晰, 50-80 中等, <50 模糊
  - contrast_score: >70 良好, 40-70 中等, <40 差
  - tilt_score: >85 水平, 70-85 轻微倾斜, <70 严重倾斜
  - shadow_score: >75 正常, 50-75 轻微阴影, <50 严重阴影

综合评分 >= 50 为可接受
"""

import cv2
import numpy as np
from vision.ocr_pipeline import ImageQuality


def estimate_blur_score(image: np.ndarray) -> int:
    """
    估算图片模糊度评分
    
    使用拉普拉斯算子的方差来衡量图像清晰度：
    - 方差越大，图像越清晰
    - 方差越小，图像越模糊
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 计算拉普拉斯方差
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()
    
    # 映射到0-100评分
    # 经验阈值：方差>100为清晰，<20为模糊
    if variance >= 100:
        return 100
    elif variance >= 50:
        return int(50 + (variance - 50) * 1.0)
    elif variance >= 20:
        return int(20 + (variance - 20) * (30 / 30))
    else:
        return int(variance * 2.5)


def estimate_contrast_score(image: np.ndarray) -> int:
    """
    估算图片对比度评分
    
    使用直方图统计来衡量对比度：
    - 直方图分布越分散，对比度越高
    - 使用标准差来量化
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 计算直方图
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten()
    
    # 计算均值和标准差
    mean_intensity = np.sum(np.arange(256) * hist) / np.sum(hist)
    variance = np.sum(hist * (np.arange(256) - mean_intensity) ** 2) / np.sum(hist)
    std_dev = np.sqrt(variance)
    
    # 映射到0-100评分
    # 标准差>50为高对比度，<20为低对比度
    if std_dev >= 50:
        return 100
    elif std_dev >= 30:
        return int(40 + (std_dev - 30) * 3.0)
    elif std_dev >= 20:
        return int(20 + (std_dev - 20) * 2.0)
    else:
        return int(std_dev * 2)


def estimate_tilt_score(image: np.ndarray) -> int:
    """
    估算图片倾斜度评分
    
    使用霍夫变换检测线条角度：
    - 检测到的主要线条角度接近0度为水平
    - 角度偏离越大，倾斜越严重
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 边缘检测
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # 霍夫变换检测线条
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)
    
    if lines is None or len(lines) == 0:
        return 85  # 无法检测，假设基本水平
    
    # 统计线条角度
    angles = []
    for line in lines:
        rho, theta = line[0]
        angle_deg = np.degrees(theta)
        # 转换到-90到90度范围
        if angle_deg > 90:
            angle_deg -= 180
        angles.append(abs(angle_deg))
    
    # 计算平均角度
    avg_angle = np.mean(angles)
    
    # 映射到0-100评分
    # 角度<2度为水平，>15度为严重倾斜
    if avg_angle < 2:
        return 100
    elif avg_angle < 5:
        return int(85 + (5 - avg_angle) * 5)
    elif avg_angle < 10:
        return int(60 + (10 - avg_angle) * 5)
    elif avg_angle < 15:
        return int(40 + (15 - avg_angle) * 4)
    else:
        return max(0, int(100 - avg_angle * 4))


def estimate_shadow_score(image: np.ndarray) -> int:
    """
    估算图片阴影评分
    
    分析亮度分布检测阴影：
    - 亮度分布均匀为正常
    - 存在明显暗区为有阴影
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 计算全局亮度
    global_mean = np.mean(gray)
    
    # 分块计算亮度差异
    h, w = gray.shape
    block_size = 3
    block_h, block_w = h // block_size, w // block_size
    
    block_means = []
    for i in range(block_size):
        for j in range(block_size):
            block = gray[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w]
            block_means.append(np.mean(block))
    
    # 计算块间亮度差异
    max_diff = max(block_means) - min(block_means)
    mean_diff = np.std(block_means)
    
    # 综合判断阴影程度
    # 差异越小越好
    if max_diff < 20 and mean_diff < 10:
        return 100
    elif max_diff < 40 and mean_diff < 20:
        return int(75 + (40 - max_diff) * 0.625)
    elif max_diff < 60 and mean_diff < 30:
        return int(50 + (60 - max_diff) * 0.833)
    else:
        return max(0, int(100 - max_diff - mean_diff))


def estimate_image_quality(image_path: str) -> ImageQuality:
    """
    综合评估图片质量
    
    返回ImageQuality对象，包含各项评分
    """
    try:
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            return ImageQuality(blur_score=0, contrast_score=0, tilt_score=0, shadow_score=0)
        
        # 统一缩放到合理尺寸（避免过大图片影响性能）
        max_dim = 1024
        h, w = image.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            image = cv2.resize(image, None, fx=scale, fy=scale)
        
        # 计算各项评分
        blur_score = estimate_blur_score(image)
        contrast_score = estimate_contrast_score(image)
        tilt_score = estimate_tilt_score(image)
        shadow_score = estimate_shadow_score(image)
        
        return ImageQuality(
            blur_score=blur_score,
            contrast_score=contrast_score,
            tilt_score=tilt_score,
            shadow_score=shadow_score
        )
    
    except Exception as e:
        return ImageQuality(blur_score=0, contrast_score=0, tilt_score=0, shadow_score=0)


def is_image_acceptable(image_path: str) -> bool:
    """
    判断图片是否可接受（综合评分 >= 50）
    """
    quality = estimate_image_quality(image_path)
    return quality.is_acceptable


def get_quality_warnings(image_path: str) -> list[str]:
    """
    获取图片质量警告信息
    """
    quality = estimate_image_quality(image_path)
    warnings = []
    
    if quality.blur_score < 50:
        warnings.append(f"图片模糊（评分: {quality.blur_score}/100），建议重新拍摄")
    if quality.contrast_score < 40:
        warnings.append(f"对比度低（评分: {quality.contrast_score}/100），建议调整光线")
    if quality.tilt_score < 70:
        warnings.append(f"图片倾斜（评分: {quality.tilt_score}/100），建议摆正拍摄")
    if quality.shadow_score < 50:
        warnings.append(f"阴影严重（评分: {quality.shadow_score}/100），建议改善照明")
    
    return warnings
