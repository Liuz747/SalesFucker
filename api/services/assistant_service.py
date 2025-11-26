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
from typing import Optional
from uuid import UUID

from infra.db import database_session
from libs.types import AccountStatus
from libs.factory import infra_registry
from models import AssistantModel
from repositories.assistant_repo import AssistantRepository
from repositories.tenant_repo import TenantRepository
from schemas.exceptions import TenantNotFoundException, AssistantNotFoundException
from schemas.assistants_schema import AssistantCreateRequest, AssistantUpdateRequest
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
            async with database_session() as session:
                # 1. 先查询 tenant 是否存在
                tenant_orm = await TenantRepository.get_tenant_by_id(request.tenant_id, session)
                if not tenant_orm:
                    raise TenantNotFoundException(tenant_id=request.tenant_id)

                # 2. 创建助理数据
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

                # 3. 存储助理数据
                assistant_orm = await AssistantRepository.insert_assistant(assistant_model, session)
                if not assistant_orm:
                    raise Exception("AssistantRepository.insert_assistant failed")

            # 4. 获取数据库生成的 assistant_id 并转换为业务模型
            created_assistant = assistant_orm.to_business_model()
            logger.info(f"助理创建成功: {created_assistant.assistant_id}")

            # 5. 异步更新缓存
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
    ) -> Optional[AssistantModel]:
        """
        获取助理详细信息
        
        参数:
            assistant_id: 助理ID
            use_cache: 是否使用缓存
            
        返回:
            Optional[AssistantResponse]: 助理信息
        """
        redis_client = infra_registry.get_cached_clients().redis
        if use_cache:
            assistant_model = await AssistantRepository.get_assistant_cache(assistant_id, redis_client)
            if assistant_model:
                return assistant_model
            logger.info("缓存失效，数据回源")

        try:
            async with database_session() as session:
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
        assistant_id: UUID,
        request: AssistantUpdateRequest
    ) -> Optional[AssistantModel]:
        """
        更新助理信息

        参数:
            assistant_id: 助理ID
            request: 更新请求

        返回:
            Optional[AssistantModel]: 更新后的助理信息
        """
        try:
            async with database_session() as session:
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                if not assistant_orm:
                    raise AssistantNotFoundException(assistant_id)

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

        except AssistantNotFoundException:
            raise
        except Exception as e:
            logger.error(f"助理更新失败: {e}")
            raise

    @staticmethod
    async def delete_assistant(assistant_id: UUID, force: bool = False) -> bool:
        """
        删除助理

        参数:
            assistant_id: 助理ID
            force: 是否强制删除

        返回:
            bool: 是否删除成功
        """
        try:
            async with database_session() as session:
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                if not assistant_orm:
                    return False

                # todo 检查是否有活跃对话
                current_customers = 0
                if current_customers > 0 and not force:
                    raise ValueError("助理有活跃对话，需要强制删除标志")

                flag = await AssistantRepository.delete(assistant_id, session)
                if not flag:
                    raise Exception("删除失败，请咨询管理员")

            # 删除缓存
            redis_client = infra_registry.get_cached_clients().redis
            asyncio.create_task(AssistantRepository.delete_assistant_cache(assistant_id, redis_client))

            logger.info(f"助理删除成功: {assistant_id}")
            return True

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"助理删除失败: {e}")
            raise
