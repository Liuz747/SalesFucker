"""
Sentiment Analysis Agent

提供情感分析和多模态处理的完整解决方案。
采用模块化设计，每个组件职责单一，便于测试和维护。

核心组件:
- SentimentAnalysisAgent: 主协调器
- MultimodalInputProcessor: 多模态输入处理
- SentimentAnalyzer: 情感分析引擎
- SalesPromptGenerator: 销售提示词生成

架构特点:
- 单一职责原则
- 组件可替换性
- 错误隔离机制
- 易于扩展测试
"""

from .agent import SentimentAnalysisAgent
from .multimodal_input_processor import MultimodalInputProcessor
from .sentiment_analyzer import SentimentAnalyzer
from .sales_prompt_generator import SalesPromptGenerator

__all__ = [
    # 主要智能体
    "SentimentAnalysisAgent",

    # 核心组件
    "MultimodalInputProcessor",
    "SentimentAnalyzer",
    "SalesPromptGenerator"
]