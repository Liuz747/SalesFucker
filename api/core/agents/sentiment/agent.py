"""
Sentiment Analysis Agent - 简化协调版

专注于协调各个专业组件，提供清晰的情感分析服务。
Agent 本身只负责流程控制和状态管理，具体业务逻辑委托给专门组件。

核心职责:
- 组件协调和流程控制
- 状态管理和错误处理
- 组件生命周期管理
- 对外接口统一
"""

from typing import Dict, Any
from langfuse import observe

from ..base import BaseAgent
from .multimodal_input_processor import MultimodalInputProcessor
from .sentiment_analyzer import SentimentAnalyzer
from .sales_prompt_generator import SalesPromptGenerator
from utils import get_current_datetime
from config import mas_config


class SentimentAnalysisAgent(BaseAgent):
    """
    情感分析智能体 - 简化协调版

    作为多模态情感分析的主入口，协调：
    - 多模态输入处理
    - 情感分析
    - 销售提示词生成

    设计原则：
    - 单一职责：只负责协调，不处理具体业务逻辑
    - 依赖注入：组件可替换，便于测试
    - 错误隔离：组件失败不影响整体流程
    - 状态清晰：明确的状态管理和更新
    """

    def __init__(self):
        super().__init__()
        self.llm_provider = mas_config.DEFAULT_LLM_PROVIDER
        self.llm_model = "openai/gpt-5-chat"

        # 初始化核心组件
        self.input_processor = MultimodalInputProcessor(
            tenant_id=getattr(self, 'tenant_id', None),
            config={
                "openai_api_key": getattr(self, '_get_openai_api_key', lambda: None)()
            }
        )

        self.sentiment_analyzer = SentimentAnalyzer(
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            invoke_llm_fn=self.invoke_llm
        )

        self.prompt_generator = SalesPromptGenerator()

        self.logger.info(f"情感分析智能体初始化完成: {self.agent_id}")

    @observe(name="sentiment-analysis", as_type="generation")
    async def process_conversation(self, state: dict) -> dict:
        """
        处理对话状态中的情感分析

        工作流程：
        1. 多模态输入处理
        2. 情感分析
        3. 销售提示词生成
        4. 状态更新

        参数:
            state: 当前对话状态，包含 customer_input

        返回:
            dict: 更新后的对话状态
        """
        start_time = get_current_datetime()

        try:
            customer_input = state.get("customer_input", "")
            self.logger.info(f"开始情感分析处理: 输入类型={type(customer_input)}")

            # 步骤1: 处理多模态输入
            processed_text, multimodal_context = await self._process_input(customer_input)

            # 步骤2: 执行情感分析
            sentiment_result = await self._analyze_sentiment(processed_text, multimodal_context)

            # 步骤3: 生成销售提示词
            sales_prompt = await self._generate_prompt(sentiment_result, multimodal_context)

            # 步骤4: 更新对话状态
            updated_state = self._update_state(state, processed_text, sentiment_result, sales_prompt, multimodal_context)

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"情感分析完成: 耗时{processing_time:.2f}s, 情感={sentiment_result.get('sentiment')}")

            return updated_state

        except Exception as e:
            self.logger.error(f"情感分析处理失败: {e}", exc_info=True)
            return self._create_error_state(state, str(e))

    async def _process_input(self, customer_input) -> tuple[str, dict]:
        """处理多模态输入"""
        try:
            return await self.input_processor.process_input(customer_input)
        except Exception as e:
            self.logger.error(f"输入处理失败: {e}")
            # 降级处理：将输入转为字符串
            return str(customer_input) if customer_input else "", {"type": "fallback", "error": str(e)}

    async def _analyze_sentiment(self, text: str, context: dict) -> dict:
        """分析情感"""
        try:
            return await self.sentiment_analyzer.analyze_sentiment(text, context)
        except Exception as e:
            self.logger.error(f"情感分析失败: {e}")
            # 降级结果
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "urgency": "medium",
                "confidence": 0.0,
                "error": str(e)
            }

    async def _generate_prompt(self, sentiment_result: dict, context: dict) -> str:
        """生成销售提示词"""
        try:
            return self.prompt_generator.generate_prompt(sentiment_result, context)
        except Exception as e:
            self.logger.error(f"提示词生成失败: {e}")
            # 降级提示词
            return "您好！我是您的美妆顾问，很高兴为您服务。"

    def _update_state(self, state: dict, processed_text: str, sentiment_result: dict, sales_prompt: str, multimodal_context: dict) -> dict:
        """更新对话状态 - 专门为sales节点提供processed_text和sales_prompt"""
        # 更新情感分析结果（保持向后兼容）
        state["sentiment_analysis"] = {
            **sentiment_result,
            "processed_input": processed_text,
            "multimodal_context": multimodal_context,
            "sales_prompt": sales_prompt,
            "agent_id": self.agent_id,
            "processing_timestamp": get_current_datetime().isoformat()
        }

        # 新增：专门为sales节点提供的两个独立字段
        state["processed_text"] = processed_text  # 多模态消息转换的纯文字
        state["sales_prompt"] = sales_prompt      # 情感分析后匹配的提示词

        # 更新活跃智能体列表
        state.setdefault("active_agents", []).append(self.agent_id)

        self.logger.info(f"sentiment节点输出 -> processed_text长度: {len(processed_text)}, sales_prompt长度: {len(sales_prompt)}")

        return state

    def _create_error_state(self, state: dict, error_message: str) -> dict:
        """创建错误状态"""
        fallback_text = str(state.get("customer_input", ""))
        fallback_prompt = "您好！我是您的美妆顾问，系统暂时遇到问题，但仍然很乐意为您服务。"

        state["sentiment_analysis"] = {
            "sentiment": "neutral",
            "score": 0.0,
            "urgency": "medium",
            "confidence": 0.0,
            "processed_input": fallback_text,
            "multimodal_context": {"type": "error"},
            "sales_prompt": fallback_prompt,
            "agent_id": self.agent_id,
            "error": error_message,
            "fallback": True
        }

        # 为sales节点提供的两个独立字段
        state["processed_text"] = fallback_text
        state["sales_prompt"] = fallback_prompt

        state.setdefault("active_agents", []).append(self.agent_id)
        return state

    def get_component_status(self) -> dict:
        """获取组件状态信息"""
        try:
            return {
                "input_processor": {
                    "supported_modalities": self.input_processor.get_supported_modalities(),
                    "status": "active"
                },
                "sentiment_analyzer": self.sentiment_analyzer.get_analyzer_info(),
                "prompt_generator": self.prompt_generator.get_generator_info(),
                "agent_id": self.agent_id,
                "llm_provider": self.llm_provider,
                "llm_model": self.llm_model
            }
        except Exception as e:
            return {
                "error": str(e),
                "agent_id": self.agent_id,
                "status": "error"
            }

    def health_check(self) -> dict:
        """健康检查"""
        try:
            # 简单的健康检查
            test_input = "你好"
            test_text, test_context = self.input_processor.process_input(test_input)
            test_sentiment = self.sentiment_analyzer.analyze_sentiment(test_text, test_context)
            test_prompt = self.prompt_generator.generate_prompt(test_sentiment, test_context)

            return {
                "status": "healthy",
                "components": {
                    "input_processor": "ok",
                    "sentiment_analyzer": "ok",
                    "prompt_generator": "ok"
                },
                "test_results": {
                    "processed_text_length": len(test_text),
                    "sentiment_detected": test_sentiment.get("sentiment"),
                    "prompt_generated": len(test_prompt) > 10
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    # ================== 配置管理方法 ==================

    def update_config(self, config: dict):
        """更新配置"""
        try:
            if "openai_api_key" in config:
                self.input_processor.update_config({"openai_api_key": config["openai_api_key"]})

            if "llm_provider" in config:
                self.llm_provider = config["llm_provider"]

            if "llm_model" in config:
                self.llm_model = config["llm_model"]

            self.logger.info(f"配置已更新: {list(config.keys())}")
        except Exception as e:
            self.logger.error(f"配置更新失败: {e}")

<<<<<<< HEAD
        return " | ".join(context_parts) if context_parts else "Initial interaction"
=======
    def _get_openai_api_key(self):
        """获取OpenAI API密钥（示例方法）"""
        # 实际实现中应该从安全配置中获取
        return None
>>>>>>> 21ddef5 (chore: sentiment and multimodal reply)
