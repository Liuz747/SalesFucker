"""
后台工作流处理器

该模块提供异步工作流处理功能，支持后台运行多智能体工作流
并通过回调机制将结果发送到用户指定的后端API。

主要功能:
- 后台工作流执行管理
- 状态跟踪和持久化
- 回调处理和重试机制
- 错误处理和审计日志
"""

from uuid import UUID

from config import mas_config
from core.app import Orchestrator
from libs.types import MessageParams
from models import ThreadStatus, WorkflowRun
from services import ThreadService
from schemas.conversation_schema import CallbackPayload
from utils import get_component_logger, get_current_datetime, get_processing_time_ms, ExternalClient


logger = get_component_logger(__name__, "BackgroundProcessor")


class BackgroundWorkflowProcessor:
    """后台工作流处理器"""

    def __init__(self):
        """初始化后台处理器"""
        self.client = ExternalClient()
        
        # 回调端点路径
        self.callback_endpoint = "/api"
    
    async def send_callback(
        self,
        callback_url: str,
        payload: CallbackPayload
    ) -> bool:
        """
        发送回调到用户后端API
        
        参数:
            callback_url: 回调URL地址
            payload: 回调载荷数据
            
        返回:
            bool: 是否发送成功
        """
        try:
            await self.client.make_request(
                "POST",
                callback_url,
                data=payload.model_dump(),
                headers={"User-Agent": "MAS-Background-Processor/1.0"},
                timeout=30.0,
                max_retries=3
            )
            
            logger.info(f"回调成功发送到: {callback_url}")
            return True
                        
        except Exception as e:
            logger.error(f"回调发送异常: {callback_url}, 错误: {str(e)}")
            return False
    
    async def process_workflow_background(
        self,
        orchestrator: Orchestrator,
        run_id: UUID,
        thread_id: UUID,
        input: MessageParams,
        assistant_id: UUID,
        tenant_id: str
    ):
        """在后台处理工作流"""
        start_time = get_current_datetime()

        logger.info(f"开始后台处理工作流 - 运行: {run_id}, 线程: {thread_id}")

        try:
            # 获取线程并更新状态为处理中
            thread = await ThreadService.get_thread(thread_id)
            if thread:
                thread.assistant_id = assistant_id
                thread.status = ThreadStatus.PROCESSING
                await ThreadService.update_thread(thread)
                logger.debug(f"线程状态更新为处理中: {thread_id}")

            # 创建工作流执行模型
            workflow = WorkflowRun(
                workflow_id=run_id,
                thread_id=thread_id,
                assistant_id=assistant_id,
                tenant_id=tenant_id,
                input=input
            )

            # 使用编排器处理消息 - 核心工作流调用
            result = await orchestrator.process_conversation(workflow)

            # 构建工作流数据
            workflow_data = {
                "input": result.input,
                "output": result.output,
                "total_tokens": result.total_tokens
            }

            processing_time = get_processing_time_ms(start_time)
            completed_at = get_current_datetime()

            # 更新线程状态为完成
            if thread:
                thread.status = ThreadStatus.COMPLETED
                await ThreadService.update_thread(thread)
                logger.debug(f"线程状态更新为完成: {thread_id}")

            logger.info(f"工作流处理完成 - 运行: {run_id}, 工作流: {run_id}, 耗时: {processing_time:.2f}ms")

            payload = CallbackPayload(
                run_id=run_id,
                thread_id=thread_id,
                status=ThreadStatus.COMPLETED,
                data=workflow_data,
                processing_time=processing_time,
                finished_at=completed_at.isoformat(),
                metadata={
                    "tenant_id": tenant_id,
                    "assistant_id": assistant_id
                }
            )

            # 发送回调
            if mas_config.CALLBACK_URL:
                callback_url = str(mas_config.CALLBACK_URL).rstrip('/') + self.callback_endpoint
                await self.send_callback(callback_url, payload)
            else:
                logger.warning(f"回调URL未配置，跳过回调发送 - 运行: {run_id}")

        except Exception as e:
            logger.error(f"后台处理失败 - 运行: {run_id}: {e}", exc_info=True)

            # 更新线程状态为失败
            thread = await ThreadService.get_thread(thread_id)
            if thread:
                thread.status = ThreadStatus.FAILED
                await ThreadService.update_thread(thread)
                logger.debug(f"线程状态更新为失败: {thread_id}")
