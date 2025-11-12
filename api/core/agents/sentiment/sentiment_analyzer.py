"""
情感分析器

专门负责分析文本情感状态，可以结合多模态信息进行综合分析。
使用LLM进行情感识别，支持情感分类、强度评分和紧急度判断。

核心功能:
- 文本情感分析
- 多模态情感融合
- 情感强度量化
- 紧急度评估
- 置信度计算
"""

from typing import Dict, Any, List, Tuple, Union
from abc import ABC, abstractmethod
from uuid import uuid4

from libs.types import Message
from utils import LoggerMixin
from infra.runtimes.entities import CompletionsRequest


class SentimentAnalysisStrategy(ABC):
    """情感分析策略基类"""

    @abstractmethod
    async def analyze(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行情感分析"""
        pass


class LLMSentimentAnalyzer(SentimentAnalysisStrategy):
    """基于LLM的情感分析器"""

    def __init__(self, llm_provider: str, llm_model: str, invoke_llm_fn):
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.invoke_llm = invoke_llm_fn

    async def analyze(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用LLM分析情感"""
        if not text or len(text.strip()) < 2:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "urgency": "medium",
                "confidence": 0.0,
                "tokens_used": 0,
                "total_tokens": 0
            }

        try:
            prompt = self._build_analysis_prompt(text, context or {})

            messages = [
                Message(role="user", content=prompt)
            ]
            request = CompletionsRequest(
                id=uuid4(),
                provider=self.llm_provider,
                model=self.llm_model,
                temperature=0.1,
                messages=messages
            )

            llm_response = await self.invoke_llm(request)
            raw_response = (
                llm_response.content
                if isinstance(llm_response.content, str)
                else str(llm_response.content)
            )

            # 提取token信息
            tokens_used = 0
            total_tokens = 0
            if llm_response and hasattr(llm_response, 'usage') and isinstance(llm_response.usage, dict):
                input_tokens = llm_response.usage.get('input_tokens', 0)
                output_tokens = llm_response.usage.get('output_tokens', 0)
                total_tokens = input_tokens + output_tokens
                tokens_used = total_tokens

            # 解析并验证结果
            result = self._parse_llm_response(raw_response)
            validated_result = self._validate_and_normalize(result)

            # 添加token信息
            validated_result["tokens_used"] = tokens_used
            validated_result["total_tokens"] = total_tokens

            return validated_result

        except Exception as e:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "urgency": "medium",
                "confidence": 0.0,
                "tokens_used": 0,
                "total_tokens": 0,
                "error": str(e)
            }

    def _build_analysis_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """构建分析提示词"""
        context_info = self._extract_context_info(context)

        prompt = f"""请分析以下客户输入的情感状态：

客户输入：{text}

{context_info}

请返回JSON格式的分析结果：
{{
    "sentiment": "positive|negative|neutral",
    "score": 0.0-1.0,
    "urgency": "high|medium|low",
    "confidence": 0.0-1.0,
    "emotional_indicators": {{
        "enthusiasm": 0.0-1.0,
        "concern": 0.0-1.0,
        "satisfaction": 0.0-1.0
    }}
}}

判断标准：
- sentiment: 整体情感倾向（积极/消极/中性）
- score: 情感强度（0-1，越接近1情感越强烈）
- urgency: 紧急程度（高/中/低）
- confidence: 分析置信度（0-1）
- emotional_indicators: 具体情感指标

请基于文本内容和上下文信息进行综合判断。"""

        return prompt

    def _extract_context_info(self, context: Dict[str, Any]) -> str:
        """从多模态上下文中提取有用信息"""
        context_parts = []

        # 语音上下文
        if context.get("modalities") and "audio" in context["modalities"]:
            context_parts.append("- 客户通过语音表达，注意语气和情感特征")

        # 图像上下文
        if context.get("modalities") and "image" in context["modalities"]:
            context_parts.append("- 包含图像内容，可能反映客户的视觉关注点")

        # 分析结果
        analysis = context.get("analysis", {})
        for key, value in analysis.items():
            if isinstance(value, dict) and value.get("text"):
                context_parts.append(f"- 从{key}中提取的内容：{value['text']}")

        return "\n上下文信息：\n" + "\n".join(context_parts) if context_parts else ""

    def _parse_llm_response(self, raw_response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            import json
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # 降级处理
            return self._fallback_parse(raw_response)

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """降级解析方法"""
        text_lower = text.lower()

        # 简单关键词分析
        if any(word in text_lower for word in ["好", "喜欢", "满意", "棒", "不错"]):
            sentiment = "positive"
            score = 0.7
        elif any(word in text_lower for word in ["不好", "讨厌", "失望", "糟糕", "问题"]):
            sentiment = "negative"
            score = 0.7
        else:
            sentiment = "neutral"
            score = 0.5

        if any(word in text_lower for word in ["急", "马上", "现在", "立即"]):
            urgency = "high"
        elif any(word in text_lower for word in ["尽快", "快点"]):
            urgency = "medium"
        else:
            urgency = "low"

        return {
            "sentiment": sentiment,
            "score": score,
            "urgency": urgency,
            "confidence": 0.3,  # 低置信度，因为是降级解析
            "emotional_indicators": {
                "enthusiasm": 0.5 if sentiment == "positive" else 0.2,
                "concern": 0.5 if sentiment == "negative" else 0.2,
                "satisfaction": 0.5 if sentiment == "positive" else 0.2
            }
        }

    def _validate_and_normalize(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """验证和标准化结果"""
        return {
            "sentiment": self._validate_sentiment(result.get("sentiment")),
            "score": self._validate_score(result.get("score")),
            "urgency": self._validate_urgency(result.get("urgency")),
            "confidence": self._validate_score(result.get("confidence", 0.5)),
            "emotional_indicators": self._validate_indicators(result.get("emotional_indicators", {}))
        }

    def _validate_sentiment(self, sentiment: str) -> str:
        """验证情感值"""
        valid_sentiments = ["positive", "negative", "neutral"]
        return sentiment if sentiment in valid_sentiments else "neutral"

    def _validate_score(self, score: Union[int, float, str]) -> float:
        """验证分数值"""
        try:
            score_float = float(score)
            return max(0.0, min(1.0, score_float))
        except (ValueError, TypeError):
            return 0.0

    def _validate_urgency(self, urgency: str) -> str:
        """验证紧急度"""
        valid_urgencies = ["high", "medium", "low"]
        return urgency if urgency in valid_urgencies else "medium"

    def _validate_indicators(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """验证情感指标"""
        validated = {}
        for key, value in indicators.items():
            validated[key] = self._validate_score(value)
        return validated


class SentimentAnalyzer(LoggerMixin):
    """
    情感分析器主类

    协调不同的分析策略，提供统一的情感分析接口。
    """

    def __init__(self, llm_provider: str, llm_model: str, invoke_llm_fn):
        super().__init__()
        self.llm_provider = llm_provider
        self.llm_model = llm_model

        # 初始化分析策略
        self.strategies: List[SentimentAnalysisStrategy] = [
            LLMSentimentAnalyzer(llm_provider, llm_model, invoke_llm_fn)
        ]

        self.logger.info(f"情感分析器初始化完成 - LLM: {llm_provider}/{llm_model}")

    async def analyze_sentiment(
        self,
        text: str,
        multimodal_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        分析文本情感

        参数:
            text: 要分析的文本
            multimodal_context: 多模态上下文信息

        返回:
            Dict[str, Any]: 情感分析结果
        """
        if not text:
            return self._empty_result()

        # 使用第一个可用的策略
        for strategy in self.strategies:
            try:
                result = await strategy.analyze(text, multimodal_context)
                result["analyzer"] = type(strategy).__name__
                result["llm_provider"] = self.llm_provider
                return result
            except Exception as e:
                self.logger.warning(f"策略{type(strategy).__name__}失败: {e}")
                continue

        # 所有策略都失败，返回默认结果
        return self._fallback_result(text)

    def _empty_result(self) -> Dict[str, Any]:
        """空文本结果"""
        return {
            "sentiment": "neutral",
            "score": 0.0,
            "urgency": "medium",
            "confidence": 0.0,
            "emotional_indicators": {
                "enthusiasm": 0.0,
                "concern": 0.0,
                "satisfaction": 0.0
            },
            "analyzer": "empty_input"
        }

    def _fallback_result(self, text: str) -> Dict[str, Any]:
        """降级结果"""
        return {
            "sentiment": "neutral",
            "score": 0.5,
            "urgency": "medium",
            "confidence": 0.1,
            "emotional_indicators": {
                "enthusiasm": 0.5,
                "concern": 0.5,
                "satisfaction": 0.5
            },
            "analyzer": "fallback",
            "error": "All strategies failed"
        }

    def add_strategy(self, strategy: SentimentAnalysisStrategy):
        """添加新的分析策略"""
        self.strategies.append(strategy)
        self.logger.info(f"添加新策略: {type(strategy).__name__}")

    def get_analyzer_info(self) -> Dict[str, Any]:
        """获取分析器信息"""
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "available_strategies": [type(s).__name__ for s in self.strategies],
            "total_strategies": len(self.strategies)
        }