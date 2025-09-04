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

import uuid
from typing import Optional

from utils import get_component_logger, get_current_datetime, get_processing_time_ms, ExternalClient
from controllers.dependencies import get_orchestrator_service
from repositories.thread_repository import ThreadRepository
from models.conversation import ConversationStatus
from .schema import CallbackPayload, WorkflowData, InputContent


logger = get_component_logger(__name__, "BackgroundProcessor")


class BackgroundWorkflowProcessor:
    """后台工作流处理器"""

    def __init__(self, repository: ThreadRepository):
        """初始化后台处理器"""
        self.client = ExternalClient()
        self.repository = repository
    
    async def send_callback(
        self,
        callback_url: str,
        payload: CallbackPayload
    ) -> tuple[bool, Optional[str]]:
        """
        发送回调到用户后端API
        
        参数:
            callback_url: 回调URL地址
            payload: 回调载荷数据
            
        返回:
            tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        try:
            # 使用 ExternalClient 发送回调
            await self.client.make_request(
                "POST",
                callback_url,
                data=payload.model_dump(),
                headers={"User-Agent": "MAS-Background-Processor/1.0"},
                timeout=30.0,
                max_retries=3
            )
            
            logger.info(f"回调成功发送到: {callback_url}")
            return True, None
                        
        except Exception as e:
            error_msg = f"回调发送异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def process_workflow_background(
        self,
        run_id: str,
        thread_id: str,
        input: InputContent,
        assistant_id: str,
        callback_url: Optional[str] = None,
        customer_id: Optional[str] = None,
        input_type: str = "text"
    ):
        """在后台处理工作流"""
        start_time = get_current_datetime()

        logger.info(f"开始后台处理工作流 - 运行: {run_id}, 线程: {thread_id}")

        try:
            # 获取线程并更新状态为处理中
            thread = await self.repository.get_thread(thread_id)
            if thread:
                thread.status = ConversationStatus.PROCESSING
                await self.repository.update_thread(thread)
                logger.debug(f"线程状态更新为处理中: {thread_id}")

            # 获取租户专用编排器实例
            orchestrator = get_orchestrator_service(thread.metadata.tenant_id)

            # 使用编排器处理消息 - 核心工作流调用
            result = await orchestrator.process_conversation(
                customer_input=input.content,
                customer_id=customer_id,
                input_type=input_type
            )

            # 构建工作流数据
            workflow_data = []
            for agent_type, agent_response in result.agent_responses.items():
                workflow_data.append(
                    WorkflowData(
                        type=agent_type,
                        content=agent_response
                    )
                )

            processing_time = get_processing_time_ms(start_time)
            completed_at = get_current_datetime()

            # 更新线程状态为完成
            thread = await self.repository.get_thread(thread_id)
            if thread:
                thread.status = ConversationStatus.COMPLETED
                await self.repository.update_thread(thread)
                logger.debug(f"线程状态更新为完成: {thread_id}")

            logger.info(f"工作流处理完成 - 运行: {run_id}, 耗时: {processing_time:.2f}ms")

            # 如果有回调URL，发送回调
            if callback_url:
                payload = CallbackPayload(
                    run_id=uuid.UUID(run_id),
                    thread_id=uuid.UUID(thread_id),
                    status=ConversationStatus.COMPLETED,
                    data=workflow_data,
                    processing_time=processing_time,
                    completed_at=completed_at,
                    metadata={
                        "tenant_id": thread.metadata.tenant_id,
                        "assistant_id": assistant_id
                    }
                )

                success, error = await self.send_callback(callback_url, payload)

                if not success:
                    logger.error(f"回调发送失败 - 运行: {run_id}, 错误: {error}")
                else:
                    logger.info(f"回调发送成功 - 运行: {run_id}")

        except Exception as e:
            logger.error(f"后台处理失败 - 运行: {run_id}: {e}", exc_info=True)

            # 更新线程状态为失败
            thread = await self.repository.get_thread(thread_id)
            if thread:
                thread.status = ConversationStatus.FAILED
                await self.repository.update_thread(thread)
                logger.debug(f"线程状态更新为失败: {thread_id}")
