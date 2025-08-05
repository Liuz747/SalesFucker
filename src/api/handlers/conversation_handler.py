"""
对话处理业务逻辑处理器

该模块实现对话处理相关的业务逻辑，包括对话创建、消息处理、
历史管理、状态监控等功能。

主要功能:
- 对话生命周期管理
- 多模态消息处理协调
- 对话历史查询和导出
- 客户档案集成
- 实时监控和分析
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from fastapi import BackgroundTasks

from src.utils import get_component_logger
from ..schemas.conversations import (
    ConversationRequest,
    ConversationStartRequest,
    ConversationHistoryRequest,
    ConversationExportRequest,
    ConversationResponse,
    ConversationStartResponse,
    ConversationStatusResponse,
    ConversationHistoryResponse,
    ConversationAnalyticsResponse,
    ConversationExportResponse,
    ConversationStatus,
    ComplianceStatus,
    InputType
)
from ..schemas.requests import PaginationRequest
from ..exceptions import (
    ConversationException,
    ValidationException,
    ProcessingException
)

logger = get_component_logger(__name__, "ConversationHandler")


class ConversationHandler:
    """对话处理业务逻辑处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.logger = logger
        # 模拟内存存储，实际应该使用数据库
        self._conversations = {}
        self._conversation_messages = {}
        self._export_tasks = {}
    
    async def start_conversation(
        self,
        request: ConversationStartRequest,
        context: Dict[str, Any],
        orchestrator
    ) -> ConversationStartResponse:
        """
        开始新对话
        
        Args:
            request: 开始对话请求
            context: 请求上下文
            orchestrator: 编排器实例
            
        Returns:
            开始对话响应
        """
        try:
            # 生成对话ID
            conversation_id = f"conv_{request.tenant_id}_{uuid.uuid4().hex[:8]}"
            
            # 初始化对话记录
            conversation = {
                "conversation_id": conversation_id,
                "tenant_id": request.tenant_id,
                "customer_id": request.customer_id,
                "conversation_type": request.conversation_type,
                "status": ConversationStatus.ACTIVE,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "message_count": 0,
                "customer_profile": request.customer_profile or {}
            }
            
            # 保存到内存（实际应保存到数据库）
            self._conversations[conversation_id] = conversation
            self._conversation_messages[conversation_id] = []
            
            # 初始化智能体（通过编排器）
            agents_initialized = await self._initialize_agents(
                conversation_id, request.tenant_id, orchestrator
            )
            
            # 加载客户记忆
            memory_loaded = await self._load_customer_memory(
                request.customer_id, request.tenant_id
            )
            
            # 生成欢迎消息
            welcome_message = await self._generate_welcome_message(
                request.customer_profile, request.conversation_type
            )
            
            self.logger.info(f"对话已开始: {conversation_id}")
            
            return ConversationStartResponse(
                success=True,
                message="对话创建成功",
                data={
                    "conversation_id": conversation_id,
                    "tenant_id": request.tenant_id
                },
                conversation_id=conversation_id,
                welcome_message=welcome_message,
                conversation_status=ConversationStatus.ACTIVE,
                agents_initialized=agents_initialized,
                memory_loaded=memory_loaded,
                customer_profile=request.customer_profile
            )
            
        except Exception as e:
            self.logger.error(f"开始对话失败: {e}", exc_info=True)
            raise ConversationException(f"开始对话失败: {str(e)}")
    
    async def _initialize_agents(
        self, conversation_id: str, tenant_id: str, orchestrator
    ) -> List[str]:
        """初始化智能体"""
        try:
            # 这里应该调用编排器来初始化智能体
            # 模拟返回已初始化的智能体列表
            return [
                f"compliance_{tenant_id}",
                f"sentiment_{tenant_id}",
                f"intent_{tenant_id}",
                f"sales_{tenant_id}",
                f"product_{tenant_id}",
                f"memory_{tenant_id}",
                f"marketing_{tenant_id}",
                f"proactive_{tenant_id}",
                f"suggestion_{tenant_id}"
            ]
        except Exception as e:
            self.logger.warning(f"智能体初始化失败: {e}")
            return []
    
    async def _load_customer_memory(
        self, customer_id: Optional[str], tenant_id: str
    ) -> bool:
        """加载客户记忆"""
        if not customer_id:
            return False
        
        try:
            # 这里应该从记忆系统加载客户历史
            # 模拟返回成功
            return True
        except Exception as e:
            self.logger.warning(f"加载客户记忆失败: {e}")
            return False
    
    async def _generate_welcome_message(
        self, customer_profile: Optional[Dict], conversation_type: str
    ) -> str:
        """生成欢迎消息"""
        welcome_messages = {
            "general": "您好！我是您的美容顾问，很高兴为您服务。有什么美容问题我可以帮助您吗？",
            "consultation": "欢迎来到专业美容咨询！我将为您提供个性化的美容建议。",
            "support": "您好！我是客服助手，很乐意帮助您解决任何问题。",
            "sales": "欢迎！我将为您介绍最适合您的美容产品。"
        }
        
        return welcome_messages.get(conversation_type, welcome_messages["general"])
    
    async def process_message(
        self,
        request: ConversationRequest,
        context: Dict[str, Any],
        orchestrator
    ) -> ConversationResponse:
        """
        处理对话消息
        
        Args:
            request: 对话请求
            context: 请求上下文
            orchestrator: 编排器实例
            
        Returns:
            对话响应
        """
        try:
            conversation_id = request.conversation_id
            if not conversation_id:
                # 如果没有提供对话ID，创建新对话
                conversation_id = f"conv_{request.tenant_id}_{uuid.uuid4().hex[:8]}"
                await self._create_conversation_record(conversation_id, request)
            
            # 验证对话存在
            if conversation_id not in self._conversations:
                raise ConversationException(f"对话不存在: {conversation_id}")
            
            # 记录消息
            message_id = await self._record_message(conversation_id, request)
            
            # 处理消息（通过编排器）
            start_time = datetime.now()
            
            try:
                # 调用编排器处理消息
                result = await orchestrator.process_conversation(
                    customer_input=request.message,
                    customer_id=request.customer_id,
                    input_type=request.input_type.value,
                    context=request.context or {}
                )
                
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds() * 1000
                
                # 提取处理结果
                final_response = result.final_response or "很抱歉，我现在无法处理您的请求。"
                
                # 更新对话状态
                await self._update_conversation_status(
                    conversation_id, result, processing_time
                )
                
                # 记录响应消息
                await self._record_response_message(
                    conversation_id, final_response, result
                )
                
                return ConversationResponse(
                    success=True,
                    message="消息处理成功",
                    data={
                        "message_id": message_id,
                        "processing_time_ms": processing_time
                    },
                    conversation_id=conversation_id,
                    response=final_response,
                    processing_complete=result.processing_complete,
                    conversation_status=ConversationStatus.ACTIVE,
                    compliance_status=ComplianceStatus.APPROVED,
                    agent_responses=result.agent_responses,
                    processing_stats={
                        "processing_time_ms": processing_time,
                        "agents_involved": len(result.agent_responses),
                        "memory_updated": result.memory_updated if hasattr(result, 'memory_updated') else False
                    },
                    error_state=result.error_state,
                    human_escalation=result.human_escalation,
                    escalation_reason=getattr(result, 'escalation_reason', None),
                    llm_provider_used=getattr(result, 'llm_provider_used', None),
                    model_used=getattr(result, 'model_used', None),
                    processing_cost=getattr(result, 'processing_cost', None),
                    token_usage=getattr(result, 'token_usage', None),
                    suggested_actions=self._generate_suggested_actions(result),
                    next_questions=self._generate_next_questions(result)
                )
                
            except Exception as processing_error:
                end_time = datetime.now()
                processing_time = (end_time - start_time).total_seconds() * 1000
                
                # 处理失败情况
                error_response = "很抱歉，系统暂时无法处理您的请求，请稍后重试。"
                
                return ConversationResponse(
                    success=False,
                    message="消息处理失败",
                    data={
                        "message_id": message_id,
                        "error": str(processing_error)
                    },
                    conversation_id=conversation_id,
                    response=error_response,
                    processing_complete=False,
                    conversation_status=ConversationStatus.FAILED,
                    compliance_status=ComplianceStatus.APPROVED,
                    agent_responses={},
                    error_state=str(processing_error),
                    human_escalation=True,
                    escalation_reason="系统处理错误"
                )
                
        except ConversationException:
            raise
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}", exc_info=True)
            raise ProcessingException(f"处理消息失败: {str(e)}")
    
    async def _create_conversation_record(
        self, conversation_id: str, request: ConversationRequest
    ):
        """创建对话记录"""
        conversation = {
            "conversation_id": conversation_id,
            "tenant_id": request.tenant_id,
            "customer_id": request.customer_id,
            "status": ConversationStatus.ACTIVE,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "message_count": 0
        }
        
        self._conversations[conversation_id] = conversation
        self._conversation_messages[conversation_id] = []
    
    async def _record_message(
        self, conversation_id: str, request: ConversationRequest
    ) -> str:
        """记录输入消息"""
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        
        message = {
            "message_id": message_id,
            "sender": "customer",
            "content": request.message,
            "input_type": request.input_type,
            "timestamp": datetime.now(),
            "attachments": request.attachments or []
        }
        
        self._conversation_messages[conversation_id].append(message)
        
        # 更新消息计数
        self._conversations[conversation_id]["message_count"] += 1
        self._conversations[conversation_id]["updated_at"] = datetime.now()
        
        return message_id
    
    async def _record_response_message(
        self, conversation_id: str, response: str, result
    ):
        """记录响应消息"""
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        
        message = {
            "message_id": message_id,
            "sender": "agent",
            "content": response,
            "input_type": InputType.TEXT,
            "timestamp": datetime.now(),
            "agent_responses": result.agent_responses,
            "processing_stats": {
                "processing_complete": result.processing_complete,
                "agents_involved": len(result.agent_responses)
            }
        }
        
        self._conversation_messages[conversation_id].append(message)
        self._conversations[conversation_id]["message_count"] += 1
    
    async def _update_conversation_status(
        self, conversation_id: str, result, processing_time: float
    ):
        """更新对话状态"""
        conversation = self._conversations[conversation_id]
        
        # 更新统计信息
        if "total_processing_time" not in conversation:
            conversation["total_processing_time"] = 0
        conversation["total_processing_time"] += processing_time
        
        # 更新状态
        if result.human_escalation:
            conversation["status"] = ConversationStatus.ESCALATED
        elif result.error_state:
            conversation["status"] = ConversationStatus.FAILED
        else:
            conversation["status"] = ConversationStatus.ACTIVE
        
        conversation["updated_at"] = datetime.now()
    
    def _generate_suggested_actions(self, result) -> List[str]:
        """生成建议操作"""
        suggestions = []
        
        if result.human_escalation:
            suggestions.append("联系人工客服")
        
        if hasattr(result, 'agent_responses'):
            product_response = result.agent_responses.get("product_agent")
            if product_response:
                suggestions.append("查看推荐产品")
        
        return suggestions
    
    def _generate_next_questions(self, result) -> List[str]:
        """生成后续问题建议"""
        return [
            "还有其他问题吗？",
            "需要了解更多产品信息吗？",
            "对我的回答满意吗？"
        ]
    
    async def get_conversation_status(
        self,
        conversation_id: str,
        tenant_id: str,
        include_details: bool = False
    ) -> ConversationStatusResponse:
        """获取对话状态"""
        try:
            if conversation_id not in self._conversations:
                raise ConversationException(f"对话不存在: {conversation_id}")
            
            conversation = self._conversations[conversation_id]
            
            # 验证租户权限
            if conversation["tenant_id"] != tenant_id:
                raise ConversationException("无权访问该对话")
            
            messages = self._conversation_messages.get(conversation_id, [])
            
            return ConversationStatusResponse(
                success=True,
                message="对话状态获取成功",
                data={"conversation_id": conversation_id},
                conversation_id=conversation_id,
                status=conversation["status"],
                tenant_id=conversation["tenant_id"],
                customer_id=conversation.get("customer_id"),
                created_at=conversation["created_at"],
                updated_at=conversation["updated_at"],
                message_count=len(messages),
                total_processing_time=conversation.get("total_processing_time", 0),
                active_agents=["sales", "product", "memory"],  # 模拟数据
                pending_actions=[],
                average_response_time=850.5,  # 模拟数据
                satisfaction_score=4.2 if include_details else None
            )
            
        except ConversationException:
            raise
        except Exception as e:
            self.logger.error(f"获取对话状态失败: {e}", exc_info=True)
            raise ValidationException(f"获取对话状态失败: {str(e)}")
    
    async def end_conversation(
        self,
        conversation_id: str,
        tenant_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """结束对话"""
        try:
            if conversation_id not in self._conversations:
                raise ConversationException(f"对话不存在: {conversation_id}")
            
            conversation = self._conversations[conversation_id]
            
            # 验证租户权限
            if conversation["tenant_id"] != tenant_id:
                raise ConversationException("无权访问该对话")
            
            # 更新状态
            conversation["status"] = ConversationStatus.COMPLETED
            conversation["end_reason"] = reason
            conversation["ended_at"] = datetime.now()
            conversation["updated_at"] = datetime.now()
            
            self.logger.info(f"对话已结束: {conversation_id}")
            
            return {
                "success": True,
                "message": "对话已结束",
                "conversation_id": conversation_id,
                "ended_at": conversation["ended_at"].isoformat()
            }
            
        except ConversationException:
            raise
        except Exception as e:
            self.logger.error(f"结束对话失败: {e}", exc_info=True)
            raise ValidationException(f"结束对话失败: {str(e)}")
    
    # 其他方法的简化实现...
    async def get_conversation_history(self, request: ConversationHistoryRequest, pagination: PaginationRequest):
        """获取对话历史 - 简化实现"""
        return ConversationHistoryResponse(
            success=True, message="历史获取成功", data=[], conversations=[], 
            total_conversations=0, active_conversations=0, 
            date_range={"start": datetime.now(), "end": datetime.now()},
            filter_summary={}, total=0, page=1, size=10, has_next=False
        )
    
    async def get_conversation_messages(self, conversation_id: str, tenant_id: str, pagination: PaginationRequest, include_attachments: bool, include_analysis: bool):
        """获取对话消息 - 简化实现"""
        return {"messages": [], "total": 0}
    
    async def get_conversation_analytics(self, tenant_id: str, days: int, customer_id: Optional[str], agent_type: Optional[str]):
        """获取对话分析 - 简化实现"""
        return ConversationAnalyticsResponse(
            success=True, message="分析获取成功", data={},
            total_conversations=100, total_messages=500,
            conversation_distribution={}, peak_hours=[],
            average_response_time=850.5, completion_rate=0.85,
            satisfaction_scores={}, agent_performance={},
            cost_analysis={}, trends={}
        )
    
    async def export_conversations(self, request: ConversationExportRequest, background_tasks: BackgroundTasks):
        """导出对话记录 - 简化实现"""
        export_id = f"export_{uuid.uuid4().hex[:8]}"
        return ConversationExportResponse(
            success=True, message="导出任务已创建", data={},
            export_id=export_id, download_url=None,
            total_conversations=10, total_messages=50, file_size_mb=2.5,
            export_status="processing", estimated_completion=datetime.now() + timedelta(minutes=5)
        )
    
    async def get_export_status(self, export_id: str, tenant_id: str):
        """获取导出状态 - 简化实现"""
        return {"export_id": export_id, "status": "completed", "download_url": "https://example.com/download"}
    
    async def get_customer_conversations(self, customer_id: str, tenant_id: str, pagination: PaginationRequest, status: Optional[ConversationStatus]):
        """获取客户对话 - 简化实现"""
        return {"conversations": [], "total": 0}
    
    async def get_customer_summary(self, customer_id: str, tenant_id: str, days: int):
        """获取客户摘要 - 简化实现"""
        return {"customer_id": customer_id, "summary": "客户摘要"}
    
    async def get_active_conversations(self, tenant_id: str, pagination: PaginationRequest):
        """获取活跃对话 - 简化实现"""
        return {"conversations": [], "total": 0}
    
    async def get_realtime_metrics(self, tenant_id: str):
        """获取实时指标 - 简化实现"""
        return {"active_conversations": 5, "messages_per_minute": 12}
    
    async def escalate_conversation(self, conversation_id: str, tenant_id: str, reason: str, priority: str):
        """升级对话 - 简化实现"""
        return {"success": True, "escalated": True}
    
    async def submit_feedback(self, conversation_id: str, tenant_id: str, rating: int, feedback: Optional[str]):
        """提交反馈 - 简化实现"""
        return {"success": True, "feedback_recorded": True}
    
    async def delete_conversation(self, conversation_id: str, tenant_id: str, permanent: bool):
        """删除对话 - 简化实现"""
        return {"success": True, "deleted": True}