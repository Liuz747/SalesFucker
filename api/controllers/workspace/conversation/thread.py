"""
对话处理路由器

该模块提供对话处理和管理相关的API端点，包括对话创建、消息处理、
历史查询、状态管理等功能。

端点功能:
- 对话生命周期管理（创建、处理、结束）
- 多模态消息处理（文本、语音、图像）
- 对话历史查询和导出
- 对话状态监控和分析
- 客户档案管理集成
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends

from utils import get_component_logger
from controllers.dependencies import get_request_context
from repositories.thread_repository import ThreadRepository
from models import ThreadOrm, ThreadStatus
from .schema import ThreadCreateRequest
from .workflow import router as workflow_router


# 依赖注入函数
async def get_thread_repository() -> ThreadRepository:
    """获取线程存储库依赖"""
    repository = ThreadRepository()
    await repository.initialize()
    return repository


logger = get_component_logger(__name__, "ConversationRouter")

# 创建路由器
router = APIRouter(prefix="/threads", tags=["conversation-threads"])

router.include_router(workflow_router, prefix="/{thread_id}/runs", tags=["workflows"])

@router.post("")
async def create_thread(
    request: ThreadCreateRequest,
    context = Depends(get_request_context),
    repository = Depends(get_thread_repository)
):
    """
    创建新的对话线程
    
    使用高性能混合存储策略，针对云端PostgreSQL优化。
    性能目标: < 5ms 响应时间
    """
    try:
        # 生成线程ID
        thread_id = request.thread_id or str(uuid.uuid4())

        # 从请求上下文获取租户ID
        tenant_id = context['tenant_id']
        
        # 创建 ORM 对象
        thread_orm = ThreadOrm(
            thread_id=thread_id,
            assistant_id=request.assistant_id,
            tenant_id=tenant_id,
            status=ThreadStatus.ACTIVE
        )
        
        # 传递给 repository
        await repository.create_thread(thread_orm)
        
        return {
            "thread_id": thread_id,
            "metadata": {
                "tenant_id": tenant_id,
                "assistant_id": request.assistant_id
            },
            "status": thread_orm.status,
            "created_at": thread_orm.created_at,
            "updated_at": thread_orm.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"线程创建失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    context = Depends(get_request_context),
    repository = Depends(get_thread_repository)
):
    """
    获取线程详情
    
    从数据库获取线程配置信息。
    """
    try:
        # 使用依赖注入的存储库获取线程
        thread = await repository.get_thread(thread_id)
        
        if not thread:
            raise HTTPException(
                status_code=404, 
                detail=f"线程不存在: {thread_id}"
            )
        
        if str(thread.tenant_id) != context['tenant_id']:
            raise HTTPException(
                status_code=403, 
                detail="租户ID不匹配，无法访问此线程"
            )

        return {
            "thread_id": thread.thread_id,
            "metadata": {"tenant_id": thread.tenant_id},
            "status": thread.status,
            "created_at": thread.created_at,
            "updated_at": thread.updated_at
        }
        
    except Exception as e:
        logger.error(f"线程获取失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

