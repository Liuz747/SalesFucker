"""
智能体API端点

用于智能体交互和测试的REST API端点。
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from src.agents import get_orchestrator
from src.api.multi_llm_handlers import MultiLLMAPIHandler
from src.api.agent_handlers import AgentTestHandler

logger = logging.getLogger(__name__)

# 全局多LLM处理器实例
multi_llm_handler = MultiLLMAPIHandler()
agent_test_handler = AgentTestHandler()

router = APIRouter(prefix="/agents", tags=["agents"])


# 请求/响应模型
class ConversationRequest(BaseModel):
    """对话请求模型。"""
    tenant_id: str = Field(description="租户标识符")
    customer_id: Optional[str] = Field(None, description="客户标识符")
    message: str = Field(description="客户消息")
    input_type: str = Field("text", description="输入类型（文本、语音、图像）")
    preferred_provider: Optional[str] = Field(None, description="首选LLM供应商")
    model_name: Optional[str] = Field(None, description="指定模型名称")
    routing_strategy: Optional[str] = Field(None, description="路由策略")


class ConversationResponse(BaseModel):
    """对话处理响应模型。"""
    conversation_id: str
    response: str
    processing_complete: bool
    error_state: Optional[str] = None
    agent_responses: Dict[str, Any] = Field(default_factory=dict)
    compliance_status: str = Field("approved")
    human_escalation: bool = False
    llm_provider_used: Optional[str] = Field(None, description="实际使用的LLM供应商")
    model_used: Optional[str] = Field(None, description="实际使用的模型")
    processing_cost: Optional[float] = Field(None, description="处理成本")
    token_usage: Optional[Dict[str, int]] = Field(None, description="令牌使用统计")


class AgentStatusResponse(BaseModel):
    """智能体状态响应模型。"""
    agent_id: str
    is_active: bool
    messages_processed: int
    errors: int
    last_activity: Optional[str] = None


class TenantAgentsResponse(BaseModel):
    """租户智能体列表响应模型。"""
    tenant_id: str
    agents: List[AgentStatusResponse]
    total_agents: int




@router.post("/conversation", response_model=ConversationResponse)
async def process_conversation(request: ConversationRequest):
    """
    通过完整的9智能体多智能体系统处理客户对话。
    
    此端点协调完整的LLM驱动对话流程：
    1. 合规智能体：LLM+规则混合安全验证
    2. 情感分析智能体：AI情绪检测和满意度评分
    3. 意图分析智能体：AI意图分类与字段提取
    4. 销售智能体：动态LLM个性化响应
    5. 产品专家智能体：AI产品推荐
    6. 记忆智能体：客户档案管理和持久化
    7. 市场策略协调器：基于细分的策略选择
    8. 主动智能体：行为触发的机会识别
    9. AI建议智能体：人机协作和升级决策
    """
    try:
        # 确保租户的智能体存在
        await agent_test_handler.get_tenant_agents(request.tenant_id)
        
        # 获取租户的编排器
        orchestrator = get_orchestrator(request.tenant_id)
        
        # 处理对话
        result = await orchestrator.process_conversation(
            customer_input=request.message,
            customer_id=request.customer_id,
            input_type=request.input_type
        )
        
        # 使用多LLM系统增强响应
        llm_enhancements = await multi_llm_handler.enhance_conversation_with_llm_routing(
            request.model_dump(), result
        )
        
        # 从销售智能体提取响应或使用备用响应
        final_response = result.final_response
        if not final_response and result.agent_responses.get("sales_agent_" + request.tenant_id):
            final_response = result.agent_responses[f"sales_agent_{request.tenant_id}"]["response"]
        
        if not final_response:
            final_response = "感谢您的消息！我能为您的美容需求提供什么帮助吗？"
        
        return ConversationResponse(
            conversation_id=result.conversation_id,
            response=final_response,
            processing_complete=result.processing_complete,
            error_state=result.error_state,
            agent_responses=result.agent_responses,
            compliance_status=result.compliance_result.get("status", "approved"),
            human_escalation=result.human_escalation,
            llm_provider_used=llm_enhancements.get("llm_provider_used"),
            model_used=llm_enhancements.get("model_used"),
            processing_cost=llm_enhancements.get("processing_cost"),
            token_usage=llm_enhancements.get("token_usage")
        )
        
    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"对话处理失败: {str(e)}"
        )


@router.get("/tenant/{tenant_id}/status", response_model=TenantAgentsResponse)
async def get_tenant_agent_status(tenant_id: str):
    """获取特定租户的所有智能体状态。"""
    try:
        # 确保智能体存在
        agents = await agent_test_handler.get_tenant_agents(tenant_id)
        
        agent_statuses = []
        for _, agent in agents.items():
            if agent:
                status = AgentStatusResponse(
                    agent_id=agent.agent_id,
                    is_active=agent.is_active,
                    messages_processed=agent.processing_stats["messages_processed"],
                    errors=agent.processing_stats["errors"],
                    last_activity=agent.processing_stats["last_activity"].isoformat() 
                        if agent.processing_stats["last_activity"] else None
                )
                agent_statuses.append(status)
        
        return TenantAgentsResponse(
            tenant_id=tenant_id,
            agents=agent_statuses,
            total_agents=len(agent_statuses)
        )
        
    except Exception as e:
        logger.error(f"获取智能体状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取智能体状态失败: {str(e)}"
        )
















 