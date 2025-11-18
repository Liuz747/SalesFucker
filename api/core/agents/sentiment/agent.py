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

        # 根据配置的provider使用相应的默认模型
        if self.llm_provider == "openrouter":
            self.llm_model = "openai/gpt-5-chat"  # 使用OpenRouter中可用的模型
        elif self.llm_provider == "zenmux":
            self.llm_model = "gpt-4o"
        elif self.llm_provider == "openai":
            self.llm_model = "gpt-4o-mini"
        elif self.llm_provider == "anthropic":
            self.llm_model = "claude-3-5-sonnet-20241022"
        elif self.llm_provider == "gemini":
            self.llm_model = "gemini-1.5-pro-002"
        else:
            self.llm_model = "gpt-4o-mini"  # 默认回退

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
            self.logger.info("=== Sentiment Agent 开始处理 ===")

            customer_input = state.get("customer_input", "")
            self.logger.info(f"开始情感分析处理: 输入长度={len(customer_input)}, 输入类型={type(customer_input)}")
            self.logger.debug(f"customer_input内容: {customer_input[:100]}..." if len(customer_input) > 100 else f"customer_input内容: {customer_input}")

            # 步骤1: 处理多模态输入
            processed_text, multimodal_context = await self._process_input(customer_input)
            self.logger.info(f"多模态输入处理完成 - processed_text长度: {len(processed_text)}, context类型: {multimodal_context.get('type')}")

            # 步骤2: 执行情感分析
            sentiment_result = await self._analyze_sentiment(processed_text, multimodal_context)
            self.logger.info(f"情感分析结果 - sentiment: {sentiment_result.get('sentiment')}, score: {sentiment_result.get('score')}, urgency: {sentiment_result.get('urgency')}")
            self.logger.info(f"情感分析token统计 - tokens_used: {sentiment_result.get('tokens_used', 0)}")

            # 步骤3: 生成销售提示词
            sales_prompt = await self._generate_prompt(sentiment_result, multimodal_context)
            self.logger.info(f"销售提示词生成完成 - 长度: {len(sales_prompt)}")
            self.logger.debug(f"sales_prompt内容: {sales_prompt[:150]}..." if len(sales_prompt) > 150 else f"sales_prompt内容: {sales_prompt}")

            # 步骤4: 更新对话状态
            updated_state = self._update_state(state, processed_text, sentiment_result, sales_prompt, multimodal_context)

            processing_time = (get_current_datetime() - start_time).total_seconds()
            self.logger.info(f"情感分析完成: 耗时{processing_time:.2f}s, 情感={sentiment_result.get('sentiment')}")
            self.logger.info("=== Sentiment Agent 处理完成 ===")

            return updated_state

        except Exception as e:
            self.logger.error(f"情感分析处理失败: {e}", exc_info=True)
            self.logger.error(f"失败时的输入: {state.get('customer_input', 'None')}")
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
        self.logger.info(f"调用情感分析器 - text长度: {len(text)}, context类型: {context.get('type', 'unknown')}")
        result = await self.sentiment_analyzer.analyze_sentiment(text, context)
        self.logger.info(f"情感分析器返回结果 - sentiment: {result.get('sentiment')}, tokens: {result.get('total_tokens', 0)}")
        return result

    async def _generate_prompt(self, sentiment_result: dict, context: dict) -> str:
        """生成销售提示词"""
        try:
            # 使用prompt_generator生成个性化提示词
            sales_prompt = self.prompt_generator.generate_prompt(sentiment_result, context)

            # 验证生成的提示词质量
            if not sales_prompt or len(sales_prompt.strip()) < 10:
                self.logger.warning("生成的sales_prompt过短，使用增强降级方案")
                return self._get_enhanced_fallback_prompt(sentiment_result)

            self.logger.info(f"成功生成sales_prompt，长度: {len(sales_prompt)}")
            return sales_prompt

        except Exception as e:
            self.logger.error(f"提示词生成失败: {e}")
            # 增强降级提示词
            return self._get_enhanced_fallback_prompt(sentiment_result)

    def _get_enhanced_fallback_prompt(self, sentiment_result: dict) -> str:
        """获取增强的降级提示词"""
        sentiment = sentiment_result.get('sentiment', 'neutral')
        urgency = sentiment_result.get('urgency', 'medium')

        # 基于情感状态生成更有针对性的降级提示词
        if sentiment == 'positive':
            if urgency == 'high':
                return "客户情绪积极且需求紧急！可以主动推荐高端产品，强调卓越效果和独特价值。建议使用热情专业的方式进行深度推荐，体现高效服务。"
            else:
                return "客户情绪积极，可以推荐产品并详细介绍功效。建议使用友好专业的方式引导购买，建立信任关系。"
        elif sentiment == 'negative':
            if urgency == 'high':
                return "客户情绪急躁且不满，需要先安抚情绪！耐心倾听问题，快速提供解决方案。建议使用同理心强的方式化解负面情绪，优先处理客户关切。"
            else:
                return "客户有负面情绪，需要先理解问题所在。提供专业的解决方案和安慰，展现同理心。建议使用温和关怀的方式提供支持。"
        else:
            if urgency == 'high':
                return "客户需求明确但时间紧迫。快速响应，提供精准的产品推荐。建议使用高效直接的方式，满足客户的紧急需求。"
            else:
                return "客户情绪平稳，需要先了解需求再提供建议。建议使用专业耐心的方式建立信任，深入了解客户的真实需求。"

    def _update_state(self, state: dict, processed_text: str, sentiment_result: dict, sales_prompt: str, multimodal_context: dict) -> dict:
        """更新对话状态 - 统一状态管理模式"""
        # 提取token信息
        sentiment_tokens = {
            "tokens_used": sentiment_result.get("tokens_used", 0),
            "total_tokens": sentiment_result.get("total_tokens", 0)
        }

        # 修复：统一状态管理，移除重复存储
        # 1. 主要数据存储在根级别（LangGraph节点间传递）
        state["processed_text"] = processed_text
        state["sales_prompt"] = sales_prompt
        state["sentiment_analysis"] = {
            **sentiment_result,
            "processed_input": processed_text,
            "multimodal_context": multimodal_context,
            "agent_id": self.agent_id,
            **sentiment_tokens
        }

        # 2. 备份存储在values结构中（用于统计和调试）
        if state.get("values") is None:
            state["values"] = {}
        if state["values"].get("agent_responses") is None:
            state["values"]["agent_responses"] = {}

        agent_data = {
            "sentiment_analysis": sentiment_result,
            "sales_prompt": sales_prompt,
            "processed_input": processed_text,
            "timestamp": get_current_datetime(),
            **sentiment_tokens
        }

        state["values"]["agent_responses"][self.agent_id] = agent_data

        # 更新活跃智能体列表
        state.setdefault("active_agents", []).append(self.agent_id)

        self.logger.info(f"统一状态管理 - 根级别字段: processed_text({len(processed_text)}), sales_prompt({len(sales_prompt)}), sentiment_analysis")
        self.logger.info(f"状态传递完成 -> 下一个Agent可访问: state['sales_prompt'], state['sentiment_analysis']")

        return state

    def _create_error_state(self, state: dict, error_message: str) -> dict:
        """创建错误状态 - 统一状态管理模式"""
        fallback_text = str(state.get("customer_input", ""))
        fallback_prompt = "您好！我是您的美妆顾问，系统暂时遇到问题，但仍然很乐意为您服务。"

        # 统一状态管理：同时设置根级别和values备份
        state["processed_text"] = fallback_text
        state["sales_prompt"] = fallback_prompt
        state["sentiment_analysis"] = {
            "sentiment": "neutral",
            "score": 0.0,
            "urgency": "medium",
            "confidence": 0.0,
            "processed_input": fallback_text,
            "multimodal_context": {"type": "error"},
            "agent_id": self.agent_id,
            "error": error_message,
            "fallback": True
        }

        state.setdefault("active_agents", []).append(self.agent_id)
        self.logger.warning(f"错误状态创建 - 使用降级响应: {fallback_prompt[:50]}...")
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

        return " | ".join(context_parts) if context_parts else "Initial interaction"
