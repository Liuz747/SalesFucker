"""
AI Suggestion Agent

Human-AI collaboration and intelligent assistance recommendations.
Handles escalation decisions and system improvement suggestions.
"""

from typing import Dict, Any, List
from ..core import BaseAgent, AgentMessage, ConversationState
from src.llm import get_llm_client, get_prompt_manager
from src.utils import get_current_datetime, get_processing_time_ms


class AISuggestionAgent(BaseAgent):
    """
    AI建议智能体
    
    提供人机协作和智能辅助建议。
    处理升级决策和系统改进建议。
    """
    
    def __init__(self, tenant_id: str):
        super().__init__(f"ai_suggestion_{tenant_id}", tenant_id)
        
        # LLM integration for intelligent suggestions
        self.llm_client = get_llm_client()
        self.prompt_manager = get_prompt_manager()
        
        # 升级规则配置
        self.escalation_rules = {
            "complexity_threshold": 0.8,
            "confidence_threshold": 0.6,
            "sentiment_escalation": ["negative"],
            "compliance_escalation": ["blocked", "flagged"],
            "intent_escalation": ["complaint", "refund", "technical_issue"]
        }
        
        # 建议类型
        self.suggestion_types = {
            "escalation": "Recommend human intervention",
            "improvement": "System enhancement suggestion",
            "strategy": "Alternative approach recommendation",
            "optimization": "Performance optimization suggestion"
        }
        
        self.logger.info(f"AI建议智能体初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理AI建议请求
        
        分析系统状态并提供智能建议。
        
        参数:
            message: 包含建议请求的消息
            
        返回:
            AgentMessage: 包含AI建议的响应
        """
        try:
            request_type = message.payload.get("request_type", "general")
            context_data = message.payload.get("context_data", {})
            
            if request_type == "escalation_check":
                suggestions = await self._analyze_escalation_need(context_data)
            elif request_type == "improvement":
                suggestions = await self._generate_improvement_suggestions(context_data)
            elif request_type == "optimization":
                suggestions = await self._analyze_optimization_opportunities(context_data)
            else:
                suggestions = await self._generate_general_suggestions(context_data)
            
            response_payload = {
                "ai_suggestions": suggestions,
                "processing_agent": self.agent_id,
                "suggestion_timestamp": get_current_datetime().isoformat()
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
            
            fallback_suggestions = {
                "suggestions": [],
                "escalation_recommended": False,
                "fallback": True
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "ai_suggestions": fallback_suggestions},
                context=message.context
            )
    
    async def process_conversation(self, state: ConversationState) -> ConversationState:
        """
        处理对话状态中的AI建议分析
        
        分析整个对话流程并提供建议。
        
        参数:
            state: 当前对话状态
            
        返回:
            ConversationState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            # 分析升级需求
            escalation_analysis = await self._analyze_escalation_need({
                "sentiment": state.sentiment_analysis,
                "intent": state.intent_analysis,
                "compliance": state.compliance_result,
                "agent_responses": state.agent_responses,
                "conversation_complexity": len(state.conversation_history)
            })
            
            # 生成系统改进建议
            improvement_suggestions = await self._analyze_conversation_quality(state)
            
            # 合并所有建议
            all_suggestions = {
                "escalation_analysis": escalation_analysis,
                "improvement_suggestions": improvement_suggestions,
                "conversation_quality_score": self._calculate_conversation_quality(state),
                "processing_complete": True
            }
            
            # 更新对话状态
            state.agent_responses[self.agent_id] = all_suggestions
            state.active_agents.append(self.agent_id)
            
            # 如果建议升级，设置升级标志
            if escalation_analysis.get("escalation_recommended", False):
                state.human_escalation = True
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"conversation_id": state.conversation_id})
            
            # 设置保守的建议状态
            state.agent_responses[self.agent_id] = {
                "escalation_analysis": {"escalation_recommended": True, "reason": "Error in AI analysis"},
                "improvement_suggestions": [],
                "error": str(e),
                "fallback": True,
                "agent_id": self.agent_id
            }
            state.human_escalation = True  # 出错时保守升级
            
            return state
    
    async def _analyze_escalation_need(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析是否需要人工升级
        
        参数:
            context_data: 上下文数据
            
        返回:
            Dict[str, Any]: 升级分析结果
        """
        try:
            escalation_factors = []
            escalation_score = 0.0
            
            # 检查情感因素
            sentiment_data = context_data.get("sentiment", {})
            if sentiment_data.get("sentiment") in self.escalation_rules["sentiment_escalation"]:
                escalation_factors.append("Negative customer sentiment detected")
                escalation_score += 0.3
            
            # 检查合规因素
            compliance_data = context_data.get("compliance", {})
            if compliance_data.get("status") in self.escalation_rules["compliance_escalation"]:
                escalation_factors.append("Compliance issues detected")
                escalation_score += 0.4
            
            # 检查意图因素
            intent_data = context_data.get("intent", {})
            if intent_data.get("intent") in self.escalation_rules["intent_escalation"]:
                escalation_factors.append("Complex customer intent requiring human attention")
                escalation_score += 0.3
            
            # 检查对话复杂度
            conversation_complexity = context_data.get("conversation_complexity", 0)
            if conversation_complexity > 10:
                escalation_factors.append("Long conversation requiring human review")
                escalation_score += 0.2
            
            # 检查代理响应质量
            agent_responses = context_data.get("agent_responses", {})
            error_agents = [agent_id for agent_id, response in agent_responses.items() 
                          if response.get("error") or response.get("fallback")]
            if len(error_agents) > 1:
                escalation_factors.append("Multiple agent failures detected")
                escalation_score += 0.3
            
            # 使用LLM进行上下文分析
            llm_analysis = await self._llm_escalation_analysis(context_data)
            if llm_analysis.get("escalation_recommended"):
                escalation_factors.append(llm_analysis.get("reason", "LLM recommends escalation"))
                escalation_score += 0.2
            
            # 决定是否升级
            escalation_recommended = escalation_score >= 0.5
            
            return {
                "escalation_recommended": escalation_recommended,
                "escalation_score": min(1.0, escalation_score),
                "escalation_factors": escalation_factors,
                "confidence": self._calculate_escalation_confidence(context_data),
                "suggested_action": "human_handoff" if escalation_recommended else "continue_ai",
                "llm_analysis": llm_analysis,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            self.logger.error(f"升级分析失败: {e}")
            return {
                "escalation_recommended": True,
                "escalation_score": 1.0,
                "escalation_factors": ["Error in escalation analysis - defaulting to human review"],
                "confidence": 0.5,
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def _llm_escalation_analysis(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM分析升级需求
        
        参数:
            context_data: 上下文数据
            
        返回:
            Dict[str, Any]: LLM分析结果
        """
        try:
            analysis_prompt = f"""
Analyze this customer service interaction and determine if human escalation is needed.

Context Data:
- Sentiment: {context_data.get('sentiment', {})}
- Intent: {context_data.get('intent', {})}
- Compliance: {context_data.get('compliance', {})}
- Agent Responses: {len(context_data.get('agent_responses', {}))} agents involved

Consider factors like:
1. Customer frustration or negative sentiment
2. Complex technical issues
3. Compliance or safety concerns
4. Repeated AI failures
5. High-value customer needs

Respond with JSON:
{{
    "escalation_recommended": true/false,
    "confidence": 0.0-1.0,
    "reason": "specific reason for recommendation",
    "urgency": "low/medium/high"
}}
"""
            
            messages = [{"role": "user", "content": analysis_prompt}]
            response = await self.llm_client.chat_completion(messages, temperature=0.3)
            
            # 简化解析
            try:
                import json
                return json.loads(response)
            except:
                return {
                    "escalation_recommended": False,
                    "confidence": 0.5,
                    "reason": "LLM analysis completed",
                    "urgency": "medium"
                }
                
        except Exception as e:
            self.logger.warning(f"LLM升级分析失败: {e}")
            return {
                "escalation_recommended": False,
                "confidence": 0.5,
                "reason": "LLM analysis unavailable",
                "urgency": "medium"
            }
    
    def _calculate_escalation_confidence(self, context_data: Dict[str, Any]) -> float:
        """
        计算升级建议置信度
        
        参数:
            context_data: 上下文数据
            
        返回:
            float: 置信度分数
        """
        confidence = 0.5  # 基础置信度
        
        # 数据完整度影响置信度
        if context_data.get("sentiment"):
            confidence += 0.1
        if context_data.get("intent"):
            confidence += 0.1
        if context_data.get("compliance"):
            confidence += 0.1
        if context_data.get("agent_responses"):
            confidence += 0.2
        
        return min(1.0, confidence)
    
    async def _analyze_conversation_quality(self, state: ConversationState) -> List[Dict[str, Any]]:
        """
        分析对话质量并提供改进建议
        
        参数:
            state: 对话状态
            
        返回:
            List[Dict[str, Any]]: 改进建议列表
        """
        suggestions = []
        
        # 分析响应时间
        if len(state.active_agents) > 6:
            suggestions.append({
                "type": "performance",
                "priority": "medium",
                "suggestion": "Consider optimizing agent workflow - many agents involved",
                "impact": "Improve response time"
            })
        
        # 分析错误率
        error_responses = [resp for resp in state.agent_responses.values() 
                         if resp.get("error") or resp.get("fallback")]
        if len(error_responses) > 1:
            suggestions.append({
                "type": "reliability",
                "priority": "high",
                "suggestion": "Multiple agent failures detected - investigate system reliability",
                "impact": "Improve conversation success rate"
            })
        
        # 分析个性化程度
        if not state.customer_profile:
            suggestions.append({
                "type": "personalization",
                "priority": "medium",
                "suggestion": "Gather more customer profile data for better personalization",
                "impact": "Enhance customer experience"
            })
        
        return suggestions
    
    def _calculate_conversation_quality(self, state: ConversationState) -> float:
        """
        计算对话质量分数
        
        参数:
            state: 对话状态
            
        返回:
            float: 质量分数 (0.0-1.0)
        """
        score = 0.5  # 基础分数
        
        # 完成度评分
        if state.processing_complete:
            score += 0.2
        
        # 错误率评分
        total_responses = len(state.agent_responses)
        error_responses = len([resp for resp in state.agent_responses.values() 
                             if resp.get("error") or resp.get("fallback")])
        if total_responses > 0:
            error_rate = error_responses / total_responses
            score += 0.2 * (1 - error_rate)
        
        # 个性化评分
        if state.customer_profile and len(state.customer_profile) > 2:
            score += 0.1
        
        return min(1.0, score)
    
    async def _generate_improvement_suggestions(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成系统改进建议"""
        suggestions = []
        
        suggestions.append({
            "type": "system_enhancement",
            "priority": "low",
            "suggestion": "Consider implementing conversation analytics dashboard",
            "impact": "Better visibility into system performance"
        })
        
        return suggestions
    
    async def _analyze_optimization_opportunities(self, context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析优化机会"""
        opportunities = []
        
        opportunities.append({
            "type": "performance_optimization",
            "priority": "medium", 
            "suggestion": "Implement response caching for common queries",
            "impact": "Faster response times"
        })
        
        return opportunities
    
    async def _generate_general_suggestions(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成一般性建议"""
        return {
            "suggestions": [],
            "escalation_recommended": False,
            "general_advice": "System operating normally"
        }
    
    def get_suggestion_metrics(self) -> Dict[str, Any]:
        """
        获取AI建议性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        return {
            "total_suggestions": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "escalation_rules_active": len(self.escalation_rules),
            "suggestion_types": list(self.suggestion_types.keys()),
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }