"""
智能体编排管理模块

该模块负责使用LangGraph管理多智能体的工作流编排。

核心功能:
- 多智能体编排协调
- 主要处理接口管理
- 模块间协调和错误处理
- 多租户工作流隔离
- 多模态输入处理支持
"""

from langfuse import observe, get_client

from config import mas_config
from models import WorkflowRun, InputType
from core.multimodal.core.processor import MultiModalProcessor
from core.multimodal.core.message import MultiModalMessage
from core.multimodal.core.attachment import AudioAttachment, ImageAttachment
from ..workflows import ChatWorkflow, TestWorkflow
from .entities import WorkflowExecutionModel
from .workflow_builder import WorkflowBuilder
from .state_manager import StateManager
from utils import (
    get_component_logger,
    get_current_datetime,
    get_processing_time,
    flush_traces
)

logger = get_component_logger(__name__)


class Orchestrator:
    """
    多智能体编排器

    使用LangGraph框架协调多个智能体的工作流程。

    采用模块化设计：
    - WorkflowBuilder: 工作流构建和节点处理
    - StateManager: 状态管理和监控
    - MultiModalProcessor: 多模态内容处理

    属性:
        graph: LangGraph工作流图实例
        workflow_builder: 工作流构建器
        state_manager: 状态管理器
        multimodal_processor: 多模态处理器（可选）
    """

    def __init__(self):
        # 初始化模块化组件
        self.state_manager = StateManager()

        # 构建工作流图
        self.workflow_builder = WorkflowBuilder(TestWorkflow)
        self.graph = self.workflow_builder.build_graph()

        # 初始化多模态处理器（如果配置了OpenAI密钥）
        self.multimodal_processor = None
        if mas_config.OPENAI_API_KEY:
            self.multimodal_processor = MultiModalProcessor(
                openai_api_key=mas_config.OPENAI_API_KEY
            )
            logger.info("多模态处理器已初始化")

        logger.info("多智能体编排器初始化完成")

    @observe(name="multi-agent-conversation", as_type="span")
    async def process_conversation(self, workflow: WorkflowRun) -> WorkflowExecutionModel:
        """
        处理客户对话的主入口函数

        通过LangGraph工作流协调所有智能体处理客户输入，
        支持文本和多模态输入（图像、音频）。

        参数:
            workflow: 工作流运行

        返回:
            WorkflowExecutionModel: 处理完成的工作流执行结果
        """
        logger.info(
            f"开始处理对话 - 租户: {workflow.tenant_id}, "
            f"助手: {workflow.assistant_id}, 输入类型: {workflow.type}"
        )
        start_time = get_current_datetime()

        try:
            # 处理多模态附件（如果有）
            if workflow.attachments and workflow.type != InputType.TEXT:
                workflow = await self._process_multimodal_workflow(workflow)

            # 构建初始工作流状态
            initial_state = self.state_manager.create_initial_state(workflow)

            # 执行工作流
            result = await self.graph.ainvoke(initial_state)
            elapsed_time = get_processing_time(start_time)

            logger.info(
                f"对话处理完成 - 耗时: {elapsed_time:.2f}s, "
                f"状态: {'成功' if not result.get('exception_count') else '失败'}"
            )

            # 更新Langfuse追踪信息
            langfuse_trace = get_client()
            langfuse_trace.update_current_trace(
                name=f"conversation-{workflow.workflow_id}",
                user_id=workflow.tenant_id,
                input={
                    "customer_input": workflow.input,
                    "input_type": workflow.type,
                    "tenant_id": workflow.tenant_id,
                    "has_attachments": workflow.attachments is not None
                },
                output={
                    "final_response": result.get("final_response"),
                    "agents_executed": list(result.get("values", {}).keys()),
                    "processing_complete": result.get("processing_complete", False)
                },
                metadata={
                    "tenant_id": workflow.tenant_id,
                    "workflow_type": "multi_agent_conversation",
                    "processing_time": elapsed_time,
                    "input_type": workflow.type,
                    "attachment_count": len(workflow.attachments) if workflow.attachments else 0
                },
                tags=["multi-agent", "conversation", workflow.type]
            )

            # 强制发送追踪数据到Langfuse
            flush_traces()

            # 构建执行结果模型（元数据 + 会话结果）
            return WorkflowExecutionModel(**result)

        except Exception as e:
            logger.error(f"对话处理失败: {e}", exc_info=True)
            # 返回统一错误状态
            raise

    async def _process_multimodal_workflow(self, workflow: WorkflowRun) -> WorkflowRun:
        """
        处理多模态工作流

        处理附件（图像/音频URL），将处理结果整合到工作流输入中。
        图像URL直接传递给视觉模型，音频URL会在处理器中按需下载。

        参数:
            workflow: 包含附件的工作流

        返回:
            WorkflowRun: 更新后的工作流（输入已整合多模态处理结果）
        """
        if not self.multimodal_processor:
            logger.warning("多模态处理器未初始化，跳过多模态处理")
            return workflow

        logger.info(
            f"开始多模态处理 - 附件数量: {len(workflow.attachments)}, "
            f"类型: {workflow.type}"
        )

        try:
            # 创建多模态消息对象
            multimodal_message = MultiModalMessage(
                sender="workflow",
                recipient="multimodal_processor",
                message_type="query",
                tenant_id=workflow.tenant_id,
                customer_id=None,
                conversation_id=str(workflow.thread_id),
                session_id=str(workflow.workflow_id)
            )

            # 添加附件到消息（URL或本地路径）
            for attachment_data in workflow.attachments:
                # 根据类型创建附件对象
                if attachment_data['type'] == 'audio':
                    attachment = AudioAttachment(
                        file_name=attachment_data.get('url', 'audio_file'),
                        content_type=attachment_data.get('content_type', 'audio/mpeg'),
                        file_size=attachment_data.get('file_size', 0),
                        upload_path=attachment_data.get('url'),  # URL或本地路径
                        tenant_id=workflow.tenant_id
                    )
                elif attachment_data['type'] == 'image':
                    attachment = ImageAttachment(
                        file_name=attachment_data.get('url', 'image_file'),
                        content_type=attachment_data.get('content_type', 'image/jpeg'),
                        file_size=attachment_data.get('file_size', 0),
                        upload_path=attachment_data.get('url'),  # URL或本地路径
                        tenant_id=workflow.tenant_id
                    )
                    # 存储source信息用于处理器判断
                    attachment.metadata['source'] = attachment_data.get('source', 'url')
                else:
                    logger.warning(f"不支持的附件类型: {attachment_data['type']}")
                    continue

                multimodal_message.add_attachment(attachment)

            # 处理多模态消息
            processed_message = await self.multimodal_processor.process_multimodal_message(
                multimodal_message
            )

            # 获取整合后的内容
            combined_content = processed_message.combined_content

            if combined_content:
                # 更新工作流输入为整合后的内容
                # 格式: [原始文本提示] + [转录文本] + [图像分析摘要]
                workflow.input = combined_content
                logger.info(f"多模态处理完成，整合内容长度: {len(combined_content)}")
            else:
                logger.warning("多模态处理未产生有效内容，使用原始输入")

            return workflow

        except Exception as e:
            logger.error(f"多模态处理失败: {e}", exc_info=True)
            # 失败时返回原始workflow，使用原始文本输入
            logger.warning("多模态处理失败，回退到原始文本输入")
            return workflow
    
