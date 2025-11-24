"""
提示词处理器

该模块提供提示词管理的业务逻辑处理，包括提示词配置、验证、测试
和库管理等功能。支持基于提示词的智能体个性化定制。

主要功能:
- 提示词配置管理
- 提示词测试和验证
- 提示词库管理
- 版本控制和历史记录
"""
import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from infra.db import database_session
from models.prompts import PromptsModel, PromptsOrmModel
from repositories.assistant_repo import AssistantRepository
from repositories.prompts_repo import PromptsRepository
from schemas.prompts_schema import (
    PromptCreateRequest, PromptUpdateRequest,
    PromptLibrarySearchRequest,
    PromptLibraryResponse,
    AssistantPromptConfig, PromptLibraryItem,
    PromptCategory, PromptType, PromptLanguage
)
from utils import get_component_logger, get_current_datetime
from fastapi import HTTPException


class PromptService:
    """
    提示词处理器
    
    处理智能体提示词相关的业务逻辑，包括配置管理、测试验证和库管理。
    """

    def __init__(self):
        """初始化提示词处理器"""
        self.logger = get_component_logger(__name__)

        # 模拟数据存储（实际应用中应该使用数据库）
        self._prompt_configs: Dict[str, Dict[str, Any]] = {}
        self._prompt_history: Dict[str, List[Dict[str, Any]]] = {}
        self._prompt_library: List[PromptLibraryItem] = []

        # 初始化提示词库
        self._initialize_prompt_library()

        self.logger.info("提示词处理器初始化完成")

    async def create_assistant_prompts(self, request: PromptCreateRequest) -> PromptsModel:
        """
        创建助理提示词配置
        
        参数:
            request: 提示词创建请求
            
        返回:
            PromptConfigResponse: 配置结果
        """
        try:
            # 验证提示词配置
            await self._validate_prompt_config(request.prompt_config)

            async with database_session() as session:
                # 再获取员工的 tenantID
                # assistant_service = AssistantService()
                # await assistant_service.get_assistant_by_id(assistant_id=prompts_model.assistant_id, use_cache=False)
                assistant_orm = await AssistantRepository.get_assistant_by_id(request.assistant_id, session)
                if assistant_orm is None:
                    raise Exception("员工不存在")
                if request.tenant_id != assistant_orm.tenant_id:
                    raise Exception("租户ID不正常")

            now = datetime.utcnow()
            prompts_model = PromptsModel(
                tenant_id=assistant_orm.tenant_id,
                assistant_id=request.assistant_id,
                personality_prompt=request.prompt_config.personality_prompt,
                greeting_prompt=request.prompt_config.greeting_prompt,
                product_recommendation_prompt=request.prompt_config.product_recommendation_prompt,
                objection_handling_prompt=request.prompt_config.tenant_id,
                closing_prompt=request.prompt_config.closing_prompt,
                context_instructions=request.prompt_config.context_instructions,
                llm_parameters=request.prompt_config.llm_parameters,
                safety_guidelines=request.prompt_config.safety_guidelines,
                forbidden_topics=request.prompt_config.forbidden_topics,
                brand_voice=request.prompt_config.brand_voice,
                product_knowledge=request.prompt_config.product_knowledge,
                version=time.perf_counter_ns(),
                is_enable=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            )

            return await self._create_assistant_prompts(prompts_model)
        except Exception as e:
            self.logger.error(f"助理提示词配置创建失败: {e}")
            raise

    async def _create_assistant_prompts(self, prompts_model: PromptsModel) -> PromptsModel:
        try:
            async with database_session() as session:
                # 先校验员工提示词是否存在
                prompts_orm = await PromptsRepository.get_latest_prompts_by_assistant_id(prompts_model.assistant_id,
                                                                                         session)
                if prompts_orm:
                    raise HTTPException("数字员工的提示词已存在")

                prompts_id = await PromptsRepository.insert_prompts(prompts_model.to_orm(), session)
                prompts_model.id = prompts_id
            self.logger.error(f"助理提示词配置创建成功: {prompts_model.assistant_id} {prompts_model}")
            asyncio.create_task(PromptsRepository.update_prompts_cache(prompts_model))
            asyncio.create_task(PromptsRepository.update_prompts_latest_version_cache(prompts_model.assistant_id,
                                                                                      prompts_model.version))
            return prompts_model
        except Exception as e:
            self.logger.error(f"助理提示词配置创建失败: {e}")
            raise

    async def get_assistant_prompts(
            self,
            assistant_id: str,
            version: Optional[int] = None,
            use_cache: bool = True
    ) -> Optional[PromptsModel]:
        """
        获取助理提示词配置
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            version: 指定版本（可选）
            
        返回:
            Optional[PromptConfigResponse]: 配置信息
        """
        try:
            if version is None:
                # 默认返回最新版本
                if use_cache:
                    version = await PromptsRepository.get_prompts_latest_version_cache(assistant_id)
                if version is None:
                    # 直接从数据库中获取最新版本的数据
                    async with database_session() as session:
                        prompts_orm = await PromptsRepository.get_latest_prompts_by_assistant_id(assistant_id, session)
                        if prompts_orm is None:
                            # raise Exception(
                            #     f"prompts 不存在。assistant_id={assistant_id}, version={version}")
                            return None
                        else:
                            asyncio.create_task(
                                PromptsRepository.update_prompts_latest_version_cache(assistant_id, prompts_orm.version))
                            asyncio.create_task(PromptsRepository.update_prompts_cache(prompts_orm.to_model()))
                            return prompts_orm.to_model()

            # 从缓存中获取获取指定版本
            if use_cache:
                prompts_model = await PromptsRepository.get_prompts_cache(assistant_id, version)
                if prompts_model is not None:
                    return prompts_model

            # 从数据库中获取指定版本

            async with database_session() as session:
                prompts_orm = await PromptsRepository.get_prompts_by_version(assistant_id, version, session)
                if prompts_orm is None:
                    raise Exception(f"version 存在， prompts 不存在。assistant_id={assistant_id}, version={version}")
                self.logger.info(f"助理提示词配置查询成功: {assistant_id}")
            # 更新缓存
            asyncio.create_task(PromptsRepository.update_prompts_cache(prompts_orm.to_model()))
            asyncio.create_task(PromptsRepository.update_prompts_latest_version_cache(assistant_id, version))
            return prompts_orm.to_model()
        except Exception as e:
            self.logger.error(f"助理提示词配置查询失败: {e}")
            raise

    async def _update_assistant_prompts(
            self,
            assistant_id: str,
            prompts_orm: PromptsOrmModel
    ) -> PromptsModel:
        """
        更新助理提示词配置

        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            request: 更新请求

        返回:
            Optional[PromptConfigResponse]: 更新后的配置
        """
        try:
            async with database_session() as session:
                prompts_orm_exists = await PromptsRepository.get_latest_prompts_by_assistant_id(assistant_id, session)
                if not prompts_orm_exists:
                    raise Exception(f"提示词不存在，assistant_id={assistant_id}")

                # 禁用正在生效的提示词
                is_disable = await PromptsRepository.disable_prompts_by_version(prompts_orm_exists.assistant_id,
                                                                                prompts_orm_exists.version, session)
                if not is_disable:
                    raise Exception(f"禁用提示词失败")
                prompts_orm.is_enable = True
                prompts_orm.is_enable = True
                prompts_id = await PromptsRepository.insert_prompts(prompts_orm, session)
                if prompts_id is None:
                    self.logger.error(f"助理提示词配置报错: assistant_id={assistant_id}, 版本: {prompts_orm.version}."
                                      f" 提示词={prompts_orm}")
                    raise Exception("保存提示词报错")

                # todo 验证更新后的配置
                # await self._validate_prompt_config(updated_config)
                self.logger.error(f"助理提示词配置成功: assistant_id={assistant_id}, 版本: {prompts_orm.version}."
                                  f" 提示词={prompts_orm}")
            prompts_model = prompts_orm.to_model()
            # 为新创建的提示词创建缓存
            asyncio.create_task(
                PromptsRepository.update_prompts_latest_version_cache(assistant_id, prompts_orm.version)
            )
            asyncio.create_task(PromptsRepository.update_prompts_cache(prompts_model))
            # 删除旧的提示词缓存
            asyncio.create_task(
                PromptsRepository.delete_assistant_cache(prompts_orm_exists.assistant_id, prompts_orm_exists.version))

            return prompts_model
        except Exception as e:
            self.logger.error(f"助理提示词配置更新失败: {e}")
            raise

    async def update_assistant_prompts(
            self,
            assistant_id: str,
            request: PromptUpdateRequest
    ) -> PromptsModel:
        """
        更新助理提示词配置
        
        参数:
            assistant_id: 助理ID
            tenant_id: 租户ID
            request: 更新请求
            
        返回:
            Optional[PromptConfigResponse]: 更新后的配置
        """
        try:
            async with database_session() as session:
                prompts_orm_exists = await PromptsRepository.get_latest_prompts_by_assistant_id(assistant_id, session)
                if not prompts_orm_exists:
                    raise Exception(f"提示词不存在，assistant_id={assistant_id}")
                prompts_orm = prompts_orm_exists.copy()

                # 存在提示词，需要重新创建
                if request.personality_prompt is not None:
                    prompts_orm.personality_prompt = request.personality_prompt
                if request.greeting_prompt is not None:
                    prompts_orm.greeting_prompt = request.greeting_prompt
                if request.product_recommendation_prompt is not None:
                    prompts_orm.product_recommendation_prompt = request.product_recommendation_prompt
                if request.objection_handling_prompt is not None:
                    prompts_orm.objection_handling_prompt = request.objection_handling_prompt
                if request.closing_prompt is not None:
                    prompts_orm.closing_prompt = request.closing_prompt
                if request.context_instructions is not None:
                    prompts_orm.context_instructions = request.context_instructions
                if request.llm_parameters is not None:
                    prompts_orm.llm_parameters = request.llm_parameters
                if request.safety_guidelines is not None:
                    prompts_orm.safety_guidelines = request.safety_guidelines
                if request.forbidden_topics is not None:
                    prompts_orm.forbidden_topics = request.forbidden_topics
                if request.brand_voice is not None:
                    prompts_orm.brand_voice = request.brand_voice
                if request.product_knowledge is not None:
                    prompts_orm.product_knowledge = request.product_knowledge
                prompts_orm.updated_at = get_current_datetime()
                prompts_orm.version = time.perf_counter_ns()

                # 禁用正在生效的提示词
                is_disable = await PromptsRepository.disable_prompts_by_version(prompts_orm_exists.assistant_id,
                                                                                prompts_orm_exists.version, session)
                if not is_disable:
                    raise Exception(f"禁用提示词失败")
                prompts_orm.is_enable = True
                prompts_orm.is_enable = True
                prompts_id = await PromptsRepository.insert_prompts(prompts_orm, session)
                if prompts_id is None:
                    self.logger.error(f"助理提示词配置报错: assistant_id={assistant_id}, 版本: {prompts_orm.version}."
                                      f" 提示词={prompts_orm}")
                    raise Exception("保存提示词报错")

                # todo 验证更新后的配置
                # await self._validate_prompt_config(updated_config)
                self.logger.error(f"助理提示词配置成功: assistant_id={assistant_id}, 版本: {prompts_orm.version}."
                                  f" 提示词={prompts_orm}")
            prompts_model = prompts_orm.to_model()
            # 为新创建的提示词创建缓存
            asyncio.create_task(
                PromptsRepository.update_prompts_latest_version_cache(assistant_id, prompts_orm.version)
            )
            asyncio.create_task(PromptsRepository.update_prompts_cache(prompts_model))
            # 删除旧的提示词缓存
            asyncio.create_task(
                PromptsRepository.delete_assistant_cache(prompts_orm_exists.assistant_id, prompts_orm_exists.version))

            return prompts_model
        except Exception as e:
            self.logger.error(f"助理提示词配置更新失败: {e}")
            raise

    async def get_prompt_library(self, request: PromptLibrarySearchRequest) -> PromptLibraryResponse:
        """
        获取提示词库
        
        参数:
            request: 搜索请求
            
        返回:
            PromptLibraryResponse: 提示词库内容
        """
        try:
            # 筛选提示词库
            filtered_items = []

            for item in self._prompt_library:
                # 分类筛选
                if request.category and item.category != request.category:
                    continue

                # 类型筛选
                if request.prompt_type and item.prompt_type != request.prompt_type:
                    continue

                # 语言筛选
                if request.language and item.language != request.language:
                    continue

                # 关键词搜索
                if request.search_text:
                    search_text = request.search_text.lower()
                    if not (search_text in item.title.lower() or
                            search_text in item.use_case.lower() or
                            search_text in item.prompt_content.lower()):
                        continue

                filtered_items.append(item)

            # 排序
            reverse = request.sort_order == "desc"
            if request.sort_by == "rating":
                filtered_items.sort(key=lambda x: x.rating, reverse=reverse)
            elif request.sort_by == "usage_count":
                filtered_items.sort(key=lambda x: x.usage_count, reverse=reverse)
            elif request.sort_by == "created_at":
                filtered_items.sort(key=lambda x: x.created_at, reverse=reverse)

            # 分页
            total_count = len(filtered_items)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            paginated_items = filtered_items[start_idx:end_idx]

            # 统计信息
            categories = {}
            languages = {}

            for item in self._prompt_library:
                categories[item.category.value] = categories.get(item.category.value, 0) + 1
                languages[item.language.value] = languages.get(item.language.value, 0) + 1

            self.logger.info(f"提示词库查询成功: 返回{len(paginated_items)}/{total_count}条记录")

            return PromptLibraryResponse(
                success=True,
                message="提示词库查询成功",
                data=paginated_items,
                items=paginated_items,
                categories=categories,
                languages=languages,
                total=total_count,
                page=request.page,
                page_size=request.page_size,
                pages=(total_count + request.page_size - 1)  # request.page_size,
            )

        except Exception as e:
            self.logger.error(f"提示词库查询失败: {e}")
            raise

    async def clone_assistant_prompts(
            self,
            source_assistant_id: str,
            target_assistant_id: str,
            target_tenant_id: str,
            modify_personality: bool = False
    ) -> PromptsModel:
        """克隆助理提示词配置"""
        try:
            # 获取 target 租户，校验信息
            from services.assistant_service import AssistantService
            assistant_service = AssistantService()
            target_assistant_model = await assistant_service.get_assistant_by_id(assistant_id=target_assistant_id,
                                                                                 use_cache=False)
            if target_assistant_model is None:
                raise Exception("目标数字员工不存在")
            if target_assistant_model.assistant_id != target_assistant_id or target_assistant_model.tenant_id != target_tenant_id:
                raise Exception("目标数字员工 id 或 目标租户 id 校验不正确")

            # 获取要克隆的版本
            source_prompts_model = await self.get_assistant_prompts(assistant_id=source_assistant_id, use_cache=False)
            if source_prompts_model is None:
                raise Exception("source assistant 无提示词")

            copy_prompts_orm = source_prompts_model.to_orm().copy()
            copy_prompts_orm.assistant_id = target_assistant_id

            if modify_personality:
                # 修改个性化部分，避免完全相同
                copy_prompts_orm.personality_prompt = (f"{copy_prompts_orm.personality_prompt}\n\n注意："
                                                       f"作为{target_assistant_id}，请保持独特的个性特色。")

            # 更新版本
            copy_prompts_orm.version = time.perf_counter_ns()
            now = get_current_datetime()
            copy_prompts_orm.created_at = now
            copy_prompts_orm.updated_at = now

            # 检查 target 租户下有无 prompts
            target_assistant_is_enable_prompts = await self.get_assistant_prompts(assistant_id=target_assistant_id,use_cache=False)
            if target_assistant_is_enable_prompts:
                r = await self._update_assistant_prompts(assistant_id=target_assistant_id, prompts_orm=copy_prompts_orm)
                return r
            else:
                r = await self._create_assistant_prompts(copy_prompts_orm.to_model())
                return r

        except Exception as e:
            self.logger.error(f"助理提示词克隆失败: {e}")
            raise

    async def get_prompt_history(
            self,
            assistant_id: str,
            limit: int = 10
    ) -> list[PromptsModel]:
        """获取提示词历史版本"""
        try:

            r = await PromptsRepository.get_prompts_list_order(assistant_id, limit)
            l: list[PromptsModel] = []
            for prompt in r:
                l.append(prompt.to_model())
            return l

        except Exception as e:
            self.logger.error(f"提示词历史查询失败: {e}")
            raise

    async def rollback_assistant_prompts(
            self,
            assistant_id: str,
            target_version: int
    ) -> Optional[PromptsModel]:
        """回退提示词配置到指定版本"""
        try:
            async with database_session() as session:
                is_active_prompts = await PromptsRepository.get_latest_prompts_by_assistant_id(assistant_id, session)
                if not is_active_prompts:
                    raise Exception(f"没有正在生效的提示词")
                target_prompts = await PromptsRepository.get_prompts_by_version(assistant_id, target_version, session)
                if not target_prompts:
                    raise Exception(f"指定版本不存在. assistant_id={assistant_id} version={target_version}")

                is_disable = await PromptsRepository.disable_prompts_by_version(assistant_id, is_active_prompts.version,
                                                                          session)
                if not is_disable:
                    raise Exception(f"禁用失败。"
                                    f"assistant_id={assistant_id} "
                                    f"disable.version={is_active_prompts.version} "
                                    f"target.version={target_prompts.version}"
                                    )
                is_enable = await PromptsRepository.enable_prompts_by_version(assistant_id, target_prompts.version, session)
                if not is_enable:
                    raise Exception(f"启用失败。"
                                    f"assistant_id={assistant_id} "
                                    f"disable.version={is_active_prompts.version} "
                                    f"enable.version={target_prompts.version}"
                                    )
                # 如果不额外查询一次，直接使用 target_prompts，会报错。
                target_prompts = await PromptsRepository.get_prompts_by_version(assistant_id, target_version, session)
                if not target_prompts:
                    raise Exception(f"更新后的版本不存在. assistant_id={assistant_id} version={target_version}")
                self.logger.info(f"提示词配置回退成功: {assistant_id}, 回退到版本: {target_version}")
            # 更新新缓存
            asyncio.create_task(PromptsRepository.update_prompts_latest_version_cache(assistant_id, target_version))
            model = target_prompts.to_model()
            asyncio.create_task(PromptsRepository.update_prompts_cache(model))
            # 删除之前生效的提示词缓存
            asyncio.create_task(PromptsRepository.delete_assistant_cache(is_active_prompts.assistant_id, is_active_prompts.version))

            return model
        except Exception as e:
            self.logger.error(f"提示词配置回退失败: {e}")
            raise

    # 私有辅助方法

    async def _validate_prompt_config(self, config: AssistantPromptConfig) -> None:
        """验证提示词配置的基本有效性"""
        if not config.personality_prompt or len(config.personality_prompt.strip()) < 50:
            raise ValueError("个性化提示词长度不能少于50个字符")

        if len(config.personality_prompt) > 4000:
            raise ValueError("个性化提示词长度不能超过4000个字符")

        # 检查危险关键词
        dangerous_keywords = ["ignore", "forget", "system", "override", "jailbreak"]
        for keyword in dangerous_keywords:
            if keyword in config.personality_prompt.lower():
                raise ValueError(f"提示词包含危险关键词: {keyword}")

    def _initialize_prompt_library(self):
        """初始化提示词库"""
        # 销售类提示词
        self._prompt_library.extend([
            PromptLibraryItem(
                item_id="sales_001",
                title="专业护肤顾问",
                category=PromptCategory.SALES,
                prompt_type=PromptType.PERSONALITY,
                language=PromptLanguage.CHINESE,
                prompt_content="""你是一位专业的护肤顾问，拥有丰富的皮肤护理知识和产品经验。你的目标是帮助客户找到最适合的护肤解决方案。

你的特点：
- 专业且耐心，善于倾听客户需求
- 能够根据不同肌肤类型提供个性化建议
- 熟悉各类护肤成分和产品功效
- 注重教育客户正确的护肤知识

交流风格：
- 语言温和专业，避免过于商业化的推销
- 先了解客户肌肤状况再推荐产品
- 提供详细的使用方法和注意事项
- 鼓励客户建立长期的护肤习惯""",
                use_case="适用于护肤品牌的专业咨询服务",
                recommended_parameters={"temperature": 0.7, "max_tokens": 800},
                author="护肤专家团队",
                usage_count=156,
                rating=4.8,
                example_context={"customer_skin_type": "油性", "concern": "痘痘"},
                example_output="根据您的油性肌肤特点和痘痘困扰，我建议您选择含有水杨酸成分的温和洁面产品...",
                notes="适合需要专业护肤建议的场景，避免过度推销"
            ),

            PromptLibraryItem(
                item_id="sales_002",
                title="时尚彩妆顾问",
                category=PromptCategory.SALES,
                prompt_type=PromptType.PERSONALITY,
                language=PromptLanguage.CHINESE,
                prompt_content="""你是一位充满活力的时尚彩妆顾问，对色彩搭配和妆容设计有着敏锐的直觉。你的使命是帮助每位客户展现最美的自己。

你的特点：
- 热情开朗，富有时尚感和创意
- 对色彩理论和妆容技巧了如指掌
- 能快速捕捉客户的风格偏好
- 善于推荐适合不同场合的妆容

交流风格：
- 语言生动有趣，充满正能量
- 分享实用的化妆技巧和流行趋势
- 鼓励客户尝试新的妆容风格
- 注重产品的实际使用效果""",
                use_case="适用于彩妆品牌的时尚咨询和产品推荐",
                recommended_parameters={"temperature": 0.8, "max_tokens": 600},
                author="彩妆师团队",
                usage_count=203,
                rating=4.6,
                example_context={"occasion": "约会", "skin_tone": "暖调"},
                example_output="约会妆容重在自然甜美！根据您的暖调肌肤，我推荐珊瑚色系的口红和腮红...",
                notes="适合年轻化、时尚化的彩妆品牌"
            )
        ])

        # 客服类提示词
        self._prompt_library.extend([
            PromptLibraryItem(
                item_id="service_001",
                title="贴心客服助手",
                category=PromptCategory.CUSTOMER_SERVICE,
                prompt_type=PromptType.PERSONALITY,
                language=PromptLanguage.CHINESE,
                prompt_content="""你是一位贴心专业的客服助手，致力于为每位客户提供优质的服务体验。

你的职责：
- 耐心解答客户的各种疑问
- 协助处理订单、配送、退换货等问题
- 收集客户反馈并提供解决方案
- 维护良好的客户关系

服务原则：
- 始终保持礼貌和耐心
- 快速准确地解决客户问题
- 主动关心客户需求
- 遇到复杂问题及时转接专业人员

沟通风格：
- 语言亲切自然，让客户感受到关怀
- 回答清晰准确，避免模糊表达
- 积极主动，提供额外的帮助建议""",
                use_case="适用于售后客服和订单咨询服务",
                recommended_parameters={"temperature": 0.6, "max_tokens": 500},
                author="客服团队",
                usage_count=89,
                rating=4.7,
                notes="注重问题解决的时效性和准确性"
            )
        ])

        self.logger.info(f"提示词库初始化完成，共加载{len(self._prompt_library)}个模板")
