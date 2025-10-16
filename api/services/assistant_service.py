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
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import HTTPException

from infra.cache import get_redis_client
from infra.db import database_session
from models.prompts import PromptsModel
from repositories.prompts_repo import PromptsRepository
from repositories.tenant_repo import TenantRepository
from schemas.exceptions import TenantNotFoundException, AssistantConflictException, AssistantNotFoundException
from schemas.assistants_schema import (
    AssistantCreateRequest, AssistantUpdateRequest, AssistantConfigRequest,
    AssistantListRequest, AssistantListResponse,
    AssistantStatsResponse, AssistantOperationResponse,
    AssistantStatus, PersonalityType, ExpertiseLevel
)
from models.assistant import AssistantModel

from repositories.assistant_repo import AssistantRepository
from services.prompts_services import PromptService
from utils import get_component_logger, get_current_datetime

logger = get_component_logger(__name__, "AssistantService")


class AssistantService:
    """
    AI员工处理器
    
    处理AI员工相关的业务逻辑，包括CRUD操作、配置管理和统计分析。
    """

    def __init__(self):
        """初始化助理处理器"""
        self.logger = get_component_logger(__name__)

        # 模拟数据存储（实际应用中应该使用数据库）
        self._assistants_store: Dict[str, Dict[str, Any]] = {}
        self._assistant_stats: Dict[str, Dict[str, Any]] = {}

        # 初始化提示词处理器
        self.prompt_handler = PromptService()

        self.logger.info("AI员工处理器初始化完成")

    async def create_assistant(self, request: AssistantCreateRequest) -> AssistantModel:
        """
        创建新的AI员工
        
        参数:
            request: 助理创建请求
            
        返回:
            AssistantResponse: 创建结果
        """

        prompts_id = uuid.UUID
        try:
            async with database_session() as session:
                # 1. 先查询 tenant 是否存在
                tenant_orm = await TenantRepository.get_tenant_by_id(request.tenant_id, session)
                if not tenant_orm:
                    # 需要 raise 个错误
                    raise TenantNotFoundException(tenant_id=request.tenant_id)

                # 2. 再查询 assistant 是否存在
                assistant_orm = await AssistantRepository.get_assistant_by_id(request.assistant_id, session)
                if assistant_orm:
                    # 需要 raise 个错误
                    raise AssistantConflictException(assistant_id=request.assistant_id)

                # 创建助理数据
                now = get_current_datetime()
                assistant_model = AssistantModel(
                    assistant_id=request.assistant_id,
                    assistant_name=request.assistant_name,
                    tenant_id=request.tenant_id,
                    assistant_status="inactive",
                    personality_type=request.personality_type,
                    expertise_level=request.expertise_level,
                    sales_style=request.sales_style or self._get_default_sales_style(request.personality_type),
                    voice_tone=request.voice_tone or self._get_default_voice_tone(request.personality_type),
                    specializations=request.specializations or [],
                    working_hours=request.working_hours or self._get_default_working_hours(),
                    max_concurrent_customers=request.max_concurrent_customers,
                    permissions=request.permissions or self._get_default_permissions(request.expertise_level),
                    profile=request.profile or {},
                    created_at=now,
                    updated_at=now,
                    is_active=True,
                    last_active_at=None,
                    registered_devices=[]
                )

                # 存储助理数据
                status = await AssistantRepository.insert_assistant(assistant_model, session)
                if not status:
                    raise Exception(f"AssistantRepository.insert_assistant is error. {request.assistant_id}")
                redis_client = await get_redis_client()
                asyncio.create_task(AssistantRepository.update_assistant_cache(
                    assistant_model,
                    redis_client
                ))

                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_model.assistant_id, session)

                if request.prompt_config:

                    # 处理提示词配置（如果提供）
                    try:
                        promptsModel = PromptsModel(
                            tenant_id=request.tenant_id,
                            assistant_id=assistant_model.assistant_id,
                            personality_prompt=request.personality_type,
                            greeting_prompt=request.prompt_config.greeting_prompt,
                            product_recommendation_prompt=request.prompt_config.product_recommendation_prompt,
                            objection_handling_prompt=request.prompt_config.objection_handling_prompt,
                            closing_prompt=request.prompt_config.closing_prompt,
                            context_instructions=request.prompt_config.context_instructions,
                            llm_parameters=request.prompt_config.llm_parameters,
                            safety_guidelines=request.prompt_config.safety_guidelines,
                            forbidden_topics=request.prompt_config.forbidden_topics,
                            brand_voice=request.prompt_config.brand_voice,
                            product_knowledge=request.prompt_config.product_knowledge,
                            version=request.prompt_config.version,
                            is_active=request.prompt_config.is_active,
                            created_at=now,
                            updated_at=now,
                        )
                        prompts_id = await PromptsRepository.insert_prompts(promptsModel.to_orm(), session)
                        prompts_orm = await PromptsRepository.get_prompts_by_id(prompts_id, session)

                        promptsModel.id = prompts_id

                        asyncio.create_task(PromptsRepository.update_prompts_cache(
                            promptsModel,
                            redis_client
                        ))
                        self.logger.info(f"助理 {request.assistant_id} 提示词配置创建成功")
                    except Exception as e:
                        self.logger.warning(f"助理 {request.assistant_id} 提示词配置创建失败: {e}")
                        # 不阻止助理创建，只记录警告
                self.logger.info(f"助理创建成功: {request.assistant_id}")

            async with database_session() as session:
                new_prompts_orm = await PromptsRepository.get_prompts_by_id(prompts_id, session)
                new_prompts_model = new_prompts_orm.to_model()
                new_assistant_orm = await AssistantRepository.get_assistant_by_id(request.assistant_id, session)
                new_assistant = new_assistant_orm.to_business_model()
                new_assistant.prompts_model_list = new_prompts_model

        except Exception as e:
            self.logger.error(f"助理创建失败: {e}")
            raise

        # return assistant_orm.to_business_model()

        return AssistantModel(
            code=0,
            message="助理创建成功",
            data=new_assistant,
            # **assistant_data,
            # current_customers=0,
            # total_conversations=0,
            # average_rating=0.0
        )

    async def list_assistants(self, request: AssistantListRequest) -> AssistantListResponse:
        """
        获取助理列表
        
        参数:
            request: 列表查询请求
            
        返回:
            AssistantListResponse: 助理列表
        """
        try:
            # 筛选租户助理
            tenant_assistants = {
                k: v for k, v in self._assistants_store.items()
                if v["tenant_id"] == request.tenant_id
            }

            # 应用筛选条件
            filtered_assistants = []
            for key, assistant in tenant_assistants.items():
                # 状态筛选
                if request.status and assistant["status"] != request.status:
                    continue

                # 个性类型筛选
                if request.personality_type and assistant["personality_type"] != request.personality_type:
                    continue

                # 专业等级筛选
                if request.expertise_level and assistant["expertise_level"] != request.expertise_level:
                    continue

                # 专业领域筛选
                if request.specialization:
                    if request.specialization not in assistant["specializations"]:
                        continue

                # 搜索筛选
                if request.search:
                    search_text = request.search.lower()
                    if not (search_text in assistant["assistant_name"].lower() or
                            search_text in assistant["assistant_id"].lower()):
                        continue

                # 添加统计信息
                if request.include_stats:
                    stats = self._assistant_stats.get(key, {})
                    assistant = {**assistant, **stats}

                filtered_assistants.append(assistant)

            # 排序
            reverse = request.sort_order == "desc"
            if request.sort_by == "created_at":
                filtered_assistants.sort(key=lambda x: x["created_at"], reverse=reverse)
            elif request.sort_by == "assistant_name":
                filtered_assistants.sort(key=lambda x: x["assistant_name"], reverse=reverse)
            elif request.sort_by == "expertise_level":
                level_order = {"junior": 1, "intermediate": 2, "senior": 3, "expert": 4}
                filtered_assistants.sort(
                    key=lambda x: level_order.get(x["expertise_level"], 0),
                    reverse=reverse
                )

            # 分页
            total_count = len(filtered_assistants)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            paginated_assistants = filtered_assistants[start_idx:end_idx]

            # 计算统计信息
            status_distribution = {}
            expertise_distribution = {}

            for assistant in tenant_assistants.values():
                status = assistant["status"]
                expertise = assistant["expertise_level"]
                status_distribution[status] = status_distribution.get(status, 0) + 1
                expertise_distribution[expertise] = expertise_distribution.get(expertise, 0) + 1

            active_count = status_distribution.get(AssistantStatus.ACTIVE, 0)

            self.logger.info(f"助理列表查询成功: 返回{len(paginated_assistants)}/{total_count}条记录")

            return AssistantListResponse(
                success=True,
                message="助理列表查询成功",
                data=paginated_assistants,
                assistants=paginated_assistants,
                total_assistants=len(tenant_assistants),
                active_assistants=active_count,
                status_distribution=status_distribution,
                expertise_distribution=expertise_distribution,
                filter_summary={
                    "total": total_count,
                    "filtered": len(filtered_assistants)
                },

                # todo 不确定分页信息使用哪些属性，先按照程序能运行写了
                total=total_count,
                page=request.page,
                page_size=request.page_size,
                pages=(total_count + request.page_size - 1) // request.page_size,

                pagination={}
            )

        except Exception as e:
            self.logger.error(f"助理列表查询失败: {e}")
            raise

    async def get_assistant_by_id(
            self,
            assistant_id: str,
            use_cache: bool = True
            # tenant_id: str,
            # include_stats: bool = False,
            # include_config: bool = True
    ) -> Optional[AssistantModel]:
        """
        获取助理详细信息
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            include_stats: 是否包含统计信息
            include_config: 是否包含配置信息
            
        返回:
            Optional[AssistantResponse]: 助理信息
        """
        if use_cache:
            redis_client = await get_redis_client()
            assistant_model = await AssistantRepository.get_assistant_cache(assistant_id, redis_client)
            if assistant_model:
                return assistant_model

        try:
            if use_cache:
                # todo 上线后修改日志等级
                logger.info("缓存失效，数据回源")
            async with database_session() as session:
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                if not assistant_orm:
                    raise AssistantNotFoundException(assistant_id)

                self.logger.info(f"助理详情查询成功: {assistant_id}")
                assistant_model = assistant_orm.to_business_model()
                await AssistantRepository.update_assistant_cache_4_task(assistant_model)
                return assistant_model
        except Exception as e:
            self.logger.error(f"助理详情查询失败: {e}")
            raise

    async def update_assistant(
            self,
            assistant_id: str,
            request: AssistantUpdateRequest
    ) -> Optional[AssistantModel]:
        """
        更新助理信息
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            request: 更新请求
            
        返回:
            Optional[AssistantResponse]: 更新后的助理信息
        """
        try:

            async with database_session() as session:
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                if not assistant_orm:
                    raise AssistantNotFoundException(assistant_id)

                # 更新字段
                # update_fields = {}
                if request.assistant_name is not None:
                    # update_fields["assistant_name"] = request.assistant_name
                    assistant_orm.assistant_name = request.assistant_name
                if request.personality_type is not None:
                    # update_fields["personality_type"] = request.personality_type
                    assistant_orm.assistant_personality_type = request.personality_type
                if request.expertise_level is not None:
                    # update_fields["expertise_level"] = request.expertise_level
                    assistant_orm.assistant_expertise_level = request.expertise_level
                if request.sales_style is not None:
                    # update_fields["sales_style"] = {**assistant["sales_style"], **request.sales_style}
                    assistant_orm.assistant_sales_style = request.sales_style
                if request.voice_tone is not None:
                    # update_fields["voice_tone"] = {**assistant["voice_tone"], **request.voice_tone}
                    assistant_orm.assistant_voice_tone = request.voice_tone
                if request.specializations is not None:
                    # update_fields["specializations"] = request.specializations
                    assistant_orm.assistant_specializations = request.specializations
                if request.working_hours is not None:
                    # update_fields["working_hours"] = {**assistant["working_hours"], **request.working_hours}
                    assistant_orm.assistant_working_hours = request.working_hours
                if request.max_concurrent_customers is not None:
                    # update_fields["max_concurrent_customers"] = request.max_concurrent_customers
                    assistant_orm.assistant_max_concurrent_customers = request.max_concurrent_customers
                if request.permissions is not None:
                    # update_fields["permissions"] = request.permissions
                    assistant_orm.assistant_permissions = request.permissions
                if request.profile is not None:
                    # update_fields["profile"] = {**assistant["profile"], **request.profile}
                    assistant_orm.assistant_profile = request.profile
                # if request.status is not None:
                    # update_fields["status"] = request.status
                    # assistant_orm.status = request.status
                assistant_orm.updated_at = get_current_datetime()

                r = await AssistantRepository.update_assistant(assistant_orm, session)
                if r is True:
                    # raise Exception("更新助理失败")
                    self.logger.info(f"助理更新成功: {assistant_id}")

                prompt_orm = None
                # 处理提示词配置更新（如果提供）
                if request.prompt_config:
                    try:
                        prompts = await PromptsRepository.get_prompts_by_assistant_id(assistant_id, session)
                        now = get_current_datetime()

                        if prompts is None:
                            # 没有提示词，需要创建
                            promptsModel = PromptsModel(
                                tenant_id=assistant_orm.tenant_id,
                                assistant_id=assistant_id,
                                personality_prompt=request.personality_type,
                                greeting_prompt=request.prompt_config.greeting_prompt,
                                product_recommendation_prompt=request.prompt_config.product_recommendation_prompt,
                                objection_handling_prompt=request.prompt_config.objection_handling_prompt,
                                closing_prompt=request.prompt_config.closing_prompt,
                                context_instructions=request.prompt_config.context_instructions,
                                llm_parameters=request.prompt_config.llm_parameters,
                                safety_guidelines=request.prompt_config.safety_guidelines,
                                forbidden_topics=request.prompt_config.forbidden_topics,
                                brand_voice=request.prompt_config.brand_voice,
                                product_knowledge=request.prompt_config.product_knowledge,
                                version="1",
                                is_active=request.prompt_config.is_active,
                                created_at=now,
                                updated_at=now,
                            )
                            prompts_id = await PromptsRepository.insert_prompts(promptsModel.to_orm(), session)
                            if prompts_id is None:
                                raise HTTPException(status_code=500, detail="提示词不存在，创建失败")

                        else:
                            # 存在提示词，需要更新
                            if request.prompt_config.personality_prompt is not None:
                                prompts.personality_prompt = request.prompt_config.personality_prompt
                            if request.prompt_config.greeting_prompt is not None:
                                prompts.greeting_prompt = request.prompt_config.greeting_prompt
                            if request.prompt_config.product_recommendation_prompt is not None:
                                prompts.product_recommendation_prompt = request.prompt_config.product_recommendation_prompt
                            if request.prompt_config.objection_handling_prompt is not None:
                                prompts.objection_handling_prompt = request.prompt_config.objection_handling_prompt
                            if request.prompt_config.closing_prompt is not None:
                                prompts.closing_prompt = request.prompt_config.closing_prompt
                            if request.prompt_config.context_instructions is not None:
                                prompts.context_instructions = request.prompt_config.context_instructions
                            if request.prompt_config.llm_parameters is not None:
                                prompts.llm_parameters = request.prompt_config.llm_parameters
                            if request.prompt_config.safety_guidelines is not None:
                                prompts.safety_guidelines = request.prompt_config.safety_guidelines
                            if request.prompt_config.forbidden_topics is not None:
                                prompts.forbidden_topics = request.prompt_config.forbidden_topics
                            if request.prompt_config.brand_voice is not None:
                                prompts.brand_voice = request.prompt_config.brand_voice
                            if request.prompt_config.product_knowledge is not None:
                                prompts.product_knowledge = request.prompt_config.product_knowledge
                            # prompts.updated_at = now,
                            # todo version 应该是用纳秒级时间戳
                            prompts.version = "1"
                            from dataclasses import dataclass, asdict
                            is_success = await PromptsRepository.update_prompts_field(assistant_id, asdict(prompts), session)
                            if not is_success:
                                raise HTTPException("更新错误")
                        self.logger.info(f"助理 {assistant_id} 提示词配置更新成功")
                    except Exception as e:
                        self.logger.warning(f"助理 {assistant_id} 提示词配置更新失败: {e}")
                        # 不阻止助理更新，只记录警告

            async with database_session() as session:
                # 更新缓存数据
                update_prompts = await PromptsRepository.get_prompts_by_assistant_id(assistant_id, session)
                PromptsRepository.update_prompts_cache(update_prompts.to_model(), await get_redis_client())
                assistant_orm = await AssistantRepository.get_assistant_by_id(assistant_id, session)
                assistant_model = assistant_orm.to_business_model()
                AssistantRepository.update_assistant_cache_4_task(assistant_model)
            assistant_model.prompts_model_list = update_prompts
            return assistant_model

        except Exception as e:
            self.logger.error(f"助理更新失败: {e}")
            raise

    async def configure_assistant(
            self,
            assistant_id: str,
            tenant_id: str,
            request: AssistantConfigRequest
    ) -> AssistantOperationResponse:
        """
        配置助理设置
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            request: 配置请求
            
        返回:
            AssistantOperationResponse: 操作结果
        """
        try:
            assistant_key = f"{tenant_id}:{assistant_id}"
            assistant = self._assistants_store.get(assistant_key)

            if not assistant:
                return AssistantOperationResponse(
                    # success=False,
                    # message="助理不存在",
                    # data={},
                    # assistant_id=assistant_id,
                    # operation="configure",
                    # result_data={"error": "助理不存在"}
                )

            # 应用配置更新
            config_type = request.config_type
            config_data = request.config_data

            if config_type in assistant:
                if request.merge_mode:
                    # 合并模式
                    if isinstance(assistant[config_type], dict):
                        assistant[config_type] = {**assistant[config_type], **config_data}
                    elif isinstance(assistant[config_type], list):
                        assistant[config_type] = list(set(assistant[config_type] + config_data))
                    else:
                        assistant[config_type] = config_data
                else:
                    # 替换模式
                    assistant[config_type] = config_data
            else:
                assistant[config_type] = config_data

            # 更新时间戳
            assistant["updated_at"] = datetime.utcnow()
            self._assistants_store[assistant_key] = assistant

            self.logger.info(f"助理配置成功: {assistant_id}, 配置类型: {config_type}")

            return AssistantOperationResponse(
                # success=True,
                # message="助理配置成功",
                # data={},
                # assistant_id=assistant_id,
                # operation="configure",
                # result_data={"config_type": config_type, "updated": True}
            )

        except Exception as e:
            self.logger.error(f"助理配置失败: {e}")
            raise

    async def get_assistant_stats(
            self,
            assistant_id: str,
            tenant_id: str,
            days: int = 30,
            include_trends: bool = True,
            include_devices: bool = True
    ) -> Optional[AssistantStatsResponse]:
        """
        获取助理统计信息
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            days: 统计天数
            include_trends: 是否包含趋势数据
            include_devices: 是否包含设备统计
            
        返回:
            Optional[AssistantStatsResponse]: 统计信息
        """
        try:
            assistant_key = f"{tenant_id}:{assistant_id}"
            assistant = self._assistants_store.get(assistant_key)

            if not assistant:
                return None

            stats = self._assistant_stats.get(assistant_key, {})

            # 生成模拟统计数据
            trends_data = {}
            if include_trends:
                trends_data = {
                    "conversations": [10, 15, 12, 18, 20, 16, 22],
                    "satisfaction": [4.2, 4.3, 4.1, 4.4, 4.5, 4.3, 4.6],
                    "response_time": [2.1, 1.8, 2.3, 1.9, 1.7, 2.0, 1.6]
                }

            device_usage = {}
            if include_devices:
                device_usage = stats.get("device_usage", {})

            self.logger.info(f"助理统计查询成功: {assistant_id}")

            return AssistantStatsResponse(
                success=True,
                message="助理统计查询成功",
                data={},
                assistant_id=assistant_id,
                total_conversations=stats.get("total_conversations", 0),
                total_customers=stats.get("total_customers", 0),
                active_conversations=stats.get("current_customers", 0),
                average_response_time=2.1,
                customer_satisfaction=stats.get("average_rating", 4.5),
                conversion_rate=0.15,
                activity_by_hour=stats.get("activity_by_hour", {}),
                activity_by_day={},
                device_usage=device_usage,
                trends=trends_data
            )

        except Exception as e:
            self.logger.error(f"助理统计查询失败: {e}")
            raise

    async def activate_assistant(self, assistant_id: str, tenant_id: str) -> AssistantOperationResponse:
        """激活助理"""
        return await self._change_assistant_status(assistant_id, tenant_id, AssistantStatus.ACTIVE, "activate")

    async def deactivate_assistant(self, assistant_id: str, tenant_id: str) -> AssistantOperationResponse:
        """停用助理"""
        return await self._change_assistant_status(assistant_id, tenant_id, AssistantStatus.INACTIVE, "deactivate")

    async def delete_assistant(self, assistant_id: str, tenant_id: str, force: bool = False) -> AssistantOperationResponse:
        """
        删除助理
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            force: 是否强制删除
            
        返回:
            AssistantOperationResponse: 操作结果
        """
        try:
            # assistant_key = f"{tenant_id}:{assistant_id}"
            assistant = await AssistantService.get_assistant_by_id(assistant_id)

            if not assistant:
                return AssistantOperationResponse(
                    code=4001,
                    message="助理不存在",
                    # success=False,
                    # message="助理不存在",
                    # data={},
                    # assistant_id=assistant_id,
                    # operation="delete",
                    # result_data={"error": "助理不存在"}
                )

            # todo 检查是否有活跃对话（模拟检查）
            # stats = self._assistant_stats.get(assistant_key, {})
            # current_customers = stats.get("current_customers", 0)
            current_customers = 0

            if current_customers > 0 and not force:
                return AssistantOperationResponse(
                    code=10001,
                    message="助理有活跃对话，需要强制删除标志",
                    # success=False,
                    # message="助理有活跃对话，需要强制删除标志",
                    # data={},
                    # assistant_id=assistant_id,
                    # operation="delete",
                    # result_data={"error": "有活跃对话", "active_conversations": current_customers}
                )

            # 删除助理数据
            # del self._assistants_store[assistant_key]
            # if assistant_key in self._assistant_stats:
            #     del self._assistant_stats[assistant_key]
            assistant.is_active = None
            # todo 不应该调用 save，应该调用 update，后面有了接口再调整
            assistant = await AssistantService.save(assistant)

            self.logger.info(f"助理删除成功: {assistant_id}")

            return AssistantOperationResponse(
                code=0,
                message="助理删除成功",
                # data=assistant,

                # success=True,
                # message="助理删除成功",
                # data={},
                # assistant_id=assistant_id,
                # operation="delete",
                # result_data={"deleted": True, "force": force},
                # affected_conversations=current_customers
            )

        except Exception as e:
            self.logger.error(f"助理删除失败: {e}")
            raise

    async def _change_assistant_status(
            self,
            assistant_id: str,
            tenant_id: str,
            new_status: AssistantStatus,
            operation: str
    ) -> AssistantOperationResponse:
        """改变助理状态的通用方法"""
        try:
            # assistant_key = f"{tenant_id}:{assistant_id}"
            # assistant = self._assistants_store.get(assistant_key)

            assistant = await AssistantService.get_assistant_by_id(assistant_id)

            if not assistant:
                r = AssistantOperationResponse()
                r.assistant_id = assistant_id
                r.operation = operation,
                r.success = True,
                r.result_data = {"error": "助理不存在"}
                return AssistantOperationResponse(
                    success=False,
                    message="助理不存在",
                    data=r,
                )

            # assistant.previous_status = assistant["status"]
            # assistant["status"] = new_status
            # assistant["updated_at"] = datetime.utcnow()

            previous_status = new_status
            assistant.assistant_status = new_status
            assistant.updated_at = datetime.utcnow()

            if new_status == AssistantStatus.ACTIVE:
                # assistant["last_active_at"] = datetime.utcnow()
                assistant.last_active_at = datetime.utcnow()

            r = await AssistantService.save(assistant)

            # self._assistants_store[assistant_key] = assistant
            if r is True:
                self.logger.info(f"助理状态变更成功: {assistant_id}, {previous_status} -> {new_status}")
                r = AssistantOperationResponse(assistant_id=assistant_id, operation=operation, success=True, )
                r.assistant_id = assistant_id
                r.operation = operation
                r.success = True
                r.previous_status = new_status
                r.new_status = new_status
                r.result_data = {"status_changed": True}
                return AssistantOperationResponse(
                    success=True,
                    message=f"助理{operation}成功",
                    data=r,
                )


        except Exception as e:
            self.logger.error(f"助理状态变更失败: {e}")
            raise

    def _get_default_sales_style(self, personality_type: PersonalityType) -> Dict[str, Any]:
        """获取默认销售风格配置"""
        styles = {
            PersonalityType.PROFESSIONAL: {
                "approach": "consultative",
                "communication_style": "formal",
                "sales_techniques": ["needs_analysis", "solution_selling"]
            },
            PersonalityType.FRIENDLY: {
                "approach": "relationship_building",
                "communication_style": "casual",
                "sales_techniques": ["rapport_building", "storytelling"]
            },
            PersonalityType.CONSULTATIVE: {
                "approach": "advisory",
                "communication_style": "educational",
                "sales_techniques": ["expert_positioning", "problem_solving"]
            },
            PersonalityType.ENTHUSIASTIC: {
                "approach": "energetic",
                "communication_style": "passionate",
                "sales_techniques": ["excitement_building", "urgency_creation"]
            },
            PersonalityType.GENTLE: {
                "approach": "supportive",
                "communication_style": "caring",
                "sales_techniques": ["trust_building", "gentle_guidance"]
            }
        }
        return styles.get(personality_type, styles[PersonalityType.PROFESSIONAL])

    def _get_default_voice_tone(self, personality_type: PersonalityType) -> Dict[str, Any]:
        """获取默认语音语调配置"""
        tones = {
            PersonalityType.PROFESSIONAL: {
                "tone": "confident",
                "pace": "moderate",
                "volume": "normal",
                "pitch": "medium"
            },
            PersonalityType.FRIENDLY: {
                "tone": "warm",
                "pace": "relaxed",
                "volume": "normal",
                "pitch": "slightly_higher"
            },
            PersonalityType.CONSULTATIVE: {
                "tone": "authoritative",
                "pace": "deliberate",
                "volume": "clear",
                "pitch": "medium"
            },
            PersonalityType.ENTHUSIASTIC: {
                "tone": "excited",
                "pace": "quick",
                "volume": "slightly_louder",
                "pitch": "higher"
            },
            PersonalityType.GENTLE: {
                "tone": "soothing",
                "pace": "slow",
                "volume": "soft",
                "pitch": "lower"
            }
        }
        return tones.get(personality_type, tones[PersonalityType.PROFESSIONAL])

    def _get_default_working_hours(self) -> Dict[str, Any]:
        """获取默认工作时间配置"""
        return {
            "timezone": "UTC",
            "schedule": {
                "monday": {"start": "09:00", "end": "18:00"},
                "tuesday": {"start": "09:00", "end": "18:00"},
                "wednesday": {"start": "09:00", "end": "18:00"},
                "thursday": {"start": "09:00", "end": "18:00"},
                "friday": {"start": "09:00", "end": "18:00"},
                "saturday": {"start": "10:00", "end": "16:00"},
                "sunday": {"start": "10:00", "end": "16:00"}
            },
            "breaks": [
                {"start": "12:00", "end": "13:00", "name": "午休"}
            ]
        }

    def _get_default_permissions(self, expertise_level: ExpertiseLevel) -> List[str]:
        """根据专业等级获取默认权限"""
        base_permissions = ["view_products", "chat_with_customers", "access_basic_analytics"]

        if expertise_level in [ExpertiseLevel.INTERMEDIATE, ExpertiseLevel.SENIOR, ExpertiseLevel.EXPERT]:
            base_permissions.extend(["create_promotions", "access_customer_history"])

        if expertise_level in [ExpertiseLevel.SENIOR, ExpertiseLevel.EXPERT]:
            base_permissions.extend(["manage_inventory", "access_advanced_analytics", "train_junior_staff"])

        if expertise_level == ExpertiseLevel.EXPERT:
            base_permissions.extend(["system_configuration", "manage_team", "access_all_data"])

        return base_permissions

    async def get_assistant_with_prompt_config(
            self,
            assistant_id: str,
            tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取助理信息及其提示词配置
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            
        返回:
            Optional[Dict[str, Any]]: 包含提示词配置的助理信息
        """
        try:
            # 获取基础助理信息
            assistant = await self.get_assistant_details(assistant_id, tenant_id)
            if not assistant:
                return None

            # 获取提示词配置
            try:
                prompt_config = await self.prompt_handler.get_assistant_prompts(
                    assistant_id, tenant_id
                )
                if prompt_config:
                    assistant_data = assistant.dict() if hasattr(assistant, 'dict') else assistant
                    assistant_data["prompt_config"] = prompt_config.config.dict() if hasattr(prompt_config.config,
                                                                                             'dict') else prompt_config.config
                    return assistant_data
            except Exception as e:
                self.logger.warning(f"获取助理 {assistant_id} 提示词配置失败: {e}")

            # 返回不含提示词配置的助理信息
            return assistant.dict() if hasattr(assistant, 'dict') else assistant

        except Exception as e:
            self.logger.error(f"获取助理详细信息失败: {e}")
            return None
