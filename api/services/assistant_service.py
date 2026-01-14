"""
AI员工处理器

该模块提供AI员工管理的业务逻辑处理，包括助理的创建、查询、更新、
配置和统计等功能。负责协调数据存储、权限验证和业务规则执行。

主要功能:
- 助理生命周期管理
- 配置和权限管理
- 统计和分析功能
- 数据验证和业务规则
"""

import asyncio
from uuid import UUID

from libs.exceptions import (
    BaseHTTPException,
    AssistantNotFoundException,
    TenantNotFoundException,
    TenantValidationException
)
from libs.factory import infra_registry
from libs.types import AccountStatus
from models import AssistantModel
from repositories.assistant_repo import AssistantRepository
from schemas import AssistantCreateRequest, AssistantUpdateRequest
from utils import get_component_logger

logger = get_component_logger(__name__, "AssistantService")


class AssistantService:
    """
    AI员工处理器
    
    处理AI员工相关的业务逻辑，包括CRUD操作、配置管理和统计分析。
    """

    @staticmethod
    async def create_assistant(request: AssistantCreateRequest) -> AssistantModel:
        """
        创建新的AI员工

        参数:
            request: 助理创建请求

        返回:
            AssistantModel: 创建的助理模型
        """
        try:
            async with infra_registry.get_db_session() as session:
                # 1. 创建助理数据
                assistant_model = AssistantModel(
                    assistant_name=request.assistant_name,
                    nickname=request.nickname,
                    address=request.address,
                    sex=request.sex,
                    tenant_id=request.tenant_id,
                    status=AccountStatus.ACTIVE,
                    personality=request.personality,
                    occupation=request.occupation,
                    voice_id=request.voice_id,
                    voice_file=request.voice_file,
                    industry=request.industry,
                    profile=request.profile or {},
                    is_active=True,
                    last_active_at=None
                )

                # 2. 存储助理数据
                assistant_orm = await AssistantRepository.insert_assistant(assistant_model, session)
                if not assistant_orm:
                    raise Exception("AssistantRepository.insert_assistant failed")

            # 4. 获取数据库生成的 assistant_id 并转换为业务模型
            created_assistant = assistant_orm.to_business_model()
            logger.info(f"助理创建成功: {created_assistant.assistant_id}")

            # 5. 处理语音克隆（如果提供了音频URL和voice_id）
            if created_assistant.voice_file and created_assistant.voice_id:
                try:
                    from services.audio_service import AudioService

                    # 克隆并激活声音（voice_file应该是音频文件的URL）
                    clone_result = await AudioService.clone_and_activate_voice(
                        voice_file=created_assistant.voice_file,
                        voice_id=created_assistant.voice_id,
                        demo_text="你好，我是你的AI助理。"
                    )
                    logger.info(f"声音克隆并激活成功: {clone_result}")

                except Exception as e:
                    logger.error(f"语音克隆失败: {e}")

            # 6. 异步更新缓存
            redis_client = infra_registry.get_cached_clients().redis
            asyncio.create_task(AssistantRepository.update_assistant_cache(
                created_assistant,
                redis_client
            ))

            return created_assistant

        except TenantNotFoundException:
            raise
        except Exception as e:
            logger.error(f"助理创建失败: {e}")
            raise

    @staticmethod
    async def get_assistant_by_id(
        assistant_id: UUID,
        use_cache: bool = True
    ) -> AssistantModel:
        """
        获取助理详细信息
        
        参数:
            assistant_id: 助理ID
            use_cache: 是否使用缓存
            
        返回:
            AssistantResponse: 助理信息
        """
        redis_client = infra_registry.get_cached_clients().redis
        if use_cache:
            assistant_model = await AssistantRepository.get_assistant_cache(assistant_id, redis_client)
            if assistant_model:
                return assistant_model
            logger.info("缓存失效，数据回源")

        try:
            async with infra_registry.get_db_session() as session:
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                if not assistant_orm:
                    raise AssistantNotFoundException(assistant_id)

                assistant_model = assistant_orm.to_business_model()
            logger.info(f"助理详情查询成功: {assistant_id}")
            asyncio.create_task(AssistantRepository.update_assistant_cache(assistant_model, redis_client))
            return assistant_model
        except Exception as e:
            logger.error(f"助理详情查询失败: {e}")
            raise

    @staticmethod
    async def update_assistant(
        tenant_id: str,
        assistant_id: UUID,
        request: AssistantUpdateRequest
    ) -> AssistantModel:
        """
        更新助理信息

        参数:
            assistant_id: 助理ID
            request: 更新请求

        返回:
            AssistantModel: 更新后的助理信息
        """
        try:
            async with infra_registry.get_db_session() as session:
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                if not assistant_orm:
                    raise AssistantNotFoundException(assistant_id)

                if assistant_orm.tenant_id != tenant_id:
                    raise TenantValidationException(tenant_id, reason=f"助理不属于当前租户")

                # 仅更新用户提供的字段
                update_data = request.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    setattr(assistant_orm, field, value)

                # 使用返回的已刷新ORM对象，避免会话分离问题
                assistant_orm = await AssistantRepository.update_assistant(assistant_orm, session)
                logger.info(f"助理更新成功: {assistant_id}")
                assistant_model = assistant_orm.to_business_model()

            # 更新缓存数据
            redis_client = infra_registry.get_cached_clients().redis
            asyncio.create_task(AssistantRepository.update_assistant_cache(assistant_model, redis_client))

            return assistant_model

        except BaseHTTPException:
            raise
        except Exception as e:
            logger.error(f"助理更新失败: {e}")
            raise

    @staticmethod
    async def delete_assistant(
        tenant_id: str,
        assistant_id: UUID,
        force: bool = False
    ) -> bool:
        """
        删除助理

        参数:
            tenant_id: 租户ID
            assistant_id: 助理ID
            force: 是否强制删除

        返回:
            bool: 是否删除成功
        """
        try:
            async with infra_registry.get_db_session() as session:
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                if not assistant_orm:
                    raise AssistantNotFoundException(assistant_id)

                # 验证租户所有权
                if assistant_orm.tenant_id != tenant_id:
                    raise TenantValidationException(tenant_id, reason=f"助理不属于当前租户")

                # TODO: 检查是否有活跃对话
                current_customers = 0
                if current_customers > 0 and not force:
                    raise ValueError("助理有活跃对话，需要强制删除标志")

                await AssistantRepository.delete(assistant_id, session)

            # 删除缓存
            redis_client = infra_registry.get_cached_clients().redis
            asyncio.create_task(AssistantRepository.delete_assistant_cache(assistant_id, redis_client))

            logger.info(f"助理删除成功: {assistant_id}")
            return True

        # TODO: Check how to handle this value error
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"助理删除失败: {e}")
            raise
