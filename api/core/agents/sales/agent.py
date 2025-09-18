"""
销售智能体 - 轻量级核心模块

该模块作为销售智能体的核心，遵循模块化设计原则。
专注于智能体核心逻辑，将模板、策略等功能分离到专门模块。

核心功能:
- 智能体核心逻辑
- 对话协调和状态管理
- 模块间集成和错误处理
- LangGraph工作流节点处理
"""

from typing import Dict, Any, Optional

from ..base import BaseAgent, AgentMessage, ThreadState
from .sales_strategies import get_sales_strategies, analyze_customer_segment, get_strategy_for_segment, adapt_strategy_to_context
from utils import to_isoformat


class SalesAgent(BaseAgent):
    """
    销售智能体 - 核心控制器
    
    负责协调各个销售模块，保持轻量级核心设计。
    
    职责:
    - 智能体生命周期管理
    - 模块间协调和集成
    - 对话状态管理
    - 错误处理和降级
    """
    
    def __init__(self):
        # 简化初始化
        super().__init__()
        
        # Strategy management
        self.sales_strategies = get_sales_strategies()
        
        self.logger.info(f"销售智能体初始化完成: {self.agent_id}, MAS架构自动LLM优化")
    
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """
        处理销售消息
        
        对单个消息执行销售对话处理，返回个性化销售响应。
        
        参数:
            message: 包含客户输入的智能体消息
            
        返回:
            AgentMessage: 包含销售响应的消息
        """
        try:
            customer_input = message.payload.get("text", "")
            
            # 生成销售响应
            sales_response = await self._generate_sales_response(customer_input, message.context)
            
            # 构建响应载荷
            response_payload = {
                "sales_response": sales_response,
                "agent_type": "sales",
                "processing_agent": self.agent_id,
                "response_timestamp": to_isoformat()
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
                "sender": message.sender,
                "processing_agent": self.agent_id
            }
            error_info = await self.handle_error(e, error_context)
            
            return await self.send_message(
                recipient=message.sender,
                message_type="response",
                payload={"error": error_info, "sales_response": "I apologize, but I'm having trouble processing your request right now."},
                context=message.context
            )
    
    async def process_conversation(self, state: ThreadState) -> ThreadState:
        """
        处理对话状态（LangGraph工作流节点）
        
        在LangGraph工作流中执行销售对话处理，生成个性化销售响应。
        
        参数:
            state: 当前对话状态
            
        返回:
            ThreadState: 更新后的对话状态
        """
        try:
            customer_input = state.customer_input
            
            # 从IntentAnalysisAgent获取增强的客户分析数据
            intent_analysis = state.intent_analysis or {}
            customer_profile_data = intent_analysis.get("customer_profile", {})
            
            # 提取客户需求信息 (来自LLM分析)
            needs = {
                "skin_concerns": customer_profile_data.get("skin_concerns", []),
                "product_interests": customer_profile_data.get("product_interests", []),
                "urgency": customer_profile_data.get("urgency", "normal"),
                "experience_level": customer_profile_data.get("experience_level", "intermediate"),
                "budget_signals": customer_profile_data.get("budget_signals", [])
            }
            
            # 获取对话阶段 (来自LLM分析)
            stage_value = intent_analysis.get("conversation_stage", "consultation")
            
            # 使用LLM提取的信息丰富客户档案
            if customer_profile_data.get("skin_type_indicators"):
                state.customer_profile["inferred_skin_type"] = customer_profile_data["skin_type_indicators"][0]
            if customer_profile_data.get("budget_signals"):
                state.customer_profile["budget_preference"] = customer_profile_data["budget_signals"][0]
            if customer_profile_data.get("experience_level"):
                state.customer_profile["experience_level"] = customer_profile_data["experience_level"]
            
            # 客户细分和策略选择
            customer_segment = analyze_customer_segment(state.customer_profile)
            strategy = get_strategy_for_segment(customer_segment)
            
            # 根据上下文调整策略
            context = {
                "sentiment": getattr(state, "sentiment", "neutral"),
                "urgency": needs.get("urgency", "normal"),
                "purchase_intent": getattr(state, "purchase_intent", "browsing")
            }
            adapted_strategy = adapt_strategy_to_context(strategy, context)
            
            # 生成LLM驱动的个性化响应
            response = await self._generate_llm_response(
                customer_input, needs, stage_value, adapted_strategy, state
            )
            
            # 更新对话状态
            state.sales_response = response
            state.active_agents.append(self.agent_id)
            state.conversation_history.extend([
                {"role": "user", "content": customer_input},
                {"role": "assistant", "content": response}
            ])
            
            # 更新处理统计
            self.update_stats(time_taken=50)
            
            return state
            
        except Exception as e:
            await self.handle_error(e, {"thread_id": state.thread_id})
            state.error_state = "sales_processing_error"
            return state
    
    async def _generate_llm_response(
            self, 
            customer_input: str, 
            needs: Dict[str, Any],
            stage: str, 
            strategy: Dict[str, Any], 
            state: ThreadState
    ) -> str:
        """
        使用MAS多LLM生成个性化销售响应
        
        利用BaseAgent的MAS多LLM功能，智能选择最优供应商生成销售响应。
        
        参数:
            customer_input: 客户输入
            needs: 客户需求分析
            stage: 对话阶段
            strategy: 销售策略
            state: 对话状态
            
        返回:
            str: LLM生成的个性化销售响应
        """
        try:
            # 构建上下文信息
            context = {
                "customer_profile": state.customer_profile,
                "conversation_history": state.conversation_history[-5:],  # 最近5轮对话
                "product_context": {
                    "concerns": needs.get("concerns", []),
                    "budget_range": state.customer_profile.get("budget_range", "medium"),
                    "skin_type": state.customer_profile.get("skin_type", "not specified")
                }
            }
            
            # 构建销售咨询提示词
            prompt = f"""
            作为专业的美妆销售顾问，请为以下客户咨询提供个性化建议：

            客户咨询：{customer_input}

            客户档案：
            - 肌肤类型：{state.customer_profile.get('skin_type', '未知')}
            - 关注问题：{', '.join(needs.get('concerns', ['一般咨询']))}
            - 预算范围：{state.customer_profile.get('budget_range', '中等')}
            - 经验水平：{needs.get('experience_level', '中级')}

            销售策略：
            - 语调风格：{strategy.get('tone', '友好')} ({self._get_tone_description(strategy.get('tone', 'friendly'))})
            - 建议方式：{strategy.get('approach', '咨询式')}
            - 对话阶段：{stage}

            请提供：
            1. 针对客户关注问题的专业分析
            2. 个性化的产品建议或解决方案
            3. 合适的后续问题或引导
            4. 保持{strategy.get('tone', '友好')}的语调风格

            请用中文回复，语言自然流畅，体现专业性和亲和力。
            """
            
            # 使用简化的LLM调用
            messages = [
                {"role": "system", "content": "你是专业的美妆销售顾问"},
                {"role": "user", "content": prompt}
            ]
            response = await self.llm_call(
                messages=messages,
                temperature=0.8,
                max_tokens=512
            )
            
            if response:
                return response
            else:
                # 如果多LLM未启用或失败，降级到简单响应
                self.logger.warning("多LLM响应失败，使用降级响应")
                return self._generate_fallback_response(stage, strategy)
            
        except Exception as e:
            self.logger.error(f"多LLM响应生成失败: {e}")
            # 降级到简单模板响应
            return self._generate_fallback_response(stage, strategy)
    
    async def _generate_sales_response(self, customer_input: str, context: Dict[str, Any]) -> str:
        """生成销售响应（多LLM增强）"""
        try:
            # 构建简化的销售咨询提示词
            prompt = f"""
作为{self.tenant_id}品牌的专业美妆顾问，请为以下客户咨询提供个性化建议：

客户咨询：{customer_input}

请提供专业、友好的回复，包含：
1. 对客户需求的理解
2. 相关的产品建议或解决方案
3. 后续的引导问题

请用中文回复，保持专业和亲和的语调。
"""
            
            # 使用简化的LLM调用
            messages = [
                {"role": "system", "content": "你是专业的美妆销售顾问"},
                {"role": "user", "content": prompt}
            ]
            response = await self.llm_call(
                messages=messages,
                temperature=0.8,
                max_tokens=400
            )
            
            if response:
                return response
            else:
                self.logger.warning("多LLM响应失败，使用降级响应")
                return self._generate_fallback_response("consultation", {"tone": "friendly"})
            
        except Exception as e:
            self.logger.error(f"销售响应生成失败: {e}")
            return self._generate_fallback_response("consultation", {"tone": "friendly"})
    
    def _get_tone_description(self, tone: str) -> str:
        """获取语调描述"""
        tone_descriptions = {
            "sophisticated": "elegant and refined",
            "energetic": "enthusiastic and exciting", 
            "professional": "expert and authoritative",
            "warm": "caring and personal",
            "friendly": "approachable and helpful"
        }
        return tone_descriptions.get(tone, "professional and helpful")
    
    def _generate_fallback_response(self, stage: str, strategy: Dict[str, Any]) -> str:
        """生成降级响应"""
        tone = strategy.get("tone", "friendly")
        
        if stage == "greeting":
            return "Hello! Welcome! I'm excited to help you find the perfect beauty products today. What brings you here?"
        elif stage == "consultation":
            return "I'd love to help you find products that work perfectly for your needs. Could you tell me more about what you're looking for?"
        else:
            return "Thank you for your interest! How can I help you with your beauty needs today?"
    
    def get_conversation_metrics(self) -> Dict[str, Any]:
        """获取销售对话性能指标"""
        return {
            "total_conversations": self.processing_stats["messages_processed"],
            "error_rate": self.processing_stats["errors"] / max(1, self.processing_stats["messages_processed"]) * 100,
            "last_activity": self.processing_stats["last_activity"],
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id
        }
    
    # ===== 销售智能体专用提示词方法 =====
    
    async def get_greeting_message(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取个性化问候消息
        
        销售智能体专用方法，根据上下文生成合适的问候语。
        
        参数:
            context: 上下文信息，如客户资料、时间、场景等
            
        返回:
            str: 个性化问候消息，失败时返回None
            
        示例:
            context = {
                'agent_name': '小美',
                'customer_name': '李女士', 
                'time_of_day': '早上',
                'previous_visit': True
            }
        """
        try:
            if hasattr(self, '_prompt_manager') and self._prompt_manager:
                if not self.tenant_id:
                    raise ValueError(f"Sales agent {self.agent_id} requires tenant_id for greeting prompt")
                greeting = await self._prompt_manager.get_greeting_prompt(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    tenant_id=self.tenant_id,
                    context=context or {}
                )
                self.logger.debug(f"获取问候消息成功: {len(greeting or '')}字符")
                return greeting
            else:
                # 降级处理：使用基础问候语
                agent_name = context.get('agent_name', '美妆顾问') if context else '美妆顾问'
                return f"您好！我是您的专属{agent_name}，很高兴为您服务！请问有什么可以帮助您的吗？"
                
        except Exception as e:
            self.logger.warning(f"获取问候消息失败: {e}")
            return "您好！欢迎来到我们的美妆专柜，有什么可以帮助您的吗？"
    
    async def get_product_recommendation_prompt(self, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取产品推荐提示词模板
        
        根据客户需求生成个性化的产品推荐引导语。
        
        参数:
            context: 推荐上下文信息
                - skin_type: 肌肤类型 (干性/油性/混合性/敏感性)
                - skin_concerns: 肌肤问题 (抗老/美白/保湿/控油等)
                - budget_range: 预算范围
                - lifestyle: 生活方式
                - preferred_brands: 偏好品牌
                
        返回:
            str: 产品推荐模板，失败时返回None
            
        示例:
            context = {
                'skin_type': '混合性肌肤',
                'skin_concerns': '毛孔粗大',
                'budget_range': '300-500元',
                'lifestyle': '上班族'
            }
        """
        try:
            if hasattr(self, '_prompt_manager') and self._prompt_manager:
                if not self.tenant_id:
                    raise ValueError(f"Sales agent {self.agent_id} requires tenant_id for product recommendation")
                recommendation = await self._prompt_manager.get_product_recommendation_prompt(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    tenant_id=self.tenant_id,
                    context=context or {}
                )
                self.logger.debug(f"获取产品推荐模板成功: {len(recommendation or '')}字符")
                return recommendation
            else:
                # 降级处理：基础推荐模板
                skin_type = context.get('skin_type', '您的肌肤') if context else '您的肌肤'
                return f"根据{skin_type}的特点，我为您精心挑选了以下几款产品，它们非常适合您的需求..."
                
        except Exception as e:
            self.logger.warning(f"获取产品推荐模板失败: {e}")
            return None
    
    async def get_objection_handling_prompt(self, objection_type: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        获取异议处理提示词
        
        销售智能体专用方法，处理客户的不同类型异议。
        
        参数:
            objection_type: 异议类型 (price/quality/need/trust/timing等)
            context: 异议具体内容和客户信息
            
        返回:
            str: 异议处理指导语，失败时返回基础回复
            
        示例:
            objection_type = "price"
            context = {
                'customer_budget': '200元以下',
                'product_price': '399元',
                'customer_concern': '太贵了'
            }
        """
        try:
            if hasattr(self, '_prompt_manager') and self._prompt_manager:
                # 扩展上下文包含异议类型
                full_context = {'objection_type': objection_type}
                if context:
                    full_context.update(context)
                    
                if not self.tenant_id:
                    raise ValueError(f"Sales agent {self.agent_id} requires tenant_id for objection handling")
                objection_prompt = await self._prompt_manager.get_custom_prompt(
                    prompt_type='objection_handling',
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    tenant_id=self.tenant_id,
                    context=full_context
                )
                
                if objection_prompt:
                    self.logger.debug(f"获取异议处理提示词成功: {objection_type}")
                    return objection_prompt
                    
        except Exception as e:
            self.logger.warning(f"获取异议处理提示词失败 {objection_type}: {e}")
        
        # 降级处理：基础异议回应
        basic_responses = {
            'price': '我理解您对价格的考虑。让我为您介绍一下这个产品的价值所在...',
            'quality': '您的担心很有道理。让我详细为您介绍产品的品质保证...',
            'need': '我明白您可能觉得不太需要。让我们一起分析一下您的实际情况...',
            'trust': '建立信任确实需要时间。让我为您展示一些客户的真实反馈...',
            'timing': '时机确实很重要。我们来看看什么时候开始使用效果最佳...'
        }
        
        return basic_responses.get(objection_type, '我理解您的顾虑，让我们一起来讨论一下...') 