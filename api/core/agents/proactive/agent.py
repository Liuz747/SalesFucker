"""
Proactive Agent

Behavior-triggered customer outreach and engagement automation.
Identifies opportunities for proactive customer contact and follow-up.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..base import BaseAgent, AgentMessage, ThreadState

from utils import get_current_datetime, get_processing_time_ms

class ProactiveAgent(BaseAgent):
    """
    主动营销智能体
    
    基于客户行为触发主动外联和跟进。
    识别营销机会并自动化客户接触。
    """
    
    def __init__(self):
        # MAS架构：使用销售优化策略生成主动营销内容
        super().__init__()
        
        # 触发器配置
        self.trigger_rules = {
            "cart_abandonment": {
                "condition": "cart_inactive_24h",
                "action": "send_cart_reminder",
                "priority": "high",
                "delay_hours": 24
            },
            "product_reorder": {
                "condition": "product_usage_period_ended",
                "action": "suggest_reorder",
                "priority": "medium", 
                "delay_days": 30
            },
            "seasonal_promotion": {
                "condition": "seasonal_event",
                "action": "send_seasonal_offer",
                "priority": "medium",
                "timing": "event_based"
            },
            "loyalty_engagement": {
                "condition": "high_value_customer_inactive",
                "action": "personalized_outreach",
                "priority": "high",
                "delay_days": 14
            }
        }
        
        # 简化的客户行为跟踪
        self.customer_behaviors: Dict[str, List[Dict[str, Any]]] = {}
        
        self.logger.info(f"主动营销智能体初始化完成: {self.agent_id}")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理主动营销消息
        
        分析客户行为并触发主动营销活动。
        
        参数:
            message: 包含客户行为数据的消息
            
        返回:
            AgentMessage: 包含主动营销建议的响应
        """
        try:
            operation = message.payload.get("operation", "analyze")
            customer_id = message.payload.get("customer_id")
            
            if operation == "analyze":
                proactive_opportunities = await self._analyze_proactive_opportunities(
                    customer_id, message.payload
                )
            elif operation == "trigger":
                proactive_opportunities = await self._execute_proactive_trigger(
                    message.payload
                )
            else:
                proactive_opportunities = {"error": f"Unknown operation: {operation}"}
            
            response_payload = {
                "proactive_opportunities": proactive_opportunities,
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
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "proactive_opportunities": []},
                context=message.context
            )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态中的主动营销分析
        
        记录客户行为并识别主动营销机会。
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        start_time = get_current_datetime()
        
        try:
            customer_id = state.customer_id
            
            # 记录客户行为
            if customer_id:
                await self._record_customer_behavior(state)
            
            # 分析主动营销机会
            proactive_opportunities = await self._analyze_conversation_opportunities(state)
            
            # 更新对话状态
            state.agent_responses[self.agent_id] = {
                "proactive_opportunities": proactive_opportunities,
                "behavior_recorded": customer_id is not None,
                "processing_complete": True
            }
            state.active_agents.append(self.agent_id)
            
            # 更新处理统计
            processing_time = get_processing_time_ms(start_time)
            self.update_stats(processing_time)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"thread_id": state.thread_id})
            
            # 设置降级状态
            state.agent_responses[self.agent_id] = {
                "proactive_opportunities": [],
                "behavior_recorded": False,
                "error": str(e),
                "fallback": True,
                "agent_id": self.agent_id
            }
            
            return state
    
    async def _analyze_proactive_opportunities(
        self, 
        customer_id: str, 
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        分析主动营销机会
        
        参数:
            customer_id: 客户ID
            data: 客户数据
            
        返回:
            List[Dict[str, Any]]: 主动营销机会列表
        """
        opportunities = []
        
        try:
            if not customer_id:
                return opportunities
            
            customer_history = self.customer_behaviors.get(customer_id, [])
            
            # 检查各种触发条件
            for trigger_name, trigger_config in self.trigger_rules.items():
                opportunity = await self._check_trigger_condition(
                    trigger_name, trigger_config, customer_id, customer_history, data
                )
                if opportunity:
                    opportunities.append(opportunity)
            
            # 按优先级排序
            opportunities.sort(key=lambda x: self._get_priority_score(x.get("priority", "low")), reverse=True)
            
            return opportunities[:5]  # 最多返回5个机会
            
        except Exception as e:
            self.logger.error(f"主动营销机会分析失败: {e}")
            return []
    
    async def _check_trigger_condition(
        self, 
        trigger_name: str, 
        trigger_config: Dict[str, Any], 
        customer_id: str,
        customer_history: List[Dict[str, Any]], 
        current_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查触发条件
        
        参数:
            trigger_name: 触发器名称
            trigger_config: 触发器配置
            customer_id: 客户ID
            customer_history: 客户历史行为
            current_data: 当前数据
            
        返回:
            Dict[str, Any]: 触发机会信息，如果不满足条件则返回None
        """
        condition = trigger_config["condition"]
        
        if condition == "cart_inactive_24h":
            # 检查购物车放弃
            cart_activity = self._find_recent_activity(customer_history, "cart_activity", hours=24)
            if cart_activity and not self._find_recent_activity(customer_history, "purchase", hours=24):
                return {
                    "trigger_name": trigger_name,
                    "opportunity_type": "cart_recovery",
                    "priority": trigger_config["priority"],
                    "action": trigger_config["action"],
                    "message": "Customer has items in cart but hasn't completed purchase in 24 hours",
                    "customer_id": customer_id
                }
        
        elif condition == "product_usage_period_ended":
            # 检查产品复购时机
            last_purchase = self._find_recent_activity(customer_history, "purchase", days=45)
            if last_purchase:
                days_since_purchase = (get_current_datetime() - datetime.fromisoformat(last_purchase["timestamp"])).days
                if days_since_purchase >= 30:
                    return {
                        "trigger_name": trigger_name,
                        "opportunity_type": "reorder_reminder",
                        "priority": trigger_config["priority"],
                        "action": trigger_config["action"],
                        "message": f"Customer's last purchase was {days_since_purchase} days ago, ideal for reorder",
                        "customer_id": customer_id
                    }
        
        elif condition == "high_value_customer_inactive":
            # 检查高价值客户活跃度
            if current_data.get("customer_value", "medium") == "high":
                last_interaction = self._find_recent_activity(customer_history, "any", days=14)
                if not last_interaction:
                    return {
                        "trigger_name": trigger_name,
                        "opportunity_type": "vip_engagement",
                        "priority": trigger_config["priority"],
                        "action": trigger_config["action"],
                        "message": "High-value customer hasn't interacted in 14+ days",
                        "customer_id": customer_id
                    }
        
        return None
    
    def _find_recent_activity(
        self, 
        history: List[Dict[str, Any]], 
        activity_type: str, 
        hours: int = None, 
        days: int = None
    ) -> Dict[str, Any]:
        """
        查找最近的活动记录
        
        参数:
            history: 客户历史记录
            activity_type: 活动类型
            hours: 时间范围（小时）
            days: 时间范围（天）
            
        返回:
            Dict[str, Any]: 活动记录，如果没有找到则返回None
        """
        if not history:
            return None
        
        # 计算时间阈值
        now = get_current_datetime()
        if hours:
            threshold = now - timedelta(hours=hours)
        elif days:
            threshold = now - timedelta(days=days)
        else:
            threshold = now - timedelta(days=30)  # 默认30天
        
        # 查找匹配的活动
        for activity in reversed(history):  # 从最新开始查找
            activity_time = datetime.fromisoformat(activity.get("timestamp", "2000-01-01"))
            if activity_time >= threshold:
                if activity_type == "any" or activity.get("type") == activity_type:
                    return activity
        
        return None
    
    def _get_priority_score(self, priority: str) -> int:
        """获取优先级分数"""
        priority_scores = {"high": 3, "medium": 2, "low": 1}
        return priority_scores.get(priority, 1)
    
    async def _record_customer_behavior(self, state: ThreadState):
        """
        记录客户行为
        
        参数:
            state: 对话状态
        """
        try:
            customer_id = state.customer_id
            if not customer_id:
                return
            
            # 创建行为记录
            behavior_record = {
                "timestamp": get_current_datetime().isoformat(),
                "type": "conversation",
                "thread_id": state.thread_id,
                "customer_input": state.customer_input,
                "sentiment": state.sentiment_analysis.get("sentiment", "neutral") if state.sentiment_analysis else "neutral",
                "intent": state.intent_analysis.get("intent", "browsing") if state.intent_analysis else "browsing",
                "agent_responses": list(state.agent_responses.keys())
            }
            
            # 存储行为记录
            if customer_id not in self.customer_behaviors:
                self.customer_behaviors[customer_id] = []
            
            self.customer_behaviors[customer_id].append(behavior_record)
            
            # 保持最近100条记录
            if len(self.customer_behaviors[customer_id]) > 100:
                self.customer_behaviors[customer_id] = self.customer_behaviors[customer_id][-100:]
            
        except Exception as e:
            self.logger.error(f"客户行为记录失败: {e}")
    
    async def _analyze_conversation_opportunities(self, state: ThreadState) -> List[Dict[str, Any]]:
        """
        分析当前对话的主动营销机会
        
        参数:
            state: 对话状态
            
        返回:
            List[Dict[str, Any]]: 机会列表
        """
        opportunities = []
        
        # 基于意图分析的机会
        if state.intent_analysis:
            intent = state.intent_analysis.get("intent", "browsing")
            if intent == "interested":
                opportunities.append({
                    "type": "follow_up",
                    "priority": "medium",
                    "message": "Customer showing interest - schedule follow-up in 24 hours",
                    "action": "send_follow_up"
                })
            elif intent == "comparing":
                opportunities.append({
                    "type": "competitive_advantage",
                    "priority": "high", 
                    "message": "Customer comparing options - highlight unique value propositions",
                    "action": "send_comparison_guide"
                })
        
        # 基于情感分析的机会
        if state.sentiment_analysis:
            sentiment = state.sentiment_analysis.get("sentiment", "neutral")
            if sentiment == "negative":
                opportunities.append({
                    "type": "service_recovery",
                    "priority": "high",
                    "message": "Customer showing negative sentiment - proactive service intervention needed",
                    "action": "escalate_to_human"
                })
        
        return opportunities
    
    def get_proactive_metrics(self) -> Dict[str, Any]:
        """
        获取主动营销性能指标
        
        返回:
            Dict[str, Any]: 性能指标信息
        """
        total_customers_tracked = len(self.customer_behaviors)
        total_behaviors = sum(len(behaviors) for behaviors in self.customer_behaviors.values())
        
        return {
            "total_analyses": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "average_processing_time": self.processing_stats["average_response_time"],
            "last_activity": self.processing_stats["last_activity"],
            "customers_tracked": total_customers_tracked,
            "total_behaviors_recorded": total_behaviors,
            "trigger_rules_active": len(self.trigger_rules),
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }