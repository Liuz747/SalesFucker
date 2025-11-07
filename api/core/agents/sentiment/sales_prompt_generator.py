"""
销售提示词生成器

专门负责基于情感分析结果和多模态信息生成个性化的销售提示词。
支持可扩展的提示词策略和多维度上下文融合。

核心功能:
- 情感驱动的提示词生成
- 多模态上下文融合
- 可配置的提示词策略
- 提示词模板管理
- 个性化增强
"""

from typing import Dict, Any, List, Tuple, Union
from abc import ABC, abstractmethod
from enum import Enum

from utils import LoggerMixin


class PromptStrategy(ABC):
    """提示词策略基类"""

    @abstractmethod
    def generate(self, sentiment_result: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """生成提示词"""
        pass


class SentimentBasedStrategy(PromptStrategy):
    """基于情感的基础策略"""

    def __init__(self):
        # 情感-紧急度到提示词的映射表
        self.prompt_matrix = {
            ("positive", "high"): {
                "base": "客户情绪积极且需求紧急，可以主动推荐产品并提供专业建议。",
                "enhancement": "强调产品效果和快速解决方案，体现高效服务。",
                "tone": "热情专业"
            },
            ("positive", "medium"): {
                "base": "客户情绪积极，可以详细沟通需求，提供个性化建议。",
                "enhancement": "营造专业顾问形象，深入了解客户需求。",
                "tone": "友好专业"
            },
            ("positive", "low"): {
                "base": "客户情绪轻松，可以友好交流，建立信任关系。",
                "enhancement": "逐步了解需求，建立长期客户关系。",
                "tone": "轻松友好"
            },
            ("negative", "high"): {
                "base": "客户情绪急躁且不满，需要先安抚情绪。",
                "enhancement": "耐心倾听问题，快速提供解决方案。",
                "tone": "耐心安抚"
            },
            ("negative", "medium"): {
                "base": "客户有负面情绪，需要理解问题所在。",
                "enhancement": "提供专业的解决方案和安慰，展现同理心。",
                "tone": "理解支持"
            },
            ("negative", "low"): {
                "base": "客户情绪低落，需要温和关怀。",
                "enhancement": "耐心了解需求，提供贴心的建议。",
                "tone": "温和关怀"
            },
            ("neutral", "high"): {
                "base": "客户需求明确但时间紧迫。",
                "enhancement": "快速响应，提供精准的产品推荐。",
                "tone": "高效直接"
            },
            ("neutral", "medium"): {
                "base": "客户态度中性，可以逐步引导。",
                "enhancement": "了解需求，提供专业的产品介绍。",
                "tone": "专业引导"
            },
            ("neutral", "low"): {
                "base": "客户处于观察阶段，需要主动引导。",
                "enhancement": "激发兴趣，建立专业形象。",
                "tone": "引导启发"
            }
        }

    def generate(self, sentiment_result: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """生成基础情感提示词"""
        sentiment = sentiment_result.get("sentiment", "neutral")
        urgency = sentiment_result.get("urgency", "medium")
        score = sentiment_result.get("score", 0.0)

        key = (sentiment, urgency)
        prompt_config = self.prompt_matrix.get(key, self._get_default_config())

        base_prompt = prompt_config["base"]
        enhancement = prompt_config["enhancement"]
        tone = prompt_config["tone"]

        # 根据情感强度调整
        intensity_modifier = self._get_intensity_modifier(score)

        return f"{base_prompt}{enhancement}{intensity_modifier}建议使用{tone}的沟通方式。"

    def _get_default_config(self) -> Dict[str, str]:
        """获取默认配置"""
        return {
            "base": "保持专业友好的态度，了解客户需求。",
            "enhancement": "提供适合的产品建议。",
            "tone": "专业友好"
        }

    def _get_intensity_modifier(self, score: float) -> str:
        """根据情感强度获取修饰语"""
        if score > 0.8:
            return "情感表达强烈，"
        elif score > 0.5:
            return "情感表达明显，"
        else:
            return "情感表达平缓，"


class MultimodalEnhancedStrategy(PromptStrategy):
    """多模态增强策略"""

    def __init__(self):
        self.base_strategy = SentimentBasedStrategy()

    def generate(self, sentiment_result: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """生成多模态增强的提示词"""
        base_prompt = self.base_strategy.generate(sentiment_result, context)

        if not context or context.get("type") != "multimodal":
            return base_prompt

        enhancements = self._extract_multimodal_enhancements(context)
        if enhancements:
            return f"{base_prompt} {enhancements}"

        return base_prompt

    def _extract_multimodal_enhancements(self, context: Dict[str, Any]) -> str:
        """提取多模态增强信息"""
        enhancements = []

        # 语音增强
        if "audio" in context.get("modalities", []):
            enhancements.append("注意客户语音中的语调和情感细节")

        # 图像增强
        if "image" in context.get("modalities", []):
            enhancements.append("结合视觉信息提供更精准的建议")

        # 分析结果增强
        analysis = context.get("analysis", {})
        for key, value in analysis.items():
            if isinstance(value, dict):
                text = value.get("text", "")
                if text and not text.startswith("["):
                    # 有实际的分析内容
                    if key.startswith("item_") and "image" in value.get("metadata", {}).get("type", ""):
                        enhancements.append("关注客户展示的视觉内容")
                    elif key.startswith("item_") and "voice" in value.get("metadata", {}).get("type", ""):
                        enhancements.append("重视客户口头表达的细节")

        return " ".join(enhancements)


class PersonalizedStrategy(PromptStrategy):
    """个性化策略"""

    def __init__(self):
        self.multimodal_strategy = MultimodalEnhancedStrategy()

    def generate(self, sentiment_result: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """生成个性化提示词"""
        base_prompt = self.multimodal_strategy.generate(sentiment_result, context)

        # 添加个性化维度
        personalization = self._add_personalization(sentiment_result, context)

        return f"{base_prompt} {personalization}"

    def _add_personalization(self, sentiment_result: Dict[str, Any], context: Dict[str, Any]) -> str:
        """添加个性化维度"""
        personalizations = []

        # 基于情感指标的个性化
        indicators = sentiment_result.get("emotional_indicators", {})
        if indicators.get("enthusiasm", 0) > 0.7:
            personalizations.append("可以推荐更多新产品或热门产品")
        elif indicators.get("concern", 0) > 0.7:
            personalizations.append("重点推荐温和、安全的产品")
        elif indicators.get("satisfaction", 0) > 0.7:
            personalizations.append("可以推荐配套产品或升级方案")

        # 基于置信度的个性化
        confidence = sentiment_result.get("confidence", 0.0)
        if confidence < 0.5:
            personalizations.append("建议多询问确认需求")

        return " ".join(personalizations)


class SalesPromptGenerator(LoggerMixin):
    """
    销售提示词生成器主类

    协调不同的生成策略，提供统一的提示词生成接口。
    """

    def __init__(self):
        super().__init__()
        self.strategies: List[PromptStrategy] = [
            PersonalizedStrategy(),  # 最完整的策略
            MultimodalEnhancedStrategy(),  # 多模态增强策略
            SentimentBasedStrategy()  # 基础策略
        ]

        self.logger.info("销售提示词生成器初始化完成")

    def generate_prompt(
        self,
        sentiment_result: Dict[str, Any],
        multimodal_context: Dict[str, Any] = None
    ) -> str:
        """
        生成销售提示词

        参数:
            sentiment_result: 情感分析结果
            multimodal_context: 多模态上下文信息

        返回:
            str: 生成的销售提示词
        """
        if not sentiment_result:
            return self._get_default_prompt()

        # 按优先级尝试不同策略
        for strategy in self.strategies:
            try:
                prompt = strategy.generate(sentiment_result, multimodal_context)
                if prompt and len(prompt.strip()) > 10:  # 确保提示词有意义
                    prompt_metadata = {
                        "strategy": type(strategy).__name__,
                        "sentiment": sentiment_result.get("sentiment"),
                        "urgency": sentiment_result.get("urgency"),
                        "has_multimodal": bool(multimodal_context and multimodal_context.get("type") == "multimodal")
                    }
                    return f"{prompt} [生成策略: {type(strategy).__name__}]"
            except Exception as e:
                self.logger.warning(f"策略{type(strategy).__name__}失败: {e}")
                continue

        # 所有策略都失败，返回降级提示词
        return self._get_fallback_prompt(sentiment_result)

    def _get_default_prompt(self) -> str:
        """获取默认提示词"""
        return "您好！我是您的美妆顾问，很高兴为您服务。请告诉我您的需求。"

    def _get_fallback_prompt(self, sentiment_result: Dict[str, Any]) -> str:
        """获取降级提示词"""
        sentiment = sentiment_result.get("sentiment", "neutral")
        urgency = sentiment_result.get("urgency", "medium")

        fallback_prompts = {
            ("positive", "high"): "很高兴为您服务！看起来您有紧急需求，让我立即为您推荐合适的产品。",
            ("positive", "medium"): "欢迎！我很乐意为您提供专业的美妆建议。",
            ("positive", "low"): "您好！很高兴见到您，让我慢慢了解您的需求。",
            ("negative", "high"): "我理解您的急切心情，让我立即帮助您解决问题。",
            ("negative", "medium"): "我理解您的顾虑，让我为您提供专业的解决方案。",
            ("negative", "low"): "我在这里倾听您的需求，会为您提供贴心的建议。",
            ("neutral", "high"): "我明白您需要快速帮助，让我立即为您处理。",
            ("neutral", "medium"): "您好！我是您的专业美妆顾问，请告诉我您的需求。",
            ("neutral", "low"): "欢迎！让我慢慢了解您需要什么样的帮助。"
        }

        return fallback_prompts.get((sentiment, urgency), "您好！我是您的美妆顾问，很高兴为您服务。")

    def add_strategy(self, strategy: PromptStrategy):
        """添加新的生成策略"""
        self.strategies.insert(0, strategy)  # 新策略优先级更高
        self.logger.info(f"添加新策略: {type(strategy).__name__}")

    def get_prompt_examples(self) -> Dict[str, List[str]]:
        """获取提示词示例（用于测试和文档）"""
        return {
            "positive_high": [
                "客户情绪积极且需求紧急，可以主动推荐产品并提供专业建议。强调产品效果和快速解决方案，体现高效服务。建议使用热情专业的沟通方式。"
            ],
            "negative_low": [
                "客户情绪低落，需要温和关怀。耐心了解需求，提供贴心的建议。建议使用温和关怀的沟通方式。"
            ],
            "neutral_medium": [
                "客户态度中性，可以逐步引导。了解需求，提供专业的产品介绍。建议使用专业引导的沟通方式。"
            ]
        }

    def get_generator_info(self) -> Dict[str, Any]:
        """获取生成器信息"""
        return {
            "total_strategies": len(self.strategies),
            "available_strategies": [type(s).__name__ for s in self.strategies],
            "default_prompt": self._get_default_prompt(),
            "capabilities": [
                "sentiment_based_generation",
                "multimodal_enhancement",
                "personalization",
                "fallback_handling"
            ]
        }