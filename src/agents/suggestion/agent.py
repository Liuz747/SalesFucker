"""
AI建议智能体 - 重构版

人机协作和智能辅助建议的轻量级编排器。
整合升级分析、质量评估、LLM分析和建议生成功能。
"""

from typing import Dict, Any
from ..base import BaseAgent, AgentMessage, ThreadState
from src.llm.intelligent_router import RoutingStrategy
from src.utils import get_current_datetime, get_processing_time_ms

from .escalation_analyzer import EscalationAnalyzer
from .quality_assessor import QualityAssessor
from .llm_analyzer import LLMAnalyzer
from .suggestion_generator import SuggestionGenerator


class AISuggestionAgent(BaseAgent):
    """
    AI建议智能体 - 重构版
    
    提供人机协作和智能辅助建议。
    使用模块化组件处理升级决策、质量评估和系统改进建议。
    """
    
    def __init__(self, tenant_id: str):
        # MAS架构：使用智能体优化策略提供系统建议
        super().__init__(
            agent_id=f"ai_suggestion_{tenant_id}", 
            tenant_id=tenant_id,
            routing_strategy=RoutingStrategy.AGENT_OPTIMIZED  # 平衡质量和效率的建议生成
        )
        
        # 初始化功能模块
        self.escalation_analyzer = EscalationAnalyzer(tenant_id)
        self.quality_assessor = QualityAssessor(tenant_id)
        self.llm_analyzer = LLMAnalyzer(tenant_id)
        self.suggestion_generator = SuggestionGenerator(tenant_id)
        
        # 建议类型映射
        self.request_handlers = {
            "escalation_check": self._handle_escalation_check,
            "improvement": self._handle_improvement_request,
            "optimization": self._handle_optimization_request,
            "quality_assessment": self._handle_quality_assessment,
            "general": self._handle_general_request
        }
        
        self.logger.info(f"AI建议智能体初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理AI建议请求
        
        参数:
            message: 包含建议请求的消息
            
        返回:
            AgentMessage: 包含AI建议的响应
        """
        try:
            request_type = message.payload.get("request_type", "general")
            context_data = message.payload.get("context_data", {})
            
            # 路由到对应的处理器
            handler = self.request_handlers.get(request_type, self._handle_general_request)
            suggestions = await handler(context_data)
            
            response_payload = {
                "ai_suggestions": suggestions,
                "processing_agent": self.agent_id,
                "suggestion_timestamp": get_current_datetime().isoformat(),
                "request_type": request_type
            }
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload=response_payload,
                context=message.context
            )
            
        except Exception as e:
            return await self._handle_processing_error(e, message)
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态中的AI建议分析
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            # 准备分析上下文
            analysis_context = self._prepare_conversation_context(state)
            
            # 执行升级分析
            escalation_analysis = await self._perform_escalation_analysis(analysis_context)
            
            # 执行质量评估
            quality_assessment = await self._perform_quality_assessment(state)
            
            # 合并分析结果
            comprehensive_analysis = {
                "escalation_analysis": escalation_analysis,
                "quality_assessment": quality_assessment,
                "conversation_quality_score": self.quality_assessor.calculate_conversation_quality_score(state),
                "processing_complete": True,
                "agent_id": self.agent_id
            }
            
            # 更新对话状态
            state = self._update_conversation_state(state, comprehensive_analysis, escalation_analysis)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            return await self._handle_conversation_error(e, state)
    
    async def _handle_escalation_check(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理升级检查请求"""
        rule_analysis = await self.escalation_analyzer.analyze_escalation_need(context_data)
        llm_analysis = await self.llm_analyzer.analyze_escalation_context(context_data)
        return self._merge_escalation_analyses(rule_analysis, llm_analysis)
    
    async def _handle_improvement_request(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理改进建议请求"""
        basic_suggestions = await self.suggestion_generator.generate_improvement_suggestions(context_data)
        llm_suggestions = await self.llm_analyzer.generate_improvement_suggestions(context_data)
        return {"basic_suggestions": basic_suggestions, "llm_suggestions": llm_suggestions, "suggestion_type": "improvement"}
    
    async def _handle_optimization_request(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理优化分析请求"""
        opportunities = await self.suggestion_generator.analyze_optimization_opportunities(context_data)
        return {"optimization_opportunities": opportunities, "suggestion_type": "optimization"}
    
    async def _handle_quality_assessment(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理质量评估请求"""
        mock_state = self._build_mock_conversation_state(context_data)
        quality_suggestions = await self.quality_assessor.assess_conversation_quality(mock_state)
        quality_score = self.quality_assessor.calculate_conversation_quality_score(mock_state)
        return {"quality_suggestions": quality_suggestions, "quality_score": quality_score, "suggestion_type": "quality_assessment"}
    
    async def _handle_general_request(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理一般性建议请求"""
        return await self.suggestion_generator.generate_general_suggestions(context_data)
    
    async def _perform_escalation_analysis(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行综合升级分析"""
        rule_analysis = await self.escalation_analyzer.analyze_escalation_need(context_data)
        llm_analysis = await self.llm_analyzer.analyze_escalation_context(context_data)
        return self._merge_escalation_analyses(rule_analysis, llm_analysis)
    
    async def _perform_quality_assessment(self, state: ThreadState) -> Dict[str, Any]:
        """执行质量评估"""
        quality_suggestions = await self.quality_assessor.assess_conversation_quality(state)
        conversation_data = {
            "total_exchanges": len(state.conversation_history),
            "agent_responses": state.agent_responses,
            "sentiment": getattr(state, 'sentiment_analysis', {}),
            "resolution_status": "pending" if not state.processing_complete else "complete",
            "error_count": len([r for r in state.agent_responses.values() if r.get("error")])
        }
        llm_quality = await self.llm_analyzer.analyze_conversation_quality(conversation_data)
        return {
            "improvement_suggestions": quality_suggestions,
            "llm_quality_analysis": llm_quality,
            "combined_score": (self.quality_assessor.calculate_conversation_quality_score(state) + llm_quality.get("quality_score", 0.5)) / 2
        }
    
    def _prepare_conversation_context(self, state: ThreadState) -> Dict[str, Any]:
        """准备对话分析上下文"""
        return {
            "sentiment": getattr(state, 'sentiment_analysis', {}),
            "intent": getattr(state, 'intent_analysis', {}),
            "compliance": getattr(state, 'compliance_result', {}),
            "agent_responses": state.agent_responses,
            "conversation_complexity": len(state.conversation_history),
            "customer_profile_available": bool(state.customer_profile)
        }
    
    def _merge_escalation_analyses(self, rule_analysis: Dict[str, Any], 
                                 llm_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """合并升级分析结果"""
        # 综合决策逻辑
        rule_recommendation = rule_analysis.get("escalation_recommended", False)
        llm_recommendation = llm_analysis.get("escalation_recommended", False)
        
        # 任一分析建议升级则升级（保守策略）
        final_recommendation = rule_recommendation or llm_recommendation
        
        # 综合置信度
        rule_confidence = rule_analysis.get("confidence", 0.5)
        llm_confidence = llm_analysis.get("confidence", 0.5)
        combined_confidence = (rule_confidence + llm_confidence) / 2
        
        return {
            "escalation_recommended": final_recommendation,
            "combined_confidence": combined_confidence,
            "rule_analysis": rule_analysis,
            "llm_analysis": llm_analysis,
            "decision_basis": "combined_analysis"
        }
    
    def _update_conversation_state(self, state: ThreadState, 
                                 analysis: Dict[str, Any],
                                 escalation_analysis: Dict[str, Any]) -> ThreadState:
        """更新对话状态"""
        # 更新代理响应
        state.agent_responses[self.agent_id] = analysis
        
        # 更新活跃代理列表
        if self.agent_id not in state.active_agents:
            state.active_agents.append(self.agent_id)
        
        # 设置升级标志
        if escalation_analysis.get("escalation_recommended", False):
            state.human_escalation = True
        
        return state
    
    def _build_mock_conversation_state(self, context_data: Dict[str, Any]) -> ThreadState:
        """从上下文数据构建模拟的对话状态"""
        # 这是一个简化的实现，实际使用中可能需要更完整的构建逻辑
        mock_state = ThreadState()
        mock_state.agent_responses = context_data.get("agent_responses", {})
        mock_state.conversation_history = context_data.get("conversation_history", [])
        mock_state.customer_profile = context_data.get("customer_profile", {})
        mock_state.processing_complete = context_data.get("processing_complete", False)
        
        return mock_state
    
    async def _handle_processing_error(self, error: Exception, message: AgentMessage) -> AgentMessage:
        """处理处理错误"""
        error_context = {
            "message_id": message.message_id,
            "sender": message.sender
        }
        error_info = await self.handle_error(error, error_context)
        
        fallback_suggestions = {
            "suggestions": [],
            "escalation_recommended": False,
            "fallback": True,
            "error": str(error)
        }
        
        return await self.send_message(
            recipient=message.sender,
            message_type="response",
            payload={"error": error_info, "ai_suggestions": fallback_suggestions},
            context=message.context
        )
    
    async def _handle_conversation_error(self, error: Exception, 
                                       state: ThreadState) -> ThreadState:
        """处理对话处理错误"""
        await self.handle_error(error, {"thread_id": state.thread_id})
        
        # 设置保守的建议状态
        state.agent_responses[self.agent_id] = {
            "escalation_analysis": {"escalation_recommended": True, "reason": "Error in AI analysis"},
            "improvement_suggestions": [],
            "error": str(error),
            "fallback": True,
            "agent_id": self.agent_id
        }
        state.human_escalation = True  # 出错时保守升级
        
        return state
    
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
            "escalation_rules_active": len(self.escalation_analyzer.get_escalation_rules()),
            "suggestion_types": self.suggestion_generator.get_suggestion_categories(),
            "component_status": {
                "escalation_analyzer": "active",
                "quality_assessor": "active", 
                "llm_analyzer": "active",
                "suggestion_generator": "active"
            },
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }
    
    def update_configuration(self, config_updates: Dict[str, Any]) -> None:
        """
        更新组件配置
        
        参数:
            config_updates: 配置更新字典
        """
        try:
            # 更新升级规则
            if "escalation_rules" in config_updates:
                self.escalation_analyzer.update_escalation_rules(config_updates["escalation_rules"])
            
            # 更新质量阈值
            if "quality_thresholds" in config_updates:
                self.quality_assessor.update_quality_thresholds(config_updates["quality_thresholds"])
            
            # 更新LLM配置
            if "llm_config" in config_updates:
                self.llm_analyzer.update_analysis_config(config_updates["llm_config"])
            
            self.logger.info(f"配置更新完成: {list(config_updates.keys())}")
            
        except Exception as e:
            self.logger.error(f"配置更新失败: {e}")