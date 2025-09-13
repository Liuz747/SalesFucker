"""
Sentiment Analysis Agent

LLM-powered sentiment analysis for customer interactions in beauty consultations.
Provides emotional context and customer satisfaction insights.
"""

from typing import Dict, Any
from ..base import BaseAgent, AgentMessage, ThreadState
from utils import parse_sentiment_response, get_current_datetime, get_processing_time_ms


class SentimentAnalysisAgent(BaseAgent):
    """
    情感分析智能体
    
    使用LLM分析客户情感状态，为对话提供情感上下文。
    专注于美妆咨询场景的情感识别和客户满意度评估。
    """
    
    def __init__(self, tenant_id: str):
        # 简化初始化
        super().__init__(
            agent_id=f"sentiment_analysis_{tenant_id}", 
            tenant_id=tenant_id
        )
        
        
        self.logger.info(f"情感分析智能体初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理情感分析消息
        
        分析单个消息的情感状态。
        
        参数:
            message: 包含待分析文本的消息
            
        返回:
            AgentMessage: 包含情感分析结果的响应
        """
        try:
            customer_input = message.payload.get("text", "")
            context = message.context.get("conversation_context", "")
            
            sentiment_result = await self._analyze_sentiment(customer_input, context)
            
            response_payload = {
                "sentiment_analysis": sentiment_result,
                "processing_agent": self.agent_id,
                "analysis_timestamp": get_current_datetime().isoformat()
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload=response_payload,
                context=message.context
            )
            
        except Exception as e:
            error_context = {
                "message_id": message.message_id,
                "sender": message.sender
            }
            error_info = await self.handle_error(e, error_context)
            
            fallback_result = {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "fallback": True
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "sentiment_analysis": fallback_result},
                context=message.context
            )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态中的情感分析
        
        在LangGraph工作流中执行情感分析，更新对话状态。
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_input = state.customer_input
            conversation_context = self._build_conversation_context(state)
            
            # 执行情感分析
            sentiment_result = await self._analyze_sentiment(customer_input, conversation_context)
            
            # 更新对话状态
            state.sentiment_analysis = sentiment_result
            state.active_agents.append(self.agent_id)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"thread_id": state.thread_id})
            
            # 设置降级情感分析
            state.sentiment_analysis = {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "emotions": [],
                "fallback": True,
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _analyze_sentiment(self, customer_input: str, conversation_context: str = "") -> Dict[str, Any]:
        """
        使用LLM分析客户情感
        
        参数:
            customer_input: 客户输入文本
            conversation_context: 对话上下文
            
        返回:
            Dict[str, Any]: 情感分析结果
        """
        try:
            # 简化的情感分析提示词
            prompt = f"""分析以下客户输入的情感状态：

客户输入：{customer_input}

请返回JSON格式：
{{
    "sentiment": "positive",
    "score": 0.8,
    "confidence": 0.9,
    "emotions": ["愉快", "满意"]
}}"""
            
            # 调用LLM分析
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm_call(messages, temperature=0.3)
            
            # 解析结构化响应
            sentiment_result = parse_sentiment_response(response)
            
            # 添加额外的分析信息
            sentiment_result["agent_id"] = self.agent_id
            sentiment_result["analysis_method"] = "llm_powered"
            
            return sentiment_result
            
        except Exception as e:
            self.logger.error(f"情感分析失败: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.5,
                "emotions": [],
                "fallback": True,
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    def _build_conversation_context(self, state: ThreadState) -> str:
        """
        构建对话上下文信息
        
        参数:
            state: 对话状态
            
        返回:
            str: 格式化的对话上下文
        """
        context_parts = []
        
        # 客户档案信息
        if state.customer_profile:
            profile_info = []
            if state.customer_profile.get("skin_type"):
                profile_info.append(f"Skin type: {state.customer_profile['skin_type']}")
            if state.customer_profile.get("previous_purchases"):
                profile_info.append(f"Previous purchases: {len(state.customer_profile['previous_purchases'])} items")
            
            if profile_info:
                context_parts.append("Customer profile: " + ", ".join(profile_info))
        
        # 对话历史
        if state.conversation_history:
            recent_history = state.conversation_history[-3:]  # 最近3条对话
            context_parts.append("Recent conversation: " + " | ".join(recent_history))
        
        # 合规和意图信息
        if state.compliance_result:
            context_parts.append(f"Compliance status: {state.compliance_result.get('status', 'unknown')}")
        
        return " | ".join(context_parts) if context_parts else "Initial interaction"
    
    def get_sentiment_metrics(self) -> Dict[str, Any]:
        """
        获取情感分析性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        return {
            "total_analyses": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }