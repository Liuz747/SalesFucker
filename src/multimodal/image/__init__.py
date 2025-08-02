"""
图像分析模块

该包提供图像分析功能，支持皮肤分析和产品识别。
基于GPT-4V实现高质量的图像内容理解和分析。

核心功能:
- 皮肤状态分析和建议
- 化妆品产品识别
- 图像预处理和优化
- 多语言分析结果输出
"""

from .gpt4v_service import GPT4VService
from .image_processor import ImageProcessor
from .skin_analyzer import SkinAnalyzer
from .product_recognizer import ProductRecognizer

__all__ = [
    "GPT4VService",
    "ImageProcessor",
    "SkinAnalyzer", 
    "ProductRecognizer"
]